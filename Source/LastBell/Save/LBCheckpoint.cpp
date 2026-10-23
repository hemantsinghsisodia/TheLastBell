#include "Save/LBCheckpoint.h"
#include "Save/LBSaveSubsystem.h"
#include "Character/LBCharacter.h"
#include "AI/LBWardenBrainComponent.h"
#include "AI/LBWardenController.h"
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
	const UWorld* World = GetWorld();
	if (!World)
	{
		return true;
	}
	// The Warden's controllers are found through the world's controller list: no manager actor and no registry to keep in sync.
	for (FConstControllerIterator It = World->GetControllerIterator(); It; ++It)
	{
		const ALBWardenController* WardenController = Cast<ALBWardenController>(It->Get());
		const ULBWardenBrainComponent* Brain = WardenController ? WardenController->GetBrain() : nullptr;
		if (Brain && Brain->IsChasingOrAttacking())
		{
			return false;
		}
	}
	return true;
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
		return;
	}

	if (!CanSaveNow())
	{
		// Refused while the Warden hunts the player (D-019). Try again while the player is still inside, after the chase ends.
		if (!World->GetTimerManager().IsTimerActive(RetryTimer))
		{
			UE_LOG(LogLB, Log, TEXT("Checkpoint '%s' refused: the Warden is chasing. Retrying while the player stays inside."), *CheckpointId.ToString());
			World->GetTimerManager().SetTimer(RetryTimer, this, &ALBCheckpoint::RetryWhileInside, 0.5f, true);
		}
		return;
	}

	World->GetTimerManager().ClearTimer(RetryTimer);
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
	Super::EndPlay(EndPlayReason);
}
