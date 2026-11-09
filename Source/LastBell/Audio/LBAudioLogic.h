#pragma once

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"
#include "AI/LBWardenTypes.h"
#include "Audio/LBAudioTypes.h"
#include "Storm/LBStormTypes.h"

/**
 * Pure maths of the audio director (plan P16 section 2.7). No UObject, no world: ULBAudioSubsystem gathers the facts and plays the
 * results. Unit tested (LastBell.Audio.Logic.*). The parameter structs are filled from ULBAudioSettings (Make*Params), so the
 * functions here are tested without a data asset.
 */
namespace LBAudioLogic
{
	// ---- Weather ---------------------------------------------------------------------------------------------------------------

	struct FRainMix
	{
		float Out = 0.f;
		float In = 0.f;
	};

	/**
	 * Out = OutGain * E^Power, In = InGain * (1 - E) * RoofRain. E is the player's exposure to the sky (0 sealed, 1 open) and RoofRain
	 * the zone's roof factor (0 none, 1 a roof overhead). E and RoofRain are clamped to 0..1.
	 */
	LASTBELL_API FRainMix RainMix(float Exposure, float RoofRain, float Power, float OutGain, float InGain);

	struct FWindMix
	{
		float Wind = 0.f;
		float Howl = 0.f;
	};

	/**
	 * Wind = OutGain * lerp(MinWind, 1, W) * max(E, InteriorWind); Howl = HowlAmount * W. W is the storm's wind strength 0..1.
	 */
	LASTBELL_API FWindMix WindMix(float Exposure, float WindStrength, float InteriorWind, float HowlAmount, float OutGain, float MinWind);

	// ---- Thunder ---------------------------------------------------------------------------------------------------------------

	/** The thunder variant set. The values are what lb.Audio.Thunder takes: 0 far, 1 mid, 2 near. */
	enum class EThunderSet : uint8
	{
		Far = 0,
		Mid = 1,
		Near = 2
	};

	struct FThunderParams
	{
		/** Delay at brightness 1 (X) and at brightness 0 (Y), seconds. */
		FVector2D Delay = FVector2D(0.6, 4.5);
		float Jitter = 0.4f;
		float NearAt = 0.75f;
		float FarBelow = 0.4f;
	};

	struct FThunderPlan
	{
		EThunderSet Set = EThunderSet::Mid;
		float Delay = 0.f;
		float Volume = 1.f;
	};

	/** The set for a brightness: Near at or above NearAt, Far below FarBelow, Mid between. */
	LASTBELL_API EThunderSet ThunderSetFor(float Brightness, const FThunderParams& Params);

	/**
	 * Thunder for a flash. Delay = lerp(Delay.Y, Delay.X, B) + (2 * Rand - 1) * Jitter, never below 0; Volume = 0.55 + 0.45 B.
	 * Rand is a draw in 0..1. Reason is reserved: all reasons are planned alike today (a flash that strikes a target is made Near
	 * by the caller).
	 */
	LASTBELL_API FThunderPlan PlanThunder(float Brightness, ELBFlashReason Reason, float Rand, const FThunderParams& Params);

	// ---- Music -----------------------------------------------------------------------------------------------------------------

	struct FMusicParams
	{
		float TensionNearDistance = 2500.f;
		int32 MinStage = 3;
		float Patrol = 0.25f;
		float Suspicious = 0.5f;
		float Investigate = 0.6f;
		float Search = 0.8f;
		float Chase = 0.4f;
		float Return = 0.15f;
		float ChaseLevel = 1.f;
	};

	struct FMusicTargets
	{
		float Tension = 0.f;
		float Chase = 0.f;
	};

	/**
	 * The tension and chase layer targets. In Chase and Attack: tension = Params.Chase and chase = ChaseLevel, whatever the stage and
	 * distance (a chase is always heard; it also lets the debug state force a chase at stage 0). In the other states tension is the
	 * state's level when Stage >= MinStage and Distance <= TensionNearDistance, else 0; chase is 0. Dormant is 0, 0.
	 */
	LASTBELL_API FMusicTargets MusicTargets(ELBWardenState State, int32 Stage, float Distance, const FMusicParams& Params);

	// ---- Stress and breathing --------------------------------------------------------------------------------------------------

	struct FStressParams
	{
		float Chase = 1.f;
		float NearSearch = 0.6f;
		/** The Warden is "near" within this distance for NearSearch. */
		float NearDistance = 1500.f;
		float SprintBonus = 0.3f;
		/** How long the sprint bonus lasts after a sprint, seconds (the caller keeps the timer). */
		float SprintSeconds = 3.f;
		/** Fall per second toward a lower target. */
		float Decay = 0.25f;
		/** Rise per second toward a higher target. An addition to the plan, which says only that S rises to its target. */
		float Rise = 0.6f;
		float DarknessLit = 0.15f;
		float DarknessUnlit = 0.55f;
		float CandleOut = 0.35f;
	};

	struct FStressInputs
	{
		ELBWardenState WardenState = ELBWardenState::Dormant;
		float WardenDistance = 1.0e9f;
		/** True while the sprint bonus runs (within SprintSeconds of sprinting). */
		bool bSprintBonus = false;
		/** The current zone's Darkness 0..1. */
		float ZoneDarkness = 0.f;
		bool bCandleLit = true;
		/** The candle went out this step: adds CandleOut to the level at once. */
		bool bCandleOutImpulse = false;
	};

	/** The level S moves toward: the Warden's contribution, raised to the darkness floor, plus the sprint bonus (0..1). */
	LASTBELL_API float StressTarget(const FStressInputs& Inputs, const FStressParams& Params);

	/** One step: the candle-out impulse first, then S rises toward the target at Rise or falls at Decay (never past it). 0..1. */
	LASTBELL_API float Stress(float Prev, const FStressInputs& Inputs, float DeltaSeconds, const FStressParams& Params);

	struct FBreathThresholds
	{
		float Calm = 0.3f;
		float Heavy = 0.55f;
		float Panic = 0.85f;
	};

	/** 0 none, 1 calm, 2 heavy, 3 panic. */
	LASTBELL_API int32 BreathTier(float StressLevel, const FBreathThresholds& Thresholds);

	// ---- Bell ------------------------------------------------------------------------------------------------------------------

	struct FBellPlan
	{
		bool bFound = false;
		int32 Stage = 0;
		int32 Strikes = 0;
		float FirstDelay = 0.f;
		float Spacing = 0.f;
		int32 Drone = -1;

		/** Seconds after the trigger of strike k (0-based). */
		float StrikeDelay(int32 K) const { return FirstDelay + Spacing * static_cast<float>(K); }
	};

	/** The beat for a tag that was added, or bFound false for a tag that is not a beat. The first matching entry wins. */
	LASTBELL_API FBellPlan BellPlan(const FGameplayTag& Tag, const TArray<FLBBellBeat>& Beats);

	/** The "current stage" of ambient tolls: the highest Stage among the beats whose Trigger is in State; 1 when none. */
	LASTBELL_API int32 CurrentBellStage(const TArray<FLBBellBeat>& Beats, const FGameplayTagContainer& State);

	struct FTollParams
	{
		bool bEnabled = true;
		FVector2D Interval = FVector2D(240.0, 420.0);
		FVector2D Strikes = FVector2D(1.0, 2.0);
		float GapAfterBeat = 90.f;
		float MaxTension = 0.5f;
		/** The delay to the next try when a toll is skipped, seconds. */
		FVector2D SkipRetry = FVector2D(30.0, 60.0);
	};

	struct FAmbientTollDecision
	{
		bool bPlay = false;
		int32 Stage = 1;
		int32 Strikes = 0;
		/** The new scheduled time of the next toll (world seconds). A very large number means never. */
		double NextTime = 0.0;
	};

	/**
	 * Called every tick with NextToll, the time the next toll is due (rand(Interval) after the last toll of any kind). Before that
	 * time it returns NextTime = NextToll and nothing else. When due: after Finale (or with tolls disabled) never; during a chase,
	 * while Tension is above MaxTension, or within GapAfterBeat of LastBeat it skips and reschedules after rand(SkipRetry); otherwise
	 * it tolls Stage with rand(Strikes) strikes and schedules the next after rand(Interval). RandA picks the strike count, RandB the
	 * interval or the retry, each a draw in 0..1.
	 */
	LASTBELL_API FAmbientTollDecision AmbientTollPlan(double Now, double NextToll, double LastBeat, bool bChase, float Tension, int32 Stage, bool bFinale,
		float RandA, float RandB, const FTollParams& Params);

	// ---- Helpers ---------------------------------------------------------------------------------------------------------------

	/** An index in 0..Count-1 that is not Last when Count > 1 (Rand in 0..1). Count 1 returns 0, Count 0 or less returns INDEX_NONE. */
	LASTBELL_API int32 PickVariant(int32 Count, int32 Last, float Rand);

	/**
	 * Moves Current toward Target at 1 / InSeconds per second when rising and 1 / OutSeconds when falling, without overshoot. A time
	 * of 0 or less jumps to the target.
	 */
	LASTBELL_API float Ease(float Current, float Target, float InSeconds, float OutSeconds, float DeltaSeconds);
}
