#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

#include "AI/LBWardenLogic.h"
#include "AI/LBWardenTuningData.h"
#include "Character/LBPlayerTuningData.h"
#include "LBGameplayTags.h"

// Pure-logic unit tests for the Phase 5 Warden brain (P5-001). Perception, navigation and the live brain component are
// covered by the functional AI tests in L_Test_Warden (P5-004).

#define LB_TEST_FLAGS (EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

// Enum classes have no TestEqual overload: compare them as ints.
#define TEST_ENUM(What, Actual, Expected) TestEqual(What, static_cast<int32>(Actual), static_cast<int32>(Expected))

namespace
{
	const ULBWardenTuningData& Tuning()
	{
		return *GetDefault<ULBWardenTuningData>();
	}

	FLBWardenFacts Facts(int32 Stage)
	{
		FLBWardenFacts F;
		F.Caps = LBWardenLogic::CapsForStage(Stage);
		return F;
	}

	ELBWardenState Next(ELBWardenState State, const FLBWardenFacts& F)
	{
		return LBWardenLogic::Evaluate(State, F, Tuning()).Next;
	}

	const ELBWardenState AllStates[] = {
		ELBWardenState::Dormant, ELBWardenState::Patrol, ELBWardenState::Investigate, ELBWardenState::Suspicious,
		ELBWardenState::Search, ELBWardenState::Chase, ELBWardenState::Attack, ELBWardenState::Return };
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenStageTest, "LastBell.Warden.Stage.Gating", LB_TEST_FLAGS)
bool FLBWardenStageTest::RunTest(const FString& Parameters)
{
	// Highest present stage wins; none present is 0.
	FGameplayTagContainer Tags;
	TestEqual(TEXT("No stage tag"), LBWardenLogic::HighestStage(Tags), 0);
	Tags.AddTag(LBTags::State_Warden_Stage_1);
	TestEqual(TEXT("Stage 1"), LBWardenLogic::HighestStage(Tags), 1);
	Tags.AddTag(LBTags::State_Warden_Stage_4);
	Tags.AddTag(LBTags::State_Warden_Stage_2);
	TestEqual(TEXT("Highest of 1,2,4"), LBWardenLogic::HighestStage(Tags), 4);
	Tags.AddTag(LBTags::State_Warden_Stage_6);
	TestEqual(TEXT("Stage 6"), LBWardenLogic::HighestStage(Tags), 6);

	for (int32 Stage = 0; Stage <= 6; ++Stage)
	{
		const FLBWardenCaps C = LBWardenLogic::CapsForStage(Stage);
		const FString Label = FString::Printf(TEXT("stage %d"), Stage);
		TestEqual(*(Label + TEXT(" active")), C.bActive, Stage >= 3);
		TestEqual(*(Label + TEXT(" patrol")), C.bPatrol, Stage >= 4);
		TestEqual(*(Label + TEXT(" search")), C.bSearch, Stage >= 4);
		TestEqual(*(Label + TEXT(" chase")), C.bChase, Stage >= 5);

		// Which states are legal.
		TEST_ENUM(*(Label + TEXT(" Dormant legal")), LBWardenLogic::IsStateAllowed(ELBWardenState::Dormant, C), Stage < 3);
		TEST_ENUM(*(Label + TEXT(" Investigate legal")), LBWardenLogic::IsStateAllowed(ELBWardenState::Investigate, C), Stage >= 3);
		TEST_ENUM(*(Label + TEXT(" Suspicious legal")), LBWardenLogic::IsStateAllowed(ELBWardenState::Suspicious, C), Stage >= 3);
		TEST_ENUM(*(Label + TEXT(" Return legal")), LBWardenLogic::IsStateAllowed(ELBWardenState::Return, C), Stage >= 3);
		TEST_ENUM(*(Label + TEXT(" Attack legal")), LBWardenLogic::IsStateAllowed(ELBWardenState::Attack, C), Stage >= 3);
		TEST_ENUM(*(Label + TEXT(" Search legal")), LBWardenLogic::IsStateAllowed(ELBWardenState::Search, C), Stage >= 4);
		TEST_ENUM(*(Label + TEXT(" Chase legal")), LBWardenLogic::IsStateAllowed(ELBWardenState::Chase, C), Stage >= 5);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenTransitionInvariantTest, "LastBell.Warden.Transitions.Invariants", LB_TEST_FLAGS)
bool FLBWardenTransitionInvariantTest::RunTest(const FString& Parameters)
{
	// Exhaustive: every state x stage 0..6 x every combination of the boolean facts x a few timer values. The brain must never
	// pick a state the stage forbids, and below stage 3 it must always end up Dormant.
	const float StateTimes[] = { 0.f, 1.f, 100.f };
	const float SightAges[] = { 0.f, 100.f };
	int32 Checked = 0;
	for (int32 Stage = 0; Stage <= 6; ++Stage)
	{
		for (const ELBWardenState State : AllStates)
		{
			for (int32 Mask = 0; Mask < (1 << 9); ++Mask)
			{
				for (const float StateTime : StateTimes)
				{
					for (const float SightAge : SightAges)
					{
						FLBWardenFacts F = Facts(Stage);
						F.bSeesPlayer = Mask & 1;
						F.bSightConfirmed = Mask & 2;
						F.bNoiseHeard = Mask & 4;
						F.bInAttackRange = Mask & 8;
						F.bAttackStillValid = Mask & 16;
						F.bArrived = Mask & 32;
						F.bPlayerUnreachable = Mask & 64;
						F.bSearchFinished = Mask & 128;
						F.bCanMaterialize = Mask & 256;
						F.StateTime = StateTime;
						F.TimeSinceSight = SightAge;

						const FLBWardenDecision D = LBWardenLogic::Evaluate(State, F, Tuning());
						++Checked;
						// A dormant Warden waiting for a safe moment to appear legitimately stays Dormant at an active stage.
						const bool bWaitingToAppear = State == ELBWardenState::Dormant && D.Next == ELBWardenState::Dormant;
						if (!LBWardenLogic::IsStateAllowed(D.Next, F.Caps) && !bWaitingToAppear)
						{
							AddError(FString::Printf(TEXT("stage %d: %s -> %s is not allowed (mask %d)"), Stage,
								LBWardenLogic::StateName(State), LBWardenLogic::StateName(D.Next), Mask));
							return false;
						}
						if (Stage < 3 && D.Next != ELBWardenState::Dormant)
						{
							AddError(FString::Printf(TEXT("stage %d: %s -> %s, expected Dormant"), Stage, LBWardenLogic::StateName(State), LBWardenLogic::StateName(D.Next)));
							return false;
						}
						if (D.bKillPlayer && (State != ELBWardenState::Attack || D.Next != ELBWardenState::Return))
						{
							AddError(TEXT("A kill may only come from a landed Attack"));
							return false;
						}
					}
				}
			}
		}
	}
	TestTrue(TEXT("Checked many combinations"), Checked > 100000);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenTransitionTableTest, "LastBell.Warden.Transitions.Table", LB_TEST_FLAGS)
bool FLBWardenTransitionTableTest::RunTest(const FString& Parameters)
{
	const ULBWardenTuningData& T = Tuning();

	// ---- Dormant ----
	{
		FLBWardenFacts F = Facts(2);
		TEST_ENUM(TEXT("Stage 2 Dormant stays"), Next(ELBWardenState::Dormant, F), ELBWardenState::Dormant);
		F = Facts(3);
		F.bCanMaterialize = false;
		TEST_ENUM(TEXT("Stage 3 but spawn is in the player's view: stays Dormant"), Next(ELBWardenState::Dormant, F), ELBWardenState::Dormant);
		F.bCanMaterialize = true;
		TEST_ENUM(TEXT("Stage 3 wakes to Patrol (post)"), Next(ELBWardenState::Dormant, F), ELBWardenState::Patrol);
		F = Facts(3);
		F.bSightConfirmed = true;
		F.bNoiseHeard = true;
		TEST_ENUM(TEXT("Dormant ignores noise and sight until it has appeared"), Next(ELBWardenState::Dormant, F), ELBWardenState::Patrol);
		F = Facts(1);
		F.bInAttackRange = true;
		TEST_ENUM(TEXT("A stage-1 Warden never attacks"), Next(ELBWardenState::Patrol, F), ELBWardenState::Dormant);
	}

	// ---- Noise ----
	for (int32 Stage = 3; Stage <= 6; ++Stage)
	{
		FLBWardenFacts F = Facts(Stage);
		F.bNoiseHeard = true;
		for (const ELBWardenState S : { ELBWardenState::Patrol, ELBWardenState::Return, ELBWardenState::Suspicious })
		{
			TEST_ENUM(*FString::Printf(TEXT("Stage %d: %s + noise -> Investigate"), Stage, LBWardenLogic::StateName(S)), Next(S, F), ELBWardenState::Investigate);
		}
		const FLBWardenDecision Re = LBWardenLogic::Evaluate(ELBWardenState::Investigate, F, T);
		TEST_ENUM(TEXT("Investigate + new noise stays Investigate"), Re.Next, ELBWardenState::Investigate);
		TestTrue(TEXT("...and re-enters to retarget"), Re.bReenter);
		if (Stage >= 4)
		{
			TEST_ENUM(TEXT("Search + noise -> Investigate"), Next(ELBWardenState::Search, F), ELBWardenState::Investigate);
		}
		if (Stage >= 5)
		{
			TEST_ENUM(TEXT("Chase ignores noise (the brain only updates the last-known spot)"), Next(ELBWardenState::Chase, F), ELBWardenState::Chase);
		}
	}

	// ---- Sight ----
	for (int32 Stage = 3; Stage <= 6; ++Stage)
	{
		FLBWardenFacts F = Facts(Stage);
		F.bSeesPlayer = true;
		F.bSightConfirmed = false;
		TEST_ENUM(TEXT("Unconfirmed sight changes nothing"), Next(ELBWardenState::Patrol, F), ELBWardenState::Patrol);
		F.bSightConfirmed = true;
		const ELBWardenState Expected = Stage >= 5 ? ELBWardenState::Chase : ELBWardenState::Investigate;
		TEST_ENUM(*FString::Printf(TEXT("Stage %d confirmed sight from Patrol"), Stage), Next(ELBWardenState::Patrol, F), Expected);
		TEST_ENUM(*FString::Printf(TEXT("Stage %d confirmed sight from Return"), Stage), Next(ELBWardenState::Return, F), Expected);
		if (Stage >= 4)
		{
			TEST_ENUM(*FString::Printf(TEXT("Stage %d confirmed sight from Search"), Stage), Next(ELBWardenState::Search, F), Expected);
		}
		TEST_ENUM(*FString::Printf(TEXT("Stage %d confirmed sight from Suspicious"), Stage), Next(ELBWardenState::Suspicious, F), Expected);
	}
	{
		FLBWardenFacts F = Facts(5);
		F.bSeesPlayer = true;
		F.bSightConfirmed = true;
		F.bPlayerUnreachable = true;
		TEST_ENUM(TEXT("Seen but unreachable: Search, not Chase"), Next(ELBWardenState::Patrol, F), ELBWardenState::Search);
		TEST_ENUM(TEXT("Already searching an unreachable player: keep searching"), Next(ELBWardenState::Search, F), ELBWardenState::Search);
	}

	// ---- Investigate / Suspicious / Search / Return ----
	{
		FLBWardenFacts F = Facts(3);
		TEST_ENUM(TEXT("Investigate underway"), Next(ELBWardenState::Investigate, F), ELBWardenState::Investigate);
		F.bArrived = true;
		TEST_ENUM(TEXT("Investigate arrived -> Suspicious"), Next(ELBWardenState::Investigate, F), ELBWardenState::Suspicious);

		F = Facts(3);
		F.StateTime = T.SuspiciousSeconds - 0.1f;
		TEST_ENUM(TEXT("Suspicious still looking"), Next(ELBWardenState::Suspicious, F), ELBWardenState::Suspicious);
		F.StateTime = T.SuspiciousSeconds;
		TEST_ENUM(TEXT("Stage 3 Suspicious timeout -> Return (no Search yet)"), Next(ELBWardenState::Suspicious, F), ELBWardenState::Return);
		F = Facts(4);
		F.StateTime = T.SuspiciousSeconds;
		TEST_ENUM(TEXT("Stage 4 Suspicious timeout -> Search"), Next(ELBWardenState::Suspicious, F), ELBWardenState::Search);

		F = Facts(4);
		TEST_ENUM(TEXT("Search underway"), Next(ELBWardenState::Search, F), ELBWardenState::Search);
		F.bSearchFinished = true;
		TEST_ENUM(TEXT("Search points visited -> Return"), Next(ELBWardenState::Search, F), ELBWardenState::Return);
		F = Facts(4);
		F.StateTime = T.SearchDurationSeconds;
		TEST_ENUM(TEXT("Search time over -> Return"), Next(ELBWardenState::Search, F), ELBWardenState::Return);

		F = Facts(4);
		TEST_ENUM(TEXT("Return underway"), Next(ELBWardenState::Return, F), ELBWardenState::Return);
		F.bArrived = true;
		TEST_ENUM(TEXT("Return arrived -> Patrol"), Next(ELBWardenState::Return, F), ELBWardenState::Patrol);
		TEST_ENUM(TEXT("Patrol with nothing happening stays"), Next(ELBWardenState::Patrol, Facts(4)), ELBWardenState::Patrol);
	}

	// ---- Chase ----
	{
		FLBWardenFacts F = Facts(5);
		F.bSeesPlayer = true;
		TEST_ENUM(TEXT("Chase while seen"), Next(ELBWardenState::Chase, F), ELBWardenState::Chase);
		F.bSeesPlayer = false;
		F.TimeSinceSight = T.LastKnownMemorySeconds - 0.1f;
		TEST_ENUM(TEXT("Lost sight, memory still fresh: keep going to the last-known spot"), Next(ELBWardenState::Chase, F), ELBWardenState::Chase);
		F.bArrived = true;
		TEST_ENUM(TEXT("...even after arriving there, until the memory runs out"), Next(ELBWardenState::Chase, F), ELBWardenState::Chase);
		F.TimeSinceSight = T.LastKnownMemorySeconds;
		TEST_ENUM(TEXT("Memory over -> Search"), Next(ELBWardenState::Chase, F), ELBWardenState::Search);

		F = Facts(5);
		F.bSeesPlayer = true;
		F.bPlayerUnreachable = true;
		TEST_ENUM(TEXT("Unreachable, still walking to the closest point"), Next(ELBWardenState::Chase, F), ELBWardenState::Chase);
		F.bArrived = true;
		TEST_ENUM(TEXT("Unreachable, arrived at the closest point -> Search (never stare)"), Next(ELBWardenState::Chase, F), ELBWardenState::Search);
	}

	// ---- Attack ----
	for (int32 Stage = 3; Stage <= 6; ++Stage)
	{
		FLBWardenFacts F = Facts(Stage);
		F.bInAttackRange = true;
		for (const ELBWardenState S : { ELBWardenState::Patrol, ELBWardenState::Investigate, ELBWardenState::Suspicious, ELBWardenState::Return })
		{
			TEST_ENUM(*FString::Printf(TEXT("Stage %d: %s + in range -> Attack"), Stage, LBWardenLogic::StateName(S)), Next(S, F), ELBWardenState::Attack);
		}
		if (Stage >= 4)
		{
			TEST_ENUM(TEXT("Search + in range -> Attack"), Next(ELBWardenState::Search, F), ELBWardenState::Attack);
		}
		if (Stage >= 5)
		{
			TEST_ENUM(TEXT("Chase + in range -> Attack"), Next(ELBWardenState::Chase, F), ELBWardenState::Attack);
		}
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenAttackWindupTest, "LastBell.Warden.Attack.Windup", LB_TEST_FLAGS)
bool FLBWardenAttackWindupTest::RunTest(const FString& Parameters)
{
	const ULBWardenTuningData& T = Tuning();
	FLBWardenFacts F = Facts(5);
	F.bAttackStillValid = true;

	F.StateTime = 0.f;
	TEST_ENUM(TEXT("Windup just started: Attack continues"), Next(ELBWardenState::Attack, F), ELBWardenState::Attack);
	F.StateTime = T.AttackWindupSeconds - 0.01f;
	FLBWardenDecision D = LBWardenLogic::Evaluate(ELBWardenState::Attack, F, T);
	TEST_ENUM(TEXT("Windup not over: Attack continues"), D.Next, ELBWardenState::Attack);
	TestFalse(TEXT("No kill before the windup ends"), D.bKillPlayer);

	F.StateTime = T.AttackWindupSeconds;
	D = LBWardenLogic::Evaluate(ELBWardenState::Attack, F, T);
	TEST_ENUM(TEXT("Windup over, still in range with sight: Return"), D.Next, ELBWardenState::Return);
	TestTrue(TEXT("...and the player is killed"), D.bKillPlayer);

	F.bAttackStillValid = false;
	D = LBWardenLogic::Evaluate(ELBWardenState::Attack, F, T);
	TEST_ENUM(TEXT("Windup over, player got away (stage 5): Chase"), D.Next, ELBWardenState::Chase);
	TestFalse(TEXT("...no kill"), D.bKillPlayer);

	F.StateTime = T.AttackWindupSeconds * 0.5f;
	D = LBWardenLogic::Evaluate(ELBWardenState::Attack, F, T);
	TEST_ENUM(TEXT("Out of range mid-windup: the check waits for the windup to end"), D.Next, ELBWardenState::Attack);

	F = Facts(3);
	F.bAttackStillValid = false;
	F.StateTime = T.AttackWindupSeconds;
	TEST_ENUM(TEXT("Stage 3 cancelled attack goes to Investigate (cannot chase)"), Next(ELBWardenState::Attack, F), ELBWardenState::Investigate);
	F = Facts(4);
	F.bAttackStillValid = false;
	F.StateTime = T.AttackWindupSeconds;
	TEST_ENUM(TEXT("Stage 4 cancelled attack goes to Investigate"), Next(ELBWardenState::Attack, F), ELBWardenState::Investigate);

	// A stage drop mid-attack (a reload) ends it.
	F = Facts(2);
	TEST_ENUM(TEXT("Stage drop during Attack -> Dormant"), Next(ELBWardenState::Attack, F), ELBWardenState::Dormant);

	// A state the new stage forbids is left through Return.
	F = Facts(4);
	TEST_ENUM(TEXT("Chase at stage 4 (stage dropped) -> Return"), Next(ELBWardenState::Chase, F), ELBWardenState::Return);
	F = Facts(3);
	TEST_ENUM(TEXT("Search at stage 3 (stage dropped) -> Return"), Next(ELBWardenState::Search, F), ELBWardenState::Return);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenSightConfirmTest, "LastBell.Warden.Sight.ConfirmTime", LB_TEST_FLAGS)
bool FLBWardenSightConfirmTest::RunTest(const FString& Parameters)
{
	const float Confirm = Tuning().SightConfirmTime;
	FLBSightConfirm S;
	TestFalse(TEXT("Not visible: not confirmed"), S.IsConfirmed(Confirm));

	// Continuous line of sight confirms exactly at the confirm time.
	const float Step = 1.f / 60.f;
	float Elapsed = 0.f;
	while (Elapsed + Step < Confirm)
	{
		S.Advance(true, Step);
		Elapsed += Step;
		TestFalse(TEXT("Before the confirm time"), S.IsConfirmed(Confirm));
	}
	S.Advance(true, Confirm - Elapsed);
	TestTrue(TEXT("At the confirm time"), S.IsConfirmed(Confirm));

	// A single frame of broken line of sight restarts the timer.
	S.Advance(false, Step);
	TestFalse(TEXT("Broken sight: unconfirmed"), S.IsConfirmed(Confirm));
	S.Advance(true, Confirm * 0.9f);
	TestFalse(TEXT("Timer restarted after the break"), S.IsConfirmed(Confirm));
	S.Advance(true, Confirm * 0.2f);
	TestTrue(TEXT("Confirmed again after a full continuous interval"), S.IsConfirmed(Confirm));

	S.Reset();
	TestFalse(TEXT("Reset"), S.IsConfirmed(Confirm));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenCandleSightTest, "LastBell.Warden.Sight.CandleMultiplier", LB_TEST_FLAGS)
bool FLBWardenCandleSightTest::RunTest(const FString& Parameters)
{
	const ULBWardenTuningData& T = Tuning();
	TestEqual(TEXT("Stage 3 radius"), LBWardenLogic::EffectiveSightRadius(3, false, T), 1500.f);
	TestEqual(TEXT("Stage 4 radius"), LBWardenLogic::EffectiveSightRadius(4, false, T), 2000.f);
	TestEqual(TEXT("Stage 5 radius"), LBWardenLogic::EffectiveSightRadius(5, false, T), 2500.f);
	TestEqual(TEXT("Stage 6 uses the stage 5 radius"), LBWardenLogic::EffectiveSightRadius(6, false, T), 2500.f);
	TestEqual(TEXT("Lit candle stage 3"), LBWardenLogic::EffectiveSightRadius(3, true, T), 1500.f * 1.25f);
	TestEqual(TEXT("Lit candle stage 5"), LBWardenLogic::EffectiveSightRadius(5, true, T), 2500.f * 1.25f);

	// A player at 1700 cm is invisible with the candle snuffed and visible with it lit (stage 3: 1500 vs 1875).
	const float LoseExtra = T.LoseSightExtraRadius;
	const float Distance = 1700.f;
	TestFalse(TEXT("Snuffed: 1700 is beyond 1500"), LBWardenLogic::IsWithinSightRadius(Distance, false, LBWardenLogic::EffectiveSightRadius(3, false, T), LoseExtra));
	TestTrue(TEXT("Lit: 1700 is within 1875"), LBWardenLogic::IsWithinSightRadius(Distance, false, LBWardenLogic::EffectiveSightRadius(3, true, T), LoseExtra));

	// Hysteresis: once seen, the target is kept out to radius + 300, then lost.
	const float R = LBWardenLogic::EffectiveSightRadius(3, false, T);
	TestFalse(TEXT("Not yet seen at R+100"), LBWardenLogic::IsWithinSightRadius(R + 100.f, false, R, LoseExtra));
	TestTrue(TEXT("Already seen: kept at R+100"), LBWardenLogic::IsWithinSightRadius(R + 100.f, true, R, LoseExtra));
	TestTrue(TEXT("Already seen: kept at R+300"), LBWardenLogic::IsWithinSightRadius(R + LoseExtra, true, R, LoseExtra));
	TestFalse(TEXT("Already seen: lost at R+301"), LBWardenLogic::IsWithinSightRadius(R + LoseExtra + 1.f, true, R, LoseExtra));

	// The view cone helper used to hide spawns.
	TestTrue(TEXT("Dead ahead"), LBWardenLogic::IsInsideViewCone(FVector::ZeroVector, FVector::ForwardVector, FVector(500, 0, 0), 45.f));
	TestTrue(TEXT("30 degrees off"), LBWardenLogic::IsInsideViewCone(FVector::ZeroVector, FVector::ForwardVector, FVector(500, 289, 0), 45.f));
	TestFalse(TEXT("60 degrees off"), LBWardenLogic::IsInsideViewCone(FVector::ZeroVector, FVector::ForwardVector, FVector(500, 866, 0), 45.f));
	TestFalse(TEXT("Behind"), LBWardenLogic::IsInsideViewCone(FVector::ZeroVector, FVector::ForwardVector, FVector(-500, 0, 0), 75.f));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenSearchPlanTest, "LastBell.Warden.Search.PointSelection", LB_TEST_FLAGS)
bool FLBWardenSearchPlanTest::RunTest(const FString& Parameters)
{
	const FVector Center(0, 0, 0);
	// Candidates on the X axis: 1000, 400, 1400 (inside radius 1500), 1600 and 3000 (outside).
	const TArray<FVector> Candidates = { FVector(1000, 0, 0), FVector(400, 0, 0), FVector(1400, 0, 0), FVector(1600, 0, 0), FVector(3000, 0, 0) };

	FLBSearchPlan Plan;
	Plan.Build(Candidates, Center, 1500.f, 3);
	TestEqual(TEXT("Only points within the radius are kept"), Plan.Points.Num(), 3);

	// Nearest-unvisited order from the Warden's position (standing at the origin).
	FVector At = Center;
	TArray<float> Order;
	while (true)
	{
		const int32 Pick = Plan.PickNext(At);
		if (Pick == INDEX_NONE)
		{
			break;
		}
		Order.Add(Plan.Points[Pick].X);
		Plan.MarkVisited(Pick);
		At = Plan.Points[Pick];
	}
	TestEqual(TEXT("Visited count"), Order.Num(), 3);
	if (Order.Num() == 3)
	{
		TestEqual(TEXT("First: nearest"), Order[0], 400.f);
		TestEqual(TEXT("Second: nearest unvisited"), Order[1], 1000.f);
		TestEqual(TEXT("Third"), Order[2], 1400.f);
	}
	TestTrue(TEXT("Plan complete"), Plan.IsComplete());
	TestEqual(TEXT("Nothing left to pick"), Plan.PickNext(At), (int32)INDEX_NONE);

	// "Nearest" is measured from the Warden, not from the search centre.
	Plan.Build(Candidates, Center, 1500.f, 3);
	const int32 FromFar = Plan.PickNext(FVector(1500, 0, 0));
	TestEqual(TEXT("From x=1500 the nearest is 1400"), Plan.Points[FromFar].X, 1400.0);

	// The visit cap: three points are available but only two visits are allowed.
	Plan.Build(Candidates, Center, 1500.f, 2);
	Plan.MarkVisited(Plan.PickNext(Center));
	Plan.MarkVisited(Plan.PickNext(Center));
	TestTrue(TEXT("Capped at MaxVisits"), Plan.IsComplete());
	TestEqual(TEXT("No third pick"), Plan.PickNext(Center), (int32)INDEX_NONE);

	// Marking twice does not double count; no candidates is an immediately complete plan.
	Plan.Build(Candidates, Center, 1500.f, 3);
	Plan.MarkVisited(0);
	Plan.MarkVisited(0);
	TestEqual(TEXT("Visited counted once"), Plan.VisitedCount, 1);
	Plan.Build(TArray<FVector>(), Center, 1500.f, 3);
	TestTrue(TEXT("Empty plan is complete"), Plan.IsComplete());
	TestEqual(TEXT("Empty plan picks nothing"), Plan.PickNext(Center), (int32)INDEX_NONE);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenStuckTest, "LastBell.Warden.Stuck.Detector", LB_TEST_FLAGS)
bool FLBWardenStuckTest::RunTest(const FString& Parameters)
{
	const ULBWardenTuningData& T = Tuning();
	FLBStuckDetector D;
	D.StuckSeconds = T.StuckSeconds;
	D.MinProgress = T.StuckMinProgress;
	D.ForgiveDistance = T.StuckForgiveDistance;
	const float Dt = 0.1f;
	const FVector Here(100, 100, 0);

	// Moving normally never trips.
	FVector P = Here;
	for (int32 i = 0; i < 200; ++i)
	{
		P.X += 5.f;  // 5 cm per 0.1 s: slow, but 25 cm of progress arrives every half second
		TEST_ENUM(TEXT("Making progress"), D.Update(Dt, P), ELBStuckResult::None);
	}

	// Standing still for just under the limit does not trip; at the limit it asks for a re-path.
	D.Reset();
	ELBStuckResult R = ELBStuckResult::None;
	float Elapsed = 0.f;
	R = D.Update(Dt, Here);  // sets the anchor
	while (Elapsed + Dt < T.StuckSeconds - 0.05f)
	{
		Elapsed += Dt;
		R = D.Update(Dt, Here);
		TEST_ENUM(TEXT("Not stuck yet"), R, ELBStuckResult::None);
	}
	while (R == ELBStuckResult::None && Elapsed < T.StuckSeconds + 1.f)
	{
		Elapsed += Dt;
		R = D.Update(Dt, Here);
	}
	TEST_ENUM(TEXT("First stuck event: re-path"), R, ELBStuckResult::Repath);
	TestTrue(TEXT("It took about StuckSeconds"), FMath::IsNearlyEqual(Elapsed, T.StuckSeconds, 0.25f));

	// Still stuck at the same place: second consecutive failure gives the target up.
	R = ELBStuckResult::None;
	Elapsed = 0.f;
	while (R == ELBStuckResult::None && Elapsed < T.StuckSeconds + 1.f)
	{
		Elapsed += Dt;
		R = D.Update(Dt, Here);
	}
	TEST_ENUM(TEXT("Second stuck event: give up"), R, ELBStuckResult::GiveUp);

	// Moving a forgiving distance after a failure clears the count: the next failure is a re-path again.
	D.Reset();
	TEST_ENUM(TEXT("Blocked move #1 re-paths"), D.RegisterFailure(Here), ELBStuckResult::Repath);
	D.Update(Dt, Here);
	D.Update(Dt, Here + FVector(T.StuckForgiveDistance + 10.f, 0, 0));
	TestEqual(TEXT("Failure forgiven after travelling"), D.GetFailures(), 0);
	TEST_ENUM(TEXT("A later failure re-paths again"), D.RegisterFailure(Here + FVector(500, 0, 0)), ELBStuckResult::Repath);
	TEST_ENUM(TEXT("But two without progress give up"), D.RegisterFailure(Here + FVector(500, 0, 0)), ELBStuckResult::GiveUp);

	// Pausing (waiting at a point) does not accumulate stuck time.
	D.Reset();
	D.Update(Dt, Here);
	for (int32 i = 0; i < 20; ++i)
	{
		D.Update(Dt, Here);
	}
	D.Pause();
	TEST_ENUM(TEXT("After a pause the timer starts over"), D.Update(Dt, Here), ELBStuckResult::None);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenSpawnSelectionTest, "LastBell.Warden.Spawn.Selection", LB_TEST_FLAGS)
bool FLBWardenSpawnSelectionTest::RunTest(const FString& Parameters)
{
	TestEqual(TEXT("No spawns"), LBWardenLogic::SelectSpawnIndex({}, 4), (int32)INDEX_NONE);
	const TArray<int32> MinStages = { 3, 5, 4, 6 };
	TestEqual(TEXT("Stage 2: nothing applies"), LBWardenLogic::SelectSpawnIndex(MinStages, 2), (int32)INDEX_NONE);
	TestEqual(TEXT("Stage 3 -> MinStage 3"), LBWardenLogic::SelectSpawnIndex(MinStages, 3), 0);
	TestEqual(TEXT("Stage 4 -> MinStage 4"), LBWardenLogic::SelectSpawnIndex(MinStages, 4), 2);
	TestEqual(TEXT("Stage 5 -> MinStage 5"), LBWardenLogic::SelectSpawnIndex(MinStages, 5), 1);
	TestEqual(TEXT("Stage 6 -> MinStage 6"), LBWardenLogic::SelectSpawnIndex(MinStages, 6), 3);
	TestEqual(TEXT("Ties: the first one wins"), LBWardenLogic::SelectSpawnIndex({ 3, 3 }, 4), 0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenTuningTest, "LastBell.Warden.Tuning.Defaults", LB_TEST_FLAGS)
bool FLBWardenTuningTest::RunTest(const FString& Parameters)
{
	const ULBWardenTuningData& T = Tuning();
	const ULBPlayerTuningData& Player = *GetDefault<ULBPlayerTuningData>();

	TestEqual(TEXT("Patrol speed"), T.PatrolSpeed, 140.f);
	TestEqual(TEXT("Investigate speed"), T.InvestigateSpeed, 190.f);
	TestEqual(TEXT("Search speed"), T.SearchSpeed, 170.f);
	TestEqual(TEXT("Chase speed"), T.ChaseSpeed, 420.f);
	TestTrue(TEXT("Chase is slower than the player's sprint"), T.ChaseSpeed < Player.SprintSpeed);
	TestTrue(TEXT("Chase is faster than the player's walk"), T.ChaseSpeed > Player.WalkSpeed);
	TestTrue(TEXT("Only chase outruns a walking player"), T.InvestigateSpeed < Player.WalkSpeed && T.SearchSpeed < Player.WalkSpeed);

	TestEqual(TEXT("Sight confirm"), T.SightConfirmTime, 0.6f);
	TestTrue(TEXT("The sight confirm time is at least the 0.5 s audible tell"), T.SightConfirmTime >= 0.5f);
	TestEqual(TEXT("Cone half angle"), T.PeripheralHalfAngle, 45.f);
	TestEqual(TEXT("Lose-sight extra"), T.LoseSightExtraRadius, 300.f);
	TestEqual(TEXT("Hearing range"), T.HearingRange, 2500.f);
	TestEqual(TEXT("Memory"), T.LastKnownMemorySeconds, 6.f);
	TestEqual(TEXT("Search duration"), T.SearchDurationSeconds, 12.f);
	TestEqual(TEXT("Search point count"), T.SearchPointCount, 3);
	TestEqual(TEXT("Search radius"), T.SearchPointRadius, 1500.f);
	TestEqual(TEXT("Suspicious"), T.SuspiciousSeconds, 2.5f);
	TestEqual(TEXT("Attack range"), T.AttackRange, 140.f);
	TestEqual(TEXT("Attack windup"), T.AttackWindupSeconds, 0.6f);
	TestEqual(TEXT("Stuck time"), T.StuckSeconds, 3.f);

	// D-038: the collision capsule must fit a 104 x 230 cm doorway.
	TestEqual(TEXT("Capsule radius"), T.CapsuleRadius, 42.f);
	TestEqual(TEXT("Capsule half height"), T.CapsuleHalfHeight, 110.f);
	TestTrue(TEXT("Capsule fits the doorway width"), T.CapsuleRadius * 2.f < 104.f);
	TestTrue(TEXT("Capsule fits the doorway height"), T.CapsuleHalfHeight * 2.f < 230.f);
	TestTrue(TEXT("Eyes are inside the capsule"), T.EyeHeight < T.CapsuleHalfHeight);

	// Hearing: loudness scales the range, so walking is heard at 30 percent and crouching barely at all.
	TestTrue(TEXT("Crouch is above the loudness threshold (audible only up close)"), Player.CrouchLoudness >= T.HearingLoudnessThreshold);
	TestTrue(TEXT("Player noise cap covers the Warden hearing range"), Player.NoiseMaxRange >= T.HearingRange);
	TestTrue(TEXT("Sprint is heard from further than walking"), Player.SprintLoudness * T.HearingRange > Player.WalkLoudness * T.HearingRange);

	TEST_ENUM(TEXT("Move speed lookup: Chase"), T.GetMoveSpeed(ELBWardenState::Chase), T.ChaseSpeed);
	TEST_ENUM(TEXT("Move speed lookup: Patrol"), T.GetMoveSpeed(ELBWardenState::Patrol), T.PatrolSpeed);
	return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS
