#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

#include "AI/LBWardenAnim.h"
#include "AI/LBWardenAnimSet.h"
#include "Character/LBPlayerTuningData.h"

// P13-2: pure-logic unit tests of the Warden's animation helpers (LastBell.Warden.Anim.*). The anim instance itself needs a skeletal
// mesh and an Animation Blueprint, which arrive in later P13 tasks; its decisions are all in these helpers.

#define LB_TEST_FLAGS (EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

#define TEST_ENUM(What, Actual, Expected) TestEqual(What, static_cast<int32>(Actual), static_cast<int32>(Expected))

namespace
{
	FLBStoopBox MakeBox(const FVector& Center, const FVector& HalfExtent, float Amount, const FRotator& Rotation = FRotator::ZeroRotator)
	{
		FLBStoopBox Box;
		Box.Center = Center;
		Box.HalfExtent = HalfExtent;
		Box.Amount = Amount;
		Box.Rotation = Rotation.Quaternion();
		return Box;
	}

	/** Feeds a steady turn: DegreesPerSecond for Seconds at 60 Hz. */
	void FeedTurn(FLBYawHistory& History, float& Now, float DegreesPerSecond, float Seconds)
	{
		const float Dt = 1.f / 60.f;
		for (float T = 0.f; T < Seconds - 1.0e-4f; T += Dt)
		{
			Now += Dt;
			History.Add(Now, DegreesPerSecond * Dt);
		}
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAnimBoxTest, "LastBell.Warden.Anim.StoopBoxRotated", LB_TEST_FLAGS)
bool FLBAnimBoxTest::RunTest(const FString& Parameters)
{
	// Axis aligned: 100 x 50 x 150 half extents at (1000, 2000, 150).
	const FLBStoopBox Flat = MakeBox(FVector(1000.0, 2000.0, 150.0), FVector(100.0, 50.0, 150.0), 1.f);
	TestTrue(TEXT("Centre is inside"), LBWardenAnim::IsPointInBox(Flat, FVector(1000.0, 2000.0, 150.0)));
	TestTrue(TEXT("Just inside on X"), LBWardenAnim::IsPointInBox(Flat, FVector(1099.0, 2000.0, 150.0)));
	TestFalse(TEXT("Just outside on X"), LBWardenAnim::IsPointInBox(Flat, FVector(1101.0, 2000.0, 150.0)));
	TestTrue(TEXT("Just inside on Y"), LBWardenAnim::IsPointInBox(Flat, FVector(1000.0, 2049.0, 150.0)));
	TestFalse(TEXT("Just outside on Y"), LBWardenAnim::IsPointInBox(Flat, FVector(1000.0, 2051.0, 150.0)));
	TestFalse(TEXT("Above the box"), LBWardenAnim::IsPointInBox(Flat, FVector(1000.0, 2000.0, 301.0)));
	TestFalse(TEXT("Below the box"), LBWardenAnim::IsPointInBox(Flat, FVector(1000.0, 2000.0, -1.0)));
	TestTrue(TEXT("The edge counts as inside"), LBWardenAnim::IsPointInBox(Flat, FVector(1100.0, 2050.0, 300.0)));

	// Turned 90 degrees: the long axis now runs along Y. A point 80 cm out on Y is inside, 80 cm out on X is not.
	const FLBStoopBox Quarter = MakeBox(FVector(1000.0, 2000.0, 150.0), FVector(100.0, 50.0, 150.0), 1.f, FRotator(0.f, 90.f, 0.f));
	TestTrue(TEXT("90 degrees: along the turned long axis, inside"), LBWardenAnim::IsPointInBox(Quarter, FVector(1000.0, 2080.0, 150.0)));
	TestFalse(TEXT("90 degrees: along the old long axis, outside"), LBWardenAnim::IsPointInBox(Quarter, FVector(1080.0, 2000.0, 150.0)));
	TestTrue(TEXT("90 degrees: 40 cm across, inside"), LBWardenAnim::IsPointInBox(Quarter, FVector(1040.0, 2000.0, 150.0)));

	// Turned 45 degrees: along the diagonal 90 cm out is inside (the long half extent is 100); the same distance along the
	// perpendicular diagonal is outside (the short half extent is 50). An unrotated test would get both wrong.
	const FLBStoopBox Diagonal = MakeBox(FVector::ZeroVector, FVector(100.0, 50.0, 150.0), 1.f, FRotator(0.f, 45.f, 0.f));
	const FVector Along = FVector(1.0, 1.0, 0.0).GetSafeNormal();
	const FVector Across = FVector(-1.0, 1.0, 0.0).GetSafeNormal();
	TestTrue(TEXT("45 degrees: 90 cm along the long axis is inside"), LBWardenAnim::IsPointInBox(Diagonal, Along * 90.0));
	TestFalse(TEXT("45 degrees: 110 cm along the long axis is outside"), LBWardenAnim::IsPointInBox(Diagonal, Along * 110.0));
	TestFalse(TEXT("45 degrees: 90 cm across is outside"), LBWardenAnim::IsPointInBox(Diagonal, Across * 90.0));
	TestTrue(TEXT("45 degrees: 40 cm across is inside"), LBWardenAnim::IsPointInBox(Diagonal, Across * 40.0));
	// A corner of the unrotated rectangle (inside it, outside the turned box) is refused.
	TestFalse(TEXT("45 degrees: a corner of the unrotated box is outside"), LBWardenAnim::IsPointInBox(Diagonal, FVector(95.0, -45.0, 0.0)));

	// Rotated about the long axis as well (a tilted box): the vertical extent follows the tilt.
	const FLBStoopBox Tilted = MakeBox(FVector::ZeroVector, FVector(100.0, 50.0, 20.0), 1.f, FRotator(0.f, 0.f, 90.f));
	TestTrue(TEXT("Rolled 90 degrees: 40 cm up is inside the old Y extent"), LBWardenAnim::IsPointInBox(Tilted, FVector(0.0, 0.0, 40.0)));
	TestFalse(TEXT("Rolled 90 degrees: 40 cm sideways is outside the old Z extent"), LBWardenAnim::IsPointInBox(Tilted, FVector(0.0, 40.0, 0.0)));

	// A box with a negative half extent holds nothing.
	TestFalse(TEXT("Negative extent holds nothing"), LBWardenAnim::IsPointInBox(MakeBox(FVector::ZeroVector, FVector(-1.0, 10.0, 10.0), 1.f), FVector::ZeroVector));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAnimStoopTargetTest, "LastBell.Warden.Anim.StoopTarget", LB_TEST_FLAGS)
bool FLBAnimStoopTargetTest::RunTest(const FString& Parameters)
{
	TArray<FLBStoopBox> Zones;
	TestEqual(TEXT("No zones: 0"), LBWardenAnim::StoopTarget(Zones, FVector::ZeroVector), 0.f);

	Zones.Add(MakeBox(FVector(0.0, 0.0, 150.0), FVector(150.0, 62.0, 150.0), 0.5f));
	Zones.Add(MakeBox(FVector(100.0, 0.0, 150.0), FVector(50.0, 62.0, 150.0), 1.f));
	Zones.Add(MakeBox(FVector(5000.0, 0.0, 150.0), FVector(150.0, 62.0, 150.0), 0.6f));

	TestEqual(TEXT("Outside every zone: 0"), LBWardenAnim::StoopTarget(Zones, FVector(0.0, 500.0, 150.0)), 0.f);
	TestEqual(TEXT("Inside only the wide, shallow zone: its amount"), LBWardenAnim::StoopTarget(Zones, FVector(-100.0, 0.0, 150.0)), 0.5f);
	TestEqual(TEXT("Inside two zones: the highest amount"), LBWardenAnim::StoopTarget(Zones, FVector(100.0, 0.0, 150.0)), 1.f);
	TestEqual(TEXT("Inside the far zone: 0.6"), LBWardenAnim::StoopTarget(Zones, FVector(5000.0, 10.0, 150.0)), 0.6f);
	TestEqual(TEXT("Above the zones (a floor higher up): 0"), LBWardenAnim::StoopTarget(Zones, FVector(0.0, 0.0, 400.0)), 0.f);

	// A zone with amount 0 never raises the result; an amount above 1 is capped.
	TArray<FLBStoopBox> Odd;
	Odd.Add(MakeBox(FVector::ZeroVector, FVector(50.0), 0.f));
	TestEqual(TEXT("Amount 0 stays 0"), LBWardenAnim::StoopTarget(Odd, FVector::ZeroVector), 0.f);
	Odd.Add(MakeBox(FVector::ZeroVector, FVector(50.0), 2.f));
	TestEqual(TEXT("Amount above 1 is capped"), LBWardenAnim::StoopTarget(Odd, FVector::ZeroVector), 1.f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAnimEaseTest, "LastBell.Warden.Anim.EaseTowards", LB_TEST_FLAGS)
bool FLBAnimEaseTest::RunTest(const FString& Parameters)
{
	TestNearlyEqual(TEXT("Up by rate * dt"), LBWardenAnim::EaseTowards(0.f, 1.f, 3.f, 0.1f), 0.3f);
	TestNearlyEqual(TEXT("Down by rate * dt"), LBWardenAnim::EaseTowards(1.f, 0.f, 3.f, 0.1f), 0.7f);
	TestEqual(TEXT("Never overshoots up"), LBWardenAnim::EaseTowards(0.9f, 1.f, 3.f, 1.f), 1.f);
	TestEqual(TEXT("Never overshoots down"), LBWardenAnim::EaseTowards(0.1f, 0.f, 3.f, 1.f), 0.f);
	TestEqual(TEXT("At the target stays"), LBWardenAnim::EaseTowards(0.5f, 0.5f, 3.f, 0.1f), 0.5f);
	TestEqual(TEXT("Zero delta does not move"), LBWardenAnim::EaseTowards(0.2f, 1.f, 3.f, 0.f), 0.2f);
	TestEqual(TEXT("Negative delta does not move"), LBWardenAnim::EaseTowards(0.2f, 1.f, 3.f, -1.f), 0.2f);
	TestEqual(TEXT("Zero rate does not move"), LBWardenAnim::EaseTowards(0.2f, 1.f, 0.f, 1.f), 0.2f);

	// 0 to 1 at 3 per second takes a third of a second, at any frame rate.
	for (const float Dt : { 1.f / 120.f, 1.f / 60.f, 1.f / 30.f })
	{
		float Value = 0.f;
		float Time = 0.f;
		while (Value < 1.f && Time < 2.f)
		{
			Value = LBWardenAnim::EaseTowards(Value, 1.f, 3.f, Dt);
			Time += Dt;
		}
		TestTrue(FString::Printf(TEXT("A full stoop takes 1/3 s at dt %.4f (took %.3f)"), Dt, Time), FMath::Abs(Time - 1.f / 3.f) <= Dt + 1.0e-4f);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAnimTurnTest, "LastBell.Warden.Anim.TurnDecision", LB_TEST_FLAGS)
bool FLBAnimTurnTest::RunTest(const FString& Parameters)
{
	float Now = 0.f;

	// A steady right turn of 120 deg/s: after 0.5 s the history holds 60 degrees.
	FLBYawHistory Right;
	FeedTurn(Right, Now, 120.f, 0.2f);
	TEST_ENUM(TEXT("24 degrees so far: no turn yet"), LBWardenAnim::TurnDecision(Right, 0.f, false, 0.f), ELBWardenTurn::None);
	FeedTurn(Right, Now, 120.f, 0.35f);
	TestNearlyEqual(TEXT("Only the last 0.5 s count"), Right.Total(), 60.f, 3.f);
	TEST_ENUM(TEXT("About 60 degrees: turn right"), LBWardenAnim::TurnDecision(Right, 0.f, false, 0.f, 55.f), ELBWardenTurn::Right);

	// The same turn to the left.
	Now = 0.f;
	FLBYawHistory Left;
	FeedTurn(Left, Now, -200.f, 0.5f);
	TEST_ENUM(TEXT("100 degrees to the left: turn left"), LBWardenAnim::TurnDecision(Left, 0.f, false, 0.f), ELBWardenTurn::Left);

	// Each gate on its own.
	TEST_ENUM(TEXT("Moving (15 cm/s): no turn"), LBWardenAnim::TurnDecision(Left, 15.f, false, 0.f), ELBWardenTurn::None);
	TEST_ENUM(TEXT("Just under the speed limit still turns"), LBWardenAnim::TurnDecision(Left, 14.f, false, 0.f), ELBWardenTurn::Left);
	TEST_ENUM(TEXT("A montage is playing: no turn"), LBWardenAnim::TurnDecision(Left, 0.f, true, 0.f), ELBWardenTurn::None);
	TEST_ENUM(TEXT("Cooldown running: no turn"), LBWardenAnim::TurnDecision(Left, 0.f, false, 0.4f), ELBWardenTurn::None);

	// A turn that comes back: left then right inside the window cancels.
	Now = 0.f;
	FLBYawHistory Wobble;
	FeedTurn(Wobble, Now, 200.f, 0.25f);
	FeedTurn(Wobble, Now, -200.f, 0.25f);
	TEST_ENUM(TEXT("Wobble: net zero, no turn"), LBWardenAnim::TurnDecision(Wobble, 0.f, false, 0.f), ELBWardenTurn::None);

	// Slow drift never adds up: 40 deg/s for 5 s is 20 degrees per window.
	Now = 0.f;
	FLBYawHistory Drift;
	for (int32 i = 0; i < 5; ++i)
	{
		FeedTurn(Drift, Now, 40.f, 1.f);
		TEST_ENUM(TEXT("Slow drift: no turn"), LBWardenAnim::TurnDecision(Drift, 0.f, false, 0.f), ELBWardenTurn::None);
	}

	// Reset forgets everything.
	Right.Reset();
	TestEqual(TEXT("Reset empties the history"), Right.Num(), 0);
	TestEqual(TEXT("Reset: total 0"), Right.Total(), 0.f);

	// History keeps a bounded number of samples.
	FLBYawHistory Long;
	Now = 0.f;
	FeedTurn(Long, Now, 10.f, 10.f);
	TestTrue(FString::Printf(TEXT("10 s at 60 Hz keeps only the last 0.5 s (%d samples)"), Long.Num()), Long.Num() <= 34);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAnimFeetTest, "LastBell.Warden.Anim.PelvisAndFeet", LB_TEST_FLAGS)
bool FLBAnimFeetTest::RunTest(const FString& Parameters)
{
	auto Hit = [](float Z) { FLBFootHit H; H.bHit = true; H.Offset = Z; return H; };

	// Flat floor: nothing to do.
	{
		const FLBFootPlacement P = LBWardenAnim::PelvisAndFeet(Hit(0.f), Hit(0.f), 35.f);
		TestFalse(TEXT("Flat: not active"), P.bActive);
		TestEqual(TEXT("Flat: pelvis stays"), P.PelvisZ, 0.f);
		TestEqual(TEXT("Flat: left 0"), P.LeftOffset, 0.f);
		TestEqual(TEXT("Flat: right 0"), P.RightOffset, 0.f);
	}
	// Under 5 cm of difference: still flat enough. Exactly 5 is not more than 5.
	{
		TestFalse(TEXT("4 cm apart: not active"), LBWardenAnim::PelvisAndFeet(Hit(0.f), Hit(4.f), 35.f).bActive);
		TestFalse(TEXT("Exactly 5 cm apart: not active"), LBWardenAnim::PelvisAndFeet(Hit(0.f), Hit(5.f), 35.f).bActive);
		TestTrue(TEXT("6 cm apart: active"), LBWardenAnim::PelvisAndFeet(Hit(0.f), Hit(6.f), 35.f).bActive);
	}
	// Going up a stair: the right foot is 18 cm higher. Active; the lower foot is at 0, so the pelvis does not move.
	{
		const FLBFootPlacement P = LBWardenAnim::PelvisAndFeet(Hit(0.f), Hit(18.f), 35.f);
		TestTrue(TEXT("Stair up: active"), P.bActive);
		TestEqual(TEXT("Stair up: right foot at 18"), P.RightOffset, 18.f);
		TestEqual(TEXT("Stair up: pelvis stays when the lower foot is on the floor"), P.PelvisZ, 0.f);
	}
	// Stepping down: the left foot is 20 cm below the floor. The pelvis drops 20.
	{
		const FLBFootPlacement P = LBWardenAnim::PelvisAndFeet(Hit(-20.f), Hit(0.f), 35.f);
		TestTrue(TEXT("Step down: active"), P.bActive);
		TestEqual(TEXT("Step down: left foot at -20"), P.LeftOffset, -20.f);
		TestEqual(TEXT("Step down: the pelvis drops by the lower foot's drop"), P.PelvisZ, -20.f);
	}
	// The drop is capped at MaxPelvisDrop.
	{
		const FLBFootPlacement P = LBWardenAnim::PelvisAndFeet(Hit(0.f), Hit(-60.f), 35.f);
		TestEqual(TEXT("A 60 cm drop is capped at 35"), P.PelvisZ, -35.f);
		TestEqual(TEXT("The foot itself still goes to -60"), P.RightOffset, -60.f);
		TestEqual(TEXT("MaxPelvisDrop 0 never drops the pelvis"), LBWardenAnim::PelvisAndFeet(Hit(0.f), Hit(-60.f), 0.f).PelvisZ, 0.f);
	}
	// The pelvis never goes up, even when both feet are on higher ground.
	{
		const FLBFootPlacement P = LBWardenAnim::PelvisAndFeet(Hit(10.f), Hit(30.f), 35.f);
		TestEqual(TEXT("Both feet high: pelvis does not rise"), P.PelvisZ, 0.f);
		TestTrue(TEXT("Both feet high but 20 apart: active"), P.bActive);
	}
	// A trace that hit nothing counts as flat ground.
	{
		FLBFootHit Miss;
		const FLBFootPlacement P = LBWardenAnim::PelvisAndFeet(Miss, Hit(20.f), 35.f);
		TestEqual(TEXT("Miss: left treated as 0"), P.LeftOffset, 0.f);
		TestEqual(TEXT("Miss: right as traced"), P.RightOffset, 20.f);
		TestTrue(TEXT("Miss against a 20 cm foot: active"), P.bActive);
		const FLBFootPlacement Both = LBWardenAnim::PelvisAndFeet(Miss, Miss, 35.f);
		TestFalse(TEXT("Two misses: inactive"), Both.bActive);
		TestEqual(TEXT("Two misses: pelvis stays"), Both.PelvisZ, 0.f);
		// Even a stale Offset on a miss is ignored.
		FLBFootHit StaleMiss;
		StaleMiss.Offset = -50.f;
		TestEqual(TEXT("A miss ignores Offset"), LBWardenAnim::PelvisAndFeet(StaleMiss, Hit(0.f), 35.f).PelvisZ, 0.f);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAnimFootTargetTest, "LastBell.Warden.Anim.FootTargetKeepsTheSwing", LB_TEST_FLAGS)
bool FLBAnimFootTargetTest::RunTest(const FString& Parameters)
{
	auto Hit = [](float Z) { FLBFootHit H; H.bHit = true; H.Offset = Z; return H; };

	// Flat floor, the animated foot lifted 20 cm in its swing: the target keeps the lift (offset 0 changes nothing).
	{
		const FLBFootPlacement P = LBWardenAnim::PelvisAndFeet(Hit(0.f), Hit(0.f), 35.f);
		const FVector Swinging(30.0, 12.0, 20.0);
		const FVector Target = LBWardenAnim::FootTarget(Swinging, P.LeftOffset);
		TestEqual(TEXT("Flat floor, lifted foot: the target is the animated foot"), Target, Swinging);
		TestEqual(TEXT("The lift survives (Z stays 20)"), Target.Z, 20.0);
		TestEqual(TEXT("A planted foot is untouched too"), LBWardenAnim::FootTarget(FVector(0.0, 0.0, 0.0), P.RightOffset), FVector::ZeroVector);
	}
	// A stair: the ground under the front foot is 18 cm up. Its target is the animated foot plus 18, the swing included.
	{
		const FLBFootPlacement P = LBWardenAnim::PelvisAndFeet(Hit(0.f), Hit(18.f), 35.f);
		const FVector Planted = LBWardenAnim::FootTarget(FVector(0.0, 0.0, 0.0), P.RightOffset);
		const FVector Swinging = LBWardenAnim::FootTarget(FVector(0.0, 0.0, 20.0), P.RightOffset);
		TestEqual(TEXT("Stair, planted foot: 18 up"), Planted.Z, 18.0);
		TestEqual(TEXT("Stair, swinging foot: its 20 cm lift plus the 18 of the step"), Swinging.Z, 38.0);
		TestEqual(TEXT("X and Y are never changed"), FVector(Swinging.X, Swinging.Y, 0.0), FVector::ZeroVector);
	}
	// The correction asked of a foot once the pelvis has dropped: it comes back up by the drop.
	TestEqual(TEXT("Flat, pelvis not moved: no correction"), LBWardenAnim::FootCorrection(0.f, 0.f), 0.f);
	TestEqual(TEXT("Flat, pelvis dropped 40 (stoop): every foot comes up 40"), LBWardenAnim::FootCorrection(0.f, -40.f), 40.f);
	TestEqual(TEXT("Step down 20, pelvis dropped 20: the low foot needs nothing, the other 20 up"), LBWardenAnim::FootCorrection(-20.f, -20.f), 0.f);
	TestEqual(TEXT("...and the foot on the floor level"), LBWardenAnim::FootCorrection(0.f, -20.f), 20.f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAnimStoopPelvisTest, "LastBell.Warden.Anim.StoopPelvis", LB_TEST_FLAGS)
bool FLBAnimStoopPelvisTest::RunTest(const FString& Parameters)
{
	const float Max = 35.f, Drop = 40.f;
	// Flat ground: only the stoop term.
	TestNearlyEqual(TEXT("Alpha 0: 0"), LBWardenAnim::CombinedPelvisZ(0.f, 0.f, Drop, Max), 0.f);
	TestNearlyEqual(TEXT("Alpha 0.7: -28"), LBWardenAnim::CombinedPelvisZ(0.f, 0.7f, Drop, Max), -28.f);
	TestNearlyEqual(TEXT("Alpha 1: -40"), LBWardenAnim::CombinedPelvisZ(0.f, 1.f, Drop, Max), -40.f);
	// On a stair: the foot IK's drop adds to the stoop.
	TestNearlyEqual(TEXT("Stair drop -20 at alpha 0.7: -48"), LBWardenAnim::CombinedPelvisZ(-20.f, 0.7f, Drop, Max), -48.f);
	TestNearlyEqual(TEXT("Stair drop -20 at alpha 1: -60"), LBWardenAnim::CombinedPelvisZ(-20.f, 1.f, Drop, Max), -60.f);
	TestNearlyEqual(TEXT("Stair drop -20 at alpha 0: -20 (no stoop)"), LBWardenAnim::CombinedPelvisZ(-20.f, 0.f, Drop, Max), -20.f);
	// The total never goes below -(Max + Drop) = -75, and never up.
	TestNearlyEqual(TEXT("Foot drop already at the cap, full stoop: -75"), LBWardenAnim::CombinedPelvisZ(-35.f, 1.f, Drop, Max), -75.f);
	TestNearlyEqual(TEXT("A larger foot drop than the cap is clamped in total"), LBWardenAnim::CombinedPelvisZ(-80.f, 1.f, Drop, Max), -75.f);
	TestNearlyEqual(TEXT("A positive foot value never lifts the pelvis"), LBWardenAnim::CombinedPelvisZ(10.f, 0.f, Drop, Max), 0.f);
	// Alpha outside 0..1 is clamped; a zero drop leaves the foot IK alone.
	TestNearlyEqual(TEXT("Alpha 2 counts as 1"), LBWardenAnim::CombinedPelvisZ(0.f, 2.f, Drop, Max), -40.f);
	TestNearlyEqual(TEXT("StoopPelvisDrop 0: stoop does nothing"), LBWardenAnim::CombinedPelvisZ(-10.f, 1.f, 0.f, Max), -10.f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAnimAttackRateTest, "LastBell.Warden.Anim.AttackPlayRate", LB_TEST_FLAGS)
bool FLBAnimAttackRateTest::RunTest(const FString& Parameters)
{
	TestNearlyEqual(TEXT("Hit at 0.9 s, windup 0.6 s: 1.5"), LBWardenAnim::AttackPlayRate(0.9f, 0.6f), 1.5f);
	TestNearlyEqual(TEXT("Hit at 0.6 s: 1.0"), LBWardenAnim::AttackPlayRate(0.6f, 0.6f), 1.f);
	TestNearlyEqual(TEXT("A very late hit is capped at 2.5"), LBWardenAnim::AttackPlayRate(3.f, 0.6f), 2.5f);
	TestNearlyEqual(TEXT("A very early hit is raised to 0.8"), LBWardenAnim::AttackPlayRate(0.2f, 0.6f), 0.8f);
	TestNearlyEqual(TEXT("Unknown hit time: 1"), LBWardenAnim::AttackPlayRate(0.f, 0.6f), 1.f);
	TestNearlyEqual(TEXT("Negative hit time: 1"), LBWardenAnim::AttackPlayRate(-1.f, 0.6f), 1.f);
	TestNearlyEqual(TEXT("Unknown windup: 1"), LBWardenAnim::AttackPlayRate(0.9f, 0.f), 1.f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAnimDefaultsTest, "LastBell.Warden.Anim.Defaults", LB_TEST_FLAGS)
bool FLBAnimDefaultsTest::RunTest(const FString& Parameters)
{
	// The numbers the plan fixes (P13 plan, section 8), and the catch camera tuning.
	const ULBWardenAnimSet& Set = *GetDefault<ULBWardenAnimSet>();
	TestEqual(TEXT("TurnPlayRate"), Set.TurnPlayRate, 1.5f);
	TestEqual(TEXT("TurnTriggerDegrees"), Set.TurnTriggerDegrees, 45.f);
	TestEqual(TEXT("TurnCooldownSeconds"), Set.TurnCooldownSeconds, 1.f);
	TestEqual(TEXT("StoopEaseRate"), Set.StoopEaseRate, 3.f);
	TestEqual(TEXT("StoopPelvisDrop"), Set.StoopPelvisDrop, 40.f);
	TestEqual(TEXT("FootTraceUp"), Set.FootTraceUp, 50.f);
	TestEqual(TEXT("FootTraceDown"), Set.FootTraceDown, 75.f);
	TestEqual(TEXT("FootIKInterpSpeed"), Set.FootIKInterpSpeed, 15.f);
	TestEqual(TEXT("MaxPelvisDrop"), Set.MaxPelvisDrop, 35.f);
	TestEqual(TEXT("PhysicsMaxDistance"), Set.PhysicsMaxDistance, 2500.f);
	TestTrue(TEXT("No montage in the defaults"), !Set.Attack && !Set.TurnLeft90 && !Set.TurnRight90 && !Set.LookAround);

	const ULBPlayerTuningData& Player = *GetDefault<ULBPlayerTuningData>();
	TestEqual(TEXT("CatchLookSeconds"), Player.CatchLookSeconds, 0.25f);
	TestEqual(TEXT("CatchHoldSeconds"), Player.CatchHoldSeconds, 0.8f);
	TestEqual(TEXT("CatchFadeSeconds"), Player.CatchFadeSeconds, 0.5f);
	return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS
