#pragma once

#include "CoreMinimal.h"
#include "LBPlayerTypes.generated.h"

UENUM(BlueprintType)
enum class ELBGait : uint8
{
	Idle,
	Walk,
	Sprint,
	Crouch
};

/** Pure, engine-free player logic so it can be unit tested without a world. */
namespace LBPlayerLogic
{
	/** Forward component of a local move axis (X = right, Y = forward), -1..1. 0 when there is no input. */
	inline float InputForwardDot(const FVector2D& Axis)
	{
		const double Len = Axis.Size();
		return Len > UE_KINDA_SMALL_NUMBER ? static_cast<float>(Axis.Y / Len) : 0.f;
	}

	/** Sprint needs the button held, not crouched, move input present and mostly forward. */
	inline bool CanSprint(bool bSprintHeld, bool bCrouched, bool bHasMoveInput, float ForwardDot, float MinForwardDot)
	{
		return bSprintHeld && !bCrouched && bHasMoveInput && ForwardDot > MinForwardDot;
	}

	/** Items whose thinnest half extent is below this fraction of their middle half extent count as flat (a note, a card). */
	constexpr float FlatItemRatio = 0.35f;

	/**
	 * Rotation in CAMERA space (X forward, Y right, Z up) that holds a flat item face-on: its thinnest local axis points back at
	 * the camera and its longest local axis points up. HalfExtent is the item's size along its own X, Y, Z axes.
	 * Returns false (and Identity) when the item is not flat.
	 */
	inline bool ComputeFaceCameraRotation(const FVector& HalfExtent, FQuat& OutRotation)
	{
		OutRotation = FQuat::Identity;
		int32 Thin = 0;
		int32 Long = 0;
		for (int32 i = 1; i < 3; ++i)
		{
			if (HalfExtent[i] < HalfExtent[Thin])
			{
				Thin = i;
			}
			if (HalfExtent[i] > HalfExtent[Long])
			{
				Long = i;
			}
		}
		if (Thin == Long)
		{
			return false;
		}
		const int32 Mid = 3 - Thin - Long;
		if (HalfExtent[Mid] <= UE_KINDA_SMALL_NUMBER || HalfExtent[Thin] > HalfExtent[Mid] * FlatItemRatio)
		{
			return false;
		}
		FVector ThinAxis = FVector::ZeroVector;
		FVector LongAxis = FVector::ZeroVector;
		ThinAxis[Thin] = 1.0;
		LongAxis[Long] = 1.0;
		// Frame whose X is the thin axis and Y the long axis, and the frame we want it to land in (X back at the camera, Y up).
		const FQuat Local(FRotationMatrix::MakeFromXY(ThinAxis, LongAxis));
		const FQuat Target(FRotationMatrix::MakeFromXY(FVector(-1.0, 0.0, 0.0), FVector(0.0, 0.0, 1.0)));
		OutRotation = Target * Local.Inverse();
		return true;
	}

	inline ELBGait SelectGait(bool bCrouched, bool bSprinting, float HorizontalSpeed, float IdleSpeedThreshold)
	{
		if (bCrouched)
		{
			return ELBGait::Crouch;
		}
		if (HorizontalSpeed < IdleSpeedThreshold)
		{
			return ELBGait::Idle;
		}
		return bSprinting ? ELBGait::Sprint : ELBGait::Walk;
	}
}

/** Accumulates travelled distance and reports how many strides were completed. */
struct FLBStrideAccumulator
{
	float Accumulated = 0.f;

	/** Returns the number of steps completed by moving Distance with the given stride. */
	int32 Advance(float Distance, float Stride)
	{
		if (Stride <= UE_KINDA_SMALL_NUMBER || Distance <= 0.f)
		{
			return 0;
		}
		Accumulated += Distance;
		const int32 Steps = FMath::FloorToInt(Accumulated / Stride);
		Accumulated -= Steps * Stride;
		return Steps;
	}

	void Reset() { Accumulated = 0.f; }
};

enum class ELBCandleState : uint8
{
	Lit,
	Snuffed,
	Relighting
};

enum class ELBCandleEvent : uint8
{
	None,
	Snuffed,
	RelightStarted,
	Relit
};

/** Snuff / relight-delay state machine. Toggling is ignored while relighting. */
struct FLBCandleStateMachine
{
	ELBCandleState State = ELBCandleState::Lit;
	float RelightTimeLeft = 0.f;

	bool IsLit() const { return State == ELBCandleState::Lit; }

	ELBCandleEvent Toggle(float RelightDelay)
	{
		switch (State)
		{
		case ELBCandleState::Lit:
			State = ELBCandleState::Snuffed;
			RelightTimeLeft = 0.f;
			return ELBCandleEvent::Snuffed;
		case ELBCandleState::Snuffed:
			State = ELBCandleState::Relighting;
			RelightTimeLeft = FMath::Max(RelightDelay, 0.f);
			return ELBCandleEvent::RelightStarted;
		default:
			return ELBCandleEvent::None;
		}
	}

	ELBCandleEvent Tick(float DeltaTime)
	{
		if (State == ELBCandleState::Relighting)
		{
			RelightTimeLeft -= DeltaTime;
			if (RelightTimeLeft <= 0.f)
			{
				State = ELBCandleState::Lit;
				RelightTimeLeft = 0.f;
				return ELBCandleEvent::Relit;
			}
		}
		return ELBCandleEvent::None;
	}
};
