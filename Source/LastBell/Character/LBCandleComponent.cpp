#include "Character/LBCandleComponent.h"
#include "Character/LBCharacter.h"
#include "Character/LBPlayerTuningData.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"

ULBCandleComponent::ULBCandleComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PostPhysics;
}

void ULBCandleComponent::BeginPlay()
{
	Super::BeginPlay();

	const ALBCharacter* Owner = Cast<ALBCharacter>(GetOwner());
	Tuning = Owner ? &Owner->GetTuning() : GetDefault<ULBPlayerTuningData>();

	SetRelativeLocation(Tuning->CandleHeldOffset);

	if (!HeldMesh)
	{
		for (USceneComponent* Child : GetAttachChildren())
		{
			if (UStaticMeshComponent* Mesh = Cast<UStaticMeshComponent>(Child))
			{
				HeldMesh = Mesh;
				break;
			}
		}
	}
	if (HeldMesh)
	{
		HeldMeshBaseRotation = HeldMesh->GetRelativeRotation().Quaternion();
	}

	// The light is created at runtime so a Blueprint cannot leave a candle without one.
	if (!Light)
	{
		Light = NewObject<UPointLightComponent>(GetOwner(), TEXT("CandleLight"));
		Light->SetMobility(EComponentMobility::Movable);
		Light->SetupAttachment(this);
		Light->RegisterComponent();
	}
	ApplyLightSettings();
}

void ULBCandleComponent::SetHeldMesh(UStaticMeshComponent* InMesh)
{
	HeldMesh = InMesh;
	HeldMeshBaseRotation = InMesh ? InMesh->GetRelativeRotation().Quaternion() : FQuat::Identity;
}

void ULBCandleComponent::ApplyLightSettings()
{
	if (!Light || !Tuning)
	{
		return;
	}
	Light->SetIntensityUnits(ELightUnits::Candelas);
	Light->SetLightColor(FLinearColor::White);
	Light->bUseTemperature = true;
	Light->SetTemperature(Tuning->CandleTemperature);
	Light->SetAttenuationRadius(Tuning->CandleAttenuationRadius);
	Light->SetCastShadows(Tuning->bCandleCastShadows);
	Light->SetIntensity(Tuning->CandleIntensity * LitAlpha);
}

bool ULBCandleComponent::ToggleCandle()
{
	const float Delay = Tuning ? Tuning->CandleRelightDelay : GetDefault<ULBPlayerTuningData>()->CandleRelightDelay;
	switch (StateMachine.Toggle(Delay))
	{
	case ELBCandleEvent::Snuffed:
		LitAlpha = 0.f; // instant off
		if (Light)
		{
			Light->SetVisibility(false);
		}
		OnCandleStateChanged.Broadcast(false);
		return true;
	case ELBCandleEvent::RelightStarted:
		OnRelightStarted.Broadcast();
		return true;
	default:
		return false;
	}
}

void ULBCandleComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

	if (!Tuning)
	{
		return;
	}

	if (StateMachine.Tick(DeltaTime) == ELBCandleEvent::Relit)
	{
		OnCandleStateChanged.Broadcast(true);
	}

	Time += DeltaTime;
	GutterAlpha = FMath::FInterpTo(GutterAlpha, bGuttering ? 1.f : 0.f, DeltaTime, Tuning->CandleGutterBlendSpeed);

	if (StateMachine.IsLit())
	{
		LitAlpha = Tuning->CandleRelightFadeTime > KINDA_SMALL_NUMBER
			? FMath::Min(LitAlpha + DeltaTime / Tuning->CandleRelightFadeTime, 1.f)
			: 1.f;
	}
	else
	{
		LitAlpha = 0.f;
	}

	if (Light)
	{
		const bool bLightOn = LitAlpha > KINDA_SMALL_NUMBER;
		Light->SetVisibility(bLightOn);
		if (bLightOn)
		{
			const float FlickerAmp = FMath::Lerp(Tuning->CandleFlickerAmplitude, Tuning->CandleFlickerAmplitude * Tuning->CandleGutterFlickerMultiplier, GutterAlpha);
			const float T = Time * Tuning->CandleFlickerFrequency;
			// Two octaves of smooth noise so the flame never looks periodic.
			const float Noise = (FMath::PerlinNoise1D(T) + 0.5f * FMath::PerlinNoise1D(T * 2.3f + 17.f)) / 1.5f;
			const float GutterScale = FMath::Lerp(1.f, Tuning->CandleGutterIntensityScale, GutterAlpha);
			Light->SetIntensity(FMath::Max(0.f, Tuning->CandleIntensity * GutterScale * LitAlpha * (1.f + FlickerAmp * Noise)));

			const float Jitter = Tuning->CandlePositionJitter * (1.f + GutterAlpha);
			Light->SetRelativeLocation(FVector(
				FMath::PerlinNoise1D(T * 0.7f + 31.f),
				FMath::PerlinNoise1D(T * 0.9f + 57.f),
				FMath::PerlinNoise1D(T * 1.1f + 91.f)) * Jitter);
		}
	}

	if (HeldMesh)
	{
		const FRotator Target(
			FMath::Clamp(-PendingLookDelta.Y * Tuning->CandleSwayStrength, -Tuning->CandleSwayMaxAngle, Tuning->CandleSwayMaxAngle),
			FMath::Clamp(PendingLookDelta.X * Tuning->CandleSwayStrength, -Tuning->CandleSwayMaxAngle, Tuning->CandleSwayMaxAngle),
			0.f);
		SwayCurrent = FMath::RInterpTo(SwayCurrent, Target, DeltaTime, Tuning->CandleSwaySpeed);
		HeldMesh->SetRelativeRotation(HeldMeshBaseRotation * SwayCurrent.Quaternion());
	}
	PendingLookDelta = FVector2D::ZeroVector;
}
