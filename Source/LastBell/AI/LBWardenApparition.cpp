#include "AI/LBWardenApparition.h"
#include "AI/LBWardenLogic.h"
#include "Storm/LBStormSubsystem.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "LBLog.h"

namespace
{
	const FName FadeParameter(TEXT("Fade"));

	/** The walking figure turns at up to this many degrees per second. */
	constexpr float WalkTurnDegreesPerSecond = 180.f;

	/** No collision, no shadows, no navigation: a visual only. */
	void MakeVisualOnly(UPrimitiveComponent* Mesh)
	{
		Mesh->SetMobility(EComponentMobility::Movable);
		Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Mesh->SetGenerateOverlapEvents(false);
		Mesh->SetCanEverAffectNavigation(false);
		Mesh->SetCastShadow(false);
		Mesh->bReceivesDecals = false;
	}
}

ALBWardenApparition::ALBWardenApparition()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;

	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Root->SetMobility(EComponentMobility::Movable);
	SetRootComponent(Root);

	Body = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Body"));
	Body->SetupAttachment(Root);
	MakeVisualOnly(Body);

	Glow = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Glow"));
	Glow->SetupAttachment(Root);
	MakeVisualOnly(Glow);

	// The animated figure: hidden unless bUseSkeletalFigure.
	Figure = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Figure"));
	Figure->SetupAttachment(Root);
	MakeVisualOnly(Figure);
	Figure->SetVisibility(false);
	// Animate only while on screen. Hidden (it is hidden whenever its fade alpha is 0, i.e. almost all game) it would otherwise
	// run ABP_Warden and its rigid-body robe/chain physics every frame (P13-8 stat anim).
	Figure->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
}

bool ALBWardenApparition::IsTagPresent() const
{
	const ULBWorldStateSubsystem* WorldState = ULBWorldStateSubsystem::Get(this);
	return WorldState && TriggerTag.IsValid() && WorldState->HasState(TriggerTag);
}

void ALBWardenApparition::MakeFadeMaterials(UMeshComponent* Mesh)
{
	if (!Mesh)
	{
		return;
	}
	const int32 SlotCount = Mesh->GetNumMaterials();
	for (int32 Slot = 0; Slot < SlotCount; ++Slot)
	{
		if (Mesh->GetMaterial(Slot))
		{
			if (UMaterialInstanceDynamic* Instance = Mesh->CreateDynamicMaterialInstance(Slot))
			{
				FadeMaterials.Add(Instance);
			}
		}
	}
}

void ALBWardenApparition::BeginPlay()
{
	Super::BeginPlay();

	// The Glow card: hidden at size 0, otherwise scaled to the size in cm (the plane is 100 cm across at scale 1).
	if (GlowSizeCm > 0.f)
	{
		Glow->SetRelativeScale3D(FVector(GlowSizeCm / 100.f));
	}
	else
	{
		Glow->SetVisibility(false);
	}

	// Either the static Body or the animated Figure is the figure; the other stays hidden and gets no fade materials.
	Body->SetVisibility(!bUseSkeletalFigure);
	Figure->SetVisibility(bUseSkeletalFigure);

	FadeMaterials.Reset();
	MakeFadeMaterials(bUseSkeletalFigure ? static_cast<UMeshComponent*>(Figure) : static_cast<UMeshComponent*>(Body));
	MakeFadeMaterials(Glow);

	LBApparition::Reset(Run);
	StopShowing();

	if (ULBWorldStateSubsystem* WorldState = ULBWorldStateSubsystem::Get(this))
	{
		WorldState->OnStateChanged.AddDynamic(this, &ALBWardenApparition::HandleWorldStateChanged);
		WorldState->OnStateReplaced.AddDynamic(this, &ALBWardenApparition::HandleWorldStateReplaced);
	}
	if (IsTagPresent())
	{
		// A checkpoint reload after the beat: it has happened, so it stays finished.
		LBApparition::Finish(Run);
	}
}

void ALBWardenApparition::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (ULBWorldStateSubsystem* WorldState = ULBWorldStateSubsystem::Get(this))
	{
		WorldState->OnStateChanged.RemoveDynamic(this, &ALBWardenApparition::HandleWorldStateChanged);
		WorldState->OnStateReplaced.RemoveDynamic(this, &ALBWardenApparition::HandleWorldStateReplaced);
	}
	Super::EndPlay(EndPlayReason);
}

void ALBWardenApparition::HandleWorldStateChanged(FGameplayTag Tag, bool bAdded)
{
	if (bAdded && TriggerTag.IsValid() && Tag == TriggerTag && Run.Phase == ELBApparitionPhase::Idle)
	{
		BeginRun();
	}
}

void ALBWardenApparition::HandleWorldStateReplaced()
{
	// A load or a new game: whatever was on screen is gone, and the tag says whether the beat has already happened.
	const int32 StationBefore = Run.Station;
	const TCHAR* PhaseBefore = LBApparition::PhaseName(Run.Phase);
	StopShowing();
	if (IsTagPresent())
	{
		LBApparition::Finish(Run);
		UE_LOG(LogLBWarden, Log, TEXT("%s: world state replaced, tag present: finished (was %s at station %d)"), *GetName(), PhaseBefore, StationBefore);
	}
	else
	{
		LBApparition::Reset(Run);
		UE_LOG(LogLBWarden, Log, TEXT("%s: world state replaced, tag absent: reset to Idle (was %s at station %d)"), *GetName(), PhaseBefore, StationBefore);
	}
	ApplyAlpha();
}

void ALBWardenApparition::BeginRun()
{
	UE_LOG(LogLBWarden, Log, TEXT("%s: run started (trigger %s, %d stations, arm delay %.2f s)"), *GetName(), *TriggerTag.ToString(), Stations.Num(), ArmDelaySeconds);
	LBApparition::Start(Run);
	SetActorTickEnabled(true);
}

void ALBWardenApparition::StopShowing()
{
	SetActorTickEnabled(false);
	Run.Alpha = 0.f;
	ApplyAlpha();
}

void ALBWardenApparition::ApplyAlpha()
{
	for (UMaterialInstanceDynamic* Instance : FadeMaterials)
	{
		if (Instance)
		{
			Instance->SetScalarParameterValue(FadeParameter, Run.Alpha);
		}
	}
	SetActorHiddenInGame(Run.Alpha <= 0.f);
}

bool ALBWardenApparition::IsLookedAt(const FLBApparitionStation& Station, const FVector& CameraLocation, const FRotator& CameraRotation) const
{
	const FVector LookPoint = Station.Location + FVector(0.0, 0.0, LookPointHeight);
	if (!LBWardenLogic::IsInsideViewCone(CameraLocation, CameraRotation.Vector(), LookPoint, Station.LookConeDegrees))
	{
		return false;
	}
	// Only now the line of sight: the trace is the expensive part.
	const UWorld* World = GetWorld();
	if (!World)
	{
		return false;
	}
	FCollisionQueryParams Params(SCENE_QUERY_STAT(LBApparitionLook), false, this);
	if (const APlayerController* PC = World->GetFirstPlayerController())
	{
		Params.AddIgnoredActor(PC->GetPawn());
	}
	return !World->LineTraceTestByChannel(CameraLocation, LookPoint, ECC_Visibility, Params);
}

bool ALBWardenApparition::AdvanceWalk(const FLBApparitionStation& Station, float DeltaSeconds)
{
	if (WalkIndex >= Station.WalkPath.Num())
	{
		return true;
	}

	FVector Location = GetActorLocation();
	FRotator Rotation = GetActorRotation();

	// Turn towards the next point (yaw only), at a limited rate.
	const FVector ToTarget = Station.WalkPath[WalkIndex] - Location;
	const FVector Flat(ToTarget.X, ToTarget.Y, 0.0);
	if (Flat.SizeSquared() > 1.0)
	{
		Rotation.Yaw = FMath::FixedTurn(static_cast<float>(Rotation.Yaw), static_cast<float>(Flat.Rotation().Yaw), WalkTurnDegreesPerSecond * DeltaSeconds);
	}

	// Move along the path; a long frame may cover several points.
	float Budget = FMath::Max(Station.WalkSpeed, 1.f) * FMath::Max(DeltaSeconds, 0.f);
	while (Budget > 0.f && WalkIndex < Station.WalkPath.Num())
	{
		const FVector Delta = Station.WalkPath[WalkIndex] - Location;
		const float Distance = static_cast<float>(Delta.Size());
		if (Distance <= Budget)
		{
			Location = Station.WalkPath[WalkIndex];
			Budget -= Distance;
			++WalkIndex;
		}
		else
		{
			Location += Delta / Distance * Budget;
			Budget = 0.f;
		}
	}

	SetActorLocationAndRotation(Location, Rotation, false, nullptr, ETeleportType::None);
	return WalkIndex >= Station.WalkPath.Num();
}

void ALBWardenApparition::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	FLBApparitionFacts Facts;
	Facts.DeltaSeconds = DeltaSeconds;

	const FLBApparitionStation* Station = Stations.IsValidIndex(Run.Station) ? &Stations[Run.Station] : nullptr;
	if (Station && Run.Phase == ELBApparitionPhase::Walk)
	{
		Facts.bWalkFinished = AdvanceWalk(*Station, DeltaSeconds);
	}

	const APlayerController* PC = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;
	const APlayerCameraManager* Camera = PC ? PC->PlayerCameraManager.Get() : nullptr;
	FVector CameraLocation = FVector::ZeroVector;
	if (Camera && Station)
	{
		CameraLocation = Camera->GetCameraLocation();
		// While walking, "too close" is about the figure, which has left the station.
		const FVector& From = Run.Phase == ELBApparitionPhase::Walk ? GetActorLocation() : Station->Location;
		Facts.PlayerDistance = static_cast<float>(FVector::DistXY(CameraLocation, From));
		if (Run.Phase == ELBApparitionPhase::WaitForLook)
		{
			Facts.bLookedAt = IsLookedAt(*Station, CameraLocation, Camera->GetCameraRotation());
		}
	}

	const ELBApparitionPhase PhaseBefore = Run.Phase;
	const int32 StationBefore = Run.Station;
	const bool bEnteredFadeIn = LBApparition::Step(Run, Stations, ArmDelaySeconds, Facts);

	// One line per transition, never per tick.
	if (bEnteredFadeIn)
	{
		UE_LOG(LogLBWarden, Log, TEXT("%s: station %d fading in"), *GetName(), Run.Station);
	}
	else if (PhaseBefore == ELBApparitionPhase::WaitForLook && Run.Station == StationBefore + 1)
	{
		UE_LOG(LogLBWarden, Log, TEXT("%s: station %d skipped, player too close (%.0f cm)"), *GetName(), StationBefore, Facts.PlayerDistance);
	}
	if (PhaseBefore != ELBApparitionPhase::Walk && Run.Phase == ELBApparitionPhase::Walk)
	{
		WalkIndex = 0;
		bWalkFinished = false;
		UE_LOG(LogLBWarden, Log, TEXT("%s: station %d walk started (%d points, %.0f cm/s)"), *GetName(), Run.Station, Station ? Station->WalkPath.Num() : 0, Station ? Station->WalkSpeed : 0.f);
	}
	else if (PhaseBefore == ELBApparitionPhase::Walk && Run.Phase != ELBApparitionPhase::Walk)
	{
		bWalkFinished = Facts.bWalkFinished;
		UE_LOG(LogLBWarden, Log, TEXT("%s: station %d walk ended (%s) at %s, player %.0f cm away"), *GetName(), StationBefore,
			bWalkFinished ? TEXT("path finished") : TEXT("cut short, player too close"), *GetActorLocation().ToCompactString(), Facts.PlayerDistance);
	}
	if (PhaseBefore != ELBApparitionPhase::Done && Run.Phase == ELBApparitionPhase::Done)
	{
		UE_LOG(LogLBWarden, Log, TEXT("%s: run done"), *GetName());
	}

	// P14: the figure appears with a flash of lightning (the station opts in).
	if (PhaseBefore != ELBApparitionPhase::Hold && Run.Phase == ELBApparitionPhase::Hold && Stations.IsValidIndex(Run.Station) && Stations[Run.Station].bLightningOnHold)
	{
		if (ULBStormSubsystem* Storm = GetWorld() ? GetWorld()->GetSubsystem<ULBStormSubsystem>() : nullptr)
		{
			if (Storm->IsActive())
			{
				Storm->RequestFlash(1.f, 0.15f, ELBFlashReason::Apparition, ELBFlashProfile::Double);
			}
		}
	}

	if (bEnteredFadeIn && Station)
	{
		// Just entered FadeIn: stand at the station and turn (yaw only) to face the player. It stays like that.
		const FVector ToPlayer = CameraLocation - Station->Location;
		const float Yaw = static_cast<float>(FVector(ToPlayer.X, ToPlayer.Y, 0.0).Rotation().Yaw);
		SetActorLocationAndRotation(Station->Location, FRotator(0.f, Yaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
		// P16: audio hangs its sting and whisper on this (no behaviour change here).
		OnAppeared.Broadcast(this, Run.Station);
	}

	ApplyAlpha();

	if (Run.Phase == ELBApparitionPhase::Done)
	{
		SetActorTickEnabled(false);
	}
}
