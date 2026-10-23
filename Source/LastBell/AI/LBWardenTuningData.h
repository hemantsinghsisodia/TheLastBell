#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "AI/LBWardenTypes.h"
#include "LBWardenTuningData.generated.h"

/**
 * Every Warden tunable (DA_WardenTuning, assigned on BP_Warden). The defaults are the Phase 5 starting values and also the
 * fallback when no asset is assigned. Speeds must stay Walk(260) < Chase < Sprint(480) of ULBPlayerTuningData; a test checks it.
 */
UCLASS(BlueprintType)
class LASTBELL_API ULBWardenTuningData : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	// ---- Body (D-038) ----
	/** Collision capsule. Must fit the monastery doorways (about 104 x 230 cm); the visual body can be taller. Keep in sync with the navmesh agent. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Body", meta = (ClampMin = "1"))
	float CapsuleRadius = 42.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Body", meta = (ClampMin = "1"))
	float CapsuleHalfHeight = 110.f;

	/** Eye height above the capsule centre (where sight is cast from). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Body", meta = (ClampMin = "0"))
	float EyeHeight = 85.f;

	// ---- Move speeds (cm/s) ----
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Speed", meta = (ClampMin = "0"))
	float PatrolSpeed = 140.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Speed", meta = (ClampMin = "0"))
	float InvestigateSpeed = 190.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Speed", meta = (ClampMin = "0"))
	float SearchSpeed = 170.f;

	/** Walking back to the route or post after a search. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Speed", meta = (ClampMin = "0"))
	float ReturnSpeed = 170.f;

	/** Must stay below the player's sprint speed and above the walk speed. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Speed", meta = (ClampMin = "0"))
	float ChaseSpeed = 420.f;

	/** Yaw turn rate while standing still (look-around, facing the player during the attack windup), degrees per second. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Speed", meta = (ClampMin = "1"))
	float TurnRate = 180.f;

	// ---- Sight ----
	/** Stage 3 (Investigation). Stages below 3 reuse this value; the Warden is dormant there anyway. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sight", meta = (ClampMin = "0"))
	float SightRadiusStage3 = 1500.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sight", meta = (ClampMin = "0"))
	float SightRadiusStage4 = 2000.f;

	/** Stage 5 and above (Hunt, Finale). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sight", meta = (ClampMin = "0"))
	float SightRadiusStage5 = 2500.f;

	/** A target already seen is only lost beyond sight radius plus this. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sight", meta = (ClampMin = "0"))
	float LoseSightExtraRadius = 300.f;

	/** Half of the sight cone, degrees (45 gives a 90 degree cone). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sight", meta = (ClampMin = "1", ClampMax = "180"))
	float PeripheralHalfAngle = 45.f;

	/** Continuous line of sight needed before sight triggers Chase or Investigate. This is also the audible-tell lead time. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sight", meta = (ClampMin = "0"))
	float SightConfirmTime = 0.6f;

	/** Multiplier on the effective sight radius while the player's candle is lit. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sight", meta = (ClampMin = "1"))
	float CandleLitSightMultiplier = 1.25f;

	// ---- Hearing ----
	/** Range at loudness 1. The engine scales it by loudness (walk 0.3 is heard at 30 percent of this range). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Hearing", meta = (ClampMin = "0"))
	float HearingRange = 2500.f;

	/** Noises quieter than this are ignored even when in range. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Hearing", meta = (ClampMin = "0", ClampMax = "1"))
	float HearingLoudnessThreshold = 0.05f;

	// ---- Memory, search, suspicion ----
	/** After losing sight in Chase, the Warden goes to the last-known location and gives up after this long. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Memory", meta = (ClampMin = "0"))
	float LastKnownMemorySeconds = 6.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Search", meta = (ClampMin = "0"))
	float SearchDurationSeconds = 12.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Search", meta = (ClampMin = "0"))
	int32 SearchPointCount = 3;

	/** Search points are chosen within this distance of the last-known location. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Search", meta = (ClampMin = "0"))
	float SearchPointRadius = 1500.f;

	/** Pause at each search point. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Search", meta = (ClampMin = "0"))
	float SearchPointPauseSeconds = 2.f;

	/** With no ALBSearchPoint in range, random reachable points within this distance of the last-known location are used. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Search", meta = (ClampMin = "0"))
	float SearchFallbackRadius = 800.f;

	/** Stand and look around at the end of an investigation. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Suspicious", meta = (ClampMin = "0"))
	float SuspiciousSeconds = 2.5f;

	/** The look-around sweeps this far either side of the heading, degrees. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Suspicious", meta = (ClampMin = "0", ClampMax = "180"))
	float LookAroundHalfAngle = 70.f;

	// ---- Attack ----
	/** Centre-to-centre distance, with line of sight, at which the Warden starts an attack. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Attack", meta = (ClampMin = "0"))
	float AttackRange = 140.f;

	/** Stop-and-tell time (audio / animation). The range and sight are checked again when it ends. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Attack", meta = (ClampMin = "0"))
	float AttackWindupSeconds = 0.6f;

	/** After a cancelled attack, no new attack may start for this long (the Warden chases instead). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Attack", meta = (ClampMin = "0"))
	float AttackCooldownSeconds = 1.5f;

	// ---- Movement ----
	/** Move acceptance radius; the agent radius is added on top. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Movement", meta = (ClampMin = "0"))
	float ArrivalRadius = 50.f;

	/** While chasing or investigating a visible target, the move is re-issued at most this often... */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Movement", meta = (ClampMin = "0.05"))
	float RepathIntervalSeconds = 0.25f;

	/** ...and only when the target moved at least this far from the current move goal. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Movement", meta = (ClampMin = "0"))
	float RepathMinDistance = 100.f;

	// ---- Stuck ----
	/** No progress for this long while moving counts as stuck: re-path first, give the target up on the second failure. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Stuck", meta = (ClampMin = "0.1"))
	float StuckSeconds = 3.f;

	/** Moving less than this from the progress anchor within StuckSeconds counts as no progress. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Stuck", meta = (ClampMin = "0"))
	float StuckMinProgress = 25.f;

	/** Travelling this far after a stuck event forgives it (the failure count restarts). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Stuck", meta = (ClampMin = "0"))
	float StuckForgiveDistance = 150.f;

	// ---- Unreachable target ----
	/** Query extent used to find the closest navigable point when a target is off the navmesh. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Unreachable", meta = (ClampMin = "0"))
	float UnreachableFallbackRadius = 600.f;

	/** After finding the player unreachable, the Warden will not start another chase for this long. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Unreachable", meta = (ClampMin = "0"))
	float UnreachableRecheckSeconds = 8.f;

	// ---- Spawning ----
	/** How often a dormant Warden retries to appear when the player could see the spawn point. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawn", meta = (ClampMin = "0.05"))
	float MaterializeRetrySeconds = 0.5f;

	/** Half of the angle around the player's view direction treated as "can see" when hiding spawns and teleports. Deliberately wider than the FOV. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawn", meta = (ClampMin = "1", ClampMax = "180"))
	float PlayerViewHalfAngle = 75.f;

	// ---- Queries ----
	float GetSightRadiusForStage(int32 Stage) const;
	float GetMoveSpeed(ELBWardenState State) const;
};
