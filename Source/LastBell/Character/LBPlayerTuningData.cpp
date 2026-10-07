#include "Character/LBPlayerTuningData.h"
#include "GameFramework/CharacterMovementComponent.h"

float ULBPlayerTuningData::GetStride(ELBGait Gait) const
{
	switch (Gait)
	{
	case ELBGait::Walk: return WalkStride;
	case ELBGait::Sprint: return SprintStride;
	case ELBGait::Crouch: return CrouchStride;
	default: return 0.f;
	}
}

float ULBPlayerTuningData::GetLoudness(ELBGait Gait) const
{
	switch (Gait)
	{
	case ELBGait::Walk: return WalkLoudness;
	case ELBGait::Sprint: return SprintLoudness;
	case ELBGait::Crouch: return CrouchLoudness;
	default: return 0.f;
	}
}

float ULBPlayerTuningData::GetGaitSpeed(ELBGait Gait) const
{
	switch (Gait)
	{
	case ELBGait::Walk: return WalkSpeed;
	case ELBGait::Sprint: return SprintSpeed;
	case ELBGait::Crouch: return CrouchSpeed;
	default: return 0.f;
	}
}

void ULBPlayerTuningData::ApplyToMovement(UCharacterMovementComponent* Movement) const
{
	if (!Movement)
	{
		return;
	}
	Movement->MaxWalkSpeed = WalkSpeed;
	Movement->MaxWalkSpeedCrouched = CrouchSpeed;
	Movement->MaxAcceleration = MaxAcceleration;
	Movement->BrakingDecelerationWalking = BrakingDeceleration;
	Movement->GroundFriction = GroundFriction;
	Movement->SetCrouchedHalfHeight(CrouchedHalfHeight);
}
