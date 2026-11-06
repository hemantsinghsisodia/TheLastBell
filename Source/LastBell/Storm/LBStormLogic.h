#pragma once

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"
#include "Storm/LBStormTypes.h"

/**
 * Pure maths of the storm and the story lights (P14-1). No UObject, no world: ULBStormSubsystem and ALBStateLightGroup gather
 * the facts and apply the results. Unit tested (LastBell.Storm.Logic.*). Numbers and formulas: Docs/plans/P14_LIGHTING_STORM.md
 * section 5 and 8.
 */
namespace LBStormLogic
{
	// ---------------------------------------------------------------------------------------------------------------------
	// Story intensity (plan 5.2)
	// ---------------------------------------------------------------------------------------------------------------------

	/**
	 * The Intensity of the last step in Steps (list order) whose tag is present (exact match, a parent tag does not count its
	 * children). Invalid tags are skipped. With no step present, DefaultIntensity.
	 */
	LASTBELL_API float StoryIntensity(const TArray<FLBStormStoryStep>& Steps, const FGameplayTagContainer& Present, float DefaultIntensity);

	/** Moves Current toward Target by at most RatePerSecond * DeltaSeconds. */
	LASTBELL_API float MoveTowards(float Current, float Target, float RatePerSecond, float DeltaSeconds);

	// ---------------------------------------------------------------------------------------------------------------------
	// Flash envelope (plan 5.3)
	// ---------------------------------------------------------------------------------------------------------------------

	/** Envelope numbers of the three profiles. Defaults are the plan's. */
	struct FEnvelope
	{
		float SheetAttack = 0.08f;
		float SheetHold = 0.10f;
		float SheetDecay = 0.25f;
		float MultiAttack = 0.03f;
		float MultiHold = 0.04f;
		float MultiDecay = 0.12f;
		float DoubleFirstPeak = 0.55f;
		float TripleFirstPeak = 0.5f;
		float TripleLastPeak = 0.7f;
	};

	struct FPulse
	{
		/** Seconds after the flash's start. */
		float Start = 0.f;
		float Peak = 1.f;
	};

	/** One flash, ready to evaluate. Time zero is the flash's start. */
	struct FFlashShape
	{
		FPulse Pulses[3];
		int32 NumPulses = 1;
		float Attack = 0.08f;
		float Hold = 0.10f;
		float Decay = 0.25f;
		float Brightness = 1.f;
	};

	/** The envelope is over (v < 0.005) this many time constants after the hold. */
	constexpr float DecayTails = 5.3f;

	/**
	 * Builds a flash. Gap1 is the gap between the first and second pulse; Gap2 between the second and third (Triple only).
	 * Auto is not a shape: it is treated as Sheet (the caller resolves it with PickProfile).
	 */
	LASTBELL_API FFlashShape MakeFlash(ELBFlashProfile Profile, float Brightness, float Gap1, float Gap2, const FEnvelope& Envelope);

	/** One pulse's envelope v(u) at u seconds after its start. */
	LASTBELL_API float EvaluatePulse(float U, float Attack, float Hold, float Decay);

	/** F(t) = min(1, Brightness * max over pulses of Peak * v), T seconds after the flash's start. 0 before the start. */
	LASTBELL_API float EvaluateFlash(const FFlashShape& Shape, float T);

	/** Seconds from the start until the flash is over: last pulse start + Attack + Hold + 5.3 * Decay. */
	LASTBELL_API float FlashDuration(const FFlashShape& Shape);

	/** Chooses Sheet / Double / Triple by weight. Roll01 in [0, 1). */
	LASTBELL_API ELBFlashProfile PickProfile(float Roll01, float WeightSheet, float WeightDouble, float WeightTriple);

	// ---------------------------------------------------------------------------------------------------------------------
	// Schedule (plan 5.3)
	// ---------------------------------------------------------------------------------------------------------------------

	struct FScheduleParams
	{
		float MinIntervalLow = 30.f;
		float MinIntervalHigh = 6.f;
		float MaxIntervalLow = 60.f;
		float MaxIntervalHigh = 14.f;
		float FirstFlashScale = 0.5f;
	};

	/** The lower and upper bound of the interval to the next ambient flash at intensity I (0..1). */
	LASTBELL_API void IntervalBounds(float Intensity, const FScheduleParams& Params, float& OutMin, float& OutMax);

	/** Uniform in the bounds (Roll01 in [0, 1]). The first flash after BeginPlay is scaled by FirstFlashScale. */
	LASTBELL_API float NextInterval(float Intensity, float Roll01, const FScheduleParams& Params, bool bFirst);

	/** The earliest start of a flash asked for at RequestedStart: not before BusyUntil + MinGap. */
	LASTBELL_API float EarliestStart(float RequestedStart, float BusyUntil, float MinGap);

	/** lerp(BrightnessMin, 1, Roll01) * lerp(BrightnessFloorLow, 1, Intensity). */
	LASTBELL_API float AmbientBrightness(float Roll01, float Intensity, float BrightnessMin, float BrightnessFloorLow);

	/** Unit vector from an azimuth (degrees, 0 = +X) and an elevation above the horizon (degrees). */
	LASTBELL_API FVector DirectionFromAngles(float AzimuthDegrees, float ElevationDegrees);

	/** The camera-to-Warden direction, flattened, then raised by RaiseDegrees above the horizon. */
	LASTBELL_API FVector RevealDirection(const FVector& CameraToTarget, float RaiseDegrees);

	// ---------------------------------------------------------------------------------------------------------------------
	// Wind (plan 5.5)
	// ---------------------------------------------------------------------------------------------------------------------

	struct FWindParams
	{
		float BaseLow = 0.2f;
		float BaseHigh = 0.65f;
		float GustLow = 0.15f;
		float GustHigh = 0.4f;
		float GustFrequency = 0.12f;
		float PhaseSpeedLow = 1.2f;
		float PhaseSpeedHigh = 2.4f;
	};

	/** The phase wraps at 100 full turns. The material only uses whole multiples of the phase, so the wrap never shows. */
	constexpr float WindPhaseWrap = 100.f * 2.f * UE_PI;

	/** clamp(Base + Gust, 0, 1) at intensity I and game time T seconds. */
	LASTBELL_API float WindStrength(float Intensity, float TimeSeconds, const FWindParams& Params);

	/** Phase + dt * lerp(PhaseSpeedLow, PhaseSpeedHigh, Strength), wrapped into [0, WindPhaseWrap). */
	LASTBELL_API float AdvanceWindPhase(float Phase, float Strength, float DeltaSeconds, const FWindParams& Params);

	// ---------------------------------------------------------------------------------------------------------------------
	// Exposure (plan 5.1)
	// ---------------------------------------------------------------------------------------------------------------------

	/** A zone that contains the point. */
	struct FExposureEntry
	{
		float Exposure = 1.f;
		int32 Priority = 0;
	};

	/** Exposure of the highest-priority zone; on a tie the lowest exposure. With no zone, DefaultExposure. Result in [0, 1]. */
	LASTBELL_API float ResolveExposure(TConstArrayView<FExposureEntry> ContainingZones, float DefaultExposure);

	// ---------------------------------------------------------------------------------------------------------------------
	// Warden reveal (plan 5.6a)
	// ---------------------------------------------------------------------------------------------------------------------

	/** The first failing condition, in the order the debug readout reports them. */
	enum class ERevealCheck : uint8
	{
		Reveal,
		Disabled,
		LowIntensity,
		NoWarden,
		Dormant,
		TooClose,
		TooFar,
		OutOfCone,
		Blocked,
		LowExposure,
		Cooldown,
		Busy
	};

	/** Everything ShouldReveal looks at, as plain numbers. */
	struct FRevealInputs
	{
		bool bEnabled = true;
		float Intensity = 1.f;
		float MinIntensity = 0.4f;
		bool bWardenExists = true;
		bool bWardenDormant = false;
		/** Camera to the Warden's head point. */
		float Distance = 2000.f;
		float MinDistance = 800.f;
		float MaxDistance = 4000.f;
		/** Angle between the camera's forward and the direction to the head point. */
		float AngleDegrees = 0.f;
		float ConeDegrees = 30.f;
		/** The visibility trace from the camera to the head point is clear. */
		bool bLineClear = true;
		float Exposure = 1.f;
		float MinExposure = 0.5f;
		float SecondsSinceLastReveal = 1.0e9f;
		float CooldownSeconds = 30.f;
		/** A flash is running or pending. */
		bool bFlashBusy = false;
	};

	/** True when a Warden reveal flash should be requested. OutCheck says which condition stopped it (Reveal when none did). */
	LASTBELL_API bool ShouldReveal(const FRevealInputs& Inputs, ERevealCheck& OutCheck);

	LASTBELL_API const TCHAR* RevealCheckName(ERevealCheck Check);

	// ---------------------------------------------------------------------------------------------------------------------
	// Story light rules (plan 8)
	// ---------------------------------------------------------------------------------------------------------------------

	/** The rule in force: what the group's lights should do right now. */
	struct FLightRule
	{
		ELBLightStateMode Mode = ELBLightStateMode::On;
		float Scale = 1.f;
		float FlickerAmount = 0.f;
		float FlickerSpeed = 0.f;

		bool operator==(const FLightRule& Other) const
		{
			return Mode == Other.Mode && Scale == Other.Scale && FlickerAmount == Other.FlickerAmount && FlickerSpeed == Other.FlickerSpeed;
		}
	};

	/** The last rule whose tag is present (exact match). With none: On at scale 1. */
	LASTBELL_API FLightRule SelectLightRule(const TArray<FLBLightStateRule>& Rules, const FGameplayTagContainer& Present);

	/**
	 * The intensity scale a rule asks for at game time T. On: 1. Off: 0. Dim: Scale. Flicker: Scale * (1 - Amount * (0.5 + 0.5 *
	 * Perlin(T * Speed + Seed))), which stays inside [Scale * (1 - Amount), Scale].
	 */
	LASTBELL_API float LightScaleAt(const FLightRule& Rule, float TimeSeconds, float Seed);

	/** 0.6 + 0.4 * Perlin(T * 9), clamped to [0, 1]: the gutter a light shows while it fades. */
	LASTBELL_API float GutterNoise(float TimeSeconds);

	/**
	 * The scale during a fade from From to To at Alpha (0..1): the straight blend times a gutter that is strongest mid-fade and
	 * gone at both ends (so the fade neither starts nor ends with a pop).
	 */
	LASTBELL_API float FadeScale(float From, float To, float Alpha, float TimeSeconds);
}
