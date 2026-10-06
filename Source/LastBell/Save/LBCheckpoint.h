#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LBCheckpoint.generated.h"

class UBoxComponent;
class UArrowComponent;

/** Trigger box that saves once when the player first enters it. The arrow marks the respawn transform. */
UCLASS()
class LASTBELL_API ALBCheckpoint : public AActor
{
	GENERATED_BODY()

public:
	ALBCheckpoint();

	UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category = "LastBell|Checkpoint")
	FName CheckpointId;

	/** Phase 5 hook: refuse saving while the Warden is chasing or attacking. */
	virtual bool CanSaveNow() const { return true; }

protected:
	virtual void PostInitializeComponents() override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "LastBell|Checkpoint")
	TObjectPtr<UBoxComponent> Trigger;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "LastBell|Checkpoint")
	TObjectPtr<UArrowComponent> SpawnArrow;

	UFUNCTION()
	void OnTriggerBeginOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);
};
