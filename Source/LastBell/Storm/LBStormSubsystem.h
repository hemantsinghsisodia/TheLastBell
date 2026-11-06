#pragma once

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"
#include "Subsystems/WorldSubsystem.h"
#include "Storm/LBStormLogic.h"
#include "Storm/LBStormTypes.h"
#include "LBStormSubsystem.generated.h"

class ALBStormZone;
class ALBWarden;
class ULBStormSettings;
class ULightComponentBase;
class UMaterialParameterCollection;

/** Fired at the first pulse of every flash. Phase 16 hangs thunder on it. */
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FLBLightningFlashSignature, float, Brightness, ELBFlashReason, Reason);

/**
 * The storm controller (P14, Docs/plans/P14_LIGHTING_STORM.md section 4 and 5). It owns:
 *   - the storm intensity, which follows the story tags;
 *   - the lightning: an ambient schedule, scripted strikes on tags, Warden reveals, flashes requested by other systems;
 *   - the flash output: it raises the tagged moon, moonlight spots, fill and sky lights while a flash runs;
 *   - the wind (strength and phase);
 *   - the exposure of the player's position, from ALBStormZone boxes;
 *   - the material parameter collection (MPC_LB_Storm) the sky, glass, shafts, foliage and reveal decals read.
 *
 * It exists in Game and PIE worlds only, and is active only when the level has an ADirectionalLight tagged LB_StormMoon and the
 * settings asset (ULBGameSettings::StormSettings) loads. Otherwise it does nothing: no tick, no writes. The numbers are in
 * ULBStormSettings and are read every frame. The maths is in LBStormLogic (unit tested).
 *
 * Linked lights are found by actor tag at BeginPlay: LB_StormMoon (the moon: base + FlashLux * F), LB_StormMoonSpot (base * (1 +
 * SpotFlashGain * F)), LB_StormFill (FillFlashGain) and LB_StormSky (SkyFlashGain). Intensities are written only while a flash
 * runs, plus once when it ends.
 */
UCLASS()
class LASTBELL_API ULBStormSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	// ---- Subsystem plumbing ---------------------------------------------------------------------------------------------------
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;
	virtual bool IsTickable() const override { return bActive; }

	// ---- Control --------------------------------------------------------------------------------------------------------------

	/**
	 * Asks for a flash Delay seconds from now. It is kept at least MinGapSeconds after the previous flash ended (a request inside
	 * the gap waits for it). Does nothing while the storm is inactive or lb.Storm.Enabled is 0.
	 */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Storm")
	void RequestFlash(float Brightness, float DelaySeconds, ELBFlashReason Reason, ELBFlashProfile Profile = ELBFlashProfile::Auto);

	/** As RequestFlash, with the direction of the bright patch in the clouds (a unit vector toward it). */
	void RequestFlashDirected(float Brightness, float DelaySeconds, ELBFlashReason Reason, ELBFlashProfile Profile, const FVector& Direction);

	/**
	 * Rescans the linked lights (by actor tag) and runs the activation again: no tagged moon makes the subsystem inactive, a moon
	 * and settings make it active. BeginPlay calls it; a test that spawns a tagged moon later calls it too.
	 */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Storm")
	void RefreshLinkedLights();

	/** Uses these settings instead of the configured asset (tests, tools). Call RefreshLinkedLights afterwards to activate. */
	void OverrideSettings(ULBStormSettings* InSettings);

	void RegisterZone(ALBStormZone* Zone);
	void UnregisterZone(ALBStormZone* Zone);

	/** lb.Storm.Intensity: replaces the story intensity (and snaps to it); negative clears. */
	void SetConsoleIntensityOverride(float Value) { ConsoleIntensityOverride = Value; }

	/** lb.Storm.Freeze: holds the flash value there and pauses the schedule; negative clears. */
	void SetConsoleFreeze(float Value) { ConsoleFreeze = Value; }

	// ---- Queries --------------------------------------------------------------------------------------------------------------

	UFUNCTION(BlueprintPure, Category = "LastBell|Storm")
	bool IsActive() const { return bActive; }

	/** The live storm intensity, 0..1. */
	UFUNCTION(BlueprintPure, Category = "LastBell|Storm")
	float GetStormIntensity() const { return Intensity; }

	/** The intensity the story (or an override) asks for. */
	UFUNCTION(BlueprintPure, Category = "LastBell|Storm")
	float GetTargetIntensity() const { return TargetIntensity; }

	/** How exposed to the sky a point is, 0..1: the highest-priority ALBStormZone containing it, else DefaultExposure. */
	UFUNCTION(BlueprintPure, Category = "LastBell|Storm")
	float GetExposureAt(const FVector& WorldLocation) const;

	/** The exposure at the camera, sampled every 0.25 s. */
	UFUNCTION(BlueprintPure, Category = "LastBell|Storm")
	float GetPlayerExposure() const { return PlayerExposure; }

	/** F, the current flash value 0..1 (what MPC LightningFlash holds). */
	UFUNCTION(BlueprintPure, Category = "LastBell|Storm")
	float GetLightningFlash() const { return CurrentFlash; }

	UFUNCTION(BlueprintPure, Category = "LastBell|Storm")
	float GetWindStrength() const { return CurrentWind; }

	/** A flash is running or pending (including strikes waiting for the player's look). */
	UFUNCTION(BlueprintPure, Category = "LastBell|Storm")
	bool IsFlashBusy() const { return Pending.Num() > 0 || Active.Num() > 0 || LookWaits.Num() > 0; }

	/** Seconds until the next ambient flash is due, or a negative number when none is armed. */
	float GetSecondsToNextAmbient() const;

	/** The last decision of the Warden reveal rule and the condition that stopped it (Reveal when none did). */
	LBStormLogic::ERevealCheck GetLastRevealCheck() const { return LastRevealCheck; }

	int32 GetLinkedLightCount() const { return Linked.Num(); }
	int32 GetZoneCount() const { return Zones.Num(); }
	const ULBStormSettings* GetSettings() const { return Settings; }

	/** Fired at the first pulse of every flash. */
	UPROPERTY(BlueprintAssignable, Category = "LastBell|Storm")
	FLBLightningFlashSignature OnLightningFlash;

protected:
	/** Game and PIE worlds only. */
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;

private:
	enum class ELinkKind : uint8 { Moon, Spot, Fill, Sky };

	struct FLinkedLight
	{
		TWeakObjectPtr<ULightComponentBase> Component;
		ELinkKind Kind = ELinkKind::Spot;
		float Base = 0.f;
	};

	/** A flash waiting for its start time (Pending) or running (Active). Time zero of Shape is Start. */
	struct FFlashInstance
	{
		LBStormLogic::FFlashShape Shape;
		double Start = 0.0;
		float Duration = 0.f;
		float Brightness = 1.f;
		ELBFlashReason Reason = ELBFlashReason::Ambient;
		FVector Direction = FVector::UpVector;
	};

	/** A look-gated strike waiting for the player to look at its target. */
	struct FLookWait
	{
		int32 StrikeIndex = INDEX_NONE;
		double Expire = 0.0;
	};

	UFUNCTION()
	void HandleStateChanged(FGameplayTag Tag, bool bAdded);

	UFUNCTION()
	void HandleStateReplaced();

	void Deactivate();
	void BindWorldState();
	void UnbindWorldState();
	void ResetRuntime();
	void RestoreLights();
	void ApplyLights(float Flash);

	float ComputeTargetIntensity() const;
	void UpdateIntensity(float DeltaSeconds);
	void UpdateWind(float DeltaSeconds, double Now);
	void UpdateExposure(double Now);

	/** Queues a flash starting at Start (absolute world time) and extends BusyUntil. Resolves Auto and draws the gaps. */
	void QueueFlash(float Brightness, double Start, ELBFlashReason Reason, ELBFlashProfile Profile, const FVector& Direction);
	/** The start time of a flash asked for Delay from now: not before the previous flash ended plus the minimum gap. */
	double ScheduledStart(double Now, float Delay) const;
	FVector RandomFlashDirection();
	void FireStrike(int32 StrikeIndex, const FVector& TowardDirection, bool bHasDirection);
	void UpdateLookWaits(double Now);
	void StartDueFlashes(double Now);
	void UpdateAmbient(double Now, bool bFrozen);
	void CheckReveal(double Now);
	bool GetCamera(FVector& OutLocation, FRotator& OutRotation) const;
	void WriteCollection();
	void DrawDebug(double Now);

	UPROPERTY(Transient)
	TObjectPtr<ULBStormSettings> Settings;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialParameterCollection> Collection;

	TArray<FLinkedLight> Linked;
	TArray<TWeakObjectPtr<ALBStormZone>> Zones;
	TWeakObjectPtr<ALBWarden> CachedWarden;

	TArray<FFlashInstance> Pending;
	TArray<FFlashInstance> Active;
	TArray<FLookWait> LookWaits;

	FRandomStream Stream;

	bool bActive = false;
	bool bBoundWorldState = false;
	bool bWarnedNoSettings = false;

	float Intensity = 0.55f;
	float TargetIntensity = 0.55f;
	float CurrentFlash = 0.f;
	float LastAppliedFlash = 0.f;
	float CurrentWind = 0.f;
	float WindPhase = 0.f;
	float PlayerExposure = 1.f;
	FVector FlashDirection = FVector(0.5, 0.5, 0.7);

	/** World time when the last scheduled flash ends. */
	double BusyUntil = -1.0e9;
	double NextAmbientAt = 0.0;
	bool bAmbientArmed = false;
	bool bFirstAmbient = true;
	double NextRevealCheckAt = 0.0;
	double LastRevealTime = -1.0e9;
	double NextExposureAt = 0.0;
	LBStormLogic::ERevealCheck LastRevealCheck = LBStormLogic::ERevealCheck::NoWarden;

	float ConsoleIntensityOverride = -1.f;
	float ConsoleFreeze = -1.f;
	int32 WriteFailures = 0;
};
