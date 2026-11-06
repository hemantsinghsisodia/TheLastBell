#include "AI/LBWardenAnim.h"

void FLBYawHistory::Add(float Now, float DeltaYawDegrees)
{
	FSample Sample;
	Sample.Time = Now;
	Sample.Delta = DeltaYawDegrees;
	Samples.Add(Sample);

	int32 Stale = 0;
	while (Stale < Samples.Num() && Samples[Stale].Time < Now - Window)
	{
		++Stale;
	}
	if (Stale > 0)
	{
		Samples.RemoveAt(0, Stale, EAllowShrinking::No);
	}
}

float FLBYawHistory::Total() const
{
	float Sum = 0.f;
	for (const FSample& Sample : Samples)
	{
		Sum += Sample.Delta;
	}
	return Sum;
}

namespace LBWardenAnim
{
	bool IsPointInBox(const FLBStoopBox& Box, const FVector& Point)
	{
		if (Box.HalfExtent.X < 0.0 || Box.HalfExtent.Y < 0.0 || Box.HalfExtent.Z < 0.0)
		{
			return false;
		}
		const FVector Local = Box.Rotation.UnrotateVector(Point - Box.Center);
		return FMath::Abs(Local.X) <= Box.HalfExtent.X && FMath::Abs(Local.Y) <= Box.HalfExtent.Y && FMath::Abs(Local.Z) <= Box.HalfExtent.Z;
	}

	float StoopTarget(TConstArrayView<FLBStoopBox> Zones, const FVector& Location)
	{
		float Best = 0.f;
		for (const FLBStoopBox& Zone : Zones)
		{
			if (Zone.Amount > Best && IsPointInBox(Zone, Location))
			{
				Best = Zone.Amount;
			}
		}
		return FMath::Clamp(Best, 0.f, 1.f);
	}

	float EaseTowards(float Current, float Target, float RatePerSecond, float DeltaSeconds)
	{
		const float MaxStep = FMath::Max(RatePerSecond, 0.f) * FMath::Max(DeltaSeconds, 0.f);
		const float Difference = Target - Current;
		if (FMath::Abs(Difference) <= MaxStep)
		{
			return Target;
		}
		return Current + FMath::Sign(Difference) * MaxStep;
	}

	ELBWardenTurn TurnDecision(const FLBYawHistory& History, float GroundSpeed, bool bMontageActive, float CooldownLeft, float TriggerDegrees, float MaxSpeed)
	{
		if (GroundSpeed >= MaxSpeed || bMontageActive || CooldownLeft > 0.f)
		{
			return ELBWardenTurn::None;
		}
		const float Total = History.Total();
		if (Total >= TriggerDegrees)
		{
			return ELBWardenTurn::Right;
		}
		if (Total <= -TriggerDegrees)
		{
			return ELBWardenTurn::Left;
		}
		return ELBWardenTurn::None;
	}

	FLBFootPlacement PelvisAndFeet(const FLBFootHit& Left, const FLBFootHit& Right, float MaxPelvisDrop, float ActivateDifference)
	{
		FLBFootPlacement Out;
		Out.LeftZ = Left.bHit ? Left.GroundZ : 0.f;
		Out.RightZ = Right.bHit ? Right.GroundZ : 0.f;

		const float Lowest = FMath::Min(Out.LeftZ, Out.RightZ);
		Out.PelvisZ = Lowest < 0.f ? -FMath::Min(-Lowest, FMath::Max(MaxPelvisDrop, 0.f)) : 0.f;
		Out.bActive = FMath::Abs(Out.LeftZ - Out.RightZ) > ActivateDifference;
		return Out;
	}

	float AttackPlayRate(float HitTimeSeconds, float WindupSeconds)
	{
		if (HitTimeSeconds <= 0.f || WindupSeconds <= 0.f)
		{
			return 1.f;
		}
		return FMath::Clamp(HitTimeSeconds / WindupSeconds, 0.8f, 2.5f);
	}
}
