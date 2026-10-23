#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "Engine/World.h"
#include "AI/LBWardenTypes.h"
#include "LBWardenTestSink.generated.h"

class ULBWardenBrainComponent;

/**
 * Records the Warden brain's Blueprint delegates (state changes, attack windup, spotted / lost tells) with world timestamps so
 * functional tests can assert on ordering and timing. Dynamic delegates can only bind UFUNCTIONs on a UObject, hence this class.
 * Test-only; never spawned by gameplay.
 */
UCLASS()
class LASTBELLTESTS_API ULBWardenTestSink : public UObject
{
	GENERATED_BODY()

public:
	struct FTransitionRecord
	{
		double Time = 0.0;
		ELBWardenState Old = ELBWardenState::Dormant;
		ELBWardenState New = ELBWardenState::Dormant;
	};

	TWeakObjectPtr<UWorld> World;
	TArray<FTransitionRecord> Transitions;
	TArray<double> SpottedTimes;
	TArray<double> LostTimes;
	TArray<double> WindupTimes;
	TArray<float> WindupSeconds;

	void Bind(ULBWardenBrainComponent* Brain, UWorld* InWorld);

	void Clear()
	{
		Transitions.Reset();
		SpottedTimes.Reset();
		LostTimes.Reset();
		WindupTimes.Reset();
		WindupSeconds.Reset();
	}

	/** Number of times the state was entered at or after FromTime. */
	int32 CountEntries(ELBWardenState State, double FromTime = -1.0) const
	{
		int32 Count = 0;
		for (const FTransitionRecord& R : Transitions)
		{
			Count += (R.New == State && R.Time >= FromTime) ? 1 : 0;
		}
		return Count;
	}

	/** Time of the first entry into State at or after FromTime, or -1. */
	double FirstEntry(ELBWardenState State, double FromTime = -1.0) const
	{
		for (const FTransitionRecord& R : Transitions)
		{
			if (R.New == State && R.Time >= FromTime)
			{
				return R.Time;
			}
		}
		return -1.0;
	}

	/** Time of the last entry into State, or -1. */
	double LastEntry(ELBWardenState State) const
	{
		for (int32 i = Transitions.Num() - 1; i >= 0; --i)
		{
			if (Transitions[i].New == State)
			{
				return Transitions[i].Time;
			}
		}
		return -1.0;
	}

	UFUNCTION()
	void HandleStateChanged(ELBWardenState OldState, ELBWardenState NewState);

	UFUNCTION()
	void HandleAttackWindup(float Seconds);

	UFUNCTION()
	void HandleSpotted();

	UFUNCTION()
	void HandleLost();

private:
	double Now() const { return World.IsValid() ? World->GetTimeSeconds() : 0.0; }
};
