#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "LBCameraFeelComponent.generated.h"

class UCameraComponent;
class ALBCharacter;
class ULBPlayerTuningData;
class UCharacterMovementComponent;

/**
 * Drives the first-person camera's relative location and FOV: crouch eye-height blend, vertical head bob,
 * sprint FOV ease and a landing dip. No roll, no shake.
 */
UCLASS(ClassGroup = "LastBell", meta = (BlueprintSpawnableComponent))
class LASTBELL_API ULBCameraFeelComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	ULBCameraFeelComponent();

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	UFUNCTION()
	void HandleLanded(const FHitResult& Hit);

	TWeakObjectPtr<ALBCharacter> Character;
	TWeakObjectPtr<UCameraComponent> Camera;
	TWeakObjectPtr<const ULBPlayerTuningData> Tuning;

	FVector BaseRelativeLocation = FVector::ZeroVector;
	float BaseFOV = 90.f;
	float StandingHalfHeight = 0.f;

	float CrouchAlpha = 0.f;
	float SprintAlpha = 0.f;

	float BobPhase = 0.f;
	float BobWeight = 0.f;
	float BobAmplitude = 0.f;
	float BobFrequency = 0.f;

	float PeakFallSpeed = 0.f;
	float DipElapsed = 0.f;
	float DipScale = 0.f;
	bool bDipActive = false;
};
