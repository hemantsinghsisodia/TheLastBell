#pragma once

#include "CoreMinimal.h"

/**
 * Pure helpers for the Warden's animation (P13-2): stoop zones, easing, turn detection, foot placement and the attack play rate.
 * No world, no actor, no anim instance: ULBWardenAnimInstance gathers the facts and applies the results. Unit tested
 * (LastBell.Warden.Anim.*).
 */

/** One oriented stoop box in world space: where it is, how it is turned, how big (half extents, cm) and how deep the stoop is. */
struct FLBStoopBox
{
	FVector Center = FVector::ZeroVector;
	FQuat Rotation = FQuat::Identity;
	FVector HalfExtent = FVector::ZeroVector;
	/** 0 (upright) to 1 (full stoop). */
	float Amount = 0.f;
};

/** Which way the Warden should turn on the spot. Yaw grows clockwise seen from above, so a positive change is a right turn. */
enum class ELBWardenTurn : uint8
{
	None,
	Left,
	Right
};

/** Yaw change per frame over the last Window seconds. Feed it every frame; Total() is the net change inside the window. */
struct LASTBELL_API FLBYawHistory
{
	/** Seconds of history that count. */
	float Window = 0.5f;

	/** Records this frame's yaw change (degrees, any sign) at time Now (seconds, increasing), and forgets samples older than Window. */
	void Add(float Now, float DeltaYawDegrees);

	void Reset() { Samples.Reset(); }

	/** Net yaw change inside the window, degrees. */
	float Total() const;

	int32 Num() const { return Samples.Num(); }

private:
	struct FSample
	{
		float Time = 0.f;
		float Delta = 0.f;
	};
	TArray<FSample> Samples;
};

/** What one foot trace found. Offset = the ground height under the foot minus the height of the floor the capsule stands on (the capsule's bottom), cm, up is positive. */
struct FLBFootHit
{
	bool bHit = false;
	float Offset = 0.f;
};

/**
 * Foot IK result. LeftOffset and RightOffset are how far each foot has to move from where the animation puts it (flat ground: 0).
 * PelvisZ is the pelvis move that goes with them (0 or negative).
 */
struct FLBFootPlacement
{
	float LeftOffset = 0.f;
	float RightOffset = 0.f;
	float PelvisZ = 0.f;
	/** The two feet are on ground that differs by more than the activation difference: the IK is wanted. */
	bool bActive = false;
};

namespace LBWardenAnim
{
	/** Is Point inside the oriented box? Edges count as inside. A box with a negative half extent contains nothing. */
	LASTBELL_API bool IsPointInBox(const FLBStoopBox& Box, const FVector& Point);

	/** The highest Amount among the boxes that contain Location; 0 when none does. */
	LASTBELL_API float StoopTarget(TConstArrayView<FLBStoopBox> Zones, const FVector& Location);

	/** Moves Current towards Target by at most RatePerSecond * DeltaSeconds (constant speed, never overshoots). */
	LASTBELL_API float EaseTowards(float Current, float Target, float RatePerSecond, float DeltaSeconds);

	/**
	 * Turn on the spot? Only when the Warden is (nearly) standing (GroundSpeed < MaxSpeed), no montage plays, the cooldown is over
	 * (CooldownLeft <= 0) and the yaw change inside the history window is at least TriggerDegrees either way.
	 */
	LASTBELL_API ELBWardenTurn TurnDecision(const FLBYawHistory& History, float GroundSpeed, bool bMontageActive, float CooldownLeft, float TriggerDegrees = 60.f, float MaxSpeed = 15.f);

	/**
	 * Foot IK from the two traces (offset based). A trace that hit nothing counts as flat ground (offset 0). The pelvis moves by the
	 * more negative of the two offsets, never lower than -MaxPelvisDrop and never up. The IK is active when the feet differ by more
	 * than ActivateDifference.
	 */
	LASTBELL_API FLBFootPlacement PelvisAndFeet(const FLBFootHit& Left, const FLBFootHit& Right, float MaxPelvisDrop, float ActivateDifference = 5.f);

	/** Where a foot goes: the animated foot's own position with Offset added to Z. A foot lifted in its swing keeps its lift. */
	LASTBELL_API FVector FootTarget(const FVector& AnimatedFoot, float Offset);

	/**
	 * How far up a foot has to move from where the pelvis move left it, to end on FootTarget: the foot's Offset minus the pelvis move
	 * that dragged it along (a pelvis dropped by 40 asks every foot to come back up by 40).
	 */
	LASTBELL_API float FootCorrection(float Offset, float AppliedPelvisZ);

	/**
	 * The pelvis translation: the foot IK's pelvis move, plus StoopPelvisDrop * StoopAlpha downwards, in total never lower than
	 * -(MaxPelvisDrop + StoopPelvisDrop) and never up.
	 */
	LASTBELL_API float CombinedPelvisZ(float FootPelvisZ, float StoopAlpha, float StoopPelvisDrop, float MaxPelvisDrop);

	/** Play rate that puts the clip's hit moment (seconds into the clip) on the end of the windup: HitTime / Windup, clamped to 0.8..2.5. 1 when either is unknown. */
	LASTBELL_API float AttackPlayRate(float HitTimeSeconds, float WindupSeconds);
}
