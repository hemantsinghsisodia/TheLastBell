#include "Audio/LBAudioLogic.h"

namespace LBAudioLogic
{
	namespace
	{
		float Saturate(float Value) { return FMath::Clamp(Value, 0.f, 1.f); }
	}

	FRainMix RainMix(float Exposure, float RoofRain, float Power, float OutGain, float InGain)
	{
		const float E = Saturate(Exposure);
		FRainMix Mix;
		Mix.Out = OutGain * FMath::Pow(E, FMath::Max(Power, 0.f));
		Mix.In = InGain * (1.f - E) * Saturate(RoofRain);
		return Mix;
	}

	FWindMix WindMix(float Exposure, float WindStrength, float InteriorWind, float HowlAmount, float OutGain, float MinWind)
	{
		const float W = Saturate(WindStrength);
		FWindMix Mix;
		Mix.Wind = OutGain * FMath::Lerp(Saturate(MinWind), 1.f, W) * FMath::Max(Saturate(Exposure), Saturate(InteriorWind));
		Mix.Howl = Saturate(HowlAmount) * W;
		return Mix;
	}

	EThunderSet ThunderSetFor(float Brightness, const FThunderParams& Params)
	{
		if (Brightness >= Params.NearAt)
		{
			return EThunderSet::Near;
		}
		if (Brightness < Params.FarBelow)
		{
			return EThunderSet::Far;
		}
		return EThunderSet::Mid;
	}

	FThunderPlan PlanThunder(float Brightness, ELBFlashReason Reason, float Rand, const FThunderParams& Params)
	{
		(void)Reason;
		const float B = Saturate(Brightness);
		FThunderPlan Plan;
		Plan.Set = ThunderSetFor(B, Params);
		const float Base = FMath::Lerp(static_cast<float>(Params.Delay.Y), static_cast<float>(Params.Delay.X), B);
		Plan.Delay = FMath::Max(0.f, Base + (2.f * Saturate(Rand) - 1.f) * Params.Jitter);
		Plan.Volume = 0.55f + 0.45f * B;
		return Plan;
	}

	FMusicTargets MusicTargets(ELBWardenState State, int32 Stage, float Distance, const FMusicParams& Params)
	{
		FMusicTargets Targets;
		if (State == ELBWardenState::Chase || State == ELBWardenState::Attack)
		{
			Targets.Tension = Params.Chase;
			Targets.Chase = Params.ChaseLevel;
			return Targets;
		}
		if (State == ELBWardenState::Dormant || Stage < Params.MinStage || Distance > Params.TensionNearDistance)
		{
			return Targets;
		}
		switch (State)
		{
		case ELBWardenState::Patrol: Targets.Tension = Params.Patrol; break;
		case ELBWardenState::Suspicious: Targets.Tension = Params.Suspicious; break;
		case ELBWardenState::Investigate: Targets.Tension = Params.Investigate; break;
		case ELBWardenState::Search: Targets.Tension = Params.Search; break;
		case ELBWardenState::Return: Targets.Tension = Params.Return; break;
		default: break;
		}
		return Targets;
	}

	float StressTarget(const FStressInputs& Inputs, const FStressParams& Params)
	{
		float Target = 0.f;
		if (Inputs.WardenState == ELBWardenState::Chase || Inputs.WardenState == ELBWardenState::Attack)
		{
			Target = Params.Chase;
		}
		else if (Inputs.WardenDistance <= Params.NearDistance
			&& (Inputs.WardenState == ELBWardenState::Investigate || Inputs.WardenState == ELBWardenState::Search || Inputs.WardenState == ELBWardenState::Suspicious))
		{
			Target = Params.NearSearch;
		}
		const float Darkness = Saturate(Inputs.ZoneDarkness) * (Inputs.bCandleLit ? Params.DarknessLit : Params.DarknessUnlit);
		Target = FMath::Max(Target, Darkness);
		if (Inputs.bSprintBonus)
		{
			Target += Params.SprintBonus;
		}
		return Saturate(Target);
	}

	float Stress(float Prev, const FStressInputs& Inputs, float DeltaSeconds, const FStressParams& Params)
	{
		float S = Saturate(Prev);
		if (Inputs.bCandleOutImpulse)
		{
			S = Saturate(S + Params.CandleOut);
		}
		const float Target = StressTarget(Inputs, Params);
		const float Dt = FMath::Max(DeltaSeconds, 0.f);
		if (Target > S)
		{
			S = FMath::Min(Target, S + Params.Rise * Dt);
		}
		else if (Target < S)
		{
			S = FMath::Max(Target, S - Params.Decay * Dt);
		}
		return Saturate(S);
	}

	int32 BreathTier(float StressLevel, const FBreathThresholds& Thresholds)
	{
		if (StressLevel >= Thresholds.Panic)
		{
			return 3;
		}
		if (StressLevel >= Thresholds.Heavy)
		{
			return 2;
		}
		if (StressLevel >= Thresholds.Calm)
		{
			return 1;
		}
		return 0;
	}

	FBellPlan BellPlan(const FGameplayTag& Tag, const TArray<FLBBellBeat>& Beats)
	{
		FBellPlan Plan;
		if (!Tag.IsValid())
		{
			return Plan;
		}
		for (const FLBBellBeat& Beat : Beats)
		{
			if (Beat.Trigger.IsValid() && Beat.Trigger == Tag)
			{
				Plan.bFound = true;
				Plan.Stage = Beat.Stage;
				Plan.Strikes = Beat.Strikes;
				Plan.FirstDelay = Beat.FirstDelay;
				Plan.Spacing = Beat.Spacing;
				Plan.Drone = Beat.Drone;
				return Plan;
			}
		}
		return Plan;
	}

	int32 CurrentBellStage(const TArray<FLBBellBeat>& Beats, const FGameplayTagContainer& State)
	{
		int32 Stage = 1;
		for (const FLBBellBeat& Beat : Beats)
		{
			if (Beat.Trigger.IsValid() && State.HasTagExact(Beat.Trigger))
			{
				Stage = FMath::Max(Stage, Beat.Stage);
			}
		}
		return Stage;
	}

	FAmbientTollDecision AmbientTollPlan(double Now, double NextToll, double LastBeat, bool bChase, float Tension, int32 Stage, bool bFinale,
		float RandA, float RandB, const FTollParams& Params)
	{
		FAmbientTollDecision Decision;
		Decision.NextTime = NextToll;
		Decision.Stage = FMath::Clamp(Stage, 1, 5);
		if (!Params.bEnabled || bFinale)
		{
			Decision.NextTime = TNumericLimits<double>::Max();
			return Decision;
		}
		if (Now < NextToll)
		{
			return Decision;
		}
		const double B = static_cast<double>(Saturate(RandB));
		if (bChase || Tension > Params.MaxTension || (Now - LastBeat) < static_cast<double>(Params.GapAfterBeat))
		{
			Decision.NextTime = Now + FMath::Lerp(Params.SkipRetry.X, Params.SkipRetry.Y, B);
			return Decision;
		}
		const int32 MinStrikes = FMath::Max(1, FMath::RoundToInt(static_cast<float>(Params.Strikes.X)));
		const int32 MaxStrikes = FMath::Max(MinStrikes, FMath::RoundToInt(static_cast<float>(Params.Strikes.Y)));
		Decision.bPlay = true;
		Decision.Strikes = FMath::Min(MaxStrikes, MinStrikes + FMath::FloorToInt(Saturate(RandA) * static_cast<float>(MaxStrikes - MinStrikes + 1)));
		Decision.NextTime = Now + FMath::Lerp(Params.Interval.X, Params.Interval.Y, B);
		return Decision;
	}

	int32 PickVariant(int32 Count, int32 Last, float Rand)
	{
		if (Count <= 0)
		{
			return INDEX_NONE;
		}
		if (Count == 1)
		{
			return 0;
		}
		// Draw among the other Count - 1 entries, then skip over Last.
		int32 Index = FMath::Clamp(FMath::FloorToInt(Saturate(Rand) * static_cast<float>(Count - 1)), 0, Count - 2);
		if (Last >= 0 && Last < Count && Index >= Last)
		{
			++Index;
		}
		return Index;
	}

	float Ease(float Current, float Target, float InSeconds, float OutSeconds, float DeltaSeconds)
	{
		if (Target > Current)
		{
			if (InSeconds <= 0.f)
			{
				return Target;
			}
			return FMath::Min(Target, Current + DeltaSeconds / InSeconds);
		}
		if (Target < Current)
		{
			if (OutSeconds <= 0.f)
			{
				return Target;
			}
			return FMath::Max(Target, Current - DeltaSeconds / OutSeconds);
		}
		return Current;
	}
}
