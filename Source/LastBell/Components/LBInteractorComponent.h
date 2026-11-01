#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "LBInteractorComponent.generated.h"

class ULBInteractableComponent;
class ULBInspectionComponent;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FLBFocusChangedSignature, ULBInteractableComponent*, NewFocus, FText, Prompt);

/** Timer-driven (no tick) camera-forward sphere trace on the Interaction channel. */
UCLASS(ClassGroup = "LastBell", meta = (BlueprintSpawnableComponent))
class LASTBELL_API ULBInteractorComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Interaction")
	float TraceDistance = 200.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Interaction")
	float TraceRadius = 8.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Interaction")
	float TraceInterval = 0.1f;

	/** Re-traces immediately, then interacts with the focused component. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Interaction")
	void TryInteract();

	UFUNCTION(BlueprintPure, Category = "LastBell|Interaction")
	ULBInteractableComponent* GetFocusedComponent() const { return FocusedComponent.Get(); }

	/** Pure prompt choice: empty for a used-up (consumed) component, else the prompt if it can be used, else the denied text. */
	static FText SelectPrompt(bool bConsumed, bool bCanInteract, const FText& PromptText, const FText& DeniedPromptText);

	/** Prompt is empty when nothing is focused, the focused component is consumed, or it cannot currently be used (then its denied text, if any). */
	UPROPERTY(BlueprintAssignable, Category = "LastBell|Interaction")
	FLBFocusChangedSignature OnFocusChanged;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	void UpdateFocus();
	bool IsOwnerInspecting() const;
	ULBInteractableComponent* TraceForInteractable() const;

	TWeakObjectPtr<ULBInteractableComponent> FocusedComponent;
	FText LastPrompt;
	TWeakObjectPtr<ULBInspectionComponent> OwnerInspection;
	FTimerHandle TraceTimer;
};
