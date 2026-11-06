#pragma once

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"
#include "LBStormTypes.generated.h"

/** The shape of one lightning flash (plan P14 section 5.3). Auto lets the storm pick one by weight. */
UENUM(BlueprintType)
enum class ELBFlashProfile : uint8
{
	Sheet,
	Double,
	Triple,
	Auto
};

/** Why a flash happened. Phase 16 (thunder) listens to OnLightningFlash and may treat the reasons differently. */
UENUM(BlueprintType)
enum class ELBFlashReason : uint8
{
	Ambient,
	Scripted,
	WardenReveal,
	Apparition,
	Debug
};

/** What a story light group does to its lights while a rule's tag is present. */
UENUM(BlueprintType)
enum class ELBLightStateMode : uint8
{
	On,
	Dim,
	Off,
	Flicker
};

/** One step of the storm's story arc: while Tag is present the storm aims at Intensity. The last present step in the list wins. */
USTRUCT(BlueprintType)
struct LASTBELL_API FLBStormStoryStep
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Storm")
	FGameplayTag Tag;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Storm", meta = (ClampMin = "0", ClampMax = "1"))
	float Intensity = 0.5f;
};

/**
 * A scripted lightning beat. It fires only when TriggerTag is ADDED while playing (never at BeginPlay or after a state replace,
 * so a checkpoint reload does not repeat it). Strike k (0-based) starts at the first strike's start + k * Spacing.
 */
USTRUCT(BlueprintType)
struct LASTBELL_API FLBStormStrike
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Storm")
	FGameplayTag TriggerTag;

	/** Seconds from the tag being added (or, with bLookGate, from the player looking at LookTarget) to the first strike. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Storm", meta = (ClampMin = "0", Units = "s"))
	float Delay = 1.2f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Storm", meta = (ClampMin = "1"))
	int32 Count = 1;

	/** Seconds from one strike's start to the next. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Storm", meta = (ClampMin = "0", Units = "s"))
	float Spacing = 1.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Storm", meta = (ClampMin = "0", ClampMax = "1"))
	float Brightness = 1.f;

	/** Profile of every strike (Auto = by weight). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Storm")
	ELBFlashProfile Profile = ELBFlashProfile::Double;

	/** Per-strike profile: entry k replaces Profile for strike k. Strikes beyond the array use Profile. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Storm")
	TArray<ELBFlashProfile> ProfileOverrides;

	/** Wait for the player to look at LookTarget before starting. If they never do within LookTimeout, nothing fires. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Storm|LookGate")
	bool bLookGate = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Storm|LookGate")
	FVector LookTarget = FVector::ZeroVector;

	/** Half angle of the view cone around the camera's forward that counts as looking. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Storm|LookGate", meta = (ClampMin = "1", ClampMax = "90", Units = "deg"))
	float LookConeDegrees = 20.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Storm|LookGate", meta = (ClampMin = "0", Units = "s"))
	float LookTimeout = 90.f;
};

/** One rule of an ALBStateLightGroup. In the list, the last rule whose RequiredTag is present wins. */
USTRUCT(BlueprintType)
struct LASTBELL_API FLBLightStateRule
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Light")
	FGameplayTag RequiredTag;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Light")
	ELBLightStateMode Mode = ELBLightStateMode::On;

	/** Dim and Flicker: the fraction of the base intensity (the top of the flicker). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Light", meta = (ClampMin = "0", ClampMax = "2"))
	float IntensityScale = 1.f;

	/** Flicker: how far the intensity dips from IntensityScale (0 = steady, 1 = to zero). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Light", meta = (ClampMin = "0", ClampMax = "1"))
	float FlickerAmount = 0.4f;

	/** Flicker: noise frequency (Perlin input per second). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Light", meta = (ClampMin = "0"))
	float FlickerSpeed = 6.f;
};
