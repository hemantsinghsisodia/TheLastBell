#include "Tests/LBRouteBot.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Editor.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerStart.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Kismet/GameplayStatics.h"
#include "AI/LBWardenBrainComponent.h"
#include "Character/LBCharacter.h"
#include "Components/LBInteractorComponent.h"
#include "Components/LBInteractableComponent.h"
#include "Objectives/LBObjectiveChainData.h"
#include "Objectives/LBObjectiveSubsystem.h"
#include "Puzzles/LBDialComponent.h"
#include "Puzzles/LBPuzzleLogic.h"
#include "Puzzles/LBSequencePuzzleComponent.h"
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

	FWardenSwitch::FWardenSwitch(bool bEnabled)
		: bPrevious(ULBWardenBrainComponent::IsWardenSystemEnabled())
	{
		ULBWardenBrainComponent::SetWardenSystemEnabled(bEnabled);
	}

	FWardenSwitch::~FWardenSwitch()
	{
		ULBWardenBrainComponent::SetWardenSystemEnabled(bPrevious);
	}
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
	CheckpointWaitStart = 0.0;
	bCheckpointEntered = false;
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
	if (!Config.GoalTags.IsEmpty())
	{
		return TEXT("goal tags");
	}
	const ULBObjectiveChainData* Chain = ActiveChain();
	return (Chain && Chain->Objectives.IsValidIndex(CurObjective)) ? Chain->Objectives[CurObjective].Text.ToString() : FString();
}

FGameplayTag FLBRouteBot::FirstMissingTag() const
{
	for (const FGameplayTag& Goal : Config.GoalTags)
	{
		if (!LBPie::HasState(Goal))
		{
			return Goal;
		}
	}
	if (!Config.GoalTags.IsEmpty())
	{
		return FGameplayTag();
	}
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
	const bool bFound = ResolveInteractable(Need, Depth, Stack, Out) || ResolveTrigger(Need, Out) || ResolveDoor(Need, Depth, Stack, Out)
		|| ResolveSequence(Need, Depth, Stack, Out) || ResolveDial(Need, Depth, Stack, Out);
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

bool FLBRouteBot::ResolveSequence(const FGameplayTag& Need, int32 Depth, TArray<FGameplayTag>& Stack, FAction& Out) const
{
	for (TActorIterator<AActor> It(LBPie::World()); It; ++It)
	{
		TInlineComponentArray<ULBSequencePuzzleComponent*> Comps(*It);
		for (const ULBSequencePuzzleComponent* Comp : Comps)
		{
			if (!Comp->SolvedTags.HasTagExact(Need) || Comp->IsSolved() || !FLBSequenceLogic::IsConfigValid(Comp->Steps))
			{
				continue;
			}
			// The next step is the first one not present, re-derived from the live state on every plan. If a wrong step ever resets the
			// puzzle, the next plan simply starts over from step 0, so no extra "re-plan" state is needed.
			const ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(LBPie::World());
			const FLBSequenceLogic::FEval Eval = FLBSequenceLogic::Evaluate(Comp->Steps, State ? State->GetStateRef() : FGameplayTagContainer());
			if (Eval.Progress >= Comp->Steps.Num())
			{
				continue;
			}
			if (Resolve(Comp->Steps[Eval.Progress], Depth + 1, Stack, Out))
			{
				if (Out.WaitTag == Comp->Steps[Eval.Progress])
				{
					Out.Sequence = Comp; // the step provider itself (not a prerequisite of it): watch the puzzle while acting
					Out.StepIndex = Eval.Progress;
				}
				return true;
			}
		}
	}
	return false;
}

bool FLBRouteBot::ResolveDial(const FGameplayTag& Need, int32 Depth, TArray<FGameplayTag>& Stack, FAction& Out) const
{
	for (TActorIterator<AActor> It(LBPie::World()); It; ++It)
	{
		AActor* Actor = *It;
		TInlineComponentArray<ULBDialComponent*> Comps(Actor);
		for (ULBDialComponent* Dial : Comps)
		{
			if (!Dial->PositionTags.Contains(Need) || Dial->bLocked || IsFailed(Actor, Need))
			{
				continue;
			}
			// The dial is cycled through its interactable, so that interactable's own requirements apply.
			FGameplayTag Missing;
			if (const ULBInteractableComponent* Interactable = Actor->FindComponentByClass<ULBInteractableComponent>())
			{
				if (!Interactable->bEnabled)
				{
					continue;
				}
				for (const FGameplayTag& R : Interactable->RequiredStateTags)
				{
					if (!LBPie::HasState(R))
					{
						Missing = R;
						break;
					}
				}
			}
			if (!Missing.IsValid())
			{
				Out = FAction{ Actor, EKind::Dial, Need, false, Dial };
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

// ---- execution -------------------------------------------------------------------------------------------------------

FLBRouteBot::EStatus FLBRouteBot::TickPlan()
{
	int32 Idx = LBPie::ObjIndex();
	if (!Config.GoalTags.IsEmpty())
	{
		Idx = FirstMissingTag().IsValid() ? 0 : INDEX_NONE;
	}
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
	DialPresses = 0;
	FVector Origin, Extent;
	Action.Actor->GetActorBounds(true, Origin, Extent);
	ActionLocation = Origin;
	return EStatus::Running;
}

FString FLBRouteBot::ActionLabel() const
{
	const TCHAR* Kind = Action.Kind == EKind::Interactable ? TEXT("interactable") : Action.Kind == EKind::Trigger ? TEXT("trigger")
		: Action.Kind == EKind::Dial ? TEXT("dial") : TEXT("door-auto");
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
	if (const ULBSequencePuzzleComponent* Sequence = Action.Sequence.Get())
	{
		// A sequence step is only valid while the puzzle is exactly at that step. If it reset (a wrong step, or the bot was moved
		// by a load) or moved on, drop this action and re-plan from the live state. This is not a provider failure.
		const ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(LBPie::World());
		const FLBSequenceLogic::FEval Eval = FLBSequenceLogic::Evaluate(Sequence->Steps, State ? State->GetStateRef() : FGameplayTagContainer());
		const bool bStepDone = Eval.bValidPrefix && Eval.Progress == Action.StepIndex + 1;
		if (!bStepDone && (!Eval.bValidPrefix || Eval.Progress != Action.StepIndex))
		{
			UE_LOG(LogLB, Display, TEXT("[RouteBot] sequence puzzle on %s changed (progress %d, expected step %d): re-planning"),
				*Label(Sequence->GetOwner()), Eval.Progress, Action.StepIndex);
			Phase = EPhase::Plan;
			return EStatus::Running;
		}
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
	else if (Action.Kind == EKind::Dial && AttemptFrames >= 6 && AttemptFrames % 6 == 0)
	{
		TickDial();
	}
	return EStatus::Running;
}

void FLBRouteBot::TickDial()
{
	ULBDialComponent* Dial = Action.Dial.Get();
	ALBCharacter* P = LBPie::Pawn();
	if (!Dial || !P)
	{
		return;
	}
	const int32 Target = Dial->PositionTags.Find(Action.WaitTag);
	const int32 Before = Dial->GetCurrentIndex();
	if (Before == Target)
	{
		return; // the tag is present: TickAct finishes the action next frame
	}
	if (DialPresses > Dial->PositionTags.Num())
	{
		return; // more effective presses than positions without arriving: let the action time out and report it
	}
	AimAt(ActionLocation);
	P->GetInteractor()->TryInteract();
	++FiredCount;
	if (Dial->GetCurrentIndex() != Before)
	{
		++DialPresses;
	}
}

void FLBRouteBot::BeginAttempt()
{
	++Attempt;
	AttemptStart = FPlatformTime::Seconds();
	AttemptFrames = 0;
	const AActor* Target = Action.Actor.Get();
	FVector Loc;
	if (Action.Kind == EKind::Interactable || Action.Kind == EKind::Dial)
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

bool FLBRouteBot::IsClearLine(const FVector& From, const FVector& To, const AActor* IgnoreActor) const
{
	FCollisionQueryParams Params(SCENE_QUERY_STAT(LBRouteLOS), false, LBPie::Pawn());
	Params.AddIgnoredActor(IgnoreActor);
	FHitResult Hit;
	return !LBPie::World()->LineTraceSingleByChannel(Hit, From, To, ECC_Visibility, Params);
}

bool FLBRouteBot::IsApproachValid(const AActor* Target, const FVector& PawnLoc, const FVector& TargetCentre, FString& OutReason) const
{
	const ALBCharacter* P = LBPie::Pawn();
	const UCapsuleComponent* Capsule = P ? P->GetCapsuleComponent() : nullptr;
	const float Radius = Capsule ? Capsule->GetScaledCapsuleRadius() : 34.f;
	const float HalfHeight = Capsule ? Capsule->GetScaledCapsuleHalfHeight() : 92.f;
	// A slightly shrunk capsule so resting on the floor (2cm above it) or grazing a wall isn't an "overlap".
	const FCollisionShape Shape = FCollisionShape::MakeCapsule(FMath::Max(Radius - 2.f, 1.f), FMath::Max(HalfHeight - 4.f, 1.f));

	// (c) not inside static geometry.
	FCollisionQueryParams Params(SCENE_QUERY_STAT(LBRouteApproach), false, P);
	Params.AddIgnoredActor(Target);
	if (LBPie::World()->OverlapAnyTestByObjectType(PawnLoc, FQuat::Identity, FCollisionObjectQueryParams(ECC_WorldStatic), Shape, Params))
	{
		OutReason = TEXT("capsule overlaps static geometry");
		return false;
	}

	// (b) not inside a checkpoint volume the player hasn't reached yet (the bot would "save" a place the player can't be in yet).
	const ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(LBPie::World());
	for (TActorIterator<ALBCheckpoint> It(LBPie::World()); It; ++It)
	{
		if (Save && Save->HasReachedCheckpoint(It->CheckpointId))
		{
			continue;
		}
		TInlineComponentArray<UBoxComponent*> Boxes(*It);
		for (const UBoxComponent* Box : Boxes)
		{
			if (Box->OverlapComponent(PawnLoc, FQuat::Identity, Shape))
			{
				OutReason = FString::Printf(TEXT("inside unreached checkpoint volume %s (%s)"), *It->CheckpointId.ToString(), *Label(*It));
				return false;
			}
		}
	}

	// (a) line of sight from the eye to the target: no shooting through walls.
	const FVector Eye = PawnLoc + FVector(0, 0, 64.f);
	FCollisionQueryParams LosParams(SCENE_QUERY_STAT(LBRouteLOS), false, P);
	LosParams.AddIgnoredActor(Target);
	FHitResult Hit;
	if (LBPie::World()->LineTraceSingleByChannel(Hit, Eye, TargetCentre, ECC_Visibility, LosParams))
	{
		OutReason = FString::Printf(TEXT("view of target blocked by %s"), *Label(Hit.GetActor()));
		return false;
	}
	return true;
}

bool FLBRouteBot::PlaceForInteractable(const AActor* Target, int32 AttemptIndex, FVector& OutPawnLoc) const
{
	FVector Origin, Extent;
	Target->GetActorBounds(true, Origin, Extent);
	const FVector ToRef = (ReferencePointFor(Origin) - Origin).GetSafeNormal2D();

	// Approach order: the target's own facing first (props face +X by convention, so a wall bell or lever is meant to be used from
	// in front), then each side (the one nearer the nearest spawn/checkpoint first), the back last. Which side is "nearer a
	// checkpoint" is only a tie-break: the reachability checks below decide whether a side is actually usable.
	TArray<FVector> Dirs;
	const FVector Forward = Target->GetActorForwardVector().GetSafeNormal2D();
	const bool bHasFacing = !Forward.IsNearlyZero();
	if (!bHasFacing)
	{
		Dirs.Append(GDirs, 4);
		Dirs.Sort([&](const FVector& A, const FVector& B) { return FVector::DotProduct(A, ToRef) > FVector::DotProduct(B, ToRef); });
	}
	else
	{
		const FVector Right(-Forward.Y, Forward.X, 0.0);
		const bool bRightFirst = FVector::DotProduct(Right, ToRef) >= FVector::DotProduct(-Right, ToRef);
		Dirs.Add(Forward);
		Dirs.Add(bRightFirst ? Right : -Right);
		Dirs.Add(bRightFirst ? -Right : Right);
		Dirs.Add(-Forward);
	}

	static const TCHAR* DirNames[4] = { TEXT("front"), TEXT("side 1"), TEXT("side 2"), TEXT("back") };
	const FVector Dir = Dirs[AttemptIndex];
	const TCHAR* DirName = bHasFacing ? DirNames[AttemptIndex] : TEXT("axis");
	const double Reach = FMath::Abs(Dir.X) * Extent.X + FMath::Abs(Dir.Y) * Extent.Y + 120.0;
	const FVector Column = Origin + Dir * Reach;
	float FloorZ;
	if (!FindFloor(FVector(Column.X, Column.Y, Origin.Z + 60.0), 4000.f, FloorZ))
	{
		UE_LOG(LogLB, Verbose, TEXT("[RouteBot] approach to %s from %s (%s) rejected: no floor"), *Label(Target), DirName, *Dir.ToCompactString());
		return false;
	}
	const ALBCharacter* P = LBPie::Pawn();
	const float HalfHeight = P ? P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() : 92.f;
	const FVector Loc(Column.X, Column.Y, FloorZ + HalfHeight + 2.f);
	FString Reason;
	if (!IsApproachValid(Target, Loc, Origin, Reason))
	{
		UE_LOG(LogLB, Verbose, TEXT("[RouteBot] approach to %s from %s (%s) at %s rejected: %s"), *Label(Target), DirName, *Dir.ToCompactString(), *Loc.ToString(), *Reason);
		return false;
	}
	UE_LOG(LogLB, Verbose, TEXT("[RouteBot] approach to %s from %s (%s) at %s accepted"), *Label(Target), DirName, *Dir.ToCompactString(), *Loc.ToString());
	OutPawnLoc = Loc;
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
		// Only step on a checkpoint the player could walk to from where the bot is now: a clear line from the pawn to the volume
		// (open doorway, same room). Otherwise the bot would teleport through a wall into a place that is still sealed, and save
		// the checkpoint early. A line that is blocked right after an action may just be a door still swinging open, so wait a short
		// while before giving up. Skipped checkpoints are re-queued after the next completed action, when the route has moved on.
		FVector CPOrigin, CPExtent;
		CP->GetActorBounds(true, CPOrigin, CPExtent);
		const ALBCharacter* P = LBPie::Pawn();
		if (P && !IsClearLine(P->GetActorLocation() + FVector(0, 0, 64.f), CPOrigin, CP))
		{
			if (CheckpointWaitStart <= 0.0)
			{
				CheckpointWaitStart = Now;
			}
			if (Now - CheckpointWaitStart < ReachWaitSeconds)
			{
				return EStatus::Running;
			}
			UE_LOG(LogLB, Verbose, TEXT("[RouteBot] checkpoint %s (%s) skipped: no clear line from the pawn at %s for %.1fs"), *CP->CheckpointId.ToString(),
				*Label(CP), *P->GetActorLocation().ToString(), ReachWaitSeconds);
			PendingCheckpoints.RemoveAt(0);
			CheckpointWaitStart = 0.0;
			return EStatus::Running;
		}
		CheckpointWaitStart = 0.0;
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
