#pragma once

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Systems/LBWorldState.h"
#include "LBWorldStateSubsystem.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FLBStateChangedSignature, FGameplayTag, Tag, bool, bAdded);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FLBStateReplacedSignature);

/** Canonical owner of all State.* progress tags. */
UCLASS()
class LASTBELL_API ULBWorldStateSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	/** Convenience lookup from any world-context object; null if there is no game instance. */
	static ULBWorldStateSubsystem* Get(const UObject* WorldContextObject);

	UFUNCTION(BlueprintCallable, Category = "LastBell|WorldState")
	void AddState(FGameplayTag Tag);

	UFUNCTION(BlueprintCallable, Category = "LastBell|WorldState")
	void RemoveState(FGameplayTag Tag);

	UFUNCTION(BlueprintPure, Category = "LastBell|WorldState")
	bool HasState(FGameplayTag Tag) const;

	UFUNCTION(BlueprintPure, Category = "LastBell|WorldState")
	bool HasAllStates(const FGameplayTagContainer& Tags) const;

	UFUNCTION(BlueprintPure, Category = "LastBell|WorldState")
	FGameplayTagContainer GetState() const;

	/** Bulk op: no per-tag events, one OnStateReplaced afterwards. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|WorldState")
	void ResetState();

	/** Bulk op: no per-tag events, one OnStateReplaced afterwards. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|WorldState")
	void ReplaceState(const FGameplayTagContainer& NewState);

	UPROPERTY(BlueprintAssignable, Category = "LastBell|WorldState")
	FLBStateChangedSignature OnStateChanged;

	UPROPERTY(BlueprintAssignable, Category = "LastBell|WorldState")
	FLBStateReplacedSignature OnStateReplaced;

private:
	FLBWorldState WorldState;
};
