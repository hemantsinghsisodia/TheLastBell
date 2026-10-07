#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameplayTagContainer.h"
#include "LBInspectableComponent.generated.h"

/** Marks an actor as inspectable: pick up, rotate, read, then put back or keep. */
UCLASS(ClassGroup = "LastBell", meta = (BlueprintSpawnableComponent))
class LASTBELL_API ULBInspectableComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Inspection")
	FText DisplayName;

	/** Optional note text shown by the inspect UI. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Inspection", meta = (MultiLine = "true"))
	FText BodyText;

	/** True for items that are collected (e.g. a key): closing grants GrantOnKeep, runs the interactable grant and hides the actor. False: closing puts the item back exactly. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Inspection")
	bool bKeepOnClose = false;

	/** Added to world state when the item is kept. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Inspection", meta = (EditCondition = "bKeepOnClose"))
	FGameplayTagContainer GrantOnKeep;

	/** Starting orientation relative to the camera (X forward, Y right, Z up). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Inspection")
	FRotator InitialInspectRotation = FRotator::ZeroRotator;

	/** Grants GrantOnKeep through world state and hides the actor. Called by the inspection component on a keep. */
	void ApplyKeep();
};
