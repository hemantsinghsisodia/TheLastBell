#include "Storm/LBStormZone.h"
#include "Storm/LBStormSubsystem.h"
#include "Components/BoxComponent.h"
#include "Engine/World.h"

ALBStormZone::ALBStormZone()
{
	PrimaryActorTick.bCanEverTick = false;

	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
	SetRootComponent(Box);
	Box->SetBoxExtent(FVector(300.0, 300.0, 300.0));
	Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Box->SetGenerateOverlapEvents(false);
	Box->SetCanEverAffectNavigation(false);
	Box->SetHiddenInGame(true);
	Box->ShapeColor = FColor(90, 150, 255);
	SetActorEnableCollision(false);
}

bool ALBStormZone::ContainsPoint(const FVector& WorldPoint) const
{
	const FVector Local = Box->GetComponentQuat().UnrotateVector(WorldPoint - Box->GetComponentLocation());
	const FVector Extent = Box->GetScaledBoxExtent();
	return FMath::Abs(Local.X) <= Extent.X && FMath::Abs(Local.Y) <= Extent.Y && FMath::Abs(Local.Z) <= Extent.Z;
}

void ALBStormZone::BeginPlay()
{
	Super::BeginPlay();
	Exposure = FMath::Clamp(Exposure, 0.f, 1.f);
	if (const UWorld* World = GetWorld())
	{
		if (ULBStormSubsystem* Subsystem = World->GetSubsystem<ULBStormSubsystem>())
		{
			Subsystem->RegisterZone(this);
		}
	}
}

void ALBStormZone::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (const UWorld* World = GetWorld())
	{
		if (ULBStormSubsystem* Subsystem = World->GetSubsystem<ULBStormSubsystem>())
		{
			Subsystem->UnregisterZone(this);
		}
	}
	Super::EndPlay(EndPlayReason);
}
