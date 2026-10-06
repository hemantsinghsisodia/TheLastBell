#include "Tests/LBRouteBot.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Editor.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerStart.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/CapsuleComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Character/LBCharacter.h"
#include "Components/LBInteractorComponent.h"
#include "Components/LBInteractableComponent.h"
#include "Objectives/LBObjectiveChainData.h"
#include "Objectives/LBObjectiveSubsystem.h"
#include "Save/LBCheckpoint.h"
#include "Save/LBSaveSubsystem.h"
#include "Systems/LBGameMode.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "LBLog.h"

// ---------------------------------------------------------------------------------------------------------------------
// LBPie helpers
// ---------------------------------------------------------------------------------------------------------------------
namespace LBPie
{
	UWorld* World() { return GEditor ? GEditor->PlayWorld.Get() : nullptr; }

	ALBCharacter* Pawn()
	{
		UWorld* W = World();
		APlayerController* PC = W ? W->GetFirstPlayerController() : nullptr;
		return PC ? Cast<ALBCharacter>(PC->GetPawn()) : nullptr;
	}

	bool WorldReady()
	{
		UWorld* W = World();
		return W && W->HasBegunPlay() && Pawn() != nullptr && W->GetSubsystem<ULBObjectiveSubsystem>() != nullptr;
	}

	int32 ObjIndex()
	{
		const ULBObjectiveSubsystem* Obj = World() ? World()->GetSubsystem<ULBObjectiveSubsystem>() : nullptr;
		return Obj ? Obj->GetActiveIndex() : -999;
	}

	bool HasState(const FGameplayTag& InTag)
	{
		const ULBWorldStateSubsystem* S = ULBWorldStateSubsystem::Get(World());
		return S && InTag.IsValid() && S->HasState(InTag);
	}

	FGameplayTag Tag(const TCHAR* Name) { return FGameplayTag::RequestGameplayTag(FName(Name), false); }

	FString MapShortName()
	{
		UWorld* W = World();
		return W ? UWorld::RemovePIEPrefix(W->GetOutermost()->GetName()) : FString();
	}

	void Teleport(const FVector& Location, const FRotator& Rotation)
	{
		ALBCharacter* P = Pawn();
		if (!P)
		{
			return;
		}
		P->SetActorLocation(Location, false, nullptr, ETeleportType::TeleportPhysics);
		if (UCharacterMovementComponent* Move = P->GetCharacterMovement())
		{
			Move->StopMovementImmediately();
		}
		if (AController* C = P->GetController())
		{
			C->SetControlRotation(Rotation);
		}
	}

	void ClearSlot() { UGameplayStatics::DeleteGameInSlot(ULBSaveSubsystem::SlotName, ULBSaveSubsystem::UserIndex); }
}

// ---------------------------------------------------------------------------------------------------------------------
// Reflection helpers (BP actors expose their config as plain properties)
// ---------------------------------------------------------------------------------------------------------------------
namespace
{
	bool ReadTagContainer(const AActor* A, const TCHAR* Name, FGameplayTagContainer& Out)
	{
		const FStructProperty* P = FindFProperty<FStructProperty>(A->GetClass(), Name);
		if (!P || P->Struct != FGameplayTagContainer::StaticStruct())
		{
			return false;
		}
		Out = *P->ContainerPtrToValuePtr<FGameplayTagContainer>(A);
		return true;
	}

	bool ReadTag(const AActor* A, const TCHAR* Name, FGameplayTag& Out)
	{
		const FStructProperty* P = FindFProperty<FStructProperty>(A->GetClass(), Name);
		if (!P || P->Struct != FGameplayTag::StaticStruct())
		{
			return false;
		}
		Out = *P->ContainerPtrToValuePtr<FGameplayTag>(A);
		return true;
	}

	FString Label(const AActor* A) { return A ? A->GetActorLabel() : FString(TEXT("<none>")); }

	const FVector GDirs[4] = { FVector(1, 0, 0), FVector(-1, 0, 0), FVector(0, 1, 0), FVector(0, -1, 0) };

	const ULBObjectiveChainData* ActiveChain()
	{
		const ALBGameMode* GM = LBPie::World() ? LBPie::World()->GetAuthGameMode<ALBGameMode>() : nullptr;
		return GM ? GM->GetObjectiveChain() : nullptr;
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// FLBRouteBot
// ---------------------------------------------------------------------------------------------------------------------
FLBRouteBot::FLBRouteBot(FAutomationTestBase* InTest, const FConfig& InConfig) : Test(InTest), Config(InConfig) {}

void FLBRouteBot::ResetForNewWorld()
{
	Phase = EPhase::Plan;
	CurObjective = -999;
	FailedProviders.Reset();
	PendingCheckpoints.Reset();
	Attempt = -1;
}

FLBRouteBot::EStatus FLBRouteBot::Fail(const FString& Message)
{
	Test->AddError(FString::Printf(TEXT("[RouteBot] %s"), *Message));
	UE_LOG(LogLB, Error, TEXT("[RouteBot] FAILED: %s"), *Message);
	return EStatus::Failed;
}

FLBRouteBot::EStatus FLBRouteBot::Tick()
{
	if (!LBPie::WorldReady())
	{
		return EStatus::Running;
	}
	if (BotWorld.Get() != LBPie::World())
	{
		BotWorld = LBPie::World();
		ResetForNewWorld();
	}
	if (const ALBCharacter* P = LBPie::Pawn(); P && P->IsDead())
	{
		return EStatus::Running;
	}
	switch (Phase)
	{
	case EPhase::Plan: return TickPlan();
	case EPhase::Act: return TickAct();
	default: return TickCheckpoints();
	}
}

FString FLBRouteBot::ObjectiveText() const
{
	const ULBObjectiveChainData* Chain = ActiveChain();
	return (Chain && Chain->Objectives.IsValidIndex(CurObjective)) ? Chain->Objectives[CurObjective].Text.ToString() : FString();
}

FGameplayTag FLBRouteBot::FirstMissingTag() const
{
	const ULBObjectiveChainData* Chain = ActiveChain();
	if (Chain && Chain->Objectives.IsValidIndex(CurObjective))
	{
		for (const FGameplayTag& T : Chain->Objectives[CurObjective].CompletionStateTags)
		{
			if (!LBPie::HasState(T))
			{
				return T;
			}
		}
	}
	return FGameplayTag();
}

bool FLBRouteBot::IsFailed(const AActor* Actor, const FGameplayTag& InTag) const
{
	return FailedProviders.Contains(FString::Printf(TEXT("%s|%s"), *GetNameSafe(Actor), *InTag.ToString()));
}

// ---- planning --------------------------------------------------------------------------------------------------------

bool FLBRouteBot::Resolve(const FGameplayTag& Need, int32 Depth, TArray<FGameplayTag>& Stack, FAction& Out) const
{
	if (Depth > 8 || Stack.Contains(Need))
	{
		return false;
	}
	Stack.Add(Need);
	const bool bFound = ResolveInteractable(Need, Depth, Stack, Out) || ResolveTrigger(Need, Out) || ResolveDoor(Need, Depth, Stack, Out);
	Stack.Pop();
	return bFound;
}

bool FLBRouteBot::ResolveInteractable(const FGameplayTag& Need, int32 Depth, TArray<FGameplayTag>& Stack, FAction& Out) const
{
	for (TActorIterator<AActor> It(LBPie::World()); It; ++It)
	{
		AActor* Actor = *It;
		TInlineComponentArray<ULBInteractableComponent*> Comps(Actor);
		for (const ULBInteractableComponent* Comp : Comps)
		{
			if (!Comp->GrantedStateTags.HasTagExact(Need) || !Comp->bEnabled || IsFailed(Actor, Need))
			{
				continue;
			}
			if (Comp->ConsumedStateTag.IsValid() && LBPie::HasState(Comp->ConsumedStateTag))
			{
				continue;
			}
			FGameplayTag Missing;
			for (const FGameplayTag& R : Comp->RequiredStateTags)
			{
				if (!LBPie::HasState(R))
				{
					Missing = R;
					break;
				}
			}
			if (!Missing.IsValid())
			{
				Out = FAction{ Actor, EKind::Interactable, Need, false };
				return true;
			}
			if (Resolve(Missing, Depth + 1, Stack, Out))
			{
				return true;
			}
		}
	}
	return false;
}

bool FLBRouteBot::ResolveTrigger(const FGameplayTag& Need, FAction& Out) const
{
	for (TActorIterator<AActor> It(LBPie::World()); It; ++It)
	{
		FGameplayTagContainer Granted;
		if (It->GetClass()->GetName().Contains(TEXT("TagTrigger")) && ReadTagContainer(*It, TEXT("GrantedStateTags"), Granted)
			&& Granted.HasTagExact(Need) && !IsFailed(*It, Need))
		{
			Out = FAction{ *It, EKind::Trigger, Need, false };
			return true;
		}
	}
	return false;
}

bool FLBRouteBot::ResolveDoor(const FGameplayTag& Need, int32 Depth, TArray<FGameplayTag>& Stack, FAction& Out) const
{
	for (TActorIterator<AActor> It(LBPie::World()); It; ++It)
	{
		FGameplayTag Open, Auto;
		if (!It->GetClass()->GetName().Contains(TEXT("Door")) || !ReadTag(*It, TEXT("OpenStateTag"), Open) || Open != Need
			|| !ReadTag(*It, TEXT("AutoOpenTag"), Auto) || !Auto.IsValid())
		{
			continue;
		}
		if (LBPie::HasState(Auto))
		{
			Out = FAction{ *It, EKind::Door, Need, true };
			return true;
		}
		if (Resolve(Auto, Depth + 1, Stack, Out))
		{
			return true;
		}
	}
	return false;
}

// ---- execution -------------------------------------------------------------------------------------------------------

FLBRouteBot::EStatus FLBRouteBot::TickPlan()
{
	const int32 Idx = LBPie::ObjIndex();
	if (Idx == INDEX_NONE || (Config.StopAtIndex.IsSet() && Idx == Config.StopAtIndex.GetValue()))
	{
		UE_LOG(LogLB, Display, TEXT("[RouteBot] done at objective index %d"), Idx);
		return EStatus::Done;
	}
	const double Now = FPlatformTime::Seconds();
	if (Idx != CurObjective)
	{
		CurObjective = Idx;
		ObjectiveStart = Now;
		FailedProviders.Reset();
	}
	if (Now - ObjectiveStart > Config.ObjectiveTimeout)
	{
		return Fail(FString::Printf(TEXT("objective %d \"%s\" not completed within %.0fs"), CurObjective, *ObjectiveText(), Config.ObjectiveTimeout));
	}

	const FGameplayTag Missing = FirstMissingTag();
	if (!Missing.IsValid())
	{
		// Index not advanced yet although all tags are present: give the subsystem a few frames.
		if (++PlanWaitFrames > 120)
		{
			return Fail(FString::Printf(TEXT("objective %d \"%s\": all tags present but the objective did not advance"), CurObjective, *ObjectiveText()));
		}
		return EStatus::Running;
	}
	PlanWaitFrames = 0;

	TArray<FGameplayTag> Stack;
	if (!Resolve(Missing, 0, Stack, Action))
	{
		return Fail(FString::Printf(TEXT("SOFT LOCK: objective %d \"%s\": no (remaining) provider for tag %s"),
			CurObjective, *ObjectiveText(), *Missing.ToString()));
	}
	Phase = EPhase::Act;
	ActionStart = FPlatformTime::Seconds();
	Attempt = -1;
	AttemptFrames = 0;
	FiredCount = 0;
	FVector Origin, Extent;
	Action.Actor->GetActorBounds(true, Origin, Extent);
	ActionLocation = Origin;
	return EStatus::Running;
}

FString FLBRouteBot::ActionLabel() const
{
	const TCHAR* Kind = Action.Kind == EKind::Interactable ? TEXT("interactable") : Action.Kind == EKind::Trigger ? TEXT("trigger") : TEXT("door-auto");
	return FString::Printf(TEXT("%s (%s) at %s"), *Label(Action.Actor.Get()), Kind, *ActionLocation.ToString());
}

void FLBRouteBot::FinishAction(bool bOk)
{
	UE_LOG(LogLB, Display, TEXT("[RouteBot] objective %d \"%s\": need %s via %s -> %s"),
		CurObjective, *ObjectiveText(), *Action.WaitTag.ToString(), *ActionLabel(), bOk ? TEXT("OK") : TEXT("FAIL"));
	if (bOk)
	{
		QueueCheckpoints(ActionLocation);
		Phase = PendingCheckpoints.Num() ? EPhase::Checkpoints : EPhase::Plan;
		bCheckpointEntered = false;
	}
	else
	{
		FailedProviders.Add(FString::Printf(TEXT("%s|%s"), *GetNameSafe(Action.Actor.Get()), *Action.WaitTag.ToString()));
		Phase = EPhase::Plan;
	}
}

FLBRouteBot::EStatus FLBRouteBot::TickAct()
{
	if (!Action.Actor.IsValid())
	{
		Phase = EPhase::Plan;
		return EStatus::Running;
	}
	if (LBPie::HasState(Action.WaitTag))
	{
		FinishAction(true);
		return EStatus::Running;
	}
	const double Now = FPlatformTime::Seconds();
	if (Now - ActionStart > Config.ActionTimeout)
	{
		FinishAction(false);
		return EStatus::Running;
	}
	if (Action.bPending)
	{
		return EStatus::Running;
	}

	const double PerAttempt = Config.ActionTimeout / 4.0;
	if (Attempt < 0 || (Now - AttemptStart > PerAttempt && Attempt < 3))
	{
		BeginAttempt();
		return EStatus::Running;
	}
	++AttemptFrames;
	if (Action.Kind == EKind::Interactable && (AttemptFrames == 6 || AttemptFrames == 36))
	{
		if (ALBCharacter* P = LBPie::Pawn())
		{
			AimAt(ActionLocation);
			P->GetInteractor()->TryInteract();
			++FiredCount;
		}
	}
	return EStatus::Running;
}

void FLBRouteBot::BeginAttempt()
{
	++Attempt;
	AttemptStart = FPlatformTime::Seconds();
	AttemptFrames = 0;
	const AActor* Target = Action.Actor.Get();
	FVector Loc;
	if (Action.Kind == EKind::Interactable)
	{
		// Skip directions without a floor.
		while (Attempt < 4 && !PlaceForInteractable(Target, Attempt, Loc))
		{
			++Attempt;
		}
		if (Attempt >= 4)
		{
			Attempt = 3;
			return; // nothing usable: the action times out
		}
		LBPie::Teleport(Loc, FRotator::ZeroRotator);
		AimAt(ActionLocation);
	}
	else if (StandPointInBounds(Target, Loc))
	{
		LBPie::Teleport(Loc, FRotator::ZeroRotator);
	}
}

bool FLBRouteBot::FindFloor(const FVector& From, float Depth, float& OutZ) const
{
	FCollisionQueryParams Params(SCENE_QUERY_STAT(LBRouteFloor), false, LBPie::Pawn());
	FHitResult Hit;
	if (LBPie::World()->LineTraceSingleByChannel(Hit, From, From - FVector(0, 0, Depth), ECC_Visibility, Params)
		&& !Hit.bStartPenetrating && Hit.ImpactNormal.Z > 0.6f)
	{
		OutZ = Hit.ImpactPoint.Z;
		return true;
	}
	return false;
}

FVector FLBRouteBot::ReferencePointFor(const FVector& Location) const
{
	FVector Best = Location - FVector(1000, 0, 0);
	float BestDist = TNumericLimits<float>::Max();
	auto Consider = [&](const AActor* A)
	{
		const float D = static_cast<float>(FVector::DistSquared(A->GetActorLocation(), Location));
		if (D < BestDist)
		{
			BestDist = D;
			Best = A->GetActorLocation();
		}
	};
	for (TActorIterator<APlayerStart> It(LBPie::World()); It; ++It) { Consider(*It); }
	for (TActorIterator<ALBCheckpoint> It(LBPie::World()); It; ++It) { Consider(*It); }
	return Best;
}

bool FLBRouteBot::PlaceForInteractable(const AActor* Target, int32 AttemptIndex, FVector& OutPawnLoc) const
{
	FVector Origin, Extent;
	Target->GetActorBounds(true, Origin, Extent);
	const FVector ToRef = (ReferencePointFor(Origin) - Origin).GetSafeNormal2D();

	// Order the four axis directions by how well they face the reference point.
	TArray<FVector> Dirs(GDirs, 4);
	Dirs.Sort([&](const FVector& A, const FVector& B) { return FVector::DotProduct(A, ToRef) > FVector::DotProduct(B, ToRef); });

	const FVector Dir = Dirs[AttemptIndex];
	const double Reach = FMath::Abs(Dir.X) * Extent.X + FMath::Abs(Dir.Y) * Extent.Y + 120.0;
	const FVector Column = Origin + Dir * Reach;
	float FloorZ;
	if (!FindFloor(FVector(Column.X, Column.Y, Origin.Z + 60.0), 4000.f, FloorZ))
	{
		return false;
	}
	const ALBCharacter* P = LBPie::Pawn();
	const float HalfHeight = P ? P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() : 92.f;
	OutPawnLoc = FVector(Column.X, Column.Y, FloorZ + HalfHeight + 2.f);
	return true;
}

bool FLBRouteBot::StandPointInBounds(const AActor* Target, FVector& OutPawnLoc) const
{
	FVector Origin, Extent;
	Target->GetActorBounds(true, Origin, Extent);
	const ALBCharacter* P = LBPie::Pawn();
	const float HalfHeight = P ? P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() : 92.f;
	float FloorZ;
	if (FindFloor(Origin, static_cast<float>(Extent.Z) + 300.f, FloorZ) && FloorZ >= Origin.Z - Extent.Z - 10.0)
	{
		OutPawnLoc = FVector(Origin.X, Origin.Y, FloorZ + HalfHeight);
	}
	else
	{
		OutPawnLoc = FVector(Origin.X, Origin.Y, Origin.Z - Extent.Z + HalfHeight);
	}
	return true;
}

void FLBRouteBot::AimAt(const FVector& Point) const
{
	if (const ALBCharacter* P = LBPie::Pawn())
	{
		const FVector Eye = P->GetActorLocation() + FVector(0, 0, 64.f);
		if (AController* C = P->GetController())
		{
			C->SetControlRotation((Point - Eye).Rotation());
		}
	}
}

void FLBRouteBot::QueueCheckpoints(const FVector& Near)
{
	PendingCheckpoints.Reset();
	const ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(LBPie::World());
	TArray<ALBCheckpoint*> Found;
	for (TActorIterator<ALBCheckpoint> It(LBPie::World()); It; ++It)
	{
		if (Save && !Save->HasReachedCheckpoint(It->CheckpointId) && FVector::Dist(It->GetActorLocation(), Near) <= Config.CheckpointRadius)
		{
			Found.Add(*It);
		}
	}
	Found.Sort([&](const ALBCheckpoint& A, const ALBCheckpoint& B)
	{
		return FVector::DistSquared(A.GetActorLocation(), Near) < FVector::DistSquared(B.GetActorLocation(), Near);
	});
	for (ALBCheckpoint* C : Found)
	{
		PendingCheckpoints.Add(C);
	}
}

FLBRouteBot::EStatus FLBRouteBot::TickCheckpoints()
{
	while (PendingCheckpoints.Num() && !PendingCheckpoints[0].IsValid())
	{
		PendingCheckpoints.RemoveAt(0);
	}
	if (PendingCheckpoints.IsEmpty())
	{
		Phase = EPhase::Plan;
		return EStatus::Running;
	}
	const ALBCheckpoint* CP = PendingCheckpoints[0].Get();
	const ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(LBPie::World());
	const double Now = FPlatformTime::Seconds();
	if (!bCheckpointEntered)
	{
		FVector Loc;
		StandPointInBounds(CP, Loc);
		LBPie::Teleport(Loc, FRotator::ZeroRotator);
		bCheckpointEntered = true;
		CheckpointStart = Now;
		return EStatus::Running;
	}
	const bool bReached = Save && Save->HasReachedCheckpoint(CP->CheckpointId);
	if (bReached || Now - CheckpointStart > 1.5)
	{
		UE_LOG(LogLB, Display, TEXT("[RouteBot] checkpoint %s (%s) at %s -> %s"), *CP->CheckpointId.ToString(), *Label(CP),
			*CP->GetActorLocation().ToString(), bReached ? TEXT("OK") : TEXT("NOT SAVED"));
		PendingCheckpoints.RemoveAt(0);
		bCheckpointEntered = false;
	}
	return EStatus::Running;
}

#endif
