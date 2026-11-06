#include "Tests/LBRouteBot.h"

#if WITH_DEV_AUTOMATION_TESTS

#include "AI/LBApparitionLogic.h"
#include "AI/LBWardenApparition.h"

// P12 fix set 1 (F1): the scripted Warden appearances. Unit tests of the pure sequence logic (LastBell.Warden.Apparition.*), then
// functional tests of ALBWardenApparition in a PIE session (LastBell.Functional.Warden.Apparition.*).

#define LB_TEST_FLAGS (EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

// Enum classes have no TestEqual overload: compare them as ints.
#define TEST_ENUM(What, Actual, Expected) TestEqual(What, static_cast<int32>(Actual), static_cast<int32>(Expected))

namespace
{
	constexpr float Dt = 1.f / 60.f;

	FLBApparitionStation MakeStation(float In, float Hold, float Out, float Gap, float MinDistance = 0.f)
	{
		FLBApparitionStation S;
		S.FadeInSeconds = In;
		S.HoldSeconds = Hold;
		S.FadeOutSeconds = Out;
		S.GapAfterSeconds = Gap;
		S.MinPlayerDistance = MinDistance;
		return S;
	}

	/** A station that walks (P13): a path of two points, nothing else changes. */
	FLBApparitionStation MakeWalkStation(float In, float Hold, float Out, float Gap, float MinDistance = 0.f)
	{
		FLBApparitionStation S = MakeStation(In, Hold, Out, Gap, MinDistance);
		S.WalkPath = { FVector(100.0, 0.0, 0.0), FVector(300.0, 200.0, 0.0) };
		S.WalkSpeed = 110.f;
		return S;
	}

	/** Steps a run at 60 Hz with the facts held constant until the test changes them. */
	struct FSim
	{
		FLBApparitionRun Run;
		TArray<FLBApparitionStation> Stations;
		float ArmDelay = 0.f;
		bool bLookedAt = false;
		float Distance = 1000.f;
		bool bWalkFinished = false;
		float Time = 0.f;
		int32 FadeInEntries = 0;

		void Start() { LBApparition::Start(Run); }

		/** One 60 Hz step. Returns what Step returned. */
		bool Tick()
		{
			FLBApparitionFacts F;
			F.DeltaSeconds = Dt;
			F.bLookedAt = bLookedAt;
			F.PlayerDistance = Distance;
			F.bWalkFinished = bWalkFinished;
			Time += Dt;
			const bool bEntered = LBApparition::Step(Run, Stations, ArmDelay, F);
			FadeInEntries += bEntered ? 1 : 0;
			return bEntered;
		}

		/** Steps until the phase is Wanted (at most MaxSeconds). */
		bool TickUntil(ELBApparitionPhase Wanted, float MaxSeconds = 30.f)
		{
			for (float T = 0.f; T < MaxSeconds; T += Dt)
			{
				if (Run.Phase == Wanted)
				{
					return true;
				}
				Tick();
			}
			return Run.Phase == Wanted;
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBApparitionWaitsForLookTest, "LastBell.Warden.Apparition.WaitsForLook", LB_TEST_FLAGS)
bool FLBApparitionWaitsForLookTest::RunTest(const FString& Parameters)
{
	FSim Sim;
	Sim.Stations = { MakeStation(1.f, 3.f, 1.5f, 0.f) };
	Sim.ArmDelay = 0.5f;
	Sim.bLookedAt = false;

	TEST_ENUM(TEXT("Starts Idle"), Sim.Run.Phase, ELBApparitionPhase::Idle);
	Sim.Tick();
	TEST_ENUM(TEXT("Idle ignores Step"), Sim.Run.Phase, ELBApparitionPhase::Idle);

	Sim.Start();
	TEST_ENUM(TEXT("Start enters the arm delay"), Sim.Run.Phase, ELBApparitionPhase::ArmDelay);

	float MaxAlpha = 0.f;
	for (int32 i = 0; i < 60 * 60; ++i)
	{
		TestFalse(TEXT("Never enters FadeIn while unseen"), Sim.Tick());
		MaxAlpha = FMath::Max(MaxAlpha, Sim.Run.Alpha);
	}
	TestEqual(TEXT("Alpha stays 0 for 60 s unseen"), MaxAlpha, 0.f);
	TEST_ENUM(TEXT("Still waiting after 60 s"), Sim.Run.Phase, ELBApparitionPhase::WaitForLook);
	TestEqual(TEXT("FadeIn was never entered"), Sim.FadeInEntries, 0);

	// The first glance starts it, on that very step.
	Sim.bLookedAt = true;
	TestTrue(TEXT("Seen: Step reports entering FadeIn"), Sim.Tick());
	TEST_ENUM(TEXT("Seen: FadeIn"), Sim.Run.Phase, ELBApparitionPhase::FadeIn);
	TestEqual(TEXT("Alpha is still 0 on the entering step (the actor moves the figure first)"), Sim.Run.Alpha, 0.f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBApparitionFadeTimingTest, "LastBell.Warden.Apparition.FadeTiming", LB_TEST_FLAGS)
bool FLBApparitionFadeTimingTest::RunTest(const FString& Parameters)
{
	const float In = 1.f, Hold = 2.f, Out = 1.5f, Gap = 0.5f;
	FSim Sim;
	Sim.Stations = { MakeStation(In, Hold, Out, Gap) };
	Sim.ArmDelay = 0.25f;
	Sim.bLookedAt = true;
	Sim.Start();

	float EntryTime = -1.f, DoneTime = -1.f, PrevAlpha = 0.f, MaxAlpha = 0.f, MidFadeInAlpha = -1.f, MidFadeOutAlpha = -1.f;
	int32 HoldTicks = 0;
	bool bRisingOk = true, bHoldOk = true, bFallingOk = true, bRangeOk = true, bQuietOk = true;
	for (int32 i = 0; i < 60 * 20 && Sim.Run.Phase != ELBApparitionPhase::Done; ++i)
	{
		if (Sim.Tick())
		{
			EntryTime = Sim.Time;
		}
		const FLBApparitionRun& R = Sim.Run;
		bRangeOk &= R.Alpha >= 0.f && R.Alpha <= 1.f;
		MaxAlpha = FMath::Max(MaxAlpha, R.Alpha);
		switch (R.Phase)
		{
		case ELBApparitionPhase::ArmDelay:
		case ELBApparitionPhase::WaitForLook:
		case ELBApparitionPhase::Gap:
		case ELBApparitionPhase::Done:
			bQuietOk &= R.Alpha == 0.f;
			break;
		case ELBApparitionPhase::FadeIn:
			bRisingOk &= R.Alpha >= PrevAlpha;
			if (MidFadeInAlpha < 0.f && Sim.Time - EntryTime >= In * 0.5f)
			{
				MidFadeInAlpha = R.Alpha;
			}
			break;
		case ELBApparitionPhase::Hold:
			bHoldOk &= R.Alpha == 1.f;
			++HoldTicks;
			break;
		case ELBApparitionPhase::FadeOut:
			bFallingOk &= R.Alpha <= PrevAlpha;
			if (MidFadeOutAlpha < 0.f && Sim.Time - EntryTime >= In + Hold + Out * 0.5f)
			{
				MidFadeOutAlpha = R.Alpha;
			}
			break;
		default:
			break;
		}
		PrevAlpha = R.Alpha;
		if (R.Phase == ELBApparitionPhase::Done)
		{
			DoneTime = Sim.Time;
		}
	}

	TestTrue(TEXT("FadeIn was entered"), EntryTime > 0.f);
	TestTrue(TEXT("The run reached Done"), DoneTime > 0.f);
	TestTrue(TEXT("Alpha rises during FadeIn"), bRisingOk);
	TestTrue(TEXT("Alpha is exactly 1 during Hold"), bHoldOk);
	TestTrue(TEXT("Alpha falls during FadeOut"), bFallingOk);
	TestTrue(TEXT("Alpha stays within 0..1"), bRangeOk);
	TestTrue(TEXT("Alpha is 0 whenever the figure is not fading or holding"), bQuietOk);
	TestEqual(TEXT("Alpha reaches 1"), MaxAlpha, 1.f);
	TestEqual(TEXT("Alpha ends at 0"), Sim.Run.Alpha, 0.f);
	TestTrue(FString::Printf(TEXT("Smoothstep is about half way half way through the fade-in (%.3f)"), MidFadeInAlpha), FMath::Abs(MidFadeInAlpha - 0.5f) < 0.05f);
	TestTrue(FString::Printf(TEXT("And half way through the fade-out (%.3f)"), MidFadeOutAlpha), FMath::Abs(MidFadeOutAlpha - 0.5f) < 0.05f);
	TestTrue(FString::Printf(TEXT("Hold lasts %.0f ticks, about %.0f"), static_cast<float>(HoldTicks), Hold / Dt), FMath::Abs(HoldTicks - Hold / Dt) <= 2.f);
	const float Total = DoneTime - EntryTime;
	TestTrue(FString::Printf(TEXT("FadeIn entry to Done takes %.3f s, the sum of the phases is %.3f s"), Total, In + Hold + Out + Gap),
		FMath::Abs(Total - (In + Hold + Out + Gap)) <= 2.f * Dt + 0.001f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBApparitionTwoStationsTest, "LastBell.Warden.Apparition.TwoStations", LB_TEST_FLAGS)
bool FLBApparitionTwoStationsTest::RunTest(const FString& Parameters)
{
	const float In = 0.5f, Hold = 0.5f, Out = 0.5f, Gap = 1.f;
	FSim Sim;
	Sim.Stations = { MakeStation(In, Hold, Out, Gap), MakeStation(In, Hold, Out, 0.f) };
	Sim.bLookedAt = true;
	Sim.Start();

	float FirstEntry = -1.f, SecondEntry = -1.f;
	bool bGapQuiet = true;
	int32 GapTicks = 0;
	for (int32 i = 0; i < 60 * 20 && Sim.Run.Phase != ELBApparitionPhase::Done; ++i)
	{
		if (Sim.Tick())
		{
			(FirstEntry < 0.f ? FirstEntry : SecondEntry) = Sim.Time;
			TestEqual(TEXT("FadeIn entered on the right station"), Sim.Run.Station, Sim.FadeInEntries - 1);
		}
		if (Sim.Run.Phase == ELBApparitionPhase::Gap)
		{
			bGapQuiet &= Sim.Run.Alpha == 0.f;
			++GapTicks;
		}
	}

	TestEqual(TEXT("FadeIn was entered twice, once per station"), Sim.FadeInEntries, 2);
	TEST_ENUM(TEXT("Done after the second station"), Sim.Run.Phase, ELBApparitionPhase::Done);
	TestTrue(TEXT("Alpha is 0 through the gap"), bGapQuiet);
	TestTrue(FString::Printf(TEXT("The gap between the stations lasts %.0f ticks, about %.0f"), static_cast<float>(GapTicks), Gap / Dt), FMath::Abs(GapTicks - Gap / Dt) <= 2.f);
	const float Between = SecondEntry - FirstEntry;
	const float Expected = In + Hold + Out + Gap;
	TestTrue(FString::Printf(TEXT("Second FadeIn begins %.3f s after the first (phases and gap add up to %.3f s)"), Between, Expected),
		Between >= Expected - 0.001f && Between <= Expected + 3.f * Dt);

	// A second station that the player is not looking at yet waits, hidden, however long it takes.
	FSim Waiting;
	Waiting.Stations = { MakeStation(0.2f, 0.2f, 0.2f, 0.f), MakeStation(0.2f, 0.2f, 0.2f, 0.f) };
	Waiting.bLookedAt = true;
	Waiting.Start();
	TestTrue(TEXT("First station reaches its gap"), Waiting.TickUntil(ELBApparitionPhase::Gap));
	Waiting.bLookedAt = false;
	TestTrue(TEXT("Second station reaches WaitForLook"), Waiting.TickUntil(ELBApparitionPhase::WaitForLook));
	TestEqual(TEXT("Waiting on station 2"), Waiting.Run.Station, 1);
	for (int32 i = 0; i < 600; ++i)
	{
		Waiting.Tick();
	}
	TEST_ENUM(TEXT("Still waiting for the second look"), Waiting.Run.Phase, ELBApparitionPhase::WaitForLook);
	TestEqual(TEXT("Hidden while waiting"), Waiting.Run.Alpha, 0.f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBApparitionTooCloseSkipsTest, "LastBell.Warden.Apparition.TooCloseSkips", LB_TEST_FLAGS)
bool FLBApparitionTooCloseSkipsTest::RunTest(const FString& Parameters)
{
	// Station 1 needs the player 300 cm away; station 2 has no minimum.
	{
		FSim Sim;
		Sim.Stations = { MakeStation(0.2f, 0.2f, 0.2f, 0.f, 300.f), MakeStation(0.2f, 0.2f, 0.2f, 0.f) };
		Sim.bLookedAt = true; // looked at, and still skipped
		Sim.Distance = 100.f;
		Sim.Start();
		bool bEnteredFirst = false;
		for (int32 i = 0; i < 5 && Sim.Run.Station == 0; ++i)
		{
			bEnteredFirst |= Sim.Tick();
			TestEqual(TEXT("A skipped station never shows"), Sim.Run.Alpha, 0.f);
		}
		TestFalse(TEXT("Too close while waiting: station 1 is skipped without fading in"), bEnteredFirst);
		TestEqual(TEXT("Moved on to station 2"), Sim.Run.Station, 1);
		TEST_ENUM(TEXT("Station 2 waits for the look"), Sim.Run.Phase, ELBApparitionPhase::WaitForLook);
		TestTrue(TEXT("Station 2 then plays"), Sim.Tick());
	}

	// The only station is skipped: Done, nothing ever shown.
	{
		FSim Sim;
		Sim.Stations = { MakeStation(0.2f, 0.2f, 0.2f, 0.f, 300.f) };
		Sim.bLookedAt = true;
		Sim.Distance = 299.f;
		Sim.Start();
		for (int32 i = 0; i < 10; ++i)
		{
			Sim.Tick();
		}
		TEST_ENUM(TEXT("Skipped the only station: Done"), Sim.Run.Phase, ELBApparitionPhase::Done);
		TestEqual(TEXT("Never faded in"), Sim.FadeInEntries, 0);
	}

	// Exactly at the minimum is far enough.
	{
		FSim Sim;
		Sim.Stations = { MakeStation(0.2f, 0.2f, 0.2f, 0.f, 300.f) };
		Sim.bLookedAt = true;
		Sim.Distance = 300.f;
		Sim.Start();
		Sim.Tick(); // the arm delay ends
		Sim.Tick(); // the look is noticed
		TestTrue(TEXT("At exactly the minimum distance it plays"), Sim.FadeInEntries == 1);
	}

	// Minimum 0 means no limit, even at distance 0.
	{
		FSim Sim;
		Sim.Stations = { MakeStation(0.2f, 0.2f, 0.2f, 0.f, 0.f) };
		Sim.bLookedAt = true;
		Sim.Distance = 0.f;
		Sim.Start();
		Sim.Tick(); // the arm delay ends
		Sim.Tick(); // the look is noticed
		TestEqual(TEXT("Minimum 0: plays even with the player on top of it"), Sim.FadeInEntries, 1);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBApparitionTooCloseDuringHoldTest, "LastBell.Warden.Apparition.TooCloseDuringHoldFadesFromCurrentAlpha", LB_TEST_FLAGS)
bool FLBApparitionTooCloseDuringHoldTest::RunTest(const FString& Parameters)
{
	const float Out = 1.f;

	// During Hold: fades out from 1.
	{
		FSim Sim;
		Sim.Stations = { MakeStation(1.f, 5.f, Out, 0.f, 150.f) };
		Sim.bLookedAt = true;
		Sim.Start();
		TestTrue(TEXT("Reaches Hold"), Sim.TickUntil(ELBApparitionPhase::Hold));
		TestEqual(TEXT("Full alpha in Hold"), Sim.Run.Alpha, 1.f);

		Sim.Distance = 50.f; // the player ran at it
		Sim.Tick();
		TEST_ENUM(TEXT("Too close: straight to FadeOut"), Sim.Run.Phase, ELBApparitionPhase::FadeOut);
		TestEqual(TEXT("Fading out from 1"), Sim.Run.FadeOutFrom, 1.f);
		TestEqual(TEXT("No jump on the step it turns"), Sim.Run.Alpha, 1.f);

		float Prev = Sim.Run.Alpha;
		bool bFalling = true;
		int32 Ticks = 0;
		while (Sim.Run.Phase == ELBApparitionPhase::FadeOut && Ticks < 600)
		{
			Sim.Tick();
			bFalling &= Sim.Run.Alpha <= Prev;
			Prev = Sim.Run.Alpha;
			++Ticks;
		}
		TestTrue(TEXT("Alpha only falls"), bFalling);
		TestTrue(FString::Printf(TEXT("The fade-out takes %d ticks, about %.0f"), Ticks, Out / Dt), FMath::Abs(Ticks - Out / Dt) <= 3.f);
		TestEqual(TEXT("Hidden at the end"), Sim.Run.Alpha, 0.f);
		TestTrue(TEXT("Then the run finishes"), Sim.TickUntil(ELBApparitionPhase::Done, 2.f));
	}

	// During FadeIn: fades out from wherever the fade-in had got to, never jumping up.
	{
		FSim Sim;
		Sim.Stations = { MakeStation(1.f, 5.f, Out, 0.f, 150.f) };
		Sim.bLookedAt = true;
		Sim.Start();
		for (int32 i = 0; i < 600 && !(Sim.Run.Phase == ELBApparitionPhase::FadeIn && Sim.Run.Alpha >= 0.4f); ++i)
		{
			Sim.Tick();
		}
		const float Before = Sim.Run.Alpha;
		TEST_ENUM(TEXT("Still fading in"), Sim.Run.Phase, ELBApparitionPhase::FadeIn);
		TestTrue(TEXT("Partly faded in"), Before >= 0.4f && Before < 1.f);

		Sim.Distance = 50.f;
		Sim.Tick();
		TEST_ENUM(TEXT("Too close during FadeIn: FadeOut"), Sim.Run.Phase, ELBApparitionPhase::FadeOut);
		TestEqual(TEXT("Fades out from the current alpha"), Sim.Run.FadeOutFrom, Before);

		float Prev = Before;
		bool bNeverAbove = true;
		for (int32 i = 0; i < 600 && Sim.Run.Phase == ELBApparitionPhase::FadeOut; ++i)
		{
			Sim.Tick();
			bNeverAbove &= Sim.Run.Alpha <= Prev + KINDA_SMALL_NUMBER;
			Prev = Sim.Run.Alpha;
		}
		TestTrue(TEXT("Alpha never rises again"), bNeverAbove);
		TestEqual(TEXT("Hidden at the end"), Sim.Run.Alpha, 0.f);
		TEST_ENUM(TEXT("Done afterwards"), (Sim.TickUntil(ELBApparitionPhase::Done, 2.f) ? ELBApparitionPhase::Done : Sim.Run.Phase), ELBApparitionPhase::Done);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBApparitionDoneIsTerminalTest, "LastBell.Warden.Apparition.DoneIsTerminal", LB_TEST_FLAGS)
bool FLBApparitionDoneIsTerminalTest::RunTest(const FString& Parameters)
{
	// After a full run nothing brings it back.
	{
		FSim Sim;
		Sim.Stations = { MakeStation(0.2f, 0.2f, 0.2f, 0.1f) };
		Sim.bLookedAt = true;
		Sim.Start();
		TestTrue(TEXT("Run reaches Done"), Sim.TickUntil(ELBApparitionPhase::Done));
		for (int32 i = 0; i < 600; ++i)
		{
			TestFalse(TEXT("Done never re-enters FadeIn"), Sim.Tick());
		}
		TEST_ENUM(TEXT("Still Done after 10 s of being looked at"), Sim.Run.Phase, ELBApparitionPhase::Done);
		TestEqual(TEXT("Alpha 0"), Sim.Run.Alpha, 0.f);
		TestEqual(TEXT("Only ever played once"), Sim.FadeInEntries, 1);
	}

	// The tag was already present: Finish goes straight to Done.
	{
		FSim Sim;
		Sim.Stations = { MakeStation(0.2f, 0.2f, 0.2f, 0.f) };
		Sim.bLookedAt = true;
		LBApparition::Finish(Sim.Run);
		TEST_ENUM(TEXT("Finish: Done"), Sim.Run.Phase, ELBApparitionPhase::Done);
		for (int32 i = 0; i < 120; ++i)
		{
			Sim.Tick();
		}
		TEST_ENUM(TEXT("Finish: stays Done"), Sim.Run.Phase, ELBApparitionPhase::Done);
		TestEqual(TEXT("Finish: never played"), Sim.FadeInEntries, 0);
	}

	// Reset goes back to Idle, which also does nothing until started.
	{
		FSim Sim;
		Sim.Stations = { MakeStation(0.2f, 0.2f, 0.2f, 0.f) };
		Sim.bLookedAt = true;
		Sim.Start();
		Sim.Tick();
		LBApparition::Reset(Sim.Run);
		TEST_ENUM(TEXT("Reset: Idle"), Sim.Run.Phase, ELBApparitionPhase::Idle);
		for (int32 i = 0; i < 120; ++i)
		{
			Sim.Tick();
		}
		TEST_ENUM(TEXT("Reset: stays Idle"), Sim.Run.Phase, ELBApparitionPhase::Idle);
		TestEqual(TEXT("Reset: never played"), Sim.FadeInEntries, 0);
	}

	// No stations: nothing to show, ends Done.
	{
		FSim Sim;
		Sim.bLookedAt = true;
		Sim.Start();
		for (int32 i = 0; i < 10; ++i)
		{
			Sim.Tick();
		}
		TEST_ENUM(TEXT("No stations: Done"), Sim.Run.Phase, ELBApparitionPhase::Done);
		TestEqual(TEXT("No stations: never played"), Sim.FadeInEntries, 0);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBApparitionZeroDurationsTest, "LastBell.Warden.Apparition.ZeroDurationsComplete", LB_TEST_FLAGS)
bool FLBApparitionZeroDurationsTest::RunTest(const FString& Parameters)
{
	// A zero duration completes that phase on the next step; nothing may hang on a 0.
	FSim Sim;
	Sim.Stations = { MakeStation(0.f, 0.f, 0.f, 0.f) };
	Sim.ArmDelay = 0.f;
	Sim.bLookedAt = true;
	Sim.Start();
	int32 Steps = 0;
	while (Sim.Run.Phase != ELBApparitionPhase::Done && Steps < 30)
	{
		Sim.Tick();
		++Steps;
		TestTrue(TEXT("Alpha stays within 0..1"), Sim.Run.Alpha >= 0.f && Sim.Run.Alpha <= 1.f);
	}
	TEST_ENUM(TEXT("All durations 0: still reaches Done"), Sim.Run.Phase, ELBApparitionPhase::Done);
	TestTrue(FString::Printf(TEXT("In a handful of steps (%d)"), Steps), Steps <= 10);
	TestEqual(TEXT("It still played once"), Sim.FadeInEntries, 1);
	return true;
}

// ---- P13: the Walk phase ----------------------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBApparitionWalkEnteredTest, "LastBell.Warden.Apparition.WalkPhaseFollowsHold", LB_TEST_FLAGS)
bool FLBApparitionWalkEnteredTest::RunTest(const FString& Parameters)
{
	const float In = 0.5f, Hold = 1.f, Out = 0.5f;
	FSim Sim;
	Sim.Stations = { MakeWalkStation(In, Hold, Out, 0.f) };
	Sim.bLookedAt = true;
	Sim.Start();

	TestTrue(TEXT("Reaches Hold"), Sim.TickUntil(ELBApparitionPhase::Hold));
	TestTrue(TEXT("Then Walk, not FadeOut"), Sim.TickUntil(ELBApparitionPhase::Walk, 5.f));
	TEST_ENUM(TEXT("In Walk"), Sim.Run.Phase, ELBApparitionPhase::Walk);
	TestEqual(TEXT("Walk runs at full alpha"), Sim.Run.Alpha, 1.f);

	// The path is not finished: it walks for as long as it takes, at full alpha, never fading.
	bool bAlphaOk = true;
	for (int32 i = 0; i < 60 * 30; ++i)
	{
		Sim.Tick();
		bAlphaOk &= Sim.Run.Alpha == 1.f;
	}
	TEST_ENUM(TEXT("Still walking after 30 s without a finished path"), Sim.Run.Phase, ELBApparitionPhase::Walk);
	TestTrue(TEXT("Alpha stays 1 the whole walk"), bAlphaOk);
	TestEqual(TEXT("Same station"), Sim.Run.Station, 0);
	TestEqual(TEXT("FadeIn was entered once"), Sim.FadeInEntries, 1);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBApparitionWalkFinishedTest, "LastBell.Warden.Apparition.WalkFinishedFadesOut", LB_TEST_FLAGS)
bool FLBApparitionWalkFinishedTest::RunTest(const FString& Parameters)
{
	const float Out = 0.5f;
	FSim Sim;
	Sim.Stations = { MakeWalkStation(0.2f, 0.2f, Out, 0.25f), MakeStation(0.2f, 0.2f, 0.2f, 0.f) };
	Sim.bLookedAt = true;
	Sim.Start();

	TestTrue(TEXT("Reaches Walk"), Sim.TickUntil(ELBApparitionPhase::Walk));
	for (int32 i = 0; i < 30; ++i)
	{
		Sim.Tick();
	}
	TEST_ENUM(TEXT("Walking"), Sim.Run.Phase, ELBApparitionPhase::Walk);

	// The actor reports the end of the path: FadeOut from alpha 1, on that very step.
	Sim.bWalkFinished = true;
	Sim.Tick();
	TEST_ENUM(TEXT("Path finished: FadeOut"), Sim.Run.Phase, ELBApparitionPhase::FadeOut);
	Sim.bWalkFinished = false;

	float PrevAlpha = 1.f;
	bool bFalling = true;
	int32 Ticks = 0;
	while (Sim.Run.Phase == ELBApparitionPhase::FadeOut && Ticks < 600)
	{
		Sim.Tick();
		bFalling &= Sim.Run.Alpha <= PrevAlpha;
		PrevAlpha = Sim.Run.Alpha;
		++Ticks;
	}
	TestTrue(TEXT("Alpha falls through the fade-out"), bFalling);
	TestTrue(FString::Printf(TEXT("The fade-out takes %d ticks, about %.0f"), Ticks, Out / Dt), FMath::Abs(Ticks - Out / Dt) <= 3.f);
	TEST_ENUM(TEXT("Then the gap"), Sim.Run.Phase, ELBApparitionPhase::Gap);
	TestEqual(TEXT("Hidden in the gap"), Sim.Run.Alpha, 0.f);

	// The next station is a plain one: it never walks.
	TestTrue(TEXT("Station 2 waits for the look"), Sim.TickUntil(ELBApparitionPhase::WaitForLook));
	TestEqual(TEXT("On station 2"), Sim.Run.Station, 1);
	TestTrue(TEXT("Station 2 fades in"), Sim.TickUntil(ELBApparitionPhase::FadeIn));
	bool bWalked = false;
	for (int32 i = 0; i < 60 * 5 && Sim.Run.Phase != ELBApparitionPhase::Done; ++i)
	{
		Sim.Tick();
		bWalked |= Sim.Run.Phase == ELBApparitionPhase::Walk;
	}
	TestFalse(TEXT("Station 2 has no path: no Walk phase"), bWalked);
	TEST_ENUM(TEXT("Done"), Sim.Run.Phase, ELBApparitionPhase::Done);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBApparitionWalkCutShortTest, "LastBell.Warden.Apparition.WalkCutShortByDistance", LB_TEST_FLAGS)
bool FLBApparitionWalkCutShortTest::RunTest(const FString& Parameters)
{
	// Too close during the walk: straight to FadeOut from alpha 1, however far along the path it was.
	{
		FSim Sim;
		Sim.Stations = { MakeWalkStation(0.2f, 0.2f, 0.5f, 0.f, 150.f) };
		Sim.bLookedAt = true;
		Sim.Distance = 1000.f;
		Sim.Start();
		TestTrue(TEXT("Reaches Walk"), Sim.TickUntil(ELBApparitionPhase::Walk));
		for (int32 i = 0; i < 20; ++i)
		{
			Sim.Tick();
		}
		TEST_ENUM(TEXT("Far away: still walking"), Sim.Run.Phase, ELBApparitionPhase::Walk);

		Sim.Distance = 100.f;
		Sim.Tick();
		TEST_ENUM(TEXT("Player within 150 cm: FadeOut"), Sim.Run.Phase, ELBApparitionPhase::FadeOut);
		Sim.Tick();
		TestTrue(TEXT("Falling from 1"), Sim.Run.Alpha < 1.f && Sim.Run.Alpha > 0.9f);
		TestTrue(TEXT("Then the run finishes"), Sim.TickUntil(ELBApparitionPhase::Done, 2.f));
	}

	// No minimum distance: a close player changes nothing.
	{
		FSim Sim;
		Sim.Stations = { MakeWalkStation(0.2f, 0.2f, 0.5f, 0.f, 0.f) };
		Sim.bLookedAt = true;
		Sim.Distance = 10.f;
		Sim.Start();
		TestTrue(TEXT("Reaches Walk"), Sim.TickUntil(ELBApparitionPhase::Walk));
		for (int32 i = 0; i < 120; ++i)
		{
			Sim.Tick();
		}
		TEST_ENUM(TEXT("MinPlayerDistance 0: a player at 10 cm does not stop the walk"), Sim.Run.Phase, ELBApparitionPhase::Walk);
	}

	// Too close during the hold: the existing rule (fade from the hold) wins, no Walk at all.
	{
		FSim Sim;
		Sim.Stations = { MakeWalkStation(0.2f, 1.f, 0.5f, 0.f, 150.f) };
		Sim.bLookedAt = true;
		Sim.Distance = 1000.f;
		Sim.Start();
		TestTrue(TEXT("Reaches Hold"), Sim.TickUntil(ELBApparitionPhase::Hold));
		Sim.Distance = 100.f;
		Sim.Tick();
		TEST_ENUM(TEXT("Too close during Hold: FadeOut, never Walk"), Sim.Run.Phase, ELBApparitionPhase::FadeOut);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBApparitionNoPathUnchangedTest, "LastBell.Warden.Apparition.StationWithoutPathHasNoWalk", LB_TEST_FLAGS)
bool FLBApparitionNoPathUnchangedTest::RunTest(const FString& Parameters)
{
	// Without a WalkPath the sequence is exactly the old one, even when the actor claims a finished walk.
	const float In = 1.f, Hold = 2.f, Out = 1.5f, Gap = 0.5f;
	FSim Sim;
	Sim.Stations = { MakeStation(In, Hold, Out, Gap) };
	Sim.ArmDelay = 0.25f;
	Sim.bLookedAt = true;
	Sim.bWalkFinished = true;
	Sim.Start();

	bool bWalked = false;
	float EntryTime = -1.f, DoneTime = -1.f;
	bool bHoldToFadeOut = true;
	ELBApparitionPhase Prev = ELBApparitionPhase::Idle;
	for (int32 i = 0; i < 60 * 20 && Sim.Run.Phase != ELBApparitionPhase::Done; ++i)
	{
		if (Sim.Tick())
		{
			EntryTime = Sim.Time;
		}
		bWalked |= Sim.Run.Phase == ELBApparitionPhase::Walk;
		if (Prev == ELBApparitionPhase::Hold && Sim.Run.Phase != ELBApparitionPhase::Hold)
		{
			bHoldToFadeOut &= Sim.Run.Phase == ELBApparitionPhase::FadeOut;
		}
		Prev = Sim.Run.Phase;
		if (Sim.Run.Phase == ELBApparitionPhase::Done)
		{
			DoneTime = Sim.Time;
		}
	}
	TestFalse(TEXT("Never enters Walk"), bWalked);
	TestTrue(TEXT("Hold goes straight to FadeOut"), bHoldToFadeOut);
	TEST_ENUM(TEXT("Done"), Sim.Run.Phase, ELBApparitionPhase::Done);
	TestTrue(FString::Printf(TEXT("Entry to Done takes %.3f s, the sum of the phases is %.3f s"), DoneTime - EntryTime, In + Hold + Out + Gap),
		FMath::Abs((DoneTime - EntryTime) - (In + Hold + Out + Gap)) <= 2.f * Dt + 0.001f);

	// The default station has an empty path and 110 cm/s.
	const FLBApparitionStation Default;
	TestEqual(TEXT("Default WalkPath is empty"), Default.WalkPath.Num(), 0);
	TestEqual(TEXT("Default WalkSpeed is 110"), Default.WalkSpeed, 110.f);
	TestEqual(TEXT("Phase name"), FString(LBApparition::PhaseName(ELBApparitionPhase::Walk)), FString(TEXT("Walk")));
	return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS

// =====================================================================================================================
// Functional tests
// =====================================================================================================================

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Editor.h"
#include "Tests/AutomationEditorCommon.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Character/LBCharacter.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "LBLog.h"

// Each test loads L_Test_Warden (the map the Warden functional tests use) and runs one PIE session. The tests build their own
// flat floor far below the level, so no level geometry gets between the player and the figure, and spawn their own
// ALBWardenApparition with SpawnActorDeferred (the placed instances in L_Monastery are not part of this). lb.Warden.Enabled is 0 for
// the session, so the map's Warden stays Dormant and hidden and cannot touch the player. The trigger is State.Test.Apparition,
// which nothing else reacts to. The Body and Glow have no meshes here: the code has to cope with that.

namespace
{
	const TCHAR* GApparitionMap = TEXT("/Game/LastBell/Maps/L_Test_Warden");
	const TCHAR* GTriggerTagName = TEXT("State.Test.Apparition");
	const TCHAR* GOtherTagName = TEXT("State.Test.Door1Open");

	constexpr float GFloorTopZ = -20000.f;
	const FVector GPlayerXY(0.0, 0.0, 0.0);
	const FVector GStation1(500.0, 0.0, GFloorTopZ);  // 500 cm ahead when the player faces +X
	const FVector GStation2(-500.0, 0.0, GFloorTopZ); // behind the player
	constexpr float GLookHeight = 200.f;

	// Short enough to keep the tests quick, long enough to be seen over a few frames.
	constexpr float GFadeIn = 0.2f;
	constexpr float GHold = 0.3f;
	constexpr float GFadeOut = 0.2f;
	constexpr float GGap = 0.1f;
	constexpr float GArmDelay = 0.1f;

	void Note(const FString& Text) { UE_LOG(LogLB, Display, TEXT("[Apparition] %s"), *Text); }

	struct FAppCtx
	{
		UWorld* W = nullptr;
		ALBCharacter* Pawn = nullptr;
		double Elapsed = 0.0; // game seconds since the step began
		int32 Frames = 0;
		bool bFirst = false;
	};

	struct FAppState
	{
		TWeakObjectPtr<ALBWardenApparition> Apparition;
		FGameplayTag Trigger;
		float AlphaSeen = 0.f;
		TWeakObjectPtr<AActor> Blocker;
		int32 WaitFrames = 0;
		// Walk test scratch.
		double WalkStartTime = 0.0;
		FVector LastLocation = FVector::ZeroVector;
		float MaxStep = 0.f;

		ALBWardenApparition* A() const { return Apparition.Get(); }
	};

	class FAppRunner : public IAutomationLatentCommand
	{
	public:
		using FStepFn = TFunction<bool(FAppCtx&)>;

		explicit FAppRunner(FAutomationTestBase* InTest)
			: S(MakeShared<FAppState>()), Test(InTest), WardenOff(false)
		{
		}

		void Add(const TCHAR* Name, FStepFn Fn, float WallTimeout = 30.f)
		{
			Steps.Add({ Name, WallTimeout, MoveTemp(Fn) });
		}

		virtual bool Update() override
		{
			if (bTearingDown)
			{
				return !LBPie::World() || (FPlatformTime::Seconds() - TeardownStart) > 30.0;
			}
			if (bAbort || StepIndex >= Steps.Num())
			{
				BeginTeardown();
				return false;
			}

			UWorld* W = LBPie::World();
			ALBCharacter* P = LBPie::Pawn();
			FStep& Step = Steps[StepIndex];
			if (!bEntered)
			{
				if (StepIndex > 0 && (!W || !P))
				{
					Test->AddError(FString::Printf(TEXT("Step '%s': PIE world or pawn is gone"), *Step.Name));
					bAbort = true;
					return false;
				}
				bEntered = true;
				Frames = 0;
				WallStart = FPlatformTime::Seconds();
				WorldStart = W ? W->GetTimeSeconds() : 0.0;
				ErrorsAtStart = ErrCount();
				Note(FString::Printf(TEXT("STEP %d begin: %s"), StepIndex + 1, *Step.Name));
			}

			FAppCtx Ctx;
			Ctx.W = W;
			Ctx.Pawn = P;
			Ctx.Elapsed = W ? W->GetTimeSeconds() - WorldStart : 0.0;
			Ctx.Frames = Frames;
			Ctx.bFirst = (Frames == 0);
			++Frames;

			const bool bDone = Step.Fn(Ctx);
			const bool bTimedOut = !bDone && (FPlatformTime::Seconds() - WallStart) > Step.Timeout;
			if (bTimedOut)
			{
				Test->AddError(FString::Printf(TEXT("Step '%s' timed out after %.0fs"), *Step.Name, Step.Timeout));
			}
			if (bDone || bTimedOut)
			{
				Note(FString::Printf(TEXT("STEP %d %s: %s"), StepIndex + 1, ErrCount() == ErrorsAtStart ? TEXT("PASS") : TEXT("FAIL"), *Step.Name));
				if (bTimedOut || ErrCount() != ErrorsAtStart)
				{
					// Later steps depend on this one: stop at the first failure.
					bAbort = true;
				}
				++StepIndex;
				bEntered = false;
			}
			return false;
		}

		TSharedRef<FAppState> S;

	private:
		struct FStep
		{
			FString Name;
			float Timeout;
			FStepFn Fn;
		};

		int32 ErrCount() const
		{
			FAutomationTestExecutionInfo Info;
			Test->GetExecutionInfo(Info);
			return Info.GetErrorTotal();
		}

		void BeginTeardown()
		{
			bTearingDown = true;
			TeardownStart = FPlatformTime::Seconds();
			if (GEditor && LBPie::World())
			{
				GEditor->RequestEndPlayMap();
			}
		}

		FAutomationTestBase* Test;
		LBPie::FWardenSwitch WardenOff;
		TArray<FStep> Steps;
		int32 StepIndex = 0;
		int32 Frames = 0;
		bool bEntered = false;
		bool bAbort = false;
		bool bTearingDown = false;
		double WallStart = 0.0;
		double WorldStart = 0.0;
		double TeardownStart = 0.0;
		int32 ErrorsAtStart = 0;
	};

	TSharedRef<FAppRunner> StartSession(FAutomationTestBase* Test)
	{
		TSharedRef<FAppRunner> Runner = MakeShared<FAppRunner>(Test);
		FAutomationEditorCommonUtils::LoadMap(GApparitionMap);
		FRequestPlaySessionParams PlayParams;
		PlayParams.WorldType = EPlaySessionWorldType::PlayInEditor;
		GEditor->RequestPlaySession(PlayParams);
		return Runner;
	}

	void Enqueue(const TSharedRef<FAppRunner>& Runner)
	{
		FAutomationTestFramework::Get().EnqueueLatentCommand(Runner);
	}

	float HalfHeight(const ALBCharacter* P) { return P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight(); }

	bool SpawnFloor(UWorld* W)
	{
		UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
		AStaticMeshActor* Floor = Cube ? W->SpawnActor<AStaticMeshActor>(FVector(0.f, 0.f, GFloorTopZ - 100.f), FRotator::ZeroRotator) : nullptr;
		if (!Floor)
		{
			return false;
		}
		Floor->SetMobility(EComponentMobility::Movable);
		Floor->GetStaticMeshComponent()->SetStaticMesh(Cube);
		Floor->SetActorScale3D(FVector(200.f, 60.f, 2.f));
		return true;
	}

	/** Stands the player on the floor at the origin, looking along +Y (at neither station). */
	void PlacePlayer(ALBCharacter* P)
	{
		P->SetActorLocationAndRotation(FVector(GPlayerXY.X, GPlayerXY.Y, GFloorTopZ + HalfHeight(P) + 0.1f), FRotator::ZeroRotator, false, nullptr, ETeleportType::TeleportPhysics);
		if (UCharacterMovementComponent* M = P->GetCharacterMovement())
		{
			M->StopMovementImmediately();
		}
		if (AController* C = P->GetController())
		{
			C->SetControlRotation(FRotator(0.f, 90.f, 0.f));
		}
	}

	void LookAway(ALBCharacter* P)
	{
		if (AController* C = P->GetController())
		{
			C->SetControlRotation(FRotator(0.f, 90.f, 0.f));
		}
	}

	/** Aims the view at the station's look point. */
	void LookAtStation(ALBCharacter* P, const FVector& Station)
	{
		const APlayerController* PC = Cast<APlayerController>(P->GetController());
		const FVector Eye = PC && PC->PlayerCameraManager ? PC->PlayerCameraManager->GetCameraLocation() : P->GetActorLocation() + FVector(0.0, 0.0, 64.0);
		if (AController* C = P->GetController())
		{
			C->SetControlRotation((Station + FVector(0.0, 0.0, GLookHeight) - Eye).Rotation());
		}
	}

	FLBApparitionStation MakeStation(const FVector& Location, float Hold = GHold)
	{
		FLBApparitionStation S;
		S.Location = Location;
		S.LookConeDegrees = 30.f;
		S.MinPlayerDistance = 150.f;
		S.FadeInSeconds = GFadeIn;
		S.HoldSeconds = Hold;
		S.FadeOutSeconds = GFadeOut;
		S.GapAfterSeconds = GGap;
		return S;
	}

	/** Spawns the apparition the way a placed one would be configured: deferred, so the tag and the stations are set before BeginPlay. */
	ALBWardenApparition* SpawnApparition(UWorld* W, const FGameplayTag& Trigger, const TArray<FLBApparitionStation>& Stations, bool bSkeletalFigure = false)
	{
		ALBWardenApparition* A = W->SpawnActorDeferred<ALBWardenApparition>(ALBWardenApparition::StaticClass(), FTransform::Identity, nullptr, nullptr, ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
		if (A)
		{
			A->TriggerTag = Trigger;
			A->ArmDelaySeconds = GArmDelay;
			A->Stations = Stations;
			A->GlowSizeCm = 300.f; // exercises the glow scale path; there is no mesh to see
		A->bUseSkeletalFigure = bSkeletalFigure;
			A->FinishSpawning(FTransform::Identity);
		}
		return A;
	}

	/** Adds the common start: PIE ready, floor and player, apparition spawned, player settled on the floor. */
	void AddSetup(FAppRunner& R, FAutomationTestBase* Test, const TArray<FLBApparitionStation>& Stations, bool bTagFirst, bool bSkeletalFigure = false)
	{
		const TSharedRef<FAppState> S = R.S;
		R.Add(TEXT("PIE ready, floor, player, apparition spawned"), [S, Test, Stations, bTagFirst, bSkeletalFigure](FAppCtx& C)
		{
			if (!LBPie::WorldReady() || C.Frames < 5)
			{
				return false;
			}
			S->Trigger = LBPie::Tag(GTriggerTagName);
			if (!Test->TestTrue(TEXT("State.Test.Apparition exists in the tag ini"), S->Trigger.IsValid()))
			{
				return true;
			}
			if (!Test->TestTrue(TEXT("Floor spawned"), SpawnFloor(C.W)))
			{
				return true;
			}
			PlacePlayer(C.Pawn);
			ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(C.W);
			if (!Test->TestNotNull(TEXT("World state subsystem"), State))
			{
				return true;
			}
			State->RemoveState(S->Trigger);
			if (bTagFirst)
			{
				State->AddState(S->Trigger);
			}
			ALBWardenApparition* A = SpawnApparition(C.W, S->Trigger, Stations, bSkeletalFigure);
			if (!Test->TestNotNull(TEXT("Apparition spawned"), A))
			{
				return true;
			}
			S->Apparition = A;
			Test->TestTrue(TEXT("Hidden at BeginPlay"), A->IsHidden());
			Test->TestEqual(TEXT("Alpha 0 at BeginPlay"), A->GetAlpha(), 0.f);
			Test->TestFalse(TEXT("Tick is off before the trigger"), A->IsActorTickEnabled());
			Test->TestNearlyEqual(TEXT("The Glow card is scaled to GlowSizeCm / 100"), static_cast<float>(A->GetGlow()->GetRelativeScale3D().X), 3.f);
			Test->TestEqual(TEXT("The skeletal Figure is visible only with bUseSkeletalFigure"), A->GetFigure()->IsVisible(), bSkeletalFigure);
			Test->TestEqual(TEXT("The static Body is visible only without bUseSkeletalFigure"), A->GetBody()->IsVisible(), !bSkeletalFigure);
			Test->TestEqual(TEXT("The Figure has no collision"), static_cast<int32>(A->GetFigure()->GetCollisionEnabled()), static_cast<int32>(ECollisionEnabled::NoCollision));
			Test->TestFalse(TEXT("The Figure casts no shadow"), A->GetFigure()->CastShadow);
			return true;
		});

		R.Add(TEXT("Settle on the floor"), [S](FAppCtx& C)
		{
			const UCharacterMovementComponent* M = C.Pawn->GetCharacterMovement();
			return C.Elapsed > 0.5 && M && M->IsMovingOnGround();
		});
	}

	/** True once the player has the figure's phase; reports a wrong phase as an error and a timeout is the runner's job. */
	bool PhaseIs(const FAppState& S, ELBApparitionPhase Phase)
	{
		return S.A() && S.A()->GetPhase() == Phase;
	}

	/** Steps for one station: fades in (checks facing and place), holds at 1, falls, and is gone. */
	void AddStationSteps(FAppRunner& R, FAutomationTestBase* Test, const TCHAR* Label, int32 Index, const FVector& Station, float ExpectedYaw)
	{
		const TSharedRef<FAppState> S = R.S;
		const FString Name(Label);
		R.Add(*(Name + TEXT(": look at it, it fades in at the station facing the player")), [S, Test, Station, ExpectedYaw, Index](FAppCtx& C)
		{
			ALBWardenApparition* A = S->A();
			if (!A)
			{
				Test->AddError(TEXT("Apparition is gone"));
				return true;
			}
			LookAtStation(C.Pawn, Station);
			if (A->GetAlpha() > 0.01f)
			{
				Test->TestEqual(TEXT("On the right station"), A->GetStationIndex(), Index);
				Test->TestTrue(TEXT("Visible once alpha is above 0"), !A->IsHidden());
				Test->TestTrue(TEXT("Standing at the station"), FVector::Dist(A->GetActorLocation(), Station) < 1.f);
				const float YawError = FMath::Abs(FMath::FindDeltaAngleDegrees(static_cast<float>(A->GetActorRotation().Yaw), ExpectedYaw));
				Test->TestTrue(FString::Printf(TEXT("Facing the player (yaw %.1f, expected %.0f)"), A->GetActorRotation().Yaw, ExpectedYaw), YawError < 3.f);
				Test->TestTrue(TEXT("Fading in"), A->GetPhase() == ELBApparitionPhase::FadeIn || A->GetPhase() == ELBApparitionPhase::Hold);
				Test->TestTrue(TEXT("Ticking while it runs"), A->IsActorTickEnabled());
				return true;
			}
			if (C.Elapsed > 5.0)
			{
				Test->AddError(FString::Printf(TEXT("Looking straight at station %d did not start the fade-in (phase %s)"), Index + 1, LBApparition::PhaseName(A->GetPhase())));
				return true;
			}
			return false;
		}, 15.f);

		R.Add(*(Name + TEXT(": alpha reaches 1 and holds")), [S, Test, Station](FAppCtx& C)
		{
			ALBWardenApparition* A = S->A();
			LookAtStation(C.Pawn, Station);
			if (A && A->GetAlpha() >= 0.999f)
			{
				Test->TestTrue(TEXT("Hold at full alpha"), A->GetPhase() == ELBApparitionPhase::Hold);
				Test->TestFalse(TEXT("Visible at full alpha"), A->IsHidden());
				return true;
			}
			if (C.Elapsed > 5.0)
			{
				Test->AddError(TEXT("Alpha never reached 1"));
				return true;
			}
			return false;
		}, 15.f);

		R.Add(*(Name + TEXT(": alpha falls")), [S, Test, Station](FAppCtx& C)
		{
			ALBWardenApparition* A = S->A();
			LookAtStation(C.Pawn, Station);
			if (A && A->GetAlpha() < 0.9f)
			{
				Test->TestTrue(TEXT("Falling in FadeOut"), A->GetPhase() == ELBApparitionPhase::FadeOut);
				return true;
			}
			if (C.Elapsed > 5.0)
			{
				Test->AddError(TEXT("Alpha never fell after the hold"));
				return true;
			}
			return false;
		}, 15.f);

		R.Add(*(Name + TEXT(": gone")), [S, Test, Station](FAppCtx& C)
		{
			ALBWardenApparition* A = S->A();
			LookAtStation(C.Pawn, Station);
			if (A && A->GetAlpha() <= 0.f)
			{
				Test->TestTrue(TEXT("Hidden at alpha 0"), A->IsHidden());
				return true;
			}
			if (C.Elapsed > 5.0)
			{
				Test->AddError(TEXT("Alpha never reached 0"));
				return true;
			}
			return false;
		}, 15.f);
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBApparitionTwoStationSequenceTest, "LastBell.Functional.Warden.Apparition.TwoStationSequence",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBApparitionTwoStationSequenceTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAppRunner> R = StartSession(this);
	const TSharedRef<FAppState> S = R->S;
	FAutomationTestBase* Test = this;
	AddSetup(*R, Test, { MakeStation(GStation1), MakeStation(GStation2) }, false);

	R->Add(TEXT("Tag added, looking away: arms, then waits hidden"), [S, Test](FAppCtx& C)
	{
		ALBWardenApparition* A = S->A();
		if (C.bFirst)
		{
			LookAway(C.Pawn);
			ULBWorldStateSubsystem::Get(C.W)->AddState(S->Trigger);
			Test->TestTrue(TEXT("Tag added: arm delay running"), A->GetPhase() == ELBApparitionPhase::ArmDelay);
			Test->TestTrue(TEXT("Tag added: ticking"), A->IsActorTickEnabled());
		}
		if (C.Elapsed < 1.0)
		{
			Test->TestTrue(TEXT("Hidden while it waits"), A->IsHidden());
			return false;
		}
		Test->TestTrue(TEXT("Waiting for the look after the arm delay"), A->GetPhase() == ELBApparitionPhase::WaitForLook);
		Test->TestEqual(TEXT("Alpha 0 while unseen"), A->GetAlpha(), 0.f);
		Test->TestTrue(TEXT("Hidden while unseen"), A->IsHidden());
		return true;
	});

	// The player stands at the origin; station 1 is at +X (the figure turns to face -X, yaw 180), station 2 at -X (yaw 0).
	AddStationSteps(*R, Test, TEXT("Station 1"), 0, GStation1, 180.f);

	R->Add(TEXT("Still looking at station 1: station 2 stays hidden"), [S, Test](FAppCtx& C)
	{
		ALBWardenApparition* A = S->A();
		LookAtStation(C.Pawn, GStation1);
		if (C.Elapsed < 0.6)
		{
			return false;
		}
		Test->TestEqual(TEXT("On station 2"), A->GetStationIndex(), 1);
		Test->TestTrue(TEXT("Waiting for the second look"), A->GetPhase() == ELBApparitionPhase::WaitForLook);
		Test->TestEqual(TEXT("Alpha 0"), A->GetAlpha(), 0.f);
		Test->TestTrue(TEXT("Hidden"), A->IsHidden());
		return true;
	});

	AddStationSteps(*R, Test, TEXT("Station 2"), 1, GStation2, 0.f);

	R->Add(TEXT("Done: hidden, tick off, and it stays that way"), [S, Test](FAppCtx& C)
	{
		ALBWardenApparition* A = S->A();
		if (C.Elapsed < 0.2)
		{
			return false;
		}
		Test->TestTrue(TEXT("Done"), A->GetPhase() == ELBApparitionPhase::Done);
		Test->TestTrue(TEXT("Hidden"), A->IsHidden());
		Test->TestEqual(TEXT("Alpha 0"), A->GetAlpha(), 0.f);
		Test->TestFalse(TEXT("Tick is off again"), A->IsActorTickEnabled());
		return true;
	});

	R->Add(TEXT("Looking at the station again does nothing"), [S, Test](FAppCtx& C)
	{
		ALBWardenApparition* A = S->A();
		LookAtStation(C.Pawn, GStation1);
		if (C.Elapsed < 0.7)
		{
			Test->TestTrue(TEXT("Hidden"), A->IsHidden());
			return false;
		}
		Test->TestTrue(TEXT("Still Done"), A->GetPhase() == ELBApparitionPhase::Done);
		Test->TestFalse(TEXT("Tick still off"), A->IsActorTickEnabled());
		return true;
	});

	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBApparitionTagAlreadyPresentTest, "LastBell.Functional.Warden.Apparition.TagAlreadyPresentStaysDone",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBApparitionTagAlreadyPresentTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAppRunner> R = StartSession(this);
	const TSharedRef<FAppState> S = R->S;
	FAutomationTestBase* Test = this;
	AddSetup(*R, Test, { MakeStation(GStation1) }, true);

	R->Add(TEXT("Tag was already there: Done at BeginPlay, hidden, not ticking"), [S, Test](FAppCtx& C)
	{
		ALBWardenApparition* A = S->A();
		Test->TestTrue(TEXT("Done"), A->GetPhase() == ELBApparitionPhase::Done);
		Test->TestTrue(TEXT("Hidden"), A->IsHidden());
		Test->TestFalse(TEXT("Tick off"), A->IsActorTickEnabled());
		return true;
	});

	R->Add(TEXT("Looking at the station and adding other tags does nothing"), [S, Test](FAppCtx& C)
	{
		ALBWardenApparition* A = S->A();
		LookAtStation(C.Pawn, GStation1);
		if (C.Frames == 20)
		{
			if (ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(C.W))
			{
				const FGameplayTag Other = LBPie::Tag(GOtherTagName);
				Test->TestTrue(TEXT("The other test tag exists"), Other.IsValid());
				State->AddState(Other);
			}
		}
		Test->TestTrue(TEXT("Hidden throughout"), A->IsHidden());
		Test->TestEqual(TEXT("Alpha 0 throughout"), A->GetAlpha(), 0.f);
		if (C.Elapsed < 1.0)
		{
			return false;
		}
		Test->TestTrue(TEXT("Still Done"), A->GetPhase() == ELBApparitionPhase::Done);
		Test->TestFalse(TEXT("Tick still off"), A->IsActorTickEnabled());
		return true;
	});

	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBApparitionStateReplacedTest, "LastBell.Functional.Warden.Apparition.StateReplacedMidRunStops",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBApparitionStateReplacedTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAppRunner> R = StartSession(this);
	const TSharedRef<FAppState> S = R->S;
	FAutomationTestBase* Test = this;
	// A long hold: the test replaces the world state while the figure is standing there.
	AddSetup(*R, Test, { MakeStation(GStation1, 30.f) }, false);

	R->Add(TEXT("Tag added, looking at the station: reaches Hold"), [S, Test](FAppCtx& C)
	{
		ALBWardenApparition* A = S->A();
		LookAtStation(C.Pawn, GStation1);
		if (C.bFirst)
		{
			ULBWorldStateSubsystem::Get(C.W)->AddState(S->Trigger);
		}
		if (A->GetAlpha() >= 0.999f)
		{
			Test->TestTrue(TEXT("In Hold"), A->GetPhase() == ELBApparitionPhase::Hold);
			Test->TestFalse(TEXT("Visible"), A->IsHidden());
			return true;
		}
		if (C.Elapsed > 5.0)
		{
			Test->AddError(TEXT("Never reached Hold"));
			return true;
		}
		return false;
	}, 15.f);

	R->Add(TEXT("ReplaceState without the tag: hidden, Idle, not ticking"), [S, Test](FAppCtx& C)
	{
		ALBWardenApparition* A = S->A();
		ULBWorldStateSubsystem::Get(C.W)->ReplaceState(FGameplayTagContainer());
		Test->TestTrue(TEXT("Hidden"), A->IsHidden());
		Test->TestEqual(TEXT("Alpha 0"), A->GetAlpha(), 0.f);
		Test->TestTrue(TEXT("Idle"), A->GetPhase() == ELBApparitionPhase::Idle);
		Test->TestFalse(TEXT("Tick off"), A->IsActorTickEnabled());
		return true;
	});

	R->Add(TEXT("Idle: nothing happens by itself"), [S, Test](FAppCtx& C)
	{
		ALBWardenApparition* A = S->A();
		LookAtStation(C.Pawn, GStation1);
		Test->TestTrue(TEXT("Hidden"), A->IsHidden());
		if (C.Elapsed < 0.5)
		{
			return false;
		}
		Test->TestTrue(TEXT("Still Idle"), A->GetPhase() == ELBApparitionPhase::Idle);
		return true;
	});

	R->Add(TEXT("Tag added again: it runs again"), [S, Test](FAppCtx& C)
	{
		ALBWardenApparition* A = S->A();
		LookAtStation(C.Pawn, GStation1);
		if (C.bFirst)
		{
			ULBWorldStateSubsystem::Get(C.W)->AddState(S->Trigger);
		}
		if (A->GetAlpha() > 0.01f)
		{
			Test->TestFalse(TEXT("Visible"), A->IsHidden());
			Test->TestTrue(TEXT("Running (FadeIn or Hold)"), A->GetPhase() == ELBApparitionPhase::FadeIn || A->GetPhase() == ELBApparitionPhase::Hold);
			return true;
		}
		if (C.Elapsed > 5.0)
		{
			Test->AddError(TEXT("It did not run again after the tag was re-added"));
			return true;
		}
		return false;
	}, 15.f);

	R->Add(TEXT("ReplaceState with the tag: hidden, Done"), [S, Test](FAppCtx& C)
	{
		ALBWardenApparition* A = S->A();
		FGameplayTagContainer WithTag;
		WithTag.AddTag(S->Trigger);
		ULBWorldStateSubsystem::Get(C.W)->ReplaceState(WithTag);
		Test->TestTrue(TEXT("Hidden"), A->IsHidden());
		Test->TestEqual(TEXT("Alpha 0"), A->GetAlpha(), 0.f);
		Test->TestTrue(TEXT("Done"), A->GetPhase() == ELBApparitionPhase::Done);
		Test->TestFalse(TEXT("Tick off"), A->IsActorTickEnabled());
		return true;
	});

	R->Add(TEXT("Done stays done"), [S, Test](FAppCtx& C)
	{
		ALBWardenApparition* A = S->A();
		LookAtStation(C.Pawn, GStation1);
		Test->TestTrue(TEXT("Hidden"), A->IsHidden());
		if (C.Elapsed < 0.7)
		{
			return false;
		}
		Test->TestTrue(TEXT("Still Done"), A->GetPhase() == ELBApparitionPhase::Done);
		return true;
	});

	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBApparitionBlockedViewTest, "LastBell.Functional.Warden.Apparition.BlockedViewStaysHidden",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBApparitionBlockedViewTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAppRunner> R = StartSession(this);
	const TSharedRef<FAppState> S = R->S;
	FAutomationTestBase* Test = this;
	AddSetup(*R, Test, { MakeStation(GStation1) }, false);

	// The player looks straight at the look point, so the cone test passes on every frame; only the line of sight can keep it hidden.
	R->Add(TEXT("A wall between the camera and the look point: it stays in WaitForLook, hidden, for over a second"), [S, Test](FAppCtx& C)
	{
		ALBWardenApparition* A = S->A();
		LookAtStation(C.Pawn, GStation1);
		const APlayerController* PC = Cast<APlayerController>(C.Pawn->GetController());
		const APlayerCameraManager* Camera = PC ? PC->PlayerCameraManager.Get() : nullptr;
		if (!Test->TestNotNull(TEXT("Camera manager"), Camera))
		{
			return true;
		}
		const FVector Eye = Camera->GetCameraLocation();
		const FVector LookPoint = GStation1 + FVector(0.0, 0.0, GLookHeight);

		if (C.bFirst)
		{
			// 20 x 400 x 400 cm, half way along the line of sight. Built from the engine cube at runtime: no asset references.
			UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
			AStaticMeshActor* Wall = Cube ? C.W->SpawnActor<AStaticMeshActor>((Eye + LookPoint) * 0.5, FRotator::ZeroRotator) : nullptr;
			if (!Test->TestNotNull(TEXT("Blocking wall spawned"), Wall))
			{
				return true;
			}
			Wall->SetMobility(EComponentMobility::Movable);
			Wall->GetStaticMeshComponent()->SetStaticMesh(Cube);
			Wall->SetActorScale3D(FVector(0.2f, 4.f, 4.f));
			S->Blocker = Wall;
			S->WaitFrames = 0;

			// The wall really blocks Visibility, and the first thing the view ray meets is the wall: neither the pawn nor the
			// apparition is in the way (the query ignores them, as IsLookedAt does).
			FCollisionQueryParams Params(SCENE_QUERY_STAT(LBApparitionTestWall), false, A);
			Params.AddIgnoredActor(C.Pawn);
			FHitResult Hit;
			const bool bHit = C.W->LineTraceSingleByChannel(Hit, Eye, LookPoint, ECC_Visibility, Params);
			Test->TestTrue(TEXT("The view ray from the camera to the look point hits something"), bHit);
			Test->TestTrue(FString::Printf(TEXT("...and it is the wall, not the pawn (hit %s)"), *GetNameSafe(Hit.GetActor())), bHit && Hit.GetActor() == Wall);

			ULBWorldStateSubsystem::Get(C.W)->AddState(S->Trigger);
			Note(FString::Printf(TEXT("wall at %s between eye %s and look point %s"), *Wall->GetActorLocation().ToCompactString(), *Eye.ToCompactString(), *LookPoint.ToCompactString()));
			return false;
		}

		// Guard: the view really is on the look point (so only the wall explains staying hidden).
		const FVector ViewDir = Camera->GetCameraRotation().Vector();
		const float OffAxisDeg = FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(static_cast<float>(FVector::DotProduct(ViewDir, (LookPoint - Eye).GetSafeNormal())), -1.f, 1.f)));
		if (C.Frames > 5)
		{
			Test->TestTrue(FString::Printf(TEXT("The view is on the look point (%.1f deg off)"), OffAxisDeg), OffAxisDeg < 5.f);
		}

		Test->TestTrue(TEXT("Hidden while the view is blocked"), A->IsHidden());
		Test->TestEqual(TEXT("Alpha stays 0 while the view is blocked"), A->GetAlpha(), 0.f);
		Test->TestTrue(TEXT("Never enters FadeIn while the view is blocked"), A->GetPhase() == ELBApparitionPhase::ArmDelay || A->GetPhase() == ELBApparitionPhase::WaitForLook);
		if (A->GetPhase() == ELBApparitionPhase::WaitForLook)
		{
			++S->WaitFrames;
		}
		if (C.Elapsed < 1.5)
		{
			return false;
		}
		// 1.5 s after the tag, less the 0.1 s arm delay: well over a second spent waiting with the view on the point.
		Test->TestTrue(TEXT("Waiting for the look, not started"), A->GetPhase() == ELBApparitionPhase::WaitForLook);
		Test->TestTrue(FString::Printf(TEXT("It waited in WaitForLook for many frames (%d)"), S->WaitFrames), S->WaitFrames > 20);
		return true;
	});

	R->Add(TEXT("Wall removed: it starts fading in"), [S, Test](FAppCtx& C)
	{
		ALBWardenApparition* A = S->A();
		LookAtStation(C.Pawn, GStation1);
		if (C.bFirst)
		{
			if (AActor* Wall = S->Blocker.Get())
			{
				Wall->Destroy();
			}
			Test->TestTrue(TEXT("Still waiting in WaitForLook when the wall goes"), A->GetPhase() == ELBApparitionPhase::WaitForLook);
			return false;
		}
		if (A->GetAlpha() > 0.01f)
		{
			Test->TestFalse(TEXT("Visible once alpha is above 0"), A->IsHidden());
			Test->TestTrue(TEXT("Fading in (or already holding)"), A->GetPhase() == ELBApparitionPhase::FadeIn || A->GetPhase() == ELBApparitionPhase::Hold);
			Test->TestEqual(TEXT("On station 1"), A->GetStationIndex(), 0);
			Note(FString::Printf(TEXT("fading in %.2fs after the wall was removed"), C.Elapsed));
			return true;
		}
		if (C.Elapsed > 3.0)
		{
			Test->AddError(FString::Printf(TEXT("Removing the wall did not start the fade-in (phase %s): is the pawn counted as a blocker?"), LBApparition::PhaseName(A->GetPhase())));
			return true;
		}
		return false;
	}, 15.f);

	Enqueue(R);
	return true;
}

// P13: a station with a WalkPath. The figure fades in, holds, walks the path (no mesh needed: the actor's location is the walk), and
// only then fades out and finishes at the last point. WalkSpeed 400 cm/s over 300 + 300 + 600 cm is 3 s.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBApparitionWalkPathTest, "LastBell.Functional.Warden.Apparition.WalkPathThenFade",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBApparitionWalkPathTest::RunTest(const FString& Parameters)
{
	const FVector P0(500.0, 300.0, GFloorTopZ);
	const FVector P1(800.0, 300.0, GFloorTopZ);
	const FVector P2(800.0, -300.0, GFloorTopZ);
	constexpr float WalkSpeed = 400.f;
	const float ExpectedWalkSeconds = (static_cast<float>(FVector::Dist(GStation1, P0) + FVector::Dist(P0, P1) + FVector::Dist(P1, P2))) / WalkSpeed;

	FLBApparitionStation Station = MakeStation(GStation1);
	Station.WalkPath = { P0, P1, P2 };
	Station.WalkSpeed = WalkSpeed;

	TSharedRef<FAppRunner> R = StartSession(this);
	const TSharedRef<FAppState> S = R->S;
	FAutomationTestBase* Test = this;
	AddSetup(*R, Test, { Station }, false, false);

	R->Add(TEXT("Tag added, looking at the station: it fades in at the station"), [S, Test, Station](FAppCtx& C)
	{
		ALBWardenApparition* A = S->A();
		if (C.bFirst)
		{
			ULBWorldStateSubsystem::Get(C.W)->AddState(S->Trigger);
		}
		LookAtStation(C.Pawn, Station.Location);
		if (A->GetAlpha() > 0.01f)
		{
			Test->TestTrue(TEXT("Standing at the station when it appears"), FVector::Dist(A->GetActorLocation(), Station.Location) < 1.f);
			return true;
		}
		if (C.Elapsed > 5.0)
		{
			Test->AddError(TEXT("The fade-in never started"));
			return true;
		}
		return false;
	}, 15.f);

	R->Add(TEXT("Hold ends: the walk begins at full alpha"), [S, Test, Station](FAppCtx& C)
	{
		ALBWardenApparition* A = S->A();
		LookAtStation(C.Pawn, Station.Location);
		if (A->GetPhase() == ELBApparitionPhase::Walk)
		{
			Test->TestEqual(TEXT("Walking at full alpha"), A->GetAlpha(), 1.f);
			Test->TestFalse(TEXT("Visible while walking"), A->IsHidden());
			S->WalkStartTime = C.W->GetTimeSeconds();
			S->LastLocation = A->GetActorLocation();
			S->MaxStep = 0.f;
			return true;
		}
		Test->TestTrue(FString::Printf(TEXT("Only FadeIn or Hold before the walk (phase %s)"), LBApparition::PhaseName(A->GetPhase())),
			A->GetPhase() == ELBApparitionPhase::FadeIn || A->GetPhase() == ELBApparitionPhase::Hold);
		if (C.Elapsed > 5.0)
		{
			Test->AddError(TEXT("The Walk phase never began"));
			return true;
		}
		return false;
	}, 15.f);

	R->Add(TEXT("Walks the path at WalkSpeed and ends on the last point"), [S, Test, Station, P1, P2, ExpectedWalkSeconds](FAppCtx& C)
	{
		ALBWardenApparition* A = S->A();
		LookAtStation(C.Pawn, Station.Location);
		const FVector Here = A->GetActorLocation();
		S->MaxStep = FMath::Max(S->MaxStep, static_cast<float>(FVector::Dist(Here, S->LastLocation)));
		S->LastLocation = Here;

		if (A->GetPhase() == ELBApparitionPhase::Walk)
		{
			Test->TestEqual(TEXT("Alpha stays 1 during the walk"), A->GetAlpha(), 1.f);
			if (C.Elapsed > ExpectedWalkSeconds + 3.f)
			{
				Test->AddError(FString::Printf(TEXT("Still walking after %.1f s (expected %.1f s) at %s"), C.Elapsed, ExpectedWalkSeconds, *Here.ToCompactString()));
				return true;
			}
			return false;
		}

		// The first frame out of Walk: FadeOut, on the last point, after the right time, facing along the last leg.
		Test->TestTrue(FString::Printf(TEXT("The walk ends in FadeOut (phase %s)"), LBApparition::PhaseName(A->GetPhase())), A->GetPhase() == ELBApparitionPhase::FadeOut);
		Test->TestTrue(FString::Printf(TEXT("On the last point (%.2f cm off)"), FVector::Dist(Here, P2)), FVector::Dist(Here, P2) < 1.f);
		const double WalkSeconds = C.W->GetTimeSeconds() - S->WalkStartTime;
		Test->TestTrue(FString::Printf(TEXT("The walk took %.2f s, expected %.2f s"), WalkSeconds, ExpectedWalkSeconds), FMath::Abs(WalkSeconds - ExpectedWalkSeconds) < 0.4);
		const float LastLegYaw = static_cast<float>((P2 - P1).Rotation().Yaw);
		const float YawError = FMath::Abs(FMath::FindDeltaAngleDegrees(static_cast<float>(A->GetActorRotation().Yaw), LastLegYaw));
		Test->TestTrue(FString::Printf(TEXT("Facing along the last leg (yaw %.1f, expected %.1f)"), A->GetActorRotation().Yaw, LastLegYaw), YawError < 10.f);
		Note(FString::Printf(TEXT("walk finished in %.2f s (expected %.2f), biggest single-frame step %.1f cm"), WalkSeconds, ExpectedWalkSeconds, S->MaxStep));
		return true;
	}, 30.f);

	R->Add(TEXT("It fades out where it stopped, then the run is done"), [S, Test, Station, P2](FAppCtx& C)
	{
		ALBWardenApparition* A = S->A();
		LookAtStation(C.Pawn, Station.Location);
		Test->TestTrue(TEXT("Stays on the last point while fading"), FVector::Dist(A->GetActorLocation(), P2) < 1.f);
		if (A->GetPhase() == ELBApparitionPhase::Done)
		{
			Test->TestTrue(TEXT("Hidden when done"), A->IsHidden());
			Test->TestEqual(TEXT("Alpha 0 when done"), A->GetAlpha(), 0.f);
			Test->TestFalse(TEXT("Tick is off when done"), A->IsActorTickEnabled());
			return true;
		}
		Test->TestTrue(FString::Printf(TEXT("FadeOut, gap or done after the walk (phase %s)"), LBApparition::PhaseName(A->GetPhase())),
			A->GetPhase() == ELBApparitionPhase::FadeOut || A->GetPhase() == ELBApparitionPhase::Gap);
		if (C.Elapsed > 4.0)
		{
			Test->AddError(TEXT("The run never finished after the walk"));
			return true;
		}
		return false;
	}, 15.f);

	Enqueue(R);
	return true;
}

// P13: the walk is cut short when the player comes within MinPlayerDistance of the figure.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBApparitionWalkCutShortFunctionalTest, "LastBell.Functional.Warden.Apparition.WalkCutShortByPlayer",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBApparitionWalkCutShortFunctionalTest::RunTest(const FString& Parameters)
{
	// A long path along +Y at X = 500: the player (at the origin) can step up to the figure.
	const FVector P0(500.0, 4000.0, GFloorTopZ);
	FLBApparitionStation Station = MakeStation(GStation1);
	Station.WalkPath = { P0 };
	Station.WalkSpeed = 100.f;

	TSharedRef<FAppRunner> R = StartSession(this);
	const TSharedRef<FAppState> S = R->S;
	FAutomationTestBase* Test = this;
	AddSetup(*R, Test, { Station }, false, false);

	R->Add(TEXT("Walking away from the station"), [S, Test, Station](FAppCtx& C)
	{
		ALBWardenApparition* A = S->A();
		if (C.bFirst)
		{
			ULBWorldStateSubsystem::Get(C.W)->AddState(S->Trigger);
		}
		if (A->GetPhase() == ELBApparitionPhase::Walk && FVector::DistXY(A->GetActorLocation(), Station.Location) > 100.0)
		{
			return true;
		}
		LookAtStation(C.Pawn, Station.Location);
		if (C.Elapsed > 8.0)
		{
			Test->AddError(FString::Printf(TEXT("It never started walking (phase %s)"), LBApparition::PhaseName(A->GetPhase())));
			return true;
		}
		return false;
	}, 20.f);

	R->Add(TEXT("The player steps within 150 cm of it: the walk ends early"), [S, Test, P0](FAppCtx& C)
	{
		ALBWardenApparition* A = S->A();
		if (C.bFirst)
		{
			// Teleport next to the figure (100 cm away).
			const FVector Figure = A->GetActorLocation();
			C.Pawn->SetActorLocation(FVector(Figure.X - 100.0, Figure.Y, Figure.Z + HalfHeight(C.Pawn) + 1.f), false, nullptr, ETeleportType::TeleportPhysics);
			S->LastLocation = Figure;
			return false;
		}
		if (A->GetPhase() != ELBApparitionPhase::Walk)
		{
			Test->TestTrue(FString::Printf(TEXT("Cut short: FadeOut (phase %s)"), LBApparition::PhaseName(A->GetPhase())),
				A->GetPhase() == ELBApparitionPhase::FadeOut || A->GetPhase() == ELBApparitionPhase::Gap || A->GetPhase() == ELBApparitionPhase::Done);
			Test->TestTrue(FString::Printf(TEXT("It stopped where it was (%.1f cm on)"), FVector::Dist(A->GetActorLocation(), S->LastLocation)), FVector::Dist(A->GetActorLocation(), S->LastLocation) < 30.f);
			Test->TestTrue(TEXT("Not at the end of the path"), FVector::Dist(A->GetActorLocation(), P0) > 500.f);
			return true;
		}
		if (C.Elapsed > 2.0)
		{
			Test->AddError(TEXT("The walk went on with the player standing next to the figure"));
			return true;
		}
		return false;
	}, 15.f);

	Enqueue(R);
	return true;
}

// P13: bUseSkeletalFigure swaps the static Body for the skeletal Figure.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBApparitionSkeletalFigureTest, "LastBell.Functional.Warden.Apparition.SkeletalFigureReplacesBody",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBApparitionSkeletalFigureTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAppRunner> R = StartSession(this);
	FAutomationTestBase* Test = this;
	// AddSetup asserts the Figure/Body visibility for the flag it was given (true here); then the first station runs normally.
	AddSetup(*R, Test, { MakeStation(GStation1) }, false, true);
	R->Add(TEXT("Tag added: runs"), [S = R->S, Test](FAppCtx& C)
	{
		if (C.bFirst)
		{
			ULBWorldStateSubsystem::Get(C.W)->AddState(S->Trigger);
		}
		LookAtStation(C.Pawn, GStation1);
		ALBWardenApparition* A = S->A();
		if (A->GetAlpha() > 0.5f)
		{
			Test->TestTrue(TEXT("Figure is the visible figure while it shows"), A->GetFigure()->IsVisible());
			Test->TestFalse(TEXT("Body stays hidden while it shows"), A->GetBody()->IsVisible());
			return true;
		}
		if (C.Elapsed > 5.0)
		{
			Test->AddError(TEXT("The fade-in never reached 0.5"));
			return true;
		}
		return false;
	}, 15.f);
	Enqueue(R);
	return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
