#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "Audio/LBAudioLogic.h"
#include "Audio/LBAudioTypes.h"
#include "LBAudioSettings.generated.h"

class AActor;
class USoundBase;
class USoundClass;
class USoundMix;

/** The weather beds (plan P16 section 2.2): four 2D loops. */
USTRUCT(BlueprintType)
struct LASTBELL_API FLBAudioWeather
{
	GENERATED_BODY()

	/** SFX_LB_Rain_Out: rain outdoors, a 2D loop. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather")
	TSoftObjectPtr<USoundBase> RainOut;

	/** SFX_LB_Rain_In: the muffled roof patter, a 2D loop. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather")
	TSoftObjectPtr<USoundBase> RainIn;

	/** SFX_LB_Wind: a 2D loop. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather")
	TSoftObjectPtr<USoundBase> Wind;

	/** SFX_LB_Wind_Howl: the tower and belfry howl, a 2D loop. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather")
	TSoftObjectPtr<USoundBase> WindHowl;
};

/** The thunder sets: variants are picked at random, never the same one twice in a row within a set. */
USTRUCT(BlueprintType)
struct LASTBELL_API FLBAudioThunder
{
	GENERATED_BODY()

	/** SFX_LB_Thunder_Near_01..04. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Thunder")
	TArray<TSoftObjectPtr<USoundBase>> Near;

	/** SFX_LB_Thunder_Mid_01..04. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Thunder")
	TArray<TSoftObjectPtr<USoundBase>> Mid;

	/** SFX_LB_Thunder_Far_01..04. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Thunder")
	TArray<TSoftObjectPtr<USoundBase>> Far;

	/** SFX_LB_Thunder_Strike_01..03: the sharp crack at the target of a tower strike. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Thunder")
	TArray<TSoftObjectPtr<USoundBase>> StrikeCrack;
};

/** The great bell, one recording per stage. */
USTRUCT(BlueprintType)
struct LASTBELL_API FLBAudioBell
{
	GENERATED_BODY()

	/** SFX_LB_Bell_Stage1..5, in order: entry 0 is stage 1 (the farthest), entry 4 is stage 5 (the finale). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell")
	TArray<TSoftObjectPtr<USoundBase>> Stage;
};

USTRUCT(BlueprintType)
struct LASTBELL_API FLBAudioMusic
{
	GENERATED_BODY()

	/** MUS_LB_Drone_A/B/C: 2D loops, one at a time, started by the story beats (FLBBellBeat::Drone indexes this array). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Music")
	TArray<TSoftObjectPtr<USoundBase>> Drones;

	/** MUS_LB_Tension: a 2D loop that rises with the Warden's threat. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Music")
	TSoftObjectPtr<USoundBase> Tension;

	/** MUS_LB_Chase: a 2D loop, only while the Warden chases. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Music")
	TSoftObjectPtr<USoundBase> Chase;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Music")
	TSoftObjectPtr<USoundBase> StingSpotted;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Music")
	TSoftObjectPtr<USoundBase> StingCaught;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Music")
	TSoftObjectPtr<USoundBase> StingApparition;
};

USTRUCT(BlueprintType)
struct LASTBELL_API FLBAudioPlayer
{
	GENERATED_BODY()

	/** SFX_LB_Breath_Calm_01..04. 2D one-shots. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Player")
	TArray<TSoftObjectPtr<USoundBase>> BreathCalm;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Player")
	TArray<TSoftObjectPtr<USoundBase>> BreathHeavy;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Player")
	TArray<TSoftObjectPtr<USoundBase>> BreathPanic;

	/** SFX_LB_Breath_Gasp_01..03: the sharp gasp when the candle goes out. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Player")
	TArray<TSoftObjectPtr<USoundBase>> BreathGasp;

	/** The candle was lit. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Player")
	TArray<TSoftObjectPtr<USoundBase>> CandleLight;

	/** The candle was snuffed. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Player")
	TArray<TSoftObjectPtr<USoundBase>> CandleOut;

	/** The relight started. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Player")
	TSoftObjectPtr<USoundBase> CandleRelight;
};

/** The Warden's sounds (plan P16 section 2.5), played by ULBWardenAudioComponent; the apparition's whisper is played by the audio subsystem. */
USTRUCT(BlueprintType)
struct LASTBELL_API FLBAudioWarden
{
	GENERATED_BODY()

	/** SFX_LB_Warden_Breath_Slow: a 3D loop for Patrol and Return. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Warden")
	TSoftObjectPtr<USoundBase> BreathSlow;

	/** A 3D loop for Investigate, Suspicious and Search. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Warden")
	TSoftObjectPtr<USoundBase> BreathFast;

	/** A 3D loop for Chase and Attack. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Warden")
	TSoftObjectPtr<USoundBase> BreathHeavy;

	/** SFX_LB_Warden_Step_01..05: one per 150 cm of walking. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Warden")
	TArray<TSoftObjectPtr<USoundBase>> Steps;

	/** SFX_LB_Warden_Chain_01..04: a clink with a step when the Warden moves faster than ChainSpeed. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Warden")
	TArray<TSoftObjectPtr<USoundBase>> Chains;

	/** SFX_LB_Warden_Robe: a 3D loop whose gain follows the speed. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Warden")
	TSoftObjectPtr<USoundBase> RobeLoop;

	/** The tell when the Warden spots the player (about 0.6 s before a chase). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Warden")
	TArray<TSoftObjectPtr<USoundBase>> Spotted;

	/** The tell on entering Chase. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Warden")
	TArray<TSoftObjectPtr<USoundBase>> Roar;

	/** The tell at the start of an attack wind-up. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Warden")
	TArray<TSoftObjectPtr<USoundBase>> Windup;

	/** When the Warden loses sight of the player. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Warden")
	TArray<TSoftObjectPtr<USoundBase>> Exhale;

	/** When the attack lands. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Warden")
	TArray<TSoftObjectPtr<USoundBase>> Caught;

	/** SFX_LB_Apparition_Whisper_01..03: where a ghostly figure appears (ALBWardenApparition). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Warden")
	TArray<TSoftObjectPtr<USoundBase>> ApparitionWhisper;

	/** Steps are one per this much walking, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Warden", meta = (ClampMin = "30", ClampMax = "400", Units = "cm"))
	float StepStride = 150.f;

	/** A chain clink joins the step above this speed, cm/s. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Warden", meta = (ClampMin = "0", ClampMax = "1000", Units = "cm/s"))
	float ChainSpeed = 150.f;

	/** The robe loop's gain is the speed divided by this, cm/s (the chase speed). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Warden", meta = (ClampMin = "10", ClampMax = "2000", Units = "cm/s"))
	float RobeFullSpeed = 420.f;

	/** The breath loops crossfade over this long, seconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Warden", meta = (ClampMin = "0", ClampMax = "10", Units = "s"))
	float BreathFade = 1.f;

	/** The Warden's footstep and chain volume, 0..2 (a mix trim on top of the SoundClass). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Warden", meta = (ClampMin = "0", ClampMax = "2"))
	float StepVolume = 1.f;
};

/**
 * What an interactable class sounds like (plan P16 section 2.2). The most specific class match wins; a class listed in
 * ULBAudioSettings::SilentClasses is silent on purpose.
 */
USTRUCT(BlueprintType)
struct LASTBELL_API FLBInteractionCue
{
	GENERATED_BODY()

	/** The actor class this row is for. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cue")
	TSoftClassPtr<AActor> ActorClass;

	/** Subclasses of ActorClass match too (a row for a more derived class beats this one). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cue")
	bool bIncludeSubclasses = true;

	/** Played when the interactable is used. A variant is picked at random, never the same twice in a row. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cue")
	TArray<TSoftObjectPtr<USoundBase>> Interact;

	/** Played when a use is refused (a locked door). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cue")
	TArray<TSoftObjectPtr<USoundBase>> Denied;

	/** Played when a dial or lever on this actor changes position. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cue")
	TArray<TSoftObjectPtr<USoundBase>> DialNotch;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cue", meta = (ClampMin = "0", ClampMax = "2"))
	float Volume = 1.f;

	/** Random pitch multiplier range (X to Y). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cue")
	FVector2D Pitch = FVector2D(0.97, 1.03);

	/** A note for people ("cloister bell: the sequence puzzle plays it"). Not used in code. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cue")
	FName Note;
};

/** The tension levels per Warden state (plan P16 section 2.2, Music). */
USTRUCT(BlueprintType)
struct LASTBELL_API FLBAudioTensionLevels
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tension", meta = (ClampMin = "0", ClampMax = "1"))
	float Patrol = 0.25f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tension", meta = (ClampMin = "0", ClampMax = "1"))
	float Suspicious = 0.5f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tension", meta = (ClampMin = "0", ClampMax = "1"))
	float Investigate = 0.6f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tension", meta = (ClampMin = "0", ClampMax = "1"))
	float Search = 0.8f;

	/** The tension layer's level during a chase (the chase layer carries the rest). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tension", meta = (ClampMin = "0", ClampMax = "1"))
	float Chase = 0.4f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tension", meta = (ClampMin = "0", ClampMax = "1"))
	float Return = 0.15f;
};

/**
 * Every sound and number of the audio director (plan P16 section 2.2) as one data asset: DA_Audio in /Game/LastBell/Data, linked from
 * ULBGameSettings::AudioSettings. ULBAudioSubsystem reads it through its pointer, so an edit in the Details panel (or over MCP) during
 * PIE shows at once (the sounds are loaded when the subsystem activates). The sounds are soft pointers, never hard references; the
 * defaults below are the plan's numbers.
 *
 * Never save the asset with DebugForceMusicState other than -1.
 */
UCLASS(BlueprintType)
class LASTBELL_API ULBAudioSettings : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	ULBAudioSettings();

	/**
	 * Fills BellBeats with the plan's story beats (section 5.3). Needs the project's gameplay tags to be registered; a tag that is
	 * not known is skipped with a warning. Tests and the asset-creation script call it.
	 */
	void FillPlanDefaults();

	/** Every soft sound reference with a name for logs, in a stable order (the preload and the Monastery.AudioSetup test use it). */
	struct FSoundEntry
	{
		FString Name;
		TSoftObjectPtr<USoundBase> Ref;
	};
	void CollectSounds(TArray<FSoundEntry>& Out) const;

	/**
	 * The row of InteractionCues that sounds for an actor of this class: the most specific match (the deepest class; a row matches a class
	 * when it is ActorClass, or a subclass of it with bIncludeSubclasses), or INDEX_NONE. bOutSilent is true when no row wins and a
	 * SilentClasses entry matches, or the silent class is more specific than the best row. Soft class pointers are loaded.
	 */
	int32 FindCueRow(const UClass* ActorClass, bool& bOutSilent) const;

	LBAudioLogic::FThunderParams MakeThunderParams() const;
	LBAudioLogic::FMusicParams MakeMusicParams() const;
	LBAudioLogic::FStressParams MakeStressParams() const;
	LBAudioLogic::FBreathThresholds MakeBreathThresholds() const;
	LBAudioLogic::FTollParams MakeTollParams() const;

	// ---- Sounds ---------------------------------------------------------------------------------------------------------------

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sounds")
	FLBAudioWeather Weather;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sounds")
	FLBAudioThunder Thunder;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sounds")
	FLBAudioBell Bell;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sounds")
	FLBAudioMusic Music;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sounds")
	FLBAudioPlayer Player;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sounds")
	FLBAudioWarden Warden;

	// ---- Interaction map ------------------------------------------------------------------------------------------------------

	/** What each interactable class sounds like. The most specific class match wins. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Interaction")
	TArray<FLBInteractionCue> InteractionCues;

	/** Interactable classes that are silent on purpose (Monastery.AudioSetup counts them as mapped). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Interaction")
	TArray<TSoftClassPtr<AActor>> SilentClasses;

	// ---- Small bells ----------------------------------------------------------------------------------------------------------

	/** Sequence step tag to the pitch multiplier of that bell (1 / its size, D-081). Filled from the level survey. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "SmallBells")
	TMap<FGameplayTag, float> SmallBellPitch;

	/** SFX_LB_SmallBell_Strike: pitched per bell by SmallBellPitch. Played at the bell that was struck. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "SmallBells")
	TSoftObjectPtr<USoundBase> SmallBellStrike;

	/** SFX_LB_SmallBell_Fail: the dissonant cluster of a wrong order. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "SmallBells")
	TSoftObjectPtr<USoundBase> SmallBellFail;

	/** SFX_LB_SmallBell_Solved: the four bells in order, then a low resonance. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "SmallBells")
	TSoftObjectPtr<USoundBase> SmallBellSolved;

	// ---- Mix ------------------------------------------------------------------------------------------------------------------

	/** Gain of the outdoor rain loop at full exposure. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mix", meta = (ClampMin = "0", ClampMax = "2"))
	float RainOutGain = 0.8f;

	/** Gain of the roof rain loop at no exposure under a full roof (zone RoofRain 1). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mix", meta = (ClampMin = "0", ClampMax = "2"))
	float RainInGain = 0.55f;

	/** RainOut = gain * exposure^power: above 1 the rain drops away faster as the player goes under cover. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mix", meta = (ClampMin = "0.1", ClampMax = "4"))
	float RainExposurePower = 0.7f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mix", meta = (ClampMin = "0", ClampMax = "2"))
	float WindOutGain = 0.6f;

	/** The wind loop's level at wind strength 0 (it rises to 1 at full strength). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mix", meta = (ClampMin = "0", ClampMax = "1"))
	float WindMin = 0.3f;

	/** The wind loop's pitch multiplier at strength 0 (X) and 1 (Y). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mix")
	FVector2D WindPitch = FVector2D(0.92, 1.08);

	/** The weather levels ease toward their targets over this long, seconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mix", meta = (ClampMin = "0", ClampMax = "10", Units = "s"))
	float MixFadeSeconds = 0.75f;

	/** The room tone crossfades over this long when the zone changes, seconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mix", meta = (ClampMin = "0", ClampMax = "10", Units = "s"))
	float RoomToneFadeSeconds = 2.f;

	/** The Darkness value of the open air (used outside every ALBAudioZone). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mix", meta = (ClampMin = "0", ClampMax = "1"))
	float OutdoorsDarkness = 0.1f;

	// ---- Thunder --------------------------------------------------------------------------------------------------------------

	/** Delay from the flash to the thunder at brightness 1 (X) and brightness 0 (Y), seconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Thunder")
	FVector2D ThunderDelay = FVector2D(0.6, 4.5);

	/** The delay is randomised by up to this much either way, seconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Thunder", meta = (ClampMin = "0", ClampMax = "3", Units = "s"))
	float ThunderJitter = 0.4f;

	/** A flash at or above this brightness has Near thunder. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Thunder", meta = (ClampMin = "0", ClampMax = "1"))
	float ThunderNearAt = 0.75f;

	/** A flash below this brightness has Far thunder. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Thunder", meta = (ClampMin = "0", ClampMax = "1"))
	float ThunderFarBelow = 0.4f;

	/** How far from the listener the thunder sits, along the flash's horizontal direction, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Thunder", meta = (ClampMin = "0", ClampMax = "200000", Units = "cm"))
	float ThunderDistance = 6000.f;

	/** The crack at a tower strike's target plays this long after the flash, seconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Thunder", meta = (ClampMin = "0", ClampMax = "2", Units = "s"))
	float StrikeCrackDelay = 0.12f;

	// ---- Bell -----------------------------------------------------------------------------------------------------------------

	/** The story beats of the great bell (FillPlanDefaults fills the plan's table). A beat fires only when its tag is added while playing. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell")
	TArray<FLBBellBeat> BellBeats;

	/** Toll stage 1 a few times after a new game starts (no beat tag present at activation). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell")
	bool bNewGameToll = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell", meta = (ClampMin = "0", ClampMax = "60", Units = "s"))
	float NewGameTollDelay = 6.f;

	/** Strikes of the new-game toll. An addition to the plan (5.3 says 3). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell", meta = (ClampMin = "1", ClampMax = "12"))
	int32 NewGameTollStrikes = 3;

	/** Seconds between the strikes of the new-game toll. An addition to the plan (5.3 says 4.5). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell", meta = (ClampMin = "0", ClampMax = "30", Units = "s"))
	float NewGameTollSpacing = 4.5f;

	/** The drone the new-game toll starts (an index into Music.Drones, -1 none). An addition to the plan (5.3 says Drone A). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell", meta = (ClampMin = "-1", ClampMax = "7"))
	int32 NewGameDrone = 0;

	/** Where the great bell sounds from (the tower bell). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell", meta = (Units = "cm"))
	FVector BellLocation = FVector::ZeroVector;

	/** Reserved for the bell's attenuation tuning; not read by code (the attenuation is on the sound asset). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell", meta = (ClampMin = "0", ClampMax = "100000", Units = "cm"))
	float BellNearDistance = 2500.f;

	/** Seconds between strikes for PlayBell (the API and lb.Audio.Bell). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell", meta = (ClampMin = "0", ClampMax = "30", Units = "s"))
	float PlayBellSpacing = 4.5f;

	/** Occasional distant tolls between the story beats. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell|Ambient")
	bool bAmbientTolls = true;

	/** Seconds from one toll (of any kind) to the next ambient one, drawn between X and Y. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell|Ambient")
	FVector2D AmbientTollInterval = FVector2D(240.0, 420.0);

	/** Strikes of an ambient toll, drawn between X and Y. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell|Ambient")
	FVector2D AmbientTollStrikes = FVector2D(1.0, 2.0);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell|Ambient", meta = (ClampMin = "0", ClampMax = "2"))
	float AmbientTollVolume = 0.5f;

	/** No ambient toll within this long of a story beat's toll, seconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell|Ambient", meta = (ClampMin = "0", ClampMax = "600", Units = "s"))
	float AmbientTollGapAfterBeat = 90.f;

	/** No ambient toll while the tension layer is above this. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell|Ambient", meta = (ClampMin = "0", ClampMax = "1"))
	float AmbientTollMaxTension = 0.5f;

	/** Seconds between the strikes of an ambient toll. An addition to the plan. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell|Ambient", meta = (ClampMin = "0", ClampMax = "30", Units = "s"))
	float AmbientTollSpacing = 4.5f;

	// ---- Music ----------------------------------------------------------------------------------------------------------------

	/** A drone holds this long at full level before it fades out, seconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Music", meta = (ClampMin = "0", ClampMax = "300", Units = "s"))
	float DroneSeconds = 45.f;

	/** A drone's fade in (X) and fade out (Y), seconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Music")
	FVector2D DroneFade = FVector2D(6.0, 8.0);

	/** The tension layer only rises for a Warden at most this far from the player, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Music", meta = (ClampMin = "0", ClampMax = "100000", Units = "cm"))
	float TensionNearDistance = 2500.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Music")
	FLBAudioTensionLevels TensionLevels;

	/** The chase layer's level in a chase. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Music", meta = (ClampMin = "0", ClampMax = "1"))
	float ChaseLevel = 1.f;

	/** The chase layer's fade in (X) and out (Y), seconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Music")
	FVector2D ChaseFade = FVector2D(0.8, 4.0);

	/** The tension layer's fade in (X) and out (Y), seconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Music")
	FVector2D TensionFade = FVector2D(3.0, 10.0);

	/** The tension layer is silent until the Warden's stage (State.Warden.Stage.N) reaches this. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Music", meta = (ClampMin = "0", ClampMax = "6"))
	int32 MusicMinStage = 3;

	// ---- Stress and breathing -------------------------------------------------------------------------------------------------

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stress", meta = (ClampMin = "0", ClampMax = "1"))
	float StressChase = 1.f;

	/** Stress while the Warden is within StressNearDistance and Investigating, Searching or Suspicious. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stress", meta = (ClampMin = "0", ClampMax = "1"))
	float StressNearSearch = 0.6f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stress", meta = (ClampMin = "0", ClampMax = "100000", Units = "cm"))
	float StressNearDistance = 1500.f;

	/** Added to the stress target for StressSprintSeconds after a sprint. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stress", meta = (ClampMin = "0", ClampMax = "1"))
	float StressSprintBonus = 0.3f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stress", meta = (ClampMin = "0", ClampMax = "30", Units = "s"))
	float StressSprintSeconds = 3.f;

	/** Stress falls this much per second toward a lower target. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stress", meta = (ClampMin = "0.01", ClampMax = "5"))
	float StressDecay = 0.25f;

	/** Stress rises this much per second toward a higher target. An addition to the plan. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stress", meta = (ClampMin = "0.01", ClampMax = "10"))
	float StressRise = 0.6f;

	/** The darkness stress floor is zone Darkness times this with the candle lit... */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stress", meta = (ClampMin = "0", ClampMax = "1"))
	float DarknessLit = 0.15f;

	/** ...and times this with the candle out. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stress", meta = (ClampMin = "0", ClampMax = "1"))
	float DarknessUnlit = 0.55f;

	/** The candle going out adds this to the stress at once. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stress", meta = (ClampMin = "0", ClampMax = "1"))
	float CandleOutStress = 0.35f;

	/** Seconds between breaths, drawn between X and Y, while the stress is at least BreathCalmAt. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stress")
	FVector2D BreathInterval = FVector2D(2.4, 4.0);

	/** Calm breaths from this stress... */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stress", meta = (ClampMin = "0", ClampMax = "1"))
	float BreathCalmAt = 0.3f;

	/** ...heavy breaths from this... */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stress", meta = (ClampMin = "0", ClampMax = "1"))
	float BreathHeavyAt = 0.55f;

	/** ...panicked breaths from this. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stress", meta = (ClampMin = "0", ClampMax = "1"))
	float BreathPanicAt = 0.85f;

	// ---- User volumes ---------------------------------------------------------------------------------------------------------

	/** SMX_LB_User: one adjuster per SoundClass; the user volumes are class overrides on it. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "UserVolumes")
	TSoftObjectPtr<USoundMix> UserMix;

	/** The SoundClasses by group: keys Master, SFX, Ambience, Music, Voice, UI (SCL_LB_*). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "UserVolumes")
	TMap<FName, TSoftObjectPtr<USoundClass>> UserClasses;

	// ---- Misc / debug ---------------------------------------------------------------------------------------------------------

	/** The audio director's random seed; 0 draws a different one every run. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Debug")
	int32 RandomSeed = 0;

	/**
	 * -1 none; 0..7 forces the Warden state the music and the tension read (ELBWardenState: 0 Dormant, 1 Patrol, 2 Investigate, 3 Suspicious,
	 * 4 Search, 5 Chase, 6 Attack, 7 Return), for tuning. Never save with a value other than -1.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Debug", meta = (ClampMin = "-1", ClampMax = "7"))
	int32 DebugForceMusicState = -1;
};
