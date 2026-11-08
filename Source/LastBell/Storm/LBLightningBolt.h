#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LBLightningBolt.generated.h"

class UMaterialInstanceDynamic;
class UMaterialInterface;
class UStaticMesh;
class UStaticMeshComponent;

/**
 * One bolt card of the storm (P15): a camera-facing quad with a branching bolt painted on it. The mesh is SM_LB_FX_BoltCard (100 x 100
 * cm, pivot at the top centre, extending down -Z), the material is MI_LB_Bolt, which reads MPC_LB_Storm.LightningFlash, so the card is
 * invisible at rest and flickers with the pulses of the flash. No code writes its brightness.
 *
 * ULBStormFXSubsystem owns a small pool of these and places them (LBStormFXLogic transforms). No collision, no shadows, no custom depth.
 */
UCLASS(NotPlaceable, Transient)
class LASTBELL_API ALBLightningBolt : public AActor
{
	GENERATED_BODY()

public:
	ALBLightningBolt();

	/** Gives the card its mesh and the material to make the dynamic instance from. Cheap to call again with the same assets. */
	void SetAssets(UStaticMesh* Mesh, UMaterialInterface* Material);

	/**
	 * Places the card and picks the atlas cell. The dynamic material instance is made from the material the first time and its scalar
	 * AtlasIndex is set. With no material only the transform is set.
	 */
	void SetBolt(const FTransform& Transform, int32 AtlasIndex);

	/** Shows the card; Now (world seconds) is when, for the pool's timeout. */
	void ShowBolt(double Now);
	void HideBolt();

	bool IsBoltShown() const { return bShown; }
	double GetShownAt() const { return ShownAt; }
	int32 GetAtlasIndex() const { return Atlas; }

	/** The world position of the card's bottom (local 0, 0, -100): where a strike bolt meets its target. */
	FVector GetBoltBottom() const;

	/** The name of the scalar parameter that picks the atlas cell. */
	static const FName AtlasParameterName;

private:
	UPROPERTY(VisibleAnywhere, Category = "Bolt")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> SourceMaterial;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> Dynamic;

	int32 Atlas = 0;
	bool bShown = false;
	double ShownAt = 0.0;
};
