#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Audio/LBAudioSubsystem.h"
#include "LBAmbientEmitter.generated.h"

class USceneComponent;
class USoundBase;

/**
 * A place that makes its own small sounds (plan P16 section 2.9): drips, creaks in the tower, distant chains in the crypt. Either
 * one-shots (a random variant every IntervalMin..IntervalMax seconds, never the same twice in a row, with a random volume and pitch)
 * or one looping sound. It plays only while the player is within ActiveRadius (checked four times a second) and the audio director
 * is running, so lb.Audio.Enabled 0 silences it too. The sound assets carry the attenuation and the concurrency.
 */
UCLASS()
class LASTBELL_API ALBAmbientEmitter : public AActor
{
	GENERATED_BODY()

public:
	ALBAmbientEmitter();

	/** One-shot variants. Used when Loop is empty. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter")
	TArray<TSoftObjectPtr<USoundBase>> Variants;

	/** A looping sound instead of the one-shots. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter")
	TSoftObjectPtr<USoundBase> Loop;

	/** Seconds between one-shots, drawn between Min and Max. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter", meta = (ClampMin = "0.1", ClampMax = "600", Units = "s"))
	float IntervalMin = 3.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter", meta = (ClampMin = "0.1", ClampMax = "600", Units = "s"))
	float IntervalMax = 9.f;

	/** Random volume multiplier of a one-shot (X to Y). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter")
	FVector2D VolumeRange = FVector2D(0.7, 1.0);

	/** Random pitch multiplier of a one-shot (X to Y). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter")
	FVector2D PitchRange = FVector2D(0.95, 1.05);

	/** Plays only while the player is this close, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter", meta = (ClampMin = "0", ClampMax = "100000", Units = "cm"))
	float ActiveRadius = 3000.f;

	/** The loop's volume multiplier (loop mode only). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter", meta = (ClampMin = "0", ClampMax = "2"))
	float LoopVolume = 1.f;

	/** The player is within ActiveRadius and the audio director is running. */
	UFUNCTION(BlueprintPure, Category = "Emitter")
	bool IsEmitterActive() const { return bActive; }

	/** Seconds on the world clock when the next one-shot is due (while active). */
	double GetNextShotTime() const { return NextShotTime; }

	/** The distance check, normally every 0.25 s from Tick; public for tests. */
	void Evaluate(double Now, float DeltaSeconds = 0.25f);

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void Tick(float DeltaSeconds) override;

private:
	void ScheduleNextShot(double Now, ULBAudioSubsystem& Audio);

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<USceneComponent> Root;

	FLBAudioLoop LoopState;
	double NextShotTime = 0.0;
	bool bActive = false;
};
