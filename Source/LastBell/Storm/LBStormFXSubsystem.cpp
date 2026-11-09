#include "Storm/LBStormFXSubsystem.h"
#include "Storm/LBLightningBolt.h"
#include "Storm/LBStormFXLogic.h"
#include "Storm/LBStormFXSettings.h"
#include "Storm/LBStormLogic.h"
#include "Storm/LBStormSettings.h"
#include "Storm/LBStormSubsystem.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInterface.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "LBLog.h"

namespace
{
#if !UE_BUILD_SHIPPING
	TAutoConsoleVariable<int32> CVarStormFXEnabled(
		TEXT("lb.StormFX.Enabled"), 1,
		TEXT("1 = the storm's particle FX run (rain, bolts, sparks). 0 = the rain is removed and no bolt is drawn. Non-shipping."),
		ECVF_Default);
#endif

	bool IsFXEnabled()
	{
#if !UE_BUILD_SHIPPING
		return CVarStormFXEnabled.GetValueOnGameThread() != 0;
#else
		return true;
#endif
	}

	// User parameters of NS_LB_Rain (plan P15 section 6.1).
	const FName PRainRate(TEXT("User.RainRate"));
	const FName PBoxHalf(TEXT("User.BoxHalf"));
	const FName PSpawnHeight(TEXT("User.SpawnHeight"));
	const FName PFallMin(TEXT("User.FallMin"));
	const FName PFallMax(TEXT("User.FallMax"));
	const FName PWind(TEXT("User.Wind"));
	const FName PSplashRate(TEXT("User.SplashRate"));
	const FName PSplashRadius(TEXT("User.SplashRadius"));
	const FName PMist(TEXT("User.Mist"));

	/** The actor the debug tower strike (DebugBolt 1, lb.StormFX.Bolt 1) hits. */
	const FName DebugTargetTag(TEXT("LB_StrikeTarget_Tower"));

	/**
	 * The rain component, made as UNiagaraFunctionLibrary::SpawnSystemAtLocation makes a non-pooled one (CreateNiagaraSystem and
	 * SpawnSystemAtLocationWithParams) but without its FApp::CanEverRender() guard. That guard returns null under -nullrhi, where the
	 * rain component must still exist (the automation suite checks it); the strike sparks stay on SpawnSystemAtLocation (fire and forget).
	 */
	UNiagaraComponent* CreateRainComponent(UWorld* World, UNiagaraSystem* System, const FVector& Location)
	{
		if (!World || !System || World->IsNetMode(NM_DedicatedServer))
		{
			return nullptr;
		}
		UNiagaraComponent* Component = NewObject<UNiagaraComponent>(World->GetWorldSettings(), NAME_None, RF_Transient);
		Component->SetAsset(System);
		Component->bAutoActivate = false;
		Component->SetAutoDestroy(false);
		Component->bAllowAnyoneToDestroyMe = true;
		Component->SetVisibleInRayTracing(false);
#if WITH_EDITORONLY_DATA
		Component->bWaitForCompilationOnActivate = GIsAutomationTesting;
#endif
		Component->RegisterComponentWithWorld(World);
		Component->SetAbsolute(true, true, true);
		Component->SetWorldLocationAndRotation(Location, FRotator::ZeroRotator);
		Component->SetRelativeScale3D(FVector::OneVector);
		Component->Activate(true);
		return Component;
	}

	/** How fast the mist amount eases toward its goal, per second. */
	constexpr float MistEaseRate = 1.f;
	constexpr int32 MaxBoltPool = 16;
}

// ---------------------------------------------------------------------------------------------------------------------
// Plumbing
// ---------------------------------------------------------------------------------------------------------------------

bool ULBStormFXSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

TStatId ULBStormFXSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(ULBStormFXSubsystem, STATGROUP_Tickables);
}

void ULBStormFXSubsystem::Initialize(FSubsystemCollectionBase& InCollection)
{
	// The storm is created first, so its settings and state are there when this one reads them.
	InCollection.InitializeDependency<ULBStormSubsystem>();
	Super::Initialize(InCollection);
}

void ULBStormFXSubsystem::Deinitialize()
{
	if (ULBStormSubsystem* Storm = BoundStorm.Get())
	{
		Storm->OnLightningStrike.RemoveDynamic(this, &ULBStormFXSubsystem::HandleLightningStrike);
	}
	BoundStorm.Reset();
	RainComponent = nullptr;
	Bolts.Reset();
	DebugBoltActor = nullptr;
	bActive = false;
	Super::Deinitialize();
}

void ULBStormFXSubsystem::OverrideSettings(ULBStormFXSettings* InSettings)
{
	SettingsOverride = InSettings;
}

void ULBStormFXSubsystem::Rearm()
{
	bGaveUp = false;
	bWarnedNoSettings = false;
}

UNiagaraComponent* ULBStormFXSubsystem::GetRainComponent() const
{
	return RainComponent;
}

int32 ULBStormFXSubsystem::GetShownBoltCount() const
{
	int32 Count = 0;
	for (const TObjectPtr<ALBLightningBolt>& Bolt : Bolts)
	{
		Count += (Bolt && Bolt->IsBoltShown()) ? 1 : 0;
	}
	return Count;
}

bool ULBStormFXSubsystem::GetViewLocation(FVector& OutLocation) const
{
	const UWorld* World = GetWorld();
	if (!World)
	{
		return false;
	}
	const APlayerController* PC = World->GetFirstPlayerController();
	const APlayerCameraManager* Camera = PC ? PC->PlayerCameraManager.Get() : nullptr;
	// The player camera, unless the controller has no pawn while a view was rendered: PIE Simulate keeps PlayerController_0 parked at
	// the start with a camera that never updates, so the rain follows the view that was rendered last frame there (P15-9).
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

bool ULBStormFXSubsystem::GetViewDirection(FVector& OutDirection) const
{
	const UWorld* World = GetWorld();
	const APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	if (const APlayerCameraManager* Camera = PC ? PC->PlayerCameraManager.Get() : nullptr)
	{
		OutDirection = Camera->GetCameraRotation().Vector();
		return true;
	}
	return false;
}

// ---------------------------------------------------------------------------------------------------------------------
// Activation
// ---------------------------------------------------------------------------------------------------------------------

bool ULBStormFXSubsystem::TryActivate(ULBStormSubsystem& Storm)
{
	UWorld* World = GetWorld();
	const ULBStormSettings* StormSettings = Storm.GetSettings();
	if (!World || !StormSettings)
	{
		return false;
	}

	Settings = SettingsOverride ? SettingsOverride.Get() : StormSettings->FXSettings.LoadSynchronous();
	if (!Settings)
	{
		if (!bWarnedNoSettings)
		{
			bWarnedNoSettings = true;
			if (StormSettings->FXSettings.IsNull())
			{
				// Not linked (yet): a level or a build without the P15 data runs as before.
				UE_LOG(LogLB, Log, TEXT("StormFX: ULBStormSettings::FXSettings is not set; no rain or bolts"));
			}
			else
			{
				UE_LOG(LogLB, Warning, TEXT("StormFX: ULBStormSettings::FXSettings (%s) does not load; no rain or bolts"), *StormSettings->FXSettings.ToString());
			}
		}
		// Nothing will change this until the level is reloaded or a test calls Rearm.
		bGaveUp = true;
		return false;
	}

	BoltMesh = Settings->BoltMesh.IsNull() ? nullptr : Settings->BoltMesh.LoadSynchronous();
	BoltMaterial = Settings->BoltMaterial.IsNull() ? nullptr : Settings->BoltMaterial.LoadSynchronous();
	SparksSystem = Settings->StrikeSparksSystem.IsNull() ? nullptr : Settings->StrikeSparksSystem.LoadSynchronous();
	Stream.Initialize(StormSettings->RandomSeed != 0 ? StormSettings->RandomSeed : static_cast<int32>(FPlatformTime::Cycles()));

	// Rain: one component that rides on the camera.
	bRainParamsValid = false;
	Mist = LBStormFXLogic::MistAmount(Storm.GetPlayerExposure(), Settings->MistMinExposure);
	if (UNiagaraSystem* RainSystem = Settings->RainSystem.IsNull() ? nullptr : Settings->RainSystem.LoadSynchronous())
	{
		FVector Camera = FVector::ZeroVector;
		GetViewLocation(Camera);
		RainComponent = CreateRainComponent(World, RainSystem, Camera);
	}
	if (!RainComponent && !bWarnedNoRain)
	{
		bWarnedNoRain = true;
		UE_LOG(LogLB, Warning, TEXT("StormFX: RainSystem is not set or does not load; there is no rain (the bolts still work)"));
	}

	SpawnBoltPool();
	for (const TObjectPtr<ALBLightningBolt>& Bolt : Bolts)
	{
		if (Bolt)
		{
			Bolt->SetAssets(BoltMesh, BoltMaterial);
		}
	}

	Storm.OnLightningStrike.AddDynamic(this, &ULBStormFXSubsystem::HandleLightningStrike);
	BoundStorm = &Storm;
	bActive = true;
	bEverActive = true;
	UE_LOG(LogLB, Log, TEXT("StormFX: active (rain %s, %d bolts)"), RainComponent ? TEXT("on") : TEXT("missing"), Bolts.Num());
	return true;
}

void ULBStormFXSubsystem::Deactivate()
{
	if (ULBStormSubsystem* Storm = BoundStorm.Get())
	{
		Storm->OnLightningStrike.RemoveDynamic(this, &ULBStormFXSubsystem::HandleLightningStrike);
	}
	BoundStorm.Reset();
	if (RainComponent)
	{
		RainComponent->DestroyComponent();
		RainComponent = nullptr;
	}
	bRainParamsValid = false;
	HideAllBolts();
	bActive = false;
	UE_LOG(LogLB, Log, TEXT("StormFX: inactive"));
}

ALBLightningBolt* ULBStormFXSubsystem::SpawnBolt()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return nullptr;
	}
	FActorSpawnParameters Params;
	Params.ObjectFlags |= RF_Transient;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	ALBLightningBolt* Bolt = World->SpawnActor<ALBLightningBolt>(ALBLightningBolt::StaticClass(), FTransform::Identity, Params);
	if (Bolt)
	{
		Bolt->SetAssets(BoltMesh, BoltMaterial);
		Bolt->HideBolt();
	}
	return Bolt;
}

void ULBStormFXSubsystem::SpawnBoltPool()
{
	const int32 Wanted = FMath::Clamp(Settings ? Settings->BoltPool : 4, 1, MaxBoltPool);
	while (Bolts.Num() < Wanted)
	{
		ALBLightningBolt* Bolt = SpawnBolt();
		if (!Bolt)
		{
			break;
		}
		Bolts.Add(Bolt);
	}
}

void ULBStormFXSubsystem::HideAllBolts()
{
	for (const TObjectPtr<ALBLightningBolt>& Bolt : Bolts)
	{
		if (Bolt)
		{
			Bolt->HideBolt();
		}
	}
	if (DebugBoltActor)
	{
		DebugBoltActor->HideBolt();
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Tick
// ---------------------------------------------------------------------------------------------------------------------

void ULBStormFXSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	ULBStormSubsystem* Storm = World->GetSubsystem<ULBStormSubsystem>();
	const bool bStormActive = Storm && Storm->IsActive();
	const bool bEnabled = IsFXEnabled();

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

	UpdateRain(*Storm, DeltaTime);
	UpdateBolts(*Storm, World->GetTimeSeconds());
	UpdateDebugBolt(World->GetTimeSeconds());
}

void ULBStormFXSubsystem::UpdateRain(const ULBStormSubsystem& Storm, float DeltaSeconds)
{
	if (!RainComponent || !Settings)
	{
		return;
	}

	FVector Camera;
	if (GetViewLocation(Camera) && !RainComponent->GetComponentLocation().Equals(Camera, 0.01))
	{
		RainComponent->SetWorldLocation(Camera);
	}

	Mist = LBStormLogic::MoveTowards(Mist, LBStormFXLogic::MistAmount(Storm.GetPlayerExposure(), Settings->MistMinExposure), MistEaseRate, DeltaSeconds);

	const ULBStormSettings* StormSettings = Storm.GetSettings();
	FRainParams Now;
	Now.Rate = Settings->bRain ? Settings->RainSpawnRate : 0.f;
	Now.BoxHalf = Settings->RainBoxHalfXY;
	Now.SpawnHeight = Settings->RainSpawnHeight;
	Now.FallMin = static_cast<float>(Settings->RainFallSpeed.X);
	Now.FallMax = static_cast<float>(Settings->RainFallSpeed.Y);
	Now.Wind = LBStormFXLogic::RainWind(StormSettings ? StormSettings->WindDirection : FVector::ZeroVector, Storm.GetWindStrength(), Settings->RainWindLean);
	Now.SplashRate = Settings->bRain ? Settings->SplashRate : 0.f;
	Now.SplashRadius = Settings->SplashRadius;
	Now.Mist = Mist;

	const FRainParams& Old = RainParams;
	const bool bAll = !bRainParamsValid;
	// Only what changed is written (the wind and the mist move; the rest changes on an edit of the data asset).
	if (bAll || Now.Rate != Old.Rate) { RainComponent->SetVariableFloat(PRainRate, Now.Rate); }
	if (bAll || Now.BoxHalf != Old.BoxHalf) { RainComponent->SetVariableFloat(PBoxHalf, Now.BoxHalf); }
	if (bAll || Now.SpawnHeight != Old.SpawnHeight) { RainComponent->SetVariableFloat(PSpawnHeight, Now.SpawnHeight); }
	if (bAll || Now.FallMin != Old.FallMin) { RainComponent->SetVariableFloat(PFallMin, Now.FallMin); }
	if (bAll || Now.FallMax != Old.FallMax) { RainComponent->SetVariableFloat(PFallMax, Now.FallMax); }
	if (bAll || !Now.Wind.Equals(Old.Wind, 0.01)) { RainComponent->SetVariableVec3(PWind, Now.Wind); }
	if (bAll || Now.SplashRate != Old.SplashRate) { RainComponent->SetVariableFloat(PSplashRate, Now.SplashRate); }
	if (bAll || Now.SplashRadius != Old.SplashRadius) { RainComponent->SetVariableFloat(PSplashRadius, Now.SplashRadius); }
	if (bAll || !FMath::IsNearlyEqual(Now.Mist, Old.Mist, 1.0e-3f)) { RainComponent->SetVariableFloat(PMist, Now.Mist); }
	RainParams = Now;
	bRainParamsValid = true;
}

void ULBStormFXSubsystem::UpdateBolts(const ULBStormSubsystem& Storm, double Now)
{
	if (!Settings)
	{
		return;
	}
	// A bolt goes when its flash has ended (no flash running and the flash value down), or after BoltMaxSeconds.
	const bool bFlashOver = !Storm.IsFlashRunning() && Storm.GetLightningFlash() < 0.01f;
	for (const TObjectPtr<ALBLightningBolt>& Bolt : Bolts)
	{
		if (Bolt && Bolt->IsBoltShown() && (bFlashOver || Now - Bolt->GetShownAt() > Settings->BoltMaxSeconds))
		{
			Bolt->HideBolt();
		}
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Bolts
// ---------------------------------------------------------------------------------------------------------------------

ALBLightningBolt* ULBStormFXSubsystem::AcquireBolt() const
{
	ALBLightningBolt* Oldest = nullptr;
	for (const TObjectPtr<ALBLightningBolt>& Entry : Bolts)
	{
		ALBLightningBolt* Bolt = Entry;
		if (!Bolt)
		{
			continue;
		}
		if (!Bolt->IsBoltShown())
		{
			return Bolt;
		}
		if (!Oldest || Bolt->GetShownAt() < Oldest->GetShownAt())
		{
			Oldest = Bolt;
		}
	}
	return Oldest;
}

FTransform ULBStormFXSubsystem::MakeStrikeTransform(const FVector& Target, const FVector& Direction, const FVector& Camera) const
{
	FVector Away(Direction.X, Direction.Y, 0.0);
	if (!Away.Normalize())
	{
		Away = FVector::ZeroVector;
	}
	// Starts in the sky above the target, a little toward the camera (against the flash direction).
	const FVector Start = Target + FVector(0.0, 0.0, Settings->StrikeSkyHeight) - Away * static_cast<double>(Settings->StrikeSkyOffset);
	return LBStormFXLogic::StrikeBoltTransform(Start, Target, Camera, Settings->StrikeWidth);
}

void ULBStormFXSubsystem::HandleLightningStrike(const FLBLightningStrikeInfo& Info)
{
	UWorld* World = GetWorld();
	if (!bActive || !Settings || !World)
	{
		return;
	}
	const double Now = World->GetTimeSeconds();

	// The same three draws for every flash, so a seeded storm replays the same bolts whatever the chances.
	const float Roll = Stream.FRand();
	const float Length = Stream.FRandRange(static_cast<float>(Settings->SkyBoltLength.X), FMath::Max(static_cast<float>(Settings->SkyBoltLength.X), static_cast<float>(Settings->SkyBoltLength.Y)));
	const int32 Atlas = Stream.RandRange(0, FMath::Max(Settings->BoltAtlasCount, 1) - 1);

	if (Info.bHasTarget && SparksSystem)
	{
		UNiagaraFunctionLibrary::SpawnSystemAtLocation(World, SparksSystem, Info.TargetLocation, FRotator::ZeroRotator, FVector::OneVector,
			/*bAutoDestroy*/ true, /*bAutoActivate*/ true, ENCPoolMethod::None, /*bPreCullCheck*/ true);
	}

	FVector Camera;
	if (!GetViewLocation(Camera))
	{
		return;
	}

	FTransform Transform;
	if (Info.bHasTarget)
	{
		// A strike always draws its bolt.
		Transform = MakeStrikeTransform(Info.TargetLocation, Info.Direction, Camera);
	}
	else
	{
		const float* Chance = Settings->SkyBoltChance.Find(Info.Reason);
		if (!LBStormFXLogic::RollBolt(Chance ? *Chance : 0.f, Roll))
		{
			return;
		}
		Transform = LBStormFXLogic::SkyBoltTransform(Camera, Info.Direction, Settings->SkyBoltDistance, Settings->SkyBoltTopHeight, Length, Settings->BoltAspect);
	}

	if (ALBLightningBolt* Bolt = AcquireBolt())
	{
		Bolt->SetBolt(Transform, Atlas);
		Bolt->ShowBolt(Now);
		LatestBolt = Bolt;
	}
}

AActor* ULBStormFXSubsystem::FindDebugTarget()
{
	if (AActor* Cached = DebugTarget.Get())
	{
		return Cached;
	}
	const UWorld* World = GetWorld();
	if (!World || World->GetTimeSeconds() < NextDebugTargetSearch)
	{
		return nullptr;
	}
	// Console and capture use only: searched at most every 2 s while a debug bolt waits for its target.
	NextDebugTargetSearch = World->GetTimeSeconds() + 2.0;
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		if (It->ActorHasTag(DebugTargetTag))
		{
			DebugTarget = *It;
			return *It;
		}
	}
	if (!bWarnedNoDebugTarget)
	{
		bWarnedNoDebugTarget = true;
		UE_LOG(LogLB, Warning, TEXT("StormFX: no actor tagged %s in this level; a debug tower strike has no target"), *DebugTargetTag.ToString());
	}
	return nullptr;
}

void ULBStormFXSubsystem::UpdateDebugBolt(double Now)
{
#if !UE_BUILD_SHIPPING
	const int32 Kind = Settings ? Settings->DebugBolt : -1;
	if (Kind < 0)
	{
		if (DebugBoltActor && DebugBoltActor->IsBoltShown())
		{
			DebugBoltActor->HideBolt();
		}
		return;
	}

	FVector Camera;
	if (!GetViewLocation(Camera))
	{
		return;
	}
	FTransform Transform;
	if (Kind == 0)
	{
		// In front of the camera, so a capture sees it.
		FVector Forward = FVector::ForwardVector;
		GetViewDirection(Forward);
		const float Length = 0.5f * static_cast<float>(Settings->SkyBoltLength.X + Settings->SkyBoltLength.Y);
		Transform = LBStormFXLogic::SkyBoltTransform(Camera, Forward, Settings->SkyBoltDistance, Settings->SkyBoltTopHeight, Length, Settings->BoltAspect);
	}
	else
	{
		const AActor* Target = FindDebugTarget();
		if (!Target)
		{
			return;
		}
		const FVector Location = Target->GetActorLocation();
		Transform = MakeStrikeTransform(Location, (Location - Camera).GetSafeNormal(), Camera);
	}

	if (!DebugBoltActor)
	{
		DebugBoltActor = SpawnBolt();
		if (!DebugBoltActor)
		{
			return;
		}
	}
	DebugBoltActor->SetBolt(Transform, 0);
	if (!DebugBoltActor->IsBoltShown())
	{
		DebugBoltActor->ShowBolt(Now);
	}
#endif
}

#if !UE_BUILD_SHIPPING
void ULBStormFXSubsystem::RequestDebugBolt(int32 Kind)
{
	UWorld* World = GetWorld();
	ULBStormSubsystem* Storm = World ? World->GetSubsystem<ULBStormSubsystem>() : nullptr;
	if (!Storm || !Storm->IsActive())
	{
		UE_LOG(LogLB, Warning, TEXT("lb.StormFX.Bolt: the storm is not active in this world (needs an actor tagged LB_StormMoon and DA_StormSettings)"));
		return;
	}
	if (!bActive)
	{
		UE_LOG(LogLB, Warning, TEXT("lb.StormFX.Bolt: the storm FX are not active (lb.StormFX.Enabled 0, or DA_StormSettings has no FXSettings); the flash will have no bolt"));
	}
	if (Kind == 1)
	{
		NextDebugTargetSearch = 0.0;
		AActor* Target = FindDebugTarget();
		if (!Target)
		{
			UE_LOG(LogLB, Warning, TEXT("lb.StormFX.Bolt 1: no actor tagged %s in this level"), *DebugTargetTag.ToString());
			return;
		}
		Storm->RequestFlashAtTarget(1.f, 0.f, ELBFlashReason::Debug, ELBFlashProfile::Double, Target);
	}
	else
	{
		Storm->RequestFlash(1.f, 0.f, ELBFlashReason::Debug, ELBFlashProfile::Double);
	}
}
#endif
