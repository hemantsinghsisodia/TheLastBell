#pragma once

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"
#include "AI/LBWardenTypes.h"

class ULBWardenTuningData;

/**
 * Pure Warden decision logic: no world, no AI module. The brain component gathers facts from perception, navigation and timers,
 * asks Evaluate() for the next state, and applies it. Everything here is unit tested (LastBell.Warden.*).
 */

/** What the current escalation stage lets the Warden do (AI_DESIGN / D-018). */
struct FLBWardenCaps
{
	bool bActive = false;  // stage 3+: the pawn exists and can investigate, return and attack
	bool bPatrol = false;  // stage 4+
	bool bSearch = false;  // stage 4+
	bool bChase = false;   // stage 5+
};

/** Everything Evaluate() may look at. The brain fills it from what perception has actually reported. */
struct FLBWardenFacts
{
	FLBWardenCaps Caps;
	/** Sight is currently reporting the player inside the effective sight radius. */
	bool bSeesPlayer = false;
	/** Continuous line of sight lasted at least SightConfirmTime. */
	bool bSightConfirmed = false;
	/** A loud enough noise arrived since the last decision. */
	bool bNoiseHeard = false;
	/** Player seen, within AttackRange, with line of sight, and the attack is off cooldown. */
	bool bInAttackRange = false;
	/** Attack state only: range and line of sight, re-checked now. */
	bool bAttackStillValid = false;
	/** The current move goal was reached (or given up on after stuck recovery). */
	bool bArrived = false;
	/** The player could not be pathed to recently (partial or failed path). */
	bool bPlayerUnreachable = false;
	/** Search state only: the search plan has no unvisited points left. */
	bool bSearchFinished = false;
	/** Dormant only: the spawn point is free of the player's eyes. */
	bool bCanMaterialize = true;
	/** Seconds in the current state. */
	float StateTime = 0.f;
	/** Seconds since the player was last seen. */
	float TimeSinceSight = 0.f;
};

struct FLBWardenDecision
{
	ELBWardenState Next = ELBWardenState::Dormant;
	/** Enter the same state again (a new stimulus retargets Investigate). */
	bool bReenter = false;
	/** The attack landed: the brain must kill the player. */
	bool bKillPlayer = false;
	const TCHAR* Reason = TEXT("");
};

/** Continuous-line-of-sight timer. */
struct FLBSightConfirm
{
	float Continuous = 0.f;
	bool bVisible = false;

	void Advance(bool bNowVisible, float DeltaTime)
	{
		bVisible = bNowVisible;
		Continuous = bNowVisible ? Continuous + FMath::Max(DeltaTime, 0.f) : 0.f;
	}

	bool IsConfirmed(float ConfirmTime) const { return bVisible && Continuous >= ConfirmTime; }
	void Reset() { Continuous = 0.f; bVisible = false; }
};

enum class ELBStuckResult : uint8
{
	None,
	/** First failure: re-issue the move. */
	Repath,
	/** Second consecutive failure: give the target up (next point / treat as arrived). */
	GiveUp
};

/** Detects "moving but not getting anywhere". Feed it the pawn location every frame while a move is active. */
struct FLBStuckDetector
{
	float StuckSeconds = 3.f;
	float MinProgress = 25.f;
	float ForgiveDistance = 150.f;

	void Reset()
	{
		bHasAnchor = false;
		TimeSinceProgress = 0.f;
		Failures = 0;
		bHasFailure = false;
	}

	/** Stop watching (waiting, standing, not moving) without forgetting earlier failures. */
	void Pause() { bHasAnchor = false; TimeSinceProgress = 0.f; }

	ELBStuckResult Update(float DeltaTime, const FVector& Location)
	{
		if (!bHasAnchor)
		{
			Anchor = Location;
			bHasAnchor = true;
			TimeSinceProgress = 0.f;
			return ELBStuckResult::None;
		}
		if (bHasFailure && FVector::Dist(Location, FailureLocation) >= ForgiveDistance)
		{
			Failures = 0;
			bHasFailure = false;
		}
		if (FVector::Dist(Location, Anchor) >= MinProgress)
		{
			Anchor = Location;
			TimeSinceProgress = 0.f;
			return ELBStuckResult::None;
		}
		TimeSinceProgress += DeltaTime;
		if (TimeSinceProgress >= StuckSeconds)
		{
			return RegisterFailure(Location);
		}
		return ELBStuckResult::None;
	}

	/** A move failed outright (blocked / off path) or the progress timer ran out. */
	ELBStuckResult RegisterFailure(const FVector& Location)
	{
		++Failures;
		bHasFailure = true;
		FailureLocation = Location;
		Anchor = Location;
		bHasAnchor = true;
		TimeSinceProgress = 0.f;
		return Failures >= 2 ? ELBStuckResult::GiveUp : ELBStuckResult::Repath;
	}

	int32 GetFailures() const { return Failures; }

private:
	FVector Anchor = FVector::ZeroVector;
	FVector FailureLocation = FVector::ZeroVector;
	float TimeSinceProgress = 0.f;
	int32 Failures = 0;
	bool bHasAnchor = false;
	bool bHasFailure = false;
};

/** Search plan: up to MaxVisits designer points within Radius of the search centre, visited nearest-first. */
struct LASTBELL_API FLBSearchPlan
{
	TArray<FVector> Points;
	TArray<bool> Visited;
	int32 MaxVisits = 3;
	int32 VisitedCount = 0;

	/** Keeps the candidates within Radius of Center (3D distance). */
	void Build(const TArray<FVector>& Candidates, const FVector& Center, float Radius, int32 MaxVisitCount);

	/** Nearest unvisited point to From, or INDEX_NONE when the plan is complete. */
	int32 PickNext(const FVector& From) const;

	void MarkVisited(int32 Index);
	bool IsComplete() const { return VisitedCount >= MaxVisits || VisitedCount >= Points.Num(); }
};

namespace LBWardenLogic
{
	/** Highest State.Warden.Stage.N present, 0 when none. */
	LASTBELL_API int32 HighestStage(const FGameplayTagContainer& WorldState);

	/** Stage <= 2 dormant; 3 investigate/suspicious/return; 4 adds patrol and search; 5+ adds chase. */
	LASTBELL_API FLBWardenCaps CapsForStage(int32 Stage);

	/** Is the state legal for the capabilities? Return is legal whenever active. */
	LASTBELL_API bool IsStateAllowed(ELBWardenState State, const FLBWardenCaps& Caps);

	/** Effective sight radius: the stage radius, times the candle multiplier while the candle is lit. */
	LASTBELL_API float EffectiveSightRadius(int32 Stage, bool bCandleLit, const ULBWardenTuningData& Tuning);

	/** Hysteresis: a target already seen stays visible out to Radius + LoseExtra. */
	LASTBELL_API bool IsWithinSightRadius(float Distance, bool bWasVisible, float Radius, float LoseExtra);

	/** Index of the spawn with the highest MinStage not above Stage (first one wins ties), or INDEX_NONE. */
	LASTBELL_API int32 SelectSpawnIndex(const TArray<int32>& MinStages, int32 Stage);

	/** True when Target lies within HalfAngleDegrees of the (unit) view direction from Origin. */
	LASTBELL_API bool IsInsideViewCone(const FVector& Origin, const FVector& ViewDirection, const FVector& Target, float HalfAngleDegrees);

	/** The transition table. Priority: stage gate, attack (resolve / start), sight, noise, then the per-state rules. */
	LASTBELL_API FLBWardenDecision Evaluate(ELBWardenState State, const FLBWardenFacts& Facts, const ULBWardenTuningData& Tuning);

	LASTBELL_API const TCHAR* StateName(ELBWardenState State);
}
