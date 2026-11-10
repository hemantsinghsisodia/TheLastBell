// NOTE: this file defines the CVars lb.Cine.Enabled, lb.Cine.Rate, lb.Cine.NoEnd and lb.Cine.Debug as file statics.
// Never Live Code it (MCP_NOTES, "PIE Simulate captures and Live Coding" item 2): close Unreal and use Tools/build_and_test.ps1.
#include "Cinematics/LBCinematicSubsystem.h"
#include "Cinematics/LBCinematicSettings.h"
#include "Cinematics/LBCinematicWidget.h"
#include "Audio/LBAudioSubsystem.h"
#include "Camera/PlayerCameraManager.h"
#include "Character/LBCharacter.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "LevelSequence.h"
#include "LevelSequenceActor.h"
#include "LevelSequencePlayer.h"
#include "MovieScene.h"
#include "MovieSceneSequencePlayer.h"
#include "Misc/PackageName.h"
#include "Save/LBSaveSubsystem.h"
#include "Sound/SoundMix.h"
#include "TimerManager.h"
#include "Storm/LBStormSubsystem.h"
#include "Systems/LBGameSettings.h"
#include "Systems/LBPlayerController.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "Blueprint/UserWidget.h"
#include "LBLog.h"

namespace
{
#if !UE_BUILD_SHIPPING
	TAutoConsoleVariable<int32> CVarCineEnabled(
		TEXT("lb.Cine.Enabled"), 1,
		TEXT("1 = cinematics start and play (the intro, the finale). 0 = a running one stops at once (restore, no must markers) and nothing starts. Non-shipping."),
		ECVF_Default);

	TAutoConsoleVariable<float> CVarCineRate(
		TEXT("lb.Cine.Rate"), 1.0f,
		TEXT("Play rate of cinematics, clamped 0.25 to 16. Tests use 8. Everything the subsystem times is scaled by it. Non-shipping."),
		ECVF_Default);

	TAutoConsoleVariable<int32> CVarCineNoEnd(
		TEXT("lb.Cine.NoEnd"), 0,
		TEXT("1 = the end marker only restores and logs 'Cine: end suppressed (lb.Cine.NoEnd)' instead of completing the game (review sessions). Non-shipping."),
		ECVF_Default);

	TAutoConsoleVariable<int32> CVarCineDebug(
		TEXT("lb.Cine.Debug"), 0,
		TEXT("1 = show the sequence time, the next marker, the lock and the skip state on screen. Non-shipping."),
		ECVF_Default);
#endif

	/** Below this amplitude the bell swing stops (section 2.8). */
	constexpr float BellStopDegrees = 0.05f;
	/** The camera comes up from black this long after a skip (section 2.3). */
	constexpr float SkipFadeSeconds = 0.5f;
	/** The widget sits above the HUD. */
	constexpr int32 WidgetZOrder = 1000;
#if !UE_BUILD_SHIPPING
	constexpr uint64 DebugKey = 0x4C42434E45ull;
#endif

	/** The head bone for a skeletal actor (the Warden figure), else the actor's location. */
	FVector LookTargetLocation(const AActor* Actor)
	{
		if (const USkeletalMeshComponent* Mesh = Actor->FindComponentByClass<USkeletalMeshComponent>())
		{
			static const FName HeadBone(TEXT("head"));
			if (Mesh->GetBoneIndex(HeadBone) != INDEX_NONE)
			{
				return Mesh->GetBoneLocation(HeadBone);
			}
		}
		return Actor->GetActorLocation();
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Plumbing
// ---------------------------------------------------------------------------------------------------------------------

bool ULBCinematicSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

TStatId ULBCinematicSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(ULBCinematicSubsystem, STATGROUP_Tickables);
}

ETickableTickType ULBCinematicSubsystem::GetTickableTickType() const
{
	return IsTemplate() ? ETickableTickType::Never : ETickableTickType::Conditional;
}

bool ULBCinematicSubsystem::IsTickable() const
{
	return bStartPending || bRunActive || Pendulum.IsSwinging();
}

bool ULBCinematicSubsystem::IsEnabled() const
{
#if !UE_BUILD_SHIPPING
	return CVarCineEnabled.GetValueOnGameThread() != 0;
#else
	return true;
#endif
}

float ULBCinematicSubsystem::ReadRate() const
{
#if !UE_BUILD_SHIPPING
	return FMath::Clamp(CVarCineRate.GetValueOnGameThread(), 0.25f, 16.f);
#else
	return 1.f;
#endif
}

void ULBCinematicSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	// The audio director exists before this one reads it (the bell swing binds its strike delegate).
	Collection.InitializeDependency<ULBAudioSubsystem>();
	Super::Initialize(Collection);
}

void ULBCinematicSubsystem::Deinitialize()
{
	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().ClearTimer(SkipFadeTimer);
	}
	if (bRunActive && !bTravelling)
	{
		// Torn down mid-run without a travel (a test ending PIE, a map change): put the player back, guarded for objects already going.
		if (Widget && IsValid(Widget))
		{
			Widget->RemoveFromParent();
		}
		if (ALBCharacter* Character = GetPlayerCharacter())
		{
			Character->SetInputLock(ELBInputLock::None);
		}
		if (APlayerController* PC = GetPlayerController())
		{
			if (ALBPlayerController* LBPC = Cast<ALBPlayerController>(PC))
			{
				LBPC->SetHUDHidden(false);
			}
			if (PC->PlayerCameraManager && IsValid(PC->PlayerCameraManager))
			{
				PC->PlayerCameraManager->StopCameraFade();
			}
		}
	}
	UnbindPlayerInput();
	if (Player)
	{
		Player->OnFinished.RemoveDynamic(this, &ULBCinematicSubsystem::HandlePlayerFinished);
	}
	// A CompleteGame travel leaves the mix pushed over the black screen; the world teardown is where it comes off.
	PopMix();
	UnbindWorldEvents();
	bRunActive = false;
	bStartPending = false;
	Super::Deinitialize();
}

void ULBCinematicSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	SetupWorld();
	if (!Settings || !IsEnabled())
	{
		return;
	}

	// The NewGame rule (section 2.3): decided here, before the save subsystem clears the pending restore one tick later.
	for (const FLBCinematicDef& Def : Settings->Cinematics)
	{
		if (Def.Trigger == ELBCineTrigger::NewGame && ShouldStartNewGameIntro(Def))
		{
			StartDef = Def;
			bStartPending = true;
			if (Def.bStartBlack)
			{
				if (APlayerController* PC = GetPlayerController())
				{
					if (PC->PlayerCameraManager)
					{
						PC->PlayerCameraManager->SetManualCameraFade(1.f, FLinearColor::Black, false);
					}
				}
			}
			UE_LOG(LogLB, Log, TEXT("Cine: %s will start on the first tick (New Game)"), *Def.Id.ToString());
			break;
		}
	}
}

bool ULBCinematicSubsystem::ShouldStartNewGameIntro(const FLBCinematicDef& Def) const
{
	const UWorld* World = GetWorld();
	const ULBGameSettings* GameSettings = ULBGameSettings::Get();
	if (!World || !GameSettings || GameSettings->NewGameMap.IsNull())
	{
		return false;
	}
	const FString WorldPackage = UWorld::RemovePIEPrefix(World->GetOutermost()->GetName());
	if (WorldPackage != GameSettings->NewGameMap.GetLongPackageName())
	{
		return false;
	}
	const ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(this);
	if (Save && Save->HasPendingRestore())
	{
		return false;
	}
	const ULBWorldStateSubsystem* State = GetWorldState();
	if (State && Def.BlockingTag.IsValid() && State->HasState(Def.BlockingTag))
	{
		return false;
	}
	return true;
}

bool ULBCinematicSubsystem::LoadSettings()
{
	Settings = nullptr;
	if (SettingsOverride)
	{
		Settings = SettingsOverride;
		return true;
	}
	const ULBGameSettings* GameSettings = ULBGameSettings::Get();
	if (!GameSettings || GameSettings->CinematicSettings.IsNull())
	{
		if (!bLoggedNoSettings)
		{
			bLoggedNoSettings = true;
			UE_LOG(LogLB, Log, TEXT("Cine: no CinematicSettings in Project Settings > The Last Bell: cinematics are off for this world"));
		}
		return false;
	}
	// Check the package first: loading a missing asset makes the engine log its own warnings.
	if (!FPackageName::DoesPackageExist(GameSettings->CinematicSettings.GetLongPackageName()))
	{
		if (!bLoggedNoSettings)
		{
			bLoggedNoSettings = true;
			UE_LOG(LogLB, Log, TEXT("Cine: CinematicSettings points at %s, which does not exist: cinematics are off for this world"),
				*GameSettings->CinematicSettings.ToString());
		}
		return false;
	}
	Settings = GameSettings->CinematicSettings.LoadSynchronous();
	if (!Settings && !bLoggedNoSettings)
	{
		bLoggedNoSettings = true;
		UE_LOG(LogLB, Log, TEXT("Cine: CinematicSettings (%s) did not load: cinematics are off for this world"), *GameSettings->CinematicSettings.ToString());
	}
	return Settings != nullptr;
}

void ULBCinematicSubsystem::OverrideSettings(ULBCinematicSettings* InSettings)
{
	SettingsOverride = InSettings;
}

void ULBCinematicSubsystem::Rearm()
{
	SetupWorld();
}

void ULBCinematicSubsystem::SetupWorld()
{
	// A swing in progress goes back to rest with the OLD rest transforms before they are read again.
	if (Pendulum.IsSwinging())
	{
		Pendulum.Reset();
		ApplyBellAngle(0.f);
	}
	UnbindWorldEvents();
	BellActor.Reset();
	BellComponent.Reset();
	HeadstockActor.Reset();
	RopeActor.Reset();

	if (!LoadSettings())
	{
		return;
	}
	BindWorldEvents();
	FindBellPieces();
}

void ULBCinematicSubsystem::BindWorldEvents()
{
	if (ULBWorldStateSubsystem* State = GetWorldState())
	{
		State->OnStateChanged.AddUniqueDynamic(this, &ULBCinematicSubsystem::HandleStateChanged);
		bStateBound = true;
	}
}

void ULBCinematicSubsystem::UnbindWorldEvents()
{
	if (bStateBound)
	{
		if (ULBWorldStateSubsystem* State = GetWorldState())
		{
			State->OnStateChanged.RemoveDynamic(this, &ULBCinematicSubsystem::HandleStateChanged);
		}
		bStateBound = false;
	}
	if (BellStrikeHandle.IsValid())
	{
		if (ULBAudioSubsystem* Audio = BoundAudio.Get())
		{
			Audio->OnGreatBellStrike.Remove(BellStrikeHandle);
		}
		BellStrikeHandle.Reset();
	}
	BoundAudio.Reset();
}

void ULBCinematicSubsystem::FindBellPieces()
{
	if (!Settings)
	{
		return;
	}
	BellActor = FindActorWithTag(Settings->BellActorTag);
	if (AActor* Bell = BellActor.Get())
	{
		USceneComponent* Found = nullptr;
		TInlineComponentArray<USceneComponent*> Components(Bell);
		for (USceneComponent* Component : Components)
		{
			if (Component && Component->GetFName() == Settings->BellComponentName)
			{
				Found = Component;
				break;
			}
		}
		if (!Found)
		{
			UE_LOG(LogLB, Warning, TEXT("Cine: the bell actor %s has no component named %s: swinging its root component instead"), *Bell->GetName(), *Settings->BellComponentName.ToString());
			Found = Bell->GetRootComponent();
		}
		BellComponent = Found;
	}
	if (!BellComponent.IsValid())
	{
		return;
	}

	HeadstockActor = FindActorWithTag(Settings->BellHeadstockTag);
	RopeActor = FindActorWithTag(Settings->BellRopeTag);

	const USceneComponent* Bell = BellComponent.Get();
	BellRestLocation = Bell->GetComponentLocation();
	BellRestRotation = Bell->GetComponentQuat();

	if (const AActor* Headstock = HeadstockActor.Get())
	{
		HeadstockRestLocation = Headstock->GetActorLocation();
		HeadstockRestRotation = Headstock->GetActorQuat();
		SwingPivot = HeadstockRestLocation;
		SwingAxis = LBCinematicLogic::AxleAxis(HeadstockRestRotation, Settings->BellSwingAxis);
	}
	else
	{
		// No headstock: the bell turns about its own origin on its own rest axis.
		SwingPivot = BellRestLocation;
		SwingAxis = LBCinematicLogic::AxleAxis(BellRestRotation, Settings->BellSwingAxis);
		if (!bWarnedNoHeadstock)
		{
			bWarnedNoHeadstock = true;
			UE_LOG(LogLB, Warning, TEXT("Cine: no actor tagged %s: the bell swings about its own origin, without a headstock"), *Settings->BellHeadstockTag.ToString());
		}
	}
	if (const AActor* Rope = RopeActor.Get())
	{
		RopeRestLocation = Rope->GetActorLocation();
	}
	else if (!bWarnedNoRope)
	{
		bWarnedNoRope = true;
		UE_LOG(LogLB, Warning, TEXT("Cine: no actor tagged %s: the bell swings without its rope"), *Settings->BellRopeTag.ToString());
	}

	if (ULBAudioSubsystem* Audio = GetWorld() ? GetWorld()->GetSubsystem<ULBAudioSubsystem>() : nullptr)
	{
		BoundAudio = Audio;
		BellStrikeHandle = Audio->OnGreatBellStrike.AddUObject(this, &ULBCinematicSubsystem::HandleGreatBellStrike);
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------------------------------------------------

ULBWorldStateSubsystem* ULBCinematicSubsystem::GetWorldState() const
{
	return ULBWorldStateSubsystem::Get(this);
}

APlayerController* ULBCinematicSubsystem::GetPlayerController() const
{
	const UWorld* World = GetWorld();
	return World ? World->GetFirstPlayerController() : nullptr;
}

ALBCharacter* ULBCinematicSubsystem::GetPlayerCharacter() const
{
	const APlayerController* PC = GetPlayerController();
	return PC ? Cast<ALBCharacter>(PC->GetPawn()) : nullptr;
}

AActor* ULBCinematicSubsystem::FindActorWithTag(FName Tag) const
{
	UWorld* World = GetWorld();
	if (!World || Tag.IsNone())
	{
		return nullptr;
	}
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		if (It->ActorHasTag(Tag))
		{
			return *It;
		}
	}
	return nullptr;
}

float ULBCinematicSubsystem::GetSkipHoldFraction() const
{
	return Settings ? SkipHold.Fraction(FMath::Clamp(Settings->SkipHoldSeconds, 0.1f, 10.f)) : 0.f;
}

int32 ULBCinematicSubsystem::GetFiredMarkerCount() const
{
	return Fired.CountSetBits();
}

// ---------------------------------------------------------------------------------------------------------------------
// Triggers
// ---------------------------------------------------------------------------------------------------------------------

void ULBCinematicSubsystem::HandleStateChanged(FGameplayTag Tag, bool bAdded)
{
	if (!bAdded || !Settings)
	{
		return;
	}
	for (const FLBCinematicDef& Def : Settings->Cinematics)
	{
		if (Def.Trigger != ELBCineTrigger::TagAdded || !Def.TriggerTag.IsValid() || !Tag.MatchesTagExact(Def.TriggerTag))
		{
			continue;
		}
		const ULBWorldStateSubsystem* State = GetWorldState();
		if (State && Def.BlockingTag.IsValid() && State->HasState(Def.BlockingTag))
		{
			continue;
		}
		if (bRunActive || !IsEnabled())
		{
			UE_LOG(LogLB, Warning, TEXT("Cine: %s not played when %s was added: %s"), *Def.Id.ToString(), *Tag.ToString(),
				bRunActive ? *FString::Printf(TEXT("%s is already playing"), *RunDef.Id.ToString()) : TEXT("lb.Cine.Enabled is 0"));
			return;
		}
		// Copy: the settings array must not change under the run, and PlayDef grants tags that re-enter this handler.
		const FLBCinematicDef Copy = Def;
		PlayDef(Copy);
		return;
	}
}

bool ULBCinematicSubsystem::Play(FName Id)
{
	if (!IsEnabled())
	{
		UE_LOG(LogLB, Warning, TEXT("Cine: Play(%s) ignored: lb.Cine.Enabled is 0"), *Id.ToString());
		return false;
	}
	if (bRunActive)
	{
		UE_LOG(LogLB, Warning, TEXT("Cine: Play(%s) ignored: %s is already playing"), *Id.ToString(), *RunDef.Id.ToString());
		return false;
	}
	if (!Settings)
	{
		LoadSettings();
	}
	if (!Settings)
	{
		UE_LOG(LogLB, Warning, TEXT("Cine: Play(%s) ignored: there are no cinematic settings for this world"), *Id.ToString());
		return false;
	}
	const FLBCinematicDef* Def = Settings->FindDef(Id);
	if (!Def)
	{
		UE_LOG(LogLB, Warning, TEXT("Cine: Play(%s) ignored: no such cinematic in the settings"), *Id.ToString());
		return false;
	}
	const FLBCinematicDef Copy = *Def;
	return PlayDef(Copy);
}

#if !UE_BUILD_SHIPPING
bool ULBCinematicSubsystem::PlayAsset(const FSoftObjectPath& SequencePath)
{
	if (!IsEnabled() || bRunActive)
	{
		UE_LOG(LogLB, Warning, TEXT("Cine: PlayAsset ignored (%s)"), bRunActive ? TEXT("a cinematic is playing") : TEXT("lb.Cine.Enabled is 0"));
		return false;
	}
	if (!Settings)
	{
		LoadSettings();
	}
	if (!Settings)
	{
		// No DA_Cinematics (the S1b spike): the class defaults give the lock, skip and fade numbers.
		if (!FallbackSettings)
		{
			FallbackSettings = NewObject<ULBCinematicSettings>(this);
		}
		Settings = FallbackSettings;
	}
	FLBCinematicDef Def;
	Def.Id = TEXT("Asset");
	Def.Sequence = TSoftObjectPtr<ULevelSequence>(SequencePath);
	Def.InitialLock = ELBInputLock::Full;
	Def.bSkippableAtStart = true;
	return PlayDef(Def);
}
#endif // !UE_BUILD_SHIPPING

// ---------------------------------------------------------------------------------------------------------------------
// The run
// ---------------------------------------------------------------------------------------------------------------------

void ULBCinematicSubsystem::ParseMarkersOf(ULevelSequence& Sequence, double& OutDurationSeconds)
{
	Markers.Reset();
	OutDurationSeconds = 0.0;
	UMovieScene* MovieScene = Sequence.GetMovieScene();
	if (!MovieScene)
	{
		return;
	}
	const TRange<FFrameNumber> Range = MovieScene->GetPlaybackRange();
	const FFrameNumber Lower = Range.HasLowerBound() ? Range.GetLowerBoundValue() : FFrameNumber(0);
	const FFrameNumber Upper = Range.HasUpperBound() ? Range.GetUpperBoundValue() : Lower;
	const FFrameRate TickResolution = MovieScene->GetTickResolution();
	OutDurationSeconds = TickResolution.AsSeconds(FFrameTime(Upper - Lower));

	for (const FMovieSceneMarkedFrame& Frame : MovieScene->GetMarkedFrames())
	{
		FLBCineMarker Marker;
		Marker.Seconds = TickResolution.AsSeconds(FFrameTime(Frame.FrameNumber - Lower));
		FString Error;
		if (LBCinematicLogic::ParseMarker(Frame.Label, Marker, Error))
		{
			Markers.Add(MoveTemp(Marker));
		}
		else
		{
			UE_LOG(LogLB, Error, TEXT("Cine: %s: %s at %.2f s (ignored)"), *Sequence.GetName(), *Error, Marker.Seconds);
		}
	}
	LBCinematicLogic::SortMarkers(Markers);
	Fired.Init(false, Markers.Num());
}

bool ULBCinematicSubsystem::PlayDef(const FLBCinematicDef& Def)
{
	UWorld* World = GetWorld();
	if (!World || bRunActive)
	{
		return false;
	}
	if (!Settings)
	{
#if !UE_BUILD_SHIPPING
		// Only PlayAsset reaches here without settings (the S1b spike): the class defaults give the lock, skip and fade numbers.
		if (!FallbackSettings)
		{
			FallbackSettings = NewObject<ULBCinematicSettings>(this);
		}
		Settings = FallbackSettings;
#else
		return false;
#endif
	}
	GetWorld()->GetTimerManager().ClearTimer(SkipFadeTimer);

	// Fresh run state.
	Markers.Reset();
	Fired.Reset();
	PrevSeconds = -1.0;
	CurSeconds = 0.0;
	SequenceSeconds = 0.0;
	bPlayerFinished = false;
	bPostHold = false;
	bTravelling = false;
	bFailSafe = false;
	bCardActive = false;
	bCreditsRolling = false;
	bEndPending = false;
	Mark = FMarkMove();
	Look = FLookAssist();
	SkipHold.End();
	LoadedSequence = nullptr;
	RunDef = Def;
	RunRate = ReadRate();
	WantedLock = Def.InitialLock;
	bSkippable = Def.bSkippableAtStart;
	bRunActive = true;

	APlayerController* PC = GetPlayerController();
	if (Def.bStartBlack && PC && PC->PlayerCameraManager)
	{
		PC->PlayerCameraManager->SetManualCameraFade(1.f, FLinearColor::Black, false);
	}

	// 1. Grant.
	if (Def.GrantOnStart.Num() > 0)
	{
		if (ULBWorldStateSubsystem* State = GetWorldState())
		{
			State->AddStates(Def.GrantOnStart);
		}
	}

	// 2. Load the sequence (small: no preloading).
	// Already in memory (an unsaved asset, a test's transient sequence), else on disk. A missing package is checked first: loading it
	// would make the engine log its own warnings.
	ULevelSequence* Sequence = Def.Sequence.IsNull() ? nullptr : Def.Sequence.Get();
	if (!Sequence && !Def.Sequence.IsNull() && FPackageName::DoesPackageExist(Def.Sequence.GetLongPackageName()))
	{
		Sequence = Def.Sequence.LoadSynchronous();
	}
	if (!Sequence)
	{
		FailRun(Def, TEXT("the sequence did not load"));
		return false;
	}
	LoadedSequence = Sequence;

	// 3. Parse the markers into seconds.
	ParseMarkersOf(*Sequence, SequenceSeconds);

	// 4. The player. The subsystem handles input, the player pawn and the HUD itself, so every disable flag is off.
	FMovieSceneSequencePlaybackSettings PlaybackSettings;
	PlaybackSettings.bAutoPlay = false;
	PlaybackSettings.PlayRate = RunRate;
	PlaybackSettings.bDisableMovementInput = false;
	PlaybackSettings.bDisableLookAtInput = false;
	PlaybackSettings.bHidePlayer = false;
	PlaybackSettings.bHideHud = false;
	ALevelSequenceActor* Actor = nullptr;
	Player = ULevelSequencePlayer::CreateLevelSequencePlayer(World, Sequence, PlaybackSettings, Actor);
	SequenceActor = Actor;
	if (!Player || !Actor)
	{
		FailRun(Def, TEXT("the sequence player could not be created"));
		return false;
	}

	UE_LOG(LogLB, Log, TEXT("Cine: play %s (%s, %.1f s, %d markers)"), *Def.Id.ToString(), *Sequence->GetName(), SequenceSeconds, Markers.Num());

	// 5. Bind, lock, hide the HUD, build the widget, go.
	Player->OnFinished.AddUniqueDynamic(this, &ULBCinematicSubsystem::HandlePlayerFinished);
	BindPlayerInput();
	if (ALBCharacter* Character = GetPlayerCharacter())
	{
		Character->SetInputLock(Def.InitialLock);
	}
	if (ALBPlayerController* LBPC = Cast<ALBPlayerController>(PC))
	{
		LBPC->SetHUDHidden(true);
	}
	if (PC)
	{
		Widget = CreateWidget<ULBCinematicWidget>(PC, ULBCinematicWidget::StaticClass());
		if (Widget)
		{
			Widget->SetSkipPromptText(Settings->SkipPromptText);
			Widget->AddToViewport(WidgetZOrder);
			Widget->SetSkipState(bSkippable, 0.f);
		}
	}

	Player->Play();
	if (!Player->IsPlaying())
	{
		FailRun(Def, TEXT("the sequence player did not start"));
		return false;
	}
	OnCinematicStarted.Broadcast(Def.Id);
	return true;
}

void ULBCinematicSubsystem::FailRun(const FLBCinematicDef& Def, const TCHAR* Why)
{
	UE_LOG(LogLB, Error, TEXT("Cine: %s failed (%s): firing the must markers, restoring input and the view"), *Def.Id.ToString(), Why);
	bFailSafe = true;
	bRunActive = true;
	RunDef = Def;

	if (Markers.IsEmpty())
	{
		// No sequence to read: the definition's own fail-safe list stands in for its must markers.
		for (const FString& Label : Def.FailSafeMarkers)
		{
			FLBCineMarker Marker;
			FString Error;
			if (LBCinematicLogic::ParseMarker(Label, Marker, Error))
			{
				Marker.bMust = true;
				Markers.Add(MoveTemp(Marker));
			}
			else
			{
				UE_LOG(LogLB, Error, TEXT("Cine: %s fail-safe %s (ignored)"), *Def.Id.ToString(), *Error);
			}
		}
		Fired.Init(false, Markers.Num());
	}

	TArray<int32> Indices;
	LBCinematicLogic::MustMarkersOnSkip(Markers, Fired, Indices);
	FireIndices(Indices);
	if (bRunActive)
	{
		FinishRun(TEXT("failed"));
	}
}

void ULBCinematicSubsystem::HandlePlayerFinished()
{
	// Called from inside the player's own update: only note it. The next tick fires what is left and restores.
	bPlayerFinished = true;
}

void ULBCinematicSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	if (!GetWorld())
	{
		return;
	}

	if (bStartPending)
	{
		bStartPending = false;
		if (IsEnabled())
		{
			const FLBCinematicDef Copy = StartDef;
			PlayDef(Copy);
		}
		else if (const APlayerController* PC = GetPlayerController())
		{
			// The CVar went to 0 after the black was set: never leave the screen black.
			if (PC->PlayerCameraManager)
			{
				PC->PlayerCameraManager->StopCameraFade();
			}
		}
	}

	if (bRunActive)
	{
		if (!IsEnabled())
		{
			FinishRun(TEXT("lb.Cine.Enabled 0"));
		}
		else
		{
			TickRun(DeltaTime * RunRate);
		}
	}

	TickBell(DeltaTime);
#if !UE_BUILD_SHIPPING
	if (CVarCineDebug.GetValueOnGameThread() != 0)
	{
		DrawDebug();
	}
#endif
}

void ULBCinematicSubsystem::TickRun(float ScaledDelta)
{
	if (!Player)
	{
		FinishRun(TEXT("no player"));
		return;
	}
	if (!bPlayerFinished && !Player->IsPlaying() && !Player->IsPaused())
	{
		bPlayerFinished = true;
	}

	TArray<int32> Indices;
	if (bPlayerFinished && !bPostHold)
	{
		// The sequence reached its end: everything left up to the end counts as crossed.
		LBCinematicLogic::MarkersToFire(Markers, PrevSeconds, SequenceSeconds + 1.0, Fired, Indices);
		FireIndices(Indices);
		if (!bRunActive)
		{
			return;
		}
		if (bCreditsRolling)
		{
			// The credits outlast the sequence: hold the run (cards, credits and skip keep ticking, no markers are read) until the roll
			// ends or is skipped, so a pending end is not lost. Black stays whatever the sequence's completion state restored.
			bPostHold = true;
			if (const APlayerController* PC = GetPlayerController())
			{
				if (PC->PlayerCameraManager)
				{
					PC->PlayerCameraManager->SetManualCameraFade(1.f, FLinearColor::Black, false);
				}
			}
		}
		else
		{
			if (bEndPending)
			{
				DoEnd();
			}
			else
			{
				FinishRun(TEXT("finished"), /*bKeepFade*/ false, /*bSnapMark*/ true);
			}
			return;
		}
	}
	else if (!bPostHold)
	{
		CurSeconds = FMath::Max(Player->GetCurrentTime().AsSeconds() - Player->GetStartTime().AsSeconds(), 0.0);
		const double From = PrevSeconds;
		PrevSeconds = FMath::Max(PrevSeconds, CurSeconds);
		LBCinematicLogic::MarkersToFire(Markers, From, CurSeconds, Fired, Indices);
		FireIndices(Indices);
		if (!bRunActive)
		{
			return;
		}
	}

	TickMark(ScaledDelta);
	TickLook(ScaledDelta);
	TickCard(ScaledDelta);
	TickCredits(ScaledDelta);
	if (!bRunActive)
	{
		return;
	}
	if (bPostHold && !bCreditsRolling)
	{
		// The roll is over and no end was waiting for it.
		FinishRun(TEXT("finished"), /*bKeepFade*/ false, /*bSnapMark*/ true);
		return;
	}

	const float HoldNeeded = Settings ? FMath::Clamp(Settings->SkipHoldSeconds, 0.1f, 10.f) : 1.f;
	if (SkipHold.Tick(ScaledDelta, HoldNeeded, bSkippable))
	{
		RequestSkip();
		return;
	}
	if (Widget)
	{
		Widget->SetSkipState(bSkippable, SkipHold.Fraction(HoldNeeded));
	}
}

void ULBCinematicSubsystem::FireIndices(const TArray<int32>& Indices)
{
	for (const int32 Index : Indices)
	{
		if (!bRunActive)
		{
			return;
		}
		FireMarkerAt(Index);
	}
}

void ULBCinematicSubsystem::FireMarkerAt(int32 Index)
{
	if (!Markers.IsValidIndex(Index))
	{
		return;
	}
	// A copy: a marker may end the run, which clears the array.
	const FLBCineMarker Marker = Markers[Index];
	UE_LOG(LogLB, Log, TEXT("Cine: marker '%s' at %.2f s"), *Marker.Label, Marker.Seconds);
	FireMarker(Marker);
	OnMarkerFired.Broadcast(Marker.Label);
}

void ULBCinematicSubsystem::FireMarker(const FLBCineMarker& Marker)
{
	UWorld* World = GetWorld();
	switch (Marker.Kind)
	{
	case ELBCineMarkerKind::Card:
		StartCard(Marker.Name);
		break;

	case ELBCineMarkerKind::Tag:
		if (ULBWorldStateSubsystem* State = GetWorldState())
		{
			State->AddState(Marker.Tag);
		}
		break;

	case ELBCineMarkerKind::Bell:
		if (ULBAudioSubsystem* Audio = World ? World->GetSubsystem<ULBAudioSubsystem>() : nullptr)
		{
			Audio->PlayBell(Marker.Stage, Marker.Strikes);
		}
		break;

	case ELBCineMarkerKind::Strike:
	{
		ULBStormSubsystem* Storm = World ? World->GetSubsystem<ULBStormSubsystem>() : nullptr;
		const float Brightness = Marker.Value >= 0.f ? Marker.Value : 1.f;
		if (!Storm)
		{
			break;
		}
		if (AActor* Target = FindActorWithTag(Marker.Name))
		{
			Storm->RequestFlashAtTarget(Brightness, 0.f, ELBFlashReason::Scripted, ELBFlashProfile::Auto, Target);
		}
		else
		{
			UE_LOG(LogLB, Warning, TEXT("Cine: marker '%s': no actor tagged %s: a plain flash instead"), *Marker.Label, *Marker.Name.ToString());
			Storm->RequestFlash(Brightness, 0.f, ELBFlashReason::Scripted);
		}
		break;
	}

	case ELBCineMarkerKind::Flash:
		if (ULBStormSubsystem* Storm = World ? World->GetSubsystem<ULBStormSubsystem>() : nullptr)
		{
			Storm->RequestFlash(Marker.Value, 0.f, ELBFlashReason::Scripted);
		}
		break;

	case ELBCineMarkerKind::Look:
		StartLook(Marker);
		break;

	case ELBCineMarkerKind::Mark:
		StartMark(Marker);
		break;

	case ELBCineMarkerKind::Lock:
		ApplyLock(Marker.Lock);
		break;

	case ELBCineMarkerKind::Skip:
		bSkippable = Marker.bFlag;
		if (!bSkippable)
		{
			SkipHold.End();
		}
		break;

	case ELBCineMarkerKind::Mix:
		if (Marker.bFlag)
		{
			PushMix();
		}
		else
		{
			PopMix();
		}
		break;

	case ELBCineMarkerKind::Credits:
		if (!bFailSafe)
		{
			StartCredits(Marker.Value);
		}
		break;

	case ELBCineMarkerKind::End:
		if (bCreditsRolling && !bFailSafe)
		{
			// Wait for the roll to finish (or be skipped).
			bEndPending = true;
		}
		else
		{
			DoEnd();
		}
		break;
	}
}

void ULBCinematicSubsystem::DoEnd()
{
	bEndPending = false;
#if !UE_BUILD_SHIPPING
	if (CVarCineNoEnd.GetValueOnGameThread() != 0)
	{
		UE_LOG(LogLB, Log, TEXT("Cine: end suppressed (lb.Cine.NoEnd)"));
		FinishRun(TEXT("end suppressed"), false, true);
		return;
	}
#endif
	ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(this);
	if (!Save)
	{
		UE_LOG(LogLB, Error, TEXT("Cine: end: there is no save subsystem, the game cannot be completed"));
		FinishRun(TEXT("end failed"));
		return;
	}
	UE_LOG(LogLB, Log, TEXT("Cine: end -> CompleteGame"));
	Save->CompleteGame();
	// A refused CompleteGame (no menu map, a travel already pending) leaves no travel: then this is an ordinary restore.
	bTravelling = Save->IsTravelPending();
	FinishRun(bTravelling ? TEXT("game completed") : TEXT("end did not travel"), false, true);
}

void ULBCinematicSubsystem::RequestSkip()
{
	if (!bRunActive)
	{
		return;
	}
	TArray<int32> Indices;

	// The credits roll stops first, so a pending end completes at once when its marker fires.
	if (bCreditsRolling)
	{
		StopCredits();
	}
	LBCinematicLogic::MustMarkersOnSkip(Markers, Fired, Indices);
	UE_LOG(LogLB, Log, TEXT("Cine: skip at %.2f s (%d must markers fired)"), CurSeconds, Indices.Num());
	FireIndices(Indices);
	if (!bRunActive)
	{
		return;
	}
	if (bEndPending)
	{
		DoEnd();
		if (!bRunActive)
		{
			return;
		}
	}

	if (Player && (Player->IsPlaying() || Player->IsPaused()))
	{
		// Jump to the last frame (so the final state is evaluated), then stop.
		const FFrameTime EndFrame = Player->GetStartTime().Time + FFrameTime(FFrameNumber(Player->GetFrameDuration()));
		Player->SetPlaybackPosition(FMovieSceneSequencePlaybackParams(EndFrame, EUpdatePositionMethod::Jump));
		Player->Stop();
	}
	if (const APlayerController* PC = GetPlayerController())
	{
		if (PC->PlayerCameraManager)
		{
			PC->PlayerCameraManager->StartCameraFade(1.f, 0.f, SkipFadeSeconds, FLinearColor::Black, false, false);
		}
	}
	FinishRun(TEXT("skipped"), /*bKeepFade*/ true, /*bSnapMark*/ true);

	// Sequencer's pre-animated restore (black, from bStartBlack) could land after the fade-up and leave the screen black: clear the fade
	// a moment after the fade-up should have ended, unless a new run started or the game is travelling.
	if (!bTravelling)
	{
		if (UWorld* World = GetWorld())
		{
			World->GetTimerManager().SetTimer(SkipFadeTimer, FTimerDelegate::CreateWeakLambda(this, [this]()
			{
				const ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(this);
				if (bRunActive || (Save && Save->IsTravelPending()))
				{
					return;
				}
				if (const APlayerController* PC = GetPlayerController())
				{
					if (PC->PlayerCameraManager)
					{
						PC->PlayerCameraManager->StopCameraFade();
					}
				}
			}), SkipFadeSeconds + 0.2f, false);
		}
	}
}

void ULBCinematicSubsystem::StopCinematic()
{
	FinishRun(TEXT("stopped"));
}

void ULBCinematicSubsystem::BeginSkipHold()
{
	if (bRunActive)
	{
		SkipHold.Begin();
	}
}

void ULBCinematicSubsystem::EndSkipHold()
{
	SkipHold.End();
}

void ULBCinematicSubsystem::BindPlayerInput()
{
	UnbindPlayerInput();
	if (ALBCharacter* Character = GetPlayerCharacter())
	{
		BoundPlayer = Character;
		PressedHandle = Character->OnLockedInteractPressed.AddUObject(this, &ULBCinematicSubsystem::BeginSkipHold);
		ReleasedHandle = Character->OnLockedInteractReleased.AddUObject(this, &ULBCinematicSubsystem::EndSkipHold);
	}
}

void ULBCinematicSubsystem::UnbindPlayerInput()
{
	if (ALBCharacter* Character = BoundPlayer.Get())
	{
		Character->OnLockedInteractPressed.Remove(PressedHandle);
		Character->OnLockedInteractReleased.Remove(ReleasedHandle);
	}
	PressedHandle.Reset();
	ReleasedHandle.Reset();
	BoundPlayer.Reset();
}

void ULBCinematicSubsystem::ApplyLock(ELBInputLock Lock)
{
	WantedLock = Lock;
	if (Look.bActive)
	{
		// The look assist holds Full on top; EndLook brings this lock back.
		return;
	}
	if (ALBCharacter* Character = GetPlayerCharacter())
	{
		Character->SetInputLock(Lock);
	}
	if (Lock == ELBInputLock::None)
	{
		SkipHold.End();
	}
}

void ULBCinematicSubsystem::FinishRun(const TCHAR* Reason, bool bKeepFade, bool bSnapMark)
{
	if (!bRunActive)
	{
		return;
	}
	const FName Id = RunDef.Id;
	const bool bGoingAway = bTravelling;

	UnbindPlayerInput();
	EndMark(bSnapMark);
	EndLook(/*bRestoreLock*/ false);
	bCardActive = false;
	bCreditsRolling = false;
	bEndPending = false;
	SkipHold.End();

	if (Player)
	{
		Player->OnFinished.RemoveDynamic(this, &ULBCinematicSubsystem::HandlePlayerFinished);
		if (!bGoingAway && (Player->IsPlaying() || Player->IsPaused()))
		{
			Player->Stop();
		}
	}

	if (!bGoingAway)
	{
		if (ALBCharacter* Character = GetPlayerCharacter())
		{
			Character->SetInputLock(ELBInputLock::None);
		}
		APlayerController* PC = GetPlayerController();
		if (ALBPlayerController* LBPC = Cast<ALBPlayerController>(PC))
		{
			LBPC->SetHUDHidden(false);
		}
		if (SequenceActor)
		{
			SequenceActor->Destroy();
		}
		if (Widget)
		{
			Widget->RemoveFromParent();
		}
		if (PC && PC->PlayerCameraManager && !bKeepFade)
		{
			PC->PlayerCameraManager->StopCameraFade();
		}
		PopMix();
	}
	// With a CompleteGame travel pending the sequence actor, the widget (end cards, black), the fade and the mix stay up over the
	// travel; Deinitialize takes the mix off at world teardown. Input and the HUD are left alone for the same reason.

	Player = nullptr;
	SequenceActor = nullptr;
	if (!bGoingAway)
	{
		Widget = nullptr;
	}
	LoadedSequence = nullptr;
	Markers.Reset();
	Fired.Reset();
	bRunActive = false;
	bFailSafe = false;
	bPlayerFinished = false;
	bPostHold = false;
	UE_LOG(LogLB, Log, TEXT("Cine: %s finished (%s)"), *Id.ToString(), Reason);
	OnCinematicFinished.Broadcast(Id);
}

// ---------------------------------------------------------------------------------------------------------------------
// Marker actions
// ---------------------------------------------------------------------------------------------------------------------

void ULBCinematicSubsystem::StartCard(FName CardId)
{
	const FLBCineCard* Found = Settings ? Settings->FindCard(CardId) : nullptr;
	if (!Found)
	{
		UE_LOG(LogLB, Warning, TEXT("Cine: card '%s' is not in the cinematic settings"), *CardId.ToString());
		return;
	}
	Card = *Found;
	Card.HoldSeconds = FMath::Clamp(Card.HoldSeconds, 0.f, 60.f);
	Card.FadeSeconds = FMath::Clamp(Card.FadeSeconds, 0.f, 10.f);
	CardElapsed = 0.f;
	bCardActive = true;
	if (Widget)
	{
		Widget->SetCard(Card.Text, Card.Style, LBCinematicLogic::CardOpacity(0.f, Card.FadeSeconds, Card.HoldSeconds));
	}
}

void ULBCinematicSubsystem::TickCard(float ScaledDelta)
{
	if (!bCardActive)
	{
		return;
	}
	CardElapsed += ScaledDelta;
	if (CardElapsed >= LBCinematicLogic::CardDuration(Card.FadeSeconds, Card.HoldSeconds))
	{
		bCardActive = false;
		if (Widget)
		{
			Widget->ClearCard();
		}
		return;
	}
	if (Widget)
	{
		Widget->SetCard(Card.Text, Card.Style, LBCinematicLogic::CardOpacity(CardElapsed, Card.FadeSeconds, Card.HoldSeconds));
	}
}

void ULBCinematicSubsystem::StartMark(const FLBCineMarker& Marker)
{
	ALBCharacter* Character = GetPlayerCharacter();
	const AActor* Target = FindActorWithTag(Marker.Name);
	if (!Character || !Target)
	{
		UE_LOG(LogLB, Warning, TEXT("Cine: marker '%s': %s"), *Marker.Label, !Character ? TEXT("there is no player pawn") : TEXT("no actor with that tag"));
		return;
	}
	const APlayerController* PC = GetPlayerController();
	const FRotator Control = PC ? PC->GetControlRotation().GetNormalized() : Character->GetActorRotation();
	const float HalfHeight = Character->GetCapsuleComponent() ? Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() : 88.f;

	Mark = FMarkMove();
	Mark.bActive = true;
	Mark.Start = Character->GetActorLocation();
	// XY to the actor; Z = actor Z + capsule half height; yaw to the actor's yaw; pitch to 0.
	Mark.End = FVector(Target->GetActorLocation().X, Target->GetActorLocation().Y, Target->GetActorLocation().Z + HalfHeight);
	Mark.StartYaw = Control.Yaw;
	Mark.EndYaw = Target->GetActorRotation().Yaw;
	Mark.StartPitch = Control.Pitch;
	const float Seconds = Marker.Value > 0.f ? Marker.Value : (Settings ? Settings->MarkSeconds : 1.5f);
	Mark.Duration = FMath::Max(Seconds, 0.05f);

	// No velocity means no footsteps: the capsule is carried, not walked.
	if (UCharacterMovementComponent* Movement = Character->GetCharacterMovement())
	{
		Movement->StopMovementImmediately();
		Movement->SetMovementMode(MOVE_None);
	}
}

void ULBCinematicSubsystem::TickMark(float ScaledDelta)
{
	if (!Mark.bActive)
	{
		return;
	}
	ALBCharacter* Character = GetPlayerCharacter();
	APlayerController* PC = GetPlayerController();
	if (!Character)
	{
		Mark.bActive = false;
		return;
	}
	Mark.Elapsed += ScaledDelta;
	const float Raw = FMath::Clamp(Mark.Elapsed / Mark.Duration, 0.f, 1.f);
	const float Alpha = LBCinematicLogic::Smoothstep(Raw);
	Character->SetActorLocation(FMath::Lerp(Mark.Start, Mark.End, static_cast<double>(Alpha)), false, nullptr, ETeleportType::TeleportPhysics);
	if (PC)
	{
		PC->SetControlRotation(FRotator(FMath::Lerp(Mark.StartPitch, 0.f, Alpha), LBCinematicLogic::ShortestYawLerp(Mark.StartYaw, Mark.EndYaw, Alpha), 0.f));
	}
	if (Raw >= 1.f)
	{
		// Movement mode stays None until the restore.
		Mark.bActive = false;
	}
}

void ULBCinematicSubsystem::EndMark(bool bSnapToEnd)
{
	ALBCharacter* Character = GetPlayerCharacter();
	if (Mark.bActive && bSnapToEnd && Character)
	{
		// A move cut short by a finish or a skip is completed, not left partway.
		Character->SetActorLocation(Mark.End, false, nullptr, ETeleportType::TeleportPhysics);
		if (APlayerController* PC = GetPlayerController())
		{
			PC->SetControlRotation(FRotator(0.f, Mark.EndYaw, 0.f));
		}
	}
	Mark.bActive = false;
	if (Character)
	{
		if (UCharacterMovementComponent* Movement = Character->GetCharacterMovement())
		{
			if (Movement->MovementMode == MOVE_None)
			{
				Movement->SetMovementMode(MOVE_Walking);
			}
		}
	}
}

void ULBCinematicSubsystem::StartLook(const FLBCineMarker& Marker)
{
	ALBCharacter* Character = GetPlayerCharacter();
	APlayerController* PC = GetPlayerController();
	AActor* Target = FindActorWithTag(Marker.Name);
	if (!Character || !PC || !Target)
	{
		UE_LOG(LogLB, Warning, TEXT("Cine: marker '%s': %s"), *Marker.Label, (!Character || !PC) ? TEXT("there is no player pawn") : TEXT("no actor with that tag"));
		return;
	}
	Look.bActive = true;
	Look.Target = Target;
	Look.Start = PC->GetControlRotation().GetNormalized();
	Look.Elapsed = 0.f;
	const float Seconds = Marker.Value > 0.f ? Marker.Value : (Settings ? Settings->LookAssistSeconds : 1.5f);
	Look.Duration = FMath::Max(Seconds, 0.05f);
	// Input is held at Full during the blend; WantedLock comes back after it.
	Character->SetInputLock(ELBInputLock::Full);
}

void ULBCinematicSubsystem::TickLook(float ScaledDelta)
{
	if (!Look.bActive)
	{
		return;
	}
	ALBCharacter* Character = GetPlayerCharacter();
	APlayerController* PC = GetPlayerController();
	const AActor* Target = Look.Target.Get();
	if (!Character || !PC || !Target)
	{
		EndLook(/*bRestoreLock*/ true);
		return;
	}
	Look.Elapsed += ScaledDelta;
	const float Raw = FMath::Clamp(Look.Elapsed / Look.Duration, 0.f, 1.f);
	const float Alpha = LBCinematicLogic::Smoothstep(Raw);

	// The target moves (the Warden walks), so the goal is recomputed every tick.
	const FRotator Goal = (LookTargetLocation(Target) - Character->GetPawnViewLocation()).Rotation().GetNormalized();
	const float Pitch = FMath::Lerp(Look.Start.Pitch, Goal.Pitch, Alpha);
	const float Yaw = LBCinematicLogic::ShortestYawLerp(Look.Start.Yaw, Goal.Yaw, Alpha);
	PC->SetControlRotation(FRotator(Pitch, Yaw, 0.f));
	if (Raw >= 1.f)
	{
		EndLook(/*bRestoreLock*/ true);
	}
}

void ULBCinematicSubsystem::EndLook(bool bRestoreLock)
{
	if (!Look.bActive)
	{
		return;
	}
	Look.bActive = false;
	Look.Target.Reset();
	if (bRestoreLock)
	{
		if (ALBCharacter* Character = GetPlayerCharacter())
		{
			Character->SetInputLock(WantedLock);
		}
	}
}

void ULBCinematicSubsystem::StartCredits(float Seconds)
{
	if (!Settings)
	{
		return;
	}
	CreditsDuration = FMath::Clamp(Seconds > 0.f ? Seconds : Settings->CreditsSeconds, 1.f, 600.f);
	CreditsElapsed = 0.f;
	bCreditsRolling = true;
	if (Widget)
	{
		Widget->BuildCredits(Settings->Credits);
		Widget->SetCreditsProgress(0.f, CreditsDuration);
	}
}

void ULBCinematicSubsystem::StopCredits()
{
	bCreditsRolling = false;
	if (Widget)
	{
		Widget->ClearCredits();
	}
}

void ULBCinematicSubsystem::TickCredits(float ScaledDelta)
{
	if (!bCreditsRolling)
	{
		return;
	}
	CreditsElapsed += ScaledDelta;
	if (CreditsElapsed >= CreditsDuration)
	{
		StopCredits();
		if (bEndPending)
		{
			DoEnd();
		}
		return;
	}
	if (Widget)
	{
		Widget->SetCreditsProgress(CreditsElapsed, CreditsDuration);
	}
}

void ULBCinematicSubsystem::PushMix()
{
	UWorld* World = GetWorld();
	if (!World || bPushedMix || !Settings)
	{
		return;
	}
	USoundMix* Mix = Settings->CineFadeMix.IsNull() ? nullptr : Settings->CineFadeMix.Get();
	if (!Mix && !Settings->CineFadeMix.IsNull() && FPackageName::DoesPackageExist(Settings->CineFadeMix.GetLongPackageName()))
	{
		Mix = Settings->CineFadeMix.LoadSynchronous();
	}
	if (!Mix)
	{
		UE_LOG(LogLB, Warning, TEXT("Cine: mix:on but the cinematic settings have no CineFadeMix that loads: the world sound is not faded"));
		return;
	}
	UGameplayStatics::PushSoundMixModifier(World, Mix);
	PushedMix = Mix;
	bPushedMix = true;
}

void ULBCinematicSubsystem::PopMix()
{
	if (!bPushedMix)
	{
		return;
	}
	if (UWorld* World = GetWorld())
	{
		if (PushedMix)
		{
			UGameplayStatics::PopSoundMixModifier(World, PushedMix);
		}
	}
	PushedMix = nullptr;
	bPushedMix = false;
}

// ---------------------------------------------------------------------------------------------------------------------
// The bell swing (section 2.8)
// ---------------------------------------------------------------------------------------------------------------------

void ULBCinematicSubsystem::HandleGreatBellStrike(int32 Stage, float Volume)
{
	if (!Settings || !BellComponent.IsValid())
	{
		return;
	}
	Pendulum.Kick(FMath::Clamp(Settings->BellSwingKickDegrees, 0.f, 45.f), FMath::Clamp(Settings->BellSwingMaxDegrees, 0.f, 45.f));
}

void ULBCinematicSubsystem::TickBell(float Delta)
{
	if (!Pendulum.IsSwinging() || !Settings)
	{
		return;
	}
	// Scaled by the play rate only while a cinematic plays, so a review at lb.Cine.Rate 8 sees the same order.
	const float Scaled = Delta * (bRunActive ? RunRate : 1.f);
	Pendulum.Advance(Scaled, FMath::Clamp(Settings->BellSwingPeriodSeconds, 0.5f, 20.f), FMath::Clamp(Settings->BellSwingDampingPerSecond, 0.f, 5.f), BellStopDegrees);
	// When the swing has just stopped the angle is exactly 0: every piece gets its rest transform back.
	ApplyBellAngle(Pendulum.AngleDeg());
}

void ULBCinematicSubsystem::ApplyBellAngle(float AngleDeg)
{
	USceneComponent* Bell = BellComponent.Get();
	if (!Bell)
	{
		return;
	}
	auto IsMovable = [this](const USceneComponent* Component, const TCHAR* What) -> bool
	{
		if (Component && Component->Mobility == EComponentMobility::Movable)
		{
			return true;
		}
		if (!bWarnedImmovable)
		{
			bWarnedImmovable = true;
			UE_LOG(LogLB, Warning, TEXT("Cine: the bell swing piece '%s' is not Movable, so it does not swing (P17-5b sets the headstock and the rope Movable)"), What);
		}
		return false;
	};

	if (IsMovable(Bell, *Bell->GetOwner()->GetName()))
	{
		const FTransform T = LBCinematicLogic::SwingAboutAxle(BellRestLocation, BellRestRotation, SwingPivot, SwingAxis, AngleDeg);
		Bell->SetWorldLocationAndRotation(T.GetLocation(), T.GetRotation(), false, nullptr, ETeleportType::TeleportPhysics);
	}
	if (AActor* Headstock = HeadstockActor.Get())
	{
		if (IsMovable(Headstock->GetRootComponent(), *Headstock->GetName()))
		{
			const FTransform T = LBCinematicLogic::SwingAboutAxle(HeadstockRestLocation, HeadstockRestRotation, SwingPivot, SwingAxis, AngleDeg);
			Headstock->SetActorLocationAndRotation(T.GetLocation(), T.GetRotation(), false, nullptr, ETeleportType::TeleportPhysics);
		}
	}
	if (AActor* Rope = RopeActor.Get())
	{
		if (IsMovable(Rope->GetRootComponent(), *Rope->GetName()))
		{
			// The hanging rope stays vertical and slides: only its Z follows the rim.
			Rope->SetActorLocation(LBCinematicLogic::RopeZAboutAxle(RopeRestLocation, SwingPivot, SwingAxis, AngleDeg), false, nullptr, ETeleportType::TeleportPhysics);
		}
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Debug
// ---------------------------------------------------------------------------------------------------------------------

#if !UE_BUILD_SHIPPING
void ULBCinematicSubsystem::DrawDebug()
{
	if (!GEngine)
	{
		return;
	}
	FString Text;
	if (bRunActive)
	{
		FString Next = TEXT("-");
		for (int32 Index = 0; Index < Markers.Num(); ++Index)
		{
			if (!Fired.IsValidIndex(Index) || !Fired[Index])
			{
				Next = FString::Printf(TEXT("%s @ %.2f"), *Markers[Index].Label, Markers[Index].Seconds);
				break;
			}
		}
		const ALBCharacter* Character = GetPlayerCharacter();
		const ELBInputLock Lock = Character ? Character->GetInputLock() : ELBInputLock::None;
		Text = FString::Printf(TEXT("Cine %s  t=%.2f/%.1f  next=%s  lock=%s  skippable=%d hold=%.2f  credits=%d"), *RunDef.Id.ToString(), CurSeconds, SequenceSeconds, *Next,
			Lock == ELBInputLock::Full ? TEXT("Full") : (Lock == ELBInputLock::Look ? TEXT("Look") : TEXT("None")), bSkippable ? 1 : 0, SkipHold.Held, bCreditsRolling ? 1 : 0);
	}
	else
	{
		Text = FString::Printf(TEXT("Cine idle  bell=%.2f deg"), Pendulum.AngleDeg());
	}
	GEngine->AddOnScreenDebugMessage(DebugKey, 0.f, FColor::Cyan, Text);
}
#endif // !UE_BUILD_SHIPPING
