#include "AI/LBApparitionLogic.h"

namespace
{
	/** Smooth 0..1 progress; a zero duration is complete. */
	float Progress(float Time, float Duration)
	{
		return Duration > UE_KINDA_SMALL_NUMBER ? FMath::SmoothStep(0.f, 1.f, FMath::Clamp(Time / Duration, 0.f, 1.f)) : 1.f;
	}

	/** Moves on to the next station, or to Done after the last one. */
	void NextStation(FLBApparitionRun& Run, int32 StationCount)
	{
		++Run.Station;
		Run.Phase = Run.Station < StationCount ? ELBApparitionPhase::WaitForLook : ELBApparitionPhase::Done;
		Run.PhaseTime = 0.f;
		Run.Alpha = 0.f;
	}

	/** An early fade-out (the player came too close) starts from the current alpha. */
	void BeginFadeOut(FLBApparitionRun& Run)
	{
		Run.FadeOutFrom = Run.Alpha;
		Run.Phase = ELBApparitionPhase::FadeOut;
		Run.PhaseTime = 0.f;
	}
}

namespace LBApparition
{
	void Start(FLBApparitionRun& Run)
	{
		Run = FLBApparitionRun();
		Run.Phase = ELBApparitionPhase::ArmDelay;
	}

	void Reset(FLBApparitionRun& Run)
	{
		Run = FLBApparitionRun();
	}

	void Finish(FLBApparitionRun& Run)
	{
		Run = FLBApparitionRun();
		Run.Phase = ELBApparitionPhase::Done;
	}

	bool Step(FLBApparitionRun& Run, const TArray<FLBApparitionStation>& Stations, float ArmDelaySeconds, const FLBApparitionFacts& Facts)
	{
		if (Run.Phase == ELBApparitionPhase::Idle || Run.Phase == ELBApparitionPhase::Done)
		{
			Run.Alpha = 0.f;
			return false;
		}
		if (Run.Phase != ELBApparitionPhase::ArmDelay && !Stations.IsValidIndex(Run.Station))
		{
			// Nothing left to show.
			Finish(Run);
			return false;
		}

		Run.PhaseTime += FMath::Max(Facts.DeltaSeconds, 0.f);
		const FLBApparitionStation* Station = Stations.IsValidIndex(Run.Station) ? &Stations[Run.Station] : nullptr;
		const bool bTooClose = Station && Station->MinPlayerDistance > 0.f && Facts.PlayerDistance < Station->MinPlayerDistance;

		switch (Run.Phase)
		{
		case ELBApparitionPhase::ArmDelay:
			Run.Alpha = 0.f;
			if (Run.PhaseTime >= ArmDelaySeconds)
			{
				Run.Phase = Stations.Num() > 0 ? ELBApparitionPhase::WaitForLook : ELBApparitionPhase::Done;
				Run.PhaseTime = 0.f;
			}
			return false;

		case ELBApparitionPhase::WaitForLook:
			Run.Alpha = 0.f;
			if (bTooClose)
			{
				NextStation(Run, Stations.Num());
				return false;
			}
			if (Facts.bLookedAt)
			{
				Run.Phase = ELBApparitionPhase::FadeIn;
				Run.PhaseTime = 0.f;
				return true;
			}
			return false;

		case ELBApparitionPhase::FadeIn:
			if (bTooClose)
			{
				BeginFadeOut(Run);
				return false;
			}
			if (Run.PhaseTime >= Station->FadeInSeconds)
			{
				Run.Phase = ELBApparitionPhase::Hold;
				Run.PhaseTime -= Station->FadeInSeconds;
				Run.Alpha = 1.f;
			}
			else
			{
				Run.Alpha = Progress(Run.PhaseTime, Station->FadeInSeconds);
			}
			return false;

		case ELBApparitionPhase::Hold:
			if (bTooClose)
			{
				BeginFadeOut(Run);
				return false;
			}
			Run.Alpha = 1.f;
			if (Run.PhaseTime >= Station->HoldSeconds)
			{
				Run.PhaseTime -= Station->HoldSeconds;
				Run.FadeOutFrom = 1.f;
				Run.Phase = ELBApparitionPhase::FadeOut;
			}
			return false;

		case ELBApparitionPhase::FadeOut:
			if (Run.PhaseTime >= Station->FadeOutSeconds)
			{
				Run.Phase = ELBApparitionPhase::Gap;
				Run.PhaseTime -= Station->FadeOutSeconds;
				Run.Alpha = 0.f;
			}
			else
			{
				Run.Alpha = Run.FadeOutFrom * (1.f - Progress(Run.PhaseTime, Station->FadeOutSeconds));
			}
			return false;

		case ELBApparitionPhase::Gap:
			Run.Alpha = 0.f;
			if (Run.PhaseTime >= Station->GapAfterSeconds)
			{
				NextStation(Run, Stations.Num());
			}
			return false;

		default:
			return false;
		}
	}

	const TCHAR* PhaseName(ELBApparitionPhase Phase)
	{
		switch (Phase)
		{
		case ELBApparitionPhase::Idle: return TEXT("Idle");
		case ELBApparitionPhase::ArmDelay: return TEXT("ArmDelay");
		case ELBApparitionPhase::WaitForLook: return TEXT("WaitForLook");
		case ELBApparitionPhase::FadeIn: return TEXT("FadeIn");
		case ELBApparitionPhase::Hold: return TEXT("Hold");
		case ELBApparitionPhase::FadeOut: return TEXT("FadeOut");
		case ELBApparitionPhase::Gap: return TEXT("Gap");
		case ELBApparitionPhase::Done: return TEXT("Done");
		default: return TEXT("?");
		}
	}
}
