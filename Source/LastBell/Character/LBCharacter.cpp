#include "Character/LBCharacter.h"
#include "Components/LBInteractorComponent.h"
#include "Systems/LBGameMode.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "EnhancedInputComponent.h"
#include "InputActionValue.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "GameFramework/PlayerController.h"
#include "LBLog.h"

ALBCharacter::ALBCharacter()
{
	PrimaryActorTick.bCanEverTick = false;

	FirstPersonCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FirstPersonCamera"));
	FirstPersonCamera->SetupAttachment(GetCapsuleComponent());
	FirstPersonCamera->SetRelativeLocation(FVector(0.f, 0.f, 64.f));
	FirstPersonCamera->bUsePawnControlRotation = true;

	Interactor = CreateDefaultSubobject<ULBInteractorComponent>(TEXT("Interactor"));
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
	}
	if (LookAction)
	{
		Input->BindAction(LookAction, ETriggerEvent::Triggered, this, &ALBCharacter::Look);
	}
	if (InteractAction)
	{
		Input->BindAction(InteractAction, ETriggerEvent::Started, this, &ALBCharacter::Interact);
	}
}

void ALBCharacter::Move(const FInputActionValue& Value)
{
	const FVector2D Axis = Value.Get<FVector2D>();
	AddMovementInput(GetActorForwardVector(), Axis.Y);
	AddMovementInput(GetActorRightVector(), Axis.X);
}

void ALBCharacter::Look(const FInputActionValue& Value)
{
	const FVector2D Axis = Value.Get<FVector2D>() * LookSensitivity;
	AddControllerYawInput(Axis.X);
	AddControllerPitchInput(Axis.Y);
}

void ALBCharacter::Interact()
{
	if (!bIsDead && Interactor)
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
