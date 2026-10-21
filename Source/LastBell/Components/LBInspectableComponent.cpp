#include "Components/LBInspectableComponent.h"
#include "GameFramework/Actor.h"

void ULBInspectableComponent::ApplyKeep()
{
	if (AActor* Owner = GetOwner())
	{
		Owner->SetActorHiddenInGame(true);
		Owner->SetActorEnableCollision(false);
	}
}
