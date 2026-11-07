#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

#include "GameplayTagContainer.h"
#include "Storm/LBStormLogic.h"
#include "Storm/LBStormSettings.h"
#include "Storm/LBStormTypes.h"
#include "UObject/StrongObjectPtr.h"

// P14-1: pure-logic unit tests of the storm and the story lights (LastBell.Storm.Logic.*). The subsystem, the zones and the light groups
// only gather facts and apply these results; their PIE tests are in LBStormFunctionalTests.cpp.

#define LB_TEST_FLAGS (EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

#define TEST_ENUM(What, Actual, Expected) TestEqual(What, static_cast<int32>(Actual), static_cast<int32>(Expected))

namespace
{
	FGameplayTag Tag(const TCHAR* Name)
	{
		return FGameplayTag::RequestGameplayTag(FName(Name), false);
	}

	/** Settings with the plan's tag tables filled, the way P14-2 creates DA_StormSettings. */
	TStrongObjectPtr<ULBStormSettings> MakePlanSettings()
	{
		TStrongObjectPtr<ULBStormSettings> Settings(NewObject<ULBStormSettings>(GetTransientPackage()));
		Settings->FillPlanTagDefaults();
		return Settings;
	}

	FGameplayTagContainer Present(std::initializer_list<const TCHAR*> Names)
	{
		FGameplayTagContainer Container;
		for (const TCHAR* Name : Names)
		{
			Container.AddTag(Tag(Name));
		}
		return Container;
	}

	/** Counts the local maxima of F over [0, End] sampled every Step: a plateau counts once. */
	int32 CountPeaks(const LBStormLogic::FFlashShape& Shape, float End, float Step, float& OutMax, float& OutMin)
	{
		int32 Peaks = 0;
		float Previous = 0.f;
		bool bRising = false;
		OutMax = 0.f;
		OutMin = 1.f;
		for (float T = 0.f; T <= End; T += Step)
		{
			const float F = LBStormLogic::EvaluateFlash(Shape, T);
			OutMax = FMath::Max(OutMax, F);
			OutMin = FMath::Min(OutMin, F);
			if (F > Previous + 1.0e-6f)
			{
				bRising = true;
			}
			else if (F < Previous - 1.0e-6f && bRising)
			{
				++Peaks;
				bRising = false;
			}
			Previous = F;
		}
		return Peaks;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormStoryIntensityTest, "LastBell.Storm.Logic.StoryIntensity", LB_TEST_FLAGS)
bool FLBStormStoryIntensityTest::RunTest(const FString& Parameters)
{
	const TStrongObjectPtr<ULBStormSettings> Settings = MakePlanSettings();
	// All eight story tags must resolve, or the table is not the plan's.
	TestEqual(TEXT("Eight story steps from the plan table"), Settings->StoryIntensity.Num(), 8);
	TestEqual(TEXT("Six scripted strikes from the plan table"), Settings->ScriptedStrikes.Num(), 6);

	const TArray<FLBStormStoryStep>& Steps = Settings->StoryIntensity;
	const float Default = Settings->DefaultIntensity;
	TestEqual(TEXT("Default intensity is 0.55"), Default, 0.55f);

	TestEqual(TEXT("No tag: the default"), LBStormLogic::StoryIntensity(Steps, FGameplayTagContainer(), Default), 0.55f);
	TestEqual(TEXT("CourtyardEntered: 0.60"), LBStormLogic::StoryIntensity(Steps, Present({ TEXT("State.Event.CourtyardEntered") }), Default), 0.60f);
	TestEqual(TEXT("Ritual.2 after the courtyard: the last present entry, 0.65"),
		LBStormLogic::StoryIntensity(Steps, Present({ TEXT("State.Event.CourtyardEntered"), TEXT("State.Ritual.2") }), Default), 0.65f);

	// Container order means nothing: the entry with the highest index in the list wins, whatever else is present.
	TestEqual(TEXT("Finale and the courtyard, listed finale first: 1.0"),
		LBStormLogic::StoryIntensity(Steps, Present({ TEXT("State.Event.Finale"), TEXT("State.Event.CourtyardEntered") }), Default), 1.0f);
	TestEqual(TEXT("CloisterEntered with the earlier Ritual.1: 0.8"),
		LBStormLogic::StoryIntensity(Steps, Present({ TEXT("State.Event.CloisterEntered"), TEXT("State.Ritual.1") }), Default), 0.8f);
	TestEqual(TEXT("A later tag alone (Ritual.3, nothing before it): 0.9"),
		LBStormLogic::StoryIntensity(Steps, Present({ TEXT("State.Ritual.3") }), Default), 0.9f);
	TestEqual(TEXT("Intensity can go down: Ritual.1 after the courtyard is 0.55"),
		LBStormLogic::StoryIntensity(Steps, Present({ TEXT("State.Event.CourtyardEntered"), TEXT("State.Ritual.1") }), Default), 0.55f);

	// Exact matching: a parent tag does not count its children.
	TArray<FLBStormStoryStep> ParentSteps;
	FLBStormStoryStep& Parent = ParentSteps.AddDefaulted_GetRef();
	Parent.Tag = Tag(TEXT("State.Ritual"));
	Parent.Intensity = 0.9f;
	if (TestTrue(TEXT("State.Ritual (the parent tag) resolves"), Parent.Tag.IsValid()))
	{
		TestEqual(TEXT("The child tag does not satisfy a parent step"), LBStormLogic::StoryIntensity(ParentSteps, Present({ TEXT("State.Ritual.1") }), 0.3f), 0.3f);
	}
	// An invalid tag in a step is skipped.
	TArray<FLBStormStoryStep> InvalidSteps;
	InvalidSteps.AddDefaulted();
	TestEqual(TEXT("An unset tag never matches"), LBStormLogic::StoryIntensity(InvalidSteps, Present({ TEXT("State.Ritual.1") }), 0.3f), 0.3f);

	// The rate: 0.5 to 1.0 at 0.02 per second takes 25 s.
	float Value = 0.5f;
	for (int32 Frame = 0; Frame < 60 * 25; ++Frame)
	{
		Value = LBStormLogic::MoveTowards(Value, 1.f, 0.02f, 1.f / 60.f);
	}
	TestNearlyEqual(TEXT("0.5 to 1.0 takes 25 s"), Value, 1.f, 0.002f);
	TestEqual(TEXT("MoveTowards never overshoots"), LBStormLogic::MoveTowards(0.99f, 1.f, 0.02f, 1.f), 1.f);
	TestEqual(TEXT("MoveTowards goes down too"), LBStormLogic::MoveTowards(0.8f, 0.5f, 0.02f, 1.f), 0.78f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormFlashEnvelopeTest, "LastBell.Storm.Logic.FlashEnvelope", LB_TEST_FLAGS)
bool FLBStormFlashEnvelopeTest::RunTest(const FString& Parameters)
{
	const LBStormLogic::FEnvelope Envelope;

	// Sheet: attack 0.08, hold 0.10, decay 0.25.
	const LBStormLogic::FFlashShape Sheet = LBStormLogic::MakeFlash(ELBFlashProfile::Sheet, 1.f, 0.1f, 0.1f, Envelope);
	TestEqual(TEXT("Sheet t = 0"), LBStormLogic::EvaluateFlash(Sheet, 0.f), 0.f);
	TestNearlyEqual(TEXT("Sheet t = 0.04 (halfway up the attack)"), LBStormLogic::EvaluateFlash(Sheet, 0.04f), 0.5f, 1.0e-4f);
	TestNearlyEqual(TEXT("Sheet t = 0.12 (in the hold)"), LBStormLogic::EvaluateFlash(Sheet, 0.12f), 1.f, 1.0e-4f);
	TestNearlyEqual(TEXT("Sheet t = 0.43 (one time constant into the decay)"), LBStormLogic::EvaluateFlash(Sheet, 0.43f), FMath::Exp(-1.f), 1.0e-4f);
	TestEqual(TEXT("Sheet before the start"), LBStormLogic::EvaluateFlash(Sheet, -0.5f), 0.f);

	// Every profile ends at its formula time: last pulse start + A + H + 5.3 tau, where v has just dropped under 0.005.
	const float Gap1 = 0.12f, Gap2 = 0.1f;
	const LBStormLogic::FFlashShape Double = LBStormLogic::MakeFlash(ELBFlashProfile::Double, 1.f, Gap1, Gap2, Envelope);
	const LBStormLogic::FFlashShape Triple = LBStormLogic::MakeFlash(ELBFlashProfile::Triple, 1.f, Gap1, Gap2, Envelope);
	TestNearlyEqual(TEXT("Sheet ends at 0.08 + 0.10 + 5.3 * 0.25"), LBStormLogic::FlashDuration(Sheet), 0.08f + 0.10f + 5.3f * 0.25f, 1.0e-4f);
	TestNearlyEqual(TEXT("Double ends at g + 0.03 + 0.04 + 5.3 * 0.12"), LBStormLogic::FlashDuration(Double), Gap1 + 0.03f + 0.04f + 5.3f * 0.12f, 1.0e-4f);
	TestNearlyEqual(TEXT("Triple ends at g1 + g2 + 0.03 + 0.04 + 5.3 * 0.12"), LBStormLogic::FlashDuration(Triple), Gap1 + Gap2 + 0.03f + 0.04f + 5.3f * 0.12f, 1.0e-4f);
	for (const LBStormLogic::FFlashShape* Shape : { &Sheet, &Double, &Triple })
	{
		const float End = LBStormLogic::FlashDuration(*Shape);
		TestTrue(TEXT("Just before the end the flash is still above 0.005"), LBStormLogic::EvaluateFlash(*Shape, End - 0.05f) > 0.005f);
		TestTrue(TEXT("At the end the flash is under 0.005"), LBStormLogic::EvaluateFlash(*Shape, End + 1.0e-3f) < 0.005f);
	}

	// Peaks: a Double has 2, a Triple has 3, a Sheet 1; never above Brightness; never negative.
	float Max = 0.f, Min = 0.f;
	TestEqual(TEXT("Sheet has 1 peak"), CountPeaks(Sheet, 3.f, 0.001f, Max, Min), 1);
	TestEqual(TEXT("Double has 2 peaks"), CountPeaks(Double, 3.f, 0.001f, Max, Min), 2);
	TestEqual(TEXT("Triple has 3 peaks"), CountPeaks(Triple, 3.f, 0.001f, Max, Min), 3);

	for (const float Brightness : { 0.3f, 0.8f, 1.f })
	{
		for (const ELBFlashProfile Profile : { ELBFlashProfile::Sheet, ELBFlashProfile::Double, ELBFlashProfile::Triple })
		{
			const LBStormLogic::FFlashShape Shape = LBStormLogic::MakeFlash(Profile, Brightness, Gap1, Gap2, Envelope);
			CountPeaks(Shape, 3.f, 0.001f, Max, Min);
			TestTrue(FString::Printf(TEXT("Maximum <= brightness %.1f (%.4f)"), Brightness, Max), Max <= Brightness + 1.0e-5f);
			TestTrue(TEXT("The maximum reaches the brightness (the middle pulse has peak 1)"), Max >= Brightness - 1.0e-3f);
			TestTrue(TEXT("F >= 0 everywhere"), Min >= 0.f);
		}
	}

	// A brightness above 1 is capped at 1 by the min(1, ...) in the formula.
	const LBStormLogic::FFlashShape Loud = LBStormLogic::MakeFlash(ELBFlashProfile::Sheet, 3.f, 0.1f, 0.1f, Envelope);
	TestEqual(TEXT("F is capped at 1"), LBStormLogic::EvaluateFlash(Loud, 0.12f), 1.f);

	// The Double's first pulse is the weaker one (0.55), the Triple's last is 0.7.
	TestNearlyEqual(TEXT("Double: first pulse peaks at 0.55"), LBStormLogic::EvaluateFlash(Double, 0.05f), 0.55f, 1.0e-4f);
	TestNearlyEqual(TEXT("Triple: first pulse peaks at 0.5"), LBStormLogic::EvaluateFlash(Triple, 0.05f), 0.5f, 1.0e-4f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormScheduleTest, "LastBell.Storm.Logic.Schedule", LB_TEST_FLAGS)
bool FLBStormScheduleTest::RunTest(const FString& Parameters)
{
	const LBStormLogic::FScheduleParams Params;
	float Min = 0.f, Max = 0.f;
	LBStormLogic::IntervalBounds(0.f, Params, Min, Max);
	TestNearlyEqual(TEXT("I = 0: min 30"), Min, 30.f, 1.0e-4f);
	TestNearlyEqual(TEXT("I = 0: max 60"), Max, 60.f, 1.0e-4f);
	LBStormLogic::IntervalBounds(0.5f, Params, Min, Max);
	TestNearlyEqual(TEXT("I = 0.5: min 18"), Min, 18.f, 1.0e-4f);
	TestNearlyEqual(TEXT("I = 0.5: max 37"), Max, 37.f, 1.0e-4f);
	LBStormLogic::IntervalBounds(1.f, Params, Min, Max);
	TestNearlyEqual(TEXT("I = 1: min 6"), Min, 6.f, 1.0e-4f);
	TestNearlyEqual(TEXT("I = 1: max 14"), Max, 14.f, 1.0e-4f);

	TestNearlyEqual(TEXT("Roll 0 gives the lower bound"), LBStormLogic::NextInterval(1.f, 0.f, Params, false), 6.f, 1.0e-4f);
	TestNearlyEqual(TEXT("Roll 1 gives the upper bound"), LBStormLogic::NextInterval(1.f, 1.f, Params, false), 14.f, 1.0e-4f);
	TestNearlyEqual(TEXT("The first flash waits half the interval"), LBStormLogic::NextInterval(1.f, 1.f, Params, true), 7.f, 1.0e-4f);

	// Seed 1401 gives the same sequence twice, and every interval is inside its bounds.
	auto Sequence = [&Params](float Intensity)
	{
		FRandomStream Stream(1401);
		TArray<float> Out;
		for (int32 Index = 0; Index < 40; ++Index)
		{
			Out.Add(LBStormLogic::NextInterval(Intensity, Stream.FRand(), Params, Index == 0));
		}
		return Out;
	};
	const TArray<float> A = Sequence(0.5f);
	const TArray<float> B = Sequence(0.5f);
	TestTrue(TEXT("Seed 1401 gives the same intervals twice"), A == B);
	LBStormLogic::IntervalBounds(0.5f, Params, Min, Max);
	bool bInBounds = true;
	for (int32 Index = 1; Index < A.Num(); ++Index)
	{
		bInBounds &= A[Index] >= Min - 1.0e-4f && A[Index] <= Max + 1.0e-4f;
	}
	TestTrue(TEXT("Every interval is inside [18, 37] at I = 0.5"), bInBounds);
	TestTrue(TEXT("The first one is scaled by 0.5"), A[0] >= Min * 0.5f - 1.0e-4f && A[0] <= Max * 0.5f + 1.0e-4f);

	// The minimum gap: a flash asked for inside the gap waits for it.
	TestNearlyEqual(TEXT("Asked 1 s while the last flash ends at 3 s: starts at 5.5"), LBStormLogic::EarliestStart(1.f, 3.f, 2.5f), 5.5f, 1.0e-4f);
	TestNearlyEqual(TEXT("Asked after the gap: unchanged"), LBStormLogic::EarliestStart(10.f, 3.f, 2.5f), 10.f, 1.0e-4f);
	TestNearlyEqual(TEXT("Asked exactly at the end of the gap: unchanged"), LBStormLogic::EarliestStart(5.5f, 3.f, 2.5f), 5.5f, 1.0e-4f);

	// A stream of requests, each asked for sooner than the gap allows: the gap between one flash's end and the next start holds.
	FRandomStream Stream(1401);
	const LBStormLogic::FEnvelope Envelope;
	float BusyUntil = -1000.f;
	float Clock = 0.f;
	bool bGapHolds = true;
	for (int32 Index = 0; Index < 50; ++Index)
	{
		Clock += Stream.FRandRange(0.f, 3.f);
		const float Start = LBStormLogic::EarliestStart(Clock, BusyUntil, 2.5f);
		bGapHolds &= Start >= BusyUntil + 2.5f - 1.0e-4f && Start >= Clock;
		const ELBFlashProfile Profile = LBStormLogic::PickProfile(Stream.FRand(), 0.5f, 0.35f, 0.15f);
		BusyUntil = Start + LBStormLogic::FlashDuration(LBStormLogic::MakeFlash(Profile, 1.f, Stream.FRandRange(0.07f, 0.16f), Stream.FRandRange(0.07f, 0.16f), Envelope));
	}
	TestTrue(TEXT("The minimum gap holds over 50 crowded requests"), bGapHolds);

	// Profile weights 0.5 / 0.35 / 0.15.
	TEST_ENUM(TEXT("Roll 0: Sheet"), LBStormLogic::PickProfile(0.f, 0.5f, 0.35f, 0.15f), ELBFlashProfile::Sheet);
	TEST_ENUM(TEXT("Roll 0.49: Sheet"), LBStormLogic::PickProfile(0.49f, 0.5f, 0.35f, 0.15f), ELBFlashProfile::Sheet);
	TEST_ENUM(TEXT("Roll 0.5: Double"), LBStormLogic::PickProfile(0.5f, 0.5f, 0.35f, 0.15f), ELBFlashProfile::Double);
	TEST_ENUM(TEXT("Roll 0.84: Double"), LBStormLogic::PickProfile(0.84f, 0.5f, 0.35f, 0.15f), ELBFlashProfile::Double);
	TEST_ENUM(TEXT("Roll 0.86: Triple"), LBStormLogic::PickProfile(0.86f, 0.5f, 0.35f, 0.15f), ELBFlashProfile::Triple);
	TEST_ENUM(TEXT("All weights zero: Sheet"), LBStormLogic::PickProfile(0.7f, 0.f, 0.f, 0.f), ELBFlashProfile::Sheet);

	// Ambient brightness: lerp(0.55, 1, roll) * lerp(0.7, 1, I).
	TestNearlyEqual(TEXT("Brightness floor: 0.55 * 0.7"), LBStormLogic::AmbientBrightness(0.f, 0.f, 0.55f, 0.7f), 0.385f, 1.0e-4f);
	TestNearlyEqual(TEXT("Brightness ceiling: 1"), LBStormLogic::AmbientBrightness(1.f, 1.f, 0.55f, 0.7f), 1.f, 1.0e-4f);

	// Directions are unit vectors, above the horizon.
	const FVector Direction = LBStormLogic::DirectionFromAngles(90.f, 30.f);
	TestNearlyEqual(TEXT("Direction is a unit vector"), static_cast<float>(Direction.Size()), 1.f, 1.0e-4f);
	TestNearlyEqual(TEXT("Elevation 30 degrees: z = 0.5"), static_cast<float>(Direction.Z), 0.5f, 1.0e-4f);
	const FVector Reveal = LBStormLogic::RevealDirection(FVector(1000.0, 0.0, -200.0), 20.f);
	TestNearlyEqual(TEXT("Reveal direction: flattened toward +X, raised 20 degrees"), static_cast<float>(Reveal.Z), FMath::Sin(FMath::DegreesToRadians(20.f)), 1.0e-4f);
	TestTrue(TEXT("Reveal direction points toward +X"), Reveal.X > 0.9 && FMath::Abs(Reveal.Y) < 1.0e-4);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormWindTest, "LastBell.Storm.Logic.Wind", LB_TEST_FLAGS)
bool FLBStormWindTest::RunTest(const FString& Parameters)
{
	const LBStormLogic::FWindParams Params;

	bool bInRange = true;
	float Mean[3] = { 0.f, 0.f, 0.f };
	const float Intensities[3] = { 0.f, 0.5f, 1.f };
	constexpr int32 Samples = 60 * 60; // 60 s at 60 Hz
	for (int32 Index = 0; Index < 3; ++Index)
	{
		float Sum = 0.f;
		for (int32 Frame = 0; Frame < Samples; ++Frame)
		{
			const float Strength = LBStormLogic::WindStrength(Intensities[Index], Frame / 60.f, Params);
			bInRange &= Strength >= 0.f && Strength <= 1.f;
			Sum += Strength;
		}
		Mean[Index] = Sum / Samples;
	}
	TestTrue(TEXT("Wind strength stays in [0, 1]"), bInRange);
	TestTrue(FString::Printf(TEXT("The 60 s mean rises with intensity (%.3f < %.3f < %.3f)"), Mean[0], Mean[1], Mean[2]), Mean[0] < Mean[1] && Mean[1] < Mean[2]);
	TestTrue(TEXT("Calm night still has some wind (mean at I = 0 is at least the base 0.2)"), Mean[0] >= 0.2f - 1.0e-3f);

	// Even the extremes are clamped (a huge gust coefficient cannot push it over 1).
	LBStormLogic::FWindParams Strong = Params;
	Strong.BaseHigh = 0.9f;
	Strong.GustHigh = 0.9f;
	bool bClamped = true;
	for (int32 Frame = 0; Frame < Samples; ++Frame)
	{
		bClamped &= LBStormLogic::WindStrength(1.f, Frame / 60.f, Strong) <= 1.f;
	}
	TestTrue(TEXT("Strength is clamped to 1"), bClamped);

	// The phase is continuous across the wrap: no step larger than 0.1 rad at 60 fps, measured modulo the wrap.
	float Phase = LBStormLogic::WindPhaseWrap - 1.f;
	bool bContinuous = true;
	bool bWrapped = false;
	bool bInWrapRange = true;
	for (int32 Frame = 0; Frame < 600; ++Frame)
	{
		const float Next = LBStormLogic::AdvanceWindPhase(Phase, 1.f, 1.f / 60.f, Params);
		float Step = Next - Phase;
		if (Step < -LBStormLogic::WindPhaseWrap * 0.5f)
		{
			bWrapped = true;
			Step += LBStormLogic::WindPhaseWrap;
		}
		bContinuous &= Step >= 0.f && Step <= 0.1f;
		bInWrapRange &= Next >= 0.f && Next < LBStormLogic::WindPhaseWrap;
		Phase = Next;
	}
	TestTrue(TEXT("The phase wrapped during the run"), bWrapped);
	TestTrue(TEXT("No phase step above 0.1 rad at 60 fps, wrap included"), bContinuous);
	TestTrue(TEXT("The phase stays in [0, 100 * 2 pi)"), bInWrapRange);
	TestNearlyEqual(TEXT("The wrap is 100 full turns"), LBStormLogic::WindPhaseWrap, 100.f * 2.f * UE_PI, 1.0e-2f);

	// Speed: 1.2 rad/s at strength 0, 2.4 at strength 1.
	TestNearlyEqual(TEXT("Phase speed at strength 0"), LBStormLogic::AdvanceWindPhase(0.f, 0.f, 1.f, Params), 1.2f, 1.0e-4f);
	TestNearlyEqual(TEXT("Phase speed at strength 1"), LBStormLogic::AdvanceWindPhase(0.f, 1.f, 1.f, Params), 2.4f, 1.0e-4f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormExposureTest, "LastBell.Storm.Logic.Exposure", LB_TEST_FLAGS)
bool FLBStormExposureTest::RunTest(const FString& Parameters)
{
	using LBStormLogic::FExposureEntry;
	TestEqual(TEXT("No zone: the default (open sky)"), LBStormLogic::ResolveExposure(TConstArrayView<FExposureEntry>(), 1.f), 1.f);
	TestEqual(TEXT("No zone: a different default"), LBStormLogic::ResolveExposure(TConstArrayView<FExposureEntry>(), 0.7f), 0.7f);

	const TArray<FExposureEntry> One = { { 0.35f, 1 } };
	TestEqual(TEXT("One zone"), LBStormLogic::ResolveExposure(One, 1.f), 0.35f);

	// The chapel (0.35, priority 1) under the crypt (0.0, priority 2): the higher priority wins.
	const TArray<FExposureEntry> Nested = { { 0.35f, 1 }, { 0.f, 2 } };
	TestEqual(TEXT("Highest priority wins"), LBStormLogic::ResolveExposure(Nested, 1.f), 0.f);
	const TArray<FExposureEntry> NestedReversed = { { 0.f, 2 }, { 0.35f, 1 } };
	TestEqual(TEXT("Highest priority wins whatever the order"), LBStormLogic::ResolveExposure(NestedReversed, 1.f), 0.f);
	const TArray<FExposureEntry> HighOpen = { { 0.3f, 1 }, { 1.f, 2 } };
	TestEqual(TEXT("A higher-priority open zone beats a lower-priority closed one"), LBStormLogic::ResolveExposure(HighOpen, 0.f), 1.f);

	// A tie takes the lowest exposure.
	const TArray<FExposureEntry> Tie = { { 0.6f, 2 }, { 0.25f, 2 }, { 0.9f, 2 }, { 0.1f, 1 } };
	TestEqual(TEXT("Tie: the lowest exposure"), LBStormLogic::ResolveExposure(Tie, 1.f), 0.25f);

	// The tower shaft (0.25, priority 3) beats the garth (1.0, priority 2) it stands in.
	const TArray<FExposureEntry> Tower = { { 1.f, 2 }, { 0.25f, 3 } };
	TestEqual(TEXT("Tower shaft over garth"), LBStormLogic::ResolveExposure(Tower, 1.f), 0.25f);

	// Out-of-range values are clamped.
	const TArray<FExposureEntry> Wild = { { 1.7f, 1 } };
	TestEqual(TEXT("Clamped to 1"), LBStormLogic::ResolveExposure(Wild, 1.f), 1.f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormRevealRuleTest, "LastBell.Storm.Logic.RevealRule", LB_TEST_FLAGS)
bool FLBStormRevealRuleTest::RunTest(const FString& Parameters)
{
	using LBStormLogic::ERevealCheck;
	using LBStormLogic::FRevealInputs;

	LBStormLogic::ERevealCheck Check = ERevealCheck::Disabled;
	const FRevealInputs Good;
	TestTrue(TEXT("All conditions true: a reveal"), LBStormLogic::ShouldReveal(Good, Check));
	TEST_ENUM(TEXT("All conditions true: the code is Reveal"), Check, ERevealCheck::Reveal);

	struct FCase
	{
		const TCHAR* Name;
		TFunction<void(FRevealInputs&)> Break;
		ERevealCheck Expected;
	};
	const FCase Cases[] = {
		{ TEXT("reveal disabled"), [](FRevealInputs& In) { In.bEnabled = false; }, ERevealCheck::Disabled },
		{ TEXT("intensity under the minimum"), [](FRevealInputs& In) { In.Intensity = 0.39f; }, ERevealCheck::LowIntensity },
		{ TEXT("no Warden"), [](FRevealInputs& In) { In.bWardenExists = false; }, ERevealCheck::NoWarden },
		{ TEXT("Warden dormant"), [](FRevealInputs& In) { In.bWardenDormant = true; }, ERevealCheck::Dormant },
		{ TEXT("too close (799 cm)"), [](FRevealInputs& In) { In.Distance = 799.f; }, ERevealCheck::TooClose },
		{ TEXT("too far (4001 cm)"), [](FRevealInputs& In) { In.Distance = 4001.f; }, ERevealCheck::TooFar },
		{ TEXT("outside the cone (31 degrees)"), [](FRevealInputs& In) { In.AngleDegrees = 31.f; }, ERevealCheck::OutOfCone },
		{ TEXT("line of sight blocked"), [](FRevealInputs& In) { In.bLineClear = false; }, ERevealCheck::Blocked },
		{ TEXT("exposure under the minimum"), [](FRevealInputs& In) { In.Exposure = 0.49f; }, ERevealCheck::LowExposure },
		{ TEXT("inside the cooldown (29.9 s)"), [](FRevealInputs& In) { In.SecondsSinceLastReveal = 29.9f; }, ERevealCheck::Cooldown },
		{ TEXT("a flash running or pending"), [](FRevealInputs& In) { In.bFlashBusy = true; }, ERevealCheck::Busy },
	};
	for (const FCase& Case : Cases)
	{
		FRevealInputs In = Good;
		Case.Break(In);
		ERevealCheck Result = ERevealCheck::Reveal;
		TestFalse(FString::Printf(TEXT("No reveal: %s"), Case.Name), LBStormLogic::ShouldReveal(In, Result));
		TEST_ENUM(*FString::Printf(TEXT("Reason code for: %s"), Case.Name), Result, Case.Expected);
	}

	// The limits are inclusive.
	FRevealInputs Edge = Good;
	Edge.Distance = 800.f;
	TestTrue(TEXT("Exactly 800 cm is allowed"), LBStormLogic::ShouldReveal(Edge, Check));
	Edge.Distance = 4000.f;
	TestTrue(TEXT("Exactly 4000 cm is allowed"), LBStormLogic::ShouldReveal(Edge, Check));
	Edge = Good;
	Edge.AngleDegrees = 30.f;
	TestTrue(TEXT("Exactly 30 degrees is allowed"), LBStormLogic::ShouldReveal(Edge, Check));
	Edge = Good;
	Edge.SecondsSinceLastReveal = 30.f;
	TestTrue(TEXT("Exactly 30 s since the last reveal is allowed"), LBStormLogic::ShouldReveal(Edge, Check));
	Edge = Good;
	Edge.Exposure = 0.5f;
	Edge.Intensity = 0.4f;
	TestTrue(TEXT("Exactly the minimum exposure and intensity are allowed"), LBStormLogic::ShouldReveal(Edge, Check));

	// Two conditions false: the first in the documented order is reported.
	FRevealInputs Two = Good;
	Two.bFlashBusy = true;
	Two.Distance = 100.f;
	LBStormLogic::ShouldReveal(Two, Check);
	TEST_ENUM(TEXT("Too close is reported before busy"), Check, ERevealCheck::TooClose);

	TestTrue(TEXT("Every code has a name"), FCString::Strlen(LBStormLogic::RevealCheckName(ERevealCheck::Blocked)) > 0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormLightRulesTest, "LastBell.Storm.Logic.LightRules", LB_TEST_FLAGS)
bool FLBStormLightRulesTest::RunTest(const FString& Parameters)
{
	TArray<FLBLightStateRule> Rules;
	{
		FLBLightStateRule& Flicker = Rules.AddDefaulted_GetRef();
		Flicker.RequiredTag = Tag(TEXT("State.Ritual.1"));
		Flicker.Mode = ELBLightStateMode::Flicker;
		Flicker.IntensityScale = 0.25f;
		Flicker.FlickerAmount = 0.45f;
		Flicker.FlickerSpeed = 7.f;
		FLBLightStateRule& Off = Rules.AddDefaulted_GetRef();
		Off.RequiredTag = Tag(TEXT("State.Ritual.2"));
		Off.Mode = ELBLightStateMode::Off;
		FLBLightStateRule& Dim = Rules.AddDefaulted_GetRef();
		Dim.RequiredTag = Tag(TEXT("State.Event.CloisterEntered"));
		Dim.Mode = ELBLightStateMode::Dim;
		Dim.IntensityScale = 0.5f;
	}
	if (!TestTrue(TEXT("The rule tags resolve"), Rules[0].RequiredTag.IsValid() && Rules[1].RequiredTag.IsValid() && Rules[2].RequiredTag.IsValid()))
	{
		return false;
	}

	// None present: On at scale 1.
	LBStormLogic::FLightRule Rule = LBStormLogic::SelectLightRule(Rules, FGameplayTagContainer());
	TEST_ENUM(TEXT("No rule present: On"), Rule.Mode, ELBLightStateMode::On);
	TestEqual(TEXT("No rule present: scale 1"), LBStormLogic::LightScaleAt(Rule, 3.f, 0.f), 1.f);

	// The last rule in the list whose tag is present wins, whatever the container order.
	Rule = LBStormLogic::SelectLightRule(Rules, Present({ TEXT("State.Ritual.1") }));
	TEST_ENUM(TEXT("Ritual.1: Flicker"), Rule.Mode, ELBLightStateMode::Flicker);
	Rule = LBStormLogic::SelectLightRule(Rules, Present({ TEXT("State.Ritual.1"), TEXT("State.Ritual.2") }));
	TEST_ENUM(TEXT("Ritual.1 and 2: the later rule, Off"), Rule.Mode, ELBLightStateMode::Off);
	Rule = LBStormLogic::SelectLightRule(Rules, Present({ TEXT("State.Ritual.2"), TEXT("State.Ritual.1") }));
	TEST_ENUM(TEXT("Container order does not matter: still Off"), Rule.Mode, ELBLightStateMode::Off);
	Rule = LBStormLogic::SelectLightRule(Rules, Present({ TEXT("State.Ritual.2"), TEXT("State.Event.CloisterEntered") }));
	TEST_ENUM(TEXT("Cloister rule is last in the list: Dim"), Rule.Mode, ELBLightStateMode::Dim);

	// Off gives 0 at any time; Dim gives its scale.
	const LBStormLogic::FLightRule Off = LBStormLogic::SelectLightRule(Rules, Present({ TEXT("State.Ritual.2") }));
	const LBStormLogic::FLightRule Dim = LBStormLogic::SelectLightRule(Rules, Present({ TEXT("State.Event.CloisterEntered") }));
	TestEqual(TEXT("Off: 0"), LBStormLogic::LightScaleAt(Off, 1.f, 0.f), 0.f);
	TestEqual(TEXT("Off: 0 later"), LBStormLogic::LightScaleAt(Off, 99.f, 5.f), 0.f);
	TestEqual(TEXT("Dim: its scale"), LBStormLogic::LightScaleAt(Dim, 1.f, 0.f), 0.5f);

	// Flicker stays inside [scale * (1 - amount), scale], for many times and per-light seeds.
	const LBStormLogic::FLightRule Flicker = LBStormLogic::SelectLightRule(Rules, Present({ TEXT("State.Ritual.1") }));
	const float Floor = 0.25f * (1.f - 0.45f);
	bool bInside = true;
	float LowSeen = 1.f, HighSeen = 0.f;
	for (const float Seed : { 0.f, 13.7f, 91.4f })
	{
		for (int32 Index = 0; Index < 3000; ++Index)
		{
			const float Scale = LBStormLogic::LightScaleAt(Flicker, Index / 60.f, Seed);
			bInside &= Scale >= Floor - 1.0e-5f && Scale <= 0.25f + 1.0e-5f;
			LowSeen = FMath::Min(LowSeen, Scale);
			HighSeen = FMath::Max(HighSeen, Scale);
		}
	}
	TestTrue(TEXT("Flicker stays within [scale * (1 - amount), scale]"), bInside);
	TestTrue(FString::Printf(TEXT("Flicker actually moves (%.3f .. %.3f)"), LowSeen, HighSeen), HighSeen - LowSeen > 0.02f);

	// The fade: exact at both ends, the gutter in between never brings it above the straight blend.
	TestEqual(TEXT("Fade starts at From"), LBStormLogic::FadeScale(1.f, 0.f, 0.f, 12.3f), 1.f);
	TestEqual(TEXT("Fade ends at To"), LBStormLogic::FadeScale(1.f, 0.f, 1.f, 12.3f), 0.f);
	TestEqual(TEXT("Fade ends at To (not zero)"), LBStormLogic::FadeScale(0.f, 1.f, 1.f, 4.f), 1.f);
	bool bBelowBlend = true;
	for (int32 Index = 0; Index <= 100; ++Index)
	{
		const float Alpha = Index / 100.f;
		const float Value = LBStormLogic::FadeScale(1.f, 0.f, Alpha, Index * 0.07f);
		bBelowBlend &= Value >= 0.f && Value <= (1.f - Alpha) + 1.0e-5f;
	}
	TestTrue(TEXT("The fade never rises above the straight blend"), bBelowBlend);
	const float Gutter = LBStormLogic::GutterNoise(3.3f);
	TestTrue(TEXT("Gutter noise in [0, 1]"), Gutter >= 0.f && Gutter <= 1.f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormScaleGlowTest, "LastBell.Storm.Logic.ScaleGlow", LB_TEST_FLAGS)
bool FLBStormScaleGlowTest::RunTest(const FString& Parameters)
{
	const FLinearColor Base(0.8f, 0.4f, 0.2f, 0.5f);

	// On: current = base gives the base colour.
	FLinearColor Value = LBStormLogic::ScaleGlow(Base, 300.f, 300.f);
	TestTrue(TEXT("On: the base colour"), Value.Equals(Base, 1.0e-6f));

	// Off: black, alpha kept.
	Value = LBStormLogic::ScaleGlow(Base, 0.f, 300.f);
	TestTrue(TEXT("Off: RGB 0"), Value.R == 0.f && Value.G == 0.f && Value.B == 0.f);
	TestEqual(TEXT("Off: alpha kept"), Value.A, 0.5f);

	// Dim 0.3: RGB scaled, alpha kept.
	Value = LBStormLogic::ScaleGlow(Base, 90.f, 300.f);
	TestTrue(TEXT("Dim 0.3: RGB * 0.3"), Value.Equals(FLinearColor(0.24f, 0.12f, 0.06f, 0.5f), 1.0e-5f));

	// A base of 0 gives black (no division by zero), whatever the current value.
	Value = LBStormLogic::ScaleGlow(Base, 50.f, 0.f);
	TestTrue(TEXT("Base intensity 0: black"), Value.R == 0.f && Value.G == 0.f && Value.B == 0.f);
	TestEqual(TEXT("Base intensity 0: alpha kept"), Value.A, 0.5f);

	// Brighter than the base (a flash) clamps to the base colour; a negative current clamps to black.
	Value = LBStormLogic::ScaleGlow(Base, 900.f, 300.f);
	TestTrue(TEXT("Current above the base clamps to s = 1"), Value.Equals(Base, 1.0e-6f));
	Value = LBStormLogic::ScaleGlow(Base, -5.f, 300.f);
	TestTrue(TEXT("Negative current clamps to s = 0"), Value.R == 0.f && Value.G == 0.f && Value.B == 0.f);
	return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS
