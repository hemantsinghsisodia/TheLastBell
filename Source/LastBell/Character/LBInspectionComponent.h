#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "LBInspectionComponent.generated.h"

class ULBInspectableComponent;
class ULBInteractableComponent;
class ULBPlayerTuningData;
class ALBCharacter;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FLBInspectBeginSignature, ULBInspectableComponent*, Inspectable);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FLBInspectEndSignature, bool, bKept);

/**
 * Inspection mode on the character: the item is carried to a hold point in front of the camera, can be
 * rotated, and is restored exactly (or kept) on close. Movement and look are blocked by the character
 * while IsInspecting(); the inspect mapping context is added through the player controller.
 */
UCLASS(ClassGroup = "LastBell", meta = (BlueprintSpawnableComponent))
class LASTBELL_API ULBInspectionComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	ULBInspectionComponent();

	/** Source is the interactable that started the inspection; on a keep its normal grant runs through Interact. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Inspection")
	bool BeginInspect(ULBInspectableComponent* Inspectable, ULBInteractableComponent* Source = nullptr);

	/**
	 * Closes the inspection: keeps or puts back according to the inspectable's bKeepOnClose. Always cleans up (tick off,
	 * inspect input context removed, OnInspectEnd broadcast), even when the item was destroyed meanwhile; in that case the
	 * restore, keep and grant steps are skipped.
	 */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Inspection")
	void EndInspect();

	/** Aborts the inspection: puts the item back (if it still exists), grants nothing, cleans up. Used on death and EndPlay. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Inspection")
	void CancelInspect();

	/**
	 * Player-initiated close (input). Ignored for the first couple of frames after BeginInspect so the key press that
	 * opened the item (still held when the inspect mapping context is added) cannot close it again.
	 */
	bool RequestClose();

	/** True when an inspection was closed during the current frame; stops a shared Interact/Exit key re-opening the item. */
	bool WasClosedThisFrame() const;

	/** Rotation input (mouse delta / stick), scaled by the tuning's InspectRotateRate. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Inspection")
	void AddRotateInput(FVector2D Axis);

	UFUNCTION(BlueprintPure, Category = "LastBell|Inspection")
	bool IsInspecting() const { return bInspecting; }

	UFUNCTION(BlueprintPure, Category = "LastBell|Inspection")
	ULBInspectableComponent* GetInspected() const { return Inspected.Get(); }

	UPROPERTY(BlueprintAssignable, Category = "LastBell|Inspection")
	FLBInspectBeginSignature OnInspectBegin;

	UPROPERTY(BlueprintAssignable, Category = "LastBell|Inspection")
	FLBInspectEndSignature OnInspectEnd;

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

protected:
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	const ULBPlayerTuningData& GetTuning() const;
	bool GetViewPoint(FVector& OutLocation, FRotator& OutRotation) const;
	void RestoreItem(ULBInspectableComponent* Inspectable);
	void FinishInspect(bool bCancel);
	void SetInputContextActive(bool bActive) const;

	bool bInspecting = false;

	TWeakObjectPtr<ULBInspectableComponent> Inspected;
	TWeakObjectPtr<ULBInteractableComponent> Source;

	FTransform OriginalTransform;
	FVector LocalCenterOffset = FVector::ZeroVector;
	bool bOriginalCollision = true;
	bool bWasSimulatingPhysics = false;

	FQuat ItemRotationInCameraSpace = FQuat::Identity;
	float BlendAlpha = 0.f;
	uint64 BeginFrame = 0;
	uint64 EndFrame = 0;
};
