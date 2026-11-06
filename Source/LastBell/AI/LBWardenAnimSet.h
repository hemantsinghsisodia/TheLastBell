#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "LBWardenAnimSet.generated.h"

class UAnimMontage;

/**
 * Everything the Warden's anim instance needs from content: the four montages and the tuning numbers (P13). Saved as
 * /Game/LastBell/Data/DA_WardenAnimSet and assigned on the Animation Blueprint's class defaults. The defaults below are the
 * safe fallback when no asset is assigned (no montages: the calls do nothing).
 */
UCLASS(BlueprintType)
class LASTBELL_API ULBWardenAnimSet : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	// ---- Montages (slot DefaultSlot) ----
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Montages")
	TObjectPtr<UAnimMontage> Attack;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Montages")
	TObjectPtr<UAnimMontage> TurnLeft90;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Montages")
	TObjectPtr<UAnimMontage> TurnRight90;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Montages")
	TObjectPtr<UAnimMontage> LookAround;

	// ---- Attack ----
	/** Play rate of Attack: hit time / windup (0.6 s), clamped 0.8..2.5 (LBWardenAnim::AttackPlayRate). Stored here so it can be tuned without re-saving the clip. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Attack", meta = (ClampMin = "0.1", ClampMax = "4"))
	float AttackPlayRate = 1.f;

	/**
	 * Seconds into the Attack montage where the hands are furthest forward (measured by the retarget script). HoldCatchPose lets the
	 * montage reach this moment before it freezes. 0 = unknown: it freezes where it is.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Attack", meta = (ClampMin = "0", Units = "s"))
	float AttackHitTime = 0.f;

	// ---- Turning on the spot ----
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Turn", meta = (ClampMin = "0.1", ClampMax = "4"))
	float TurnPlayRate = 1.5f;

	/** Yaw change over the last 0.5 s that starts a turn montage. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Turn", meta = (ClampMin = "1", Units = "deg"))
	float TurnTriggerDegrees = 60.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Turn", meta = (ClampMin = "0", Units = "s"))
	float TurnCooldownSeconds = 1.f;

	// ---- Stoop ----
	/** How fast StoopAlpha follows the stoop zones, per second (3 = a full stoop in a third of a second). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Stoop", meta = (ClampMin = "0.1"))
	float StoopEaseRate = 3.f;

	// ---- Foot IK ----
	/** Foot trace starts this far above the floor the capsule stands on. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "FootIK", meta = (ClampMin = "0", Units = "cm"))
	float FootTraceUp = 50.f;

	/** ...and ends this far below it. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "FootIK", meta = (ClampMin = "0", Units = "cm"))
	float FootTraceDown = 75.f;

	/** Interpolation speed of the foot targets, the pelvis and the IK alpha (FInterpTo speed, 1/s). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "FootIK", meta = (ClampMin = "0.1"))
	float FootIKInterpSpeed = 15.f;

	/** The pelvis never drops more than this. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "FootIK", meta = (ClampMin = "0", Units = "cm"))
	float MaxPelvisDrop = 35.f;

	// ---- Physics ----
	/** Robe and chain physics are off beyond this distance from the player's camera. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Physics", meta = (ClampMin = "0", Units = "cm"))
	float PhysicsMaxDistance = 2500.f;
};
