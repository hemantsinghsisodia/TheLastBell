#pragma once

#include "CoreMinimal.h"

/** Pure logic: tracks which SaveIds are in use so duplicates can be detected. */
struct LASTBELL_API FLBSaveIdRegistry
{
	/** Returns false if the id is None or already registered. */
	bool Register(FName Id)
	{
		if (Id.IsNone() || Ids.Contains(Id))
		{
			return false;
		}
		Ids.Add(Id);
		return true;
	}

	void Unregister(FName Id) { Ids.Remove(Id); }
	void Reset() { Ids.Reset(); }
	bool Contains(FName Id) const { return Ids.Contains(Id); }

private:
	TSet<FName> Ids;
};
