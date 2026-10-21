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

	/** True for items that are collected (e.g. a key): closing runs the interactable's normal grant (GrantedStateTags, single use) and hides the actor. False: closing puts the item back exactly. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Inspection")
	bool bKeepOnClose = false;

	/** Starting orientation relative to the camera (X forward, Y right, Z up). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Inspection")
	FRotator InitialInspectRotation = FRotator::ZeroRotator;

	/** Hides the kept actor and disables its collision. Called by the inspection component on a keep; world-state grants go through the interactable. */
	void ApplyKeep();
};
