#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LBCheckpoint.generated.h"

class UBoxComponent;
class UArrowComponent;
class ALBCharacter;
class ULBCinematicSubsystem;

/** Trigger box that saves once when the player first enters it. The arrow marks the respawn transform. */
UCLASS()
class LASTBELL_API ALBCheckpoint : public AActor
{
	GENERATED_BODY()

public:
	ALBCheckpoint();

	UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category = "LastBell|Checkpoint")
	FName CheckpointId;

	/**
	 * False while any Warden is in Chase or Attack (D-019) or a cinematic plays (P17: nothing is saved under a cinematic). A refused
	 * checkpoint retries while the player stays inside the trigger. A checkpoint refused because a cinematic plays also remembers that and
	 * saves once when the cinematic finishes, even if the player has left the trigger by then (see HandleCinematicFinished).
	 */
	virtual bool CanSaveNow() const;

	/** Why CanSaveNow is false ("the Warden is chasing" or "a cinematic is playing"), or null when saving is allowed. */
	const TCHAR* GetSaveRefusalReason() const;

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
	/**
	 * Saves if nothing forbids it. If something refuses, starts a retry timer that runs while the player stays inside; if a cinematic is
	 * playing, it also waits for the cinematic's end (OnCinematicFinished).
	 */
	void TrySave(const ALBCharacter* Character);
	void RetryWhileInside();

	/** True while the world's cinematic subsystem has a run active. */
	bool IsCinematicPlaying() const;
	/** Binds OnCinematicFinished (once) so the save refused during a cinematic is tried again when it ends. */
	void WaitForCinematicEnd();
	/** Unbinds OnCinematicFinished and forgets the pending save. Safe to call when nothing is pending. */
	void StopWaitingForCinematicEnd();
	/** The cinematic ended: one more try, whether or not the player is still inside the trigger. */
	void HandleCinematicFinished(FName CinematicId);

	FTimerHandle RetryTimer;

	/** Set while this checkpoint is bound to OnCinematicFinished of CinematicSubsystem; never bound otherwise. */
	TWeakObjectPtr<ULBCinematicSubsystem> CinematicSubsystem;
	FDelegateHandle CinematicFinishedHandle;
};
