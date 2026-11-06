#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "Storm/LBStormLogic.h"
#include "Storm/LBStormTypes.h"
#include "LBStormSettings.generated.h"

class UMaterialParameterCollection;

/**
 * Every number of the storm (plan P14 section 5), as one data asset: DA_StormSettings in /Game/LastBell/Data. The defaults here are
 * the plan's (flash preset B). ULBStormSubsystem reads the asset through its pointer every frame, so an edit in the Details panel
 * (or over MCP) during PIE shows at once.
 *
 * The two tag arrays are empty by default, because the Gameplay Tags from the ini may not be registered yet when the class default
 * object is built. FillPlanTagDefaults() fills them at runtime; call it once when creating the asset (or on a transient copy in a
 * test). Never save the asset with DebugFreezeFlash or DebugIntensityOverride other than -1.
 */
UCLASS(BlueprintType)
class LASTBELL_API ULBStormSettings : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	// ---- Assets ---------------------------------------------------------------------------------------------------------------

	/** MPC_LB_Storm. Unset: the subsystem skips the material parameter writes. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Assets")
	TSoftObjectPtr<UMaterialParameterCollection> Collection;

	// ---- Story intensity (5.2) ------------------------------------------------------------------------------------------------

	/** In story order; the last entry whose tag is present sets the target. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story")
	TArray<FLBStormStoryStep> StoryIntensity;

	/** The target when no StoryIntensity tag is present. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story", meta = (ClampMin = "0", ClampMax = "1"))
	float DefaultIntensity = 0.55f;

	/** How fast the live intensity moves toward the target (per second). 0.02 means 0.5 to 1.0 takes 25 s. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story", meta = (ClampMin = "0"))
	float IntensityRatePerSecond = 0.02f;

	// ---- Exposure (5.1) -------------------------------------------------------------------------------------------------------

	/** Exposure outside every zone: the open sky. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Exposure", meta = (ClampMin = "0", ClampMax = "1"))
	float DefaultExposure = 1.f;

	/** How often the player's exposure is sampled (seconds). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Exposure", meta = (ClampMin = "0.05", Units = "s"))
	float ExposureSampleSeconds = 0.25f;

	// ---- Lightning schedule (5.3) ---------------------------------------------------------------------------------------------

	/** Turn off to stop the random flashes (tests do). Scripted strikes, reveals and apparitions still happen. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schedule")
	bool bAmbientFlashes = true;

	/** Seed of the storm's random stream. 0 seeds from the time; tests use 1401. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schedule")
	int32 RandomSeed = 0;

	/** Interval to the next ambient flash: uniform in [lerp(MinIntervalLow, MinIntervalHigh, I), lerp(MaxIntervalLow, MaxIntervalHigh, I)]. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schedule", meta = (ClampMin = "0", Units = "s"))
	float MinIntervalLow = 30.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schedule", meta = (ClampMin = "0", Units = "s"))
	float MinIntervalHigh = 6.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schedule", meta = (ClampMin = "0", Units = "s"))
	float MaxIntervalLow = 60.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schedule", meta = (ClampMin = "0", Units = "s"))
	float MaxIntervalHigh = 14.f;

	/** The first ambient flash after BeginPlay waits this much of its interval. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schedule", meta = (ClampMin = "0"))
	float FirstFlashScale = 0.5f;

	/** Any flash is kept at least this long after the previous one ended (strikes of one scripted sequence excepted). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schedule", meta = (ClampMin = "0", Units = "s"))
	float MinGapSeconds = 2.5f;

	/** Profile weights of an ambient flash. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schedule", meta = (ClampMin = "0"))
	float WeightSheet = 0.5f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schedule", meta = (ClampMin = "0"))
	float WeightDouble = 0.35f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schedule", meta = (ClampMin = "0"))
	float WeightTriple = 0.15f;

	/** Ambient brightness: lerp(BrightnessMin, 1, random) * lerp(BrightnessFloorLow, 1, I). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schedule", meta = (ClampMin = "0", ClampMax = "1"))
	float BrightnessMin = 0.55f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schedule", meta = (ClampMin = "0", ClampMax = "1"))
	float BrightnessFloorLow = 0.7f;

	/** Elevation range (degrees above the horizon) of the bright patch in the clouds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schedule", meta = (ClampMin = "0", ClampMax = "90", Units = "deg"))
	float ElevationMin = 15.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Schedule", meta = (ClampMin = "0", ClampMax = "90", Units = "deg"))
	float ElevationMax = 35.f;

	// ---- Envelope (5.3) -------------------------------------------------------------------------------------------------------

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Envelope", meta = (ClampMin = "0.001", Units = "s"))
	float SheetAttack = 0.08f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Envelope", meta = (ClampMin = "0", Units = "s"))
	float SheetHold = 0.10f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Envelope", meta = (ClampMin = "0.001", Units = "s"))
	float SheetDecay = 0.25f;

	/** Attack / hold / decay of every pulse of a Double or Triple flash. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Envelope", meta = (ClampMin = "0.001", Units = "s"))
	float MultiAttack = 0.03f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Envelope", meta = (ClampMin = "0", Units = "s"))
	float MultiHold = 0.04f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Envelope", meta = (ClampMin = "0.001", Units = "s"))
	float MultiDecay = 0.12f;

	/** Peak of the first pulse of a Double, and of the first and last pulse of a Triple (the middle pulse of both is 1). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Envelope", meta = (ClampMin = "0", ClampMax = "1"))
	float DoubleFirstPeak = 0.55f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Envelope", meta = (ClampMin = "0", ClampMax = "1"))
	float TripleFirstPeak = 0.5f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Envelope", meta = (ClampMin = "0", ClampMax = "1"))
	float TripleLastPeak = 0.7f;

	/** The gaps between the pulses of a Double or Triple are uniform in [GapMin, GapMax]. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Envelope", meta = (ClampMin = "0", Units = "s"))
	float GapMin = 0.07f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Envelope", meta = (ClampMin = "0", Units = "s"))
	float GapMax = 0.16f;

	// ---- Flash output (5.4, preset B) -----------------------------------------------------------------------------------------

	/** The moon (LB_StormMoon) gets base + FlashLux * F. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flash Output", meta = (ClampMin = "0"))
	float FlashLux = 8.f;

	/** LB_StormMoonSpot lights: base * (1 + SpotFlashGain * F). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flash Output", meta = (ClampMin = "0"))
	float SpotFlashGain = 3.f;

	/** LB_StormFill lights: base * (1 + FillFlashGain * F). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flash Output", meta = (ClampMin = "0"))
	float FillFlashGain = 1.5f;

	/** LB_StormSky (the SkyLight): base * (1 + SkyFlashGain * F). Set 0 if Lumen's bounce smears (R-59). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flash Output", meta = (ClampMin = "0"))
	float SkyFlashGain = 0.6f;

	/** Copied to the MPC every frame for the materials. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flash Output|Materials")
	float DomeFlashGain = 6.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flash Output|Materials")
	float DomeFlashAdd = 0.05f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flash Output|Materials")
	float GlassFlashGain = 2.5f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flash Output|Materials")
	float ShaftFlashGain = 3.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flash Output|Materials")
	float PoolFlashGain = 2.5f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flash Output|Materials")
	float RevealGain = 4.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flash Output|Materials")
	float RevealEmissive = 3.f;

	/** MPC FlashTint: the colour of lightning. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flash Output|Materials")
	FLinearColor FlashTint = FLinearColor(0.75f, 0.82f, 1.f, 1.f);

	// ---- Wind (5.5) -----------------------------------------------------------------------------------------------------------

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Wind", meta = (ClampMin = "0", ClampMax = "1"))
	float WindBaseLow = 0.2f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Wind", meta = (ClampMin = "0", ClampMax = "1"))
	float WindBaseHigh = 0.65f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Wind", meta = (ClampMin = "0", ClampMax = "1"))
	float GustLow = 0.15f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Wind", meta = (ClampMin = "0", ClampMax = "1"))
	float GustHigh = 0.4f;

	/** Perlin input per second of game time. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Wind", meta = (ClampMin = "0"))
	float GustFrequency = 0.12f;

	/** Phase speed (rad/s) at wind strength 0 and 1. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Wind", meta = (ClampMin = "0"))
	float PhaseSpeedLow = 1.2f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Wind", meta = (ClampMin = "0"))
	float PhaseSpeedHigh = 2.4f;

	/** The direction the wind blows toward (normalised before it is written). West-south-west by default. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Wind")
	FVector WindDirection = FVector(0.87, 0.5, 0.0);

	// ---- Reveals (5.6a) -------------------------------------------------------------------------------------------------------

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Reveal")
	bool bRevealEnabled = true;

	/** How often the reveal rule is checked. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Reveal", meta = (ClampMin = "0.1", Units = "Hz"))
	float RevealCheckHz = 5.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Reveal", meta = (ClampMin = "0", ClampMax = "1"))
	float RevealMinIntensity = 0.4f;

	/** The head point is the Warden's location plus this much on Z. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Reveal", meta = (Units = "cm"))
	float WardenHeadOffsetZ = 140.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Reveal", meta = (ClampMin = "0", Units = "cm"))
	float RevealMinDistance = 800.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Reveal", meta = (ClampMin = "0", Units = "cm"))
	float RevealMaxDistance = 4000.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Reveal", meta = (ClampMin = "1", ClampMax = "90", Units = "deg"))
	float RevealConeDegrees = 30.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Reveal", meta = (ClampMin = "0", ClampMax = "1"))
	float RevealMinExposure = 0.5f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Reveal", meta = (ClampMin = "0", Units = "s"))
	float RevealCooldownSeconds = 30.f;

	/** The reveal flash starts after a delay uniform in [RevealDelayMin, RevealDelayMax]. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Reveal", meta = (ClampMin = "0", Units = "s"))
	float RevealDelayMin = 0.3f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Reveal", meta = (ClampMin = "0", Units = "s"))
	float RevealDelayMax = 0.9f;

	/** The bright patch's direction is camera-to-Warden, flattened, then raised by this much. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Reveal", meta = (ClampMin = "0", ClampMax = "90", Units = "deg"))
	float RevealRaiseDegrees = 20.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Reveal", meta = (ClampMin = "0", ClampMax = "1"))
	float RevealBrightness = 1.f;

	// ---- Scripted strikes (5.6b) ----------------------------------------------------------------------------------------------

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Scripted")
	TArray<FLBStormStrike> ScriptedStrikes;

	// ---- Debug (live tuning) --------------------------------------------------------------------------------------------------

	/** 0..1 holds the flash value F there and pauses the schedule; -1 = off. Never save with a value other than -1. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Debug", meta = (ClampMin = "-1", ClampMax = "1"))
	float DebugFreezeFlash = -1.f;

	/** 0..1 replaces the story intensity (and snaps to it); -1 = off. Never save with a value other than -1. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Debug", meta = (ClampMin = "-1", ClampMax = "1"))
	float DebugIntensityOverride = -1.f;

	/**
	 * Fills StoryIntensity and ScriptedStrikes from the plan's tables (5.2 and 5.6b), replacing what is there. A tag the project
	 * does not know is skipped with a warning. Call it when creating DA_StormSettings.
	 */
	UFUNCTION(BlueprintCallable, CallInEditor, Category = "Storm")
	void FillPlanTagDefaults();

	/** The envelope numbers for LBStormLogic. */
	LBStormLogic::FEnvelope MakeEnvelope() const;
	LBStormLogic::FScheduleParams MakeScheduleParams() const;
	LBStormLogic::FWindParams MakeWindParams() const;
};
