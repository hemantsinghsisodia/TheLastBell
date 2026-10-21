#include "Puzzles/LBPuzzleLogic.h"

FLBSequenceLogic::FEval FLBSequenceLogic::Evaluate(const TArray<FGameplayTag>& Steps, const FGameplayTagContainer& State)
{
	FEval Result;
	int32 PresentCount = 0;
	bool bPrefixOpen = true;
	for (const FGameplayTag& Step : Steps)
	{
		const bool bPresent = Step.IsValid() && State.HasTagExact(Step);
		if (bPresent)
		{
			++PresentCount;
			if (bPrefixOpen)
			{
				++Result.Progress;
			}
		}
		else
		{
			bPrefixOpen = false;
		}
	}
	Result.bValidPrefix = (PresentCount == Result.Progress);
	return Result;
}

FGameplayTagContainer FLBSequenceLogic::ToContainer(const TArray<FGameplayTag>& Steps)
{
	FGameplayTagContainer Out;
	for (const FGameplayTag& Step : Steps)
	{
		if (Step.IsValid())
		{
			Out.AddTag(Step);
		}
	}
	return Out;
}

bool FLBSequenceLogic::IsConfigValid(const TArray<FGameplayTag>& Steps)
{
	if (Steps.IsEmpty())
	{
		return false;
	}
	TSet<FGameplayTag> Seen;
	for (const FGameplayTag& Step : Steps)
	{
		if (!Step.IsValid())
		{
			return false;
		}
		bool bAlreadyInSet = false;
		Seen.Add(Step, &bAlreadyInSet);
		if (bAlreadyInSet)
		{
			return false;
		}
	}
	return true;
}

int32 FLBDialLogic::FindCurrentIndex(const TArray<FGameplayTag>& Positions, const FGameplayTagContainer& State)
{
	for (int32 Index = 0; Index < Positions.Num(); ++Index)
	{
		if (Positions[Index].IsValid() && State.HasTagExact(Positions[Index]))
		{
			return Index;
		}
	}
	return INDEX_NONE;
}

int32 FLBDialLogic::NextIndex(int32 Num, int32 Current)
{
	if (Num <= 0)
	{
		return INDEX_NONE;
	}
	if (Current < 0 || Current >= Num)
	{
		return 0;
	}
	return (Current + 1) % Num;
}

FLBDialChange FLBDialLogic::PlanInit(const TArray<FGameplayTag>& Positions, int32 InitialIndex, const FGameplayTagContainer& State)
{
	FLBDialChange Change;
	if (Positions.IsEmpty())
	{
		return Change;
	}
	const int32 Current = FindCurrentIndex(Positions, State);
	if (Current == INDEX_NONE)
	{
		Change.NewIndex = FMath::Clamp(InitialIndex, 0, Positions.Num() - 1);
		Change.Add = Positions[Change.NewIndex];
		return Change;
	}
	Change.NewIndex = Current;
	for (int32 Index = Current + 1; Index < Positions.Num(); ++Index)
	{
		if (Positions[Index].IsValid() && Positions[Index] != Positions[Current] && State.HasTagExact(Positions[Index]))
		{
			Change.Remove.AddTag(Positions[Index]);
		}
	}
	return Change;
}

FLBDialChange FLBDialLogic::PlanCycle(const TArray<FGameplayTag>& Positions, const FGameplayTagContainer& State)
{
	FLBDialChange Change;
	if (Positions.IsEmpty())
	{
		return Change;
	}
	const int32 Current = FindCurrentIndex(Positions, State);
	Change.NewIndex = NextIndex(Positions.Num(), Current);
	if (Change.NewIndex == Current)
	{
		return Change; // a single-position dial: nothing to change
	}
	if (Current != INDEX_NONE)
	{
		Change.Remove.AddTag(Positions[Current]);
	}
	Change.Add = Positions[Change.NewIndex];
	return Change;
}
