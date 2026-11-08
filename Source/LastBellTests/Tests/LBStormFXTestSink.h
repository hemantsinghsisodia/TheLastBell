#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "Engine/World.h"
#include "Storm/LBStormTypes.h"
#include "LBStormFXTestSink.generated.h"

class ULBStormSubsystem;

/**
 * Records the storm's OnLightningFlash and OnLightningStrike delegates with a running sequence number and the world time, so the P15
 * functional tests can assert that the two fire together for the same flash. Dynamic delegates can only bind UFUNCTIONs on a UObject,
 * hence this class. Test-only; never spawned by gameplay.
 */
UCLASS()
class LASTBELLTESTS_API ULBStormFXTestSink : public UObject
{
	GENERATED_BODY()

public:
	struct FFlashRecord
	{
		int32 Seq = 0;
		double Time = 0.0;
		float Brightness = 0.f;
		ELBFlashReason Reason = ELBFlashReason::Ambient;
	};

	struct FStrikeRecord
	{
		int32 Seq = 0;
		double Time = 0.0;
		FLBLightningStrikeInfo Info;
	};

	TWeakObjectPtr<UWorld> World;
	TArray<FFlashRecord> Flashes;
	TArray<FStrikeRecord> Strikes;
	int32 NextSeq = 0;

	void Bind(ULBStormSubsystem* Storm, UWorld* InWorld);

	UFUNCTION()
	void HandleFlash(float Brightness, ELBFlashReason Reason);

	UFUNCTION()
	void HandleStrike(const FLBLightningStrikeInfo& Info);
};
