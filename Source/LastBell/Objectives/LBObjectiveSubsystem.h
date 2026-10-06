#pragma once

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"
#include "Subsystems/WorldSubsystem.h"
#include "LBObjectiveSubsystem.generated.h"

class ULBObjectiveChainData;
class ULBWorldStateSubsystem;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FLBObjectiveChangedSignature, int32, Index, FText, Text);

/** Derives the active objective from world state; broadcasts only when the active index changes. */
UCLASS()
class LASTBELL_API ULBObjectiveSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void Deinitialize() override;

	UFUNCTION(BlueprintPure, Category = "LastBell|Objectives")
	FText GetActiveObjectiveText() const;

	/** INDEX_NONE when all complete or no chain is assigned. */
	UFUNCTION(BlueprintPure, Category = "LastBell|Objectives")
	int32 GetActiveIndex() const { return ActiveIndex; }

	UPROPERTY(BlueprintAssignable, Category = "LastBell|Objectives")
	FLBObjectiveChangedSignature OnObjectiveChanged;

protected:
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;

private:
	UFUNCTION()
	void HandleStateChanged(FGameplayTag Tag, bool bAdded);

	UFUNCTION()
	void HandleStateReplaced();

	void Recompute();

	UPROPERTY(Transient)
	TObjectPtr<const ULBObjectiveChainData> Chain;

	TWeakObjectPtr<ULBWorldStateSubsystem> WorldState;
	int32 ActiveIndex = INDEX_NONE;
	bool bHasComputed = false;
};
