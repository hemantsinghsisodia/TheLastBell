#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "AI/LBWardenAnim.h"
#include "LBWardenAnimInstance.generated.h"

class ULBWardenAnimSet;

/**
 * Parent class of ABP_Warden (P13). It owns no animation: it works out the variables the Animation Blueprint's graph reads
 * (speed, stoop, foot IK, pelvis, physics blend), starts the turn and look-around montages, and plays or freezes the attack
 * montage when BP_Warden asks. The decisions are in LBWardenAnim (unit tested); the numbers are in ULBWardenAnimSet.
 *
 * Threading: NativeUpdateAnimation runs on the game thread and does everything that touches the world (the stoop query, the foot
 * traces, the camera distance, montages). NativeThreadSafeUpdateAnimation only eases the variables towards the targets the game
 * thread left in plain members, so it never reads a UObject.
 *
 * It also works on an actor that is not a pawn (the apparition's Figure): the speed then comes from the actor's movement.
 */
UCLASS(Blueprintable)
class LASTBELL_API ULBWardenAnimInstance : public UAnimInstance
{
	GENERATED_BODY()

public:
	/** DA_WardenAnimSet. Set on the Animation Blueprint's class defaults. With none assigned the class defaults of ULBWardenAnimSet apply and no montage plays. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Warden")
	TObjectPtr<ULBWardenAnimSet> AnimSet;

	// ---- Variables the graph binds to ----

	/** Horizontal speed, cm/s. From the movement component when the owner has one, otherwise from how far the owner moved. */
	UPROPERTY(BlueprintReadOnly, Category = "Warden")
	float GroundSpeed = 0.f;

	/** 0 upright, 1 full stoop: the highest zone amount at the owner's location, eased at StoopEaseRate per second. */
	UPROPERTY(BlueprintReadOnly, Category = "Warden")
	float StoopAlpha = 0.f;

	/** Where the left foot goes, component space (the animated foot's X and Y, the ground's height plus the ankle height). */
	UPROPERTY(BlueprintReadOnly, Category = "Warden")
	FVector FootIKLeft = FVector::ZeroVector;

	UPROPERTY(BlueprintReadOnly, Category = "Warden")
	FVector FootIKRight = FVector::ZeroVector;

	/** Pelvis translation, component space (only Z is used, 0 or negative): the lower foot's drop, at most MaxPelvisDrop. */
	UPROPERTY(BlueprintReadOnly, Category = "Warden")
	FVector PelvisOffset = FVector::ZeroVector;

	/** 1 while the two feet stand on ground that differs by more than 5 cm, easing back to 0 on flat floor. */
	UPROPERTY(BlueprintReadOnly, Category = "Warden")
	float FootIKAlpha = 0.f;

	/** 1 within PhysicsMaxDistance of the player's camera, otherwise 0: the robe and chain physics blend. */
	UPROPERTY(BlueprintReadOnly, Category = "Warden")
	float PhysicsAlpha = 0.f;

	// ---- Called from BP_Warden ----

	/** Plays the Attack montage at AttackPlayRate. */
	UFUNCTION(BlueprintCallable, Category = "Warden")
	void PlayAttack();

	UFUNCTION(BlueprintCallable, Category = "Warden")
	void PlayLookAround();

	/** Freezes the Attack montage where it is. Before its hit time (AttackHitTime) it first lets it get there. */
	UFUNCTION(BlueprintCallable, Category = "Warden")
	void HoldCatchPose();

	/** The assigned anim set, or the class defaults when none is assigned. Never null. */
	const ULBWardenAnimSet& GetAnimSet() const;

protected:
	virtual void NativeInitializeAnimation() override;
	virtual void NativeUpdateAnimation(float DeltaSeconds) override;
	virtual void NativeThreadSafeUpdateAnimation(float DeltaSeconds) override;

private:
	/** Traces under both feet (game thread) and fills the foot, pelvis and alpha targets. */
	void UpdateFootTargets(const AActor& Owner, const UWorld& World);
	/** Turn montage when the owner has been turning on the spot. */
	void UpdateTurn(const AActor& Owner, float DeltaSeconds);
	/** Pauses the held attack once it has reached its hit time. */
	void UpdateCatchHold();

	// Game-thread state.
	FLBYawHistory YawHistory;
	FVector LastLocation = FVector::ZeroVector;
	float LastYaw = 0.f;
	float ClockSeconds = 0.f;
	float TurnCooldownLeft = 0.f;
	bool bHasLastLocation = false;
	bool bHasLastYaw = false;
	bool bHoldingCatchPose = false;
	bool bCatchPoseFrozen = false;

	// Ankle height above the soles in the reference pose (component Z), measured at initialisation.
	float RefFootHeightLeft = 0.f;
	float RefFootHeightRight = 0.f;

	// Targets written by the game thread and eased towards by the thread-safe update. Plain values only.
	float TargetStoop = 0.f;
	FVector TargetFootLeft = FVector::ZeroVector;
	FVector TargetFootRight = FVector::ZeroVector;
	float TargetPelvisZ = 0.f;
	float TargetFootAlpha = 0.f;
	float CachedStoopEaseRate = 3.f;
	float CachedFootInterpSpeed = 15.f;
};
