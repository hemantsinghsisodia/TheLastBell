#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "Character/LBPlayerTypes.h"
#include "LBPlayerTuningData.generated.h"

class UCharacterMovementComponent;

/** Every player-feel tunable. Defaults are the Phase 3 feel targets and double as the safe fallback when no asset is assigned. */
UCLASS(BlueprintType)
class LASTBELL_API ULBPlayerTuningData : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	// ---- Movement ----
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Movement", meta = (ClampMin = "0"))
	float WalkSpeed = 260.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Movement", meta = (ClampMin = "0"))
	float SprintSpeed = 480.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Movement", meta = (ClampMin = "0"))
	float CrouchSpeed = 140.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Movement", meta = (ClampMin = "0"))
	float MaxAcceleration = 1400.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Movement", meta = (ClampMin = "0"))
	float BrakingDeceleration = 1600.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Movement", meta = (ClampMin = "0"))
	float GroundFriction = 8.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Movement", meta = (ClampMin = "1"))
	float CrouchedHalfHeight = 58.f;

	/** Move input must point this far forward (dot with facing) to sprint. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Movement", meta = (ClampMin = "-1", ClampMax = "1"))
	float SprintMinForwardDot = 0.5f;

	/** Horizontal speed below which the gait is Idle. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Movement", meta = (ClampMin = "0"))
	float IdleSpeedThreshold = 10.f;

	// ---- Camera feel ----
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Camera", meta = (ClampMin = "0.01"))
	float CrouchCameraBlendTime = 0.2f;

	/** Vertical bob amplitude in cm. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Camera|Bob", meta = (ClampMin = "0"))
	float WalkBobAmplitude = 0.6f;

	/** Bob cycles per second at full gait speed. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Camera|Bob", meta = (ClampMin = "0"))
	float WalkBobFrequency = 1.6f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Camera|Bob", meta = (ClampMin = "0"))
	float SprintBobAmplitude = 1.4f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Camera|Bob", meta = (ClampMin = "0"))
	float SprintBobFrequency = 2.3f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Camera|Bob", meta = (ClampMin = "0"))
	float CrouchBobAmplitude = 0.4f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Camera|Bob", meta = (ClampMin = "0"))
	float CrouchBobFrequency = 1.2f;

	/** How quickly the bob fades in and out (1/s). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Camera|Bob", meta = (ClampMin = "0.1"))
	float BobSettleSpeed = 8.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Camera|FOV")
	float SprintFOVDelta = 4.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Camera|FOV", meta = (ClampMin = "0.01"))
	float SprintFOVEaseTime = 0.25f;

	/** Downward camera offset in cm at a full-speed landing. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Camera|Landing", meta = (ClampMin = "0"))
	float LandingDipDepth = 3.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Camera|Landing", meta = (ClampMin = "0.01"))
	float LandingDipTime = 0.3f;

	/** Falls slower than this produce no dip. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Camera|Landing", meta = (ClampMin = "0"))
	float LandingDipMinFallSpeed = 250.f;

	/** Falls at or above this speed produce the full dip. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Camera|Landing", meta = (ClampMin = "1"))
	float LandingDipFullFallSpeed = 700.f;

	// ---- Footsteps ----
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Footsteps", meta = (ClampMin = "1"))
	float WalkStride = 160.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Footsteps", meta = (ClampMin = "1"))
	float SprintStride = 210.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Footsteps", meta = (ClampMin = "1"))
	float CrouchStride = 120.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Footsteps", meta = (ClampMin = "0", ClampMax = "1"))
	float WalkLoudness = 0.3f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Footsteps", meta = (ClampMin = "0", ClampMax = "1"))
	float SprintLoudness = 0.8f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Footsteps", meta = (ClampMin = "0", ClampMax = "1"))
	float CrouchLoudness = 0.1f;

	/** Extra trace length below the capsule bottom when looking for the floor. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Footsteps", meta = (ClampMin = "0"))
	float FootstepTraceExtraDepth = 30.f;

	/** Complex traces read per-material physical materials. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Footsteps")
	bool bFootstepTraceComplex = true;

	// ---- Candle ----
	/** In candelas. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Candle", meta = (ClampMin = "0"))
	float CandleIntensity = 10.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Candle", meta = (ClampMin = "1"))
	float CandleAttenuationRadius = 600.f;

	/** Kelvin. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Candle", meta = (ClampMin = "1000", ClampMax = "12000"))
	float CandleTemperature = 1900.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Candle")
	bool bCandleCastShadows = false;

	/** Fractional intensity swing (0.12 = +-12%). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Candle|Flicker", meta = (ClampMin = "0", ClampMax = "1"))
	float CandleFlickerAmplitude = 0.12f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Candle|Flicker", meta = (ClampMin = "0"))
	float CandleFlickerFrequency = 6.f;

	/** Light position jitter in cm. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Candle|Flicker", meta = (ClampMin = "0"))
	float CandlePositionJitter = 0.6f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Candle|Guttering", meta = (ClampMin = "0", ClampMax = "1"))
	float CandleGutterIntensityScale = 0.55f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Candle|Guttering", meta = (ClampMin = "1"))
	float CandleGutterFlickerMultiplier = 2.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Candle|Guttering", meta = (ClampMin = "0.1"))
	float CandleGutterBlendSpeed = 6.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Candle", meta = (ClampMin = "0"))
	float CandleRelightDelay = 1.2f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Candle", meta = (ClampMin = "0"))
	float CandleRelightFadeTime = 0.25f;

	/**
	 * Candle offset relative to the camera (the hand): X forward, Y right, Z up, cm. Measured by LastBell.Functional.PlayerFeel.CandleOnScreen:
	 * puts the flame in the lower-right quadrant of the frame (never cut off) for 16:9, 4:3, 1:1 and 0.94 windows, standing, crouched and sprinting.
	 * The camera keeps its vertical FOV when the window gets narrower, so the horizontal field shrinks; do not push Y out further.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Candle")
	FVector CandleHeldOffset = FVector(36.f, 14.f, -10.f);

	/** Degrees of held-mesh sway per unit of look input. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Candle|Sway", meta = (ClampMin = "0"))
	float CandleSwayStrength = 0.6f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Candle|Sway", meta = (ClampMin = "0"))
	float CandleSwayMaxAngle = 4.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Candle|Sway", meta = (ClampMin = "0.1"))
	float CandleSwaySpeed = 8.f;

	// ---- Inspection ----
	/** Distance in front of the camera at which the item is held, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Inspection", meta = (ClampMin = "5"))
	float InspectHoldDistance = 45.f;

	/**
	 * Degrees of item rotation per unit of rotate input. Raw mouse counts reach the action multiplied by 0.07 (the Mouse2D axis
	 * sensitivity in DefaultInput.ini), so 4 is about 0.28 degrees per mouse count; a gamepad stick delivers up to 1 per frame.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Inspection", meta = (ClampMin = "0"))
	float InspectRotateRate = 4.0f;

	/** Time for the item to travel to the hold point. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Inspection", meta = (ClampMin = "0"))
	float InspectBlendTime = 0.25f;

	// ---- Queries ----
	float GetStride(ELBGait Gait) const;
	float GetLoudness(ELBGait Gait) const;
	float GetGaitSpeed(ELBGait Gait) const;

	/** Applies speeds, acceleration, braking, friction and crouched half height. */
	void ApplyToMovement(UCharacterMovementComponent* Movement) const;
};
