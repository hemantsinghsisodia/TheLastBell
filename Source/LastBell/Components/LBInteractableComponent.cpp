#include "Components/LBInteractableComponent.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "LBLog.h"

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
	return PassesStateRequirements(WorldState ? WorldState->GetStateRef() : FGameplayTagContainer());
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
		FGameplayTagContainer ToAdd = GrantedStateTags;
		if (bSingleUse && ConsumedStateTag.IsValid())
		{
			ToAdd.AddTag(ConsumedStateTag);
		}
		WorldState->AddStates(ToAdd);
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

	if (bSingleUse && !ConsumedStateTag.IsValid())
	{
		UE_LOG(LogLB, Warning, TEXT("Single-use interactable on '%s' has no ConsumedStateTag: single-use state not persisted"), *GetNameSafe(GetOwner()));
	}

	if (ConsumedStateTag.IsValid())
	{
		const ULBWorldStateSubsystem* WorldState = ULBWorldStateSubsystem::Get(this);
		if (WorldState && WorldState->HasState(ConsumedStateTag))
		{
			bEnabled = false;
		}
	}
}
