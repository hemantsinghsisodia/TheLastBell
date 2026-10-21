#pragma once

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"

/**
 * Pure (UObject-free) logic behind the sequence and dial puzzle components, so it can be unit tested.
 * Both work on the canonical world state tag set: progress is DERIVED from which tags are present, never stored.
 */

/** Evaluation of an ordered step list against the world state. */
struct LASTBELL_API FLBSequenceLogic
{
	struct FEval
	{
		/** Number of leading steps that are present (steps are accepted strictly in order). */
		int32 Progress = 0;
		/** True when the present step tags are exactly Steps[0 .. Progress-1], i.e. no step is present out of order. */
		bool bValidPrefix = true;
	};

	static FEval Evaluate(const TArray<FGameplayTag>& Steps, const FGameplayTagContainer& State);

	/** All step tags as a container (for bulk removal). */
	static FGameplayTagContainer ToContainer(const TArray<FGameplayTag>& Steps);

	/** True when the step list is usable: non-empty, every tag valid, no duplicates. */
	static bool IsConfigValid(const TArray<FGameplayTag>& Steps);
};

/** A planned change to the world state for a dial. */
struct LASTBELL_API FLBDialChange
{
	/** Tag to add (invalid = none). */
	FGameplayTag Add;
	/** Tags to remove. */
	FGameplayTagContainer Remove;
	/** Position index after the change (INDEX_NONE if the dial has no positions). */
	int32 NewIndex = INDEX_NONE;
};

/** One tag per dial position; exactly one is present at any time. */
struct LASTBELL_API FLBDialLogic
{
	/** Lowest index whose tag is present, or INDEX_NONE. */
	static int32 FindCurrentIndex(const TArray<FGameplayTag>& Positions, const FGameplayTagContainer& State);

	/** The index after Current, wrapping. INDEX_NONE (no current position) goes to 0. Returns INDEX_NONE when Num <= 0. */
	static int32 NextIndex(int32 Num, int32 Current);

	/**
	 * BeginPlay plan. No position present: add Positions[InitialIndex] (clamped into range). Several present (corrupt):
	 * keep the lowest index and remove the others. Exactly one present: no change.
	 */
	static FLBDialChange PlanInit(const TArray<FGameplayTag>& Positions, int32 InitialIndex, const FGameplayTagContainer& State);

	/** Cycle plan: remove the current tag, add the next one (wrapping). */
	static FLBDialChange PlanCycle(const TArray<FGameplayTag>& Positions, const FGameplayTagContainer& State);
};
