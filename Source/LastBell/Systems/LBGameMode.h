#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "LBGameMode.generated.h"

class ULBObjectiveChainData;

UCLASS()
class LASTBELL_API ALBGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	ALBGameMode();

	UFUNCTION(BlueprintPure, Category = "LastBell|Objectives")
	const ULBObjectiveChainData* GetObjectiveChain() const { return ObjectiveChain; }

	/** Reloads the last checkpoint; starts a new game on the current map when there is no valid save. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Game")
	void HandlePlayerDeath(AController* Controller);

	/** Spawns at the pending checkpoint transform when a restore is pending, else at a PlayerStart. */
	virtual void RestartPlayer(AController* NewPlayer) override;

	/** Hands the objective chain to the objective subsystem before any actor BeginPlay. */
	virtual void StartPlay() override;

protected:
	UPROPERTY(EditDefaultsOnly, Category = "LastBell|Objectives")
	TObjectPtr<ULBObjectiveChainData> ObjectiveChain;
};
