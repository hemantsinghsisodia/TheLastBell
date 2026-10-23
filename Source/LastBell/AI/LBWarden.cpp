#include "AI/LBWarden.h"
#include "AI/LBWardenBrainComponent.h"
#include "AI/LBWardenController.h"
#include "AI/LBWardenTuningData.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

ALBWarden::ALBWarden()
{
	PrimaryActorTick.bCanEverTick = false;

	// Collision must fit the monastery doorways (about 104 x 230 cm, D-038). The visual body is taller and lives in BP_Warden.
	const ULBWardenTuningData* Defaults = GetDefault<ULBWardenTuningData>();
	GetCapsuleComponent()->InitCapsuleSize(Defaults->CapsuleRadius, Defaults->CapsuleHalfHeight);
	// Eye height above the capsule centre.
	BaseEyeHeight = Defaults->EyeHeight;

	AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
	AIControllerClass = ALBWardenController::StaticClass();

	bUseControllerRotationYaw = false;
	bUseControllerRotationPitch = false;
	bUseControllerRotationRoll = false;

	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->bOrientRotationToMovement = true;
	Movement->bUseControllerDesiredRotation = false;
	Movement->RotationRate = FRotator(0.f, 360.f, 0.f);
	Movement->MaxWalkSpeed = Defaults->PatrolSpeed;
	Movement->MaxAcceleration = 1200.f;
	Movement->BrakingDecelerationWalking = 2000.f;
}

const ULBWardenTuningData& ALBWarden::GetTuning() const
{
	return Tuning ? *Tuning : *GetDefault<ULBWardenTuningData>();
}

ULBWardenBrainComponent* ALBWarden::GetBrain() const
{
	const ALBWardenController* WardenController = Cast<ALBWardenController>(GetController());
	return WardenController ? WardenController->GetBrain() : nullptr;
}

void ALBWarden::BeginPlay()
{
	Super::BeginPlay();
	// An assigned tuning asset overrides the constructor defaults (a Blueprint cannot run the constructor with its own asset).
	const ULBWardenTuningData& T = GetTuning();
	GetCapsuleComponent()->SetCapsuleSize(T.CapsuleRadius, T.CapsuleHalfHeight);
	BaseEyeHeight = T.EyeHeight;
	// Hidden until the brain decides the stage allows an appearance and the player cannot see the spawn point.
	SetDormantPresentation(true);
}

void ALBWarden::SetDormantPresentation(bool bDormant)
{
	bDormantPresentation = bDormant;
	SetActorHiddenInGame(bDormant);
	SetActorEnableCollision(!bDormant);
	if (UCharacterMovementComponent* Movement = GetCharacterMovement())
	{
		if (bDormant)
		{
			Movement->StopMovementImmediately();
			Movement->DisableMovement();
		}
		else if (Movement->MovementMode == MOVE_None)
		{
			Movement->SetMovementMode(MOVE_Walking);
		}
	}
}
