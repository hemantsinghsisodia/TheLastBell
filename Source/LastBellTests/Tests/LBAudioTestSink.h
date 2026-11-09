#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "Engine/World.h"
#include "Storm/LBStormTypes.h"
#include "LBAudioTestSink.generated.h"

class ULBStormSubsystem;

/**
 * Records the storm's OnLightningStrike delegate with the world time (the time of the flash), so the P16 functional tests can measure the
 * delay from a flash to its thunder. Dynamic delegates can only bind UFUNCTIONs on a UObject, hence this class. The audio subsystem keeps
 * its own request log (ULBAudioSubsystem::GetRequests), which is the other half of those tests. Test-only; never spawned by gameplay.
 */
UCLASS()
class LASTBELLTESTS_API ULBAudioTestSink : public UObject
{
	GENERATED_BODY()

public:
	struct FStrikeRecord
	{
		double Time = 0.0;
		FLBLightningStrikeInfo Info;
	};

	TWeakObjectPtr<UWorld> World;
	TArray<FStrikeRecord> Strikes;

	void Bind(ULBStormSubsystem* Storm, UWorld* InWorld);

	UFUNCTION()
	void HandleStrike(const FLBLightningStrikeInfo& Info);
};
