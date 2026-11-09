#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LBAudioZone.generated.h"

class UBoxComponent;
class USoundBase;

/**
 * A box in the level that says what the air sounds like inside (plan P16 section 2.4): how much of the rain is heard as a roof
 * patter, how much wind comes through, how much the tower howls, how frightening the place is without a light, and the room tone.
 * No collision; it only registers with ULBAudioSubsystem, which checks the listener against the zones four times a second. Rotate
 * the actor to line it up with a wall; set the size with the box extent (half extents, cm). Follows ALBStormZone.
 *
 * Inside several zones the highest Priority wins; outdoors (no zone) is the default. The reverb is not here: it comes from engine
 * AAudioVolume actors with the same bounds.
 */
UCLASS()
class LASTBELL_API ALBAudioZone : public AActor
{
	GENERATED_BODY()

public:
	ALBAudioZone();

	/** Inside several zones the highest priority wins. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Audio")
	int32 Priority = 0;

	/** How loud the roof rain loop is under cover, 0 (none: a crypt) to 1 (a roof right above). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Audio", meta = (ClampMin = "0", ClampMax = "1"))
	float RoofRain = 0.f;

	/** How much wind is heard inside, 0 to 1 (the wind loop is at least this loud, times the storm's wind strength). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Audio", meta = (ClampMin = "0", ClampMax = "1"))
	float InteriorWind = 0.f;

	/** The tower howl, 0 to 1 (times the storm's wind strength). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Audio", meta = (ClampMin = "0", ClampMax = "1"))
	float Howl = 0.f;

	/** How frightening the place is to stand in without light, 0 to 1: it sets the floor of the player's stress (crypt 1.0, outdoors 0.1). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Audio", meta = (ClampMin = "0", ClampMax = "1"))
	float Darkness = 0.1f;

	/** The room tone: a 2D loop that crossfades in when the listener enters. Leave empty for none. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Audio")
	TSoftObjectPtr<USoundBase> RoomTone;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Audio", meta = (ClampMin = "0", ClampMax = "2"))
	float RoomToneVolume = 1.f;

	/** For the debug readout and the tests ("Chapel", "Crypt"). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Audio")
	FName ZoneName;

	UFUNCTION(BlueprintPure, Category = "Audio")
	UBoxComponent* GetBox() const { return Box; }

	/** The point is inside the (possibly rotated and scaled) box. */
	UFUNCTION(BlueprintPure, Category = "Audio")
	bool ContainsPoint(const FVector& WorldPoint) const;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UBoxComponent> Box;
};
