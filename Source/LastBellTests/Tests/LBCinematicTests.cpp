#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

#include "Cinematics/LBCineAuthoringLibrary.h"
#include "Cinematics/LBCinematicLogic.h"
#include "LevelSequence.h"
#include "MovieScene.h"
#include "Tracks/MovieSceneCameraCutTrack.h"
#include "UObject/StrongObjectPtr.h"

// P17-1 pure-logic unit tests of the cinematic markers, the skip, the easing, the bell swing and the credits speed
// (LastBell.Cine.*). The subsystem, the widget and the PIE behaviour are in LBCinematicFunctionalTests.cpp.

#define LB_CINE_TEST_FLAGS (EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

namespace LBCineUnitTest
{
	FLBCineMarker At(double Seconds, const TCHAR* Label)
	{
		FLBCineMarker Marker;
		Marker.Seconds = Seconds;
		FString Error;
		const bool bOk = LBCinematicLogic::ParseMarker(Label, Marker, Error);
		check(bOk);
		return Marker;
	}

	/** Fires through a list of steps at the given times and returns the labels in firing order. */
	TArray<FString> Run(const TArray<FLBCineMarker>& Sorted, TBitArray<>& Fired, double& Prev, const TArray<double>& Times)
	{
		TArray<FString> Out;
		for (const double Time : Times)
		{
			TArray<int32> Indices;
			LBCinematicLogic::MarkersToFire(Sorted, Prev, Time, Fired, Indices);
			for (const int32 Index : Indices)
			{
				Out.Add(Sorted[Index].Label);
			}
			Prev = FMath::Max(Prev, Time);
		}
		return Out;
	}
}

// =====================================================================================================================
// ParseMarkers
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBCineParseMarkersTest, "LastBell.Cine.ParseMarkers", LB_CINE_TEST_FLAGS)
bool FLBCineParseMarkersTest::RunTest(const FString& Parameters)
{
	using namespace LBCinematicLogic;
	FLBCineMarker M;
	FString Error;

	TestTrue(TEXT("card"), ParseMarker(TEXT("card:Intro_1"), M, Error));
	TestTrue(TEXT("card kind"), M.Kind == ELBCineMarkerKind::Card);
	TestEqual(TEXT("card id"), M.Name, FName(TEXT("Intro_1")));
	TestFalse(TEXT("not a must marker"), M.bMust);

	TestTrue(TEXT("must tag"), ParseMarker(TEXT("!tag:State.Event.Arrival"), M, Error));
	TestTrue(TEXT("tag kind"), M.Kind == ELBCineMarkerKind::Tag);
	TestTrue(TEXT("'!' makes a must marker"), M.bMust);
	TestTrue(TEXT("the tag resolved"), M.Tag.IsValid() && M.Tag.ToString() == TEXT("State.Event.Arrival"));

	TestTrue(TEXT("bell"), ParseMarker(TEXT("bell:5x1"), M, Error));
	TestTrue(TEXT("bell kind"), M.Kind == ELBCineMarkerKind::Bell);
	TestEqual(TEXT("bell stage"), M.Stage, 5);
	TestEqual(TEXT("bell strikes"), M.Strikes, 1);

	TestTrue(TEXT("strike with brightness"), ParseMarker(TEXT("strike:LB_StrikeTarget_Tower,0.8"), M, Error));
	TestTrue(TEXT("strike kind"), M.Kind == ELBCineMarkerKind::Strike);
	TestEqual(TEXT("strike actor tag"), M.Name, FName(TEXT("LB_StrikeTarget_Tower")));
	TestNearlyEqual(TEXT("strike brightness"), M.Value, 0.8f);
	TestTrue(TEXT("strike without brightness"), ParseMarker(TEXT("strike:LB_StrikeTarget_Tower"), M, Error));
	TestTrue(TEXT("...uses the default"), M.Value < 0.f);

	TestTrue(TEXT("flash"), ParseMarker(TEXT("flash:0.9"), M, Error));
	TestTrue(TEXT("flash kind"), M.Kind == ELBCineMarkerKind::Flash);
	TestNearlyEqual(TEXT("flash brightness"), M.Value, 0.9f);

	TestTrue(TEXT("look with seconds"), ParseMarker(TEXT("look:LB_Cine_Warden,1.2"), M, Error));
	TestTrue(TEXT("look kind"), M.Kind == ELBCineMarkerKind::Look);
	TestNearlyEqual(TEXT("look seconds"), M.Value, 1.2f);
	TestTrue(TEXT("look without seconds"), ParseMarker(TEXT("look:LB_Cine_StairTop"), M, Error));
	TestTrue(TEXT("...uses the default"), M.Value < 0.f);

	TestTrue(TEXT("mark"), ParseMarker(TEXT("mark:LB_Cine_FinaleMark,1.5"), M, Error));
	TestTrue(TEXT("mark kind"), M.Kind == ELBCineMarkerKind::Mark);
	TestNearlyEqual(TEXT("mark seconds"), M.Value, 1.5f);

	TestTrue(TEXT("lock Look"), ParseMarker(TEXT("lock:Look"), M, Error));
	TestTrue(TEXT("lock Look value"), M.Kind == ELBCineMarkerKind::Lock && M.Lock == ELBInputLock::Look);
	TestTrue(TEXT("lock Full"), ParseMarker(TEXT("lock:Full"), M, Error) && M.Lock == ELBInputLock::Full);
	TestTrue(TEXT("!lock None"), ParseMarker(TEXT("!lock:None"), M, Error) && M.Lock == ELBInputLock::None && M.bMust);

	TestTrue(TEXT("skip 1"), ParseMarker(TEXT("skip:1"), M, Error) && M.Kind == ELBCineMarkerKind::Skip && M.bFlag);
	TestTrue(TEXT("skip 0"), ParseMarker(TEXT("skip:0"), M, Error) && !M.bFlag);
	TestTrue(TEXT("mix on"), ParseMarker(TEXT("mix:on"), M, Error) && M.Kind == ELBCineMarkerKind::Mix && M.bFlag);
	TestTrue(TEXT("mix off"), ParseMarker(TEXT("mix:off"), M, Error) && !M.bFlag);

	TestTrue(TEXT("credits with seconds"), ParseMarker(TEXT("credits:40"), M, Error) && M.Kind == ELBCineMarkerKind::Credits);
	TestNearlyEqual(TEXT("credits seconds"), M.Value, 40.f);
	TestTrue(TEXT("credits without seconds"), ParseMarker(TEXT("credits"), M, Error) && M.Value < 0.f);
	TestTrue(TEXT("end"), ParseMarker(TEXT("end"), M, Error) && M.Kind == ELBCineMarkerKind::End);
	TestTrue(TEXT("!end"), ParseMarker(TEXT("!end"), M, Error) && M.bMust);

	// The time the caller set is kept.
	FLBCineMarker Timed;
	Timed.Seconds = 12.5;
	TestTrue(TEXT("parse into a timed marker"), ParseMarker(TEXT("card:A"), Timed, Error));
	TestEqual(TEXT("the time is kept"), Timed.Seconds, 12.5);
	TestEqual(TEXT("the label is kept"), Timed.Label, FString(TEXT("card:A")));

	// Every error case: a failed parse reports why and leaves the marker alone.
	const TCHAR* Bad[] = {
		TEXT(""), TEXT("!"), TEXT("Card:A"), TEXT("jump:A"), TEXT("card"), TEXT("card:"), TEXT("card:A,B"), TEXT("card: A"), TEXT("card:A B"),
		TEXT("tag:Not.A.Real.Tag"), TEXT("tag"), TEXT("bell:5"), TEXT("bell:0x1"), TEXT("bell:6x1"), TEXT("bell:5x0"), TEXT("bell:axb"), TEXT("bell:5x1,2"),
		TEXT("strike"), TEXT("strike:A,2"), TEXT("strike:A,x"), TEXT("strike:A,0.5,1"), TEXT("flash"), TEXT("flash:2"), TEXT("flash:-1"),
		TEXT("look:A,0"), TEXT("look:A,x"), TEXT("mark:A,-1"), TEXT("lock:half"), TEXT("lock:none"), TEXT("lock"), TEXT("skip:2"), TEXT("skip"),
		TEXT("mix:maybe"), TEXT("credits:0"), TEXT("credits:x"), TEXT("end:now"), TEXT("!!end"), TEXT("card:A,"), TEXT("card:,A")
	};
	for (const TCHAR* Label : Bad)
	{
		FLBCineMarker Untouched;
		Untouched.Seconds = 3.0;
		Untouched.Label = TEXT("keep");
		FString Why;
		TestFalse(FString::Printf(TEXT("'%s' is rejected"), Label), ParseMarker(Label, Untouched, Why));
		TestFalse(FString::Printf(TEXT("'%s' says why"), Label), Why.IsEmpty());
		TestEqual(FString::Printf(TEXT("'%s' leaves the marker alone"), Label), Untouched.Label, FString(TEXT("keep")));
	}
	return true;
}

// =====================================================================================================================
// MarkersCrossing
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBCineMarkersCrossingTest, "LastBell.Cine.MarkersCrossing", LB_CINE_TEST_FLAGS)
bool FLBCineMarkersCrossingTest::RunTest(const FString& Parameters)
{
	using namespace LBCineUnitTest;
	TArray<FLBCineMarker> Markers = {
		At(0.0, TEXT("skip:1")), At(0.8, TEXT("card:Intro_1")), At(2.0, TEXT("card:Intro_2")), At(2.0, TEXT("flash:0.5")), At(5.0, TEXT("!lock:None")) };
	LBCinematicLogic::SortMarkers(Markers);

	// Rates 0.5, 1 and 8: the same order whatever the step size (the step is dt * rate).
	for (const double Rate : { 0.5, 1.0, 8.0 })
	{
		TBitArray<> Fired;
		double Prev = -1.0;
		TArray<double> Times;
		for (double T = 0.0; T < 6.0 + 1.0e-9; T += (1.0 / 60.0) * Rate)
		{
			Times.Add(T);
		}
		const TArray<FString> Order = Run(Markers, Fired, Prev, Times);
		TestEqual(*FString::Printf(TEXT("rate %.1f: all five fire"), Rate), Order.Num(), 5);
		if (Order.Num() == 5)
		{
			TestEqual(TEXT("first (time 0 fires on the first step)"), Order[0], FString(TEXT("skip:1")));
			TestEqual(TEXT("second"), Order[1], FString(TEXT("card:Intro_1")));
			TestEqual(TEXT("third: same frame, authored order"), Order[2], FString(TEXT("card:Intro_2")));
			TestEqual(TEXT("fourth"), Order[3], FString(TEXT("flash:0.5")));
			TestEqual(TEXT("fifth"), Order[4], FString(TEXT("!lock:None")));
		}
	}

	// Several markers crossed in one big step all fire, in order.
	{
		TBitArray<> Fired;
		double Prev = -1.0;
		const TArray<FString> Order = Run(Markers, Fired, Prev, { 10.0 });
		TestEqual(TEXT("one big step fires everything"), Order.Num(), 5);
		TestEqual(TEXT("...in time order"), Order.IsValidIndex(4) ? Order[4] : FString(), FString(TEXT("!lock:None")));
	}

	// Edges: (Prev, Cur] - a marker exactly on Cur fires, one exactly on Prev already did.
	{
		TBitArray<> Fired;
		TArray<int32> Indices;
		LBCinematicLogic::MarkersToFire(Markers, 0.0, 0.8, Fired, Indices);
		TestEqual(TEXT("the marker on Cur fires, the one on Prev does not"), Indices.Num(), 1);
		LBCinematicLogic::MarkersToFire(Markers, 0.8, 0.8, Fired, Indices);
		TestEqual(TEXT("no time passed: nothing"), Indices.Num(), 0);
	}

	// No repeat, and a backward jump fires nothing.
	{
		TBitArray<> Fired;
		double Prev = -1.0;
		Run(Markers, Fired, Prev, { 3.0 });
		TArray<int32> Indices;
		LBCinematicLogic::MarkersToFire(Markers, 3.0, 1.0, Fired, Indices);
		TestEqual(TEXT("a backward jump fires nothing"), Indices.Num(), 0);
		LBCinematicLogic::MarkersToFire(Markers, 1.0, 3.0, Fired, Indices);
		TestEqual(TEXT("jumping forward over fired markers does not repeat them"), Indices.Num(), 0);
		LBCinematicLogic::MarkersToFire(Markers, 3.0, 6.0, Fired, Indices);
		TestEqual(TEXT("the one left still fires once"), Indices.Num(), 1);
		LBCinematicLogic::MarkersToFire(Markers, 3.0, 6.0, Fired, Indices);
		TestEqual(TEXT("...and never twice"), Indices.Num(), 0);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBCineSkipFiresMustOnceTest, "LastBell.Cine.SkipFiresMustOnce", LB_CINE_TEST_FLAGS)
bool FLBCineSkipFiresMustOnceTest::RunTest(const FString& Parameters)
{
	using namespace LBCineUnitTest;
	TArray<FLBCineMarker> Markers = {
		At(0.0, TEXT("skip:1")), At(1.0, TEXT("!tag:State.Event.Arrival")), At(2.0, TEXT("card:Intro_1")), At(3.0, TEXT("!lock:None")), At(4.0, TEXT("flash:0.5")) };
	LBCinematicLogic::SortMarkers(Markers);

	// A skip at 1.5 s: the first must marker has already fired on its own.
	TBitArray<> Fired;
	double Prev = -1.0;
	Run(Markers, Fired, Prev, { 1.5 });
	TArray<int32> Indices;
	LBCinematicLogic::MustMarkersOnSkip(Markers, Fired, Indices);
	TestEqual(TEXT("one must marker is left"), Indices.Num(), 1);
	TestEqual(TEXT("it is the lock"), Indices.IsValidIndex(0) ? Markers[Indices[0]].Label : FString(), FString(TEXT("!lock:None")));

	LBCinematicLogic::MustMarkersOnSkip(Markers, Fired, Indices);
	TestEqual(TEXT("a second skip fires none"), Indices.Num(), 0);

	// A skip at the very start fires both, in order, and the plain markers are dropped.
	TBitArray<> Fresh;
	LBCinematicLogic::MustMarkersOnSkip(Markers, Fresh, Indices);
	TestEqual(TEXT("both must markers"), Indices.Num(), 2);
	TestTrue(TEXT("in time order"), Indices.Num() == 2 && Markers[Indices[0]].Seconds < Markers[Indices[1]].Seconds);

	// The skip hold: counts only while skippable and held, fires once.
	LBCinematicLogic::FSkipHold Hold;
	TestFalse(TEXT("not holding: nothing"), Hold.Tick(2.f, 1.f, true));
	Hold.Begin();
	TestFalse(TEXT("held but not skippable: nothing"), Hold.Tick(2.f, 1.f, false));
	TestNearlyEqual(TEXT("...and nothing counted"), Hold.Held, 0.f);
	TestFalse(TEXT("0.6 s of 1.0"), Hold.Tick(0.6f, 1.f, true));
	TestNearlyEqual(TEXT("fraction 0.6"), Hold.Fraction(1.f), 0.6f);
	TestTrue(TEXT("1.0 s reached: fires"), Hold.Tick(0.5f, 1.f, true));
	TestFalse(TEXT("...once"), Hold.Tick(0.5f, 1.f, true));
	Hold.End();
	TestNearlyEqual(TEXT("release resets"), Hold.Held, 0.f);
	Hold.Begin();
	TestFalse(TEXT("a new hold starts from zero"), Hold.Tick(0.9f, 1.f, true));
	Hold.End();
	TestFalse(TEXT("letting go early never fires"), Hold.Tick(0.5f, 1.f, true));
	return true;
}

// =====================================================================================================================
// EaseAndYaw, CreditsSpeed, cards
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBCineEaseAndYawTest, "LastBell.Cine.EaseAndYaw", LB_CINE_TEST_FLAGS)
bool FLBCineEaseAndYawTest::RunTest(const FString& Parameters)
{
	using namespace LBCinematicLogic;
	TestNearlyEqual(TEXT("smoothstep 0"), Smoothstep(0.f), 0.f);
	TestNearlyEqual(TEXT("smoothstep 0.5"), Smoothstep(0.5f), 0.5f);
	TestNearlyEqual(TEXT("smoothstep 1"), Smoothstep(1.f), 1.f);
	TestNearlyEqual(TEXT("smoothstep clamps below"), Smoothstep(-3.f), 0.f);
	TestNearlyEqual(TEXT("smoothstep clamps above"), Smoothstep(7.f), 1.f);
	TestTrue(TEXT("smoothstep is slow at the start"), Smoothstep(0.1f) < 0.1f);
	TestTrue(TEXT("smoothstep is slow at the end"), Smoothstep(0.9f) > 0.9f);

	// The shortest way round.
	TestNearlyEqual(TEXT("10 to 30 at half"), ShortestYawLerp(10.f, 30.f, 0.5f), 20.f);
	TestNearlyEqual(TEXT("350 to 10 goes through 0 (half is 360)"), FRotator::NormalizeAxis(ShortestYawLerp(350.f, 10.f, 0.5f)), 0.f, 1.0e-3f);
	TestNearlyEqual(TEXT("10 to 350 goes through 0 (half is 0)"), FRotator::NormalizeAxis(ShortestYawLerp(10.f, 350.f, 0.5f)), 0.f, 1.0e-3f);
	TestNearlyEqual(TEXT("-170 to 170 goes through 180"), FMath::Abs(FRotator::NormalizeAxis(ShortestYawLerp(-170.f, 170.f, 0.5f))), 180.f, 1.0e-3f);
	TestNearlyEqual(TEXT("alpha 0 is the start"), ShortestYawLerp(40.f, 200.f, 0.f), 40.f);
	TestNearlyEqual(TEXT("alpha 1 is the end (same angle)"), FRotator::NormalizeAxis(ShortestYawLerp(40.f, 200.f, 1.f) - 200.f), 0.f, 1.0e-3f);

	// Card opacity: 0.3 in, 2.4 hold, 0.3 out.
	TestNearlyEqual(TEXT("card at 0"), CardOpacity(0.f, 0.3f, 2.4f), 0.f);
	TestNearlyEqual(TEXT("card half way in"), CardOpacity(0.15f, 0.3f, 2.4f), 0.5f);
	TestNearlyEqual(TEXT("card holding"), CardOpacity(1.5f, 0.3f, 2.4f), 1.f);
	TestNearlyEqual(TEXT("card half way out"), CardOpacity(0.3f + 2.4f + 0.15f, 0.3f, 2.4f), 0.5f);
	TestNearlyEqual(TEXT("card after its life"), CardOpacity(3.1f, 0.3f, 2.4f), 0.f);
	TestNearlyEqual(TEXT("card duration"), CardDuration(0.3f, 2.4f), 3.0f);
	TestNearlyEqual(TEXT("a card with no fade is on for its hold"), CardOpacity(1.f, 0.f, 2.f), 1.f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBCineCreditsSpeedTest, "LastBell.Cine.CreditsSpeed", LB_CINE_TEST_FLAGS)
bool FLBCineCreditsSpeedTest::RunTest(const FString& Parameters)
{
	using namespace LBCinematicLogic;
	// The box travels its own height plus the viewport's in the given seconds.
	TestNearlyEqual(TEXT("1200 + 1080 px in 40 s"), CreditsPixelsPerSecond(1200.f, 1080.f, 40.f), 57.f);
	TestNearlyEqual(TEXT("scales with the box"), CreditsPixelsPerSecond(2400.f, 1080.f, 40.f), 87.f);
	TestNearlyEqual(TEXT("scales with the time"), CreditsPixelsPerSecond(1200.f, 1080.f, 20.f), 114.f);
	TestTrue(TEXT("zero seconds does not divide by zero"), FMath::IsFinite(CreditsPixelsPerSecond(100.f, 100.f, 0.f)));
	TestNearlyEqual(TEXT("an empty box still scrolls the viewport"), CreditsPixelsPerSecond(0.f, 1080.f, 10.f), 108.f);
	return true;
}

// =====================================================================================================================
// Bell pendulum and axle
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBCineBellPendulumTest, "LastBell.Cine.BellPendulum", LB_CINE_TEST_FLAGS)
bool FLBCineBellPendulumTest::RunTest(const FString& Parameters)
{
	using LBCinematicLogic::FBellPendulum;
	constexpr float Kick = 6.f, Max = 16.f, Period = 2.6f, Damping = 0.25f, Stop = 0.05f;

	// A kick from rest: angle(t) = A e^(-d t) sin(2 pi t / P).
	{
		FBellPendulum P;
		TestFalse(TEXT("at rest"), P.IsSwinging());
		TestNearlyEqual(TEXT("rest angle"), P.AngleDeg(), 0.f);
		P.Kick(Kick, Max);
		TestTrue(TEXT("swinging after a kick"), P.IsSwinging());
		TestNearlyEqual(TEXT("angle 0 at the kick"), P.AngleDeg(), 0.f);
		float T = 0.f;
		for (int32 Step = 0; Step < 100; ++Step)
		{
			P.Advance(0.01f, Period, Damping, Stop);
			T += 0.01f;
		}
		const float Expected = Kick * FMath::Exp(-Damping * T) * FMath::Sin(UE_TWO_PI * T / Period);
		TestNearlyEqual(TEXT("angle at 1 s matches the formula"), P.AngleDeg(), Expected, 1.0e-3f);
	}

	// Decay: the amplitude falls as e^(-d t).
	{
		FBellPendulum P;
		P.Kick(Kick, Max);
		P.Advance(4.f, Period, Damping, Stop);
		TestNearlyEqual(TEXT("amplitude after 4 s"), P.AmplitudeDeg, Kick * FMath::Exp(-Damping * 4.f), 1.0e-3f);
	}

	// Kicks add and clamp.
	{
		FBellPendulum P;
		P.Kick(Kick, Max);
		P.Kick(Kick, Max);
		TestNearlyEqual(TEXT("two kicks add"), P.AmplitudeDeg, 12.f);
		P.Kick(Kick, Max);
		TestNearlyEqual(TEXT("three kicks clamp at the maximum"), P.AmplitudeDeg, Max);
		P.Kick(Kick, Max);
		TestNearlyEqual(TEXT("...and stay there"), P.AmplitudeDeg, Max);
		P.Kick(0.f, Max);
		TestNearlyEqual(TEXT("a zero kick does nothing"), P.AmplitudeDeg, Max);
	}

	// A kick during a swing does not pop the angle and keeps the swing direction.
	{
		FBellPendulum P;
		P.Kick(Kick, Max);
		P.Advance(0.9f, Period, Damping, Stop);
		const float Before = P.AngleDeg();
		const float AmplitudeBefore = P.AmplitudeDeg;
		const bool bMovingUpBefore = FMath::Cos(P.Phase) >= 0.f;
		P.Kick(Kick, Max);
		TestNearlyEqual(TEXT("the angle does not jump on a kick"), P.AngleDeg(), Before, 1.0e-3f);
		TestTrue(TEXT("the amplitude grew"), P.AmplitudeDeg > AmplitudeBefore + 5.9f);
		TestEqual(TEXT("the swing direction is kept"), FMath::Cos(P.Phase) >= 0.f, bMovingUpBefore);
	}

	// Stop threshold: below 0.05 degrees it stops exactly at rest.
	{
		FBellPendulum P;
		P.Kick(Kick, Max);
		float T = 0.f;
		bool bStopped = false;
		while (T < 60.f)
		{
			if (!P.Advance(0.02f, Period, Damping, Stop))
			{
				bStopped = true;
				break;
			}
			T += 0.02f;
		}
		TestTrue(TEXT("the swing stops"), bStopped);
		// 6 e^(-0.25 t) < 0.05 at t = ln(120) / 0.25 = 19.15 s.
		TestNearlyEqual(TEXT("...after about 19.2 s"), T, FMath::Loge(Kick / Stop) / Damping, 0.1f);
		TestFalse(TEXT("not swinging"), P.IsSwinging());
		TestNearlyEqual(TEXT("exactly at rest"), P.AngleDeg(), 0.f, 0.f);
		TestFalse(TEXT("advancing at rest reports no swing"), P.Advance(1.f, Period, Damping, Stop));
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBCineBellAxleTest, "LastBell.Cine.BellAxle", LB_CINE_TEST_FLAGS)
bool FLBCineBellAxleTest::RunTest(const FString& Parameters)
{
	using namespace LBCinematicLogic;
	// The F0 values: the axle at the headstock (12420, 2000, 2880), axis +Y (headstock rotation 0, Pitch).
	const FVector Pivot(12420.0, 2000.0, 2880.0);
	const FVector Axis = AxleAxis(FQuat::Identity, ELBBellSwingAxis::Pitch);
	TestTrue(TEXT("Pitch is the headstock's local Y"), Axis.Equals(FVector::YAxisVector, 1.0e-6));
	TestTrue(TEXT("Roll is the headstock's local X"), AxleAxis(FQuat::Identity, ELBBellSwingAxis::Roll).Equals(FVector::XAxisVector, 1.0e-6));
	const FQuat Yawed(FVector::ZAxisVector, FMath::DegreesToRadians(90.0));
	TestTrue(TEXT("a turned headstock turns the axis"), AxleAxis(Yawed, ELBBellSwingAxis::Pitch).Equals(-FVector::XAxisVector, 1.0e-6));

	// The bell origin (the crown) is 20 cm below the axle.
	const FVector BellRest(12420.0, 2000.0, 2860.0);
	const FQuat BellRestRotation = FQuat::Identity;

	{
		const FTransform Zero = SwingAboutAxle(BellRest, BellRestRotation, Pivot, Axis, 0.f);
		TestTrue(TEXT("0 degrees gives the rest location back exactly"), Zero.GetLocation() == BellRest);
		TestTrue(TEXT("0 degrees gives the rest rotation back exactly"), Zero.GetRotation() == BellRestRotation);
	}
	{
		// The pivot stays fixed.
		for (const float Angle : { -16.f, -5.f, 7.f, 16.f })
		{
			const FTransform T = SwingAboutAxle(Pivot, BellRestRotation, Pivot, Axis, Angle);
			TestTrue(*FString::Printf(TEXT("the pivot stays fixed at %.0f degrees"), Angle), T.GetLocation().Equals(Pivot, 1.0e-6));
		}
	}
	{
		// At 16 degrees the bell origin moves 20 sin(16) = 5.5 cm in X and stays 20 cos(16) below the axle.
		const FTransform T = SwingAboutAxle(BellRest, BellRestRotation, Pivot, Axis, 16.f);
		const double Expected = 20.0 * FMath::Sin(FMath::DegreesToRadians(16.0));
		TestNearlyEqual(TEXT("X moves 20 sin 16 = 5.5 cm"), static_cast<float>(FMath::Abs(T.GetLocation().X - BellRest.X)), static_cast<float>(Expected), 1.0e-3f);
		TestNearlyEqual(TEXT("...about 5.5"), static_cast<float>(FMath::Abs(T.GetLocation().X - BellRest.X)), 5.5f, 0.05f);
		TestNearlyEqual(TEXT("Y does not move"), static_cast<float>(T.GetLocation().Y), static_cast<float>(BellRest.Y), 1.0e-3f);
		TestNearlyEqual(TEXT("it stays 20 cm from the axle"), static_cast<float>(FVector::Dist(T.GetLocation(), Pivot)), 20.f, 1.0e-3f);
		// The bell turns by the same angle about Y.
		const FQuat Expected16(Axis, FMath::DegreesToRadians(16.0));
		TestTrue(TEXT("the rotation is the swing rotation"), T.GetRotation().Equals(Expected16, 1.0e-5f));
	}
	{
		// The headstock turns with it (it is at the pivot, so only its rotation changes).
		const FQuat HeadRest = FQuat::Identity;
		const FTransform T = SwingAboutAxle(Pivot, HeadRest, Pivot, Axis, 10.f);
		TestTrue(TEXT("the headstock stays at the axle"), T.GetLocation().Equals(Pivot, 1.0e-6));
		TestNearlyEqual(TEXT("...and turns by the angle"), static_cast<float>(FMath::RadiansToDegrees(HeadRest.AngularDistance(T.GetRotation()))), 10.f, 1.0e-3f);
	}

	// The rope: only Z changes. Its top at (12550, 1835, 2750) sits on the wheel's east rim.
	{
		const FVector RopeTop(12550.0, 1835.0, 2750.0);
		const FVector Zero = RopeZAboutAxle(RopeTop, Pivot, Axis, 0.f);
		TestTrue(TEXT("0 degrees gives the rope back exactly"), Zero == RopeTop);
		for (const float Angle : { -16.f, 16.f })
		{
			const FVector Moved = RopeZAboutAxle(RopeTop, Pivot, Axis, Angle);
			TestTrue(*FString::Printf(TEXT("the rope keeps X and Y at %.0f degrees"), Angle), Moved.X == RopeTop.X && Moved.Y == RopeTop.Y);
			// The exact rotation of the offset (130, -165, -130) about Y.
			const double Rad = FMath::DegreesToRadians(static_cast<double>(Angle));
			const double ExpectedZ = Pivot.Z + (-130.0 * FMath::Sin(Rad) + (-130.0) * FMath::Cos(Rad));
			TestNearlyEqual(*FString::Printf(TEXT("rope Z at %.0f degrees"), Angle), static_cast<float>(Moved.Z), static_cast<float>(ExpectedZ), 1.0e-3f);
			// "About 36 cm": the first-order rim travel 130 * 0.279 = 36; the exact value differs a little because the offset is below the axle.
			const float Travel = static_cast<float>(FMath::Abs(Moved.Z - RopeTop.Z));
			TestTrue(*FString::Printf(TEXT("the rope top moves about 36 cm at %.0f degrees (%.1f)"), Angle, Travel), Travel > 28.f && Travel < 43.f);
		}
		// Opposite angles move it in opposite directions.
		TestTrue(TEXT("the rope goes up for one sign and down for the other"),
			(RopeZAboutAxle(RopeTop, Pivot, Axis, 16.f).Z - RopeTop.Z) * (RopeZAboutAxle(RopeTop, Pivot, Axis, -16.f).Z - RopeTop.Z) < 0.0);
	}
	return true;
}

// =====================================================================================================================
// Authoring helper
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBCineCameraCutCanBlendHelperTest, "LastBell.Cine.CameraCutCanBlendHelper", LB_CINE_TEST_FLAGS)
bool FLBCineCameraCutCanBlendHelperTest::RunTest(const FString& Parameters)
{
	TStrongObjectPtr<ULevelSequence> Sequence(NewObject<ULevelSequence>(GetTransientPackage()));
	Sequence->Initialize();
	UMovieScene* MovieScene = Sequence->GetMovieScene();
	if (!TestNotNull(TEXT("the sequence has a movie scene"), MovieScene))
	{
		return false;
	}
	UMovieSceneCameraCutTrack* Track = Cast<UMovieSceneCameraCutTrack>(MovieScene->AddCameraCutTrack(UMovieSceneCameraCutTrack::StaticClass()));
	if (!TestNotNull(TEXT("a camera cut track was added"), Track))
	{
		return false;
	}

	// Mark the track as the engine does by default (false) and flip it.
	ULBCineAuthoringLibrary::SetCameraCutTrackCanBlend(Track, false);
	TestFalse(TEXT("can blend is false"), ULBCineAuthoringLibrary::GetCameraCutTrackCanBlend(Track));
	TestTrue(TEXT("set returns true"), ULBCineAuthoringLibrary::SetCameraCutTrackCanBlend(Track, true));
	TestTrue(TEXT("can blend reads back true"), ULBCineAuthoringLibrary::GetCameraCutTrackCanBlend(Track));
	TestTrue(TEXT("the member itself is true"), Track->bCanBlend);
	TestTrue(TEXT("set false returns true"), ULBCineAuthoringLibrary::SetCameraCutTrackCanBlend(Track, false));
	TestFalse(TEXT("can blend reads back false"), ULBCineAuthoringLibrary::GetCameraCutTrackCanBlend(Track));

	// A null track: false, with a warning.
	AddExpectedError(TEXT("SetCameraCutTrackCanBlend: the track is null"), EAutomationExpectedErrorFlags::Contains, 1);
	TestFalse(TEXT("set on a null track is false"), ULBCineAuthoringLibrary::SetCameraCutTrackCanBlend(nullptr, true));
	TestFalse(TEXT("get on a null track is false"), ULBCineAuthoringLibrary::GetCameraCutTrackCanBlend(nullptr));
	return true;
}

#endif
