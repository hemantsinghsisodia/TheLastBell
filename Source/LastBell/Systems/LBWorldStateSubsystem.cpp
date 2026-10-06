#include "Systems/LBWorldStateSubsystem.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "LBLog.h"

ULBWorldStateSubsystem* ULBWorldStateSubsystem::Get(const UObject* WorldContextObject)
{
	const UWorld* World = WorldContextObject ? WorldContextObject->GetWorld() : nullptr;
	UGameInstance* GameInstance = World ? World->GetGameInstance() : nullptr;
	return GameInstance ? GameInstance->GetSubsystem<ULBWorldStateSubsystem>() : nullptr;
}

void ULBWorldStateSubsystem::AddState(FGameplayTag Tag)
{
	if (WorldState.Add(Tag))
	{
		UE_LOG(LogLB, Verbose, TEXT("State added: %s"), *Tag.ToString());
		OnStateChanged.Broadcast(Tag, true);
	}
}

void ULBWorldStateSubsystem::AddStates(const FGameplayTagContainer& Tags)
{
	TArray<FGameplayTag> Added;
	for (const FGameplayTag& Tag : Tags)
	{
		if (WorldState.Add(Tag))
		{
			Added.Add(Tag);
		}
	}
	for (const FGameplayTag& Tag : Added)
	{
		UE_LOG(LogLB, Verbose, TEXT("State added: %s"), *Tag.ToString());
		OnStateChanged.Broadcast(Tag, true);
	}
}

void ULBWorldStateSubsystem::RemoveState(FGameplayTag Tag)
{
	if (WorldState.Remove(Tag))
	{
		UE_LOG(LogLB, Verbose, TEXT("State removed: %s"), *Tag.ToString());
		OnStateChanged.Broadcast(Tag, false);
	}
}

bool ULBWorldStateSubsystem::HasState(FGameplayTag Tag) const
{
	return WorldState.Has(Tag);
}

bool ULBWorldStateSubsystem::HasAllStates(const FGameplayTagContainer& Tags) const
{
	return WorldState.HasAll(Tags);
}

FGameplayTagContainer ULBWorldStateSubsystem::GetState() const
{
	return WorldState.GetTags();
}

void ULBWorldStateSubsystem::ResetState()
{
	WorldState.Reset();
	UE_LOG(LogLB, Log, TEXT("World state reset"));
	OnStateReplaced.Broadcast();
}

void ULBWorldStateSubsystem::ReplaceState(const FGameplayTagContainer& NewState)
{
	WorldState.Replace(NewState);
	UE_LOG(LogLB, Log, TEXT("World state replaced (%d tags)"), NewState.Num());
	OnStateReplaced.Broadcast();
}
