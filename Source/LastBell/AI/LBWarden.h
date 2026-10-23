#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "LBWarden.generated.h"

class ULBWardenBrainComponent;
class ULBWardenTuningData;

/**
 * The Warden pawn. C++ owns the capsule, movement setup and brain; BP_Warden adds the mesh, animation and audio.
 * Place exactly one in the persistent level (anywhere; it starts dormant and hidden). It is never saved (D-012): the brain
 * rebuilds it from the State.Warden.Stage.N tags at the matching ALBWardenSpawnPoint.
 */
UCLASS()
class LASTBELL_API ALBWarden : public ACharacter
{
	GENERATED_BODY()

public:
	ALBWarden();

	/** DA_WardenTuning. When empty the ULBWardenTuningData class defaults are used. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "LastBell|Warden")
	TObjectPtr<ULBWardenTuningData> Tuning;

	/** The assigned tuning asset, or the class defaults when none is assigned. Never null. */
	const ULBWardenTuningData& GetTuning() const;

	/** The brain lives on the AI controller; null before possession. */
	UFUNCTION(BlueprintPure, Category = "LastBell|Warden")
	ULBWardenBrainComponent* GetBrain() const;

	/** Dormant presentation: hidden, no collision, no movement. Driven by the brain. */
	void SetDormantPresentation(bool bDormant);

	UFUNCTION(BlueprintPure, Category = "LastBell|Warden")
	bool IsDormantPresentation() const { return bDormantPresentation; }

protected:
	virtual void BeginPlay() override;

private:
	bool bDormantPresentation = false;
};
