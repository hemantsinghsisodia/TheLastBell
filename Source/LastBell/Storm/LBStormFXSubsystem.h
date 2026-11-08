#pragma once

#include "CoreMinimal.h"
#include "Math/RandomStream.h"
#include "Subsystems/WorldSubsystem.h"
#include "Storm/LBStormTypes.h"
#include "LBStormFXSubsystem.generated.h"

class ALBLightningBolt;
class ULBStormFXSettings;
class ULBStormSubsystem;
class UMaterialInterface;
class UNiagaraComponent;
class UNiagaraSystem;
class UStaticMesh;

/**
 * The storm's particle FX (plan P15 section 2.3): the rain that follows the camera and the lightning bolts. It reads the storm
 * (ULBStormSubsystem) and draws; it changes nothing in it.
 *
 *   - One UNiagaraComponent from ULBStormFXSettings::RainSystem rides on the camera. Its user parameters (rate, box, fall, wind, splashes,
 *     mist) are written when they change.
 *   - OnLightningStrike draws a bolt from a small pool of ALBLightningBolt cards: a strike with a target puts a bolt from the sky to the
 *     target and sparks at it; any other flash rolls a sky bolt by reason (ULBStormFXSettings::SkyBoltChance). The bolt's brightness is the
 *     material's (MPC LightningFlash); a bolt is hidden when its flash ends or after BoltMaxSeconds.
 *
 * It exists in Game and PIE worlds only. Activation is lazy, in Tick: on the first tick where the storm is active it loads the storm's
 * FXSettings and, if lb.StormFX.Enabled is 1, makes the rain and binds OnLightningStrike. A storm that goes inactive, or the CVar going to 0,
 * switches it off again (the rain is destroyed, the bolts hidden). A world that has begun play with no active storm (the main menu, the test
 * maps) stops the subsystem ticking for good; Rearm() lets a test that activates the storm later start it again.
 */
UCLASS()
class LASTBELL_API ULBStormFXSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	// ---- Subsystem plumbing ---------------------------------------------------------------------------------------------------
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;
	/** Ticks while active or still waiting for the storm's first active tick. */
	virtual bool IsTickable() const override { return !bGaveUp; }

	// ---- Control --------------------------------------------------------------------------------------------------------------

	/** Uses these settings instead of the storm's FXSettings asset (tests, tools). Call Rearm afterwards. */
	void OverrideSettings(ULBStormFXSettings* InSettings);

	/** Starts ticking again after the subsystem gave up on an inactive storm. Tests that spawn the tagged moon after BeginPlay call it. */
	void Rearm();

#if !UE_BUILD_SHIPPING
	/** lb.StormFX.Bolt: a debug flash that draws a sky bolt (Kind 0) or a tower strike at the actor tagged LB_StrikeTarget_Tower (Kind 1). */
	void RequestDebugBolt(int32 Kind);
#endif

	// ---- Queries --------------------------------------------------------------------------------------------------------------

	/** The FX are running: the storm is active, the settings loaded and lb.StormFX.Enabled is 1. */
	UFUNCTION(BlueprintPure, Category = "LastBell|Storm")
	bool IsActive() const { return bActive; }

	/** The rain system's component, or null when inactive or no RainSystem loads. */
	UNiagaraComponent* GetRainComponent() const;

	/** Bolts of the pool that are shown right now (the debug bolt not counted). */
	int32 GetShownBoltCount() const;

	/** The bolt placed last (shown or not), or null. */
	const ALBLightningBolt* GetLatestBolt() const { return LatestBolt.Get(); }

	/** The debug bolt shown by ULBStormFXSettings::DebugBolt, or null. */
	const ALBLightningBolt* GetDebugBolt() const { return DebugBoltActor; }

protected:
	/** Game and PIE worlds only. */
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;

private:
	/** The rain's user parameters as last written, so unchanged values are not written again. */
	struct FRainParams
	{
		float Rate = 0.f;
		float BoxHalf = 0.f;
		float SpawnHeight = 0.f;
		float FallMin = 0.f;
		float FallMax = 0.f;
		FVector Wind = FVector::ZeroVector;
		float SplashRate = 0.f;
		float SplashRadius = 0.f;
		float Mist = 0.f;
	};

	UFUNCTION()
	void HandleLightningStrike(const FLBLightningStrikeInfo& Info);

	bool TryActivate(ULBStormSubsystem& Storm);
	void Deactivate();
	void SpawnBoltPool();
	void HideAllBolts();
	void UpdateRain(const ULBStormSubsystem& Storm, float DeltaSeconds);
	void UpdateBolts(const ULBStormSubsystem& Storm, double Now);
	void UpdateDebugBolt(double Now);
	ALBLightningBolt* AcquireBolt() const;
	ALBLightningBolt* SpawnBolt();
	/** The card transform of a strike bolt to Target: it starts in the sky above it, a little toward the camera (against Direction). */
	FTransform MakeStrikeTransform(const FVector& Target, const FVector& Direction, const FVector& Camera) const;
	/** The camera's location (the player camera, else the last rendered view). False when there is none. */
	bool GetViewLocation(FVector& OutLocation) const;
	bool GetViewDirection(FVector& OutDirection) const;
	AActor* FindDebugTarget();

	UPROPERTY(Transient)
	TObjectPtr<ULBStormFXSettings> Settings;

	/** Set by OverrideSettings; used instead of the storm's FXSettings. */
	UPROPERTY(Transient)
	TObjectPtr<ULBStormFXSettings> SettingsOverride;

	UPROPERTY(Transient)
	TObjectPtr<UNiagaraComponent> RainComponent;

	UPROPERTY(Transient)
	TObjectPtr<UNiagaraSystem> SparksSystem;

	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> BoltMesh;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> BoltMaterial;

	UPROPERTY(Transient)
	TArray<TObjectPtr<ALBLightningBolt>> Bolts;

	UPROPERTY(Transient)
	TObjectPtr<ALBLightningBolt> DebugBoltActor;

	TWeakObjectPtr<ALBLightningBolt> LatestBolt;
	TWeakObjectPtr<ULBStormSubsystem> BoundStorm;
	TWeakObjectPtr<AActor> DebugTarget;

	FRandomStream Stream;
	FRainParams RainParams;
	bool bRainParamsValid = false;

	bool bActive = false;
	/** The subsystem has been active at least once, so it keeps waiting for the storm and the CVar. */
	bool bEverActive = false;
	/** Stops IsTickable: the world began play with no active storm, or the settings did not load. */
	bool bGaveUp = false;
	bool bWarnedNoSettings = false;
	bool bWarnedNoRain = false;
	bool bWarnedNoDebugTarget = false;

	float Mist = 0.f;
	double NextDebugTargetSearch = 0.0;
};
