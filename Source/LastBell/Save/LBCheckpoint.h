#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LBCheckpoint.generated.h"

class UBoxComponent;
class UArrowComponent;
class ALBCharacter;

/** Trigger box that saves once when the player first enters it. The arrow marks the respawn transform. */
UCLASS()
class LASTBELL_API ALBCheckpoint : public AActor
{
	GENERATED_BODY()

public:
	ALBCheckpoint();

	UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category = "LastBell|Checkpoint")
	FName CheckpointId;

	/** False while any Warden is in Chase or Attack (D-019). A refused checkpoint retries while the player stays inside the trigger. */
	virtual bool CanSaveNow() const;

protected:
	virtual void PostInitializeComponents() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "LastBell|Checkpoint")
	TObjectPtr<UBoxComponent> Trigger;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "LastBell|Checkpoint")
	TObjectPtr<UArrowComponent> SpawnArrow;

	UFUNCTION()
	void OnTriggerBeginOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);

private:
	/** Saves if nothing forbids it; if only the Warden rule refuses, starts a retry timer that runs while the player stays inside. */
	void TrySave(const ALBCharacter* Character);
	void RetryWhileInside();

	FTimerHandle RetryTimer;
};
