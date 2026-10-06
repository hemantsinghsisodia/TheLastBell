#include "Save/LBCheckpoint.h"
#include "Save/LBSaveSubsystem.h"
#include "Character/LBCharacter.h"
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

	ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(this);
	if (!Save || Save->HasReachedCheckpoint(CheckpointId) || !CanSaveNow())
	{
		return;
	}

	Save->SaveCheckpoint(CheckpointId, SpawnArrow->GetComponentTransform());
}
