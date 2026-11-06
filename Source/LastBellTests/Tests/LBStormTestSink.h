#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "Engine/World.h"
#include "Storm/LBStormTypes.h"
#include "LBStormTestSink.generated.h"

class ULBStormSubsystem;

/**
 * Records the storm's OnLightningFlash delegate with world timestamps so functional tests can assert on the number, reason and time
 * of flashes. Dynamic delegates can only bind UFUNCTIONs on a UObject, hence this class. Test-only; never spawned by gameplay.
 */
UCLASS()
class LASTBELLTESTS_API ULBStormTestSink : public UObject
{
	GENERATED_BODY()

public:
	struct FRecord
	{
		double Time = 0.0;
		float Brightness = 0.f;
		ELBFlashReason Reason = ELBFlashReason::Ambient;
	};

	TWeakObjectPtr<UWorld> World;
	TArray<FRecord> Flashes;

	void Bind(ULBStormSubsystem* Storm, UWorld* InWorld);

	UFUNCTION()
	void HandleFlash(float Brightness, ELBFlashReason Reason);

	int32 Count(ELBFlashReason Reason) const
	{
		int32 Result = 0;
		for (const FRecord& Record : Flashes)
		{
			Result += Record.Reason == Reason ? 1 : 0;
		}
		return Result;
	}

	/** Time of the last flash with this reason, or -1. */
	double LastTime(ELBFlashReason Reason) const
	{
		double Result = -1.0;
		for (const FRecord& Record : Flashes)
		{
			if (Record.Reason == Reason)
			{
				Result = Record.Time;
			}
		}
		return Result;
	}
};
