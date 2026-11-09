#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Audio/LBAudioSubsystem.h"
#include "AI/LBWardenTypes.h"
#include "LBWardenAudioComponent.generated.h"

class ALBWarden;
class ULBWardenBrainComponent;

/**
 * The Warden's sounds (plan P16 section 2.5): its breath, steps, chains and robe, and the audible tells. Created in ALBWarden's
 * constructor, so BP_Warden has it without being saved. It plays only while the audio director (ULBAudioSubsystem) is active and the
 * Warden is on the stage (not dormant: visible and in stage 3 or higher); the sounds come from DA_Audio.Warden.
 *
 *   - Breath: three 3D loops (slow for Patrol and Return, fast for Investigate, Suspicious and Search, heavy for Chase and Attack)
 *     that crossfade by state.
 *   - Steps: by distance (FLBAudioWarden::StepStride), a no-repeat step variant at the foot, plus a chain clink above ChainSpeed.
 *   - Robe: a 3D loop whose gain is the speed over RobeFullSpeed.
 *   - Tells: on the brain's OnPlayerSpotted, entering Chase (OnStateChanged), OnAttackWindup, OnPlayerLost and OnPlayerCaught, a no-repeat
 *     variant of the matching set, attached to the Warden. Their attenuation (ATT_LB_WardenTell) is on the sound asset.
 *
 * It listens to the brain, binding lazily the first time the controller has one. It changes nothing about the AI.
 */
UCLASS(ClassGroup = "LastBell", meta = (BlueprintSpawnableComponent))
class LASTBELL_API ULBWardenAudioComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	ULBWardenAudioComponent();

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/** The Warden is on stage and the audio director is running, so its sounds play. */
	UFUNCTION(BlueprintPure, Category = "LastBell|Audio")
	bool IsAudioActive() const { return bAudioActive; }

	/** The eased level of a breath loop: 0 slow, 1 fast, 2 heavy. */
	float GetBreathLevel(int32 Tier) const;

	/** The eased level of the robe loop. */
	float GetRobeLevel() const { return Robe.Level; }

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	UFUNCTION()
	void HandlePlayerSpotted();
	UFUNCTION()
	void HandlePlayerLost();
	UFUNCTION()
	void HandleAttackWindup(float WindupSeconds);
	UFUNCTION()
	void HandlePlayerCaught();
	UFUNCTION()
	void HandleStateChanged(ELBWardenState OldState, ELBWardenState NewState);

	void EnsureBound();
	void Unbind();
	void Silence();
	/** Plays one tell of the set (no repeat) attached to the Warden; does nothing when the Warden is not on stage. */
	void PlayTell(FName Cue, const TArray<TSoftObjectPtr<USoundBase>>& Set, FName Key);
	ULBAudioSubsystem* GetAudio() const;
	bool IsOnStage(const ULBWardenBrainComponent* Brain) const;

	TWeakObjectPtr<ALBWarden> Warden;
	TWeakObjectPtr<ULBWardenBrainComponent> BoundBrain;

	FLBAudioLoop Breath[3];
	FLBAudioLoop Robe;
	float StrideLeft = 0.f;
	FVector LastLocation = FVector::ZeroVector;
	bool bHasLastLocation = false;
	bool bAudioActive = false;
};
