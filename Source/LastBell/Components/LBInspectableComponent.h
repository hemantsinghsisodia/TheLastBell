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

	/**
	 * Flat items (a note, a card) are turned face-on automatically when inspection starts: the thinnest axis of the item
	 * points back at the camera and its longest axis points up. InitialInspectRotation is applied on top of that.
	 * Turn this off to take full control of the orientation with InitialInspectRotation alone.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Inspection")
	bool bAutoFaceCamera = true;

	/**
	 * Extra rotation applied when inspection starts, in CAMERA space (X forward, Y right, Z up), not in the item's own
	 * space: (0,0,0) means "the item's axes line up with the camera's". Applied after the automatic face-the-camera
	 * alignment when bAutoFaceCamera is on. Hand-authored face-on value for a flat sheet whose thin axis is local Z and
	 * long axis local Y (bAutoFaceCamera off): MakeFromZY(Z = (-1,0,0), Y = (0,0,1)), see the InspectFlatFacesCamera test.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Inspection")
	FRotator InitialInspectRotation = FRotator::ZeroRotator;

	/** Hides the kept actor and disables its collision. Called by the inspection component on a keep; world-state grants go through the interactable. */
	void ApplyKeep();
};
