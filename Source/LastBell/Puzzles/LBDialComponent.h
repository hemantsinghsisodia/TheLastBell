#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameplayTagContainer.h"
#include "LBDialComponent.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FLBDialChangedSignature, int32, NewIndex);

/**
 * A multi-position dial / lever whose position is a world state tag (one tag per position, exactly one present).
 * The position is derived from the tags, so it saves and loads with the rest of the progress.
 *
 * Interaction: if the owner has a ULBInteractableComponent, the dial binds its OnInteracted in BeginPlay and cycles on every
 * successful interaction. The interactable keeps its normal gating (RequiredStateTags, bEnabled, prompts); give it no
 * GrantedStateTags and do not make it single-use. A combination puzzle needs no controller: the target interactable lists
 * the wanted position tags in its RequiredStateTags.
 */
UCLASS(ClassGroup = "LastBell", meta = (BlueprintSpawnableComponent))
class LASTBELL_API ULBDialComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	/** One tag per position, in cycle order. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Dial")
	TArray<FGameplayTag> PositionTags;

	/** Position used when no position tag is present on BeginPlay (a new game). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Dial")
	int32 InitialIndex = 0;

	/** When true the dial does not cycle (e.g. the puzzle it serves is solved). Set from Blueprint, typically from a tag. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Dial")
	bool bLocked = false;

	/** Fired after the position changed through CycleNext. */
	UPROPERTY(BlueprintAssignable, Category = "LastBell|Dial")
	FLBDialChangedSignature OnDialChanged;

	/** Removes the current position tag, adds the next (wrapping). Returns the new index, or INDEX_NONE when locked or empty. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Dial")
	int32 CycleNext();

	/** Index of the position whose tag is present in world state, or INDEX_NONE. */
	UFUNCTION(BlueprintPure, Category = "LastBell|Dial")
	int32 GetCurrentIndex() const;

	UFUNCTION(BlueprintPure, Category = "LastBell|Dial")
	FGameplayTag GetCurrentTag() const;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	UFUNCTION()
	void HandleInteracted(AActor* Instigator);

	TWeakObjectPtr<class ULBInteractableComponent> BoundInteractable;
};
