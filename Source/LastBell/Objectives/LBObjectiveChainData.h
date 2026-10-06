#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "GameplayTagContainer.h"
#include "LBObjectiveChainData.generated.h"

USTRUCT(BlueprintType)
struct LASTBELL_API FLBObjective
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Objectives")
	FGameplayTag Id;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Objectives")
	FText Text;

	/** Objective is complete when all of these are present in world state. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Objectives")
	FGameplayTagContainer CompletionStateTags;
};

/** Ordered objective chain. Reordering after saves exist requires bumping the save version. */
UCLASS(BlueprintType)
class LASTBELL_API ULBObjectiveChainData : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "LastBell|Objectives")
	TArray<FLBObjective> Objectives;

	/** First objective whose completion tags are not all present; INDEX_NONE if all are complete. */
	UFUNCTION(BlueprintPure, Category = "LastBell|Objectives")
	int32 FindActiveIndex(const FGameplayTagContainer& State) const;
};
