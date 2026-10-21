#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

#include "Components/LBInteractableComponent.h"
#include "Engine/GameInstance.h"
#include "LBGameplayTags.h"
#include "Puzzles/LBPuzzleLogic.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "Tests/LBTestSink.h"
#include "UObject/StrongObjectPtr.h"

// Pure-logic unit tests for the Phase 4 puzzle framework (P4-001). Component behaviour in a live world is covered by
// LastBell.Functional.Puzzles.* (LBPuzzleFunctionalTests.cpp).

#define LB_TEST_FLAGS (EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

namespace
{
	TArray<FGameplayTag> ThreeSteps()
	{
		return { LBTags::State_Warden_Stage_1, LBTags::State_Warden_Stage_2, LBTags::State_Warden_Stage_3 };
	}

	FGameplayTagContainer Make(std::initializer_list<FGameplayTag> Tags)
	{
		FGameplayTagContainer Out;
		for (const FGameplayTag& Tag : Tags)
		{
			Out.AddTag(Tag);
		}
		return Out;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBSequenceLogicTest, "LastBell.Puzzles.Sequence.Logic", LB_TEST_FLAGS)
bool FLBSequenceLogicTest::RunTest(const FString& Parameters)
{
	const TArray<FGameplayTag> Steps = ThreeSteps();
	const FGameplayTag S1 = Steps[0], S2 = Steps[1], S3 = Steps[2];

	// Correct order: every prefix is valid and progress grows by one each time, the full set is a solve.
	FGameplayTagContainer State;
	FLBSequenceLogic::FEval Eval = FLBSequenceLogic::Evaluate(Steps, State);
	TestEqual(TEXT("Empty: progress"), Eval.Progress, 0);
	TestTrue(TEXT("Empty: valid"), Eval.bValidPrefix);
	State.AddTag(S1);
	Eval = FLBSequenceLogic::Evaluate(Steps, State);
	TestEqual(TEXT("After step 1: progress"), Eval.Progress, 1);
	TestTrue(TEXT("After step 1: valid"), Eval.bValidPrefix);
	State.AddTag(S2);
	Eval = FLBSequenceLogic::Evaluate(Steps, State);
	TestEqual(TEXT("After step 2: progress"), Eval.Progress, 2);
	TestTrue(TEXT("After step 2: valid"), Eval.bValidPrefix);
	State.AddTag(S3);
	Eval = FLBSequenceLogic::Evaluate(Steps, State);
	TestEqual(TEXT("After step 3: progress equals step count (solved)"), Eval.Progress, Steps.Num());
	TestTrue(TEXT("After step 3: valid"), Eval.bValidPrefix);

	// Wrong order: the first step missing but a later one present is invalid, from any start.
	State = Make({ S2 });
	Eval = FLBSequenceLogic::Evaluate(Steps, State);
	TestEqual(TEXT("Step 2 first: progress 0"), Eval.Progress, 0);
	TestFalse(TEXT("Step 2 first: invalid"), Eval.bValidPrefix);
	State = Make({ S1, S3 });
	Eval = FLBSequenceLogic::Evaluate(Steps, State);
	TestEqual(TEXT("Steps 1 and 3: progress 1"), Eval.Progress, 1);
	TestFalse(TEXT("Steps 1 and 3 (skipped 2): invalid"), Eval.bValidPrefix);
	State = Make({ S3, S2, S1 });
	Eval = FLBSequenceLogic::Evaluate(Steps, State);
	TestTrue(TEXT("Container order is irrelevant: all three present is a valid full prefix"), Eval.bValidPrefix && Eval.Progress == 3);

	// A failure resets: removing every step tag returns to a valid, empty state.
	State = Make({ S1, S3 });
	State.RemoveTags(FLBSequenceLogic::ToContainer(Steps));
	Eval = FLBSequenceLogic::Evaluate(Steps, State);
	TestTrue(TEXT("After reset: valid and empty"), Eval.bValidPrefix && Eval.Progress == 0 && State.IsEmpty());

	// Unrelated tags never matter.
	State = Make({ S1, LBTags::State_Warden_Stage_6 });
	Eval = FLBSequenceLogic::Evaluate(Steps, State);
	TestTrue(TEXT("Unrelated tag ignored"), Eval.bValidPrefix && Eval.Progress == 1);

	// A mid-progress prefix (what a mid-puzzle save contains) validates and resumes where it stopped.
	State = Make({ S1, S2 });
	Eval = FLBSequenceLogic::Evaluate(Steps, State);
	TestTrue(TEXT("Mid-progress prefix valid"), Eval.bValidPrefix && Eval.Progress == 2);

	// Configuration validation.
	TestTrue(TEXT("Config valid"), FLBSequenceLogic::IsConfigValid(Steps));
	TestFalse(TEXT("Empty config invalid"), FLBSequenceLogic::IsConfigValid(TArray<FGameplayTag>()));
	TestFalse(TEXT("Duplicate step invalid"), FLBSequenceLogic::IsConfigValid({ S1, S2, S1 }));
	TestFalse(TEXT("Invalid tag invalid"), FLBSequenceLogic::IsConfigValid({ S1, FGameplayTag() }));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBDialLogicTest, "LastBell.Puzzles.Dial.Logic", LB_TEST_FLAGS)
bool FLBDialLogicTest::RunTest(const FString& Parameters)
{
	const TArray<FGameplayTag> Positions = ThreeSteps();

	TestEqual(TEXT("No position present"), FLBDialLogic::FindCurrentIndex(Positions, FGameplayTagContainer()), static_cast<int32>(INDEX_NONE));
	TestEqual(TEXT("NextIndex wraps"), FLBDialLogic::NextIndex(3, 2), 0);
	TestEqual(TEXT("NextIndex from none goes to 0"), FLBDialLogic::NextIndex(3, INDEX_NONE), 0);
	TestEqual(TEXT("NextIndex with no positions"), FLBDialLogic::NextIndex(0, 0), static_cast<int32>(INDEX_NONE));

	// Init: nothing present adds the initial position.
	FLBDialChange Init = FLBDialLogic::PlanInit(Positions, 1, FGameplayTagContainer());
	TestEqual(TEXT("Init adds InitialIndex tag"), Init.Add, Positions[1]);
	TestEqual(TEXT("Init index"), Init.NewIndex, 1);
	TestTrue(TEXT("Init removes nothing"), Init.Remove.IsEmpty());
	Init = FLBDialLogic::PlanInit(Positions, 99, FGameplayTagContainer());
	TestEqual(TEXT("Init clamps a too-large InitialIndex"), Init.NewIndex, 2);
	Init = FLBDialLogic::PlanInit(Positions, -4, FGameplayTagContainer());
	TestEqual(TEXT("Init clamps a negative InitialIndex"), Init.NewIndex, 0);

	// Init: exactly one present (a loaded save) is left alone, whatever InitialIndex says.
	Init = FLBDialLogic::PlanInit(Positions, 0, Make({ Positions[2] }));
	TestFalse(TEXT("Loaded position: nothing added"), Init.Add.IsValid());
	TestTrue(TEXT("Loaded position: nothing removed"), Init.Remove.IsEmpty());
	TestEqual(TEXT("Loaded position: index kept"), Init.NewIndex, 2);

	// Init: corrupt, several present: keep the lowest index, remove the others.
	Init = FLBDialLogic::PlanInit(Positions, 2, Make({ Positions[2], Positions[1] }));
	TestEqual(TEXT("Corrupt: lowest index kept"), Init.NewIndex, 1);
	TestFalse(TEXT("Corrupt: nothing added"), Init.Add.IsValid());
	TestTrue(TEXT("Corrupt: higher position removed"), Init.Remove.HasTagExact(Positions[2]) && Init.Remove.Num() == 1);
	Init = FLBDialLogic::PlanInit(Positions, 0, Make({ Positions[0], Positions[1], Positions[2] }));
	TestTrue(TEXT("Corrupt (all three): keeps index 0, removes both others"), Init.NewIndex == 0 && Init.Remove.Num() == 2 && !Init.Remove.HasTagExact(Positions[0]));

	// Cycling 0 -> 1 -> 2 -> 0 on a real container, applying each plan the way the component does.
	FGameplayTagContainer State = Make({ Positions[0] });
	const int32 Expected[] = { 1, 2, 0, 1 };
	for (const int32 ExpectedIndex : Expected)
	{
		const FLBDialChange Change = FLBDialLogic::PlanCycle(Positions, State);
		State.RemoveTags(Change.Remove);
		State.AddTag(Change.Add);
		TestEqual(TEXT("Cycle new index"), Change.NewIndex, ExpectedIndex);
		TestEqual(TEXT("Cycle leaves exactly one position tag"), State.Num(), 1);
		TestEqual(TEXT("Cycle current index matches"), FLBDialLogic::FindCurrentIndex(Positions, State), ExpectedIndex);
	}

	// Cycle from "no position" starts at 0; a single-position dial changes nothing.
	const FLBDialChange FromNone = FLBDialLogic::PlanCycle(Positions, FGameplayTagContainer());
	TestTrue(TEXT("Cycle from none adds position 0"), FromNone.NewIndex == 0 && FromNone.Add == Positions[0] && FromNone.Remove.IsEmpty());
	const TArray<FGameplayTag> Single = { Positions[0] };
	const FLBDialChange SingleChange = FLBDialLogic::PlanCycle(Single, Make({ Positions[0] }));
	TestTrue(TEXT("Single-position dial: no change"), SingleChange.NewIndex == 0 && !SingleChange.Add.IsValid() && SingleChange.Remove.IsEmpty());
	const FLBDialChange Empty = FLBDialLogic::PlanCycle(TArray<FGameplayTag>(), FGameplayTagContainer());
	TestEqual(TEXT("Empty dial: no index"), Empty.NewIndex, static_cast<int32>(INDEX_NONE));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBDerivedAvailabilityTest, "LastBell.Puzzles.DerivedSingleUseAvailability", LB_TEST_FLAGS)
bool FLBDerivedAvailabilityTest::RunTest(const FString& Parameters)
{
	// A single-use interactable with a ConsumedStateTag is available iff that tag is absent (consume -> unavailable -> reset -> available).
	ULBInteractableComponent* Comp = NewObject<ULBInteractableComponent>(GetTransientPackage());
	Comp->bSingleUse = true;
	Comp->ConsumedStateTag = LBTags::State_Warden_Stage_4;
	FGameplayTagContainer State;

	TestTrue(TEXT("Available before use"), Comp->PassesStateRequirements(State));
	State.AddTag(Comp->ConsumedStateTag);
	TestFalse(TEXT("Unavailable once the consumed tag is present"), Comp->PassesStateRequirements(State));
	TestTrue(TEXT("bEnabled is not what made it unavailable"), Comp->bEnabled);
	State.RemoveTag(Comp->ConsumedStateTag);
	TestTrue(TEXT("Available again after the tag is removed (puzzle reset)"), Comp->PassesStateRequirements(State));

	// bEnabled remains the independent designer switch.
	Comp->bEnabled = false;
	TestFalse(TEXT("Locked by bEnabled"), Comp->PassesStateRequirements(State));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBRemoveStatesTest, "LastBell.WorldState.RemoveStates", LB_TEST_FLAGS)
bool FLBRemoveStatesTest::RunTest(const FString& Parameters)
{
	ULBWorldStateSubsystem* Subsystem = NewObject<ULBWorldStateSubsystem>(NewObject<UGameInstance>(GetTransientPackage()));
	TStrongObjectPtr<ULBTestSink> Sink(NewObject<ULBTestSink>(GetTransientPackage()));
	Subsystem->OnStateChanged.AddDynamic(Sink.Get(), &ULBTestSink::HandleStateChanged);

	Subsystem->AddStates(Make({ LBTags::State_Warden_Stage_1, LBTags::State_Warden_Stage_2, LBTags::State_Warden_Stage_3 }));
	Sink->StateEvents.Reset();

	// Two present, one absent: removed together, one event per tag actually removed, none for the absent one.
	Subsystem->RemoveStates(Make({ LBTags::State_Warden_Stage_1, LBTags::State_Warden_Stage_3, LBTags::State_Warden_Stage_5 }));
	TestFalse(TEXT("Stage 1 removed"), Subsystem->HasState(LBTags::State_Warden_Stage_1));
	TestFalse(TEXT("Stage 3 removed"), Subsystem->HasState(LBTags::State_Warden_Stage_3));
	TestTrue(TEXT("Stage 2 untouched"), Subsystem->HasState(LBTags::State_Warden_Stage_2));
	TestEqual(TEXT("Events only for removed tags"), Sink->StateEvents.Num(), 2);
	for (const TPair<FGameplayTag, bool>& Event : Sink->StateEvents)
	{
		TestFalse(TEXT("Event is a removal"), Event.Value);
	}

	// Single pass: by the time any listener runs, all removals are already applied.
	Sink->StateEvents.Reset();
	Subsystem->RemoveStates(Make({ LBTags::State_Warden_Stage_2 }));
	TestEqual(TEXT("One more event"), Sink->StateEvents.Num(), 1);
	Subsystem->RemoveStates(Make({ LBTags::State_Warden_Stage_2 }));
	TestEqual(TEXT("Removing an absent tag fires nothing"), Sink->StateEvents.Num(), 1);

	// The argument may alias the live container.
	Subsystem->AddStates(Make({ LBTags::State_Warden_Stage_1, LBTags::State_Warden_Stage_2 }));
	Subsystem->RemoveStates(Subsystem->GetStateRef());
	TestEqual(TEXT("Removing the live container empties the state"), Subsystem->GetStateRef().Num(), 0);
	return true;
}

#endif
