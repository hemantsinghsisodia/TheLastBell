#include "Components/LBInteractableComponent.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "Character/LBInspectionComponent.h"
#include "Components/LBInspectableComponent.h"
#include "AI/LBNoiseTags.h"
#include "Perception/AISense_Hearing.h"
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

	if (bInspectOnInteract)
	{
		ULBInspectableComponent* Inspectable = GetOwner() ? GetOwner()->FindComponentByClass<ULBInspectableComponent>() : nullptr;
		ULBInspectionComponent* Inspection = Instigator ? Instigator->FindComponentByClass<ULBInspectionComponent>() : nullptr;
		if (Inspection && Inspection->IsInspecting())
		{
			// Already inspecting (this item or another): ignore the press instead of falling back to the plain grant.
			return;
		}
		if (Inspectable && Inspection && Inspection->BeginInspect(Inspectable, this))
		{
			return;
		}
		UE_LOG(LogLB, Warning, TEXT("'%s' has bInspectOnInteract but cannot be inspected; running the normal interaction"), *GetNameSafe(GetOwner()));
	}

	ApplyInteraction(Instigator);
}

void ULBInteractableComponent::CompleteInspection(AActor* Instigator)
{
	if (CanInteract(Instigator))
	{
		ApplyInteraction(Instigator);
	}
}

void ULBInteractableComponent::ApplyInteraction(AActor* Instigator)
{
	if (ULBWorldStateSubsystem* WorldState = ULBWorldStateSubsystem::Get(this))
	{
		FGameplayTagContainer ToAdd = GrantedStateTags;
		if (bSingleUse && ConsumedStateTag.IsValid())
		{
			ToAdd.AddTag(ConsumedStateTag);
		}
		WorldState->AddStates(ToAdd);
	}
	// With a ConsumedStateTag, availability is derived from that tag (absent = usable), so a puzzle reset that removes the
	// tag makes this usable again. Without one (or without a world state to hold it) the only way to remember use is bEnabled.
	if (bSingleUse && (!ConsumedStateTag.IsValid() || !ULBWorldStateSubsystem::Get(this)))
	{
		bEnabled = false;
	}
	if (NoiseLoudness > 0.f && GetOwner())
	{
		// The emitting actor is the instigator, so the Warden sees "a door made a noise", not "the player".
		UAISense_Hearing::ReportNoiseEvent(GetWorld(), GetOwner()->GetActorLocation(), NoiseLoudness, GetOwner(), 0.f, LBNoiseTags::Interact);
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
	// A present ConsumedStateTag no longer touches bEnabled: PassesStateRequirements derives availability from the tag.
}
