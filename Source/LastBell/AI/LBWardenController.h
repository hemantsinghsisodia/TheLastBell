#pragma once

#include "CoreMinimal.h"
#include "AIController.h"
#include "Perception/AIPerceptionTypes.h"
#include "LBWardenController.generated.h"

class ULBWardenBrainComponent;
class UAISenseConfig_Sight;
class UAISenseConfig_Hearing;

/**
 * AI controller for the Warden. Owns the perception component (sight + hearing, detecting enemies, neutrals and friendlies
 * because the player is neutral) and the brain. It forwards perception updates and move-completed events to the brain and
 * contains no decision logic.
 */
UCLASS()
class LASTBELL_API ALBWardenController : public AAIController
{
	GENERATED_BODY()

public:
	ALBWardenController();

	UFUNCTION(BlueprintPure, Category = "LastBell|Warden")
	ULBWardenBrainComponent* GetBrain() const { return Brain; }

	/** Applies the sight radii for the stage (the largest effective radius, candle included) and the tuning's hearing range. */
	void UpdatePerceptionForStage(int32 Stage);

	virtual void OnMoveCompleted(FAIRequestID RequestID, const FPathFollowingResult& Result) override;
	using AAIController::OnMoveCompleted;

protected:
	virtual void PostInitializeComponents() override;
	virtual void OnPossess(APawn* InPawn) override;

private:
	UFUNCTION()
	void HandleTargetPerceptionUpdated(AActor* Actor, FAIStimulus Stimulus);

	UPROPERTY(VisibleAnywhere, Category = "LastBell|Warden")
	TObjectPtr<ULBWardenBrainComponent> Brain;

	UPROPERTY(Transient)
	TObjectPtr<UAISenseConfig_Sight> SightConfig;

	UPROPERTY(Transient)
	TObjectPtr<UAISenseConfig_Hearing> HearingConfig;
};
