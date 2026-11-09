#include "Audio/LBAudioZone.h"
#include "Audio/LBAudioSubsystem.h"
#include "Components/BoxComponent.h"
#include "Engine/World.h"

ALBAudioZone::ALBAudioZone()
{
	PrimaryActorTick.bCanEverTick = false;

	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
	SetRootComponent(Box);
	Box->SetBoxExtent(FVector(300.0, 300.0, 300.0));
	Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Box->SetGenerateOverlapEvents(false);
	Box->SetCanEverAffectNavigation(false);
	Box->SetHiddenInGame(true);
	Box->ShapeColor = FColor(255, 170, 60);
	SetActorEnableCollision(false);
}

bool ALBAudioZone::ContainsPoint(const FVector& WorldPoint) const
{
	const FVector Local = Box->GetComponentQuat().UnrotateVector(WorldPoint - Box->GetComponentLocation());
	const FVector Extent = Box->GetScaledBoxExtent();
	return FMath::Abs(Local.X) <= Extent.X && FMath::Abs(Local.Y) <= Extent.Y && FMath::Abs(Local.Z) <= Extent.Z;
}

void ALBAudioZone::BeginPlay()
{
	Super::BeginPlay();
	if (const UWorld* World = GetWorld())
	{
		if (ULBAudioSubsystem* Subsystem = World->GetSubsystem<ULBAudioSubsystem>())
		{
			Subsystem->RegisterZone(this);
		}
	}
}

void ALBAudioZone::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (const UWorld* World = GetWorld())
	{
		if (ULBAudioSubsystem* Subsystem = World->GetSubsystem<ULBAudioSubsystem>())
		{
			Subsystem->UnregisterZone(this);
		}
	}
	Super::EndPlay(EndPlayReason);
}
