#include "Character/LBCameraFeelComponent.h"
#include "Character/LBCharacter.h"
#include "Character/LBPlayerTuningData.h"
#include "Systems/LBUserSettings.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

ULBCameraFeelComponent::ULBCameraFeelComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PostPhysics;
}

void ULBCameraFeelComponent::BeginPlay()
{
	Super::BeginPlay();

	ALBCharacter* Owner = Cast<ALBCharacter>(GetOwner());
	Character = Owner;
	if (!Owner)
	{
		SetComponentTickEnabled(false);
		return;
	}

	Tuning = &Owner->GetTuning();
	Camera = Owner->FindComponentByClass<UCameraComponent>();
	if (UCameraComponent* Cam = Camera.Get())
	{
		BaseRelativeLocation = Cam->GetRelativeLocation();
		BaseFOV = Cam->FieldOfView;
	}
	else
	{
		SetComponentTickEnabled(false);
	}
	StandingHalfHeight = Owner->GetDefaultHalfHeight();
	Owner->LandedDelegate.AddDynamic(this, &ULBCameraFeelComponent::HandleLanded);
}

void ULBCameraFeelComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (ALBCharacter* Owner = Character.Get())
	{
		Owner->LandedDelegate.RemoveDynamic(this, &ULBCameraFeelComponent::HandleLanded);
	}
	Super::EndPlay(EndPlayReason);
}

void ULBCameraFeelComponent::HandleLanded(const FHitResult& Hit)
{
	const ULBPlayerTuningData* T = Tuning.Get();
	if (!T)
	{
		return;
	}
	const float Range = FMath::Max(T->LandingDipFullFallSpeed - T->LandingDipMinFallSpeed, 1.f);
	DipScale = FMath::Clamp((PeakFallSpeed - T->LandingDipMinFallSpeed) / Range, 0.f, 1.f);
	PeakFallSpeed = 0.f;
	if (DipScale > 0.f)
	{
		DipElapsed = 0.f;
		bDipActive = true;
	}
}

void ULBCameraFeelComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

	ALBCharacter* Owner = Character.Get();
	UCameraComponent* Cam = Camera.Get();
	const ULBPlayerTuningData* T = Tuning.Get();
	if (!Owner || !Cam || !T)
	{
		return;
	}

	const UCharacterMovementComponent* Movement = Owner->GetCharacterMovement();
	const ELBGait Gait = Owner->GetGait();
	const float Speed2D = Owner->GetVelocity().Size2D();
	const bool bOnGround = Movement && Movement->IsMovingOnGround();

	if (Movement && Movement->IsFalling())
	{
		PeakFallSpeed = FMath::Max(PeakFallSpeed, -static_cast<float>(Owner->GetVelocity().Z));
	}

	// Crouch eye height. The capsule snaps to its crouched size instantly (feet stay put), so the camera
	// height is blended in height-above-feet space and converted back to a capsule-relative offset.
	CrouchAlpha = FMath::FInterpConstantTo(CrouchAlpha, Owner->bIsCrouched ? 1.f : 0.f, DeltaTime, 1.f / FMath::Max(T->CrouchCameraBlendTime, KINDA_SMALL_NUMBER));
	const float EyeAboveFeet = FMath::Lerp(StandingHalfHeight, T->CrouchedHalfHeight, FMath::SmoothStep(0.f, 1.f, CrouchAlpha)) + BaseRelativeLocation.Z;
	const float CapsuleHalfHeight = Owner->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	float RelativeZ = EyeAboveFeet - CapsuleHalfHeight;

	// Head bob: vertical only, scaled by speed and gait, settling to zero when idle, airborne or disabled.
	const ULBUserSettings* Settings = ULBUserSettings::Get();
	const bool bBobAllowed = !Settings || Settings->bHeadBob;
	const bool bBobbing = bBobAllowed && bOnGround && Gait != ELBGait::Idle;
	if (bBobbing)
	{
		switch (Gait)
		{
		case ELBGait::Sprint:
			BobAmplitude = T->SprintBobAmplitude;
			BobFrequency = T->SprintBobFrequency;
			break;
		case ELBGait::Crouch:
			BobAmplitude = T->CrouchBobAmplitude;
			BobFrequency = T->CrouchBobFrequency;
			break;
		default:
			BobAmplitude = T->WalkBobAmplitude;
			BobFrequency = T->WalkBobFrequency;
			break;
		}
	}
	BobWeight = FMath::FInterpTo(BobWeight, bBobbing ? 1.f : 0.f, DeltaTime, T->BobSettleSpeed);
	if (BobWeight < KINDA_SMALL_NUMBER)
	{
		BobWeight = 0.f;
		BobPhase = 0.f;
	}
	float BobZ = 0.f;
	if (BobWeight > 0.f)
	{
		const float GaitSpeed = FMath::Max(T->GetGaitSpeed(Gait), 1.f);
		const float SpeedRatio = FMath::Clamp(Speed2D / GaitSpeed, 0.f, 1.f);
		BobPhase = FMath::Fmod(BobPhase + DeltaTime * BobFrequency * SpeedRatio * UE_TWO_PI, UE_TWO_PI);
		BobZ = FMath::Sin(BobPhase) * BobAmplitude * SpeedRatio * BobWeight;
	}

	// Landing dip: down and back up along a half sine.
	float DipZ = 0.f;
	if (bDipActive)
	{
		DipElapsed += DeltaTime;
		const float Alpha = DipElapsed / FMath::Max(T->LandingDipTime, KINDA_SMALL_NUMBER);
		if (Alpha >= 1.f)
		{
			bDipActive = false;
		}
		else
		{
			DipZ = -T->LandingDipDepth * DipScale * FMath::Sin(Alpha * UE_PI);
		}
	}

	// Skip the writes when nothing visibly changed so an idle pawn does not dirty the camera transform every frame.
	constexpr float ApplyEpsilon = 0.001f;
	const FVector NewLocation(BaseRelativeLocation.X, BaseRelativeLocation.Y, RelativeZ + BobZ + DipZ);
	if (!bHasApplied || !NewLocation.Equals(LastAppliedLocation, ApplyEpsilon))
	{
		Cam->SetRelativeLocation(NewLocation);
		LastAppliedLocation = NewLocation;
	}

	// Sprint FOV.
	SprintAlpha = FMath::FInterpConstantTo(SprintAlpha, Gait == ELBGait::Sprint ? 1.f : 0.f, DeltaTime, 1.f / FMath::Max(T->SprintFOVEaseTime, KINDA_SMALL_NUMBER));
	const float NewFOV = BaseFOV + T->SprintFOVDelta * FMath::SmoothStep(0.f, 1.f, SprintAlpha);
	if (!bHasApplied || !FMath::IsNearlyEqual(NewFOV, LastAppliedFOV, ApplyEpsilon))
	{
		Cam->SetFieldOfView(NewFOV);
		LastAppliedFOV = NewFOV;
	}
	bHasApplied = true;
}
