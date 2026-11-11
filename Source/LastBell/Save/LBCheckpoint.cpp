#include "Save/LBCheckpoint.h"
#include "Save/LBSaveSubsystem.h"
#include "Character/LBCharacter.h"
#include "AI/LBWardenBrainComponent.h"
#include "AI/LBWardenController.h"
#include "Cinematics/LBCinematicSubsystem.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "TimerManager.h"
#include "Components/BoxComponent.h"
#include "Components/ArrowComponent.h"
#include "LBLog.h"

ALBCheckpoint::ALBCheckpoint()
{
	PrimaryActorTick.bCanEverTick = false;

	Trigger = CreateDefaultSubobject<UBoxComponent>(TEXT("Trigger"));
	SetRootComponent(Trigger);
	Trigger->SetBoxExtent(FVector(100.f, 100.f, 100.f));
	Trigger->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Trigger->SetCollisionObjectType(ECC_WorldStatic);
	Trigger->SetCollisionResponseToAllChannels(ECR_Ignore);
	Trigger->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
	Trigger->SetGenerateOverlapEvents(true);

	SpawnArrow = CreateDefaultSubobject<UArrowComponent>(TEXT("SpawnArrow"));
	SpawnArrow->SetupAttachment(Trigger);
	SpawnArrow->SetRelativeLocation(FVector(0.f, 0.f, 0.f));
}

void ALBCheckpoint::PostInitializeComponents()
{
	Super::PostInitializeComponents();
	Trigger->OnComponentBeginOverlap.AddDynamic(this, &ALBCheckpoint::OnTriggerBeginOverlap);
}

void ALBCheckpoint::OnTriggerBeginOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
	int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	const ALBCharacter* Character = Cast<ALBCharacter>(OtherActor);
	if (!Character || !Character->IsPlayerControlled())
	{
		return;
	}

	if (CheckpointId.IsNone())
	{
		UE_LOG(LogLB, Error, TEXT("Checkpoint '%s' has no CheckpointId"), *GetName());
		return;
	}

	TrySave(Character);
}

bool ALBCheckpoint::CanSaveNow() const
{
	return GetSaveRefusalReason() == nullptr;
}

const TCHAR* ALBCheckpoint::GetSaveRefusalReason() const
{
	const UWorld* World = GetWorld();
	if (!World)
	{
		return nullptr;
	}
	// The Warden's controllers are found through the world's controller list: no manager actor and no registry to keep in sync.
	for (FConstControllerIterator It = World->GetControllerIterator(); It; ++It)
	{
		const ALBWardenController* WardenController = Cast<ALBWardenController>(It->Get());
		const ULBWardenBrainComponent* Brain = WardenController ? WardenController->GetBrain() : nullptr;
		if (Brain && Brain->IsChasingOrAttacking())
		{
			return TEXT("the Warden is chasing");
		}
	}
	// P17: nothing is saved while a cinematic plays. The intro hands the controls back at 27.5 s but the run lasts until 29.0 s, so a
	// player walking through CP_Approach in that window is refused here; the checkpoint then saves when the cinematic finishes
	// (WaitForCinematicEnd / HandleCinematicFinished), with Arrival already set, even though the player has left the trigger.
	if (IsCinematicPlaying())
	{
		return TEXT("a cinematic is playing");
	}
	return nullptr;
}

bool ALBCheckpoint::IsCinematicPlaying() const
{
	const UWorld* World = GetWorld();
	const ULBCinematicSubsystem* Cinematics = World ? World->GetSubsystem<ULBCinematicSubsystem>() : nullptr;
	return Cinematics && Cinematics->IsPlaying();
}

void ALBCheckpoint::WaitForCinematicEnd()
{
	if (CinematicFinishedHandle.IsValid())
	{
		return;
	}
	const UWorld* World = GetWorld();
	ULBCinematicSubsystem* Cinematics = World ? World->GetSubsystem<ULBCinematicSubsystem>() : nullptr;
	if (!Cinematics)
	{
		return;
	}
	CinematicSubsystem = Cinematics;
	CinematicFinishedHandle = Cinematics->OnCinematicFinished.AddUObject(this, &ALBCheckpoint::HandleCinematicFinished);
	UE_LOG(LogLB, Log, TEXT("Checkpoint '%s' will try again when the cinematic finishes."), *CheckpointId.ToString());
}

void ALBCheckpoint::StopWaitingForCinematicEnd()
{
	if (!CinematicFinishedHandle.IsValid())
	{
		return;
	}
	if (ULBCinematicSubsystem* Cinematics = CinematicSubsystem.Get())
	{
		Cinematics->OnCinematicFinished.Remove(CinematicFinishedHandle);
	}
	CinematicFinishedHandle.Reset();
	CinematicSubsystem.Reset();
}

void ALBCheckpoint::HandleCinematicFinished(FName CinematicId)
{
	// One shot: unbind first (removing during the broadcast is safe) so nothing below can leave it bound.
	StopWaitingForCinematicEnd();

	const UWorld* World = GetWorld();
	const APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	const ALBCharacter* Player = PC ? Cast<ALBCharacter>(PC->GetPawn()) : nullptr;
	if (!Player || CheckpointId.IsNone())
	{
		return;
	}
	UE_LOG(LogLB, Log, TEXT("Checkpoint '%s': cinematic '%s' finished, trying to save."), *CheckpointId.ToString(), *CinematicId.ToString());
	// TrySave does the rest: it skips a pending travel (CompleteGame), a checkpoint that already saved and a dead player, and it asks
	// CanSaveNow again for the other reasons (the Warden chasing). If it is refused once more, the existing retry timer takes over
	// (it only keeps going while the player is inside the trigger).
	TrySave(Player);
}

void ALBCheckpoint::TrySave(const ALBCharacter* Character)
{
	UWorld* World = GetWorld();
	ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(this);
	if (!World || Character->IsDead() || !Save || Save->IsTravelPending() || Save->HasReachedCheckpoint(CheckpointId))
	{
		if (World)
		{
			World->GetTimerManager().ClearTimer(RetryTimer);
		}
		StopWaitingForCinematicEnd();
		return;
	}

	// CanSaveNow is virtual (a test double may override it), so ask it first; the reason only words the log.
	if (!CanSaveNow())
	{
		// Refused while the Warden hunts the player (D-019) or a cinematic plays. Try again while the player is still inside.
		// A cinematic refusal is also remembered: the checkpoint saves once when the cinematic finishes, even if the player left.
		if (IsCinematicPlaying())
		{
			WaitForCinematicEnd();
		}
		if (!World->GetTimerManager().IsTimerActive(RetryTimer))
		{
			const TCHAR* Reason = GetSaveRefusalReason();
			UE_LOG(LogLB, Log, TEXT("Checkpoint '%s' refused (%s). Retrying while the player stays inside."), *CheckpointId.ToString(), Reason ? Reason : TEXT("not allowed now"));
			World->GetTimerManager().SetTimer(RetryTimer, this, &ALBCheckpoint::RetryWhileInside, 0.5f, true);
		}
		return;
	}

	World->GetTimerManager().ClearTimer(RetryTimer);
	StopWaitingForCinematicEnd();
	Save->SaveCheckpoint(CheckpointId, SpawnArrow->GetComponentTransform());
}

void ALBCheckpoint::RetryWhileInside()
{
	const UWorld* World = GetWorld();
	const APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	const ALBCharacter* Player = PC ? Cast<ALBCharacter>(PC->GetPawn()) : nullptr;
	if (!Player || !Trigger->IsOverlappingActor(Player))
	{
		GetWorldTimerManager().ClearTimer(RetryTimer);
		return;
	}
	TrySave(Player);
}

void ALBCheckpoint::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	GetWorldTimerManager().ClearTimer(RetryTimer);
	StopWaitingForCinematicEnd();
	Super::EndPlay(EndPlayReason);
}
