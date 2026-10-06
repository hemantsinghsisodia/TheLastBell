#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameplayTagContainer.h"
#include "LBInteractableComponent.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FLBInteractSignature, AActor*, Instigator);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FLBFocusSignature);

/** Add to any actor to make it interactable. */
UCLASS(ClassGroup = "LastBell", meta = (BlueprintSpawnableComponent))
class LASTBELL_API ULBInteractableComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Interaction")
	FText PromptText;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Interaction")
	bool bEnabled = true;

	/** Shown instead of PromptText while the component is focused but cannot be used (empty = no prompt). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Interaction")
	FText DeniedPromptText;

	/** All of these must be present in world state. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Interaction")
	FGameplayTagContainer RequiredStateTags;

	/** Added to world state on a successful interaction. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Interaction")
	FGameplayTagContainer GrantedStateTags;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Interaction")
	bool bSingleUse = false;

	/** Persists single use: added on interaction, and disables this component on BeginPlay when present. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Interaction")
	FGameplayTag ConsumedStateTag;

	/** Pure gating logic: enabled, all requirements present, not consumed. */
	bool PassesStateRequirements(const FGameplayTagContainer& WorldState) const;

	UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category = "LastBell|Interaction")
	bool CanInteract(AActor* Instigator);

	UFUNCTION(BlueprintCallable, Category = "LastBell|Interaction")
	void Interact(AActor* Instigator);

	/** Called by the interactor. */
	void NotifyFocusBegin();
	void NotifyFocusEnd();

	UPROPERTY(BlueprintAssignable, Category = "LastBell|Interaction")
	FLBInteractSignature OnInteracted;

	UPROPERTY(BlueprintAssignable, Category = "LastBell|Interaction")
	FLBInteractSignature OnInteractDenied;

	UPROPERTY(BlueprintAssignable, Category = "LastBell|Interaction")
	FLBFocusSignature OnFocusBegin;

	UPROPERTY(BlueprintAssignable, Category = "LastBell|Interaction")
	FLBFocusSignature OnFocusEnd;

protected:
	virtual void BeginPlay() override;
};
