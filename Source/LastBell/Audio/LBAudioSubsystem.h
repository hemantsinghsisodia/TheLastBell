#pragma once

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"
#include "Math/RandomStream.h"
#include "Subsystems/WorldSubsystem.h"
#include "AI/LBWardenTypes.h"
#include "Audio/LBAudioLogic.h"
#include "Audio/LBAudioTypes.h"
#include "Storm/LBStormTypes.h"
#include "LBAudioSubsystem.generated.h"

class AActor;
class ALBAudioZone;
class ALBCharacter;
class ALBWarden;
class ALBWardenApparition;
class UAudioComponent;
class ULBAudioSettings;
class ULBAudioSubsystem;
class ULBInspectableComponent;
class ULBInspectionComponent;
class ULBInteractableComponent;
class ULBStormSubsystem;
class ULBWardenBrainComponent;
class USceneComponent;
class USoundBase;
class USoundMix;
class ULBWorldStateSubsystem;
struct FLBInteractionCue;

/** The moment any great-bell strike starts (beats, the new-game toll, ambient tolls, PlayBell), never for the small bells: Stage 1..5 and the volume. */
DECLARE_MULTICAST_DELEGATE_TwoParams(FOnLBGreatBellStrike, int32 /*Stage*/, float /*Volume*/);

/** One play request, as the test sink records it (non-shipping builds). Loops record one request when they start. */
struct FLBAudioRequest
{
	/** One of LBAudioCue::*. */
	FName Cue;
	/** World time the sound was started (a scheduled sound is recorded when it plays, not when it was asked for). */
	double Time = 0.0;
	/** Where it plays (positional sounds). Zero for 2D. */
	FVector Location = FVector::ZeroVector;
	bool bPositional = false;
	float Volume = 1.f;
	float Pitch = 1.f;
	/** Which variant of the set was picked, or INDEX_NONE. */
	int32 Variant = INDEX_NONE;
	/** Cue-specific: thunder set (0 far, 1 mid, 2 near), bell stage, breath tier, interaction cue index. */
	int32 Aux = 0;
	/** The soft sound reference loaded (false when it is unset or does not load: the request is still recorded). */
	bool bSoundResolved = false;
};

/** The loops the subsystem owns, in the order of ULBAudioSubsystem::GetLayerLevel. */
enum class ELBAudioLayer : uint8
{
	RainOut,
	RainIn,
	Wind,
	WindHowl,
	RoomA,
	RoomB,
	Drone,
	Tension,
	Chase,
	Count
};

/**
 * A looping sound with a level that eases toward a target. Update creates the audio component when the level first rises above zero,
 * follows the level with its volume, and stops it when the level is back at zero. Without an audio device (-nosound) the component
 * is never created, but the level, and the request recorded at the start, behave the same. Used by the subsystem (2D) and by the
 * Warden audio component and the ambient emitter (attached to an actor).
 */
struct LASTBELL_API FLBAudioLoop
{
	TWeakObjectPtr<UAudioComponent> Component;
	TWeakObjectPtr<USoundBase> LoadedSound;
	float Level = 0.f;
	float AppliedVolume = -1.f;
	float AppliedPitch = -1.f;
	bool bStarted = false;

	/**
	 * Eases Level toward Target (In or Out seconds for the whole 0..1 range) and applies it. Ref is the sound (may change between calls:
	 * the loop restarts with the new one). AttachTo null makes a 2D loop. A null or unloadable Ref plays nothing.
	 */
	void Update(ULBAudioSubsystem& Audio, FName Cue, const TSoftObjectPtr<USoundBase>& Ref, USceneComponent* AttachTo, float Target, float InSeconds,
		float OutSeconds, float Pitch, float DeltaSeconds);

	/** Stops now and forgets the component. */
	void Stop();

	/** Fades the component out over Seconds and forgets it. */
	void FadeOutAndForget(float Seconds);
};

/**
 * Forwards the delegates of one actor's interactable, dial and sequence-puzzle components to the audio subsystem. Those delegates
 * do not say which actor fired, so each bound actor gets one proxy. Internal; owned by ULBAudioSubsystem.
 */
UCLASS()
class LASTBELL_API ULBAudioProxy : public UObject
{
	GENERATED_BODY()

public:
	TWeakObjectPtr<ULBAudioSubsystem> Owner;
	TWeakObjectPtr<AActor> Actor;

	/** Binds every relevant component the actor has now (idempotent). */
	void BindComponents();
	void UnbindComponents();

	UFUNCTION()
	void HandleInteracted(AActor* Instigator);
	UFUNCTION()
	void HandleDenied(AActor* Instigator);
	UFUNCTION()
	void HandleDialChanged(int32 NewIndex);
	UFUNCTION()
	void HandleStepAccepted(int32 Index, FGameplayTag Step);
	UFUNCTION()
	void HandlePuzzleFailed(FGameplayTag WrongStep);
	UFUNCTION()
	void HandlePuzzleSolved();
};

/**
 * The audio director (plan P16 section 2.3). It listens to the storm, the world state, the Warden and the interactables, and plays
 * the weather beds, thunder, the great bell's tolls, the music layers, the player's breath and candle, and the interaction cues. All
 * sounds come from ULBAudioSettings (DA_Audio) as soft pointers; every sound is null-safe (an unset or unloadable one logs once and
 * plays nothing, and a world with no audio device, -nosound, records the request all the same).
 *
 * It exists in Game and PIE worlds only. Activation mirrors ULBStormFXSubsystem: lazy, in Tick, on the first tick where the storm is
 * active (the monastery is the only map with a storm, so the main menu and the test maps stay silent unless a test overrides the
 * settings). lb.Audio.Enabled 0 switches it off (everything fades out over 0.5 s and the delegates are unbound) and 1 brings it back.
 *
 * Design choices that differ from the plan text: thunder binds ULBStormSubsystem::OnLightningStrike only (it carries the brightness,
 * the reason, the direction and the target of the same flash that OnLightningFlash announces); the room tone has two loop slots so
 * it can crossfade; the apparition's whisper is played here, from the apparition's OnAppeared event.
 */
UCLASS()
class LASTBELL_API ULBAudioSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	// ---- Subsystem plumbing ---------------------------------------------------------------------------------------------------
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;
	/** Ticks while active or still waiting for the storm's first active tick. */
	virtual bool IsTickable() const override { return !bGaveUp; }
	/** True: the great bell of the ending must keep tolling while the ending sequence pauses the game (P16-6). */
	virtual bool IsTickableWhenPaused() const override { return true; }

	// ---- Control --------------------------------------------------------------------------------------------------------------

	/** Uses these settings instead of ULBGameSettings::AudioSettings (tests, tools). Call Rearm afterwards. */
	void OverrideSettings(ULBAudioSettings* InSettings);

	/** Starts ticking again after the subsystem gave up on an inactive storm. Tests that spawn the tagged moon after BeginPlay call it. */
	void Rearm();

	/**
	 * Binds every interactable, dial, sequence puzzle and apparition in the world that is not bound yet. Activation and OnActorSpawned
	 * call it; a test or a tool that adds a component to a spawned actor later calls it too.
	 */
	void RefreshBindings();

	/**
	 * Tolls the great bell: Strikes strikes of the stage (1 to 5) from now, PlayBellSpacing seconds apart, at BellLocation. For the
	 * finale sequence of Phase 17 and lb.Audio.Bell. Does nothing while the subsystem is inactive.
	 */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Audio")
	void PlayBell(int32 Stage, int32 Strikes);

	/** Pushes the user volume groups (ULBUserSettings) onto the SoundMix. Activation and a change of the user settings call it. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Audio")
	void ApplyUserVolumes();

	void RegisterZone(ALBAudioZone* Zone);
	void UnregisterZone(ALBAudioZone* Zone);

	/** lb.Audio.Music: forces the Warden state the music reads (an ELBWardenState value), or -1 to clear. */
	void SetConsoleMusicState(int32 State) { ConsoleMusicState = State; }

	/** lb.Audio.Thunder: plays one thunder of the set now (0 far, 1 mid, 2 near), from the front of the view. */
	void PlayDebugThunder(int32 Set);

	void SetDebugOverlay(bool bOn) { bDebugOverlay = bOn; }

	// ---- Playing (used by the Warden audio component, the ambient emitter and the footsteps) ------------------------------------

	/** Plays a 2D one-shot. Records the request. Returns the component (null without an audio device or when the sound is not available). */
	UAudioComponent* Play2D(FName Cue, const TSoftObjectPtr<USoundBase>& Ref, float Volume = 1.f, float Pitch = 1.f, int32 Variant = INDEX_NONE, int32 Aux = 0);

	/** Plays a positional one-shot at a place (the sound asset's own attenuation). */
	UAudioComponent* PlayAt(FName Cue, const TSoftObjectPtr<USoundBase>& Ref, const FVector& Location, float Volume = 1.f, float Pitch = 1.f, int32 Variant = INDEX_NONE, int32 Aux = 0);

	/** Plays a one-shot that follows a component. */
	UAudioComponent* PlayAttached(FName Cue, const TSoftObjectPtr<USoundBase>& Ref, USceneComponent* AttachTo, float Volume = 1.f, float Pitch = 1.f, int32 Variant = INDEX_NONE, int32 Aux = 0);

	/** Loads a soft sound (null when unset or missing; one log line per cue). Loaded sounds are kept alive by the subsystem. */
	USoundBase* ResolveSound(const TSoftObjectPtr<USoundBase>& Ref, FName Cue);

	/** A random variant of the set that is not the one picked last for Key (INDEX_NONE for an empty set). */
	int32 PickVariantFor(FName Key, int32 Count);

	float RandomFraction() { return Stream.FRand(); }
	float RandomRange(float Min, float Max) { return Stream.FRandRange(Min, FMath::Max(Min, Max)); }

	/**
	 * Broadcast the moment a great-bell strike starts playing (P17: the cinematic subsystem swings the bell on it). Fires for story beats,
	 * the new-game toll, ambient tolls and PlayBell; never for the small bells.
	 */
	FOnLBGreatBellStrike OnGreatBellStrike;

	// ---- Queries --------------------------------------------------------------------------------------------------------------

	/** The audio director is running: the storm is active, the settings loaded and lb.Audio.Enabled is 1. */
	UFUNCTION(BlueprintPure, Category = "LastBell|Audio")
	bool IsActive() const { return bActive; }

	const ULBAudioSettings* GetSettings() const { return Settings; }

	/** The player's stress level 0..1 (breathing). */
	UFUNCTION(BlueprintPure, Category = "LastBell|Audio")
	float GetStress() const { return StressLevel; }

	/** The eased level of a loop, 0..1 (the volume it is played at). */
	float GetLayerLevel(ELBAudioLayer Layer) const;

	/** The target levels the music layers move toward right now (tension, chase). */
	LBAudioLogic::FMusicTargets GetMusicTargets() const { return LastMusicTargets; }

	/** The Warden state the music reads: the debug force, else the Warden's own. */
	ELBWardenState GetEffectiveWardenState() const;

	/** The zone the listener is in, or null outdoors. */
	const ALBAudioZone* GetCurrentZone() const { return CurrentZone.Get(); }

	/** The highest bell stage reached by the beats so far (1 at the start). */
	int32 GetBellStage() const { return BellStageReached; }

	/** Seconds on the world clock when the next ambient toll is due. */
	double GetNextTollTime() const { return NextTollTime; }

	/** The volume last pushed for a group (Master, SFX, Ambience, Music, Voice, UI), or -1. */
	float GetAppliedVolume(ELBAudioVolumeGroup Group) const;

	int32 GetBoundActorCount() const { return Proxies.Num(); }

	/** Sounds scheduled but not yet played. */
	int32 GetScheduledCount() const { return Scheduled.Num(); }

	/** The listener: the player camera, else the last rendered view. False when there is none. */
	bool GetListenerLocation(FVector& OutLocation) const;

	// ---- Test sink (non-shipping) ---------------------------------------------------------------------------------------------

	/** Records a request made outside the subsystem (footsteps, the Warden component, the emitter). A no-op in shipping builds. */
	void RecordRequest(const FLBAudioRequest& Request);

#if !UE_BUILD_SHIPPING
	const TArray<FLBAudioRequest>& GetRequests() const { return Requests; }
	void ClearRequests() { Requests.Reset(); }
	int32 CountRequests(FName Cue) const;
#endif

	// ---- Events from the proxies (public so the proxy can call them) ----------------------------------------------------------

	void NotifyInteracted(AActor* Actor, bool bDenied);
	void NotifyDialChanged(AActor* Actor, int32 NewIndex);
	void NotifyStepAccepted(AActor* Actor, int32 Index, FGameplayTag Step);
	void NotifyPuzzleFailed(AActor* Actor, FGameplayTag WrongStep);
	void NotifyPuzzleSolved(AActor* Actor);

protected:
	/** Game and PIE worlds only. */
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;

private:
	struct FScheduled
	{
		enum class EKind : uint8 { Thunder, Crack, Bell, Drone };
		double Time = 0.0;
		EKind Kind = EKind::Thunder;
		/** Thunder: set. Bell: stage. Drone: index. */
		int32 Aux = 0;
		float Volume = 1.f;
		FVector Location = FVector::ZeroVector;
		/** Thunder: the direction (horizontal, unit) from the listener. */
		FVector Direction = FVector::ForwardVector;
		bool bAmbient = false;
		/**
		 * Time is on World->GetUnpausedTimeSeconds() (which keeps running while the game is paused) instead of GetTimeSeconds().
		 * The great bell's strikes use it so the finale keeps tolling under the ending's pause (P16-6).
		 */
		bool bUnpausedClock = false;
	};

	// ---- Activation ----
	bool TryActivate(ULBStormSubsystem& Storm);
	void Deactivate();
	void BindWorldEvents();
	void UnbindWorldEvents();
	void PreloadSounds();

	// ---- Delegates ----
	UFUNCTION()
	void HandleLightningStrike(const FLBLightningStrikeInfo& Info);
	UFUNCTION()
	void HandleStateChanged(FGameplayTag Tag, bool bAdded);
	UFUNCTION()
	void HandleStateReplaced();
	UFUNCTION()
	void HandlePlayerSpotted();
	UFUNCTION()
	void HandlePlayerCaught();
	UFUNCTION()
	void HandleCandleState(bool bLit);
	UFUNCTION()
	void HandleRelightStarted();
	/** The player opened an inspection: a note rustles on pick-up. */
	UFUNCTION()
	void HandleInspectBegin(ULBInspectableComponent* Inspectable);
	/**
	 * The inspection ended (kept or put back, including CancelInspect, which never fires OnInteracted): the inspected actor's
	 * Interact cue plays again as the put-down. A kept item already played it through OnInteracted in the same frame; that one is not doubled.
	 */
	UFUNCTION()
	void HandleInspectEnd(bool bKept);
	UFUNCTION()
	void HandleApparitionAppeared(ALBWardenApparition* Apparition, int32 StationIndex);

	void HandleActorSpawned(AActor* Actor);
	void HandleUserVolumesChanged();

	// ---- Per frame ----
	void TickWorld(UWorld& World, ULBStormSubsystem& Storm, float DeltaSeconds);
	void UpdateScheduled(double Now, double UnpausedNow, bool bPaused);
	void UpdateZone(double Now);
	void UpdateWardenLink(double Now);
	void UpdateWeather(const ULBStormSubsystem& Storm, float DeltaSeconds);
	void UpdateRoomTone(float DeltaSeconds);
	void UpdateMusic(double Now, float DeltaSeconds);
	void UpdateStress(double Now, float DeltaSeconds);
	void UpdateAmbientToll(double Now);
	void DrawDebugOverlay(double Now);

	// ---- Helpers ----
	void BindPlayerEvents();
	/** The Interact / Denied row play of NotifyInteracted, without the same-frame inspection bookkeeping. */
	void PlayInteractCue(AActor* Actor, bool bDenied);
	/** bPlayFirstNow: when FirstDelay <= 0 the first strike plays in this call and only the rest are scheduled (story beats). */
	void ScheduleBell(int32 Stage, int32 Strikes, float FirstDelay, float Spacing, bool bAmbient, bool bPlayFirstNow = false);
	void ScheduleDrone(int32 Drone, float Delay);
	void StartDrone(int32 Drone, double Now);
	void PlayScheduled(const FScheduled& Item, double Now);
	void PlayThunder(int32 Set, float Volume, const FVector& Direction);
	void PlaySting(FName Cue, const TSoftObjectPtr<USoundBase>& Ref);
	AActor* FindStepActor(const FGameplayTag& Step) const;
	/** True when Step is a key of DA_Audio.SmallBellPitch: only the cloister bell puzzle's steps use the small-bell sounds. */
	bool IsBellStep(const FGameplayTag& Step) const;
	/** True when a sequence puzzle component on Actor has a step that IsBellStep. */
	bool IsBellPuzzle(const AActor* Actor) const;
	const FLBInteractionCue* FindInteractionCue(const AActor* Actor, int32& OutIndex, bool& bOutSilent);
	bool GetPlayerFacts(FVector& OutLocation, bool& bOutSprinting, bool& bOutCandleLit) const;
	ALBCharacter* GetPlayer() const;
	void Remember(USoundBase* Sound);
	void WarnOnce(FName Key, const TCHAR* Text, const FString& Detail);
	bool IsBeatTagPresent() const;

	UPROPERTY(Transient)
	TObjectPtr<ULBAudioSettings> Settings;

	/** Set by OverrideSettings; used instead of the configured asset. */
	UPROPERTY(Transient)
	TObjectPtr<ULBAudioSettings> SettingsOverride;

	/** Keeps the loaded sounds alive (the settings hold soft pointers only). */
	UPROPERTY(Transient)
	TArray<TObjectPtr<USoundBase>> LoadedSounds;

	UPROPERTY(Transient)
	TArray<TObjectPtr<ULBAudioProxy>> Proxies;

	UPROPERTY(Transient)
	TObjectPtr<USoundMix> PushedMix;

	TWeakObjectPtr<ULBStormSubsystem> BoundStorm;
	TWeakObjectPtr<ULBWorldStateSubsystem> BoundState;
	TWeakObjectPtr<ULBWardenBrainComponent> BoundBrain;
	TWeakObjectPtr<UObject> BoundCandle;
	TWeakObjectPtr<UObject> BoundInspection;
	/** The actor of the running inspection (from OnInspectBegin), so OnInspectEnd (which carries no actor) can play its put-down cue. */
	TWeakObjectPtr<AActor> InspectedActor;
	/** Same-frame markers so a kept item's Interact cue is not played twice (OnInteracted and OnInspectEnd both fire on a keep). */
	TWeakObjectPtr<AActor> LastInteractedActor;
	uint64 LastInteractedFrame = 0;
	TWeakObjectPtr<AActor> LastInspectEndActor;
	uint64 LastInspectEndFrame = 0;
	TWeakObjectPtr<ALBWarden> CachedWarden;
	TWeakObjectPtr<const ALBAudioZone> CurrentZone;
	TArray<TWeakObjectPtr<ALBAudioZone>> Zones;
	TSet<TWeakObjectPtr<ALBWardenApparition>> BoundApparitions;
	FDelegateHandle ActorSpawnedHandle;
	FDelegateHandle UserVolumesHandle;

	FRandomStream Stream;
	TArray<FScheduled> Scheduled;
	TMap<FName, int32> LastVariant;
	TSet<FName> WarnedKeys;
	float AppliedVolumes[6] = { -1.f, -1.f, -1.f, -1.f, -1.f, -1.f };

	FLBAudioLoop Loops[static_cast<int32>(ELBAudioLayer::Count)];

	bool bActive = false;
	/** The subsystem has been active at least once, so it keeps waiting for the storm and the CVar. */
	bool bEverActive = false;
	/** Stops IsTickable: the world began play with no active storm, or the settings did not load. */
	bool bGaveUp = false;
	bool bWarnedNoSettings = false;
	bool bDebugOverlay = false;
	bool bFinaleReached = false;
	FGameplayTag FinaleTag;

	// Weather and rooms
	int32 ActiveRoomSlot = 0;
	TSoftObjectPtr<USoundBase> RoomSlotRef[2];
	TWeakObjectPtr<const ALBAudioZone> RoomZone;
	bool bRoomInitialised = false;
	double NextZoneCheck = 0.0;
	double NextWardenSearch = 0.0;

	// Warden facts
	ELBWardenState RealWardenState = ELBWardenState::Dormant;
	int32 WardenStage = 0;
	float WardenDistance = 1.0e9f;
	int32 ConsoleMusicState = -1;
	LBAudioLogic::FMusicTargets LastMusicTargets;

	// Drone
	int32 DronePlaying = -1;
	int32 DroneRequested = -1;
	double DroneFadeOutAt = 0.0;

	// Bell
	int32 BellStageReached = 1;
	double LastBeatTime = -1.0e9;
	double NextTollTime = 0.0;

	// Stress
	float StressLevel = 0.f;
	float SprintBonusLeft = 0.f;
	bool bCandleOutImpulse = false;
	bool bCandleLit = true;
	double NextBreathAt = 0.0;

	/** The listener's last known place, kept for the frames when there is no view. */
	FVector LastListener = FVector::ZeroVector;
	bool bHasListener = false;

#if !UE_BUILD_SHIPPING
	TArray<FLBAudioRequest> Requests;
#endif
};
