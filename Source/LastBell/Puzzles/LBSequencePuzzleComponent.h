#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameplayTagContainer.h"
#include "LBSequencePuzzleComponent.generated.h"

class ULBWorldStateSubsystem;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FLBSequenceStepSignature, int32, Index, FGameplayTag, Step);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FLBSequenceFailedSignature, FGameplayTag, WrongStep);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FLBSequenceSolvedSignature);

/**
 * Ordered-steps puzzle driven purely by world state tags. Steps are normally granted by interactables (BP_PuzzleCandle,
 * bells). When a step tag is added in order the puzzle accepts it; out of order it removes every step tag (next tick) and
 * fires OnPuzzleFailed; when the last step is accepted it adds SolvedTags, fires OnPuzzleSolved and stops listening.
 *
 * Progress is never stored: it is the longest present prefix of Steps, so a save made mid-puzzle simply works. On BeginPlay
 * and on OnStateReplaced the present step tags are validated and silently reset when they are not a valid prefix. Blueprints
 * snap their visuals from the tags at BeginPlay; the delegates here are for live feedback only (no events fire for state that
 * was already present when the level began).
 */
UCLASS(ClassGroup = "LastBell", meta = (BlueprintSpawnableComponent))
class LASTBELL_API ULBSequencePuzzleComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	/** The step tags, in the required order. Must be unique. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Puzzle")
	TArray<FGameplayTag> Steps;

	/** Added to world state when the puzzle is solved. If all of these are already present on BeginPlay the component is inert. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Puzzle")
	FGameplayTagContainer SolvedTags;

	/** A step was accepted in order. Index is the step's position in Steps. */
	UPROPERTY(BlueprintAssignable, Category = "LastBell|Puzzle")
	FLBSequenceStepSignature OnStepAccepted;

	/** A step was added out of order; all step tags have just been removed. WrongStep is the offending tag. */
	UPROPERTY(BlueprintAssignable, Category = "LastBell|Puzzle")
	FLBSequenceFailedSignature OnPuzzleFailed;

	/** The last step was accepted and SolvedTags have been added. */
	UPROPERTY(BlueprintAssignable, Category = "LastBell|Puzzle")
	FLBSequenceSolvedSignature OnPuzzleSolved;

	/** Number of steps currently accepted (the present, in-order prefix). */
	UFUNCTION(BlueprintPure, Category = "LastBell|Puzzle")
	int32 GetProgress() const { return Accepted; }

	UFUNCTION(BlueprintPure, Category = "LastBell|Puzzle")
	bool IsSolved() const { return bSolved; }

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	enum class EMode : uint8
	{
		Live,  // a step was just added by gameplay: accept / fail loudly
		Quiet, // BeginPlay, state replaced or a removal: re-derive and silently repair
	};

	UFUNCTION()
	void HandleStateChanged(FGameplayTag Tag, bool bAdded);

	UFUNCTION()
	void HandleStateReplaced();

	UFUNCTION()
	void ExecutePendingFail();

	void Evaluate(FGameplayTag Trigger, EMode Mode);
	void ResetSteps();
	void Solve();
	void StopListening();

	TWeakObjectPtr<ULBWorldStateSubsystem> WorldState;
	int32 Accepted = 0;
	bool bSolved = false;
	bool bListening = false;
	/** True while this component itself removes step tags, so it ignores its own broadcasts. */
	bool bInternalChange = false;
	bool bFailPending = false;
	FGameplayTag PendingWrongStep;
};
