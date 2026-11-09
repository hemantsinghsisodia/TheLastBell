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

	/** The fallback sound, played when Variants is empty. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Footstep")
	TObjectPtr<USoundBase> Sound = nullptr;

	/** P16: the step sounds of this surface. One is picked at random per step, never the same one twice in a row; empty falls back to Sound. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Footstep")
	TArray<TObjectPtr<USoundBase>> Variants;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Footstep", meta = (ClampMin = "0"))
	float VolumeMin = 0.8f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Footstep", meta = (ClampMin = "0"))
	float VolumeMax = 1.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Footstep", meta = (ClampMin = "0.1"))
	float PitchMin = 0.95f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Footstep", meta = (ClampMin = "0.1"))
	float PitchMax = 1.05f;

	/** P16: volume multiplier while crouched (on top of VolumeMin/Max). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Footstep", meta = (ClampMin = "0", ClampMax = "2"))
	float CrouchVolume = 0.5f;

	/** P16: volume multiplier while sprinting (on top of VolumeMin/Max). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Footstep", meta = (ClampMin = "0", ClampMax = "2"))
	float SprintVolume = 1.25f;
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

	/** The row for a surface (the Default row as the fallback), or null when there is no table or no match. */
	const FLBFootstepRow* FindRow(EPhysicalSurface Surface) const;

	/**
	 * The sound for a step on this row: a random non-null entry of Variants that is not the one picked last for this row (PickVariant in
	 * LBAudioLogic), else Sound. OutVariant is the index picked, or INDEX_NONE for the fallback. Remembers the pick per surface.
	 */
	USoundBase* PickStepSound(const FLBFootstepRow& Row, int32& OutVariant);

	/** The row's volume multiplier for a gait: CrouchVolume, SprintVolume, else 1. */
	static float GaitVolume(const FLBFootstepRow& Row, ELBGait Gait);

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
	/** Index into the non-null Variants of the last pick, per surface. */
	TMap<TEnumAsByte<EPhysicalSurface>, int32> LastVariant;
};
