#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "LBWardenStoopSubsystem.generated.h"

class ALBWardenStoopZone;

/**
 * Keeps the stoop zones of the world (P13). Zones register on BeginPlay and unregister on EndPlay (a subsystem, not a manager
 * actor). The Warden's anim instance asks GetStoopAmount for its location every frame; there are a dozen zones, so the
 * query walks them all.
 */
UCLASS()
class LASTBELL_API ULBWardenStoopSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	void RegisterZone(ALBWardenStoopZone* Zone);
	void UnregisterZone(ALBWardenStoopZone* Zone);

	/** The highest StoopAmount among the zones whose box contains Location; 0 when none does. */
	UFUNCTION(BlueprintPure, Category = "LastBell|Warden")
	float GetStoopAmount(const FVector& Location) const;

	int32 GetZoneCount() const { return Zones.Num(); }

private:
	TArray<TWeakObjectPtr<ALBWardenStoopZone>> Zones;
};
