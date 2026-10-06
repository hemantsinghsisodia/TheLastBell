#pragma once

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"

/** Pure logic holder for the canonical set of State.* tags. Each mutator returns true if anything changed. */
struct LASTBELL_API FLBWorldState
{
	bool Add(const FGameplayTag& Tag);
	bool Remove(const FGameplayTag& Tag);
	bool Has(const FGameplayTag& Tag) const;
	bool HasAll(const FGameplayTagContainer& InTags) const;
	bool Reset();
	bool Replace(const FGameplayTagContainer& NewTags);
	const FGameplayTagContainer& GetTags() const { return Tags; }

private:
	FGameplayTagContainer Tags;
};
