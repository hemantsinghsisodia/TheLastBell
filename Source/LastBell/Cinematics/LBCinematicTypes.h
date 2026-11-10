#pragma once

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"
#include "Character/LBPlayerTypes.h"
#include "Engine/EngineTypes.h"
#include "LBCinematicTypes.generated.h"

class ULevelSequence;

/** What starts a cinematic by itself. */
UENUM(BlueprintType)
enum class ELBCineTrigger : uint8
{
	/** The first tick of the New Game map when the world is not a restore (not Continue, a death reload or a checkpoint load). */
	NewGame,
	/** The moment TriggerTag is added to the world state. A replace (a load) never triggers. */
	TagAdded
};

/** How a card is drawn (section 3.3). */
UENUM(BlueprintType)
enum class ELBCineCardStyle : uint8
{
	/** A centred line of story text. */
	Line,
	/** The large, letter-spaced title. */
	Title
};

/** One credits line's look (section 2.9). */
UENUM(BlueprintType)
enum class ELBCreditStyle : uint8
{
	Heading,
	Name,
	Small,
	/** A 40 px spacer. */
	Gap
};

/** Which local axis of the bell's axle the swing turns about (section 2.8). */
UENUM(BlueprintType)
enum class ELBBellSwingAxis : uint8
{
	/** The axle is the headstock's local Y. */
	Pitch,
	/** The axle is the headstock's local X. */
	Roll
};

/** One cinematic: a Level Sequence and the rules around playing it (section 2.2). Soft references only. */
USTRUCT(BlueprintType)
struct LASTBELL_API FLBCinematicDef
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cinematic")
	FName Id;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cinematic")
	TSoftObjectPtr<ULevelSequence> Sequence;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cinematic")
	ELBCineTrigger Trigger = ELBCineTrigger::NewGame;

	/** TagAdded only: the world-state tag whose addition plays this cinematic. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cinematic", meta = (EditCondition = "Trigger == ELBCineTrigger::TagAdded"))
	FGameplayTag TriggerTag;

	/** The cinematic never starts by itself while this tag is present in the world state. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cinematic")
	FGameplayTag BlockingTag;

	/** The player's input lock from the first frame. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cinematic")
	ELBInputLock InitialLock = ELBInputLock::Full;

	/** The screen is black from the first frame (the NewGame trigger fades to black at world begin play, before the first tick). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cinematic")
	bool bStartBlack = false;

	/** Holding Interact skips from the very start. A skip:0 or skip:1 marker changes it later. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cinematic")
	bool bSkippableAtStart = false;

	/** Added to the world state when the cinematic starts. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cinematic")
	FGameplayTagContainer GrantOnStart;

	/**
	 * P17-1 DEVIATION (not in plan section 2.2): marker labels (the same grammar as the sequence's, every one treated as a must marker)
	 * that fire when the sequence itself cannot be loaded, since a missing sequence has no markers to read. Intro: "!tag:State.Event.Arrival";
	 * Finale: "!end". Empty means a failed cinematic only restores. Filled by P17-2 in DA_Cinematics.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cinematic")
	TArray<FString> FailSafeMarkers;
};

/** One story card (section 3.3). */
USTRUCT(BlueprintType)
struct LASTBELL_API FLBCineCard
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Card")
	FText Text;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Card")
	ELBCineCardStyle Style = ELBCineCardStyle::Line;

	/** Seconds the card stays fully visible. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Card", meta = (ClampMin = "0.0", ClampMax = "60.0", Units = "s"))
	float HoldSeconds = 2.4f;

	/** Seconds of the fade in, and again of the fade out. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Card", meta = (ClampMin = "0.0", ClampMax = "10.0", Units = "s"))
	float FadeSeconds = 0.3f;
};

/** One line of the credits roll. */
USTRUCT(BlueprintType)
struct LASTBELL_API FLBCreditLine
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Credits")
	ELBCreditStyle Style = ELBCreditStyle::Name;

	/** Ignored for a Gap. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Credits")
	FText Text;
};

/** What a marker does (section 2.1). */
enum class ELBCineMarkerKind : uint8
{
	Card,
	Tag,
	Bell,
	Strike,
	Flash,
	Look,
	Mark,
	Lock,
	Skip,
	Mix,
	Credits,
	End
};

/** One parsed Sequencer marker, with its time in seconds from the start of the playback range. Pure data (not a USTRUCT). */
struct LASTBELL_API FLBCineMarker
{
	/** Seconds from the start of the sequence's playback range. */
	double Seconds = 0.0;
	/** The label as authored. */
	FString Label;
	/** A leading '!': a skip fires it if it has not fired yet. */
	bool bMust = false;
	ELBCineMarkerKind Kind = ELBCineMarkerKind::End;

	/** Card: the card id. Strike, Look, Mark: the actor tag. */
	FName Name;
	/** Tag: the world-state tag. */
	FGameplayTag Tag;
	/** Bell: the stage 1..5 and the number of strikes. */
	int32 Stage = 0;
	int32 Strikes = 0;
	/** Strike, Flash: the brightness. Look, Mark, Credits: the seconds. Negative means "use the default". */
	float Value = -1.f;
	/** Lock. */
	ELBInputLock Lock = ELBInputLock::None;
	/** Skip: skippable from here. Mix: pushed (on). */
	bool bFlag = false;
};
