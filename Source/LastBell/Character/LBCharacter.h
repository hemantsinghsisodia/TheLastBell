#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "Character/LBPlayerTypes.h"
#include "LBCharacter.generated.h"

class UCameraComponent;
class UInputAction;
class ULBInteractorComponent;
class ULBPlayerTuningData;
class ULBCameraFeelComponent;
class ULBCandleComponent;
class ULBFootstepComponent;
class ULBInspectionComponent;
class UAIPerceptionStimuliSourceComponent;
struct FInputActionValue;

UCLASS()
class LASTBELL_API ALBCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	ALBCharacter();

	/** Disables input and asks the game mode to handle death. Safe to call repeatedly. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Player")
	void Kill();

	UFUNCTION(BlueprintPure, Category = "LastBell|Player")
	bool IsDead() const { return bIsDead; }

	UFUNCTION(BlueprintPure, Category = "LastBell|Player")
	ULBInteractorComponent* GetInteractor() const { return Interactor; }

	UFUNCTION(BlueprintPure, Category = "LastBell|Player")
	ULBCandleComponent* GetCandle() const { return Candle; }

	UFUNCTION(BlueprintPure, Category = "LastBell|Player")
	ULBInspectionComponent* GetInspection() const { return Inspection; }

	UFUNCTION(BlueprintPure, Category = "LastBell|Player")
	ELBGait GetGait() const;

	/** The assigned tuning asset, or the class defaults when none is assigned. Never null. */
	const ULBPlayerTuningData& GetTuning() const;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "LastBell|Tuning")
	TObjectPtr<ULBPlayerTuningData> Tuning;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "LastBell|Input")
	TObjectPtr<UInputAction> MoveAction;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "LastBell|Input")
	TObjectPtr<UInputAction> LookAction;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "LastBell|Input")
	TObjectPtr<UInputAction> InteractAction;

	/** Hold. Sprint only while moving forward-ish and not crouched. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "LastBell|Input")
	TObjectPtr<UInputAction> SprintAction;

	/** Hold. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "LastBell|Input")
	TObjectPtr<UInputAction> CrouchAction;

	/** Press: snuff / relight the candle. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "LastBell|Input")
	TObjectPtr<UInputAction> CandleAction;

	/** Axis2D, in the inspect mapping context. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "LastBell|Input")
	TObjectPtr<UInputAction> InspectRotateAction;

	/** Press, in the inspect mapping context. Pressing Interact again also closes. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "LastBell|Input")
	TObjectPtr<UInputAction> InspectExitAction;

	/** Extra multiplier on top of the user's mouse sensitivity setting. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Input")
	float LookSensitivity = 1.0f;

protected:
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;
	virtual void OnStartCrouch(float HalfHeightAdjust, float ScaledHalfHeightAdjust) override;
	virtual void OnEndCrouch(float HalfHeightAdjust, float ScaledHalfHeightAdjust) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "LastBell|Player")
	TObjectPtr<UCameraComponent> FirstPersonCamera;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "LastBell|Player")
	TObjectPtr<ULBInteractorComponent> Interactor;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "LastBell|Player")
	TObjectPtr<ULBCameraFeelComponent> CameraFeel;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "LastBell|Player")
	TObjectPtr<ULBCandleComponent> Candle;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "LastBell|Player")
	TObjectPtr<ULBFootstepComponent> Footsteps;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "LastBell|Player")
	TObjectPtr<ULBInspectionComponent> Inspection;

	/** Makes the player visible to AI sight (registered for Sight in BeginPlay). Noise goes through ULBFootstepComponent. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "LastBell|Player")
	TObjectPtr<UAIPerceptionStimuliSourceComponent> StimuliSource;

private:
	void Move(const FInputActionValue& Value);
	void MoveCompleted();
	void Look(const FInputActionValue& Value);
	void Interact();
	void SprintStarted();
	void SprintCompleted();
	void CrouchStarted();
	void CrouchCompleted();
	void CandlePressed();
	void InspectRotate(const FInputActionValue& Value);
	void InspectExit();
	bool IsInspecting() const;
	/** Re-derives bSprinting from the current inputs and applies MaxWalkSpeed. Called whenever one of those inputs changes. */
	void UpdateSprintState();

	bool bIsDead = false;
	bool bSprintHeld = false;
	bool bSprinting = false;
	ELBGait CachedGait = ELBGait::Idle;
	FVector2D MoveInput = FVector2D::ZeroVector;
};
