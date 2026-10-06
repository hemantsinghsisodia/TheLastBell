#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "LBInteractorComponent.generated.h"

class ULBInteractableComponent;

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

	/** Prompt is empty when nothing is focused or the focused component cannot currently be used. */
	UPROPERTY(BlueprintAssignable, Category = "LastBell|Interaction")
	FLBFocusChangedSignature OnFocusChanged;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	void UpdateFocus();
	ULBInteractableComponent* TraceForInteractable() const;

	TWeakObjectPtr<ULBInteractableComponent> FocusedComponent;
	FText LastPrompt;
	FTimerHandle TraceTimer;
};
