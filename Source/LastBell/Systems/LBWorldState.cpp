#include "Systems/LBWorldState.h"

bool FLBWorldState::Add(const FGameplayTag& Tag)
{
	if (!Tag.IsValid() || Tags.HasTagExact(Tag))
	{
		return false;
	}
	Tags.AddTagFast(Tag);
	return true;
}

bool FLBWorldState::Remove(const FGameplayTag& Tag)
{
	return Tag.IsValid() && Tags.RemoveTag(Tag);
}

bool FLBWorldState::Has(const FGameplayTag& Tag) const
{
	return Tag.IsValid() && Tags.HasTagExact(Tag);
}

bool FLBWorldState::HasAll(const FGameplayTagContainer& InTags) const
{
	return Tags.HasAllExact(InTags);
}

bool FLBWorldState::Reset()
{
	if (Tags.IsEmpty())
	{
		return false;
	}
	Tags.Reset();
	return true;
}

bool FLBWorldState::Replace(const FGameplayTagContainer& NewTags)
{
	// Exact set comparison, independent of order.
	if (Tags.Num() == NewTags.Num() && Tags.HasAllExact(NewTags))
	{
		return false;
	}
	Tags = NewTags;
	return true;
}
