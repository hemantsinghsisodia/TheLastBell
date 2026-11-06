#include "AI/LBWardenStoopSubsystem.h"
#include "AI/LBWardenAnim.h"
#include "AI/LBWardenStoopZone.h"

void ULBWardenStoopSubsystem::RegisterZone(ALBWardenStoopZone* Zone)
{
	if (Zone)
	{
		Zones.RemoveAllSwap([](const TWeakObjectPtr<ALBWardenStoopZone>& Entry) { return !Entry.IsValid(); });
		Zones.AddUnique(Zone);
	}
}

void ULBWardenStoopSubsystem::UnregisterZone(ALBWardenStoopZone* Zone)
{
	Zones.RemoveSingleSwap(TWeakObjectPtr<ALBWardenStoopZone>(Zone));
}

float ULBWardenStoopSubsystem::GetStoopAmount(const FVector& Location) const
{
	// On the stack: the query runs once per Warden per frame.
	TArray<FLBStoopBox, TInlineAllocator<32>> Boxes;
	for (const TWeakObjectPtr<ALBWardenStoopZone>& Zone : Zones)
	{
		if (const ALBWardenStoopZone* Live = Zone.Get())
		{
			Boxes.Add(Live->ToStoopBox());
		}
	}
	return LBWardenAnim::StoopTarget(Boxes, Location);
}
