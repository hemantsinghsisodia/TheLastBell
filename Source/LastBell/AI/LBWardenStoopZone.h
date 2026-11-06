#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "AI/LBWardenAnim.h"
#include "LBWardenStoopZone.generated.h"

class UBoxComponent;

/**
 * A box in the level where the Warden stoops (P13): a low door, a low stair headroom. No collision; it only registers with
 * ULBWardenStoopSubsystem, which the Warden's anim instance asks for the stoop at its location. Rotate the actor to line it up
 * with the wall; set the size with the box's extent (half extents, cm). The box outline shows in the editor.
 */
UCLASS()
class LASTBELL_API ALBWardenStoopZone : public AActor
{
	GENERATED_BODY()

public:
	ALBWardenStoopZone();

	/** 0 = upright, 1 = full stoop. Inside several zones the highest amount wins. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stoop", meta = (ClampMin = "0", ClampMax = "1"))
	float StoopAmount = 1.f;

	UFUNCTION(BlueprintPure, Category = "Stoop")
	UBoxComponent* GetBox() const { return Box; }

	/** The zone as a world-space oriented box, ready for LBWardenAnim::StoopTarget. */
	FLBStoopBox ToStoopBox() const;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UBoxComponent> Box;
};
