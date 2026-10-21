#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "LBTestSink.generated.h"

class ULBInspectableComponent;

/**
 * Receives the dynamic multicast delegates of the player components so automation tests can count and inspect events.
 * Dynamic delegates can only bind UFUNCTIONs on a UObject, hence this tiny class. Test-only; never spawned by gameplay.
 */
UCLASS()
class LASTBELLTESTS_API ULBTestSink : public UObject
{
	GENERATED_BODY()

public:
	UFUNCTION()
	void HandleFootstep(float Loudness, FVector Location, TEnumAsByte<EPhysicalSurface> Surface)
	{
		FootstepLoudness.Add(Loudness);
	}

	UFUNCTION()
	void HandleInspectBegin(ULBInspectableComponent* Inspectable)
	{
		++InspectBeginCount;
	}

	UFUNCTION()
	void HandleInspectEnd(bool bKept)
	{
		++InspectEndCount;
		LastInspectKept = bKept;
	}

	UFUNCTION()
	void HandleInteracted(AActor* Instigator)
	{
		++InteractedCount;
	}

	UFUNCTION()
	void HandleCandleState(bool bLit)
	{
		CandleStateEvents.Add(bLit);
	}

	TArray<float> FootstepLoudness;
	int32 InspectBeginCount = 0;
	int32 InspectEndCount = 0;
	int32 InteractedCount = 0;
	bool LastInspectKept = false;
	TArray<bool> CandleStateEvents;
};
