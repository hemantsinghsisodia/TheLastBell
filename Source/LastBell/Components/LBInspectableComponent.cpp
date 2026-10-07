#include "Components/LBInspectableComponent.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "GameFramework/Actor.h"

void ULBInspectableComponent::ApplyKeep()
{
	if (!GrantOnKeep.IsEmpty())
	{
		if (ULBWorldStateSubsystem* WorldState = ULBWorldStateSubsystem::Get(this))
		{
			WorldState->AddStates(GrantOnKeep);
		}
	}
	if (AActor* Owner = GetOwner())
	{
		Owner->SetActorHiddenInGame(true);
		Owner->SetActorEnableCollision(false);
	}
}
