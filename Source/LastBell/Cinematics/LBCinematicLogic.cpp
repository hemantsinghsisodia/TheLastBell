#include "Cinematics/LBCinematicLogic.h"
#include "Misc/DefaultValueHelper.h"

namespace
{
	bool ParseFloatArg(const FString& Text, float& Out)
	{
		return FDefaultValueHelper::ParseFloat(Text, Out) && FMath::IsFinite(Out);
	}

	bool ParseIntArg(const FString& Text, int32& Out)
	{
		return FDefaultValueHelper::ParseInt(Text, Out);
	}

	bool Fail(FString& OutError, const FString& Label, const TCHAR* Reason)
	{
		OutError = FString::Printf(TEXT("marker '%s': %s"), *Label, Reason);
		return false;
	}
}

namespace LBCinematicLogic
{
	bool ParseMarker(const FString& Label, FLBCineMarker& OutMarker, FString& OutError)
	{
		OutError.Reset();
		if (Label.IsEmpty())
		{
			return Fail(OutError, Label, TEXT("the label is empty"));
		}
		for (const TCHAR Char : Label)
		{
			if (FChar::IsWhitespace(Char))
			{
				return Fail(OutError, Label, TEXT("a label has no spaces"));
			}
		}

		FLBCineMarker Parsed;
		Parsed.Seconds = OutMarker.Seconds;
		Parsed.Label = Label;

		FString Body = Label;
		if (Body.StartsWith(TEXT("!")))
		{
			Parsed.bMust = true;
			Body.RightChopInline(1, EAllowShrinking::No);
		}
		if (Body.IsEmpty())
		{
			return Fail(OutError, Label, TEXT("there is no kind after the '!'"));
		}

		FString Kind;
		FString ArgText;
		const bool bHasColon = Body.Split(TEXT(":"), &Kind, &ArgText);
		if (!bHasColon)
		{
			Kind = Body;
		}
		TArray<FString> Args;
		if (bHasColon)
		{
			if (ArgText.IsEmpty())
			{
				return Fail(OutError, Label, TEXT("the argument after ':' is empty"));
			}
			ArgText.ParseIntoArray(Args, TEXT(","), /*bCullEmpty*/ false);
			for (const FString& Arg : Args)
			{
				if (Arg.IsEmpty())
				{
					return Fail(OutError, Label, TEXT("an argument is empty"));
				}
			}
		}

		// The argument count rule of each kind: Min..Max.
		auto NeedArgs = [&](int32 Min, int32 Max) -> bool
		{
			if (Args.Num() < Min)
			{
				OutError = FString::Printf(TEXT("marker '%s': missing argument"), *Label);
				return false;
			}
			if (Args.Num() > Max)
			{
				OutError = FString::Printf(TEXT("marker '%s': too many arguments"), *Label);
				return false;
			}
			return true;
		};

		if (Kind == TEXT("card"))
		{
			if (!NeedArgs(1, 1)) { return false; }
			Parsed.Kind = ELBCineMarkerKind::Card;
			Parsed.Name = FName(*Args[0]);
		}
		else if (Kind == TEXT("tag"))
		{
			if (!NeedArgs(1, 1)) { return false; }
			Parsed.Kind = ELBCineMarkerKind::Tag;
			Parsed.Tag = FGameplayTag::RequestGameplayTag(FName(*Args[0]), /*ErrorIfNotFound*/ false);
			if (!Parsed.Tag.IsValid())
			{
				OutError = FString::Printf(TEXT("marker '%s': '%s' is not a gameplay tag the project knows"), *Label, *Args[0]);
				return false;
			}
		}
		else if (Kind == TEXT("bell"))
		{
			if (!NeedArgs(1, 1)) { return false; }
			Parsed.Kind = ELBCineMarkerKind::Bell;
			FString StageText;
			FString StrikeText;
			if (!Args[0].Split(TEXT("x"), &StageText, &StrikeText) || !ParseIntArg(StageText, Parsed.Stage) || !ParseIntArg(StrikeText, Parsed.Strikes))
			{
				return Fail(OutError, Label, TEXT("expected bell:<Stage>x<Strikes>, for example bell:5x1"));
			}
			if (Parsed.Stage < 1 || Parsed.Stage > 5)
			{
				return Fail(OutError, Label, TEXT("the bell stage must be 1 to 5"));
			}
			if (Parsed.Strikes < 1 || Parsed.Strikes > 32)
			{
				return Fail(OutError, Label, TEXT("the number of strikes must be 1 to 32"));
			}
		}
		else if (Kind == TEXT("strike"))
		{
			if (!NeedArgs(1, 2)) { return false; }
			Parsed.Kind = ELBCineMarkerKind::Strike;
			Parsed.Name = FName(*Args[0]);
			if (Args.Num() > 1)
			{
				if (!ParseFloatArg(Args[1], Parsed.Value) || Parsed.Value < 0.f || Parsed.Value > 1.f)
				{
					return Fail(OutError, Label, TEXT("the brightness must be a number from 0 to 1"));
				}
			}
		}
		else if (Kind == TEXT("flash"))
		{
			if (!NeedArgs(1, 1)) { return false; }
			Parsed.Kind = ELBCineMarkerKind::Flash;
			if (!ParseFloatArg(Args[0], Parsed.Value) || Parsed.Value < 0.f || Parsed.Value > 1.f)
			{
				return Fail(OutError, Label, TEXT("the brightness must be a number from 0 to 1"));
			}
		}
		else if (Kind == TEXT("look") || Kind == TEXT("mark"))
		{
			if (!NeedArgs(1, 2)) { return false; }
			Parsed.Kind = Kind == TEXT("look") ? ELBCineMarkerKind::Look : ELBCineMarkerKind::Mark;
			Parsed.Name = FName(*Args[0]);
			if (Args.Num() > 1)
			{
				if (!ParseFloatArg(Args[1], Parsed.Value) || Parsed.Value <= 0.f || Parsed.Value > 60.f)
				{
					return Fail(OutError, Label, TEXT("the seconds must be a number above 0 and at most 60"));
				}
			}
		}
		else if (Kind == TEXT("lock"))
		{
			if (!NeedArgs(1, 1)) { return false; }
			Parsed.Kind = ELBCineMarkerKind::Lock;
			if (Args[0] == TEXT("None"))
			{
				Parsed.Lock = ELBInputLock::None;
			}
			else if (Args[0] == TEXT("Look"))
			{
				Parsed.Lock = ELBInputLock::Look;
			}
			else if (Args[0] == TEXT("Full"))
			{
				Parsed.Lock = ELBInputLock::Full;
			}
			else
			{
				return Fail(OutError, Label, TEXT("the lock must be None, Look or Full"));
			}
		}
		else if (Kind == TEXT("skip"))
		{
			if (!NeedArgs(1, 1)) { return false; }
			Parsed.Kind = ELBCineMarkerKind::Skip;
			if (Args[0] != TEXT("0") && Args[0] != TEXT("1"))
			{
				return Fail(OutError, Label, TEXT("skip needs 0 or 1"));
			}
			Parsed.bFlag = Args[0] == TEXT("1");
		}
		else if (Kind == TEXT("mix"))
		{
			if (!NeedArgs(1, 1)) { return false; }
			Parsed.Kind = ELBCineMarkerKind::Mix;
			if (Args[0] != TEXT("on") && Args[0] != TEXT("off"))
			{
				return Fail(OutError, Label, TEXT("mix needs on or off"));
			}
			Parsed.bFlag = Args[0] == TEXT("on");
		}
		else if (Kind == TEXT("credits"))
		{
			if (!NeedArgs(0, 1)) { return false; }
			Parsed.Kind = ELBCineMarkerKind::Credits;
			if (Args.Num() > 0)
			{
				if (!ParseFloatArg(Args[0], Parsed.Value) || Parsed.Value <= 0.f || Parsed.Value > 600.f)
				{
					return Fail(OutError, Label, TEXT("the seconds must be a number above 0 and at most 600"));
				}
			}
		}
		else if (Kind == TEXT("end"))
		{
			if (!NeedArgs(0, 0)) { return false; }
			Parsed.Kind = ELBCineMarkerKind::End;
		}
		else
		{
			OutError = FString::Printf(TEXT("marker '%s': unknown kind '%s'"), *Label, *Kind);
			return false;
		}

		OutMarker = MoveTemp(Parsed);
		return true;
	}

	void SortMarkers(TArray<FLBCineMarker>& Markers)
	{
		Markers.StableSort([](const FLBCineMarker& A, const FLBCineMarker& B) { return A.Seconds < B.Seconds; });
	}

	void MarkersToFire(const TArray<FLBCineMarker>& Sorted, double PrevSeconds, double CurSeconds, TBitArray<>& FiredMask, TArray<int32>& OutIndices)
	{
		OutIndices.Reset();
		if (FiredMask.Num() != Sorted.Num())
		{
			FiredMask.SetNum(Sorted.Num(), false);
		}
		if (CurSeconds <= PrevSeconds)
		{
			return;
		}
		for (int32 Index = 0; Index < Sorted.Num(); ++Index)
		{
			const double Time = Sorted[Index].Seconds;
			if (Time > CurSeconds)
			{
				break;
			}
			if (Time > PrevSeconds && !FiredMask[Index])
			{
				FiredMask[Index] = true;
				OutIndices.Add(Index);
			}
		}
	}

	void MustMarkersOnSkip(const TArray<FLBCineMarker>& Sorted, TBitArray<>& FiredMask, TArray<int32>& OutIndices)
	{
		OutIndices.Reset();
		if (FiredMask.Num() != Sorted.Num())
		{
			FiredMask.SetNum(Sorted.Num(), false);
		}
		for (int32 Index = 0; Index < Sorted.Num(); ++Index)
		{
			if (Sorted[Index].bMust && !FiredMask[Index])
			{
				FiredMask[Index] = true;
				OutIndices.Add(Index);
			}
		}
	}

	float Smoothstep(float Alpha)
	{
		const float T = FMath::Clamp(Alpha, 0.f, 1.f);
		return T * T * (3.f - 2.f * T);
	}

	float ShortestYawLerp(float FromYaw, float ToYaw, float Alpha)
	{
		const float Delta = FMath::UnwindDegrees(ToYaw - FromYaw);
		return FromYaw + Delta * Alpha;
	}

	float CardDuration(float Fade, float Hold)
	{
		return FMath::Max(Fade, 0.f) * 2.f + FMath::Max(Hold, 0.f);
	}

	float CardOpacity(float Elapsed, float Fade, float Hold)
	{
		const float F = FMath::Max(Fade, 0.f);
		const float H = FMath::Max(Hold, 0.f);
		if (Elapsed < 0.f || Elapsed > CardDuration(F, H))
		{
			return 0.f;
		}
		if (F > UE_SMALL_NUMBER && Elapsed < F)
		{
			return Elapsed / F;
		}
		if (Elapsed <= F + H)
		{
			return 1.f;
		}
		return F > UE_SMALL_NUMBER ? FMath::Clamp(1.f - (Elapsed - F - H) / F, 0.f, 1.f) : 0.f;
	}

	float CreditsPixelsPerSecond(float BoxHeight, float ViewportHeight, float Seconds)
	{
		return (FMath::Max(BoxHeight, 0.f) + FMath::Max(ViewportHeight, 0.f)) / FMath::Max(Seconds, UE_KINDA_SMALL_NUMBER);
	}

	// ---- Bell pendulum ---------------------------------------------------------------------------------------------------------

	void FBellPendulum::Kick(float KickDeg, float MaxDeg)
	{
		if (KickDeg <= 0.f || MaxDeg <= 0.f)
		{
			return;
		}
		if (AmplitudeDeg <= 0.f)
		{
			AmplitudeDeg = FMath::Min(KickDeg, MaxDeg);
			Phase = 0.f;
			return;
		}
		// Keep the angle and the swing direction while the amplitude grows, so a kick during a swing does not pop the bell.
		const float Angle = AmplitudeDeg * FMath::Sin(Phase);
		const bool bMovingUp = FMath::Cos(Phase) >= 0.f;
		const float NewAmplitude = FMath::Min(AmplitudeDeg + KickDeg, MaxDeg);
		const float SinPhase = FMath::Clamp(Angle / NewAmplitude, -1.f, 1.f);
		const float CosPhase = FMath::Sqrt(FMath::Max(1.f - SinPhase * SinPhase, 0.f)) * (bMovingUp ? 1.f : -1.f);
		AmplitudeDeg = NewAmplitude;
		Phase = FMath::Atan2(SinPhase, CosPhase);
	}

	bool FBellPendulum::Advance(float Dt, float PeriodSeconds, float DampingPerSecond, float StopDeg)
	{
		if (AmplitudeDeg <= 0.f)
		{
			return false;
		}
		const float Step = FMath::Max(Dt, 0.f);
		Phase = FMath::Fmod(Phase + UE_TWO_PI * Step / FMath::Max(PeriodSeconds, 0.05f), UE_TWO_PI);
		AmplitudeDeg *= FMath::Exp(-FMath::Max(DampingPerSecond, 0.f) * Step);
		if (AmplitudeDeg < StopDeg)
		{
			Reset();
			return false;
		}
		return true;
	}

	float FBellPendulum::AngleDeg() const
	{
		return AmplitudeDeg > 0.f ? AmplitudeDeg * FMath::Sin(Phase) : 0.f;
	}

	FTransform SwingAboutAxle(const FVector& RestLocation, const FQuat& RestRotation, const FVector& Pivot, const FVector& Axis, float AngleDeg)
	{
		if (FMath::IsNearlyZero(AngleDeg, 1.0e-6f) || Axis.IsNearlyZero())
		{
			return FTransform(RestRotation, RestLocation);
		}
		const FQuat Q(Axis.GetSafeNormal(), FMath::DegreesToRadians(static_cast<double>(AngleDeg)));
		FQuat Rotation = Q * RestRotation;
		Rotation.Normalize();
		return FTransform(Rotation, Pivot + Q.RotateVector(RestLocation - Pivot));
	}

	FVector RopeZAboutAxle(const FVector& RopeRestLocation, const FVector& Pivot, const FVector& Axis, float AngleDeg)
	{
		const FTransform Swung = SwingAboutAxle(RopeRestLocation, FQuat::Identity, Pivot, Axis, AngleDeg);
		return FVector(RopeRestLocation.X, RopeRestLocation.Y, Swung.GetLocation().Z);
	}

	FVector AxleAxis(const FQuat& HeadstockRestRotation, ELBBellSwingAxis SwingAxis)
	{
		return HeadstockRestRotation.RotateVector(SwingAxis == ELBBellSwingAxis::Pitch ? FVector::YAxisVector : FVector::XAxisVector).GetSafeNormal();
	}

	bool FSkipHold::Tick(float Dt, float Needed, bool bSkippable)
	{
		if (!bHolding || !bSkippable)
		{
			Held = 0.f;
			return false;
		}
		Held += FMath::Max(Dt, 0.f);
		if (!bTriggered && Held >= Needed)
		{
			bTriggered = true;
			return true;
		}
		return false;
	}
}
