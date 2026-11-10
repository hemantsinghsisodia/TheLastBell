// NOTE: this file defines the CVar lb.Audio.Enabled. Never Live Code it (MCP_NOTES, "PIE Simulate captures and Live Coding" item 2).
#include "Audio/LBAudioSubsystem.h"
#include "Audio/LBAudioSettings.h"
#include "Audio/LBAudioZone.h"
#include "AI/LBWarden.h"
#include "AI/LBWardenApparition.h"
#include "AI/LBWardenBrainComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Character/LBCandleComponent.h"
#include "Character/LBCharacter.h"
#include "Character/LBInspectionComponent.h"
#include "Components/AudioComponent.h"
#include "Components/LBInteractableComponent.h"
#include "Components/LBInspectableComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Puzzles/LBDialComponent.h"
#include "Puzzles/LBSequencePuzzleComponent.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundClass.h"
#include "Sound/SoundMix.h"
#include "Storm/LBStormSubsystem.h"
#include "Systems/LBGameSettings.h"
#include "Systems/LBUserSettings.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "AudioDevice.h"
#include "LBLog.h"

namespace
{
#if !UE_BUILD_SHIPPING
	TAutoConsoleVariable<int32> CVarAudioEnabled(
		TEXT("lb.Audio.Enabled"), 1,
		TEXT("1 = the audio director runs (weather, thunder, bell, music, breath, interaction cues). 0 = everything fades out and the director unbinds. Non-shipping."),
		ECVF_Default);
#endif

	bool IsAudioEnabled()
	{
#if !UE_BUILD_SHIPPING
		return CVarAudioEnabled.GetValueOnGameThread() != 0;
#else
		return true;
#endif
	}

	/** A loop whose level is below this is not played. */
	constexpr float LoopOnThreshold = 0.003f;
	constexpr int32 MaxRequests = 4096;
	constexpr int32 MaxScheduled = 256;
	constexpr double ZoneCheckInterval = 0.25;
	constexpr double WardenSearchInterval = 1.0;
	constexpr float DeactivateFadeSeconds = 0.5f;

	constexpr int32 DroneLayerSlot = static_cast<int32>(ELBAudioLayer::Drone);

	FVector Horizontal(const FVector& Direction)
	{
		FVector Out(Direction.X, Direction.Y, 0.0);
		return Out.Normalize() ? Out : FVector::ForwardVector;
	}

	FName VolumeGroupName(ELBAudioVolumeGroup Group)
	{
		switch (Group)
		{
		case ELBAudioVolumeGroup::Master: return FName(TEXT("Master"));
		case ELBAudioVolumeGroup::SFX: return FName(TEXT("SFX"));
		case ELBAudioVolumeGroup::Ambience: return FName(TEXT("Ambience"));
		case ELBAudioVolumeGroup::Music: return FName(TEXT("Music"));
		case ELBAudioVolumeGroup::Voice: return FName(TEXT("Voice"));
		case ELBAudioVolumeGroup::UI: return FName(TEXT("UI"));
		}
		return NAME_None;
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// FLBAudioLoop
// ---------------------------------------------------------------------------------------------------------------------

void FLBAudioLoop::Update(ULBAudioSubsystem& Audio, FName Cue, const TSoftObjectPtr<USoundBase>& Ref, USceneComponent* AttachTo, float Target, float InSeconds,
	float OutSeconds, float Pitch, float DeltaSeconds)
{
	Level = LBAudioLogic::Ease(Level, Target, InSeconds, OutSeconds, DeltaSeconds);

	if (Level > LoopOnThreshold)
	{
		USoundBase* Sound = Audio.ResolveSound(Ref, Cue);
		if (bStarted && Sound != LoadedSound.Get())
		{
			// The sound changed under a running loop (a drone swap, a room slot reused): restart with the new one.
			Stop();
		}
		if (!bStarted)
		{
			bStarted = true;
			LoadedSound = Sound;
			AppliedVolume = -1.f;
			AppliedPitch = -1.f;

			FLBAudioRequest Request;
			Request.Cue = Cue;
			Request.bPositional = AttachTo != nullptr;
			Request.Location = AttachTo ? AttachTo->GetComponentLocation() : FVector::ZeroVector;
			Request.Volume = Level;
			Request.Pitch = Pitch;
			Request.bSoundResolved = Sound != nullptr;
			Audio.RecordRequest(Request);

			if (Sound)
			{
				UWorld* World = Audio.GetWorld();
				UAudioComponent* Comp = nullptr;
				if (AttachTo)
				{
					// Plays at once; bAutoDestroy false keeps the component for the next start.
					Comp = UGameplayStatics::SpawnSoundAttached(Sound, AttachTo, NAME_None, FVector::ZeroVector, EAttachLocation::KeepRelativeOffset, true,
						Level, Pitch, 0.f, nullptr, nullptr, false);
				}
				else if (World)
				{
					Comp = UGameplayStatics::CreateSound2D(World, Sound, Level, Pitch, 0.f, nullptr, false, false);
					if (Comp)
					{
						Comp->Play();
					}
				}
				Component = Comp;
				if (Comp)
				{
					AppliedVolume = Level;
					AppliedPitch = Pitch;
				}
			}
		}
		if (UAudioComponent* Comp = Component.Get())
		{
			if (!FMath::IsNearlyEqual(AppliedVolume, Level, 0.002f))
			{
				Comp->SetVolumeMultiplier(Level);
				AppliedVolume = Level;
			}
			if (!FMath::IsNearlyEqual(AppliedPitch, Pitch, 0.002f))
			{
				Comp->SetPitchMultiplier(Pitch);
				AppliedPitch = Pitch;
			}
		}
	}
	else if (bStarted && Target <= 0.f)
	{
		Stop();
	}
}

void FLBAudioLoop::Stop()
{
	if (UAudioComponent* Comp = Component.Get())
	{
		Comp->Stop();
		Comp->DestroyComponent();
	}
	Component.Reset();
	LoadedSound.Reset();
	bStarted = false;
	AppliedVolume = -1.f;
	AppliedPitch = -1.f;
}

void FLBAudioLoop::FadeOutAndForget(float Seconds)
{
	if (UAudioComponent* Comp = Component.Get())
	{
		// The component destroys itself when the fade has finished.
		Comp->bAutoDestroy = true;
		Comp->FadeOut(Seconds, 0.f);
	}
	Component.Reset();
	LoadedSound.Reset();
	bStarted = false;
	Level = 0.f;
	AppliedVolume = -1.f;
	AppliedPitch = -1.f;
}

// ---------------------------------------------------------------------------------------------------------------------
// ULBAudioProxy
// ---------------------------------------------------------------------------------------------------------------------

void ULBAudioProxy::BindComponents()
{
	AActor* Target = Actor.Get();
	if (!Target)
	{
		return;
	}
	TArray<ULBInteractableComponent*> Interactables;
	Target->GetComponents(Interactables);
	for (ULBInteractableComponent* Interactable : Interactables)
	{
		Interactable->OnInteracted.AddUniqueDynamic(this, &ULBAudioProxy::HandleInteracted);
		Interactable->OnInteractDenied.AddUniqueDynamic(this, &ULBAudioProxy::HandleDenied);
	}
	TArray<ULBDialComponent*> Dials;
	Target->GetComponents(Dials);
	for (ULBDialComponent* Dial : Dials)
	{
		Dial->OnDialChanged.AddUniqueDynamic(this, &ULBAudioProxy::HandleDialChanged);
	}
	TArray<ULBSequencePuzzleComponent*> Puzzles;
	Target->GetComponents(Puzzles);
	for (ULBSequencePuzzleComponent* Puzzle : Puzzles)
	{
		Puzzle->OnStepAccepted.AddUniqueDynamic(this, &ULBAudioProxy::HandleStepAccepted);
		Puzzle->OnPuzzleFailed.AddUniqueDynamic(this, &ULBAudioProxy::HandlePuzzleFailed);
		Puzzle->OnPuzzleSolved.AddUniqueDynamic(this, &ULBAudioProxy::HandlePuzzleSolved);
	}
}

void ULBAudioProxy::UnbindComponents()
{
	AActor* Target = Actor.Get();
	if (!Target)
	{
		return;
	}
	TArray<ULBInteractableComponent*> Interactables;
	Target->GetComponents(Interactables);
	for (ULBInteractableComponent* Interactable : Interactables)
	{
		Interactable->OnInteracted.RemoveDynamic(this, &ULBAudioProxy::HandleInteracted);
		Interactable->OnInteractDenied.RemoveDynamic(this, &ULBAudioProxy::HandleDenied);
	}
	TArray<ULBDialComponent*> Dials;
	Target->GetComponents(Dials);
	for (ULBDialComponent* Dial : Dials)
	{
		Dial->OnDialChanged.RemoveDynamic(this, &ULBAudioProxy::HandleDialChanged);
	}
	TArray<ULBSequencePuzzleComponent*> Puzzles;
	Target->GetComponents(Puzzles);
	for (ULBSequencePuzzleComponent* Puzzle : Puzzles)
	{
		Puzzle->OnStepAccepted.RemoveDynamic(this, &ULBAudioProxy::HandleStepAccepted);
		Puzzle->OnPuzzleFailed.RemoveDynamic(this, &ULBAudioProxy::HandlePuzzleFailed);
		Puzzle->OnPuzzleSolved.RemoveDynamic(this, &ULBAudioProxy::HandlePuzzleSolved);
	}
}

void ULBAudioProxy::HandleInteracted(AActor* Instigator)
{
	if (ULBAudioSubsystem* Audio = Owner.Get())
	{
		Audio->NotifyInteracted(Actor.Get(), false);
	}
}

void ULBAudioProxy::HandleDenied(AActor* Instigator)
{
	if (ULBAudioSubsystem* Audio = Owner.Get())
	{
		Audio->NotifyInteracted(Actor.Get(), true);
	}
}

void ULBAudioProxy::HandleDialChanged(int32 NewIndex)
{
	if (ULBAudioSubsystem* Audio = Owner.Get())
	{
		Audio->NotifyDialChanged(Actor.Get(), NewIndex);
	}
}

void ULBAudioProxy::HandleStepAccepted(int32 Index, FGameplayTag Step)
{
	if (ULBAudioSubsystem* Audio = Owner.Get())
	{
		Audio->NotifyStepAccepted(Actor.Get(), Index, Step);
	}
}

void ULBAudioProxy::HandlePuzzleFailed(FGameplayTag WrongStep)
{
	if (ULBAudioSubsystem* Audio = Owner.Get())
	{
		Audio->NotifyPuzzleFailed(Actor.Get(), WrongStep);
	}
}

void ULBAudioProxy::HandlePuzzleSolved()
{
	if (ULBAudioSubsystem* Audio = Owner.Get())
	{
		Audio->NotifyPuzzleSolved(Actor.Get());
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Plumbing
// ---------------------------------------------------------------------------------------------------------------------

bool ULBAudioSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

TStatId ULBAudioSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(ULBAudioSubsystem, STATGROUP_Tickables);
}

void ULBAudioSubsystem::Initialize(FSubsystemCollectionBase& InCollection)
{
	// The storm is created first, so its state is there when this one reads it.
	InCollection.InitializeDependency<ULBStormSubsystem>();
	Super::Initialize(InCollection);
}

void ULBAudioSubsystem::Deinitialize()
{
	UnbindWorldEvents();
	for (FLBAudioLoop& Loop : Loops)
	{
		Loop.Stop();
	}
	Proxies.Reset();
	Scheduled.Reset();
	bActive = false;
	Super::Deinitialize();
}

void ULBAudioSubsystem::OverrideSettings(ULBAudioSettings* InSettings)
{
	SettingsOverride = InSettings;
}

void ULBAudioSubsystem::Rearm()
{
	bGaveUp = false;
	bWarnedNoSettings = false;
}

void ULBAudioSubsystem::RegisterZone(ALBAudioZone* Zone)
{
	if (Zone)
	{
		Zones.AddUnique(Zone);
	}
}

void ULBAudioSubsystem::UnregisterZone(ALBAudioZone* Zone)
{
	Zones.Remove(Zone);
	if (CurrentZone.Get() == Zone)
	{
		CurrentZone.Reset();
	}
}

float ULBAudioSubsystem::GetLayerLevel(ELBAudioLayer Layer) const
{
	const int32 Index = static_cast<int32>(Layer);
	return Index >= 0 && Index < static_cast<int32>(ELBAudioLayer::Count) ? Loops[Index].Level : 0.f;
}

float ULBAudioSubsystem::GetAppliedVolume(ELBAudioVolumeGroup Group) const
{
	return AppliedVolumes[FMath::Clamp(static_cast<int32>(Group), 0, 5)];
}

bool ULBAudioSubsystem::GetListenerLocation(FVector& OutLocation) const
{
	const UWorld* World = GetWorld();
	if (!World)
	{
		return false;
	}
	const APlayerController* PC = World->GetFirstPlayerController();
	const APlayerCameraManager* Camera = PC ? PC->PlayerCameraManager.Get() : nullptr;
	// As ULBStormFXSubsystem: the player camera, unless the controller has no pawn while a view was rendered (PIE Simulate).
	if (Camera && (PC->GetPawn() || World->ViewLocationsRenderedLastFrame.IsEmpty()))
	{
		OutLocation = Camera->GetCameraLocation();
		return true;
	}
	if (!World->ViewLocationsRenderedLastFrame.IsEmpty())
	{
		OutLocation = World->ViewLocationsRenderedLastFrame[0];
		return true;
	}
	return false;
}

ALBCharacter* ULBAudioSubsystem::GetPlayer() const
{
	const UWorld* World = GetWorld();
	const APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	return PC ? Cast<ALBCharacter>(PC->GetPawn()) : nullptr;
}

ELBWardenState ULBAudioSubsystem::GetEffectiveWardenState() const
{
	const int32 Forced = ConsoleMusicState >= 0 ? ConsoleMusicState : (Settings ? Settings->DebugForceMusicState : -1);
	if (Forced >= 0 && Forced <= static_cast<int32>(ELBWardenState::Return))
	{
		return static_cast<ELBWardenState>(Forced);
	}
	return RealWardenState;
}

#if !UE_BUILD_SHIPPING
int32 ULBAudioSubsystem::CountRequests(FName Cue) const
{
	int32 Count = 0;
	for (const FLBAudioRequest& Request : Requests)
	{
		Count += Request.Cue == Cue ? 1 : 0;
	}
	return Count;
}
#endif

void ULBAudioSubsystem::RecordRequest(const FLBAudioRequest& Request)
{
#if !UE_BUILD_SHIPPING
	FLBAudioRequest Copy = Request;
	if (const UWorld* World = GetWorld())
	{
		Copy.Time = World->GetTimeSeconds();
	}
	if (Requests.Num() >= MaxRequests)
	{
		Requests.RemoveAt(0, MaxRequests / 4, EAllowShrinking::No);
	}
	Requests.Add(Copy);
#endif
}

// ---------------------------------------------------------------------------------------------------------------------
// Sounds
// ---------------------------------------------------------------------------------------------------------------------

void ULBAudioSubsystem::Remember(USoundBase* Sound)
{
	if (Sound)
	{
		LoadedSounds.AddUnique(Sound);
	}
}

void ULBAudioSubsystem::WarnOnce(FName Key, const TCHAR* Text, const FString& Detail)
{
	if (!WarnedKeys.Contains(Key))
	{
		WarnedKeys.Add(Key);
		UE_LOG(LogLB, Warning, TEXT("Audio: %s %s"), Text, *Detail);
	}
}

USoundBase* ULBAudioSubsystem::ResolveSound(const TSoftObjectPtr<USoundBase>& Ref, FName Cue)
{
	if (Ref.IsNull())
	{
		if (!WarnedKeys.Contains(Cue))
		{
			WarnedKeys.Add(Cue);
			UE_LOG(LogLB, Log, TEXT("Audio: cue '%s' has no sound set; it plays nothing"), *Cue.ToString());
		}
		return nullptr;
	}
	USoundBase* Sound = Ref.Get();
	if (!Sound)
	{
		const FName PathKey(*Ref.ToString());
		if (WarnedKeys.Contains(PathKey))
		{
			// Already tried and failed: do not hit the disk every time.
			return nullptr;
		}
		Sound = Ref.LoadSynchronous();
		if (Sound)
		{
			Remember(Sound);
		}
		else
		{
			WarnedKeys.Add(PathKey);
			UE_LOG(LogLB, Warning, TEXT("Audio: cue '%s': sound '%s' does not load; it plays nothing"), *Cue.ToString(), *Ref.ToString());
		}
	}
	return Sound;
}

int32 ULBAudioSubsystem::PickVariantFor(FName Key, int32 Count)
{
	int32& Last = LastVariant.FindOrAdd(Key, INDEX_NONE);
	const int32 Picked = LBAudioLogic::PickVariant(Count, Last, Stream.FRand());
	Last = Picked;
	return Picked;
}

UAudioComponent* ULBAudioSubsystem::Play2D(FName Cue, const TSoftObjectPtr<USoundBase>& Ref, float Volume, float Pitch, int32 Variant, int32 Aux)
{
	USoundBase* Sound = ResolveSound(Ref, Cue);
	FLBAudioRequest Request;
	Request.Cue = Cue;
	Request.Volume = Volume;
	Request.Pitch = Pitch;
	Request.Variant = Variant;
	Request.Aux = Aux;
	Request.bSoundResolved = Sound != nullptr;
	RecordRequest(Request);
	UWorld* World = GetWorld();
	return (Sound && World) ? UGameplayStatics::SpawnSound2D(World, Sound, Volume, Pitch) : nullptr;
}

UAudioComponent* ULBAudioSubsystem::PlayAt(FName Cue, const TSoftObjectPtr<USoundBase>& Ref, const FVector& Location, float Volume, float Pitch, int32 Variant, int32 Aux)
{
	USoundBase* Sound = ResolveSound(Ref, Cue);
	FLBAudioRequest Request;
	Request.Cue = Cue;
	Request.bPositional = true;
	Request.Location = Location;
	Request.Volume = Volume;
	Request.Pitch = Pitch;
	Request.Variant = Variant;
	Request.Aux = Aux;
	Request.bSoundResolved = Sound != nullptr;
	RecordRequest(Request);
	UWorld* World = GetWorld();
	return (Sound && World) ? UGameplayStatics::SpawnSoundAtLocation(World, Sound, Location, FRotator::ZeroRotator, Volume, Pitch) : nullptr;
}

UAudioComponent* ULBAudioSubsystem::PlayAttached(FName Cue, const TSoftObjectPtr<USoundBase>& Ref, USceneComponent* AttachTo, float Volume, float Pitch, int32 Variant, int32 Aux)
{
	if (!AttachTo)
	{
		return Play2D(Cue, Ref, Volume, Pitch, Variant, Aux);
	}
	USoundBase* Sound = ResolveSound(Ref, Cue);
	FLBAudioRequest Request;
	Request.Cue = Cue;
	Request.bPositional = true;
	Request.Location = AttachTo->GetComponentLocation();
	Request.Volume = Volume;
	Request.Pitch = Pitch;
	Request.Variant = Variant;
	Request.Aux = Aux;
	Request.bSoundResolved = Sound != nullptr;
	RecordRequest(Request);
	return Sound ? UGameplayStatics::SpawnSoundAttached(Sound, AttachTo, NAME_None, FVector::ZeroVector, EAttachLocation::KeepRelativeOffset, true, Volume, Pitch) : nullptr;
}

void ULBAudioSubsystem::PreloadSounds()
{
	if (!Settings)
	{
		return;
	}
	// Loaded once here so no first play stalls on a disk read. An unset entry is skipped; a missing one is logged once.
	TArray<ULBAudioSettings::FSoundEntry> Entries;
	Settings->CollectSounds(Entries);
	for (const ULBAudioSettings::FSoundEntry& Entry : Entries)
	{
		if (!Entry.Ref.IsNull())
		{
			// Kept alive even when it was already resident, so a garbage collection cannot drop a sound the director is about to play.
			Remember(ResolveSound(Entry.Ref, FName(*Entry.Name)));
		}
	}
	if (!Settings->UserMix.IsNull())
	{
		Settings->UserMix.LoadSynchronous();
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Activation
// ---------------------------------------------------------------------------------------------------------------------

bool ULBAudioSubsystem::TryActivate(ULBStormSubsystem& Storm)
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return false;
	}

	if (SettingsOverride)
	{
		Settings = SettingsOverride;
	}
	else
	{
		const ULBGameSettings* GameSettings = ULBGameSettings::Get();
		Settings = (GameSettings && !GameSettings->AudioSettings.IsNull()) ? GameSettings->AudioSettings.LoadSynchronous() : nullptr;
		if (!Settings && !bWarnedNoSettings)
		{
			bWarnedNoSettings = true;
			if (GameSettings && GameSettings->AudioSettings.IsNull())
			{
				UE_LOG(LogLB, Log, TEXT("Audio: ULBGameSettings::AudioSettings is not set; the audio director stays silent"));
			}
			else
			{
				UE_LOG(LogLB, Warning, TEXT("Audio: ULBGameSettings::AudioSettings (%s) does not load; the audio director stays silent"),
					GameSettings ? *GameSettings->AudioSettings.ToString() : TEXT("none"));
			}
		}
	}
	if (!Settings)
	{
		// Nothing will change this until the level is reloaded or a test calls Rearm.
		bGaveUp = true;
		return false;
	}

	const double Now = World->GetTimeSeconds();
	Stream.Initialize(Settings->RandomSeed != 0 ? Settings->RandomSeed : static_cast<int32>(FPlatformTime::Cycles()));
	Scheduled.Reset();
	LastVariant.Reset();
	for (FLBAudioLoop& Loop : Loops)
	{
		Loop.Stop();
		Loop.Level = 0.f;
	}
	RoomSlotRef[0].Reset();
	RoomSlotRef[1].Reset();
	ActiveRoomSlot = 0;
	bRoomInitialised = false;
	RoomZone.Reset();
	CurrentZone.Reset();
	DronePlaying = -1;
	DroneRequested = -1;
	DroneFadeOutAt = 0.0;
	StressLevel = 0.f;
	SprintBonusLeft = 0.f;
	bCandleOutImpulse = false;
	bCandleLit = true;
	NextBreathAt = 0.0;
	NextZoneCheck = 0.0;
	NextWardenSearch = 0.0;
	LastMusicTargets = LBAudioLogic::FMusicTargets();
	RealWardenState = ELBWardenState::Dormant;
	WardenStage = 0;
	WardenDistance = 1.0e9f;

	PreloadSounds();

	// Story progress already in the world state counts as reached (a checkpoint load starts mid-story).
	FinaleTag = FGameplayTag::RequestGameplayTag(FName(TEXT("State.Event.Finale")), /*ErrorIfNotFound*/ false);
	const ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(World);
	BellStageReached = State ? LBAudioLogic::CurrentBellStage(Settings->BellBeats, State->GetStateRef()) : 1;
	bFinaleReached = State && FinaleTag.IsValid() && State->HasState(FinaleTag);
	LastBeatTime = -1.0e9;
	NextTollTime = Now + static_cast<double>(RandomRange(static_cast<float>(Settings->AmbientTollInterval.X), static_cast<float>(Settings->AmbientTollInterval.Y)));

	BindWorldEvents();
	BoundStorm = &Storm;
	bActive = true;
	bEverActive = true;
	RefreshBindings();

	// A new game: the great bell tolls a few times from afar. Not when a beat tag is already present (a checkpoint load).
	if (Settings->bNewGameToll && !IsBeatTagPresent())
	{
		ScheduleBell(1, Settings->NewGameTollStrikes, Settings->NewGameTollDelay, Settings->NewGameTollSpacing, false);
		ScheduleDrone(Settings->NewGameDrone, Settings->NewGameTollDelay);
		LastBeatTime = Now + Settings->NewGameTollDelay;
	}

	ApplyUserVolumes();
	UE_LOG(LogLB, Log, TEXT("Audio: active (%d sounds loaded, %d zones, %d bound actors)"), LoadedSounds.Num(), Zones.Num(), Proxies.Num());
	return true;
}

void ULBAudioSubsystem::Deactivate()
{
	UnbindWorldEvents();
	for (FLBAudioLoop& Loop : Loops)
	{
		Loop.FadeOutAndForget(DeactivateFadeSeconds);
	}
	Scheduled.Reset();
	bActive = false;
	UE_LOG(LogLB, Log, TEXT("Audio: inactive"));
}

bool ULBAudioSubsystem::IsBeatTagPresent() const
{
	const ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(this);
	if (!State || !Settings)
	{
		return false;
	}
	for (const FLBBellBeat& Beat : Settings->BellBeats)
	{
		if (Beat.Trigger.IsValid() && State->HasState(Beat.Trigger))
		{
			return true;
		}
	}
	return false;
}

void ULBAudioSubsystem::BindWorldEvents()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	if (ULBStormSubsystem* Storm = World->GetSubsystem<ULBStormSubsystem>())
	{
		Storm->OnLightningStrike.AddUniqueDynamic(this, &ULBAudioSubsystem::HandleLightningStrike);
		BoundStorm = Storm;
	}
	if (ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(World))
	{
		State->OnStateChanged.AddUniqueDynamic(this, &ULBAudioSubsystem::HandleStateChanged);
		State->OnStateReplaced.AddUniqueDynamic(this, &ULBAudioSubsystem::HandleStateReplaced);
		BoundState = State;
	}
	if (!ActorSpawnedHandle.IsValid())
	{
		ActorSpawnedHandle = World->AddOnActorSpawnedHandler(FOnActorSpawned::FDelegate::CreateUObject(this, &ULBAudioSubsystem::HandleActorSpawned));
	}
	if (!UserVolumesHandle.IsValid())
	{
		UserVolumesHandle = ULBUserSettings::OnAudioVolumesChanged().AddUObject(this, &ULBAudioSubsystem::HandleUserVolumesChanged);
	}
}

void ULBAudioSubsystem::UnbindWorldEvents()
{
	if (ULBStormSubsystem* Storm = BoundStorm.Get())
	{
		Storm->OnLightningStrike.RemoveDynamic(this, &ULBAudioSubsystem::HandleLightningStrike);
	}
	BoundStorm.Reset();
	if (ULBWorldStateSubsystem* State = BoundState.Get())
	{
		State->OnStateChanged.RemoveDynamic(this, &ULBAudioSubsystem::HandleStateChanged);
		State->OnStateReplaced.RemoveDynamic(this, &ULBAudioSubsystem::HandleStateReplaced);
	}
	BoundState.Reset();
	if (ActorSpawnedHandle.IsValid())
	{
		if (UWorld* World = GetWorld())
		{
			World->RemoveOnActorSpawnedHandler(ActorSpawnedHandle);
		}
		ActorSpawnedHandle.Reset();
	}
	if (UserVolumesHandle.IsValid())
	{
		ULBUserSettings::OnAudioVolumesChanged().Remove(UserVolumesHandle);
		UserVolumesHandle.Reset();
	}
	if (ULBWardenBrainComponent* Brain = BoundBrain.Get())
	{
		Brain->OnPlayerSpotted.RemoveDynamic(this, &ULBAudioSubsystem::HandlePlayerSpotted);
		Brain->OnPlayerCaught.RemoveDynamic(this, &ULBAudioSubsystem::HandlePlayerCaught);
	}
	BoundBrain.Reset();
	if (ULBCandleComponent* Candle = Cast<ULBCandleComponent>(BoundCandle.Get()))
	{
		Candle->OnCandleStateChanged.RemoveDynamic(this, &ULBAudioSubsystem::HandleCandleState);
		Candle->OnRelightStarted.RemoveDynamic(this, &ULBAudioSubsystem::HandleRelightStarted);
	}
	BoundCandle.Reset();
	if (ULBInspectionComponent* Inspection = Cast<ULBInspectionComponent>(BoundInspection.Get()))
	{
		Inspection->OnInspectBegin.RemoveDynamic(this, &ULBAudioSubsystem::HandleInspectBegin);
		Inspection->OnInspectEnd.RemoveDynamic(this, &ULBAudioSubsystem::HandleInspectEnd);
	}
	BoundInspection.Reset();
	InspectedActor.Reset();
	for (const TWeakObjectPtr<ALBWardenApparition>& Weak : BoundApparitions)
	{
		if (ALBWardenApparition* Apparition = Weak.Get())
		{
			Apparition->OnAppeared.RemoveDynamic(this, &ULBAudioSubsystem::HandleApparitionAppeared);
		}
	}
	BoundApparitions.Reset();
	for (ULBAudioProxy* Proxy : Proxies)
	{
		if (Proxy)
		{
			Proxy->UnbindComponents();
		}
	}
	Proxies.Reset();

	if (PushedMix)
	{
		if (UWorld* World = GetWorld())
		{
			UGameplayStatics::PopSoundMixModifier(World, PushedMix);
		}
		PushedMix = nullptr;
	}
}

void ULBAudioSubsystem::RefreshBindings()
{
	UWorld* World = GetWorld();
	if (!World || !bActive)
	{
		return;
	}
	Proxies.RemoveAll([](const ULBAudioProxy* Proxy) { return !Proxy || !Proxy->Actor.IsValid(); });
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		HandleActorSpawned(*It);
	}
}

void ULBAudioSubsystem::HandleActorSpawned(AActor* Actor)
{
	if (!bActive || !Actor || Actor->IsActorBeingDestroyed())
	{
		return;
	}
	if (ALBWardenApparition* Apparition = Cast<ALBWardenApparition>(Actor))
	{
		Apparition->OnAppeared.AddUniqueDynamic(this, &ULBAudioSubsystem::HandleApparitionAppeared);
		BoundApparitions.Add(Apparition);
		return;
	}
	if (!Actor->FindComponentByClass<ULBInteractableComponent>() && !Actor->FindComponentByClass<ULBDialComponent>() && !Actor->FindComponentByClass<ULBSequencePuzzleComponent>())
	{
		return;
	}
	ULBAudioProxy* Found = nullptr;
	for (ULBAudioProxy* Proxy : Proxies)
	{
		if (Proxy && Proxy->Actor.Get() == Actor)
		{
			Found = Proxy;
			break;
		}
	}
	if (!Found)
	{
		Found = NewObject<ULBAudioProxy>(this);
		Found->Owner = this;
		Found->Actor = Actor;
		Proxies.Add(Found);
	}
	// Idempotent: a component added to an already bound actor is picked up by the next refresh.
	Found->BindComponents();
}

void ULBAudioSubsystem::HandleUserVolumesChanged()
{
	if (bActive)
	{
		ApplyUserVolumes();
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// User volumes
// ---------------------------------------------------------------------------------------------------------------------

void ULBAudioSubsystem::ApplyUserVolumes()
{
	const ULBUserSettings* User = ULBUserSettings::Get();
	UWorld* World = GetWorld();
	if (!User)
	{
		return;
	}
	for (int32 Index = 0; Index < 6; ++Index)
	{
		AppliedVolumes[Index] = User->GetVolume(static_cast<ELBAudioVolumeGroup>(Index));
	}
	if (!Settings || !World)
	{
		return;
	}
	USoundMix* Mix = Settings->UserMix.IsNull() ? nullptr : Settings->UserMix.LoadSynchronous();
	if (!Mix)
	{
		if (!Settings->UserMix.IsNull() || Settings->UserClasses.Num() > 0)
		{
			WarnOnce(FName(TEXT("UserMix")), TEXT("UserMix is not set or does not load; the user volumes have no effect"), FString());
		}
		return;
	}
	if (PushedMix != Mix)
	{
		if (PushedMix)
		{
			UGameplayStatics::PopSoundMixModifier(World, PushedMix);
		}
		UGameplayStatics::PushSoundMixModifier(World, Mix);
		PushedMix = Mix;
	}
	// The Master class is the parent of the other five, so its override scales them too (bApplyToChildren); each group's own override adds its share.
	for (int32 Index = 0; Index < 6; ++Index)
	{
		const ELBAudioVolumeGroup Group = static_cast<ELBAudioVolumeGroup>(Index);
		const TSoftObjectPtr<USoundClass>* ClassRef = Settings->UserClasses.Find(VolumeGroupName(Group));
		if (!ClassRef || ClassRef->IsNull())
		{
			continue;
		}
		if (USoundClass* SoundClass = ClassRef->LoadSynchronous())
		{
			UGameplayStatics::SetSoundMixClassOverride(World, Mix, SoundClass, AppliedVolumes[Index], 1.f, 0.05f, true);
		}
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Tick
// ---------------------------------------------------------------------------------------------------------------------

void ULBAudioSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	ULBStormSubsystem* Storm = World->GetSubsystem<ULBStormSubsystem>();
	const bool bStormActive = Storm && Storm->IsActive();
	const bool bEnabled = IsAudioEnabled();

	if (bActive)
	{
		if (!bStormActive || !bEnabled)
		{
			Deactivate();
			return;
		}
	}
	else
	{
		if (!World->HasBegunPlay())
		{
			return;
		}
		if (!bStormActive)
		{
			// No storm in this world after BeginPlay (the main menu, the test maps): never tick again, unless it was active once.
			bGaveUp = !bEverActive;
			return;
		}
		if (!bEnabled || !TryActivate(*Storm))
		{
			return;
		}
	}

	if (World->IsPaused())
	{
		// The ending sequence pauses the game: only the great bell's strikes keep running (they use the unpaused clock and play as UI sounds).
		UpdateScheduled(World->GetTimeSeconds(), World->GetUnpausedTimeSeconds(), /*bPaused*/ true);
		return;
	}
	TickWorld(*World, *Storm, DeltaTime);
}

void ULBAudioSubsystem::TickWorld(UWorld& World, ULBStormSubsystem& Storm, float DeltaSeconds)
{
	if (!Settings)
	{
		return;
	}
	const double Now = World.GetTimeSeconds();

	FVector Listener;
	bHasListener = GetListenerLocation(Listener);
	if (bHasListener)
	{
		LastListener = Listener;
	}

	UpdateScheduled(Now, World.GetUnpausedTimeSeconds(), /*bPaused*/ false);
	UpdateZone(Now);
	UpdateWardenLink(Now);
	BindPlayerEvents();
	UpdateWeather(Storm, DeltaSeconds);
	UpdateRoomTone(DeltaSeconds);
	UpdateMusic(Now, DeltaSeconds);
	UpdateStress(Now, DeltaSeconds);
	UpdateAmbientToll(Now);
	if (bDebugOverlay)
	{
		DrawDebugOverlay(Now);
	}
}

void ULBAudioSubsystem::UpdateZone(double Now)
{
	if (Now < NextZoneCheck)
	{
		return;
	}
	NextZoneCheck = Now + ZoneCheckInterval;
	Zones.RemoveAll([](const TWeakObjectPtr<ALBAudioZone>& Zone) { return !Zone.IsValid(); });
	if (!bHasListener)
	{
		return;
	}
	const ALBAudioZone* Best = nullptr;
	for (const TWeakObjectPtr<ALBAudioZone>& Weak : Zones)
	{
		const ALBAudioZone* Zone = Weak.Get();
		if (Zone && Zone->ContainsPoint(LastListener) && (!Best || Zone->Priority > Best->Priority))
		{
			Best = Zone;
		}
	}
	CurrentZone = Best;
}

void ULBAudioSubsystem::UpdateWardenLink(double Now)
{
	if (Now >= NextWardenSearch)
	{
		NextWardenSearch = Now + WardenSearchInterval;
		if (!CachedWarden.IsValid())
		{
			for (TActorIterator<ALBWarden> It(GetWorld()); It; ++It)
			{
				CachedWarden = *It;
				break;
			}
		}
		ALBWarden* Warden = CachedWarden.Get();
		ULBWardenBrainComponent* Brain = Warden ? Warden->GetBrain() : nullptr;
		if (Brain != BoundBrain.Get())
		{
			if (ULBWardenBrainComponent* Old = BoundBrain.Get())
			{
				Old->OnPlayerSpotted.RemoveDynamic(this, &ULBAudioSubsystem::HandlePlayerSpotted);
				Old->OnPlayerCaught.RemoveDynamic(this, &ULBAudioSubsystem::HandlePlayerCaught);
			}
			if (Brain)
			{
				Brain->OnPlayerSpotted.AddUniqueDynamic(this, &ULBAudioSubsystem::HandlePlayerSpotted);
				Brain->OnPlayerCaught.AddUniqueDynamic(this, &ULBAudioSubsystem::HandlePlayerCaught);
			}
			BoundBrain = Brain;
		}
	}

	// The Warden's facts for the music and the stress, every tick (cheap).
	const ALBWarden* Warden = CachedWarden.Get();
	const ULBWardenBrainComponent* Brain = BoundBrain.Get();
	if (Warden && Brain && !Warden->IsDormantPresentation() && Brain->GetState() != ELBWardenState::Dormant)
	{
		RealWardenState = Brain->GetState();
		WardenStage = Brain->GetStage();
		WardenDistance = bHasListener ? static_cast<float>(FVector::Dist(Warden->GetActorLocation(), LastListener)) : 1.0e9f;
	}
	else
	{
		RealWardenState = ELBWardenState::Dormant;
		WardenStage = Brain ? Brain->GetStage() : 0;
		WardenDistance = 1.0e9f;
	}
}

void ULBAudioSubsystem::BindPlayerEvents()
{
	ALBCharacter* Player = GetPlayer();
	ULBInspectionComponent* Inspection = Player ? Player->GetInspection() : nullptr;
	if (Inspection != BoundInspection.Get())
	{
		if (ULBInspectionComponent* OldInspection = Cast<ULBInspectionComponent>(BoundInspection.Get()))
		{
			OldInspection->OnInspectBegin.RemoveDynamic(this, &ULBAudioSubsystem::HandleInspectBegin);
			OldInspection->OnInspectEnd.RemoveDynamic(this, &ULBAudioSubsystem::HandleInspectEnd);
		}
		InspectedActor.Reset();
		if (Inspection)
		{
			Inspection->OnInspectBegin.AddUniqueDynamic(this, &ULBAudioSubsystem::HandleInspectBegin);
			Inspection->OnInspectEnd.AddUniqueDynamic(this, &ULBAudioSubsystem::HandleInspectEnd);
		}
		BoundInspection = Inspection;
	}
	ULBCandleComponent* Candle = Player ? Player->GetCandle() : nullptr;
	if (Candle == BoundCandle.Get())
	{
		return;
	}
	if (ULBCandleComponent* Old = Cast<ULBCandleComponent>(BoundCandle.Get()))
	{
		Old->OnCandleStateChanged.RemoveDynamic(this, &ULBAudioSubsystem::HandleCandleState);
		Old->OnRelightStarted.RemoveDynamic(this, &ULBAudioSubsystem::HandleRelightStarted);
	}
	if (Candle)
	{
		Candle->OnCandleStateChanged.AddUniqueDynamic(this, &ULBAudioSubsystem::HandleCandleState);
		Candle->OnRelightStarted.AddUniqueDynamic(this, &ULBAudioSubsystem::HandleRelightStarted);
	}
	BoundCandle = Candle;
}

void ULBAudioSubsystem::UpdateWeather(const ULBStormSubsystem& Storm, float DeltaSeconds)
{
	const ALBAudioZone* Zone = CurrentZone.Get();
	const float E = Storm.GetPlayerExposure();
	const float W = Storm.GetWindStrength();
	const float RoofRain = Zone ? Zone->RoofRain : 0.f;
	const float InteriorWind = Zone ? Zone->InteriorWind : 0.f;
	const float Howl = Zone ? Zone->Howl : 0.f;

	const LBAudioLogic::FRainMix Rain = LBAudioLogic::RainMix(E, RoofRain, Settings->RainExposurePower, Settings->RainOutGain, Settings->RainInGain);
	const LBAudioLogic::FWindMix Wind = LBAudioLogic::WindMix(E, W, InteriorWind, Howl, Settings->WindOutGain, Settings->WindMin);
	const float Fade = Settings->MixFadeSeconds;
	const float WindPitch = FMath::Lerp(static_cast<float>(Settings->WindPitch.X), static_cast<float>(Settings->WindPitch.Y), FMath::Clamp(W, 0.f, 1.f));

	Loops[static_cast<int32>(ELBAudioLayer::RainOut)].Update(*this, LBAudioCue::LoopRainOut, Settings->Weather.RainOut, nullptr, Rain.Out, Fade, Fade, 1.f, DeltaSeconds);
	Loops[static_cast<int32>(ELBAudioLayer::RainIn)].Update(*this, LBAudioCue::LoopRainIn, Settings->Weather.RainIn, nullptr, Rain.In, Fade, Fade, 1.f, DeltaSeconds);
	Loops[static_cast<int32>(ELBAudioLayer::Wind)].Update(*this, LBAudioCue::LoopWind, Settings->Weather.Wind, nullptr, Wind.Wind, Fade, Fade, WindPitch, DeltaSeconds);
	Loops[static_cast<int32>(ELBAudioLayer::WindHowl)].Update(*this, LBAudioCue::LoopWindHowl, Settings->Weather.WindHowl, nullptr, Wind.Howl, Fade, Fade, 1.f, DeltaSeconds);
}

void ULBAudioSubsystem::UpdateRoomTone(float DeltaSeconds)
{
	const ALBAudioZone* Zone = CurrentZone.Get();
	if (!bRoomInitialised)
	{
		bRoomInitialised = true;
		RoomZone = Zone;
		RoomSlotRef[ActiveRoomSlot] = Zone ? Zone->RoomTone : TSoftObjectPtr<USoundBase>();
	}
	else if (RoomZone.Get() != Zone)
	{
		// The zone changed: the other slot takes the new tone while this one fades out.
		RoomZone = Zone;
		ActiveRoomSlot = 1 - ActiveRoomSlot;
		RoomSlotRef[ActiveRoomSlot] = Zone ? Zone->RoomTone : TSoftObjectPtr<USoundBase>();
	}
	const float Fade = Settings->RoomToneFadeSeconds;
	for (int32 Slot = 0; Slot < 2; ++Slot)
	{
		const bool bActiveSlot = Slot == ActiveRoomSlot;
		const float Target = (bActiveSlot && Zone && !RoomSlotRef[Slot].IsNull()) ? Zone->RoomToneVolume : 0.f;
		Loops[static_cast<int32>(ELBAudioLayer::RoomA) + Slot].Update(*this, LBAudioCue::LoopRoomTone, RoomSlotRef[Slot], nullptr, Target, Fade, Fade, 1.f, DeltaSeconds);
	}
}

void ULBAudioSubsystem::UpdateMusic(double Now, float DeltaSeconds)
{
	ELBWardenState State = GetEffectiveWardenState();
	int32 Stage = WardenStage;
	float Distance = WardenDistance;
	const int32 Forced = ConsoleMusicState >= 0 ? ConsoleMusicState : Settings->DebugForceMusicState;
	if (Forced >= 0)
	{
		// A forced state is for tuning: it plays whatever the stage and the distance.
		Stage = 99;
		Distance = 0.f;
	}
	LastMusicTargets = LBAudioLogic::MusicTargets(State, Stage, Distance, Settings->MakeMusicParams());

	const FVector2D TensionFade = Settings->TensionFade;
	const FVector2D ChaseFade = Settings->ChaseFade;
	Loops[static_cast<int32>(ELBAudioLayer::Tension)].Update(*this, LBAudioCue::LoopTension, Settings->Music.Tension, nullptr, LastMusicTargets.Tension,
		static_cast<float>(TensionFade.X), static_cast<float>(TensionFade.Y), 1.f, DeltaSeconds);
	Loops[static_cast<int32>(ELBAudioLayer::Chase)].Update(*this, LBAudioCue::LoopChase, Settings->Music.Chase, nullptr, LastMusicTargets.Chase,
		static_cast<float>(ChaseFade.X), static_cast<float>(ChaseFade.Y), 1.f, DeltaSeconds);

	// The drone: one at a time. A new request waits for a different drone that is still audible to fade out first.
	FLBAudioLoop& Drone = Loops[DroneLayerSlot];
	if (DroneRequested >= 0)
	{
		if (DronePlaying == DroneRequested || Drone.Level <= 0.01f)
		{
			DronePlaying = DroneRequested;
			DroneRequested = -1;
			DroneFadeOutAt = Now + static_cast<double>(Settings->DroneFade.X) + static_cast<double>(Settings->DroneSeconds);
		}
	}
	const bool bHold = DronePlaying >= 0 && DroneRequested < 0 && Now < DroneFadeOutAt;
	const TSoftObjectPtr<USoundBase> DroneRef = Settings->Music.Drones.IsValidIndex(DronePlaying) ? Settings->Music.Drones[DronePlaying] : TSoftObjectPtr<USoundBase>();
	Drone.Update(*this, LBAudioCue::LoopDrone, DroneRef, nullptr, bHold ? 1.f : 0.f, static_cast<float>(Settings->DroneFade.X), static_cast<float>(Settings->DroneFade.Y), 1.f, DeltaSeconds);
}

bool ULBAudioSubsystem::GetPlayerFacts(FVector& OutLocation, bool& bOutSprinting, bool& bOutCandleLit) const
{
	const ALBCharacter* Player = GetPlayer();
	if (!Player)
	{
		return false;
	}
	OutLocation = Player->GetActorLocation();
	bOutSprinting = Player->GetGait() == ELBGait::Sprint;
	const ULBCandleComponent* Candle = Player->GetCandle();
	bOutCandleLit = Candle ? Candle->IsLit() : true;
	return true;
}

void ULBAudioSubsystem::UpdateStress(double Now, float DeltaSeconds)
{
	FVector PlayerLocation = FVector::ZeroVector;
	bool bSprinting = false;
	bool bLit = true;
	const bool bHasPlayer = GetPlayerFacts(PlayerLocation, bSprinting, bLit);
	bCandleLit = bLit;

	const LBAudioLogic::FStressParams Params = Settings->MakeStressParams();
	SprintBonusLeft = bSprinting ? Params.SprintSeconds : FMath::Max(0.f, SprintBonusLeft - DeltaSeconds);

	LBAudioLogic::FStressInputs Inputs;
	Inputs.WardenState = GetEffectiveWardenState();
	Inputs.WardenDistance = ConsoleMusicState >= 0 || Settings->DebugForceMusicState >= 0 ? 0.f : WardenDistance;
	Inputs.bSprintBonus = SprintBonusLeft > 0.f;
	Inputs.ZoneDarkness = CurrentZone.IsValid() ? CurrentZone->Darkness : Settings->OutdoorsDarkness;
	Inputs.bCandleLit = bLit;
	Inputs.bCandleOutImpulse = bCandleOutImpulse;
	bCandleOutImpulse = false;
	StressLevel = LBAudioLogic::Stress(StressLevel, Inputs, DeltaSeconds, Params);

	if (!bHasPlayer)
	{
		return;
	}
	const int32 Tier = LBAudioLogic::BreathTier(StressLevel, Settings->MakeBreathThresholds());
	if (Tier > 0 && Now >= NextBreathAt)
	{
		const TArray<TSoftObjectPtr<USoundBase>>& Set = Tier >= 3 ? Settings->Player.BreathPanic : (Tier == 2 ? Settings->Player.BreathHeavy : Settings->Player.BreathCalm);
		const FName Key = Tier >= 3 ? FName(TEXT("Breath.Panic")) : (Tier == 2 ? FName(TEXT("Breath.Heavy")) : FName(TEXT("Breath.Calm")));
		const int32 Variant = PickVariantFor(Key, Set.Num());
		Play2D(LBAudioCue::Breath, Variant >= 0 ? Set[Variant] : TSoftObjectPtr<USoundBase>(), 1.f, RandomRange(0.97f, 1.03f), Variant, Tier);
		NextBreathAt = Now + static_cast<double>(RandomRange(static_cast<float>(Settings->BreathInterval.X), static_cast<float>(Settings->BreathInterval.Y)));
	}
}

void ULBAudioSubsystem::UpdateAmbientToll(double Now)
{
	if (NextTollTime >= TNumericLimits<double>::Max() && !bFinaleReached && Settings->bAmbientTolls)
	{
		// The tolls were switched off and on again live: start counting again.
		NextTollTime = Now + static_cast<double>(RandomRange(static_cast<float>(Settings->AmbientTollInterval.X), static_cast<float>(Settings->AmbientTollInterval.Y)));
	}
	if (Now < NextTollTime)
	{
		return;
	}
	const ELBWardenState State = GetEffectiveWardenState();
	const bool bChase = State == ELBWardenState::Chase || State == ELBWardenState::Attack;
	const float Tension = Loops[static_cast<int32>(ELBAudioLayer::Tension)].Level;
	const LBAudioLogic::FAmbientTollDecision Decision = LBAudioLogic::AmbientTollPlan(Now, NextTollTime, LastBeatTime, bChase, Tension, BellStageReached,
		bFinaleReached, Stream.FRand(), Stream.FRand(), Settings->MakeTollParams());
	NextTollTime = Decision.NextTime;
	if (Decision.bPlay)
	{
		ScheduleBell(Decision.Stage, Decision.Strikes, 0.f, Settings->AmbientTollSpacing, true);
	}
}

void ULBAudioSubsystem::DrawDebugOverlay(double Now)
{
#if !UE_BUILD_SHIPPING
	if (!GEngine || !Settings)
	{
		return;
	}
	const ULBStormSubsystem* Storm = BoundStorm.Get();
	const ALBAudioZone* Zone = CurrentZone.Get();
	int32 Voices = 0;
	if (const UWorld* World = GetWorld())
	{
		if (FAudioDevice* Device = World->GetAudioDeviceRaw())
		{
			Voices = Device->GetNumActiveSources();
		}
	}
	const ELBWardenState State = GetEffectiveWardenState();
	const FString Lines[] = {
		FString::Printf(TEXT("AUDIO  E %.2f  W %.2f  zone %s  voices %d  stress %.2f  bell stage %d  next toll in %.0fs"), Storm ? Storm->GetPlayerExposure() : 0.f,
			Storm ? Storm->GetWindStrength() : 0.f, Zone ? *Zone->ZoneName.ToString() : TEXT("outdoors"), Voices, StressLevel, BellStageReached,
			NextTollTime >= TNumericLimits<double>::Max() ? -1.0 : FMath::Max(0.0, NextTollTime - Now)),
		FString::Printf(TEXT("  rain out %.2f in %.2f  wind %.2f howl %.2f  room %.2f/%.2f"), Loops[0].Level, Loops[1].Level, Loops[2].Level, Loops[3].Level, Loops[4].Level, Loops[5].Level),
		FString::Printf(TEXT("  music drone %.2f tension %.2f (target %.2f) chase %.2f (target %.2f)  warden state %d stage %d dist %.0f"), Loops[6].Level, Loops[7].Level,
			LastMusicTargets.Tension, Loops[8].Level, LastMusicTargets.Chase, static_cast<int32>(State), WardenStage, WardenDistance < 1.0e8f ? WardenDistance : -1.f),
	};
	for (int32 Index = 0; Index < UE_ARRAY_COUNT(Lines); ++Index)
	{
		GEngine->AddOnScreenDebugMessage(0x4C410000 + Index, 0.f, FColor::Orange, Lines[Index]);
	}
#endif
}

// ---------------------------------------------------------------------------------------------------------------------
// Scheduled sounds
// ---------------------------------------------------------------------------------------------------------------------

void ULBAudioSubsystem::UpdateScheduled(double Now, double UnpausedNow, bool bPaused)
{
	if (Scheduled.IsEmpty())
	{
		return;
	}
	// Played in order of time. PlayScheduled may schedule more (it does not today), so copy the due ones out first.
	TArray<FScheduled, TInlineAllocator<8>> Due;
	for (int32 Index = Scheduled.Num() - 1; Index >= 0; --Index)
	{
		const FScheduled& Candidate = Scheduled[Index];
		// While paused only the items on the unpaused clock (the great bell) are due; the others wait for the game to resume.
		if (Candidate.bUnpausedClock ? Candidate.Time <= UnpausedNow : (!bPaused && Candidate.Time <= Now))
		{
			Due.Add(Scheduled[Index]);
			Scheduled.RemoveAtSwap(Index, EAllowShrinking::No);
		}
	}
	Due.Sort([](const FScheduled& A, const FScheduled& B) { return A.Time < B.Time; });
	for (const FScheduled& Item : Due)
	{
		PlayScheduled(Item, Now);
	}
}

void ULBAudioSubsystem::PlayScheduled(const FScheduled& Item, double Now)
{
	switch (Item.Kind)
	{
	case FScheduled::EKind::Thunder:
		PlayThunder(Item.Aux, Item.Volume, Item.Direction);
		break;
	case FScheduled::EKind::Crack:
	{
		const TArray<TSoftObjectPtr<USoundBase>>& Set = Settings->Thunder.StrikeCrack;
		const int32 Variant = PickVariantFor(FName(TEXT("Thunder.Strike")), Set.Num());
		PlayAt(LBAudioCue::ThunderStrike, Variant >= 0 ? Set[Variant] : TSoftObjectPtr<USoundBase>(), Item.Location, Item.Volume, RandomRange(0.96f, 1.04f), Variant);
		break;
	}
	case FScheduled::EKind::Bell:
	{
		const int32 Stage = FMath::Clamp(Item.Aux, 1, 5);
		const TArray<TSoftObjectPtr<USoundBase>>& Set = Settings->Bell.Stage;
		const TSoftObjectPtr<USoundBase> Ref = Set.IsValidIndex(Stage - 1) ? Set[Stage - 1] : TSoftObjectPtr<USoundBase>();
		UAudioComponent* Strike = PlayAt(Item.bAmbient ? LBAudioCue::BellAmbient : LBAudioCue::Bell, Ref, Settings->BellLocation, Item.Volume, 1.f, Stage - 1, Stage);
		if (Strike && !Item.bAmbient)
		{
			// A UI sound keeps sounding while the game is paused (the ending sequence pauses it).
			Strike->SetUISound(true);
		}
		// P17: the bell swings by itself on every great-bell strike (also without an audio device, when Strike is null).
		OnGreatBellStrike.Broadcast(Stage, Item.Volume);
		break;
	}
	case FScheduled::EKind::Drone:
		StartDrone(Item.Aux, Now);
		break;
	}
}

void ULBAudioSubsystem::PlayThunder(int32 Set, float Volume, const FVector& Direction)
{
	const TArray<TSoftObjectPtr<USoundBase>>* Variants = &Settings->Thunder.Mid;
	FName Key(TEXT("Thunder.Mid"));
	if (Set >= static_cast<int32>(LBAudioLogic::EThunderSet::Near))
	{
		Variants = &Settings->Thunder.Near;
		Key = FName(TEXT("Thunder.Near"));
	}
	else if (Set <= static_cast<int32>(LBAudioLogic::EThunderSet::Far))
	{
		Variants = &Settings->Thunder.Far;
		Key = FName(TEXT("Thunder.Far"));
	}
	const int32 Variant = PickVariantFor(Key, Variants->Num());
	// Along the flash's direction from where the listener is now, so the thunder comes from the flash side.
	const FVector Location = LastListener + Horizontal(Direction) * static_cast<double>(Settings->ThunderDistance);
	PlayAt(LBAudioCue::Thunder, Variant >= 0 ? (*Variants)[Variant] : TSoftObjectPtr<USoundBase>(), Location, Volume, RandomRange(0.95f, 1.05f), Variant, Set);
}

void ULBAudioSubsystem::ScheduleBell(int32 Stage, int32 Strikes, float FirstDelay, float Spacing, bool bAmbient, bool bPlayFirstNow)
{
	const UWorld* World = GetWorld();
	if (!World || !Settings || Strikes <= 0)
	{
		return;
	}
	const double Now = World->GetTimeSeconds();
	const double UnpausedNow = World->GetUnpausedTimeSeconds();
	for (int32 K = 0; K < Strikes; ++K)
	{
		FScheduled Item;
		Item.Kind = FScheduled::EKind::Bell;
		Item.Aux = Stage;
		Item.Volume = bAmbient ? Settings->AmbientTollVolume : 1.f;
		Item.bAmbient = bAmbient;
		Item.bUnpausedClock = !bAmbient;
		Item.Time = (Item.bUnpausedClock ? UnpausedNow : Now) + static_cast<double>(FirstDelay) + static_cast<double>(Spacing) * K;
		if (K == 0 && bPlayFirstNow && FirstDelay <= 0.f)
		{
			PlayScheduled(Item, Now);
			continue;
		}
		if (Scheduled.Num() < MaxScheduled)
		{
			Scheduled.Add(Item);
		}
	}
	// A toll of any kind restarts the wait for the next ambient one.
	const double LastStrike = Now + static_cast<double>(FirstDelay) + static_cast<double>(Spacing) * FMath::Max(Strikes - 1, 0);
	NextTollTime = FMath::Max(NextTollTime >= TNumericLimits<double>::Max() ? 0.0 : NextTollTime,
		LastStrike + static_cast<double>(RandomRange(static_cast<float>(Settings->AmbientTollInterval.X), static_cast<float>(Settings->AmbientTollInterval.Y))));
}

void ULBAudioSubsystem::ScheduleDrone(int32 Drone, float Delay)
{
	const UWorld* World = GetWorld();
	if (!World || Drone < 0 || Scheduled.Num() >= MaxScheduled)
	{
		return;
	}
	FScheduled Item;
	Item.Kind = FScheduled::EKind::Drone;
	Item.Time = World->GetTimeSeconds() + static_cast<double>(Delay);
	Item.Aux = Drone;
	Scheduled.Add(Item);
}

void ULBAudioSubsystem::StartDrone(int32 Drone, double Now)
{
	// Picked up by UpdateMusic (the same tick): it fades the current drone out first when it is a different one.
	DroneRequested = Drone;
}

void ULBAudioSubsystem::PlayBell(int32 Stage, int32 Strikes)
{
	if (!bActive || !Settings)
	{
		UE_LOG(LogLB, Warning, TEXT("Audio: PlayBell ignored, the audio director is not active (needs the storm, DA_Audio and lb.Audio.Enabled 1)"));
		return;
	}
	ScheduleBell(FMath::Clamp(Stage, 1, 5), FMath::Max(Strikes, 1), 0.f, Settings->PlayBellSpacing, false);
}

void ULBAudioSubsystem::PlayDebugThunder(int32 Set)
{
	if (!bActive || !Settings)
	{
		UE_LOG(LogLB, Warning, TEXT("Audio: lb.Audio.Thunder ignored, the audio director is not active"));
		return;
	}
	FVector Forward = FVector::ForwardVector;
	if (const APlayerController* PC = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr)
	{
		if (const APlayerCameraManager* Camera = PC->PlayerCameraManager.Get())
		{
			Forward = Camera->GetCameraRotation().Vector();
		}
	}
	PlayThunder(FMath::Clamp(Set, 0, 2), 1.f, Forward);
}

// ---------------------------------------------------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------------------------------------------------

void ULBAudioSubsystem::HandleLightningStrike(const FLBLightningStrikeInfo& Info)
{
	const UWorld* World = GetWorld();
	if (!bActive || !Settings || !World || Scheduled.Num() >= MaxScheduled)
	{
		return;
	}
	const double Now = World->GetTimeSeconds();
	LBAudioLogic::FThunderPlan Plan = LBAudioLogic::PlanThunder(Info.Brightness, Info.Reason, Stream.FRand(), Settings->MakeThunderParams());
	if (Info.bHasTarget)
	{
		// The strike's own thunder is the near one, after the crack at the target.
		Plan.Set = LBAudioLogic::EThunderSet::Near;
	}
	FScheduled Thunder;
	Thunder.Kind = FScheduled::EKind::Thunder;
	Thunder.Time = Now + static_cast<double>(Plan.Delay);
	Thunder.Aux = static_cast<int32>(Plan.Set);
	Thunder.Volume = Plan.Volume;
	Thunder.Direction = Horizontal(Info.Direction);
	Scheduled.Add(Thunder);

	if (Info.bHasTarget)
	{
		FScheduled Crack;
		Crack.Kind = FScheduled::EKind::Crack;
		Crack.Time = Now + static_cast<double>(Settings->StrikeCrackDelay);
		Crack.Location = Info.TargetLocation;
		Crack.Volume = 1.f;
		Scheduled.Add(Crack);
	}
}

void ULBAudioSubsystem::HandleStateChanged(FGameplayTag Tag, bool bAdded)
{
	const UWorld* World = GetWorld();
	if (!bAdded || !bActive || !Settings || !World)
	{
		return;
	}
	const double Now = World->GetTimeSeconds();
	if (FinaleTag.IsValid() && Tag == FinaleTag)
	{
		bFinaleReached = true;
	}
	const LBAudioLogic::FBellPlan Plan = LBAudioLogic::BellPlan(Tag, Settings->BellBeats);
	if (!Plan.bFound)
	{
		return;
	}
	BellStageReached = FMath::Max(BellStageReached, Plan.Stage);
	LastBeatTime = Now;
	if (Plan.Strikes > 0)
	{
		ScheduleBell(Plan.Stage, Plan.Strikes, Plan.FirstDelay, Plan.Spacing, false, /*bPlayFirstNow*/ true);
	}
	if (Plan.Drone >= 0)
	{
		ScheduleDrone(Plan.Drone, 0.f);
	}
}

void ULBAudioSubsystem::HandleStateReplaced()
{
	const UWorld* World = GetWorld();
	if (!bActive || !Settings || !World)
	{
		return;
	}
	// A checkpoint load: nothing is tolled or droned for the tags that arrive. The progress is re-read, and tolls still waiting are dropped.
	const ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(World);
	BellStageReached = State ? LBAudioLogic::CurrentBellStage(Settings->BellBeats, State->GetStateRef()) : 1;
	bFinaleReached = State && FinaleTag.IsValid() && State->HasState(FinaleTag);
	Scheduled.RemoveAll([](const FScheduled& Item) { return Item.Kind == FScheduled::EKind::Bell || Item.Kind == FScheduled::EKind::Drone; });
	NextTollTime = World->GetTimeSeconds() + static_cast<double>(RandomRange(static_cast<float>(Settings->AmbientTollInterval.X), static_cast<float>(Settings->AmbientTollInterval.Y)));
}

void ULBAudioSubsystem::PlaySting(FName Cue, const TSoftObjectPtr<USoundBase>& Ref)
{
	Play2D(Cue, Ref, 1.f, 1.f);
}

void ULBAudioSubsystem::HandlePlayerSpotted()
{
	if (bActive && Settings)
	{
		PlaySting(LBAudioCue::StingSpotted, Settings->Music.StingSpotted);
	}
}

void ULBAudioSubsystem::HandlePlayerCaught()
{
	if (bActive && Settings)
	{
		PlaySting(LBAudioCue::StingCaught, Settings->Music.StingCaught);
	}
}

void ULBAudioSubsystem::HandleCandleState(bool bLit)
{
	if (!bActive || !Settings)
	{
		return;
	}
	USceneComponent* Candle = Cast<USceneComponent>(BoundCandle.Get());
	const TArray<TSoftObjectPtr<USoundBase>>& Set = bLit ? Settings->Player.CandleLight : Settings->Player.CandleOut;
	const FName Key = bLit ? FName(TEXT("Candle.Light")) : FName(TEXT("Candle.Out"));
	const int32 Variant = PickVariantFor(Key, Set.Num());
	PlayAttached(bLit ? LBAudioCue::CandleLight : LBAudioCue::CandleOut, Variant >= 0 ? Set[Variant] : TSoftObjectPtr<USoundBase>(), Candle, 1.f,
		RandomRange(0.97f, 1.03f), Variant);
	bCandleLit = bLit;
	if (!bLit)
	{
		// The light goes out: a sharp gasp now, and the stress jumps (UpdateStress applies the impulse).
		bCandleOutImpulse = true;
		const TArray<TSoftObjectPtr<USoundBase>>& Gasps = Settings->Player.BreathGasp;
		const int32 GaspVariant = PickVariantFor(FName(TEXT("Breath.Gasp")), Gasps.Num());
		Play2D(LBAudioCue::BreathGasp, GaspVariant >= 0 ? Gasps[GaspVariant] : TSoftObjectPtr<USoundBase>(), 1.f, RandomRange(0.97f, 1.03f), GaspVariant);
	}
}

void ULBAudioSubsystem::HandleRelightStarted()
{
	if (bActive && Settings)
	{
		PlayAttached(LBAudioCue::CandleRelight, Settings->Player.CandleRelight, Cast<USceneComponent>(BoundCandle.Get()));
	}
}

void ULBAudioSubsystem::HandleApparitionAppeared(ALBWardenApparition* Apparition, int32 StationIndex)
{
	if (!bActive || !Settings || !Apparition)
	{
		return;
	}
	PlaySting(LBAudioCue::StingApparition, Settings->Music.StingApparition);
	// The whisper and one chain clink, at the figure.
	const FVector Location = Apparition->GetActorLocation();
	const TArray<TSoftObjectPtr<USoundBase>>& Whispers = Settings->Warden.ApparitionWhisper;
	const int32 WhisperVariant = PickVariantFor(FName(TEXT("Apparition.Whisper")), Whispers.Num());
	PlayAt(LBAudioCue::ApparitionWhisper, WhisperVariant >= 0 ? Whispers[WhisperVariant] : TSoftObjectPtr<USoundBase>(), Location, 1.f, 1.f, WhisperVariant, StationIndex);
	const TArray<TSoftObjectPtr<USoundBase>>& Chains = Settings->Warden.Chains;
	const int32 ChainVariant = PickVariantFor(FName(TEXT("Apparition.Chain")), Chains.Num());
	PlayAt(LBAudioCue::ApparitionChain, ChainVariant >= 0 ? Chains[ChainVariant] : TSoftObjectPtr<USoundBase>(), Location, 1.f, 1.f, ChainVariant, StationIndex);
}

// ---------------------------------------------------------------------------------------------------------------------
// Interaction cues
// ---------------------------------------------------------------------------------------------------------------------

const FLBInteractionCue* ULBAudioSubsystem::FindInteractionCue(const AActor* Actor, int32& OutIndex, bool& bOutSilent)
{
	OutIndex = INDEX_NONE;
	bOutSilent = false;
	if (!Actor || !Settings)
	{
		return nullptr;
	}
	OutIndex = Settings->FindCueRow(Actor->GetClass(), bOutSilent);
	if (OutIndex != INDEX_NONE)
	{
		return &Settings->InteractionCues[OutIndex];
	}
	if (!bOutSilent && !WarnedKeys.Contains(Actor->GetClass()->GetFName()))
	{
		WarnedKeys.Add(Actor->GetClass()->GetFName());
		UE_LOG(LogLB, Log, TEXT("Audio: interactable class '%s' is neither mapped in DA_Audio.InteractionCues nor listed in SilentClasses; it is silent"), *Actor->GetClass()->GetName());
	}
	return nullptr;
}

void ULBAudioSubsystem::NotifyInteracted(AActor* Actor, bool bDenied)
{
	if (!bActive || !Actor)
	{
		return;
	}
	if (!bDenied)
	{
		// A put-down that ended in this very frame already played the Interact cue (OnInspectEnd came first): not a second rustle.
		if (LastInspectEndActor.Get() == Actor && LastInspectEndFrame == GFrameCounter)
		{
			return;
		}
		LastInteractedActor = Actor;
		LastInteractedFrame = GFrameCounter;
	}
	PlayInteractCue(Actor, bDenied);
}

void ULBAudioSubsystem::PlayInteractCue(AActor* Actor, bool bDenied)
{
	if (!bActive || !Actor)
	{
		return;
	}
	int32 CueIndex = INDEX_NONE;
	bool bSilent = false;
	const FLBInteractionCue* Cue = FindInteractionCue(Actor, CueIndex, bSilent);
	if (!Cue)
	{
		return;
	}
	// A dial or lever plays its notch when the position changes (NotifyDialChanged), not a second sound for the same press.
	if (!bDenied && !Cue->DialNotch.IsEmpty() && Actor->FindComponentByClass<ULBDialComponent>())
	{
		return;
	}
	const TArray<TSoftObjectPtr<USoundBase>>& Set = bDenied ? Cue->Denied : Cue->Interact;
	if (Set.IsEmpty())
	{
		return;
	}
	const FName Key(*FString::Printf(TEXT("Cue%d.%s"), CueIndex, bDenied ? TEXT("Denied") : TEXT("Interact")));
	const int32 Variant = PickVariantFor(Key, Set.Num());
	PlayAt(bDenied ? LBAudioCue::Denied : LBAudioCue::Interact, Set[Variant], Actor->GetActorLocation(), Cue->Volume,
		RandomRange(static_cast<float>(Cue->Pitch.X), static_cast<float>(Cue->Pitch.Y)), Variant, CueIndex);
}

void ULBAudioSubsystem::NotifyDialChanged(AActor* Actor, int32 NewIndex)
{
	if (!bActive || !Actor)
	{
		return;
	}
	int32 CueIndex = INDEX_NONE;
	bool bSilent = false;
	const FLBInteractionCue* Cue = FindInteractionCue(Actor, CueIndex, bSilent);
	if (!Cue || Cue->DialNotch.IsEmpty())
	{
		return;
	}
	const FName Key(*FString::Printf(TEXT("Cue%d.Dial"), CueIndex));
	const int32 Variant = PickVariantFor(Key, Cue->DialNotch.Num());
	PlayAt(LBAudioCue::DialNotch, Cue->DialNotch[Variant], Actor->GetActorLocation(), Cue->Volume,
		RandomRange(static_cast<float>(Cue->Pitch.X), static_cast<float>(Cue->Pitch.Y)), Variant, NewIndex);
}

void ULBAudioSubsystem::HandleInspectBegin(ULBInspectableComponent* Inspectable)
{
	// A note is picked up: its mapped Interact cue (the paper rustle) plays now. Putting it down plays it again (HandleInspectEnd).
	AActor* Item = Inspectable ? Inspectable->GetOwner() : nullptr;
	InspectedActor = Item;
	if (bActive && Item)
	{
		PlayInteractCue(Item, /*bDenied*/ false);
	}
}

void ULBAudioSubsystem::HandleInspectEnd(bool bKept)
{
	AActor* Item = InspectedActor.Get();
	InspectedActor.Reset();
	if (!bActive || !Item)
	{
		return;
	}
	// A kept item's grant (CompleteInspection -> OnInteracted) runs before OnInspectEnd and has already played the cue in this frame.
	if (bKept && LastInteractedActor.Get() == Item && LastInteractedFrame == GFrameCounter)
	{
		return;
	}
	LastInspectEndActor = Item;
	LastInspectEndFrame = GFrameCounter;
	PlayInteractCue(Item, /*bDenied*/ false);
}

AActor* ULBAudioSubsystem::FindStepActor(const FGameplayTag& Step) const
{
	if (!Step.IsValid())
	{
		return nullptr;
	}
	for (const ULBAudioProxy* Proxy : Proxies)
	{
		AActor* Candidate = Proxy ? Proxy->Actor.Get() : nullptr;
		if (!Candidate)
		{
			continue;
		}
		TArray<ULBInteractableComponent*> Interactables;
		Candidate->GetComponents(Interactables);
		for (const ULBInteractableComponent* Interactable : Interactables)
		{
			if (Interactable->GrantedStateTags.HasTagExact(Step))
			{
				return Candidate;
			}
		}
	}
	return nullptr;
}

bool ULBAudioSubsystem::IsBellStep(const FGameplayTag& Step) const
{
	return Settings && Step.IsValid() && Settings->SmallBellPitch.Contains(Step);
}

bool ULBAudioSubsystem::IsBellPuzzle(const AActor* Actor) const
{
	if (!Actor)
	{
		return false;
	}
	TArray<ULBSequencePuzzleComponent*> Puzzles;
	Actor->GetComponents(Puzzles);
	for (const ULBSequencePuzzleComponent* Puzzle : Puzzles)
	{
		for (const FGameplayTag& Step : Puzzle->Steps)
		{
			if (IsBellStep(Step))
			{
				return true;
			}
		}
	}
	return false;
}

void ULBAudioSubsystem::NotifyStepAccepted(AActor* Actor, int32 Index, FGameplayTag Step)
{
	// The small-bell strike is only for the cloister bell puzzle (a step that has an entry in SmallBellPitch). Any other sequence puzzle,
	// the chapel candles, is silent per step: the candle's own interact cue already plays.
	if (!bActive || !Settings || !IsBellStep(Step))
	{
		return;
	}
	// At the bell that grants the step (the puzzle component itself may sit on a controller actor), else at the puzzle's actor.
	const AActor* BellActor = FindStepActor(Step);
	const AActor* Where = BellActor ? BellActor : Actor;
	const float* Pitch = Settings->SmallBellPitch.Find(Step);
	PlayAt(LBAudioCue::SmallBellStrike, Settings->SmallBellStrike, Where ? Where->GetActorLocation() : LastListener, 1.f, Pitch ? *Pitch : 1.f, INDEX_NONE, Index);
}

void ULBAudioSubsystem::NotifyPuzzleFailed(AActor* Actor, FGameplayTag WrongStep)
{
	if (!bActive || !Settings)
	{
		return;
	}
	if (IsBellStep(WrongStep) || IsBellPuzzle(Actor))
	{
		const AActor* BellActor = FindStepActor(WrongStep);
		const AActor* Where = BellActor ? BellActor : Actor;
		PlayAt(LBAudioCue::SmallBellFail, Settings->SmallBellFail, Where ? Where->GetActorLocation() : LastListener);
		return;
	}
	// Any other sequence puzzle (the chapel candles): one candle-out variant at the puzzle actor, as the flames are snuffed.
	const TArray<TSoftObjectPtr<USoundBase>>& Set = Settings->Player.CandleOut;
	const int32 Variant = PickVariantFor(FName(TEXT("Candle.Out")), Set.Num());
	PlayAt(LBAudioCue::CandleOut, Variant >= 0 ? Set[Variant] : TSoftObjectPtr<USoundBase>(), Actor ? Actor->GetActorLocation() : LastListener, 1.f,
		RandomRange(0.97f, 1.03f), Variant);
}

void ULBAudioSubsystem::NotifyPuzzleSolved(AActor* Actor)
{
	// Silent for a puzzle that is not the bells: its ritual mechanism and the story beat cover the result.
	if (!bActive || !Settings || !IsBellPuzzle(Actor))
	{
		return;
	}
	PlayAt(LBAudioCue::SmallBellSolved, Settings->SmallBellSolved, Actor ? Actor->GetActorLocation() : LastListener);
}
