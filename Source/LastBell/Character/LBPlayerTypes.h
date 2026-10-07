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

/** What happens when an inspection is closed. The actor's transform is always restored first. */
struct FLBInspectCloseResult
{
	bool bKept = false;
	bool bGrantKeepTags = false;
	bool bRunInteractGrant = false;
	bool bHideActor = false;
};

namespace LBPlayerLogic
{
	inline FLBInspectCloseResult ResolveInspectClose(bool bKeepOnClose, bool bHasInteractable)
	{
		FLBInspectCloseResult Result;
		Result.bKept = bKeepOnClose;
		Result.bGrantKeepTags = bKeepOnClose;
		Result.bRunInteractGrant = bKeepOnClose && bHasInteractable;
		Result.bHideActor = bKeepOnClose;
		return Result;
	}
}
