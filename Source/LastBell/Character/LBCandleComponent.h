#pragma once

#include "CoreMinimal.h"
#include "Components/SceneComponent.h"
#include "Character/LBPlayerTypes.h"
#include "LBCandleComponent.generated.h"

class UPointLightComponent;
class UStaticMeshComponent;
class ULBPlayerTuningData;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FLBCandleStateChangedSignature, bool, bLit);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FLBCandleRelightStartedSignature);

/**
 * The player's handheld candle. Owns a runtime-created point light (warm, flickering), supports snuff and
 * delayed relight, and gutters while the owner sprints. Attach it to the camera: its relative offset is the hand.
 * The visible candle mesh is a UStaticMeshComponent attached under this component in Blueprint (auto-found),
 * or assigned through SetHeldMesh.
 */
UCLASS(ClassGroup = "LastBell", meta = (BlueprintSpawnableComponent))
class LASTBELL_API ULBCandleComponent : public USceneComponent
{
	GENERATED_BODY()

public:
	ULBCandleComponent();

	/** Snuff when lit, start the relight when snuffed. Ignored while relighting. Returns true if accepted. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Candle")
	bool ToggleCandle();

	UFUNCTION(BlueprintPure, Category = "LastBell|Candle")
	bool IsLit() const { return StateMachine.IsLit(); }

	UFUNCTION(BlueprintPure, Category = "LastBell|Candle")
	bool IsRelighting() const { return StateMachine.State == ELBCandleState::Relighting; }

	UFUNCTION(BlueprintCallable, Category = "LastBell|Candle")
	void SetGuttering(bool bInGuttering) { bGuttering = bInGuttering; }

	UFUNCTION(BlueprintPure, Category = "LastBell|Candle")
	bool IsGuttering() const { return bGuttering; }

	/** Look input this frame, used for the held-mesh sway. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Candle")
	void AddLookDelta(FVector2D LookDelta) { PendingLookDelta = LookDelta; }

	UFUNCTION(BlueprintCallable, Category = "LastBell|Candle")
	void SetHeldMesh(UStaticMeshComponent* InMesh);

	UFUNCTION(BlueprintPure, Category = "LastBell|Candle")
	UPointLightComponent* GetLight() const { return Light; }

	/** The visible candle. Set in Blueprint or found among the attached children at BeginPlay. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Candle")
	TObjectPtr<UStaticMeshComponent> HeldMesh;

	UPROPERTY(BlueprintAssignable, Category = "LastBell|Candle")
	FLBCandleStateChangedSignature OnCandleStateChanged;

	UPROPERTY(BlueprintAssignable, Category = "LastBell|Candle")
	FLBCandleRelightStartedSignature OnRelightStarted;

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

protected:
	virtual void BeginPlay() override;

private:
	void ApplyLightSettings();

	UPROPERTY(Transient)
	TObjectPtr<UPointLightComponent> Light;

	const ULBPlayerTuningData* Tuning = nullptr;
	FLBCandleStateMachine StateMachine;

	bool bGuttering = false;
	float GutterAlpha = 0.f;
	float LitAlpha = 1.f;
	float Time = 0.f;

	FVector2D PendingLookDelta = FVector2D::ZeroVector;
	FRotator SwayCurrent = FRotator::ZeroRotator;
	FQuat HeldMeshBaseRotation = FQuat::Identity;
};
