#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Engine/DataTable.h"
#include "Character/LBPlayerTypes.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "LBFootstepComponent.generated.h"

class ALBCharacter;
class ULBPlayerTuningData;
class USoundBase;

/** One row of DT_Footsteps. The row whose SurfaceType matches the floor is used; SurfaceType_Default is the fallback. */
USTRUCT(BlueprintType)
struct LASTBELL_API FLBFootstepRow : public FTableRowBase
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Footstep")
	TEnumAsByte<EPhysicalSurface> SurfaceType = SurfaceType_Default;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Footstep")
	TObjectPtr<USoundBase> Sound = nullptr;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Footstep", meta = (ClampMin = "0"))
	float VolumeMin = 0.8f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Footstep", meta = (ClampMin = "0"))
	float VolumeMax = 1.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Footstep", meta = (ClampMin = "0.1"))
	float PitchMin = 0.95f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Footstep", meta = (ClampMin = "0.1"))
	float PitchMax = 1.05f;
};

/** Loudness is 0..1 by gait. The component also reports each step to the AI hearing sense (UAISense_Hearing::ReportNoiseEvent). */
DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FLBFootstepSignature, float, Loudness, FVector, Location, TEnumAsByte<EPhysicalSurface>, Surface);

/** Distance-based footsteps: stride per gait, floor physical material to sound, and the OnFootstep event. */
UCLASS(ClassGroup = "LastBell", meta = (BlueprintSpawnableComponent))
class LASTBELL_API ULBFootstepComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	ULBFootstepComponent();

	/** Rows are FLBFootstepRow. Set in Blueprint (DT_Footsteps). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Footsteps")
	TObjectPtr<UDataTable> FootstepTable;

	UPROPERTY(BlueprintAssignable, Category = "LastBell|Footsteps")
	FLBFootstepSignature OnFootstep;

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	UFUNCTION()
	void HandleLanded(const FHitResult& Hit);

	void EmitStep(float Loudness, FName NoiseTag);

	TWeakObjectPtr<ALBCharacter> Character;
	TWeakObjectPtr<const ULBPlayerTuningData> Tuning;
	FLBStrideAccumulator Stride;
};
