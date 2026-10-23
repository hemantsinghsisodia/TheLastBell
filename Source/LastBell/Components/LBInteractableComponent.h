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

	/** Designer / Blueprint "locked" switch. Not changed by use when ConsumedStateTag is valid (see there). */
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

	/**
	 * Persists single use. Added to world state on interaction; while it is present the component is unavailable, and removing it
	 * (e.g. a puzzle reset) makes the component usable again. Availability is derived from the tag, never from bEnabled.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Interaction")
	FGameplayTag ConsumedStateTag;

	/** When true (and the actor also has a ULBInspectableComponent), interacting starts an inspection instead of the normal grant. The normal grant then runs when the inspection closes with a keep (see CompleteInspection). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Interaction")
	bool bInspectOnInteract = false;

	/**
	 * Loudness (0..1) of the noise a successful interaction makes, heard by the Warden at this actor's location.
	 * 0 = silent. Suggested: door 0.6, dropped object 0.7, ritual mechanism 1.0. Heard out to the Warden's hearing range times this.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Interaction", meta = (ClampMin = "0", ClampMax = "1"))
	float NoiseLoudness = 0.f;

	/** Pure gating logic: enabled, all requirements present, consumed tag absent. */
	bool PassesStateRequirements(const FGameplayTagContainer& WorldState) const;

	UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category = "LastBell|Interaction")
	bool CanInteract(AActor* Instigator);

	UFUNCTION(BlueprintCallable, Category = "LastBell|Interaction")
	void Interact(AActor* Instigator);

	/** Runs the normal interaction path (grant, consume, OnInteracted) after an inspection was kept. Called by the inspection component. */
	void CompleteInspection(AActor* Instigator);

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

private:
	void ApplyInteraction(AActor* Instigator);
};
