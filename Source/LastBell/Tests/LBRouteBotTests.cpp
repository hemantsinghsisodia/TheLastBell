#include "Tests/LBRouteBot.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Editor.h"
#include "EngineUtils.h"
#include "Tests/AutomationEditorCommon.h"
#include "Engine/World.h"
#include "Misc/PackageName.h"
#include "Components/ArrowComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Character/LBCharacter.h"
#include "Objectives/LBObjectiveSubsystem.h"
#include "Save/LBCheckpoint.h"
#include "Save/LBSaveGame.h"
#include "Save/LBSaveSubsystem.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "LBLog.h"

namespace
{
	const TCHAR* GMicroSliceMap = TEXT("/Game/LastBell/Maps/L_Test_MicroSlice");
	const TCHAR* GMonasteryMap = TEXT("/Game/LastBell/Maps/L_Monastery");
	const TCHAR* GMainMenuMap = TEXT("/Game/LastBell/Maps/L_MainMenu");
	constexpr int32 GClimbTowerIndex = 10;

	/** Runs a list of steps (each returns true when done) with per-step and global timeouts; never hangs. */
	class FLBStepRunner : public IAutomationLatentCommand
	{
	public:
		struct FStep
		{
			FString Name;
			float TimeoutSeconds;
			TFunction<bool(FLBStepRunner&)> Fn;
		};

		FLBStepRunner(FAutomationTestBase* InTest, TArray<FStep> InSteps, float InGlobalTimeout)
			: Test(InTest), Steps(MoveTemp(InSteps)), GlobalTimeout(InGlobalTimeout), GlobalStart(FPlatformTime::Seconds())
		{
		}

		FAutomationTestBase* Test;
		int32 Aux = 0;
		int32 FramesInStep = 0;
		double StepStart = 0.0;

		void Abort(const FString& Why)
		{
			Test->AddError(Why);
			bAbort = true;
		}

		virtual bool Update() override
		{
			if (bFinished)
			{
				return true;
			}
			if (FPlatformTime::Seconds() - GlobalStart > GlobalTimeout)
			{
				Abort(FString::Printf(TEXT("Global timeout of %.0fs hit at step '%s'"), GlobalTimeout, Steps.IsValidIndex(Index) ? *Steps[Index].Name : TEXT("?")));
			}
			if (!bAbort && Index < Steps.Num())
			{
				RunStep();
			}
			if (bAbort || Index >= Steps.Num())
			{
				Finish();
				return true;
			}
			return false;
		}

	private:
		TArray<FStep> Steps;
		float GlobalTimeout;
		double GlobalStart;
		int32 Index = 0;
		bool bEntered = false;
		bool bAbort = false;
		bool bFinished = false;

		void RunStep()
		{
			FStep& Step = Steps[Index];
			if (!bEntered)
			{
				bEntered = true;
				StepStart = FPlatformTime::Seconds();
				FramesInStep = 0;
				Aux = 0;
				UE_LOG(LogLB, Display, TEXT("[RouteTest] STEP %d begin: %s"), Index + 1, *Step.Name);
			}
			const bool bDone = Step.Fn(*this);
			++FramesInStep;
			if (!bAbort && !bDone && FPlatformTime::Seconds() - StepStart > Step.TimeoutSeconds)
			{
				Abort(FString::Printf(TEXT("Step %d '%s' timed out after %.0fs (objective index %d, map %s)"), Index + 1, *Step.Name,
					Step.TimeoutSeconds, LBPie::ObjIndex(), *LBPie::MapShortName()));
			}
			if (bDone && !bAbort)
			{
				UE_LOG(LogLB, Display, TEXT("[RouteTest] STEP %d done: %s"), Index + 1, *Step.Name);
				++Index;
				bEntered = false;
			}
		}

		void Finish()
		{
			bFinished = true;
			if (GEditor && GEditor->PlayWorld)
			{
				GEditor->RequestEndPlayMap();
			}
			LBPie::ClearSlot();
		}
	};

	using FStep = FLBStepRunner::FStep;

	/** Bot step: ticks until Done; any failure aborts the whole test. */
	FStep BotStep(const FString& Name, TSharedRef<FLBRouteBot> Bot, float Timeout, TFunction<void()> OnDone = nullptr)
	{
		return { Name, Timeout, [Bot, OnDone](FLBStepRunner& R)
		{
			switch (Bot->Tick())
			{
			case FLBRouteBot::EStatus::Failed:
				R.Abort(TEXT("Route bot failed (see [RouteBot] error above)"));
				return false;
			case FLBRouteBot::EStatus::Done:
				if (OnDone) { OnDone(); }
				return true;
			default:
				return false;
			}
		} };
	}

	FStep WaitPieStart()
	{
		return { TEXT("PIE start"), 90.f, [](FLBStepRunner& R) { return LBPie::WorldReady() && R.FramesInStep >= 5; } };
	}

	FStep EndPie()
	{
		return { TEXT("End PIE"), 30.f, [](FLBStepRunner& R)
		{
			if (R.Aux == 0) { GEditor->RequestEndPlayMap(); R.Aux = 1; return false; }
			return LBPie::World() == nullptr;
		} };
	}

	void StartPie(const TCHAR* MapPath)
	{
		FAutomationEditorCommonUtils::LoadMap(MapPath);
		FRequestPlaySessionParams PlayParams;
		PlayParams.WorldType = EPlaySessionWorldType::PlayInEditor;
		GEditor->RequestPlaySession(PlayParams);
	}

	const ULBSaveGame* LoadSave()
	{
		return UGameplayStatics::DoesSaveGameExist(ULBSaveSubsystem::SlotName, 0)
			? Cast<ULBSaveGame>(UGameplayStatics::LoadGameFromSlot(ULBSaveSubsystem::SlotName, 0)) : nullptr;
	}

	/** World location of a checkpoint's respawn arrow, or false if not found. */
	bool FindCheckpointSpawn(const FName Id, FVector& Out)
	{
		for (TActorIterator<ALBCheckpoint> It(LBPie::World()); It; ++It)
		{
			if (It->CheckpointId == Id)
			{
				const UArrowComponent* Arrow = It->FindComponentByClass<UArrowComponent>();
				Out = Arrow ? Arrow->GetComponentLocation() : It->GetActorLocation();
				return true;
			}
		}
		return false;
	}

	/** Reads the BP_EndingTrigger "EndingSeconds" property by reflection; falls back to the spec value of 8 s. */
	float ReadEndingSeconds()
	{
		for (TActorIterator<AActor> It(LBPie::World()); It; ++It)
		{
			if (It->GetClass()->GetName().Contains(TEXT("EndingTrigger")))
			{
				if (const FNumericProperty* P = FindFProperty<FNumericProperty>(It->GetClass(), TEXT("EndingSeconds")))
				{
					const void* Ptr = P->ContainerPtrToValuePtr<void>(*It);
					return P->IsFloatingPoint() ? static_cast<float>(P->GetFloatingPointPropertyValue(Ptr)) : static_cast<float>(P->GetSignedIntPropertyValue(Ptr));
				}
			}
		}
		return 8.f;
	}

	/** State shared between the Monastery steps. */
	struct FMonasteryContext
	{
		int32 IndexBeforeDeath = INDEX_NONE;
		FVector TowerBaseSpawn = FVector::ZeroVector;
		TWeakObjectPtr<UWorld> OldWorld;
		float EndingSeconds = 8.f;
		double FinaleTime = 0.0;
	};
}

// ---------------------------------------------------------------------------------------------------------------------
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBRouteBotMicroSliceTest, "LastBell.Functional.RouteBot.MicroSlice",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBRouteBotMicroSliceTest::RunTest(const FString& Parameters)
{
	LBPie::ClearSlot();
	StartPie(GMicroSliceMap);

	TSharedRef<FLBRouteBot> Bot = MakeShared<FLBRouteBot>(this, FLBRouteBot::FConfig());
	TArray<FStep> Steps;
	Steps.Add(WaitPieStart());
	Steps.Add(BotStep(TEXT("Route bot completes all objectives"), Bot, 120.f));
	Steps.Add({ TEXT("All objectives complete"), 10.f, [this](FLBStepRunner&)
	{
		TestEqual(TEXT("Objective index after route"), LBPie::ObjIndex(), static_cast<int32>(INDEX_NONE));
		return true;
	} });
	Steps.Add(EndPie());

	ADD_LATENT_AUTOMATION_COMMAND(FLBStepRunner(this, MoveTemp(Steps), 300.f));
	return true;
}

// ---------------------------------------------------------------------------------------------------------------------
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBRouteBotMonasteryTest, "LastBell.Functional.RouteBot.Monastery",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBRouteBotMonasteryTest::RunTest(const FString& Parameters)
{
	if (!FPackageName::DoesPackageExist(GMonasteryMap))
	{
		AddWarning(TEXT("L_Monastery does not exist yet: RouteBot.Monastery skipped"));
		return true;
	}

	LBPie::ClearSlot();
	StartPie(GMonasteryMap);

	TSharedRef<FMonasteryContext> Ctx = MakeShared<FMonasteryContext>();
	FLBRouteBot::FConfig ToTower;
	ToTower.StopAtIndex = GClimbTowerIndex;
	TSharedRef<FLBRouteBot> TowerBot = MakeShared<FLBRouteBot>(this, ToTower);
	TSharedRef<FLBRouteBot> FinaleBot = MakeShared<FLBRouteBot>(this, FLBRouteBot::FConfig());

	TArray<FStep> Steps;
	Steps.Add(WaitPieStart());

	// 1. New Game state
	Steps.Add({ TEXT("New Game state"), 20.f, [this](FLBStepRunner&)
	{
		if (ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(LBPie::World())) { Save->DeleteSave(); }
		if (ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(LBPie::World())) { State->ResetState(); }
		TestEqual(TEXT("Objective index at New Game"), LBPie::ObjIndex(), 0);
		TestFalse(TEXT("No save at New Game"), UGameplayStatics::DoesSaveGameExist(ULBSaveSubsystem::SlotName, 0));
		return true;
	} });

	// 2. Route to "Climb the bell tower"
	Steps.Add(BotStep(TEXT("Route to objective 10 (Climb the bell tower)"), TowerBot, 400.f));
	Steps.Add({ TEXT("Save with CP_TowerBase exists"), 10.f, [this, Ctx](FLBStepRunner&)
	{
		const ULBSaveGame* Save = LoadSave();
		if (!Save) { return false; }
		TestTrue(TEXT("ReachedCheckpoints contains CP_TowerBase"), Save->ReachedCheckpoints.Contains(TEXT("CP_TowerBase")));
		TestEqual(TEXT("Active objective index"), LBPie::ObjIndex(), GClimbTowerIndex);
		Ctx->IndexBeforeDeath = LBPie::ObjIndex();
		if (!FindCheckpointSpawn(TEXT("CP_TowerBase"), Ctx->TowerBaseSpawn)) { AddError(TEXT("CP_TowerBase actor not found in the map")); }
		Ctx->EndingSeconds = ReadEndingSeconds();
		return true;
	} });

	// 3. Death and restore
	Steps.Add({ TEXT("Kill and restore"), 60.f, [this, Ctx](FLBStepRunner& R)
	{
		if (R.Aux == 0)
		{
			Ctx->OldWorld = LBPie::World();
			LBPie::Pawn()->Kill();
			R.Aux = 1;
			return false;
		}
		if (LBPie::World() == Ctx->OldWorld.Get() || !LBPie::WorldReady()) { return false; }
		if (R.Aux == 1) { R.Aux = 2; R.FramesInStep = 0; return false; }
		if (R.FramesInStep < 15) { return false; }

		for (const TCHAR* Name : { TEXT("State.Ritual.1"), TEXT("State.Ritual.2"), TEXT("State.Ritual.3") })
		{
			TestTrue(FString::Printf(TEXT("%s present after restore"), Name), LBPie::HasState(LBPie::Tag(Name)));
		}
		TestEqual(TEXT("Objective index unchanged after restore"), LBPie::ObjIndex(), Ctx->IndexBeforeDeath);
		const float Dist = static_cast<float>(FVector::Dist(LBPie::Pawn()->GetActorLocation(), Ctx->TowerBaseSpawn));
		TestTrue(FString::Printf(TEXT("Pawn within 100cm of CP_TowerBase spawn (dist %.1f)"), Dist), Dist <= 100.f);
		return true;
	} });

	// 4. Through the finale
	Steps.Add(BotStep(TEXT("Route through State.Event.Finale"), FinaleBot, 400.f, [Ctx]() { Ctx->FinaleTime = FPlatformTime::Seconds(); }));

	// 5. Ending: travel to the main menu, save wiped
	Steps.Add({ TEXT("Ending returns to main menu"), 120.f, [this, Ctx](FLBStepRunner& R)
	{
		if (LBPie::MapShortName() != GMainMenuMap)
		{
			if (FPlatformTime::Seconds() - Ctx->FinaleTime > Ctx->EndingSeconds + 5.0)
			{
				AddError(FString::Printf(TEXT("Ending did not travel to L_MainMenu within %.0fs (still on %s)"), Ctx->EndingSeconds + 5.f, *LBPie::MapShortName()));
				R.Abort(TEXT("Ending timeout"));
			}
			return false;
		}
		const ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(LBPie::World());
		TestTrue(TEXT("Save subsystem present"), Save != nullptr);
		TestFalse(TEXT("HasValidSave is false after the ending"), Save && Save->HasValidSave());
		return true;
	} });
	Steps.Add(EndPie());

	ADD_LATENT_AUTOMATION_COMMAND(FLBStepRunner(this, MoveTemp(Steps), 600.f));
	return true;
}

#endif
