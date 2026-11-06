#include "AI/LBWardenStoopZone.h"
#include "AI/LBWardenAnim.h"
#include "AI/LBWardenStoopSubsystem.h"
#include "Components/BoxComponent.h"
#include "Engine/World.h"

ALBWardenStoopZone::ALBWardenStoopZone()
{
	PrimaryActorTick.bCanEverTick = false;

	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
	SetRootComponent(Box);
	Box->SetBoxExtent(FVector(150.0, 62.0, 150.0));
	Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Box->SetGenerateOverlapEvents(false);
	Box->SetCanEverAffectNavigation(false);
	Box->SetHiddenInGame(true);
	Box->ShapeColor = FColor(255, 160, 40);
	SetActorEnableCollision(false);
}

FLBStoopBox ALBWardenStoopZone::ToStoopBox() const
{
	FLBStoopBox Out;
	Out.Center = Box->GetComponentLocation();
	Out.Rotation = Box->GetComponentQuat();
	Out.HalfExtent = Box->GetScaledBoxExtent();
	Out.Amount = StoopAmount;
	return Out;
}

void ALBWardenStoopZone::BeginPlay()
{
	Super::BeginPlay();
	if (UWorld* World = GetWorld())
	{
		if (ULBWardenStoopSubsystem* Subsystem = World->GetSubsystem<ULBWardenStoopSubsystem>())
		{
			Subsystem->RegisterZone(this);
		}
	}
}

void ALBWardenStoopZone::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (UWorld* World = GetWorld())
	{
		if (ULBWardenStoopSubsystem* Subsystem = World->GetSubsystem<ULBWardenStoopSubsystem>())
		{
			Subsystem->UnregisterZone(this);
		}
	}
	Super::EndPlay(EndPlayReason);
}
