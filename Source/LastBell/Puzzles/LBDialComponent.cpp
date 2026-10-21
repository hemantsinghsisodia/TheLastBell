#include "Puzzles/LBDialComponent.h"
#include "Puzzles/LBPuzzleLogic.h"
#include "Components/LBInteractableComponent.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "LBLog.h"

void ULBDialComponent::BeginPlay()
{
	Super::BeginPlay();

	if (PositionTags.IsEmpty())
	{
		UE_LOG(LogLB, Warning, TEXT("Dial on '%s' has no PositionTags; inert"), *GetNameSafe(GetOwner()));
		return;
	}

	if (ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(this))
	{
		if (!PositionTags.IsValidIndex(InitialIndex))
		{
			UE_LOG(LogLB, Warning, TEXT("Dial on '%s': InitialIndex %d is out of range; clamped"), *GetNameSafe(GetOwner()), InitialIndex);
		}
		const FLBDialChange Init = FLBDialLogic::PlanInit(PositionTags, InitialIndex, State->GetStateRef());
		if (!Init.Remove.IsEmpty())
		{
			UE_LOG(LogLB, Warning, TEXT("Dial on '%s' had several positions set (corrupt state); keeping index %d"), *GetNameSafe(GetOwner()), Init.NewIndex);
			State->RemoveStates(Init.Remove);
		}
		if (Init.Add.IsValid())
		{
			State->AddState(Init.Add);
		}
	}

	if (AActor* Owner = GetOwner())
	{
		if (ULBInteractableComponent* Interactable = Owner->FindComponentByClass<ULBInteractableComponent>())
		{
			Interactable->OnInteracted.AddUniqueDynamic(this, &ULBDialComponent::HandleInteracted);
			BoundInteractable = Interactable;
		}
	}
}

void ULBDialComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (ULBInteractableComponent* Interactable = BoundInteractable.Get())
	{
		Interactable->OnInteracted.RemoveDynamic(this, &ULBDialComponent::HandleInteracted);
	}
	BoundInteractable.Reset();
	Super::EndPlay(EndPlayReason);
}

void ULBDialComponent::HandleInteracted(AActor* Instigator)
{
	CycleNext();
}

int32 ULBDialComponent::GetCurrentIndex() const
{
	const ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(this);
	return State ? FLBDialLogic::FindCurrentIndex(PositionTags, State->GetStateRef()) : INDEX_NONE;
}

FGameplayTag ULBDialComponent::GetCurrentTag() const
{
	const int32 Index = GetCurrentIndex();
	return PositionTags.IsValidIndex(Index) ? PositionTags[Index] : FGameplayTag();
}

int32 ULBDialComponent::CycleNext()
{
	ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(this);
	if (bLocked || !State || PositionTags.IsEmpty())
	{
		return INDEX_NONE;
	}
	const FLBDialChange Change = FLBDialLogic::PlanCycle(PositionTags, State->GetStateRef());
	if (!Change.Remove.IsEmpty())
	{
		State->RemoveStates(Change.Remove);
	}
	if (Change.Add.IsValid())
	{
		State->AddState(Change.Add);
	}
	OnDialChanged.Broadcast(Change.NewIndex);
	return Change.NewIndex;
}
