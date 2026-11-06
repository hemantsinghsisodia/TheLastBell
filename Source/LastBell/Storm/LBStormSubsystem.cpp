#include "Storm/LBStormSubsystem.h"
#include "Storm/LBStormSettings.h"
#include "Storm/LBStormZone.h"
#include "AI/LBWarden.h"
#include "Systems/LBGameSettings.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/LightComponent.h"
#include "Components/LightComponentBase.h"
#include "Components/SkyLightComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "LBLog.h"

namespace
{
	const FName MoonTag(TEXT("LB_StormMoon"));
	const FName MoonSpotTag(TEXT("LB_StormMoonSpot"));
	const FName FillTag(TEXT("LB_StormFill"));
	const FName SkyTag(TEXT("LB_StormSky"));

#if !UE_BUILD_SHIPPING
	TAutoConsoleVariable<int32> CVarStormEnabled(
		TEXT("lb.Storm.Enabled"), 1,
		TEXT("1 = the storm runs (flashes, wind, story intensity). 0 = no flashes, wind 0, flash value 0. Non-shipping."),
		ECVF_Default);

	TAutoConsoleVariable<int32> CVarStormDebug(
		TEXT("lb.Storm.Debug"), 0,
		TEXT("1 = show the storm's intensity, target, time to the next flash, wind, player exposure and the last Warden reveal decision on screen. Non-shipping."),
		ECVF_Default);
#endif

	bool IsStormEnabled()
	{
#if !UE_BUILD_SHIPPING
		return CVarStormEnabled.GetValueOnGameThread() != 0;
#else
		return true;
#endif
	}

	// MPC parameter names (plan section 4). The asset MPC_LB_Storm is made in P14-2 with exactly these.
	const FName PStormIntensity(TEXT("StormIntensity"));
	const FName PLightningFlash(TEXT("LightningFlash"));
	const FName PWindStrength(TEXT("WindStrength"));
	const FName PWindPhase(TEXT("WindPhase"));
	const FName PPlayerExposure(TEXT("PlayerExposure"));
	const FName PDomeFlashGain(TEXT("DomeFlashGain"));
	const FName PDomeFlashAdd(TEXT("DomeFlashAdd"));
	const FName PGlassFlashGain(TEXT("GlassFlashGain"));
	const FName PShaftFlashGain(TEXT("ShaftFlashGain"));
	const FName PPoolFlashGain(TEXT("PoolFlashGain"));
	const FName PRevealGain(TEXT("RevealGain"));
	const FName PRevealEmissive(TEXT("RevealEmissive"));
	const FName PWindDirection(TEXT("WindDirection"));
	const FName PFlashDirection(TEXT("FlashDirection"));
	const FName PFlashTint(TEXT("FlashTint"));

	/** Fixed keys of the on-screen debug lines (AddOnScreenDebugMessage replaces a line with the same key). */
	constexpr uint64 DebugKeyBase = 0x4C42530000ull;
}

// ---------------------------------------------------------------------------------------------------------------------
// Plumbing
// ---------------------------------------------------------------------------------------------------------------------

bool ULBStormSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

TStatId ULBStormSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(ULBStormSubsystem, STATGROUP_Tickables);
}

void ULBStormSubsystem::Initialize(FSubsystemCollectionBase& InCollection)
{
	Super::Initialize(InCollection);
}

void ULBStormSubsystem::Deinitialize()
{
	UnbindWorldState();
	Pending.Reset();
	Active.Reset();
	LookWaits.Reset();
	Linked.Reset();
	Zones.Reset();
	bActive = false;
	Super::Deinitialize();
}

void ULBStormSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	RefreshLinkedLights();
}

void ULBStormSubsystem::OverrideSettings(ULBStormSettings* InSettings)
{
	Settings = InSettings;
	if (bActive)
	{
		// Already running: start the schedule afresh with the new numbers.
		ResetRuntime();
	}
}

void ULBStormSubsystem::RegisterZone(ALBStormZone* Zone)
{
	if (Zone)
	{
		Zones.RemoveAllSwap([](const TWeakObjectPtr<ALBStormZone>& Entry) { return !Entry.IsValid(); });
		Zones.AddUnique(Zone);
	}
}

void ULBStormSubsystem::UnregisterZone(ALBStormZone* Zone)
{
	Zones.RemoveSingleSwap(TWeakObjectPtr<ALBStormZone>(Zone));
}

// ---------------------------------------------------------------------------------------------------------------------
// Activation and linked lights
// ---------------------------------------------------------------------------------------------------------------------

void ULBStormSubsystem::RefreshLinkedLights()
{
	// Put every light we touched back to its base value before forgetting it.
	RestoreLights();
	Linked.Reset();

	UWorld* World = GetWorld();
	if (!World)
	{
		Deactivate();
		return;
	}

	// One pass: the moon first matters (no moon, no storm), the other tags are collected on the way.
	ADirectionalLight* Moon = nullptr;
	int32 MoonCount = 0;
	struct FFound
	{
		AActor* Actor;
		ELinkKind Kind;
	};
	TArray<FFound> Others;
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		AActor* Actor = *It;
		if (Actor->ActorHasTag(MoonTag))
		{
			if (ADirectionalLight* Directional = Cast<ADirectionalLight>(Actor))
			{
				++MoonCount;
				if (!Moon)
				{
					Moon = Directional;
				}
			}
		}
		if (Actor->ActorHasTag(MoonSpotTag))
		{
			Others.Add({ Actor, ELinkKind::Spot });
		}
		if (Actor->ActorHasTag(FillTag))
		{
			Others.Add({ Actor, ELinkKind::Fill });
		}
		if (Actor->ActorHasTag(SkyTag))
		{
			Others.Add({ Actor, ELinkKind::Sky });
		}
	}

	if (!Moon)
	{
		UE_LOG(LogLB, Verbose, TEXT("Storm: no actor tagged %s in this level, staying inactive"), *MoonTag.ToString());
		Deactivate();
		return;
	}
	if (MoonCount > 1)
	{
		UE_LOG(LogLB, Warning, TEXT("Storm: %d directional lights are tagged %s; using %s"), MoonCount, *MoonTag.ToString(), *Moon->GetName());
	}

	// Only now the settings: a level without a moon never loads them.
	if (!Settings)
	{
		const ULBGameSettings* GameSettings = GetDefault<ULBGameSettings>();
		Settings = GameSettings ? GameSettings->StormSettings.LoadSynchronous() : nullptr;
	}
	if (!Settings)
	{
		if (!bWarnedNoSettings)
		{
			bWarnedNoSettings = true;
			UE_LOG(LogLB, Warning, TEXT("Storm: the level has a %s light but ULBGameSettings::StormSettings is not set or does not load; the storm stays inactive"), *MoonTag.ToString());
		}
		Deactivate();
		return;
	}

	auto AddLink = [this](AActor* Actor, ELinkKind Kind)
	{
		ULightComponentBase* Component = Actor ? Actor->FindComponentByClass<ULightComponentBase>() : nullptr;
		if (!Component)
		{
			UE_LOG(LogLB, Warning, TEXT("Storm: %s is tagged for the storm but has no light component"), *GetNameSafe(Actor));
			return;
		}
		FLinkedLight& Link = Linked.AddDefaulted_GetRef();
		Link.Component = Component;
		Link.Kind = Kind;
		Link.Base = Component->Intensity;
	};
	AddLink(Moon, ELinkKind::Moon);
	for (const FFound& Found : Others)
	{
		AddLink(Found.Actor, Found.Kind);
	}

	Collection = Settings->Collection.IsNull() ? nullptr : Settings->Collection.LoadSynchronous();

	const bool bWasActive = bActive;
	bActive = true;
	BindWorldState();
	if (!bWasActive)
	{
		ResetRuntime();
	}
	UE_LOG(LogLB, Log, TEXT("Storm: active with %d linked lights, %d zones, intensity %.2f"), Linked.Num(), Zones.Num(), Intensity);
}

void ULBStormSubsystem::Deactivate()
{
	UnbindWorldState();
	Pending.Reset();
	Active.Reset();
	LookWaits.Reset();
	bActive = false;
}

void ULBStormSubsystem::BindWorldState()
{
	if (bBoundWorldState)
	{
		return;
	}
	if (ULBWorldStateSubsystem* WorldState = ULBWorldStateSubsystem::Get(this))
	{
		WorldState->OnStateChanged.AddDynamic(this, &ULBStormSubsystem::HandleStateChanged);
		WorldState->OnStateReplaced.AddDynamic(this, &ULBStormSubsystem::HandleStateReplaced);
		bBoundWorldState = true;
	}
}

void ULBStormSubsystem::UnbindWorldState()
{
	if (!bBoundWorldState)
	{
		return;
	}
	if (ULBWorldStateSubsystem* WorldState = ULBWorldStateSubsystem::Get(this))
	{
		WorldState->OnStateChanged.RemoveDynamic(this, &ULBStormSubsystem::HandleStateChanged);
		WorldState->OnStateReplaced.RemoveDynamic(this, &ULBStormSubsystem::HandleStateReplaced);
	}
	bBoundWorldState = false;
}

void ULBStormSubsystem::ResetRuntime()
{
	Pending.Reset();
	Active.Reset();
	LookWaits.Reset();
	CurrentFlash = 0.f;
	LastAppliedFlash = 0.f;
	WindPhase = 0.f;
	BusyUntil = -1.0e9;
	bAmbientArmed = false;
	bFirstAmbient = true;
	NextRevealCheckAt = 0.0;
	LastRevealTime = -1.0e9;
	NextExposureAt = 0.0;
	LastRevealCheck = LBStormLogic::ERevealCheck::NoWarden;
	if (Settings)
	{
		Stream.Initialize(Settings->RandomSeed != 0 ? Settings->RandomSeed : static_cast<int32>(FPlatformTime::Cycles()));
		Collection = Settings->Collection.IsNull() ? nullptr : Settings->Collection.LoadSynchronous();
	}
	// BeginPlay snaps to the story's intensity.
	TargetIntensity = ComputeTargetIntensity();
	Intensity = TargetIntensity;
}

void ULBStormSubsystem::RestoreLights()
{
	for (const FLinkedLight& Link : Linked)
	{
		if (ULightComponentBase* Component = Link.Component.Get())
		{
			if (ULightComponent* Light = Cast<ULightComponent>(Component))
			{
				Light->SetIntensity(Link.Base);
			}
			else if (USkyLightComponent* Sky = Cast<USkyLightComponent>(Component))
			{
				Sky->SetIntensity(Link.Base);
			}
		}
	}
	LastAppliedFlash = 0.f;
}

void ULBStormSubsystem::ApplyLights(float Flash)
{
	if (Flash <= 0.f && LastAppliedFlash <= 0.f)
	{
		return;
	}
	// A flash is running (or just ended): write every linked light. A light that has disappeared is skipped.
	for (const FLinkedLight& Link : Linked)
	{
		ULightComponentBase* Component = Link.Component.Get();
		if (!Component)
		{
			continue;
		}
		float Value = Link.Base;
		switch (Link.Kind)
		{
		case ELinkKind::Moon:
			Value = Link.Base + Settings->FlashLux * Flash;
			break;
		case ELinkKind::Spot:
			Value = Link.Base * (1.f + Settings->SpotFlashGain * Flash);
			break;
		case ELinkKind::Fill:
			Value = Link.Base * (1.f + Settings->FillFlashGain * Flash);
			break;
		case ELinkKind::Sky:
			Value = Link.Base * (1.f + Settings->SkyFlashGain * Flash);
			break;
		}
		if (ULightComponent* Light = Cast<ULightComponent>(Component))
		{
			Light->SetIntensity(Value);
		}
		else if (USkyLightComponent* Sky = Cast<USkyLightComponent>(Component))
		{
			Sky->SetIntensity(Value);
		}
	}
	LastAppliedFlash = Flash;
}

// ---------------------------------------------------------------------------------------------------------------------
// World state
// ---------------------------------------------------------------------------------------------------------------------

float ULBStormSubsystem::ComputeTargetIntensity() const
{
	if (!Settings)
	{
		return 0.55f;
	}
	const float Override = ConsoleIntensityOverride >= 0.f ? ConsoleIntensityOverride : Settings->DebugIntensityOverride;
	if (Override >= 0.f)
	{
		return FMath::Clamp(Override, 0.f, 1.f);
	}
	const ULBWorldStateSubsystem* WorldState = ULBWorldStateSubsystem::Get(this);
	if (!WorldState)
	{
		return Settings->DefaultIntensity;
	}
	return FMath::Clamp(LBStormLogic::StoryIntensity(Settings->StoryIntensity, WorldState->GetStateRef(), Settings->DefaultIntensity), 0.f, 1.f);
}

void ULBStormSubsystem::HandleStateChanged(FGameplayTag Tag, bool bAdded)
{
	if (!bActive || !Settings)
	{
		return;
	}
	// The intensity itself follows the tags in Tick (at IntensityRatePerSecond); here only the scripted strikes.
	if (!bAdded || !IsStormEnabled())
	{
		return;
	}
	const UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	for (int32 Index = 0; Index < Settings->ScriptedStrikes.Num(); ++Index)
	{
		const FLBStormStrike& Strike = Settings->ScriptedStrikes[Index];
		if (!Strike.TriggerTag.IsValid() || Strike.TriggerTag != Tag)
		{
			continue;
		}
		if (Strike.bLookGate)
		{
			FLookWait& Wait = LookWaits.AddDefaulted_GetRef();
			Wait.StrikeIndex = Index;
			Wait.Expire = World->GetTimeSeconds() + Strike.LookTimeout;
		}
		else
		{
			FireStrike(Index, FVector::ZeroVector, false);
		}
	}
}

void ULBStormSubsystem::HandleStateReplaced()
{
	if (!bActive)
	{
		return;
	}
	// A load or a new game: snap to the story's intensity, and never replay the strikes the tags would have fired.
	LookWaits.Reset();
	TargetIntensity = ComputeTargetIntensity();
	Intensity = TargetIntensity;
}

// ---------------------------------------------------------------------------------------------------------------------
// Flashes
// ---------------------------------------------------------------------------------------------------------------------

double ULBStormSubsystem::ScheduledStart(double Now, float Delay) const
{
	const float BusyRelative = static_cast<float>(FMath::Max(BusyUntil - Now, -1.0e8));
	const float Relative = LBStormLogic::EarliestStart(FMath::Max(Delay, 0.f), BusyRelative, Settings ? Settings->MinGapSeconds : 0.f);
	return Now + Relative;
}

FVector ULBStormSubsystem::RandomFlashDirection()
{
	const float Azimuth = Stream.FRandRange(0.f, 360.f);
	const float Elevation = Stream.FRandRange(Settings->ElevationMin, FMath::Max(Settings->ElevationMin, Settings->ElevationMax));
	return LBStormLogic::DirectionFromAngles(Azimuth, Elevation);
}

void ULBStormSubsystem::QueueFlash(float Brightness, double Start, ELBFlashReason Reason, ELBFlashProfile Profile, const FVector& Direction)
{
	// The random draws are the same whatever the profile, so a seeded storm replays the same sequence.
	const float ProfileRoll = Stream.FRand();
	const float Gap1 = Stream.FRandRange(Settings->GapMin, FMath::Max(Settings->GapMin, Settings->GapMax));
	const float Gap2 = Stream.FRandRange(Settings->GapMin, FMath::Max(Settings->GapMin, Settings->GapMax));
	if (Profile == ELBFlashProfile::Auto)
	{
		Profile = LBStormLogic::PickProfile(ProfileRoll, Settings->WeightSheet, Settings->WeightDouble, Settings->WeightTriple);
	}

	FFlashInstance& Flash = Pending.AddDefaulted_GetRef();
	Flash.Shape = LBStormLogic::MakeFlash(Profile, Brightness, Gap1, Gap2, Settings->MakeEnvelope());
	Flash.Start = Start;
	Flash.Duration = LBStormLogic::FlashDuration(Flash.Shape);
	Flash.Brightness = Brightness;
	Flash.Reason = Reason;
	Flash.Direction = Direction.GetSafeNormal();
	if (Flash.Direction.IsNearlyZero())
	{
		Flash.Direction = LBStormLogic::DirectionFromAngles(0.f, 25.f);
	}
	BusyUntil = FMath::Max(BusyUntil, Start + Flash.Duration);
}

void ULBStormSubsystem::RequestFlash(float Brightness, float DelaySeconds, ELBFlashReason Reason, ELBFlashProfile Profile)
{
	if (!bActive || !Settings || !IsStormEnabled())
	{
		return;
	}
	RequestFlashDirected(Brightness, DelaySeconds, Reason, Profile, RandomFlashDirection());
}

void ULBStormSubsystem::RequestFlashDirected(float Brightness, float DelaySeconds, ELBFlashReason Reason, ELBFlashProfile Profile, const FVector& Direction)
{
	const UWorld* World = GetWorld();
	if (!bActive || !Settings || !World || !IsStormEnabled())
	{
		return;
	}
	const double Now = World->GetTimeSeconds();
	QueueFlash(Brightness, ScheduledStart(Now, DelaySeconds), Reason, Profile, Direction);
}

void ULBStormSubsystem::FireStrike(int32 StrikeIndex, const FVector& TowardDirection, bool bHasDirection)
{
	const UWorld* World = GetWorld();
	if (!World || !Settings || !Settings->ScriptedStrikes.IsValidIndex(StrikeIndex))
	{
		return;
	}
	const FLBStormStrike& Strike = Settings->ScriptedStrikes[StrikeIndex];
	const double Now = World->GetTimeSeconds();
	// The gap applies before the first strike; the strikes of one sequence then follow their own spacing, start to start.
	const double FirstStart = ScheduledStart(Now, Strike.Delay);
	const int32 Count = FMath::Max(Strike.Count, 1);
	for (int32 Index = 0; Index < Count; ++Index)
	{
		const ELBFlashProfile Profile = Strike.ProfileOverrides.IsValidIndex(Index) ? Strike.ProfileOverrides[Index] : Strike.Profile;
		const FVector Direction = bHasDirection ? TowardDirection : RandomFlashDirection();
		QueueFlash(Strike.Brightness, FirstStart + Index * static_cast<double>(Strike.Spacing), ELBFlashReason::Scripted, Profile, Direction);
	}
	UE_LOG(LogLB, Verbose, TEXT("Storm: scripted strike for %s: %d flash(es) from %.2f s"), *Strike.TriggerTag.ToString(), Count, FirstStart - Now);
}

bool ULBStormSubsystem::GetCamera(FVector& OutLocation, FRotator& OutRotation) const
{
	const UWorld* World = GetWorld();
	const APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	const APlayerCameraManager* Camera = PC ? PC->PlayerCameraManager.Get() : nullptr;
	if (!Camera)
	{
		return false;
	}
	OutLocation = Camera->GetCameraLocation();
	OutRotation = Camera->GetCameraRotation();
	return true;
}

void ULBStormSubsystem::UpdateLookWaits(double Now)
{
	if (LookWaits.IsEmpty())
	{
		return;
	}
	FVector CameraLocation;
	FRotator CameraRotation;
	const bool bHasCamera = GetCamera(CameraLocation, CameraRotation);
	for (int32 Index = LookWaits.Num() - 1; Index >= 0; --Index)
	{
		const FLookWait Wait = LookWaits[Index];
		if (!Settings->ScriptedStrikes.IsValidIndex(Wait.StrikeIndex) || Now > Wait.Expire)
		{
			// Never looked in time: nothing fires.
			LookWaits.RemoveAtSwap(Index);
			continue;
		}
		if (!bHasCamera)
		{
			continue;
		}
		const FLBStormStrike& Strike = Settings->ScriptedStrikes[Wait.StrikeIndex];
		const FVector ToTarget = (Strike.LookTarget - CameraLocation).GetSafeNormal();
		const float Cos = static_cast<float>(FVector::DotProduct(CameraRotation.Vector(), ToTarget));
		const float Angle = FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(Cos, -1.f, 1.f)));
		if (Angle <= Strike.LookConeDegrees)
		{
			const int32 StrikeIndex = Wait.StrikeIndex;
			LookWaits.RemoveAtSwap(Index);
			FireStrike(StrikeIndex, ToTarget, true);
		}
	}
}

void ULBStormSubsystem::StartDueFlashes(double Now)
{
	TArray<FFlashInstance, TInlineAllocator<4>> Started;
	for (int32 Index = 0; Index < Pending.Num();)
	{
		if (Pending[Index].Start <= Now)
		{
			Started.Add(Pending[Index]);
			Pending.RemoveAt(Index);
		}
		else
		{
			++Index;
		}
	}
	for (const FFlashInstance& Flash : Started)
	{
		Active.Add(Flash);
		FlashDirection = Flash.Direction;
		OnLightningFlash.Broadcast(Flash.Brightness, Flash.Reason);
	}
}

void ULBStormSubsystem::UpdateAmbient(double Now, bool bFrozen)
{
	if (!Settings->bAmbientFlashes || bFrozen)
	{
		bAmbientArmed = false;
		return;
	}
	// A scripted sequence, a reveal or any other flash running or pending holds the ambient timer; it restarts afterwards.
	if (IsFlashBusy())
	{
		bAmbientArmed = false;
		return;
	}
	if (!bAmbientArmed)
	{
		NextAmbientAt = Now + LBStormLogic::NextInterval(Intensity, Stream.FRand(), Settings->MakeScheduleParams(), bFirstAmbient);
		bFirstAmbient = false;
		bAmbientArmed = true;
		return;
	}
	if (Now >= NextAmbientAt)
	{
		bAmbientArmed = false;
		const float Brightness = LBStormLogic::AmbientBrightness(Stream.FRand(), Intensity, Settings->BrightnessMin, Settings->BrightnessFloorLow);
		QueueFlash(Brightness, ScheduledStart(Now, 0.f), ELBFlashReason::Ambient, ELBFlashProfile::Auto, RandomFlashDirection());
	}
}

void ULBStormSubsystem::CheckReveal(double Now)
{
	if (Now < NextRevealCheckAt)
	{
		return;
	}
	NextRevealCheckAt = Now + 1.0 / FMath::Max(Settings->RevealCheckHz, 0.1f);

	const UWorld* World = GetWorld();
	FVector CameraLocation;
	FRotator CameraRotation;
	if (!World || !GetCamera(CameraLocation, CameraRotation))
	{
		return;
	}

	if (!CachedWarden.IsValid())
	{
		CachedWarden = nullptr;
		for (TActorIterator<ALBWarden> It(World); It; ++It)
		{
			CachedWarden = *It;
			break;
		}
	}
	const ALBWarden* Warden = CachedWarden.Get();

	LBStormLogic::FRevealInputs In;
	In.bEnabled = Settings->bRevealEnabled;
	In.Intensity = Intensity;
	In.MinIntensity = Settings->RevealMinIntensity;
	In.bWardenExists = Warden != nullptr;
	In.bWardenDormant = Warden && Warden->IsDormantPresentation();
	In.MinDistance = Settings->RevealMinDistance;
	In.MaxDistance = Settings->RevealMaxDistance;
	In.ConeDegrees = Settings->RevealConeDegrees;
	In.MinExposure = Settings->RevealMinExposure;
	In.CooldownSeconds = Settings->RevealCooldownSeconds;
	In.SecondsSinceLastReveal = static_cast<float>(FMath::Min(Now - LastRevealTime, 1.0e9));
	In.bFlashBusy = IsFlashBusy();

	FVector WardenLocation = FVector::ZeroVector;
	FVector Head = FVector::ZeroVector;
	if (Warden)
	{
		WardenLocation = Warden->GetActorLocation();
		Head = WardenLocation + FVector(0.0, 0.0, Settings->WardenHeadOffsetZ);
		const FVector ToHead = Head - CameraLocation;
		In.Distance = static_cast<float>(ToHead.Size());
		const float Cos = In.Distance > UE_SMALL_NUMBER ? static_cast<float>(FVector::DotProduct(CameraRotation.Vector(), ToHead / In.Distance)) : 1.f;
		In.AngleDegrees = FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(Cos, -1.f, 1.f)));
		In.Exposure = GetExposureAt(WardenLocation);
	}
	In.bLineClear = true;

	LBStormLogic::ERevealCheck Check = LBStormLogic::ERevealCheck::Reveal;
	bool bReveal = LBStormLogic::ShouldReveal(In, Check);
	if (bReveal)
	{
		// The cheap conditions all hold: only now the trace.
		FCollisionQueryParams Params(SCENE_QUERY_STAT(LBStormReveal), false);
		if (const APlayerController* PC = World->GetFirstPlayerController())
		{
			Params.AddIgnoredActor(PC->GetPawn());
		}
		Params.AddIgnoredActor(Warden);
		In.bLineClear = !World->LineTraceTestByChannel(CameraLocation, Head, ECC_Visibility, Params);
		bReveal = LBStormLogic::ShouldReveal(In, Check);
	}
	LastRevealCheck = Check;

	if (bReveal)
	{
		LastRevealTime = Now;
		const float Delay = Stream.FRandRange(Settings->RevealDelayMin, FMath::Max(Settings->RevealDelayMin, Settings->RevealDelayMax));
		const FVector Direction = LBStormLogic::RevealDirection(WardenLocation - CameraLocation, Settings->RevealRaiseDegrees);
		QueueFlash(Settings->RevealBrightness, ScheduledStart(Now, Delay), ELBFlashReason::WardenReveal, ELBFlashProfile::Double, Direction);
		UE_LOG(LogLB, Verbose, TEXT("Storm: Warden reveal, flash in %.2f s (%.0f cm away)"), Delay, In.Distance);
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Tick
// ---------------------------------------------------------------------------------------------------------------------

void ULBStormSubsystem::UpdateIntensity(float DeltaSeconds)
{
	TargetIntensity = ComputeTargetIntensity();
	const bool bOverride = ConsoleIntensityOverride >= 0.f || Settings->DebugIntensityOverride >= 0.f;
	if (bOverride)
	{
		Intensity = TargetIntensity;
	}
	else
	{
		Intensity = LBStormLogic::MoveTowards(Intensity, TargetIntensity, Settings->IntensityRatePerSecond, DeltaSeconds);
	}
}

void ULBStormSubsystem::UpdateWind(float DeltaSeconds, double Now)
{
	if (!IsStormEnabled())
	{
		CurrentWind = 0.f;
		return;
	}
	const LBStormLogic::FWindParams Params = Settings->MakeWindParams();
	CurrentWind = LBStormLogic::WindStrength(Intensity, static_cast<float>(Now), Params);
	WindPhase = LBStormLogic::AdvanceWindPhase(WindPhase, CurrentWind, DeltaSeconds, Params);
}

float ULBStormSubsystem::GetExposureAt(const FVector& WorldLocation) const
{
	TArray<LBStormLogic::FExposureEntry, TInlineAllocator<8>> Containing;
	for (const TWeakObjectPtr<ALBStormZone>& Zone : Zones)
	{
		if (const ALBStormZone* Live = Zone.Get())
		{
			if (Live->ContainsPoint(WorldLocation))
			{
				Containing.Add({ Live->Exposure, Live->Priority });
			}
		}
	}
	return LBStormLogic::ResolveExposure(Containing, Settings ? Settings->DefaultExposure : 1.f);
}

void ULBStormSubsystem::UpdateExposure(double Now)
{
	if (Now < NextExposureAt)
	{
		return;
	}
	NextExposureAt = Now + Settings->ExposureSampleSeconds;
	FVector CameraLocation;
	FRotator CameraRotation;
	if (GetCamera(CameraLocation, CameraRotation))
	{
		PlayerExposure = GetExposureAt(CameraLocation);
	}
}

float ULBStormSubsystem::GetSecondsToNextAmbient() const
{
	const UWorld* World = GetWorld();
	if (!bAmbientArmed || !World)
	{
		return -1.f;
	}
	return static_cast<float>(FMath::Max(NextAmbientAt - World->GetTimeSeconds(), 0.0));
}

void ULBStormSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	UWorld* World = GetWorld();
	if (!bActive || !Settings || !World)
	{
		return;
	}
	const double Now = World->GetTimeSeconds();
	const bool bEnabled = IsStormEnabled();

	UpdateIntensity(DeltaTime);
	UpdateWind(DeltaTime, Now);

	float Flash = 0.f;
	if (!bEnabled)
	{
		Pending.Reset();
		Active.Reset();
		LookWaits.Reset();
		bAmbientArmed = false;
	}
	else
	{
		const float Freeze = ConsoleFreeze >= 0.f ? ConsoleFreeze : Settings->DebugFreezeFlash;
		const bool bFrozen = Freeze >= 0.f;

		UpdateLookWaits(Now);
		StartDueFlashes(Now);
		for (int32 Index = Active.Num() - 1; Index >= 0; --Index)
		{
			if (Now - Active[Index].Start > Active[Index].Duration)
			{
				Active.RemoveAtSwap(Index);
			}
		}
		for (const FFlashInstance& Instance : Active)
		{
			Flash = FMath::Max(Flash, LBStormLogic::EvaluateFlash(Instance.Shape, static_cast<float>(Now - Instance.Start)));
		}
		if (bFrozen)
		{
			// A flash held for a capture: the schedule and the reveal rule are paused.
			Flash = FMath::Clamp(Freeze, 0.f, 1.f);
			UpdateAmbient(Now, true);
		}
		else
		{
			UpdateAmbient(Now, false);
			CheckReveal(Now);
		}
	}
	CurrentFlash = Flash;

	UpdateExposure(Now);
	ApplyLights(Flash);
	WriteCollection();
	DrawDebug(Now);
}

void ULBStormSubsystem::WriteCollection()
{
	UWorld* World = GetWorld();
	if (!Collection || !World)
	{
		return;
	}
	UMaterialParameterCollectionInstance* Instance = World->GetParameterCollectionInstance(Collection);
	if (!Instance)
	{
		return;
	}

	bool bAllWritten = true;
	auto Scalar = [&](const FName& Name, float Value) { bAllWritten &= Instance->SetScalarParameterValue(Name, Value); };
	auto Vector = [&](const FName& Name, const FLinearColor& Value) { bAllWritten &= Instance->SetVectorParameterValue(Name, Value); };

	Scalar(PStormIntensity, Intensity);
	Scalar(PLightningFlash, CurrentFlash);
	Scalar(PWindStrength, CurrentWind);
	Scalar(PWindPhase, WindPhase);
	Scalar(PPlayerExposure, PlayerExposure);
	// Copied every frame so a live edit of the data asset shows at once.
	Scalar(PDomeFlashGain, Settings->DomeFlashGain);
	Scalar(PDomeFlashAdd, Settings->DomeFlashAdd);
	Scalar(PGlassFlashGain, Settings->GlassFlashGain);
	Scalar(PShaftFlashGain, Settings->ShaftFlashGain);
	Scalar(PPoolFlashGain, Settings->PoolFlashGain);
	Scalar(PRevealGain, Settings->RevealGain);
	Scalar(PRevealEmissive, Settings->RevealEmissive);

	const FVector Wind = Settings->WindDirection.GetSafeNormal();
	Vector(PWindDirection, FLinearColor(static_cast<float>(Wind.X), static_cast<float>(Wind.Y), static_cast<float>(Wind.Z), 0.f));
	Vector(PFlashDirection, FLinearColor(static_cast<float>(FlashDirection.X), static_cast<float>(FlashDirection.Y), static_cast<float>(FlashDirection.Z), 0.f));
	Vector(PFlashTint, Settings->FlashTint);

	if (!bAllWritten && WriteFailures++ == 0)
	{
		UE_LOG(LogLB, Warning, TEXT("Storm: %s lacks one or more storm parameters (StormIntensity, LightningFlash, WindStrength, WindPhase, PlayerExposure, the gains, WindDirection, FlashDirection, FlashTint)"),
			*GetNameSafe(Collection));
	}
}

void ULBStormSubsystem::DrawDebug(double Now)
{
#if !UE_BUILD_SHIPPING
	if (CVarStormDebug.GetValueOnGameThread() == 0 || !GEngine)
	{
		return;
	}
	const float Next = GetSecondsToNextAmbient();
	const FString NextText = Next >= 0.f ? FString::Printf(TEXT("%.1f s"), Next) : FString(TEXT("held"));
	GEngine->AddOnScreenDebugMessage(DebugKeyBase + 1, 0.f, FColor::Cyan,
		FString::Printf(TEXT("Storm intensity %.2f (target %.2f)   flash %.2f   next ambient flash %s"), Intensity, TargetIntensity, CurrentFlash, *NextText));
	GEngine->AddOnScreenDebugMessage(DebugKeyBase + 2, 0.f, FColor::Cyan,
		FString::Printf(TEXT("Storm wind %.2f   player exposure %.2f   pending %d, running %d"), CurrentWind, PlayerExposure, Pending.Num(), Active.Num()));
	GEngine->AddOnScreenDebugMessage(DebugKeyBase + 3, 0.f, FColor::Cyan,
		FString::Printf(TEXT("Storm reveal: %s (last reveal %.0f s ago)"), LBStormLogic::RevealCheckName(LastRevealCheck), FMath::Min(Now - LastRevealTime, 9999.0)));
#endif
}
