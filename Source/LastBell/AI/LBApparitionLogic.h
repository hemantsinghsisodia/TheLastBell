#pragma once

#include "CoreMinimal.h"
#include "LBApparitionLogic.generated.h"

/**
 * Pure logic of a scripted Warden appearance (P12 fix set 1). No world, no actor: ALBWardenApparition gathers the facts and
 * applies the result. Unit tested (LastBell.Warden.Apparition.*).
 *
 *   Idle -> Start -> ArmDelay -> for each station: WaitForLook -> FadeIn -> Hold -> [Walk] -> FadeOut -> Gap -> Done
 *
 * Walk (P13) is only entered when the station has a WalkPath. The actor does the walking and reports when the path is finished
 * through the facts; the logic stays pure.
 */

/** One place the figure appears: where, how the player must look at it, and how long each part lasts. */
USTRUCT(BlueprintType)
struct LASTBELL_API FLBApparitionStation
{
	GENERATED_BODY()

	/** World location of the figure's feet. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Apparition")
	FVector Location = FVector::ZeroVector;

	/** Half angle of the player's view cone the look point must be inside before the figure forms. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Apparition", meta = (ClampMin = "1", ClampMax = "90", Units = "deg"))
	float LookConeDegrees = 30.f;

	/** Flat distance (cm) under which the station is skipped while waiting, or fades out early while it is showing. 0 = never. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Apparition", meta = (ClampMin = "0", Units = "cm"))
	float MinPlayerDistance = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Apparition", meta = (ClampMin = "0", Units = "s"))
	float FadeInSeconds = 1.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Apparition", meta = (ClampMin = "0", Units = "s"))
	float HoldSeconds = 3.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Apparition", meta = (ClampMin = "0", Units = "s"))
	float FadeOutSeconds = 1.5f;

	/** Pause after the fade-out before the next station starts waiting for the player's eyes. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Apparition", meta = (ClampMin = "0", Units = "s"))
	float GapAfterSeconds = 0.f;

	/**
	 * World-space points the figure walks through, in order, after the hold and before it fades out. Empty = it stays where it
	 * is (the behaviour of every station before Phase 13). The figure fades out early if the player comes within MinPlayerDistance.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Apparition|Walk")
	TArray<FVector> WalkPath;

	/** Walking speed along WalkPath. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Apparition|Walk", meta = (ClampMin = "1", Units = "cm/s"))
	float WalkSpeed = 110.f;
};

UENUM(BlueprintType)
enum class ELBApparitionPhase : uint8
{
	Idle,
	ArmDelay,
	WaitForLook,
	FadeIn,
	Hold,
	/** Walking along the station's WalkPath at full alpha (P13). */
	Walk,
	FadeOut,
	Gap,
	Done
};

/** The running appearance. Alpha is the figure's fade (0 hidden, 1 fully there); the actor writes it into the materials. */
struct FLBApparitionRun
{
	ELBApparitionPhase Phase = ELBApparitionPhase::Idle;
	int32 Station = 0;
	/** Seconds spent in the current phase. */
	float PhaseTime = 0.f;
	/** Alpha when the FadeOut began (an early fade-out starts from wherever the fade-in had got to). */
	float FadeOutFrom = 1.f;
	float Alpha = 0.f;
};

/** What Step() may look at. The actor fills it every tick. */
struct FLBApparitionFacts
{
	float DeltaSeconds = 0.f;
	/** The current station's look point is inside the player's view cone with a clear line of sight. */
	bool bLookedAt = false;
	/** Flat distance from the player to the current station (during Walk: to the figure, which has moved on). */
	float PlayerDistance = 1.0e9f;
	/** Walk only: the figure has reached the end of its path. */
	bool bWalkFinished = false;
};

namespace LBApparition
{
	/** Begin a run: ArmDelay, first station, alpha 0. */
	LASTBELL_API void Start(FLBApparitionRun& Run);

	/** Back to Idle. */
	LASTBELL_API void Reset(FLBApparitionRun& Run);

	/** Straight to Done (the tag is already present: the one-shot has been used). */
	LASTBELL_API void Finish(FLBApparitionRun& Run);

	/**
	 * Advance by Facts.DeltaSeconds. At most one phase change per call (a zero duration completes on the next call); the time left
	 * over carries into the next fade or hold. Returns true when the run has just entered FadeIn: the actor then moves and turns
	 * the figure.
	 */
	LASTBELL_API bool Step(FLBApparitionRun& Run, const TArray<FLBApparitionStation>& Stations, float ArmDelaySeconds, const FLBApparitionFacts& Facts);

	LASTBELL_API const TCHAR* PhaseName(ELBApparitionPhase Phase);
}
