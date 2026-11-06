#include "Storm/LBStormLogic.h"

namespace LBStormLogic
{
	float StoryIntensity(const TArray<FLBStormStoryStep>& Steps, const FGameplayTagContainer& Present, float DefaultIntensity)
	{
		float Result = DefaultIntensity;
		for (const FLBStormStoryStep& Step : Steps)
		{
			if (Step.Tag.IsValid() && Present.HasTagExact(Step.Tag))
			{
				Result = Step.Intensity;
			}
		}
		return Result;
	}

	float MoveTowards(float Current, float Target, float RatePerSecond, float DeltaSeconds)
	{
		const float MaxStep = FMath::Max(RatePerSecond, 0.f) * FMath::Max(DeltaSeconds, 0.f);
		const float Delta = Target - Current;
		return FMath::Abs(Delta) <= MaxStep ? Target : Current + FMath::Sign(Delta) * MaxStep;
	}

	FFlashShape MakeFlash(ELBFlashProfile Profile, float Brightness, float Gap1, float Gap2, const FEnvelope& Envelope)
	{
		FFlashShape Shape;
		Shape.Brightness = FMath::Max(Brightness, 0.f);
		Gap1 = FMath::Max(Gap1, 0.f);
		Gap2 = FMath::Max(Gap2, 0.f);
		switch (Profile)
		{
		case ELBFlashProfile::Double:
			Shape.Attack = Envelope.MultiAttack;
			Shape.Hold = Envelope.MultiHold;
			Shape.Decay = Envelope.MultiDecay;
			Shape.NumPulses = 2;
			Shape.Pulses[0] = { 0.f, Envelope.DoubleFirstPeak };
			Shape.Pulses[1] = { Gap1, 1.f };
			break;
		case ELBFlashProfile::Triple:
			Shape.Attack = Envelope.MultiAttack;
			Shape.Hold = Envelope.MultiHold;
			Shape.Decay = Envelope.MultiDecay;
			Shape.NumPulses = 3;
			Shape.Pulses[0] = { 0.f, Envelope.TripleFirstPeak };
			Shape.Pulses[1] = { Gap1, 1.f };
			Shape.Pulses[2] = { Gap1 + Gap2, Envelope.TripleLastPeak };
			break;
		case ELBFlashProfile::Sheet:
		case ELBFlashProfile::Auto:
		default:
			Shape.Attack = Envelope.SheetAttack;
			Shape.Hold = Envelope.SheetHold;
			Shape.Decay = Envelope.SheetDecay;
			Shape.NumPulses = 1;
			Shape.Pulses[0] = { 0.f, 1.f };
			break;
		}
		// A zero attack or decay would divide by zero in EvaluatePulse.
		Shape.Attack = FMath::Max(Shape.Attack, UE_KINDA_SMALL_NUMBER);
		Shape.Decay = FMath::Max(Shape.Decay, UE_KINDA_SMALL_NUMBER);
		Shape.Hold = FMath::Max(Shape.Hold, 0.f);
		return Shape;
	}

	float EvaluatePulse(float U, float Attack, float Hold, float Decay)
	{
		if (U < 0.f)
		{
			return 0.f;
		}
		if (U < Attack)
		{
			return U / Attack;
		}
		if (U < Attack + Hold)
		{
			return 1.f;
		}
		return FMath::Exp(-(U - Attack - Hold) / Decay);
	}

	float EvaluateFlash(const FFlashShape& Shape, float T)
	{
		float Best = 0.f;
		for (int32 Index = 0; Index < Shape.NumPulses; ++Index)
		{
			const FPulse& Pulse = Shape.Pulses[Index];
			Best = FMath::Max(Best, Pulse.Peak * EvaluatePulse(T - Pulse.Start, Shape.Attack, Shape.Hold, Shape.Decay));
		}
		return FMath::Clamp(Shape.Brightness * Best, 0.f, 1.f);
	}

	float FlashDuration(const FFlashShape& Shape)
	{
		float LastStart = 0.f;
		for (int32 Index = 0; Index < Shape.NumPulses; ++Index)
		{
			LastStart = FMath::Max(LastStart, Shape.Pulses[Index].Start);
		}
		return LastStart + Shape.Attack + Shape.Hold + DecayTails * Shape.Decay;
	}

	ELBFlashProfile PickProfile(float Roll01, float WeightSheet, float WeightDouble, float WeightTriple)
	{
		WeightSheet = FMath::Max(WeightSheet, 0.f);
		WeightDouble = FMath::Max(WeightDouble, 0.f);
		WeightTriple = FMath::Max(WeightTriple, 0.f);
		const float Total = WeightSheet + WeightDouble + WeightTriple;
		if (Total <= UE_SMALL_NUMBER)
		{
			return ELBFlashProfile::Sheet;
		}
		const float Pick = FMath::Clamp(Roll01, 0.f, 1.f) * Total;
		if (Pick < WeightSheet)
		{
			return ELBFlashProfile::Sheet;
		}
		return Pick < WeightSheet + WeightDouble ? ELBFlashProfile::Double : ELBFlashProfile::Triple;
	}

	void IntervalBounds(float Intensity, const FScheduleParams& Params, float& OutMin, float& OutMax)
	{
		const float I = FMath::Clamp(Intensity, 0.f, 1.f);
		OutMin = FMath::Lerp(Params.MinIntervalLow, Params.MinIntervalHigh, I);
		OutMax = FMath::Lerp(Params.MaxIntervalLow, Params.MaxIntervalHigh, I);
		OutMax = FMath::Max(OutMax, OutMin);
	}

	float NextInterval(float Intensity, float Roll01, const FScheduleParams& Params, bool bFirst)
	{
		float Min = 0.f, Max = 0.f;
		IntervalBounds(Intensity, Params, Min, Max);
		const float Interval = FMath::Lerp(Min, Max, FMath::Clamp(Roll01, 0.f, 1.f));
		return bFirst ? Interval * Params.FirstFlashScale : Interval;
	}

	float EarliestStart(float RequestedStart, float BusyUntil, float MinGap)
	{
		return FMath::Max(RequestedStart, BusyUntil + FMath::Max(MinGap, 0.f));
	}

	float AmbientBrightness(float Roll01, float Intensity, float BrightnessMin, float BrightnessFloorLow)
	{
		return FMath::Lerp(BrightnessMin, 1.f, FMath::Clamp(Roll01, 0.f, 1.f)) * FMath::Lerp(BrightnessFloorLow, 1.f, FMath::Clamp(Intensity, 0.f, 1.f));
	}

	FVector DirectionFromAngles(float AzimuthDegrees, float ElevationDegrees)
	{
		const float Az = FMath::DegreesToRadians(AzimuthDegrees);
		const float El = FMath::DegreesToRadians(ElevationDegrees);
		const float Flat = FMath::Cos(El);
		return FVector(Flat * FMath::Cos(Az), Flat * FMath::Sin(Az), FMath::Sin(El));
	}

	FVector RevealDirection(const FVector& CameraToTarget, float RaiseDegrees)
	{
		const FVector Flat(CameraToTarget.X, CameraToTarget.Y, 0.0);
		if (Flat.SizeSquared() < UE_SMALL_NUMBER)
		{
			return DirectionFromAngles(0.f, RaiseDegrees);
		}
		return DirectionFromAngles(static_cast<float>(Flat.Rotation().Yaw), RaiseDegrees);
	}

	float WindStrength(float Intensity, float TimeSeconds, const FWindParams& Params)
	{
		const float I = FMath::Clamp(Intensity, 0.f, 1.f);
		const float Base = FMath::Lerp(Params.BaseLow, Params.BaseHigh, I);
		const float Gust = FMath::Lerp(Params.GustLow, Params.GustHigh, I) * FMath::Max(0.f, 2.f * FMath::PerlinNoise1D(TimeSeconds * Params.GustFrequency));
		return FMath::Clamp(Base + Gust, 0.f, 1.f);
	}

	float AdvanceWindPhase(float Phase, float Strength, float DeltaSeconds, const FWindParams& Params)
	{
		const float Speed = FMath::Lerp(Params.PhaseSpeedLow, Params.PhaseSpeedHigh, FMath::Clamp(Strength, 0.f, 1.f));
		float Next = Phase + FMath::Max(DeltaSeconds, 0.f) * Speed;
		Next = FMath::Fmod(Next, WindPhaseWrap);
		return Next < 0.f ? Next + WindPhaseWrap : Next;
	}

	float ResolveExposure(TConstArrayView<FExposureEntry> ContainingZones, float DefaultExposure)
	{
		if (ContainingZones.IsEmpty())
		{
			return FMath::Clamp(DefaultExposure, 0.f, 1.f);
		}
		const FExposureEntry* Best = nullptr;
		for (const FExposureEntry& Entry : ContainingZones)
		{
			if (!Best || Entry.Priority > Best->Priority || (Entry.Priority == Best->Priority && Entry.Exposure < Best->Exposure))
			{
				Best = &Entry;
			}
		}
		return FMath::Clamp(Best->Exposure, 0.f, 1.f);
	}

	bool ShouldReveal(const FRevealInputs& In, ERevealCheck& OutCheck)
	{
		OutCheck = ERevealCheck::Reveal;
		if (!In.bEnabled)
		{
			OutCheck = ERevealCheck::Disabled;
		}
		else if (In.Intensity < In.MinIntensity)
		{
			OutCheck = ERevealCheck::LowIntensity;
		}
		else if (!In.bWardenExists)
		{
			OutCheck = ERevealCheck::NoWarden;
		}
		else if (In.bWardenDormant)
		{
			OutCheck = ERevealCheck::Dormant;
		}
		else if (In.Distance < In.MinDistance)
		{
			OutCheck = ERevealCheck::TooClose;
		}
		else if (In.Distance > In.MaxDistance)
		{
			OutCheck = ERevealCheck::TooFar;
		}
		else if (In.AngleDegrees > In.ConeDegrees)
		{
			OutCheck = ERevealCheck::OutOfCone;
		}
		else if (!In.bLineClear)
		{
			OutCheck = ERevealCheck::Blocked;
		}
		else if (In.Exposure < In.MinExposure)
		{
			OutCheck = ERevealCheck::LowExposure;
		}
		else if (In.SecondsSinceLastReveal < In.CooldownSeconds)
		{
			OutCheck = ERevealCheck::Cooldown;
		}
		else if (In.bFlashBusy)
		{
			OutCheck = ERevealCheck::Busy;
		}
		return OutCheck == ERevealCheck::Reveal;
	}

	const TCHAR* RevealCheckName(ERevealCheck Check)
	{
		switch (Check)
		{
		case ERevealCheck::Reveal: return TEXT("reveal");
		case ERevealCheck::Disabled: return TEXT("disabled");
		case ERevealCheck::LowIntensity: return TEXT("storm intensity too low");
		case ERevealCheck::NoWarden: return TEXT("no Warden");
		case ERevealCheck::Dormant: return TEXT("Warden dormant");
		case ERevealCheck::TooClose: return TEXT("too close");
		case ERevealCheck::TooFar: return TEXT("too far");
		case ERevealCheck::OutOfCone: return TEXT("outside the view cone");
		case ERevealCheck::Blocked: return TEXT("line of sight blocked");
		case ERevealCheck::LowExposure: return TEXT("not exposed to the sky");
		case ERevealCheck::Cooldown: return TEXT("cooldown");
		case ERevealCheck::Busy: return TEXT("a flash is running or pending");
		default: return TEXT("?");
		}
	}

	FLightRule SelectLightRule(const TArray<FLBLightStateRule>& Rules, const FGameplayTagContainer& Present)
	{
		FLightRule Result;
		for (const FLBLightStateRule& Rule : Rules)
		{
			if (Rule.RequiredTag.IsValid() && Present.HasTagExact(Rule.RequiredTag))
			{
				Result.Mode = Rule.Mode;
				Result.Scale = Rule.IntensityScale;
				Result.FlickerAmount = Rule.FlickerAmount;
				Result.FlickerSpeed = Rule.FlickerSpeed;
			}
		}
		return Result;
	}

	float LightScaleAt(const FLightRule& Rule, float TimeSeconds, float Seed)
	{
		switch (Rule.Mode)
		{
		case ELBLightStateMode::Off:
			return 0.f;
		case ELBLightStateMode::Dim:
			return Rule.Scale;
		case ELBLightStateMode::Flicker:
		{
			const float Noise = FMath::Clamp(0.5f + 0.5f * FMath::PerlinNoise1D(TimeSeconds * Rule.FlickerSpeed + Seed), 0.f, 1.f);
			return Rule.Scale * (1.f - FMath::Clamp(Rule.FlickerAmount, 0.f, 1.f) * Noise);
		}
		case ELBLightStateMode::On:
		default:
			return 1.f;
		}
	}

	float GutterNoise(float TimeSeconds)
	{
		return FMath::Clamp(0.6f + 0.4f * FMath::PerlinNoise1D(TimeSeconds * 9.f), 0.f, 1.f);
	}

	float FadeScale(float From, float To, float Alpha, float TimeSeconds)
	{
		const float A = FMath::Clamp(Alpha, 0.f, 1.f);
		const float Weight = 4.f * A * (1.f - A);
		return FMath::Lerp(From, To, A) * FMath::Lerp(1.f, GutterNoise(TimeSeconds), Weight);
	}
}
