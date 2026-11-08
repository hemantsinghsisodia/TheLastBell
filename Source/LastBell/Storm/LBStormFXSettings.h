#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "Storm/LBStormTypes.h"
#include "LBStormFXSettings.generated.h"

class UMaterialInterface;
class UNiagaraSystem;
class UStaticMesh;

/**
 * Every number and asset of the storm's particle FX (plan P15 section 2.2), as one data asset: DA_StormFX in /Game/LastBell/Data,
 * linked from ULBStormSettings::FXSettings. ULBStormFXSubsystem reads it through its pointer every frame, so an edit in the Details
 * panel (or over MCP) during PIE shows at once (the bolt pool size and the assets are read when the subsystem activates).
 *
 * The assets are soft pointers, never hard references. Never save the asset with DebugBolt other than -1.
 */
UCLASS(BlueprintType)
class LASTBELL_API ULBStormFXSettings : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	ULBStormFXSettings();

	// ---- Assets ---------------------------------------------------------------------------------------------------------------

	/** NS_LB_Rain: one system, attached to the camera by the subsystem. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Assets")
	TSoftObjectPtr<UNiagaraSystem> RainSystem;

	/** NS_LB_StrikeSparks: spawned at the target of a tower strike. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Assets")
	TSoftObjectPtr<UNiagaraSystem> StrikeSparksSystem;

	/** SM_LB_FX_BoltCard: a 100 x 100 cm plane in XZ, pivot at the top centre, extending down -Z, normal +Y. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Assets")
	TSoftObjectPtr<UStaticMesh> BoltMesh;

	/** MI_LB_Bolt: reads MPC_LB_Storm.LightningFlash, so a bolt is invisible at rest and flickers with the pulses. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Assets")
	TSoftObjectPtr<UMaterialInterface> BoltMaterial;

	// ---- Rain -----------------------------------------------------------------------------------------------------------------

	/** Rain on or off. Off sets the spawn rates to zero. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rain")
	bool bRain = true;

	/** User.RainRate. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rain", meta = (ClampMin = "0", Units = "Hz"))
	float RainSpawnRate = 35000.f;

	/** User.BoxHalf: half the rain box, horizontally. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rain", meta = (ClampMin = "0", Units = "cm"))
	float RainBoxHalfXY = 1800.f;

	/** User.SpawnHeight: where the drops start, above the camera. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rain", meta = (ClampMin = "0", Units = "cm"))
	float RainSpawnHeight = 2500.f;

	/** User.FallMin (X) and User.FallMax (Y), in cm/s. The splashes fall at the same speed. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rain")
	FVector2D RainFallSpeed = FVector2D(1100.0, 1400.0);

	/** User.Wind = WindDirection * WindStrength * RainWindLean (the storm's wind, horizontal). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rain", meta = (ClampMin = "0", Units = "cm/s"))
	float RainWindLean = 500.f;

	/** User.SplashRate. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rain", meta = (ClampMin = "0", Units = "Hz"))
	float SplashRate = 2500.f;

	/** User.SplashRadius. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rain", meta = (ClampMin = "0", Units = "cm"))
	float SplashRadius = 1200.f;

	/** User.Mist = smoothstep(Min - 0.1, Min + 0.1, the player's exposure), eased at 1 per second. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rain", meta = (ClampMin = "0", ClampMax = "1"))
	float MistMinExposure = 0.6f;

	// ---- Bolts ----------------------------------------------------------------------------------------------------------------

	/**
	 * The chance that a flash of this reason draws a sky bolt. A flash that strikes a target always draws its bolt. A reason that is
	 * missing from the map never draws one.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bolts")
	TMap<ELBFlashReason, float> SkyBoltChance;

	/** Horizontal distance from the camera to a sky bolt. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bolts", meta = (ClampMin = "0", Units = "cm"))
	float SkyBoltDistance = 60000.f;

	/** The top of a sky bolt, above the camera. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bolts", meta = (ClampMin = "0", Units = "cm"))
	float SkyBoltTopHeight = 22000.f;

	/** Min (X) and max (Y) length of a sky bolt, in cm; random per bolt. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bolts")
	FVector2D SkyBoltLength = FVector2D(16000.0, 26000.0);

	/** Card width divided by length. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bolts", meta = (ClampMin = "0.01"))
	float BoltAspect = 0.35f;

	/** A tower strike starts this high above its target. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bolts", meta = (ClampMin = "0", Units = "cm"))
	float StrikeSkyHeight = 12000.f;

	/** A tower strike starts this far toward the camera (horizontally, against the flash direction). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bolts", meta = (ClampMin = "0", Units = "cm"))
	float StrikeSkyOffset = 2500.f;

	/** Card width of a tower strike. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bolts", meta = (ClampMin = "1", Units = "cm"))
	float StrikeWidth = 1400.f;

	/** Cells in T_LB_FX_Bolts (4 x 2). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bolts", meta = (ClampMin = "1"))
	int32 BoltAtlasCount = 8;

	/** A bolt is hidden when its flash ends, or after this long, whichever comes first. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bolts", meta = (ClampMin = "0.1", Units = "s"))
	float BoltMaxSeconds = 2.5f;

	/** Bolt actors kept. Read when the subsystem activates. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bolts", meta = (ClampMin = "1", ClampMax = "16"))
	int32 BoltPool = 4;

	// ---- Debug (live tuning) --------------------------------------------------------------------------------------------------

	/**
	 * -1 none, 0 a sky bolt, 1 a tower strike (at the actor tagged LB_StrikeTarget_Tower). While 0 or 1 one bolt is shown every frame
	 * (for captures, with DebugFreezeFlash). Never save with a value other than -1.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Debug", meta = (ClampMin = "-1", ClampMax = "1"))
	int32 DebugBolt = -1;
};
