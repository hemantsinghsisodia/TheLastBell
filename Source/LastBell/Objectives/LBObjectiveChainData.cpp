#include "Objectives/LBObjectiveChainData.h"

int32 ULBObjectiveChainData::FindActiveIndex(const FGameplayTagContainer& State) const
{
	for (int32 Index = 0; Index < Objectives.Num(); ++Index)
	{
		if (!State.HasAllExact(Objectives[Index].CompletionStateTags))
		{
			return Index;
		}
	}
	return INDEX_NONE;
}
