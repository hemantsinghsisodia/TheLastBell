#include "Objectives/LBObjectiveSubsystem.h"
#include "Objectives/LBObjectiveChainData.h"
#include "Systems/LBGameMode.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
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

	const ALBGameMode* GameMode = Cast<ALBGameMode>(UGameplayStatics::GetGameMode(&InWorld));
	Chain = GameMode ? GameMode->GetObjectiveChain() : nullptr;
	if (!Chain)
	{
		UE_LOG(LogLB, Log, TEXT("ObjectiveSubsystem inactive: no ObjectiveChain on the game mode"));
		return;
	}

	ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(&InWorld);
	if (!State)
	{
		return;
	}
	WorldState = State;
	State->OnStateChanged.AddDynamic(this, &ULBObjectiveSubsystem::HandleStateChanged);
	State->OnStateReplaced.AddDynamic(this, &ULBObjectiveSubsystem::HandleStateReplaced);
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

	const int32 NewIndex = Chain->FindActiveIndex(State->GetState());
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
