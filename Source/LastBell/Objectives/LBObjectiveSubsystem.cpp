#include "Objectives/LBObjectiveSubsystem.h"
#include "Objectives/LBObjectiveChainData.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "Engine/World.h"
#include "LBLog.h"

bool ULBObjectiveSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
	if (!Super::ShouldCreateSubsystem(Outer))
	{
		return false;
	}
	const UWorld* World = Cast<UWorld>(Outer);
	return World && (World->WorldType == EWorldType::Game || World->WorldType == EWorldType::PIE);
}

void ULBObjectiveSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	// Chain normally arrives earlier via SetChain (game mode StartPlay); this covers late binding only.
	EnsureBoundToWorldState();
	Recompute();
}

void ULBObjectiveSubsystem::EnsureBoundToWorldState()
{
	if (WorldState.IsValid())
	{
		return;
	}
	if (ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(GetWorld()))
	{
		WorldState = State;
		State->OnStateChanged.AddDynamic(this, &ULBObjectiveSubsystem::HandleStateChanged);
		State->OnStateReplaced.AddDynamic(this, &ULBObjectiveSubsystem::HandleStateReplaced);
	}
}

void ULBObjectiveSubsystem::SetChain(const ULBObjectiveChainData* InChain)
{
	Chain = InChain;
	bHasComputed = false;
	ActiveIndex = INDEX_NONE;
	if (!Chain)
	{
		return;
	}
	EnsureBoundToWorldState();
	Recompute();
}

void ULBObjectiveSubsystem::Deinitialize()
{
	if (ULBWorldStateSubsystem* State = WorldState.Get())
	{
		State->OnStateChanged.RemoveDynamic(this, &ULBObjectiveSubsystem::HandleStateChanged);
		State->OnStateReplaced.RemoveDynamic(this, &ULBObjectiveSubsystem::HandleStateReplaced);
	}
	Super::Deinitialize();
}

FText ULBObjectiveSubsystem::GetActiveObjectiveText() const
{
	if (Chain && Chain->Objectives.IsValidIndex(ActiveIndex))
	{
		return Chain->Objectives[ActiveIndex].Text;
	}
	return FText::GetEmpty();
}

void ULBObjectiveSubsystem::HandleStateChanged(FGameplayTag Tag, bool bAdded)
{
	Recompute();
}

void ULBObjectiveSubsystem::HandleStateReplaced()
{
	Recompute();
}

void ULBObjectiveSubsystem::Recompute()
{
	const ULBWorldStateSubsystem* State = WorldState.Get();
	if (!Chain || !State)
	{
		return;
	}

	const int32 NewIndex = Chain->FindActiveIndex(State->GetStateRef());
	if (bHasComputed && NewIndex == ActiveIndex)
	{
		return;
	}
	// The first compute always broadcasts so listeners get an initial value.
	bHasComputed = true;
	ActiveIndex = NewIndex;
	UE_LOG(LogLB, Log, TEXT("Active objective: %d"), ActiveIndex);
	OnObjectiveChanged.Broadcast(ActiveIndex, GetActiveObjectiveText());
}
