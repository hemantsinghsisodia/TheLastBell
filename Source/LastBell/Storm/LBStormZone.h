#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LBStormZone.generated.h"

class UBoxComponent;

/**
 * A box in the level that says how exposed the space inside is to the sky, 0 (a sealed crypt) to 1 (the open courtyard). No
 * collision; it only registers with ULBStormSubsystem, which uses the zones for the Warden reveal rule and for the player's
 * exposure (PlayerExposure in MPC_LB_Storm). Rotate the actor to line it up with a wall; set the size with the box extent (half
 * extents, cm).
 *
 * Exposure at a point is that of the highest-Priority zone containing it; on a tie the lowest Exposure wins.
 */
UCLASS()
class LASTBELL_API ALBStormZone : public AActor
{
	GENERATED_BODY()

public:
	ALBStormZone();

	/** 0 = sealed from the sky, 1 = open sky. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Storm", meta = (ClampMin = "0", ClampMax = "1"))
	float Exposure = 1.f;

	/** Inside several zones the highest priority wins. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Storm")
	int32 Priority = 0;

	UFUNCTION(BlueprintPure, Category = "Storm")
	UBoxComponent* GetBox() const { return Box; }

	/** The point is inside the (possibly rotated and scaled) box. */
	UFUNCTION(BlueprintPure, Category = "Storm")
	bool ContainsPoint(const FVector& WorldPoint) const;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UBoxComponent> Box;
};
