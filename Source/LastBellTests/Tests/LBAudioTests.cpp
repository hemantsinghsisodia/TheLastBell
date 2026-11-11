#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

#include "Audio/LBAudioLogic.h"
#include "Audio/LBAudioSettings.h"
#include "Audio/LBAudioTypes.h"
#include "GameplayTagContainer.h"

// P16-1: pure-logic unit tests of the audio director (LastBell.Audio.Logic.*). The subsystem, the Warden audio component and the emitters
// only gather facts and apply these results; their PIE tests are in LBAudioFunctionalTests.cpp.

#define LB_AUDIO_TEST_FLAGS (EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

namespace LBAudioUnitTest
{
	FGameplayTag Tag(const TCHAR* Name)
	{
		return FGameplayTag::RequestGameplayTag(FName(Name), false);
	}

	/** A beat table written out here, so the BellPlan tests do not depend on FillPlanDefaults. */
	TArray<FLBBellBeat> MakeBeats(FAutomationTestBase& Test)
	{
		struct FRow { const TCHAR* Tag; int32 Stage; int32 Strikes; float First; float Spacing; int32 Drone; };
		static const FRow Rows[] = {
			{ TEXT("State.Event.Arrival"), 1, 3, 0.f, 4.5f, -1 }, // P17: the intro's first toll (owner 2026-11-11: no intro music)
			{ TEXT("State.Ritual.1"), 2, 3, 2.f, 4.5f, 1 },
			{ TEXT("State.Event.CryptEntered"), 1, 0, 0.f, 0.f, 0 },
			{ TEXT("State.Ritual.2"), 3, 3, 2.f, 4.5f, 2 },
			{ TEXT("State.Ritual.3"), 4, 3, 2.f, 4.0f, 1 },
			{ TEXT("State.Event.TowerTop"), 4, 4, 1.f, 3.5f, 2 },
			{ TEXT("State.Event.Finale"), 5, 5, 0.f, 2.0f, -1 },
		};
		TArray<FLBBellBeat> Beats;
		for (const FRow& Row : Rows)
		{
			const FGameplayTag T = Tag(Row.Tag);
			Test.TestTrue(FString::Printf(TEXT("Tag %s is registered"), Row.Tag), T.IsValid());
			FLBBellBeat& Beat = Beats.AddDefaulted_GetRef();
			Beat.Trigger = T;
			Beat.Stage = Row.Stage;
			Beat.Strikes = Row.Strikes;
			Beat.FirstDelay = Row.First;
			Beat.Spacing = Row.Spacing;
			Beat.Drone = Row.Drone;
		}
		return Beats;
	}
}

// =====================================================================================================================
// RainMix, WindMix
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioRainMixTest, "LastBell.Audio.Logic.RainMix", LB_AUDIO_TEST_FLAGS)
bool FLBAudioRainMixTest::RunTest(const FString& Parameters)
{
	// Defaults: OutGain 0.8, InGain 0.55, power 0.7.
	{
		const LBAudioLogic::FRainMix Open = LBAudioLogic::RainMix(1.f, 1.f, 0.7f, 0.8f, 0.55f);
		TestNearlyEqual(TEXT("Exposure 1: the outdoor rain is the full gain"), Open.Out, 0.8f, 1.0e-4f);
		TestNearlyEqual(TEXT("Exposure 1: no roof rain, whatever the roof"), Open.In, 0.f, 1.0e-4f);
	}
	{
		const LBAudioLogic::FRainMix Sealed = LBAudioLogic::RainMix(0.f, 1.f, 0.7f, 0.8f, 0.55f);
		TestNearlyEqual(TEXT("Exposure 0: no outdoor rain"), Sealed.Out, 0.f, 1.0e-4f);
		TestNearlyEqual(TEXT("Exposure 0 under a full roof: the full roof gain"), Sealed.In, 0.55f, 1.0e-4f);
		const LBAudioLogic::FRainMix Crypt = LBAudioLogic::RainMix(0.f, 0.f, 0.7f, 0.8f, 0.55f);
		TestNearlyEqual(TEXT("Exposure 0 with no roof (the crypt): no roof rain"), Crypt.In, 0.f, 1.0e-4f);
	}
	{
		const LBAudioLogic::FRainMix Half = LBAudioLogic::RainMix(0.5f, 1.f, 0.7f, 0.8f, 0.55f);
		TestNearlyEqual(TEXT("Exposure 0.5: Out = gain * 0.5^0.7"), Half.Out, 0.8f * FMath::Pow(0.5f, 0.7f), 1.0e-4f);
		TestNearlyEqual(TEXT("Exposure 0.5 under a full roof: In = gain * 0.5"), Half.In, 0.55f * 0.5f, 1.0e-4f);
		const LBAudioLogic::FRainMix HalfRoof = LBAudioLogic::RainMix(0.5f, 0.5f, 0.7f, 0.8f, 0.55f);
		TestNearlyEqual(TEXT("A half roof halves the roof rain"), HalfRoof.In, Half.In * 0.5f, 1.0e-4f);
	}
	{
		const LBAudioLogic::FRainMix Clamped = LBAudioLogic::RainMix(3.f, 2.f, 0.7f, 0.8f, 0.55f);
		TestNearlyEqual(TEXT("Exposure and roof are clamped to 0..1"), Clamped.Out, 0.8f, 1.0e-4f);
		TestTrue(TEXT("Outdoor rain falls monotonically as the exposure drops"), LBAudioLogic::RainMix(0.8f, 0.f, 0.7f, 0.8f, 0.55f).Out > LBAudioLogic::RainMix(0.4f, 0.f, 0.7f, 0.8f, 0.55f).Out);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioWindMixTest, "LastBell.Audio.Logic.WindMix", LB_AUDIO_TEST_FLAGS)
bool FLBAudioWindMixTest::RunTest(const FString& Parameters)
{
	// OutGain 0.6, WindMin 0.3.
	{
		const LBAudioLogic::FWindMix Calm = LBAudioLogic::WindMix(1.f, 0.f, 0.f, 0.f, 0.6f, 0.3f);
		TestNearlyEqual(TEXT("Outdoors in no wind: gain * WindMin"), Calm.Wind, 0.6f * 0.3f, 1.0e-4f);
		const LBAudioLogic::FWindMix Gale = LBAudioLogic::WindMix(1.f, 1.f, 0.f, 0.f, 0.6f, 0.3f);
		TestNearlyEqual(TEXT("Outdoors in full wind: the full gain"), Gale.Wind, 0.6f, 1.0e-4f);
	}
	{
		const LBAudioLogic::FWindMix Indoors = LBAudioLogic::WindMix(0.f, 1.f, 0.f, 0.f, 0.6f, 0.3f);
		TestNearlyEqual(TEXT("Sealed with no interior wind: silent"), Indoors.Wind, 0.f, 1.0e-4f);
		const LBAudioLogic::FWindMix Draught = LBAudioLogic::WindMix(0.f, 1.f, 0.4f, 0.f, 0.6f, 0.3f);
		TestNearlyEqual(TEXT("Sealed with interior wind 0.4: 0.4 of the gain"), Draught.Wind, 0.6f * 0.4f, 1.0e-4f);
		const LBAudioLogic::FWindMix Mixed = LBAudioLogic::WindMix(0.7f, 1.f, 0.4f, 0.f, 0.6f, 0.3f);
		TestNearlyEqual(TEXT("The larger of exposure and interior wind wins"), Mixed.Wind, 0.6f * 0.7f, 1.0e-4f);
	}
	{
		const LBAudioLogic::FWindMix Tower = LBAudioLogic::WindMix(0.f, 0.5f, 0.f, 1.f, 0.6f, 0.3f);
		TestNearlyEqual(TEXT("Howl = zone howl * wind strength"), Tower.Howl, 0.5f, 1.0e-4f);
		const LBAudioLogic::FWindMix NoHowl = LBAudioLogic::WindMix(0.f, 1.f, 0.f, 0.f, 0.6f, 0.3f);
		TestNearlyEqual(TEXT("No howl in a zone without one"), NoHowl.Howl, 0.f, 1.0e-4f);
	}
	return true;
}

// =====================================================================================================================
// ThunderPlan
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioThunderPlanTest, "LastBell.Audio.Logic.ThunderPlan", LB_AUDIO_TEST_FLAGS)
bool FLBAudioThunderPlanTest::RunTest(const FString& Parameters)
{
	const LBAudioLogic::FThunderParams P; // 0.6..4.5 s, jitter 0.4, near at 0.75, far below 0.4

	// The variant sets and their boundaries.
	TestTrue(TEXT("Brightness 1: near"), LBAudioLogic::PlanThunder(1.f, ELBFlashReason::Ambient, 0.5f, P).Set == LBAudioLogic::EThunderSet::Near);
	TestTrue(TEXT("Brightness 0.75 (the boundary): near"), LBAudioLogic::PlanThunder(0.75f, ELBFlashReason::Ambient, 0.5f, P).Set == LBAudioLogic::EThunderSet::Near);
	TestTrue(TEXT("Brightness just under 0.75: mid"), LBAudioLogic::PlanThunder(0.749f, ELBFlashReason::Ambient, 0.5f, P).Set == LBAudioLogic::EThunderSet::Mid);
	TestTrue(TEXT("Brightness 0.4 (the boundary): mid"), LBAudioLogic::PlanThunder(0.4f, ELBFlashReason::Ambient, 0.5f, P).Set == LBAudioLogic::EThunderSet::Mid);
	TestTrue(TEXT("Brightness just under 0.4: far"), LBAudioLogic::PlanThunder(0.399f, ELBFlashReason::Ambient, 0.5f, P).Set == LBAudioLogic::EThunderSet::Far);
	TestTrue(TEXT("Brightness 0: far"), LBAudioLogic::PlanThunder(0.f, ELBFlashReason::Ambient, 0.5f, P).Set == LBAudioLogic::EThunderSet::Far);
	TestEqual(TEXT("lb.Audio.Thunder: far is 0"), static_cast<int32>(LBAudioLogic::EThunderSet::Far), 0);
	TestEqual(TEXT("lb.Audio.Thunder: mid is 1"), static_cast<int32>(LBAudioLogic::EThunderSet::Mid), 1);
	TestEqual(TEXT("lb.Audio.Thunder: near is 2"), static_cast<int32>(LBAudioLogic::EThunderSet::Near), 2);

	// The delay: 0.6 s at brightness 1, 4.5 s at brightness 0, linear between, at the middle of the jitter.
	TestNearlyEqual(TEXT("Brightness 1: the delay is 0.6 s"), LBAudioLogic::PlanThunder(1.f, ELBFlashReason::Scripted, 0.5f, P).Delay, 0.6f, 1.0e-4f);
	TestNearlyEqual(TEXT("Brightness 0: the delay is 4.5 s"), LBAudioLogic::PlanThunder(0.f, ELBFlashReason::Scripted, 0.5f, P).Delay, 4.5f, 1.0e-4f);
	TestNearlyEqual(TEXT("Brightness 0.5: the delay is 2.55 s"), LBAudioLogic::PlanThunder(0.5f, ELBFlashReason::Scripted, 0.5f, P).Delay, 2.55f, 1.0e-4f);

	// Monotonic: a brighter flash is heard sooner.
	float Previous = 1.0e9f;
	bool bMonotonic = true;
	for (int32 Step = 0; Step <= 20; ++Step)
	{
		const float Delay = LBAudioLogic::PlanThunder(Step / 20.f, ELBFlashReason::Ambient, 0.5f, P).Delay;
		bMonotonic &= Delay <= Previous + 1.0e-6f;
		Previous = Delay;
	}
	TestTrue(TEXT("The delay never grows as the brightness grows"), bMonotonic);

	// The jitter bounds: +-0.4 s around the base, and never below zero.
	{
		const float Early = LBAudioLogic::PlanThunder(0.5f, ELBFlashReason::Ambient, 0.f, P).Delay;
		const float Late = LBAudioLogic::PlanThunder(0.5f, ELBFlashReason::Ambient, 1.f, P).Delay;
		TestNearlyEqual(TEXT("Rand 0 is 0.4 s early"), Early, 2.55f - 0.4f, 1.0e-4f);
		TestNearlyEqual(TEXT("Rand 1 is 0.4 s late"), Late, 2.55f + 0.4f, 1.0e-4f);
		bool bInside = true;
		for (int32 Step = 0; Step <= 50; ++Step)
		{
			const float Delay = LBAudioLogic::PlanThunder(0.5f, ELBFlashReason::Ambient, Step / 50.f, P).Delay;
			bInside &= Delay >= 2.55f - 0.4f - 1.0e-4f && Delay <= 2.55f + 0.4f + 1.0e-4f;
		}
		TestTrue(TEXT("Every draw stays inside the jitter bounds"), bInside);
		LBAudioLogic::FThunderParams WideJitter = P;
		WideJitter.Jitter = 3.f;
		TestTrue(TEXT("A jitter larger than the delay never makes it negative"), LBAudioLogic::PlanThunder(1.f, ELBFlashReason::Ambient, 0.f, WideJitter).Delay >= 0.f);
	}

	// Volume 0.55 + 0.45 B.
	TestNearlyEqual(TEXT("Brightness 1: volume 1"), LBAudioLogic::PlanThunder(1.f, ELBFlashReason::Ambient, 0.5f, P).Volume, 1.f, 1.0e-4f);
	TestNearlyEqual(TEXT("Brightness 0: volume 0.55"), LBAudioLogic::PlanThunder(0.f, ELBFlashReason::Ambient, 0.5f, P).Volume, 0.55f, 1.0e-4f);
	TestNearlyEqual(TEXT("Brightness 0.4: volume 0.73"), LBAudioLogic::PlanThunder(0.4f, ELBFlashReason::Ambient, 0.5f, P).Volume, 0.73f, 1.0e-4f);
	return true;
}

// =====================================================================================================================
// MusicTargets
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioMusicTargetsTest, "LastBell.Audio.Logic.MusicTargets", LB_AUDIO_TEST_FLAGS)
bool FLBAudioMusicTargetsTest::RunTest(const FString& Parameters)
{
	const LBAudioLogic::FMusicParams P; // stage >= 3, within 2500 cm, the plan's levels

	struct FRow { ELBWardenState State; float Tension; const TCHAR* Name; };
	const FRow Rows[] = {
		{ ELBWardenState::Dormant, 0.f, TEXT("Dormant") },
		{ ELBWardenState::Patrol, 0.25f, TEXT("Patrol") },
		{ ELBWardenState::Investigate, 0.6f, TEXT("Investigate") },
		{ ELBWardenState::Suspicious, 0.5f, TEXT("Suspicious") },
		{ ELBWardenState::Search, 0.8f, TEXT("Search") },
		{ ELBWardenState::Return, 0.15f, TEXT("Return") },
	};
	for (const FRow& Row : Rows)
	{
		const LBAudioLogic::FMusicTargets T = LBAudioLogic::MusicTargets(Row.State, 4, 1000.f, P);
		TestNearlyEqual(FString::Printf(TEXT("%s at stage 4, 1000 cm: tension %.2f"), Row.Name, Row.Tension), T.Tension, Row.Tension, 1.0e-4f);
		TestNearlyEqual(FString::Printf(TEXT("%s: no chase layer"), Row.Name), T.Chase, 0.f, 1.0e-4f);
	}

	// Below the minimum stage: nothing, for every state that is not a chase.
	for (const FRow& Row : Rows)
	{
		TestNearlyEqual(FString::Printf(TEXT("%s at stage 2: silent"), Row.Name), LBAudioLogic::MusicTargets(Row.State, 2, 1000.f, P).Tension, 0.f, 1.0e-4f);
		TestNearlyEqual(FString::Printf(TEXT("%s at stage 3 (the minimum): the level"), Row.Name), LBAudioLogic::MusicTargets(Row.State, 3, 1000.f, P).Tension, Row.Tension, 1.0e-4f);
	}

	// Too far: nothing.
	TestNearlyEqual(TEXT("Search at 2500 cm (the limit): the level"), LBAudioLogic::MusicTargets(ELBWardenState::Search, 4, 2500.f, P).Tension, 0.8f, 1.0e-4f);
	TestNearlyEqual(TEXT("Search at 2501 cm: silent"), LBAudioLogic::MusicTargets(ELBWardenState::Search, 4, 2501.f, P).Tension, 0.f, 1.0e-4f);

	// A chase: tension 0.4, chase 1, whatever the stage and the distance. Attack is the same.
	for (const ELBWardenState State : { ELBWardenState::Chase, ELBWardenState::Attack })
	{
		const LBAudioLogic::FMusicTargets Near = LBAudioLogic::MusicTargets(State, 4, 500.f, P);
		TestNearlyEqual(TEXT("Chase: tension 0.4"), Near.Tension, 0.4f, 1.0e-4f);
		TestNearlyEqual(TEXT("Chase: the chase layer at 1"), Near.Chase, 1.f, 1.0e-4f);
		const LBAudioLogic::FMusicTargets Far = LBAudioLogic::MusicTargets(State, 0, 90000.f, P);
		TestNearlyEqual(TEXT("Chase at stage 0, far away: still tension 0.4"), Far.Tension, 0.4f, 1.0e-4f);
		TestNearlyEqual(TEXT("Chase at stage 0, far away: still the chase layer"), Far.Chase, 1.f, 1.0e-4f);
	}
	LBAudioLogic::FMusicParams Quiet = P;
	Quiet.ChaseLevel = 0.7f;
	TestNearlyEqual(TEXT("ChaseLevel sets the chase layer"), LBAudioLogic::MusicTargets(ELBWardenState::Chase, 4, 100.f, Quiet).Chase, 0.7f, 1.0e-4f);
	return true;
}

// =====================================================================================================================
// Stress and breath
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioStressTest, "LastBell.Audio.Logic.Stress", LB_AUDIO_TEST_FLAGS)
bool FLBAudioStressTest::RunTest(const FString& Parameters)
{
	const LBAudioLogic::FStressParams P; // chase 1, near search 0.6 within 1500, sprint +0.3, decay 0.25, rise 0.6, darkness 0.15 / 0.55, candle out 0.35

	// Rises toward the Warden's level, never past it.
	{
		LBAudioLogic::FStressInputs Chase;
		Chase.WardenState = ELBWardenState::Chase;
		Chase.WardenDistance = 800.f;
		TestNearlyEqual(TEXT("Chase target is 1"), LBAudioLogic::StressTarget(Chase, P), 1.f, 1.0e-4f);
		float S = 0.f;
		S = LBAudioLogic::Stress(S, Chase, 0.5f, P);
		TestNearlyEqual(TEXT("It rises at Rise per second (0.6 * 0.5)"), S, 0.3f, 1.0e-4f);
		for (int32 Step = 0; Step < 100; ++Step)
		{
			S = LBAudioLogic::Stress(S, Chase, 0.1f, P);
		}
		TestNearlyEqual(TEXT("It stops at the target"), S, 1.f, 1.0e-4f);

		// Decays after the chase at 0.25 per second, down to the floor.
		const LBAudioLogic::FStressInputs Calm;
		S = LBAudioLogic::Stress(S, Calm, 1.f, P);
		TestNearlyEqual(TEXT("It decays at 0.25 per second"), S, 0.75f, 1.0e-4f);
		for (int32 Step = 0; Step < 100; ++Step)
		{
			S = LBAudioLogic::Stress(S, Calm, 0.1f, P);
		}
		TestNearlyEqual(TEXT("It decays to zero"), S, 0.f, 1.0e-4f);
	}

	// A Warden near and searching: 0.6. Too far, or not searching: nothing.
	{
		LBAudioLogic::FStressInputs Near;
		Near.WardenState = ELBWardenState::Search;
		Near.WardenDistance = 1000.f;
		TestNearlyEqual(TEXT("Search within 1500 cm: 0.6"), LBAudioLogic::StressTarget(Near, P), 0.6f, 1.0e-4f);
		Near.WardenState = ELBWardenState::Investigate;
		TestNearlyEqual(TEXT("Investigate within 1500 cm: 0.6"), LBAudioLogic::StressTarget(Near, P), 0.6f, 1.0e-4f);
		Near.WardenState = ELBWardenState::Suspicious;
		TestNearlyEqual(TEXT("Suspicious within 1500 cm: 0.6"), LBAudioLogic::StressTarget(Near, P), 0.6f, 1.0e-4f);
		Near.WardenDistance = 1600.f;
		TestNearlyEqual(TEXT("Suspicious at 1600 cm: 0"), LBAudioLogic::StressTarget(Near, P), 0.f, 1.0e-4f);
		Near.WardenDistance = 500.f;
		Near.WardenState = ELBWardenState::Patrol;
		TestNearlyEqual(TEXT("Patrol nearby: 0"), LBAudioLogic::StressTarget(Near, P), 0.f, 1.0e-4f);
	}

	// A sprint adds 0.3 while its bonus runs.
	{
		LBAudioLogic::FStressInputs Sprint;
		Sprint.bSprintBonus = true;
		TestNearlyEqual(TEXT("Sprinting alone: 0.3"), LBAudioLogic::StressTarget(Sprint, P), 0.3f, 1.0e-4f);
		Sprint.WardenState = ELBWardenState::Search;
		Sprint.WardenDistance = 800.f;
		TestNearlyEqual(TEXT("Sprinting with the Warden near: 0.9"), LBAudioLogic::StressTarget(Sprint, P), 0.9f, 1.0e-4f);
		Sprint.WardenState = ELBWardenState::Chase;
		TestNearlyEqual(TEXT("Sprinting in a chase: capped at 1"), LBAudioLogic::StressTarget(Sprint, P), 1.f, 1.0e-4f);
	}

	// Darkness: zone darkness times 0.15 lit, 0.55 with the candle out.
	{
		LBAudioLogic::FStressInputs Crypt;
		Crypt.ZoneDarkness = 1.f;
		Crypt.bCandleLit = true;
		TestNearlyEqual(TEXT("The crypt with the candle lit: 0.15"), LBAudioLogic::StressTarget(Crypt, P), 0.15f, 1.0e-4f);
		Crypt.bCandleLit = false;
		TestNearlyEqual(TEXT("The crypt with the candle out: 0.55"), LBAudioLogic::StressTarget(Crypt, P), 0.55f, 1.0e-4f);
		LBAudioLogic::FStressInputs Cloister = Crypt;
		Cloister.ZoneDarkness = 0.2f;
		TestNearlyEqual(TEXT("The cloister with the candle out: 0.2 * 0.55"), LBAudioLogic::StressTarget(Cloister, P), 0.11f, 1.0e-4f);
		LBAudioLogic::FStressInputs CryptLit = Crypt;
		CryptLit.bCandleLit = true;
		TestTrue(TEXT("Unlit is more stressful than lit in the same place"), LBAudioLogic::StressTarget(Crypt, P) > LBAudioLogic::StressTarget(CryptLit, P));

		// The darkness is a floor under the Warden's level, not added to it.
		LBAudioLogic::FStressInputs Both = Crypt;
		Both.WardenState = ELBWardenState::Chase;
		TestNearlyEqual(TEXT("A chase in the dark: still 1 (the darkness is a floor)"), LBAudioLogic::StressTarget(Both, P), 1.f, 1.0e-4f);

		// Lit against unlit, stepped: the unlit level is the higher one after a few seconds.
		float Lit = 0.f;
		float Unlit = 0.f;
		LBAudioLogic::FStressInputs LitInputs = Crypt;
		LitInputs.bCandleLit = true;
		for (int32 Step = 0; Step < 50; ++Step)
		{
			Lit = LBAudioLogic::Stress(Lit, LitInputs, 0.1f, P);
			Unlit = LBAudioLogic::Stress(Unlit, Crypt, 0.1f, P);
		}
		TestTrue(FString::Printf(TEXT("After 5 s in the crypt: unlit %.2f is above lit %.2f"), Unlit, Lit), Unlit > Lit + 0.3f);
	}

	// The candle-out impulse adds 0.35 at once and then decays at 0.25 per second.
	{
		LBAudioLogic::FStressInputs Out;
		Out.bCandleOutImpulse = true;
		float S = LBAudioLogic::Stress(0.1f, Out, 0.f, P);
		TestNearlyEqual(TEXT("The impulse adds 0.35 at once (zero delta)"), S, 0.45f, 1.0e-4f);
		Out.bCandleOutImpulse = false;
		S = LBAudioLogic::Stress(S, Out, 1.f, P);
		TestNearlyEqual(TEXT("Then it decays at 0.25 per second"), S, 0.2f, 1.0e-4f);
		Out.bCandleOutImpulse = true;
		TestNearlyEqual(TEXT("The impulse cannot take the level past 1"), LBAudioLogic::Stress(0.9f, Out, 0.f, P), 1.f, 1.0e-4f);
	}

	// Breath tiers: calm from 0.3, heavy from 0.55, panic from 0.85.
	{
		const LBAudioLogic::FBreathThresholds T;
		TestEqual(TEXT("0.29: no breath"), LBAudioLogic::BreathTier(0.29f, T), 0);
		TestEqual(TEXT("0.3: calm"), LBAudioLogic::BreathTier(0.3f, T), 1);
		TestEqual(TEXT("0.54: calm"), LBAudioLogic::BreathTier(0.54f, T), 1);
		TestEqual(TEXT("0.55: heavy"), LBAudioLogic::BreathTier(0.55f, T), 2);
		TestEqual(TEXT("0.84: heavy"), LBAudioLogic::BreathTier(0.84f, T), 2);
		TestEqual(TEXT("0.85: panic"), LBAudioLogic::BreathTier(0.85f, T), 3);
		TestEqual(TEXT("1: panic"), LBAudioLogic::BreathTier(1.f, T), 3);
	}
	return true;
}

// =====================================================================================================================
// AmbientTollPlan
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioAmbientTollTest, "LastBell.Audio.Logic.AmbientTollPlan", LB_AUDIO_TEST_FLAGS)
bool FLBAudioAmbientTollTest::RunTest(const FString& Parameters)
{
	const LBAudioLogic::FTollParams P; // 240..420 s, 1..2 strikes, gap 90 s, max tension 0.5, retry 30..60 s
	const double Beat = -1.0e9; // long ago

	// Not due yet: nothing changes.
	{
		const LBAudioLogic::FAmbientTollDecision D = LBAudioLogic::AmbientTollPlan(100.0, 300.0, Beat, false, 0.f, 2, false, 0.5f, 0.5f, P);
		TestFalse(TEXT("Before the due time: no toll"), D.bPlay);
		TestEqual(TEXT("Before the due time: the due time is kept"), D.NextTime, 300.0);
	}

	// Due: it tolls the current stage, 1 or 2 strikes, and the next one is 240..420 s later.
	{
		const LBAudioLogic::FAmbientTollDecision Low = LBAudioLogic::AmbientTollPlan(300.0, 300.0, Beat, false, 0.f, 3, false, 0.f, 0.f, P);
		TestTrue(TEXT("Due: a toll"), Low.bPlay);
		TestEqual(TEXT("It tolls the current stage"), Low.Stage, 3);
		TestEqual(TEXT("Rand 0: one strike"), Low.Strikes, 1);
		TestEqual(TEXT("Rand 0: the next toll is 240 s later"), Low.NextTime, 540.0);
		const LBAudioLogic::FAmbientTollDecision High = LBAudioLogic::AmbientTollPlan(300.0, 300.0, Beat, false, 0.f, 3, false, 0.99f, 1.f, P);
		TestEqual(TEXT("Rand 0.99: two strikes"), High.Strikes, 2);
		TestEqual(TEXT("Rand 1: the next toll is 420 s later"), High.NextTime, 720.0);
		bool bInside = true;
		bool bBothCounts[3] = { false, false, false };
		for (int32 Step = 0; Step <= 40; ++Step)
		{
			const LBAudioLogic::FAmbientTollDecision D = LBAudioLogic::AmbientTollPlan(1000.0, 1000.0, Beat, false, 0.f, 1, false, Step / 40.f, Step / 40.f, P);
			bInside &= D.NextTime >= 1240.0 - 1.0e-6 && D.NextTime <= 1420.0 + 1.0e-6 && D.Strikes >= 1 && D.Strikes <= 2;
			bBothCounts[FMath::Clamp(D.Strikes, 0, 2)] = true;
		}
		TestTrue(TEXT("Every draw: 1 or 2 strikes and a next time inside 240..420 s"), bInside);
		TestTrue(TEXT("Both strike counts come up"), bBothCounts[1] && bBothCounts[2]);
	}

	// Skipped (and retried in 30..60 s): a chase, tension above 0.5, within 90 s of a beat.
	{
		const LBAudioLogic::FAmbientTollDecision Chase = LBAudioLogic::AmbientTollPlan(300.0, 300.0, Beat, true, 0.f, 2, false, 0.5f, 0.f, P);
		TestFalse(TEXT("During a chase: skipped"), Chase.bPlay);
		TestEqual(TEXT("During a chase: retried in 30 s (rand 0)"), Chase.NextTime, 330.0);
		const LBAudioLogic::FAmbientTollDecision Tense = LBAudioLogic::AmbientTollPlan(300.0, 300.0, Beat, false, 0.51f, 2, false, 0.5f, 1.f, P);
		TestFalse(TEXT("Tension above 0.5: skipped"), Tense.bPlay);
		TestEqual(TEXT("Tension above 0.5: retried in 60 s (rand 1)"), Tense.NextTime, 360.0);
		const LBAudioLogic::FAmbientTollDecision AtLimit = LBAudioLogic::AmbientTollPlan(300.0, 300.0, Beat, false, 0.5f, 2, false, 0.5f, 0.5f, P);
		TestTrue(TEXT("Tension exactly 0.5: allowed"), AtLimit.bPlay);
		const LBAudioLogic::FAmbientTollDecision Recent = LBAudioLogic::AmbientTollPlan(300.0, 300.0, 250.0, false, 0.f, 2, false, 0.5f, 0.5f, P);
		TestFalse(TEXT("50 s after a beat toll: skipped"), Recent.bPlay);
		TestTrue(TEXT("50 s after a beat toll: retried in 30..60 s"), Recent.NextTime >= 330.0 && Recent.NextTime <= 360.0);
		const LBAudioLogic::FAmbientTollDecision After = LBAudioLogic::AmbientTollPlan(300.0, 300.0, 200.0, false, 0.f, 2, false, 0.5f, 0.5f, P);
		TestTrue(TEXT("100 s after a beat toll: allowed"), After.bPlay);
	}

	// None after the finale, and none with the tolls switched off.
	{
		const LBAudioLogic::FAmbientTollDecision Finale = LBAudioLogic::AmbientTollPlan(300.0, 300.0, Beat, false, 0.f, 5, true, 0.5f, 0.5f, P);
		TestFalse(TEXT("After the finale: no toll"), Finale.bPlay);
		TestTrue(TEXT("After the finale: never again"), Finale.NextTime >= 1.0e12);
		LBAudioLogic::FTollParams Off = P;
		Off.bEnabled = false;
		TestFalse(TEXT("Disabled: no toll"), LBAudioLogic::AmbientTollPlan(300.0, 300.0, Beat, false, 0.f, 2, false, 0.5f, 0.5f, Off).bPlay);
	}

	// A stage outside 1..5 is clamped.
	TestEqual(TEXT("Stage 9 is clamped to 5"), LBAudioLogic::AmbientTollPlan(300.0, 300.0, Beat, false, 0.f, 9, false, 0.5f, 0.5f, P).Stage, 5);
	return true;
}

// =====================================================================================================================
// BellPlan and the current stage
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioBellPlanTest, "LastBell.Audio.Logic.BellPlan", LB_AUDIO_TEST_FLAGS)
bool FLBAudioBellPlanTest::RunTest(const FString& Parameters)
{
	using namespace LBAudioUnitTest;
	const TArray<FLBBellBeat> Beats = MakeBeats(*this);

	struct FRow { const TCHAR* Tag; int32 Stage; int32 Strikes; float First; float Spacing; int32 Drone; };
	const FRow Expected[] = {
		{ TEXT("State.Event.Arrival"), 1, 3, 0.f, 4.5f, -1 }, // P17: the intro's first toll (owner 2026-11-11: no intro music)
		{ TEXT("State.Ritual.1"), 2, 3, 2.f, 4.5f, 1 },
		{ TEXT("State.Event.CryptEntered"), 1, 0, 0.f, 0.f, 0 },
		{ TEXT("State.Ritual.2"), 3, 3, 2.f, 4.5f, 2 },
		{ TEXT("State.Ritual.3"), 4, 3, 2.f, 4.0f, 1 },
		{ TEXT("State.Event.TowerTop"), 4, 4, 1.f, 3.5f, 2 },
		{ TEXT("State.Event.Finale"), 5, 5, 0.f, 2.0f, -1 },
	};
	for (const FRow& Row : Expected)
	{
		const LBAudioLogic::FBellPlan Plan = LBAudioLogic::BellPlan(Tag(Row.Tag), Beats);
		TestTrue(FString::Printf(TEXT("%s is a beat"), Row.Tag), Plan.bFound);
		TestEqual(FString::Printf(TEXT("%s: stage"), Row.Tag), Plan.Stage, Row.Stage);
		TestEqual(FString::Printf(TEXT("%s: strikes"), Row.Tag), Plan.Strikes, Row.Strikes);
		TestNearlyEqual(FString::Printf(TEXT("%s: first delay"), Row.Tag), Plan.FirstDelay, Row.First, 1.0e-4f);
		TestNearlyEqual(FString::Printf(TEXT("%s: spacing"), Row.Tag), Plan.Spacing, Row.Spacing, 1.0e-4f);
		TestEqual(FString::Printf(TEXT("%s: drone"), Row.Tag), Plan.Drone, Row.Drone);
	}

	// The strike times of a beat: First, First + Spacing, ...
	const LBAudioLogic::FBellPlan Ritual1 = LBAudioLogic::BellPlan(Tag(TEXT("State.Ritual.1")), Beats);
	TestNearlyEqual(TEXT("Ritual 1, strike 0 at 2 s"), Ritual1.StrikeDelay(0), 2.f, 1.0e-4f);
	TestNearlyEqual(TEXT("Ritual 1, strike 2 at 11 s"), Ritual1.StrikeDelay(2), 11.f, 1.0e-4f);

	// Tags that are not beats give nothing.
	const LBAudioLogic::FBellPlan Unknown = LBAudioLogic::BellPlan(Tag(TEXT("State.Chapel.Candle.1")), Beats);
	TestFalse(TEXT("A tag that is not a beat gives nothing"), Unknown.bFound);
	TestEqual(TEXT("...and no strikes"), Unknown.Strikes, 0);
	TestFalse(TEXT("An invalid tag gives nothing"), LBAudioLogic::BellPlan(FGameplayTag(), Beats).bFound);
	TestFalse(TEXT("An empty table gives nothing"), LBAudioLogic::BellPlan(Tag(TEXT("State.Ritual.1")), TArray<FLBBellBeat>()).bFound);

	// The current stage for ambient tolls: none 1, Ritual 1 gives 2, Ritual 2 gives 3, Ritual 3 or TowerTop gives 4.
	{
		FGameplayTagContainer State;
		TestEqual(TEXT("Nothing reached: stage 1"), LBAudioLogic::CurrentBellStage(Beats, State), 1);
		State.AddTag(Tag(TEXT("State.Event.CryptEntered")));
		TestEqual(TEXT("Only the crypt entered: stage 1"), LBAudioLogic::CurrentBellStage(Beats, State), 1);
		State.AddTag(Tag(TEXT("State.Ritual.1")));
		TestEqual(TEXT("Ritual 1: stage 2"), LBAudioLogic::CurrentBellStage(Beats, State), 2);
		State.AddTag(Tag(TEXT("State.Ritual.2")));
		TestEqual(TEXT("Ritual 2: stage 3"), LBAudioLogic::CurrentBellStage(Beats, State), 3);
		State.AddTag(Tag(TEXT("State.Ritual.3")));
		TestEqual(TEXT("Ritual 3: stage 4"), LBAudioLogic::CurrentBellStage(Beats, State), 4);
		FGameplayTagContainer Tower;
		Tower.AddTag(Tag(TEXT("State.Event.TowerTop")));
		TestEqual(TEXT("The tower top: stage 4"), LBAudioLogic::CurrentBellStage(Beats, Tower), 4);
	}

	// FillPlanDefaults writes the same table.
	{
		ULBAudioSettings* Settings = NewObject<ULBAudioSettings>(GetTransientPackage());
		Settings->FillPlanDefaults();
		TestEqual(TEXT("FillPlanDefaults: seven beats (the six of P16 and the P17 Arrival beat)"), Settings->BellBeats.Num(), 7);
		for (const FRow& Row : Expected)
		{
			const LBAudioLogic::FBellPlan Plan = LBAudioLogic::BellPlan(Tag(Row.Tag), Settings->BellBeats);
			TestTrue(FString::Printf(TEXT("FillPlanDefaults: %s"), Row.Tag), Plan.bFound && Plan.Stage == Row.Stage && Plan.Strikes == Row.Strikes && Plan.Drone == Row.Drone
				&& FMath::IsNearlyEqual(Plan.FirstDelay, Row.First) && FMath::IsNearlyEqual(Plan.Spacing, Row.Spacing));
		}
		// The C++ defaults are the plan's numbers.
		TestNearlyEqual(TEXT("Default RainOutGain"), Settings->RainOutGain, 0.8f, 1.0e-6f);
		TestNearlyEqual(TEXT("Default RainInGain"), Settings->RainInGain, 0.55f, 1.0e-6f);
		TestNearlyEqual(TEXT("Default MixFadeSeconds"), Settings->MixFadeSeconds, 0.75f, 1.0e-6f);
		TestNearlyEqual(TEXT("Default ThunderDistance"), Settings->ThunderDistance, 6000.f, 1.0e-3f);
		TestNearlyEqual(TEXT("Default AmbientTollVolume"), Settings->AmbientTollVolume, 0.5f, 1.0e-6f);
		TestNearlyEqual(TEXT("Default AmbientTollGapAfterBeat"), Settings->AmbientTollGapAfterBeat, 90.f, 1.0e-6f);
		TestEqual(TEXT("Default MusicMinStage"), Settings->MusicMinStage, 3);
		TestNearlyEqual(TEXT("Default DarknessUnlit"), Settings->DarknessUnlit, 0.55f, 1.0e-6f);
		TestEqual(TEXT("Default DebugForceMusicState is -1"), Settings->DebugForceMusicState, -1);
		TestTrue(TEXT("The new-game toll is on by default"), Settings->bNewGameToll);
		TestTrue(TEXT("The ambient tolls are on by default"), Settings->bAmbientTolls);
	}
	return true;
}

// =====================================================================================================================
// PickVariant, Ease
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioPickVariantTest, "LastBell.Audio.Logic.PickVariant", LB_AUDIO_TEST_FLAGS)
bool FLBAudioPickVariantTest::RunTest(const FString& Parameters)
{
	TestEqual(TEXT("Count 1 returns 0"), LBAudioLogic::PickVariant(1, 0, 0.7f), 0);
	TestEqual(TEXT("Count 1 returns 0 whatever Last is"), LBAudioLogic::PickVariant(1, INDEX_NONE, 0.2f), 0);
	TestEqual(TEXT("Count 0 returns INDEX_NONE"), LBAudioLogic::PickVariant(0, INDEX_NONE, 0.2f), static_cast<int32>(INDEX_NONE));

	// Never the last one over 1000 draws, and every other one comes up.
	for (const int32 Count : { 2, 3, 4, 6 })
	{
		FRandomStream Stream(4242 + Count);
		int32 Last = INDEX_NONE;
		int32 Repeats = 0;
		TArray<int32> Seen;
		Seen.Init(0, Count);
		for (int32 Draw = 0; Draw < 1000; ++Draw)
		{
			const int32 Picked = LBAudioLogic::PickVariant(Count, Last, Stream.FRand());
			if (Picked < 0 || Picked >= Count)
			{
				AddError(FString::Printf(TEXT("Count %d: index %d out of range"), Count, Picked));
				return true;
			}
			Repeats += Picked == Last ? 1 : 0;
			++Seen[Picked];
			Last = Picked;
		}
		TestEqual(FString::Printf(TEXT("Count %d: no repeat in 1000 draws"), Count), Repeats, 0);
		bool bAll = true;
		for (const int32 Hits : Seen)
		{
			bAll &= Hits > 0;
		}
		TestTrue(FString::Printf(TEXT("Count %d: every variant comes up"), Count), bAll);
	}

	// Edge draws: Rand 0 and Rand 1 (and beyond) stay in range and avoid Last.
	for (int32 Last = 0; Last < 4; ++Last)
	{
		for (const float Rand : { 0.f, 0.999999f, 1.f, 5.f, -1.f })
		{
			const int32 Picked = LBAudioLogic::PickVariant(4, Last, Rand);
			TestTrue(FString::Printf(TEXT("Last %d, rand %.2f: in range and not Last"), Last, Rand), Picked >= 0 && Picked < 4 && Picked != Last);
		}
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioEaseTest, "LastBell.Audio.Logic.Ease", LB_AUDIO_TEST_FLAGS)
bool FLBAudioEaseTest::RunTest(const FString& Parameters)
{
	TestNearlyEqual(TEXT("Rising: 1 / InSeconds per second"), LBAudioLogic::Ease(0.f, 1.f, 2.f, 4.f, 0.5f), 0.25f, 1.0e-5f);
	TestNearlyEqual(TEXT("Falling: 1 / OutSeconds per second"), LBAudioLogic::Ease(1.f, 0.f, 2.f, 4.f, 0.5f), 0.875f, 1.0e-5f);
	TestNearlyEqual(TEXT("No overshoot upward"), LBAudioLogic::Ease(0.9f, 1.f, 1.f, 1.f, 5.f), 1.f, 1.0e-6f);
	TestNearlyEqual(TEXT("No overshoot downward"), LBAudioLogic::Ease(0.1f, 0.f, 1.f, 1.f, 5.f), 0.f, 1.0e-6f);
	TestNearlyEqual(TEXT("At the target it stays"), LBAudioLogic::Ease(0.4f, 0.4f, 1.f, 1.f, 1.f), 0.4f, 1.0e-6f);
	TestNearlyEqual(TEXT("A zero fade-in jumps up"), LBAudioLogic::Ease(0.f, 0.8f, 0.f, 3.f, 0.01f), 0.8f, 1.0e-6f);
	TestNearlyEqual(TEXT("A zero fade-out jumps down"), LBAudioLogic::Ease(0.8f, 0.f, 3.f, 0.f, 0.01f), 0.f, 1.0e-6f);
	TestNearlyEqual(TEXT("Asymmetric: the way up is faster than the way down"), LBAudioLogic::Ease(0.5f, 1.f, 1.f, 10.f, 0.1f) - 0.5f, 0.1f, 1.0e-5f);
	// A fade over exactly InSeconds.
	float Level = 0.f;
	for (int32 Step = 0; Step < 30; ++Step)
	{
		Level = LBAudioLogic::Ease(Level, 1.f, 3.f, 8.f, 0.1f);
	}
	TestNearlyEqual(TEXT("A 3 s fade-in is complete after 3 s of steps"), Level, 1.f, 1.0e-4f);
	return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS
