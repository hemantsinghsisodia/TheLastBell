#include "Components/LBInteractableComponent.h"
#include "Systems/LBWorldStateSubsystem.h"

bool ULBInteractableComponent::PassesStateRequirements(const FGameplayTagContainer& WorldState) const
{
	if (!bEnabled)
	{
		return false;
	}
	if (ConsumedStateTag.IsValid() && WorldState.HasTagExact(ConsumedStateTag))
	{
		return false;
	}
	return WorldState.HasAllExact(RequiredStateTags);
}

bool ULBInteractableComponent::CanInteract_Implementation(AActor* Instigator)
{
	const ULBWorldStateSubsystem* WorldState = ULBWorldStateSubsystem::Get(this);
	return PassesStateRequirements(WorldState ? WorldState->GetState() : FGameplayTagContainer());
}

void ULBInteractableComponent::Interact(AActor* Instigator)
{
	if (!CanInteract(Instigator))
	{
		OnInteractDenied.Broadcast(Instigator);
		return;
	}

	if (ULBWorldStateSubsystem* WorldState = ULBWorldStateSubsystem::Get(this))
	{
		for (const FGameplayTag& Tag : GrantedStateTags)
		{
			WorldState->AddState(Tag);
		}
		if (bSingleUse && ConsumedStateTag.IsValid())
		{
			WorldState->AddState(ConsumedStateTag);
		}
	}
	if (bSingleUse)
	{
		bEnabled = false;
	}
	OnInteracted.Broadcast(Instigator);
}

void ULBInteractableComponent::NotifyFocusBegin()
{
	OnFocusBegin.Broadcast();
}

void ULBInteractableComponent::NotifyFocusEnd()
{
	OnFocusEnd.Broadcast();
}

void ULBInteractableComponent::BeginPlay()
{
	Super::BeginPlay();

	if (ConsumedStateTag.IsValid())
	{
		const ULBWorldStateSubsystem* WorldState = ULBWorldStateSubsystem::Get(this);
		if (WorldState && WorldState->HasState(ConsumedStateTag))
		{
			bEnabled = false;
		}
	}
}
