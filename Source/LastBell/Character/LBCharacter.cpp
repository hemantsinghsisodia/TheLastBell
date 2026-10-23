#include "Character/LBCharacter.h"
#include "Character/LBCameraFeelComponent.h"
#include "Character/LBCandleComponent.h"
#include "Character/LBFootstepComponent.h"
#include "Character/LBInspectionComponent.h"
#include "Character/LBPlayerTuningData.h"
#include "Components/LBInteractorComponent.h"
#include "Systems/LBGameMode.h"
#include "Systems/LBUserSettings.h"
#include "Camera/CameraComponent.h"
#include "Perception/AIPerceptionStimuliSourceComponent.h"
#include "Perception/AISense_Sight.h"
#include "Components/CapsuleComponent.h"
#include "EnhancedInputComponent.h"
#include "InputActionValue.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "GameFramework/PlayerController.h"
#include "LBLog.h"

ALBCharacter::ALBCharacter()
{
	PrimaryActorTick.bCanEverTick = true;

	FirstPersonCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FirstPersonCamera"));
	FirstPersonCamera->SetupAttachment(GetCapsuleComponent());
	FirstPersonCamera->SetRelativeLocation(FVector(0.f, 0.f, 64.f));
	FirstPersonCamera->bUsePawnControlRotation = true;

	Interactor = CreateDefaultSubobject<ULBInteractorComponent>(TEXT("Interactor"));
	CameraFeel = CreateDefaultSubobject<ULBCameraFeelComponent>(TEXT("CameraFeel"));
	Footsteps = CreateDefaultSubobject<ULBFootstepComponent>(TEXT("Footsteps"));
	Inspection = CreateDefaultSubobject<ULBInspectionComponent>(TEXT("Inspection"));

	Candle = CreateDefaultSubobject<ULBCandleComponent>(TEXT("Candle"));
	Candle->SetupAttachment(FirstPersonCamera);

	StimuliSource = CreateDefaultSubobject<UAIPerceptionStimuliSourceComponent>(TEXT("StimuliSource"));

	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->GetNavAgentPropertiesRef().bCanCrouch = true;
	// The capsule shrinks with the feet planted; ULBCameraFeelComponent blends the eye height.
	Movement->bCrouchMaintainsBaseLocation = true;
}

const ULBPlayerTuningData& ALBCharacter::GetTuning() const
{
	return Tuning ? *Tuning : *GetDefault<ULBPlayerTuningData>();
}

void ALBCharacter::BeginPlay()
{
	Super::BeginPlay();
	if (!Tuning)
	{
		UE_LOG(LogLB, Verbose, TEXT("%s has no Tuning asset: using the class defaults"), *GetName());
	}
	GetTuning().ApplyToMovement(GetCharacterMovement());

	// Visible to AI sight. The component's own auto-register flag and sense list are protected, so register explicitly here.
	if (StimuliSource)
	{
		StimuliSource->RegisterForSense(UAISense_Sight::StaticClass());
	}
}

bool ALBCharacter::IsInspecting() const
{
	return Inspection && Inspection->IsInspecting();
}

ELBGait ALBCharacter::GetGait() const
{
	return CachedGait;
}

void ALBCharacter::UpdateSprintState()
{
	const ULBPlayerTuningData& T = GetTuning();
	bSprinting = !IsInspecting() && LBPlayerLogic::CanSprint(bSprintHeld, bIsCrouched,
		!MoveInput.IsNearlyZero(), LBPlayerLogic::InputForwardDot(MoveInput), T.SprintMinForwardDot);
	if (UCharacterMovementComponent* Movement = GetCharacterMovement())
	{
		const float Speed = bSprinting ? T.SprintSpeed : T.WalkSpeed;
		if (Movement->MaxWalkSpeed != Speed)
		{
			Movement->MaxWalkSpeed = Speed;
		}
	}
}

void ALBCharacter::OnStartCrouch(float HalfHeightAdjust, float ScaledHalfHeightAdjust)
{
	Super::OnStartCrouch(HalfHeightAdjust, ScaledHalfHeightAdjust);
	UpdateSprintState();
}

void ALBCharacter::OnEndCrouch(float HalfHeightAdjust, float ScaledHalfHeightAdjust)
{
	Super::OnEndCrouch(HalfHeightAdjust, ScaledHalfHeightAdjust);
	UpdateSprintState();
}

void ALBCharacter::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	// Gait is derived once per frame; every consumer (footsteps, candle, camera) reads this cache.
	CachedGait = LBPlayerLogic::SelectGait(bIsCrouched, bSprinting, GetVelocity().Size2D(), GetTuning().IdleSpeedThreshold);
	if (Candle)
	{
		Candle->SetGuttering(CachedGait == ELBGait::Sprint);
	}
}

void ALBCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);

	UEnhancedInputComponent* Input = Cast<UEnhancedInputComponent>(PlayerInputComponent);
	if (!Input)
	{
		UE_LOG(LogLB, Error, TEXT("%s: input component is not an EnhancedInputComponent"), *GetName());
		return;
	}

	if (MoveAction)
	{
		Input->BindAction(MoveAction, ETriggerEvent::Triggered, this, &ALBCharacter::Move);
		Input->BindAction(MoveAction, ETriggerEvent::Completed, this, &ALBCharacter::MoveCompleted);
		Input->BindAction(MoveAction, ETriggerEvent::Canceled, this, &ALBCharacter::MoveCompleted);
	}
	if (LookAction)
	{
		Input->BindAction(LookAction, ETriggerEvent::Triggered, this, &ALBCharacter::Look);
	}
	if (InteractAction)
	{
		Input->BindAction(InteractAction, ETriggerEvent::Started, this, &ALBCharacter::Interact);
	}
	if (SprintAction)
	{
		Input->BindAction(SprintAction, ETriggerEvent::Started, this, &ALBCharacter::SprintStarted);
		Input->BindAction(SprintAction, ETriggerEvent::Completed, this, &ALBCharacter::SprintCompleted);
		Input->BindAction(SprintAction, ETriggerEvent::Canceled, this, &ALBCharacter::SprintCompleted);
	}
	if (CrouchAction)
	{
		Input->BindAction(CrouchAction, ETriggerEvent::Started, this, &ALBCharacter::CrouchStarted);
		Input->BindAction(CrouchAction, ETriggerEvent::Completed, this, &ALBCharacter::CrouchCompleted);
		Input->BindAction(CrouchAction, ETriggerEvent::Canceled, this, &ALBCharacter::CrouchCompleted);
	}
	if (CandleAction)
	{
		Input->BindAction(CandleAction, ETriggerEvent::Started, this, &ALBCharacter::CandlePressed);
	}
	if (InspectRotateAction)
	{
		Input->BindAction(InspectRotateAction, ETriggerEvent::Triggered, this, &ALBCharacter::InspectRotate);
	}
	if (InspectExitAction)
	{
		Input->BindAction(InspectExitAction, ETriggerEvent::Started, this, &ALBCharacter::InspectExit);
	}
}

void ALBCharacter::Move(const FInputActionValue& Value)
{
	if (IsInspecting())
	{
		MoveInput = FVector2D::ZeroVector;
		UpdateSprintState();
		return;
	}
	const FVector2D Axis = Value.Get<FVector2D>();
	MoveInput = Axis;
	UpdateSprintState();
	AddMovementInput(GetActorForwardVector(), Axis.Y);
	AddMovementInput(GetActorRightVector(), Axis.X);
}

void ALBCharacter::MoveCompleted()
{
	MoveInput = FVector2D::ZeroVector;
	UpdateSprintState();
}

void ALBCharacter::SprintStarted()
{
	bSprintHeld = true;
	UpdateSprintState();
}

void ALBCharacter::SprintCompleted()
{
	bSprintHeld = false;
	UpdateSprintState();
}

void ALBCharacter::CrouchStarted()
{
	if (!IsInspecting())
	{
		Crouch();
	}
}

void ALBCharacter::CrouchCompleted()
{
	// The engine refuses to stand up under a ceiling and keeps trying until there is room.
	UnCrouch();
}

void ALBCharacter::CandlePressed()
{
	if (Candle)
	{
		Candle->ToggleCandle();
	}
}

void ALBCharacter::InspectRotate(const FInputActionValue& Value)
{
	if (Inspection)
	{
		Inspection->AddRotateInput(Value.Get<FVector2D>());
	}
}

void ALBCharacter::InspectExit()
{
	if (Inspection)
	{
		Inspection->RequestClose();
	}
}

void ALBCharacter::Look(const FInputActionValue& Value)
{
	if (IsInspecting())
	{
		return;
	}
	FVector2D Axis = Value.Get<FVector2D>();
	if (const ULBUserSettings* Settings = ULBUserSettings::Get())
	{
		Axis *= Settings->MouseSensitivity;
		if (Settings->bInvertY)
		{
			Axis.Y = -Axis.Y;
		}
	}
	Axis *= LookSensitivity;
	if (Candle)
	{
		Candle->AddLookDelta(Axis);
	}
	AddControllerYawInput(Axis.X);
	AddControllerPitchInput(Axis.Y);
}

void ALBCharacter::Interact()
{
	if (bIsDead)
	{
		return;
	}
	if (IsInspecting())
	{
		Inspection->RequestClose();
		return;
	}
	if (Inspection && Inspection->WasClosedThisFrame())
	{
		return;
	}
	if (Interactor)
	{
		Interactor->TryInteract();
	}
}

void ALBCharacter::Kill()
{
	if (bIsDead)
	{
		return;
	}
	bIsDead = true;
	UE_LOG(LogLB, Log, TEXT("Player killed"));

	if (IsInspecting())
	{
		// Put the item back (granting nothing) before input is cut off.
		Inspection->CancelInspect();
	}

	AController* PlayerController = GetController();
	if (APlayerController* PC = Cast<APlayerController>(PlayerController))
	{
		DisableInput(PC);
	}
	if (ALBGameMode* GameMode = GetWorld() ? GetWorld()->GetAuthGameMode<ALBGameMode>() : nullptr)
	{
		GameMode->HandlePlayerDeath(PlayerController);
	}
	else
	{
		UE_LOG(LogLB, Warning, TEXT("Kill: no ALBGameMode, death not handled"));
	}
}
