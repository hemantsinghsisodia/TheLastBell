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

/** Fired by the character while an input lock is on and the player presses or releases Interact (the cinematic skip hold binds these). */
DECLARE_MULTICAST_DELEGATE(FLBLockedInteractSignature);

/** Where the catch camera looks. Public so tests can compare the view against the same point. */
namespace LBCatchCamera
{
	/** Name of the socket on the killer's skeletal mesh the view turns to. */
	LASTBELL_API const FName& MaskSocketName();

	/** Distance above the killer's location used when it has no mask socket, cm. */
	constexpr double FallbackHeight = 230.0;

	/** The point the view is pulled to: the killer's mask socket, or its location plus FallbackHeight. */
	LASTBELL_API FVector ResolveLookTarget(const AActor* Killer);
}

UCLASS()
class LASTBELL_API ALBCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	ALBCharacter();

	/**
	 * Disables input and asks the game mode to handle death. Safe to call repeatedly.
	 *
	 * With a Killer (the Warden's catch) the death is not immediate: the view turns to the killer's "mask" socket (or its location
	 * plus 230 cm without one) over CatchLookSeconds, holds for CatchHoldSeconds, the camera fades to black over CatchFadeSeconds,
	 * and only then does the game mode handle the death. IsDead() is true from the moment of the call. With no Killer (console,
	 * kill volumes) the death is handled at once, exactly as before.
	 */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Player")
	void Kill(AActor* Killer = nullptr);

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

	/**
	 * Sets how much of the player's control a cinematic takes (P17 section 2.4). Any lock other than None clears the move input, stops the
	 * character, stands it up and turns sprint off (an open inspection is cancelled). Look: only turning the head works. Full: nothing
	 * works. Interact presses and releases are forwarded to OnLockedInteractPressed / OnLockedInteractReleased.
	 */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Player")
	void SetInputLock(ELBInputLock NewLock);

	UFUNCTION(BlueprintPure, Category = "LastBell|Player")
	ELBInputLock GetInputLock() const { return InputLock; }

	/** The player pressed Interact while an input lock was on. */
	FLBLockedInteractSignature OnLockedInteractPressed;

	/** The player let go of Interact after a locked press (polled from the key state, so it also works if the lock ended meanwhile). */
	FLBLockedInteractSignature OnLockedInteractReleased;

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
	/** Interact Completed / Canceled. Releases a locked press only if no key bound to Interact is still down. */
	void InteractReleased();
	/** True while any key mapped to the Interact action is held. */
	bool IsInteractKeyDown() const;
	void ReleaseLockedInteract();
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

	/** Moves the catch camera along (look, hold, fade) and hands over to the game mode at the end. */
	void TickCatch(float DeltaSeconds);
	void FinishDeath();

	enum class ECatchStage : uint8
	{
		None,
		Look,
		Hold,
		Fade
	};

	ECatchStage CatchStage = ECatchStage::None;
	float CatchStageTime = 0.f;
	FRotator CatchStartRotation = FRotator::ZeroRotator;
	FVector CatchLastTarget = FVector::ZeroVector;
	TWeakObjectPtr<AActor> CatchKiller;

	ELBInputLock InputLock = ELBInputLock::None;
	/** A locked Interact press was forwarded and its release has not been yet. */
	bool bLockedInteractHeld = false;

	bool bIsDead = false;
	bool bSprintHeld = false;
	bool bSprinting = false;
	ELBGait CachedGait = ELBGait::Idle;
	FVector2D MoveInput = FVector2D::ZeroVector;
};
