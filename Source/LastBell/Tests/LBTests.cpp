#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

#include "Systems/LBWorldState.h"
#include "Objectives/LBObjectiveChainData.h"
#include "Save/LBSaveGame.h"
#include "Save/LBSaveIdRegistry.h"
#include "Components/LBInteractableComponent.h"
#include "LBGameplayTags.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/GameInstance.h"
#include "Save/LBSaveSubsystem.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "Systems/LBGameSettings.h"
#include "Objectives/LBObjectiveSubsystem.h"

#define LB_TEST_FLAGS (EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWorldStateTest, "LastBell.WorldState.AddRemoveResetReplace", LB_TEST_FLAGS)
bool FLBWorldStateTest::RunTest(const FString& Parameters)
{
	FLBWorldState State;
	const FGameplayTag A = LBTags::State_Warden_Stage_1;
	const FGameplayTag B = LBTags::State_Warden_Stage_2;

	TestTrue(TEXT("Add new tag changes"), State.Add(A));
	TestFalse(TEXT("Add duplicate does not change"), State.Add(A));
	TestFalse(TEXT("Add invalid does not change"), State.Add(FGameplayTag()));
	TestTrue(TEXT("Has after add"), State.Has(A));
	TestFalse(TEXT("Remove missing does not change"), State.Remove(B));
	TestTrue(TEXT("Remove present changes"), State.Remove(A));
	TestFalse(TEXT("Has after remove"), State.Has(A));

	State.Add(A);
	State.Add(B);
	FGameplayTagContainer Same;
	Same.AddTag(B);
	Same.AddTag(A);
	TestFalse(TEXT("Replace with same set (other order) does not change"), State.Replace(Same));
	FGameplayTagContainer Other;
	Other.AddTag(LBTags::State_Warden_Stage_3);
	TestTrue(TEXT("Replace with different set changes"), State.Replace(Other));
	TestTrue(TEXT("Has replaced tag"), State.Has(LBTags::State_Warden_Stage_3));
	TestFalse(TEXT("Old tag gone"), State.Has(A));
	TestTrue(TEXT("Reset non-empty changes"), State.Reset());
	TestFalse(TEXT("Reset empty does not change"), State.Reset());
	TestTrue(TEXT("Replace empty -> non-empty changes"), State.Replace(Other));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBObjectiveTest, "LastBell.Objectives.FindActiveIndex", LB_TEST_FLAGS)
bool FLBObjectiveTest::RunTest(const FString& Parameters)
{
	ULBObjectiveChainData* Chain = NewObject<ULBObjectiveChainData>(GetTransientPackage());
	FGameplayTagContainer State;

	TestEqual(TEXT("Empty chain"), Chain->FindActiveIndex(State), static_cast<int32>(INDEX_NONE));

	const FGameplayTag Tags[3] = { LBTags::State_Warden_Stage_1, LBTags::State_Warden_Stage_2, LBTags::State_Warden_Stage_3 };
	for (const FGameplayTag& Tag : Tags)
	{
		FLBObjective Objective;
		Objective.CompletionStateTags.AddTag(Tag);
		Chain->Objectives.Add(Objective);
	}

	TestEqual(TEXT("Nothing complete"), Chain->FindActiveIndex(State), 0);
	State.AddTag(Tags[0]);
	TestEqual(TEXT("First complete"), Chain->FindActiveIndex(State), 1);

	// Out of order: third done, second not -> still active at 1.
	State.AddTag(Tags[2]);
	TestEqual(TEXT("Out-of-order completion"), Chain->FindActiveIndex(State), 1);

	State.AddTag(Tags[1]);
	TestEqual(TEXT("All complete"), Chain->FindActiveIndex(State), static_cast<int32>(INDEX_NONE));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBSaveRoundTripTest, "LastBell.Save.RoundTripAndVersion", LB_TEST_FLAGS)
bool FLBSaveRoundTripTest::RunTest(const FString& Parameters)
{
	ULBSaveGame* Save = NewObject<ULBSaveGame>(GetTransientPackage());
	Save->CheckpointId = TEXT("CP_Test");
	Save->MapName = TEXT("/Game/LastBell/Maps/L_Test");
	Save->CheckpointTransform = FTransform(FRotator(0.f, 90.f, 0.f), FVector(10.f, 20.f, 30.f));
	Save->WorldState.AddTag(LBTags::State_Warden_Stage_1);
	Save->WorldState.AddTag(LBTags::State_Warden_Stage_4);
	Save->ReachedCheckpoints.Add(TEXT("CP_Test"));
	Save->ReachedCheckpoints.Add(TEXT("CP_Other"));
	FLBActorSaveRecord Record;
	Record.bState = true;
	Record.Value = 42.5f;
	Record.Index = 7;
	Save->ActorRecords.Add(TEXT("Statue_A"), Record);
	Save->PlayTimeSeconds = 123.5f;

	TArray<uint8> Bytes;
	if (!TestTrue(TEXT("SaveGameToMemory"), UGameplayStatics::SaveGameToMemory(Save, Bytes)))
	{
		return false;
	}
	const ULBSaveGame* Loaded = Cast<ULBSaveGame>(UGameplayStatics::LoadGameFromMemory(Bytes));
	if (!TestNotNull(TEXT("LoadGameFromMemory"), Loaded))
	{
		return false;
	}

	TestEqual(TEXT("Version"), Loaded->SaveVersion, ULBSaveGame::CurrentVersion);
	TestEqual(TEXT("CheckpointId"), Loaded->CheckpointId, FName(TEXT("CP_Test")));
	TestEqual(TEXT("MapName"), Loaded->MapName, Save->MapName);
	TestTrue(TEXT("Transform"), Loaded->CheckpointTransform.Equals(Save->CheckpointTransform));
	TestTrue(TEXT("WorldState"), Loaded->WorldState.HasAllExact(Save->WorldState) && Loaded->WorldState.Num() == 2);
	TestEqual(TEXT("ReachedCheckpoints"), Loaded->ReachedCheckpoints.Num(), 2);
	TestTrue(TEXT("Reached contains id"), Loaded->ReachedCheckpoints.Contains(TEXT("CP_Other")));
	const FLBActorSaveRecord* Found = Loaded->ActorRecords.Find(TEXT("Statue_A"));
	if (TestNotNull(TEXT("Record present"), Found))
	{
		TestTrue(TEXT("Record.bState"), Found->bState);
		TestEqual(TEXT("Record.Value"), Found->Value, 42.5f);
		TestEqual(TEXT("Record.Index"), Found->Index, 7);
	}
	TestEqual(TEXT("PlayTime"), Loaded->PlayTimeSeconds, 123.5f);

	TestTrue(TEXT("Current version compatible"), ULBSaveGame::IsVersionCompatible(ULBSaveGame::CurrentVersion));
	TestFalse(TEXT("Older version rejected"), ULBSaveGame::IsVersionCompatible(ULBSaveGame::CurrentVersion - 1));
	TestFalse(TEXT("Newer version rejected"), ULBSaveGame::IsVersionCompatible(ULBSaveGame::CurrentVersion + 1));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBSaveIdRegistryTest, "LastBell.Save.IdRegistry", LB_TEST_FLAGS)
bool FLBSaveIdRegistryTest::RunTest(const FString& Parameters)
{
	FLBSaveIdRegistry Registry;
	TestFalse(TEXT("None rejected"), Registry.Register(NAME_None));
	TestTrue(TEXT("First register ok"), Registry.Register(TEXT("Statue_A")));
	TestFalse(TEXT("Duplicate rejected"), Registry.Register(TEXT("Statue_A")));
	TestTrue(TEXT("Other id ok"), Registry.Register(TEXT("Statue_B")));
	Registry.Unregister(TEXT("Statue_A"));
	TestTrue(TEXT("Re-register after unregister"), Registry.Register(TEXT("Statue_A")));
	Registry.Reset();
	TestTrue(TEXT("Register after reset"), Registry.Register(TEXT("Statue_B")));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBInteractableTest, "LastBell.Interaction.PassesStateRequirements", LB_TEST_FLAGS)
bool FLBInteractableTest::RunTest(const FString& Parameters)
{
	ULBInteractableComponent* Comp = NewObject<ULBInteractableComponent>(GetTransientPackage());
	FGameplayTagContainer State;

	TestTrue(TEXT("No requirements passes"), Comp->PassesStateRequirements(State));

	Comp->RequiredStateTags.AddTag(LBTags::State_Warden_Stage_1);
	TestFalse(TEXT("Missing required tag fails"), Comp->PassesStateRequirements(State));
	State.AddTag(LBTags::State_Warden_Stage_1);
	TestTrue(TEXT("Required tag present passes"), Comp->PassesStateRequirements(State));

	Comp->ConsumedStateTag = LBTags::State_Warden_Stage_2;
	TestTrue(TEXT("Consumed tag absent passes"), Comp->PassesStateRequirements(State));
	State.AddTag(LBTags::State_Warden_Stage_2);
	TestFalse(TEXT("Consumed tag present fails"), Comp->PassesStateRequirements(State));

	State.RemoveTag(LBTags::State_Warden_Stage_2);
	Comp->bEnabled = false;
	TestFalse(TEXT("Disabled fails"), Comp->PassesStateRequirements(State));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAddStatesTest, "LastBell.WorldState.AddStates", LB_TEST_FLAGS)
bool FLBAddStatesTest::RunTest(const FString& Parameters)
{
	ULBWorldStateSubsystem* Subsystem = NewObject<ULBWorldStateSubsystem>(NewObject<UGameInstance>(GetTransientPackage()));
	FGameplayTagContainer Tags;
	Tags.AddTag(LBTags::State_Warden_Stage_1);
	Tags.AddTag(LBTags::State_Warden_Stage_2);
	Subsystem->AddStates(Tags);
	TestTrue(TEXT("All added"), Subsystem->HasAllStates(Tags));
	TestEqual(TEXT("Count"), Subsystem->GetStateRef().Num(), 2);
	Subsystem->AddStates(Tags);
	TestEqual(TEXT("Re-add is idempotent"), Subsystem->GetStateRef().Num(), 2);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBMergeRecordsTest, "LastBell.Save.KnownRecordsOverlay", LB_TEST_FLAGS)
bool FLBMergeRecordsTest::RunTest(const FString& Parameters)
{
	TMap<FName, FLBActorSaveRecord> Known;
	FLBActorSaveRecord Old;
	Old.Index = 1;
	Known.Add(TEXT("Unloaded"), Old);
	Known.Add(TEXT("Live"), Old);
	TMap<FName, FLBActorSaveRecord> Live;
	FLBActorSaveRecord Fresh;
	Fresh.Index = 9;
	Live.Add(TEXT("Live"), Fresh);
	Live.Add(TEXT("New"), Fresh);

	const TMap<FName, FLBActorSaveRecord> Merged = ULBSaveSubsystem::MergeRecords(Known, Live);
	TestEqual(TEXT("Count"), Merged.Num(), 3);
	TestEqual(TEXT("Unloaded actor's record preserved"), Merged.FindRef(TEXT("Unloaded")).Index, 1);
	TestEqual(TEXT("Live overrides known"), Merged.FindRef(TEXT("Live")).Index, 9);
	TestEqual(TEXT("New live record added"), Merged.FindRef(TEXT("New")).Index, 9);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBGameSettingsTest, "LastBell.Flow.GameSettingsDefaults", LB_TEST_FLAGS)
bool FLBGameSettingsTest::RunTest(const FString& Parameters)
{
	const ULBGameSettings* Settings = ULBGameSettings::Get();
	if (!TestNotNull(TEXT("Settings"), Settings))
	{
		return false;
	}
	TestEqual(TEXT("MainMenuMap"), Settings->MainMenuMap.GetLongPackageName(), FString(TEXT("/Game/LastBell/Maps/L_MainMenu")));
	TestEqual(TEXT("NewGameMap"), Settings->NewGameMap.GetLongPackageName(), FString(TEXT("/Game/LastBell/Maps/L_Monastery")));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBSetChainNullTest, "LastBell.Objectives.SetChainNullIsInert", LB_TEST_FLAGS)
bool FLBSetChainNullTest::RunTest(const FString& Parameters)
{
	ULBObjectiveSubsystem* Sub = NewObject<ULBObjectiveSubsystem>(GetTransientPackage());
	Sub->SetChain(nullptr);
	TestEqual(TEXT("Inactive index"), Sub->GetActiveIndex(), static_cast<int32>(INDEX_NONE));
	TestTrue(TEXT("Empty text"), Sub->GetActiveObjectiveText().IsEmpty());
	return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS
