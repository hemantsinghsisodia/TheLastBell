#include "Tests/LBRouteBot.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Tests/LBUITestUtil.h"
#include "Editor.h"
#include "EngineUtils.h"
#include "Tests/AutomationEditorCommon.h"
#include "AI/LBWarden.h"
#include "Audio/LBAudioSettings.h"
#include "Audio/LBAudioSubsystem.h"
#include "Audio/LBAudioTypes.h"
#include "Camera/CameraComponent.h"
#include "Character/LBCharacter.h"
#include "Character/LBInspectionComponent.h"
#include "Cinematics/LBCinematicSettings.h"
#include "Cinematics/LBCinematicSubsystem.h"
#include "Cinematics/LBCinematicWidget.h"
#include "Components/LBInspectableComponent.h"
#include "Components/LightComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/PackageName.h"
#include "LevelSequence.h"
#include "MovieScene.h"
#include "Save/LBSaveSubsystem.h"
#include "Storm/LBStormSettings.h"
#include "Storm/LBStormSubsystem.h"
#include "Systems/LBGameInstance.h"
#include "Systems/LBPlayerController.h"
#include "Systems/LBUserSettings.h"
#include "UI/LBBrightnessWidget.h"
#include "UI/LBConfirmWidget.h"
#include "UI/LBCreditsWidget.h"
#include "UI/LBHUDWidget.h"
#include "Components/LBInteractableComponent.h"
#include "Components/LBInteractorComponent.h"
#include "Character/LBCandleComponent.h"
#include "Objectives/LBObjectiveSubsystem.h"
#include "UI/LBGraphicsSettings.h"
#include "UI/LBKeyBindings.h"
#include "UI/LBKeyIconWidget.h"
#include "UI/LBLoadingScreen.h"
#include "UI/LBMainMenuWidget.h"
#include "UI/LBPauseWidget.h"
#include "UI/LBSettingsWidget.h"
#include "UI/LBUILogic.h"
#include "UI/LBUISubsystem.h"
#include "UObject/StrongObjectPtr.h"
#include "LBLog.h"

// P18-1 functional tests of the UI (LastBell.Functional.UI.*). Every test loads /Game/LastBell/Maps/L_Test_Warden (one PIE session each) and builds its
// screens through ULBUISubsystem, so none needs the P18-2 content (fonts, icons, DA_UIStyle, IA_Pause, the menu video) or L_MainMenu. The brightness
// screen is marked as seen for the sessions (except the gate test) and the user settings are put back afterwards.
//
// EXPECTED TO FAIL until P18-2 (they need the IMC mapping names and Enhanced Input user settings): UI.Rebind.InteractChangesPromptAndSkip.
// Also updated for the C++ menu and EXPECTED TO FAIL until P18-2 points BP_MenuPlayerController at ULBMainMenuWidget: Flow.MenuToGameInput.

#define LB_UIFUNC_FLAGS (EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

namespace LBUITest
{
	const TCHAR* GUIMap = TEXT("/Game/LastBell/Maps/L_Test_Warden");

	void UINote(const FString& Text) { UE_LOG(LogLB, Display, TEXT("[UITest] %s"), *Text); }

	struct FUICtx
	{
		UWorld* W = nullptr;
		double Elapsed = 0.0; // world seconds since the step began (frozen while paused)
		double Wall = 0.0;    // real seconds since the step began
		double Now = 0.0;
		int32 Frames = 0;
	};

	struct FUIState
	{
		int32 Phase = 0;
		int32 Counter = 0;
		double T0 = 0.0;
		double Wall0 = 0.0;
		double Number0 = 0.0;
		double Number1 = 0.0;
		FVector Vector0 = FVector::ZeroVector;
		TArray<TWeakObjectPtr<AActor>> Actors;
		TStrongObjectPtr<ULBCinematicSettings> CineSettings;
		TArray<TStrongObjectPtr<ULevelSequence>> Sequences;
		TStrongObjectPtr<ULBAudioSettings> AudioSettings;
		TStrongObjectPtr<ULBStormSettings> StormSettings;
		TWeakObjectPtr<UWorld> OldWorld;
		int32 ArmCount = 0;
	};

	/** Sets a console variable for its lifetime and puts it back. */
	class FUICVarGuard
	{
	public:
		FUICVarGuard(const TCHAR* InName, int32 Value) : Name(InName)
		{
			if (IConsoleVariable* Var = IConsoleManager::Get().FindConsoleVariable(Name))
			{
				Previous = Var->GetInt();
				Var->Set(Value, ECVF_SetByCode);
			}
		}
		~FUICVarGuard()
		{
			if (IConsoleVariable* Var = IConsoleManager::Get().FindConsoleVariable(Name))
			{
				Var->Set(Previous, ECVF_SetByCode);
			}
		}
		FUICVarGuard(const FUICVarGuard&) = delete;
		FUICVarGuard& operator=(const FUICVarGuard&) = delete;

	private:
		const TCHAR* Name;
		int32 Previous = 0;
	};

	ULBUISubsystem* UIGet(UWorld* W) { return ULBUISubsystem::Get(W); }
	ALBPlayerController* UILBController(UWorld* W) { return W ? Cast<ALBPlayerController>(W->GetFirstPlayerController()) : nullptr; }

	class FUIRunner : public IAutomationLatentCommand
	{
	public:
		using FStepFn = TFunction<bool(FUICtx&)>;

		FUIRunner(FAutomationTestBase* InTest, bool bWardenOn, bool bCineOn, bool bCalibrated)
			: S(MakeShared<FUIState>()), Test(InTest), WardenSwitch(bWardenOn), CineSwitch(bCineOn), AudioOn(TEXT("lb.Audio.Enabled"), 1)
		{
			if (ULBUserSettings* Settings = ULBUserSettings::GetUserSettings())
			{
				// The guard puts the player's settings back; the sessions run with the brightness screen already seen unless a test asks otherwise.
				Settings->bBrightnessCalibrated = bCalibrated;
			}
		}

		void Add(const TCHAR* Name, FStepFn Fn, float WallTimeout = 40.f)
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
			FStep& Step = Steps[StepIndex];
			if (!bEntered)
			{
				if (StepIndex > 0 && !W)
				{
					Test->AddError(FString::Printf(TEXT("Step '%s': the PIE world is gone"), *Step.Name));
					bAbort = true;
					return false;
				}
				bEntered = true;
				Frames = 0;
				WallStart = FPlatformTime::Seconds();
				WorldStart = W ? W->GetTimeSeconds() : 0.0;
				ErrorsAtStart = ErrCount();
				UINote(FString::Printf(TEXT("STEP %d begin: %s"), StepIndex + 1, *Step.Name));
			}

			FUICtx Ctx;
			Ctx.W = W;
			Ctx.Now = W ? W->GetTimeSeconds() : 0.0;
			Ctx.Elapsed = Ctx.Now - WorldStart;
			Ctx.Wall = FPlatformTime::Seconds() - WallStart;
			Ctx.Frames = Frames;
			++Frames;

			const bool bDone = Step.Fn(Ctx);
			const bool bTimedOut = !bDone && Ctx.Wall > Step.Timeout;
			if (bTimedOut)
			{
				Test->AddError(FString::Printf(TEXT("Step '%s' timed out after %.0fs (map %s, phase %d)"), *Step.Name, Step.Timeout, *LBPie::MapShortName(), S->Phase));
			}
			if (bDone || bTimedOut)
			{
				UINote(FString::Printf(TEXT("STEP %d %s: %s"), StepIndex + 1, ErrCount() == ErrorsAtStart ? TEXT("PASS") : TEXT("FAIL"), *Step.Name));
				if (bTimedOut || ErrCount() != ErrorsAtStart)
				{
					bAbort = true;
				}
				++StepIndex;
				bEntered = false;
			}
			return false;
		}

		TSharedRef<FUIState> S;

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
			if (UWorld* W = LBPie::World())
			{
				// Never leave the world paused or a screen up when the session ends.
				if (ULBUISubsystem* Subsystem = UIGet(W))
				{
					Subsystem->ClosePause();
					Subsystem->ClearScreens();
				}
			}
			if (GEditor && LBPie::World())
			{
				GEditor->RequestEndPlayMap();
			}
			LBPie::ClearSlot();
		}

		FAutomationTestBase* Test;
		FLBUserSettingsGuard SettingsGuard;
		LBPie::FWardenSwitch WardenSwitch;
		LBPie::FCineSwitch CineSwitch;
		FUICVarGuard AudioOn;
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

	TSharedRef<FUIRunner> UIStartSession(FAutomationTestBase* Test, bool bWardenOn = false, bool bCineOn = false, bool bCalibrated = true)
	{
		LBPie::ClearSlot();
		TSharedRef<FUIRunner> Runner = MakeShared<FUIRunner>(Test, bWardenOn, bCineOn, bCalibrated);
		FAutomationEditorCommonUtils::LoadMap(GUIMap);
		FRequestPlaySessionParams PlayParams;
		PlayParams.WorldType = EPlaySessionWorldType::PlayInEditor;
		GEditor->RequestPlaySession(PlayParams);
		return Runner;
	}

	void UIEnqueue(const TSharedRef<FUIRunner>& Runner)
	{
		FAutomationTestFramework::Get().EnqueueLatentCommand(Runner);
	}

	void UIAddReady(FUIRunner& R)
	{
		R.Add(TEXT("PIE ready"), [](FUICtx& C) { return LBPie::WorldReady() && C.Frames >= 5; }, 90.f);
	}

	ALBWarden* UIFindWarden(UWorld* W)
	{
		for (TActorIterator<ALBWarden> It(W); It; ++It)
		{
			return *It;
		}
		return nullptr;
	}
}

using namespace LBUITest;

// =====================================================================================================================
// Main menu
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUIMenuNoContinueTest, "LastBell.Functional.UI.MainMenu.ContinueHiddenWithoutSave", LB_UIFUNC_FLAGS)
bool FLBUIMenuNoContinueTest::RunTest(const FString& Parameters)
{
	TSharedRef<FUIRunner> R = UIStartSession(this);
	const TSharedRef<FUIState> S = R->S;
	FAutomationTestBase* Test = this;
	UIAddReady(*R);

	R->Add(TEXT("No save: the menu has no Continue item"), [S, Test](FUICtx& C)
	{
		ULBUISubsystem* Subsystem = UIGet(C.W);
		ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(C.W);
		if (!Test->TestNotNull(TEXT("The UI subsystem"), Subsystem) || !Test->TestNotNull(TEXT("The save subsystem"), Save))
		{
			return true;
		}
		LBPie::ClearSlot();
		Test->TestFalse(TEXT("No valid save"), Save->HasValidSave());

		Subsystem->PushScreen(ELBScreen::MainMenu);
		ULBMainMenuWidget* Menu = Cast<ULBMainMenuWidget>(Subsystem->GetTopWidget());
		if (Test->TestNotNull(TEXT("The main menu is on top"), Menu))
		{
			Test->TestEqual(TEXT("It is the main menu screen"), Subsystem->GetTopScreen(), ELBScreen::MainMenu);
			Test->TestEqual(TEXT("No Continue"), Menu->FindItemByLabel(NSLOCTEXT("LastBellUI", "MenuContinue", "Continue")), static_cast<int32>(INDEX_NONE));
			Test->TestNotEqual(TEXT("New Game"), Menu->FindItemByLabel(NSLOCTEXT("LastBellUI", "MenuNewGame", "New Game")), static_cast<int32>(INDEX_NONE));
			Test->TestNotEqual(TEXT("Settings"), Menu->FindItemByLabel(NSLOCTEXT("LastBellUI", "MenuSettings", "Settings")), static_cast<int32>(INDEX_NONE));
			Test->TestNotEqual(TEXT("Credits"), Menu->FindItemByLabel(NSLOCTEXT("LastBellUI", "MenuCredits", "Credits")), static_cast<int32>(INDEX_NONE));
			Test->TestNotEqual(TEXT("Quit"), Menu->FindItemByLabel(NSLOCTEXT("LastBellUI", "MenuQuit", "Quit")), static_cast<int32>(INDEX_NONE));
			Test->TestEqual(TEXT("Four items"), Menu->GetItemCount(), 4);
			Test->TestEqual(TEXT("The first item (New Game) is selected"), Menu->GetItemLabel(Menu->GetSelectedIndex()).ToString(), FString(TEXT("New Game")));

			// Keyboard: Down moves the selection, Back on the main menu does nothing.
			Menu->MoveSelection(1);
			Test->TestEqual(TEXT("Down selects Settings"), Menu->GetItemLabel(Menu->GetSelectedIndex()).ToString(), FString(TEXT("Settings")));
			Menu->MoveSelection(-1);
			Test->TestEqual(TEXT("Up selects New Game again"), Menu->GetItemLabel(Menu->GetSelectedIndex()).ToString(), FString(TEXT("New Game")));
			Subsystem->HandleBack();
			Test->TestEqual(TEXT("Back leaves the main menu on top"), Subsystem->GetTopScreen(), ELBScreen::MainMenu);
			Test->TestFalse(TEXT("The menu never pauses the game"), C.W->IsPaused());
			Test->TestTrue(TEXT("The cursor is shown"), UILBController(C.W) && UILBController(C.W)->bShowMouseCursor);
		}
		Subsystem->ClearScreens();
		return true;
	});

	R->Add(TEXT("With a save: Continue is the first item"), [S, Test](FUICtx& C)
	{
		ULBUISubsystem* Subsystem = UIGet(C.W);
		ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(C.W);
		ALBCharacter* Pawn = LBPie::Pawn();
		if (!Subsystem || !Save || !Pawn)
		{
			Test->AddError(TEXT("The UI subsystem, the save subsystem or the pawn is missing"));
			return true;
		}
		if (!Test->TestTrue(TEXT("A checkpoint save was written"), Save->SaveCheckpoint(FName(TEXT("UITest")), Pawn->GetActorTransform())) || !Test->TestTrue(TEXT("It reads as a valid save"), Save->HasValidSave()))
		{
			return true;
		}
		Subsystem->PushScreen(ELBScreen::MainMenu);
		ULBMainMenuWidget* Menu = Cast<ULBMainMenuWidget>(Subsystem->GetTopWidget());
		if (Test->TestNotNull(TEXT("The main menu is on top"), Menu))
		{
			Test->TestEqual(TEXT("Continue is item 0"), Menu->FindItemByLabel(NSLOCTEXT("LastBellUI", "MenuContinue", "Continue")), 0);
			Test->TestEqual(TEXT("Five items"), Menu->GetItemCount(), 5);
			Test->TestEqual(TEXT("Continue is selected first"), Menu->GetSelectedIndex(), 0);
		}
		Subsystem->ClearScreens();
		return true;
	});

	UIEnqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUIMenuNewGameConfirmTest, "LastBell.Functional.UI.MainMenu.NewGameConfirmsWhenSave", LB_UIFUNC_FLAGS)
bool FLBUIMenuNewGameConfirmTest::RunTest(const FString& Parameters)
{
	TSharedRef<FUIRunner> R = UIStartSession(this);
	const TSharedRef<FUIState> S = R->S;
	FAutomationTestBase* Test = this;
	UIAddReady(*R);

	R->Add(TEXT("With a save, New Game asks first; Cancel and Back keep everything"), [S, Test](FUICtx& C)
	{
		ULBUISubsystem* Subsystem = UIGet(C.W);
		ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(C.W);
		ALBCharacter* Pawn = LBPie::Pawn();
		if (!Subsystem || !Save || !Pawn)
		{
			Test->AddError(TEXT("The UI subsystem, the save subsystem or the pawn is missing"));
			return true;
		}
		if (!Test->TestTrue(TEXT("A checkpoint save was written"), Save->SaveCheckpoint(FName(TEXT("UITest")), Pawn->GetActorTransform())))
		{
			return true;
		}
		Subsystem->PushScreen(ELBScreen::MainMenu);
		ULBMainMenuWidget* Menu = Cast<ULBMainMenuWidget>(Subsystem->GetTopWidget());
		if (!Test->TestNotNull(TEXT("The main menu is on top"), Menu))
		{
			return true;
		}
		const int32 NewGame = Menu->FindItemByLabel(NSLOCTEXT("LastBellUI", "MenuNewGame", "New Game"));
		Menu->ActivateItem(NewGame);
		Test->TestEqual(TEXT("A confirm dialog is on top"), Subsystem->GetTopScreen(), ELBScreen::Confirm);
		Test->TestFalse(TEXT("No travel started"), Save->IsTravelPending());
		Test->TestTrue(TEXT("The save is still there"), Save->HasValidSave());
		if (const ULBConfirmWidget* Dialog = Cast<ULBConfirmWidget>(Subsystem->GetTopWidget()))
		{
			Test->TestTrue(TEXT("It says progress will be erased"), Dialog->GetMessageTextForTest().ToString().Contains(TEXT("erase your progress")));
			Test->TestFalse(TEXT("A plain question has no countdown"), Dialog->IsCountdownActive());
		}

		// Back answers Cancel.
		Subsystem->HandleBack();
		Test->TestEqual(TEXT("Back closes the dialog: the main menu is on top again"), Subsystem->GetTopScreen(), ELBScreen::MainMenu);
		Test->TestFalse(TEXT("Still no travel"), Save->IsTravelPending());
		Test->TestTrue(TEXT("The save survived"), Save->HasValidSave());

		// The Cancel button.
		Menu->ActivateItem(NewGame);
		if (ULBConfirmWidget* Dialog = Cast<ULBConfirmWidget>(Subsystem->GetTopWidget()))
		{
			Dialog->Cancel();
		}
		Test->TestEqual(TEXT("Cancel returns to the main menu"), Subsystem->GetTopScreen(), ELBScreen::MainMenu);
		Test->TestTrue(TEXT("The save survived"), Save->HasValidSave());
		Subsystem->ClearScreens();
		return true;
	});

	UIEnqueue(R);
	return true;
}

// =====================================================================================================================
// Pause
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUIPauseFreezesWorldTest, "LastBell.Functional.UI.Pause.FreezesWorld", LB_UIFUNC_FLAGS)
bool FLBUIPauseFreezesWorldTest::RunTest(const FString& Parameters)
{
	TSharedRef<FUIRunner> R = UIStartSession(this, /*bWardenOn*/ true);
	const TSharedRef<FUIState> S = R->S;
	FAutomationTestBase* Test = this;
	UIAddReady(*R);

	R->Add(TEXT("The world runs; Pause freezes it for a second of real time; Resume continues"), [S, Test](FUICtx& C)
	{
		ULBUISubsystem* Subsystem = UIGet(C.W);
		ALBCharacter* Pawn = LBPie::Pawn();
		if (!Subsystem || !Pawn)
		{
			Test->AddError(TEXT("The UI subsystem or the pawn is missing"));
			return true;
		}
		ALBWarden* Warden = UIFindWarden(C.W);
		ULBStormSubsystem* Storm = C.W->GetSubsystem<ULBStormSubsystem>();
		ULBAudioSubsystem* Audio = C.W->GetSubsystem<ULBAudioSubsystem>();

		switch (S->Phase)
		{
		case 0:
			// Control: the world advances while not paused.
			if (C.Elapsed < 0.5)
			{
				return false;
			}
			Test->TestTrue(TEXT("The world time advanced while not paused"), C.Elapsed >= 0.4);
			Test->TestTrue(TEXT("Pause may open here"), Subsystem->CanOpenPause());
			if (!Test->TestTrue(TEXT("OpenPause succeeds"), Subsystem->OpenPause()))
			{
				return true;
			}
			Test->TestTrue(TEXT("The world is paused"), C.W->IsPaused());
			Test->TestTrue(TEXT("The pause menu is on top"), Subsystem->GetTopScreen() == ELBScreen::Pause && Subsystem->IsPauseOpen());
			Test->TestTrue(TEXT("It is the pause widget"), Cast<ULBPauseWidget>(Subsystem->GetTopWidget()) != nullptr);
			S->Number0 = C.W->GetTimeSeconds();
			S->Number1 = C.W->GetUnpausedTimeSeconds();
			S->Vector0 = Warden ? Warden->GetActorLocation() : FVector::ZeroVector;
			S->T0 = Storm ? Storm->GetStormIntensity() : 0.0;
			S->Counter = Audio ? Audio->GetScheduledCount() : 0;
			S->Wall0 = FPlatformTime::Seconds();
			S->Phase = 1;
			return false;

		case 1:
			if (FPlatformTime::Seconds() - S->Wall0 < 1.0 || C.Frames < 20)
			{
				return false;
			}
			Test->TestTrue(TEXT("Still paused"), C.W->IsPaused());
			Test->TestTrue(FString::Printf(TEXT("The world time did not move (%.5f -> %.5f)"), S->Number0, C.W->GetTimeSeconds()), FMath::Abs(C.W->GetTimeSeconds() - S->Number0) < 0.001);
			Test->TestTrue(TEXT("Real time did pass (the unpaused clock moved)"), C.W->GetUnpausedTimeSeconds() - S->Number1 > 0.8);
			if (Warden)
			{
				Test->TestTrue(TEXT("The Warden did not move"), FVector::Dist(Warden->GetActorLocation(), S->Vector0) < 0.1);
			}
			if (Storm)
			{
				Test->TestTrue(TEXT("The storm did not move"), FMath::Abs(Storm->GetStormIntensity() - S->T0) < 0.0001);
			}
			if (Audio)
			{
				Test->TestEqual(TEXT("The audio schedule did not change"), Audio->GetScheduledCount(), S->Counter);
			}
			Subsystem->ClosePause();
			Test->TestFalse(TEXT("Resume unpauses the world"), C.W->IsPaused());
			Test->TestEqual(TEXT("No screen is left"), Subsystem->GetScreenCount(), 0);
			Test->TestFalse(TEXT("The cursor is hidden again"), UILBController(C.W) && UILBController(C.W)->bShowMouseCursor);
			S->Number0 = C.W->GetTimeSeconds();
			S->Phase = 2;
			return false;

		default:
			if (C.W->GetTimeSeconds() - S->Number0 < 0.3)
			{
				return false;
			}
			Test->TestTrue(TEXT("The world runs again after Resume"), true);
			return true;
		}
	}, 60.f);

	UIEnqueue(R);
	return true;
}

namespace LBUITest
{
	TSoftObjectPtr<ULevelSequence> UIMakeSequence(FUIState& S, double Seconds, const TArray<TPair<double, FString>>& Markers)
	{
		ULevelSequence* Sequence = NewObject<ULevelSequence>(GetTransientPackage());
		Sequence->Initialize();
		UMovieScene* MovieScene = Sequence->GetMovieScene();
		MovieScene->SetDisplayRate(FFrameRate(30, 1));
		MovieScene->SetTickResolutionDirectly(FFrameRate(24000, 1));
		MovieScene->SetPlaybackRange(FFrameNumber(0), static_cast<int32>(Seconds * 24000.0));
		for (const TPair<double, FString>& Marker : Markers)
		{
			FMovieSceneMarkedFrame Frame(FFrameNumber(static_cast<int32>(Marker.Key * 24000.0)));
			Frame.Label = Marker.Value;
			MovieScene->AddMarkedFrame(Frame);
		}
		S.Sequences.Add(TStrongObjectPtr<ULevelSequence>(Sequence));
		return TSoftObjectPtr<ULevelSequence>(Sequence);
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUIPauseFreezesCinematicTest, "LastBell.Functional.UI.Pause.FreezesCinematic", LB_UIFUNC_FLAGS)
bool FLBUIPauseFreezesCinematicTest::RunTest(const FString& Parameters)
{
	TSharedRef<FUIRunner> R = UIStartSession(this, /*bWardenOn*/ false, /*bCineOn*/ true);
	const TSharedRef<FUIState> S = R->S;
	FAutomationTestBase* Test = this;
	UIAddReady(*R);

	R->Add(TEXT("A cinematic plays; Pause freezes the sequence and its widget; Resume continues from the same moment"), [S, Test](FUICtx& C)
	{
		ULBUISubsystem* Subsystem = UIGet(C.W);
		ULBCinematicSubsystem* Cine = C.W->GetSubsystem<ULBCinematicSubsystem>();
		if (!Subsystem || !Cine)
		{
			Test->AddError(TEXT("The UI or the cinematic subsystem is missing"));
			return true;
		}

		switch (S->Phase)
		{
		case 0:
		{
			FLBCinematicDef Def;
			Def.Id = TEXT("UIPause");
			Def.InitialLock = ELBInputLock::Full;
			Def.Sequence = UIMakeSequence(*S, 20.0, { { 0.0, TEXT("skip:1") }, { 12.0, TEXT("tag:State.Test.Door1Open") } });
			S->CineSettings.Reset(NewObject<ULBCinematicSettings>(GetTransientPackage()));
			S->CineSettings->Cinematics.Add(Def);
			Cine->OverrideSettings(S->CineSettings.Get());
			Cine->Rearm();
			if (!Test->TestTrue(TEXT("The cinematic starts"), Cine->Play(TEXT("UIPause"))))
			{
				return true;
			}
			S->Phase = 1;
			return false;
		}

		case 1:
			if (Cine->GetSequenceSeconds() < 1.0)
			{
				return false;
			}
			Cine->BeginSkipHold();
			Test->TestTrue(TEXT("Pause may open during a cinematic"), Subsystem->CanOpenPause());
			if (!Test->TestTrue(TEXT("OpenPause succeeds during the cinematic"), Subsystem->OpenPause()))
			{
				return true;
			}
			S->Number0 = Cine->GetSequenceSeconds();
			S->Number1 = C.W->GetTimeSeconds();
			S->Counter = Cine->GetFiredMarkerCount();
			S->Wall0 = FPlatformTime::Seconds();
			Test->TestEqual(TEXT("Opening the pause cancels the skip hold"), Cine->GetSkipHoldFraction(), 0.f);
			S->Phase = 2;
			return false;

		case 2:
			if (FPlatformTime::Seconds() - S->Wall0 < 1.0 || C.Frames < 20)
			{
				return false;
			}
			Test->TestTrue(TEXT("The cinematic is still playing"), Cine->IsPlaying());
			Test->TestTrue(FString::Printf(TEXT("The sequence time held (%.4f -> %.4f)"), S->Number0, Cine->GetSequenceSeconds()), FMath::Abs(Cine->GetSequenceSeconds() - S->Number0) < 0.001);
			Test->TestTrue(TEXT("The world time held"), FMath::Abs(C.W->GetTimeSeconds() - S->Number1) < 0.001);
			Test->TestEqual(TEXT("No marker fired"), Cine->GetFiredMarkerCount(), S->Counter);
			Test->TestNotNull(TEXT("The overlay widget stays"), Cine->GetWidget());
			Test->TestEqual(TEXT("The skip hold did not advance"), Cine->GetSkipHoldFraction(), 0.f);
			Subsystem->ClosePause();
			S->Wall0 = FPlatformTime::Seconds();
			S->Number1 = C.W->GetTimeSeconds();
			S->Phase = 3;
			return false;

		case 3:
			// The sequence itself must also have held: if its player had kept running through the pause, the time would jump by about a second now.
			if (C.Frames < 3)
			{
				return false;
			}
			if (S->Counter != -1)
			{
				S->Counter = -1;
				Test->TestTrue(FString::Printf(TEXT("After Resume the sequence continues from where it stopped (%.3f from %.3f)"), Cine->GetSequenceSeconds(), S->Number0),
					Cine->GetSequenceSeconds() - S->Number0 < 0.6);
			}
			if (C.W->GetTimeSeconds() - S->Number1 < 0.8)
			{
				return false;
			}
			Test->TestTrue(TEXT("...and advances again"), Cine->GetSequenceSeconds() - S->Number0 > 0.5);
			Cine->StopCinematic();
			return true;
		}
		return true;
	}, 90.f);

	UIEnqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUIPauseBellTest, "LastBell.Functional.UI.Pause.BellStopsAndResumes", LB_UIFUNC_FLAGS)
bool FLBUIPauseBellTest::RunTest(const FString& Parameters)
{
	TSharedRef<FUIRunner> R = UIStartSession(this);
	const TSharedRef<FUIState> S = R->S;
	FAutomationTestBase* Test = this;
	UIAddReady(*R);

	R->Add(TEXT("The audio director is up with a tagged moon and transient settings"), [S, Test](FUICtx& C)
	{
		if (S->Phase == 0)
		{
			S->StormSettings.Reset(NewObject<ULBStormSettings>(GetTransientPackage()));
			S->AudioSettings.Reset(NewObject<ULBAudioSettings>(GetTransientPackage()));
			S->AudioSettings->PlayBellSpacing = 0.5f;
			ADirectionalLight* Moon = C.W->SpawnActor<ADirectionalLight>(FVector(0.0, 0.0, 5000.0), FRotator(-40.f, 35.f, 0.f));
			ULBStormSubsystem* Storm = C.W->GetSubsystem<ULBStormSubsystem>();
			ULBAudioSubsystem* Audio = C.W->GetSubsystem<ULBAudioSubsystem>();
			if (!Test->TestNotNull(TEXT("Moon"), Moon) || !Test->TestNotNull(TEXT("Storm subsystem"), Storm) || !Test->TestNotNull(TEXT("Audio subsystem"), Audio))
			{
				return true;
			}
			S->Actors.Add(Moon);
			if (ULightComponent* Light = Moon->GetLightComponent())
			{
				Light->SetMobility(EComponentMobility::Movable);
				Light->SetIntensity(0.9f);
			}
			Moon->Tags.Add(FName(TEXT("LB_StormMoon")));
			Storm->OverrideSettings(S->StormSettings.Get());
			Storm->RefreshLinkedLights();
			Audio->OverrideSettings(S->AudioSettings.Get());
			Audio->Rearm();
			S->Phase = 1;
			return false;
		}
		const ULBAudioSubsystem* Audio = C.W->GetSubsystem<ULBAudioSubsystem>();
		if (Audio && Audio->IsActive() && C.Frames >= 4)
		{
			return true;
		}
		if (C.Elapsed > 3.0)
		{
			Test->AddError(TEXT("The audio director did not become active within 3 s"));
			return true;
		}
		return false;
	});

	R->Add(TEXT("A scheduled strike does not play during the pause; it plays after Resume"), [S, Test](FUICtx& C)
	{
		ULBUISubsystem* Subsystem = UIGet(C.W);
		ULBAudioSubsystem* Audio = C.W->GetSubsystem<ULBAudioSubsystem>();
		if (!Subsystem || !Audio)
		{
			Test->AddError(TEXT("The UI or the audio subsystem is missing"));
			return true;
		}
		auto StageRequests = [Audio](int32 Stage)
		{
			int32 Count = 0;
			for (const FLBAudioRequest& Request : Audio->GetRequests())
			{
				Count += (Request.Cue == LBAudioCue::Bell && Request.Aux == Stage) ? 1 : 0;
			}
			return Count;
		};
		auto BellRequests = [Audio]()
		{
			int32 Count = 0;
			for (const FLBAudioRequest& Request : Audio->GetRequests())
			{
				Count += Request.Cue == LBAudioCue::Bell ? 1 : 0;
			}
			return Count;
		};

		switch (S->Phase)
		{
		case 1:
			Audio->ClearRequests();
			S->Counter = Audio->GetScheduledCount();
			Audio->PlayBell(3, 4);
			Test->TestEqual(TEXT("Four strikes were added to the schedule"), Audio->GetScheduledCount(), S->Counter + 4);
			// Pause in the same frame, before the schedule's next tick can play the first strike.
			if (!Test->TestTrue(TEXT("OpenPause succeeds"), Subsystem->OpenPause()))
			{
				return true;
			}
			S->Wall0 = FPlatformTime::Seconds();
			S->Phase = 2;
			return false;

		case 2:
			if (FPlatformTime::Seconds() - S->Wall0 < 1.5 || C.Frames < 20)
			{
				return false;
			}
			Test->TestEqual(TEXT("No bell strike played during the pause"), BellRequests(), 0);
			Test->TestEqual(TEXT("The schedule did not change"), Audio->GetScheduledCount(), S->Counter + 4);
			Subsystem->ClosePause();
			S->T0 = C.W->GetTimeSeconds();
			S->Phase = 3;
			return false;

		default:
			if (C.W->GetTimeSeconds() - S->T0 < 3.0)
			{
				return false;
			}
			Test->TestEqual(TEXT("After Resume all four stage-3 strikes played"), StageRequests(3), 4);
			for (const FLBAudioRequest& Request : Audio->GetRequests())
			{
				if (Request.Cue == LBAudioCue::Bell)
				{
					Test->TestTrue(TEXT("Every strike came after the pause ended"), Request.Time >= S->T0 - 0.001);
				}
			}
			return true;
		}
	}, 60.f);

	UIEnqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUIPauseBlockedTest, "LastBell.Functional.UI.Pause.BlockedDuringTravelAndDeath", LB_UIFUNC_FLAGS)
bool FLBUIPauseBlockedTest::RunTest(const FString& Parameters)
{
	TSharedRef<FUIRunner> R = UIStartSession(this);
	const TSharedRef<FUIState> S = R->S;
	FAutomationTestBase* Test = this;
	UIAddReady(*R);

	R->Add(TEXT("Pause is refused on the main menu and while the player is dying; Escape is consumed, not leaked"), [S, Test](FUICtx& C)
	{
		ULBUISubsystem* Subsystem = UIGet(C.W);
		ALBCharacter* Pawn = LBPie::Pawn();
		if (!Subsystem || !Pawn)
		{
			Test->AddError(TEXT("The UI subsystem or the pawn is missing"));
			return true;
		}
		FString Why;
		Test->TestTrue(TEXT("A healthy player in play may pause"), Subsystem->CanOpenPause(&Why));

		// The main menu: Escape means Back there.
		Subsystem->PushScreen(ELBScreen::MainMenu);
		Test->TestFalse(TEXT("No pause on the main menu"), Subsystem->CanOpenPause(&Why));
		Test->TestTrue(TEXT("...and it says so"), Why.Contains(TEXT("main menu")));
		Test->TestFalse(TEXT("OpenPause refuses"), Subsystem->OpenPause());
		Test->TestFalse(TEXT("The world is not paused"), C.W->IsPaused());
		Subsystem->ClearScreens();

		// A death: IsDead is true from the moment of the call (a killer makes it a slow catch, so the session ends before the level reloads).
		AActor* Killer = C.W->SpawnActor<AActor>(Pawn->GetActorLocation() + FVector(400.0, 0.0, 0.0), FRotator::ZeroRotator);
		S->Actors.Add(Killer);
		Pawn->Kill(Killer);
		Test->TestTrue(TEXT("The player is dead"), Pawn->IsDead());
		Test->TestFalse(TEXT("No pause during the death"), Subsystem->CanOpenPause(&Why));
		Test->TestTrue(TEXT("...and it says so"), Why.Contains(TEXT("dead")));
		Test->TestTrue(TEXT("Escape is consumed (HandleBack returns true)"), Subsystem->HandleBack());
		Test->TestFalse(TEXT("...but opened nothing"), Subsystem->IsPauseOpen() || C.W->IsPaused());
		Test->TestEqual(TEXT("No screen"), Subsystem->GetScreenCount(), 0);
		return true;
	});

	UIEnqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUIPauseInspectionTest, "LastBell.Functional.UI.Pause.EscapeClosesInspectionFirst", LB_UIFUNC_FLAGS)
bool FLBUIPauseInspectionTest::RunTest(const FString& Parameters)
{
	TSharedRef<FUIRunner> R = UIStartSession(this);
	const TSharedRef<FUIState> S = R->S;
	FAutomationTestBase* Test = this;
	UIAddReady(*R);

	R->Add(TEXT("The first Escape closes the note, the second opens the pause menu"), [S, Test](FUICtx& C)
	{
		ULBUISubsystem* Subsystem = UIGet(C.W);
		ALBCharacter* Pawn = LBPie::Pawn();
		if (!Subsystem || !Pawn || !Pawn->GetInspection())
		{
			Test->AddError(TEXT("The UI subsystem, the pawn or its inspection component is missing"));
			return true;
		}
		ULBInspectionComponent* Inspection = Pawn->GetInspection();

		if (S->Phase == 0)
		{
			const FVector Base = Pawn->GetActorLocation() + FVector(300.0, 0.0, 100.0);
			AStaticMeshActor* UINote = C.W->SpawnActor<AStaticMeshActor>(Base, FRotator::ZeroRotator);
			if (!Test->TestNotNull(TEXT("The note actor spawned"), UINote))
			{
				return true;
			}
			S->Actors.Add(UINote);
			UINote->SetMobility(EComponentMobility::Movable);
			UINote->SetActorLocation(Base);
			ULBInspectableComponent* Inspectable = NewObject<ULBInspectableComponent>(UINote);
			UINote->AddInstanceComponent(Inspectable);
			Inspectable->RegisterComponent();
			if (!Test->TestTrue(TEXT("BeginInspect succeeded"), Inspection->BeginInspect(Inspectable)))
			{
				return true;
			}
			Test->TestTrue(TEXT("The player is inspecting"), Inspection->IsInspecting());
			S->Phase = 1;
			return false;
		}
		if (S->Phase == 1)
		{
			// RequestClose ignores the first frames after BeginInspect: press Escape on later frames.
			if (C.Frames < 6)
			{
				return false;
			}
			Test->TestTrue(TEXT("Escape is consumed"), Subsystem->HandleBack());
			if (Inspection->IsInspecting() && C.Frames < 40)
			{
				return false;
			}
			Test->TestFalse(TEXT("The first Escape closed the note"), Inspection->IsInspecting());
			Test->TestFalse(TEXT("...and did not pause"), Subsystem->IsPauseOpen() || C.W->IsPaused());
			S->Phase = 2;
			return false;
		}
		Test->TestTrue(TEXT("The second Escape is consumed"), Subsystem->HandleBack());
		Test->TestTrue(TEXT("...and opens the pause menu"), Subsystem->IsPauseOpen() && C.W->IsPaused());
		Test->TestEqual(TEXT("The pause screen is on top"), Subsystem->GetTopScreen(), ELBScreen::Pause);

		// Escape again resumes exactly where it stopped.
		const double Time = C.W->GetTimeSeconds();
		Test->TestTrue(TEXT("Escape in the pause menu is consumed"), Subsystem->HandleBack());
		Test->TestFalse(TEXT("It resumes"), Subsystem->IsPauseOpen() || C.W->IsPaused());
		Test->TestTrue(TEXT("The time is where it stopped"), FMath::Abs(C.W->GetTimeSeconds() - Time) < 0.001);
		return true;
	});

	UIEnqueue(R);
	return true;
}

// =====================================================================================================================
// Rebinding (EXPECTED TO FAIL until P18-2: needs Enhanced Input user settings and the IMC mapping names)
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUIRebindTest, "LastBell.Functional.UI.Rebind.InteractChangesPromptAndSkip", LB_UIFUNC_FLAGS)
bool FLBUIRebindTest::RunTest(const FString& Parameters)
{
	TSharedRef<FUIRunner> R = UIStartSession(this);
	const TSharedRef<FUIState> S = R->S;
	FAutomationTestBase* Test = this;
	UIAddReady(*R);

	R->Add(TEXT("Rebinding Interact changes the prompt icon and the skip prompt; conflicts are refused; Reset restores E"), [S, Test](FUICtx& C)
	{
		APlayerController* PC = C.W->GetFirstPlayerController();
		ULocalPlayer* LocalPlayer = PC ? PC->GetLocalPlayer() : nullptr;
		if (!Test->TestNotNull(TEXT("A local player"), LocalPlayer))
		{
			return true;
		}
		if (!Test->TestTrue(TEXT("P18-2: Enhanced Input user settings are on and IMC_LB_Gameplay names its mappings LB_Interact etc."), LBKeyBindings::IsRebindable(LocalPlayer, ELBBindAction::Interact)))
		{
			return true;
		}
		LBKeyBindings::ResetAll(LocalPlayer);

		ULBKeyIconWidget* Prompt = CreateWidget<ULBKeyIconWidget>(PC, ULBKeyIconWidget::StaticClass());
		ULBCinematicWidget* Overlay = CreateWidget<ULBCinematicWidget>(PC, ULBCinematicWidget::StaticClass());
		if (!Test->TestNotNull(TEXT("The prompt icon widget"), Prompt) || !Test->TestNotNull(TEXT("The cinematic overlay widget"), Overlay))
		{
			return true;
		}
		Prompt->SetBoundAction(ELBBindAction::Interact);
		Test->TestEqual(TEXT("The prompt shows E at first"), Prompt->GetKey(), EKeys::E);
		const ULBKeyIconWidget* SkipIcon = Overlay->GetSkipKeyIconForTest();
		if (Test->TestNotNull(TEXT("The skip prompt has a key icon"), SkipIcon))
		{
			Test->TestEqual(TEXT("The skip prompt shows E at first"), SkipIcon->GetKey(), EKeys::E);
		}

		const LBKeyBindings::FRebindResult Done = LBKeyBindings::Rebind(LocalPlayer, ELBBindAction::Interact, EKeys::R);
		Test->TestTrue(TEXT("Interact rebinds to R"), Done.bOk);
		Test->TestEqual(TEXT("GetKey follows"), LBKeyBindings::GetKey(LocalPlayer, ELBBindAction::Interact), EKeys::R);
		Test->TestEqual(TEXT("The prompt icon followed the binding"), Prompt->GetKey(), EKeys::R);
		if (SkipIcon)
		{
			Test->TestEqual(TEXT("The skip prompt followed the binding"), SkipIcon->GetKey(), EKeys::R);
		}
		Test->TestFalse(TEXT("A key-cap names the key when there is no icon"), Prompt->IsShowingIconForTest() ? false : Prompt->GetCapTextForTest().IsEmpty());

		const LBKeyBindings::FRebindResult Clash = LBKeyBindings::Rebind(LocalPlayer, ELBBindAction::Candle, EKeys::R);
		Test->TestFalse(TEXT("Candle on R is refused (R is Interact now)"), Clash.bOk);
		Test->TestEqual(TEXT("...naming the action in the way"), Clash.Conflict, ELBBindAction::Interact);
		Test->TestFalse(TEXT("...with a message"), Clash.Message.IsEmpty());
		Test->TestEqual(TEXT("Candle kept its key"), LBKeyBindings::GetKey(LocalPlayer, ELBBindAction::Candle), EKeys::F);
		Test->TestFalse(TEXT("A gamepad button is refused"), LBKeyBindings::Rebind(LocalPlayer, ELBBindAction::Candle, EKeys::Gamepad_FaceButton_Bottom).bOk);

		LBKeyBindings::ResetAll(LocalPlayer);
		Test->TestEqual(TEXT("Reset to defaults restores E"), LBKeyBindings::GetKey(LocalPlayer, ELBBindAction::Interact), EKeys::E);
		Test->TestEqual(TEXT("...and the prompt follows"), Prompt->GetKey(), EKeys::E);
		return true;
	});

	UIEnqueue(R);
	return true;
}

// =====================================================================================================================
// Settings
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUIFOVTest, "LastBell.Functional.UI.Settings.FOVApplies", LB_UIFUNC_FLAGS)
bool FLBUIFOVTest::RunTest(const FString& Parameters)
{
	TSharedRef<FUIRunner> R = UIStartSession(this);
	const TSharedRef<FUIState> S = R->S;
	FAutomationTestBase* Test = this;
	UIAddReady(*R);

	R->Add(TEXT("The camera takes the user's FOV, motion blur and film grain settings"), [S, Test](FUICtx& C)
	{
		ALBCharacter* Pawn = LBPie::Pawn();
		ULBUserSettings* Settings = ULBUserSettings::GetUserSettings();
		UCameraComponent* Camera = Pawn ? Pawn->FindComponentByClass<UCameraComponent>() : nullptr;
		if (!Test->TestNotNull(TEXT("The player camera"), Camera) || !Test->TestNotNull(TEXT("The user settings"), Settings))
		{
			return true;
		}
		switch (S->Phase)
		{
		case 0:
			// The default FOV is today's camera FOV.
			if (C.Frames < 5)
			{
				return false;
			}
			Settings->SetFieldOfViewTransient(LBUILogic::DefaultFOV);
			S->Phase = 1;
			return false;
		case 1:
			if (C.Frames < 3)
			{
				return false;
			}
			Test->TestTrue(FString::Printf(TEXT("FOV 90 (the default) reads 90 on the idle camera (%.2f)"), Camera->FieldOfView), FMath::IsNearlyEqual(Camera->FieldOfView, 90.f, 0.05f));
			Settings->SetFieldOfViewTransient(100.f);
			S->Counter = C.Frames;
			S->Phase = 2;
			return false;
		case 2:
			if (C.Frames < S->Counter + 3)
			{
				return false;
			}
			Test->TestTrue(FString::Printf(TEXT("FOV 100 reaches the camera (%.2f)"), Camera->FieldOfView), FMath::IsNearlyEqual(Camera->FieldOfView, 100.f, 0.05f));
			Settings->SetFieldOfViewTransient(72.f);
			Settings->bMotionBlur = false;
			Settings->bFilmGrain = false;
			S->Counter = C.Frames;
			S->Phase = 3;
			return false;
		case 3:
			if (C.Frames < S->Counter + 3)
			{
				return false;
			}
			Test->TestTrue(FString::Printf(TEXT("FOV 72 reaches the camera (%.2f)"), Camera->FieldOfView), FMath::IsNearlyEqual(Camera->FieldOfView, 72.f, 0.05f));
			Test->TestTrue(TEXT("Motion blur off overrides the amount to 0"), Camera->PostProcessSettings.bOverride_MotionBlurAmount && Camera->PostProcessSettings.MotionBlurAmount == 0.f);
			Test->TestTrue(TEXT("Film grain off overrides the intensity to 0"), Camera->PostProcessSettings.bOverride_FilmGrainIntensity && Camera->PostProcessSettings.FilmGrainIntensity == 0.f);
			Settings->bMotionBlur = true;
			Settings->bFilmGrain = true;
			S->Counter = C.Frames;
			S->Phase = 4;
			return false;
		default:
			if (C.Frames < S->Counter + 3)
			{
				return false;
			}
			Test->TestTrue(TEXT("Motion blur on forces the engine default amount"), Camera->PostProcessSettings.bOverride_MotionBlurAmount && Camera->PostProcessSettings.MotionBlurAmount > 0.f);
			Test->TestFalse(TEXT("Film grain on leaves the level's value alone (no override)"), Camera->PostProcessSettings.bOverride_FilmGrainIntensity);
			return true;
		}
	});

	UIEnqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUIBrightnessGateTest, "LastBell.Functional.UI.Brightness.FirstLaunchGate", LB_UIFUNC_FLAGS)
bool FLBUIBrightnessGateTest::RunTest(const FString& Parameters)
{
	TSharedRef<FUIRunner> R = UIStartSession(this, false, false, /*bCalibrated*/ false);
	const TSharedRef<FUIState> S = R->S;
	FAutomationTestBase* Test = this;
	UIAddReady(*R);

	R->Add(TEXT("First launch: the brightness screen comes before the menu, cannot be skipped, and is never shown again once confirmed"), [S, Test](FUICtx& C)
	{
		ULBUISubsystem* Subsystem = UIGet(C.W);
		ULBUserSettings* Settings = ULBUserSettings::GetUserSettings();
		if (!Subsystem || !Settings)
		{
			Test->AddError(TEXT("The UI subsystem or the user settings are missing"));
			return true;
		}
		Settings->Gamma = LBUILogic::DefaultGamma;
		Test->TestFalse(TEXT("Not calibrated yet"), Settings->bBrightnessCalibrated);

		Subsystem->PushScreen(ELBScreen::MainMenu);
		Test->TestEqual(TEXT("The brightness screen is on top of the menu"), Subsystem->GetTopScreen(), ELBScreen::Brightness);
		Test->TestTrue(TEXT("It is the first-launch one"), Subsystem->IsFirstLaunchBrightnessOpen());
		Test->TestEqual(TEXT("The menu waits below"), Subsystem->GetScreenCount(), 2);

		Subsystem->HandleBack();
		Test->TestEqual(TEXT("Back is ignored on the first launch"), Subsystem->GetTopScreen(), ELBScreen::Brightness);

		ULBBrightnessWidget* Screen = Cast<ULBBrightnessWidget>(Subsystem->GetTopWidget());
		if (!Test->TestNotNull(TEXT("The brightness widget"), Screen))
		{
			return true;
		}
		const int32 SliderItem = 0;
		Screen->AdjustItem(SliderItem, 1);
		Test->TestTrue(TEXT("The slider moved the gamma up"), Settings->Gamma > LBUILogic::DefaultGamma - 0.001f);
		Screen->ConfirmBrightness();
		Test->TestTrue(TEXT("Confirm marks it as calibrated"), Settings->bBrightnessCalibrated);
		Test->TestEqual(TEXT("The main menu is on top again"), Subsystem->GetTopScreen(), ELBScreen::MainMenu);
		Test->TestFalse(TEXT("The first-launch flag is gone"), Subsystem->IsFirstLaunchBrightnessOpen());

		// Never shown again.
		Subsystem->ClearScreens();
		Subsystem->PushScreen(ELBScreen::MainMenu);
		Test->TestEqual(TEXT("The second time the menu opens straight away"), Subsystem->GetTopScreen(), ELBScreen::MainMenu);
		Subsystem->ClearScreens();

		// From Settings it can be opened again, and Back puts the gamma back.
		const float Before = Settings->Gamma;
		Subsystem->OpenBrightness(/*bFirstLaunch*/ false);
		Test->TestEqual(TEXT("Opened from Settings"), Subsystem->GetTopScreen(), ELBScreen::Brightness);
		Test->TestFalse(TEXT("It is not the first-launch one"), Subsystem->IsFirstLaunchBrightnessOpen());
		Settings->SetGammaTransient(2.5f);
		Subsystem->HandleBack();
		Test->TestEqual(TEXT("Back closes it"), Subsystem->GetScreenCount(), 0);
		Test->TestTrue(TEXT("...and the gamma is what it was"), FMath::IsNearlyEqual(Settings->Gamma, Before, 0.001f));
		return true;
	});

	UIEnqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUISettingsScreenTest, "LastBell.Functional.UI.Settings.TabsApplyAndPersist", LB_UIFUNC_FLAGS)
bool FLBUISettingsScreenTest::RunTest(const FString& Parameters)
{
	TSharedRef<FUIRunner> R = UIStartSession(this);
	const TSharedRef<FUIState> S = R->S;
	FAutomationTestBase* Test = this;
	UIAddReady(*R);

	R->Add(TEXT("Each tab builds; Audio and Accessibility apply at once; the preset shows Custom; Back discards graphics changes"), [S, Test](FUICtx& C)
	{
		ULBUISubsystem* Subsystem = UIGet(C.W);
		ULBUserSettings* Settings = ULBUserSettings::GetUserSettings();
		if (!Subsystem || !Settings)
		{
			Test->AddError(TEXT("The UI subsystem or the user settings are missing"));
			return true;
		}
		Subsystem->OpenSettings();
		ULBSettingsWidget* Screen = Cast<ULBSettingsWidget>(Subsystem->GetTopWidget());
		if (!Test->TestNotNull(TEXT("The settings screen"), Screen))
		{
			return true;
		}

		// Every tab builds rows.
		for (int32 Tab = 0; Tab < 5; ++Tab)
		{
			Screen->SwitchTab(static_cast<ELBSettingsTab>(Tab));
			Test->TestEqual(TEXT("The tab switched"), static_cast<int32>(Screen->GetActiveTab()), Tab);
			Test->TestTrue(FString::Printf(TEXT("Tab %d has rows"), Tab), Screen->GetItemCount() > 1);
		}

		// Audio: a slider adjusts the user's volume and saves.
		Settings->SetVolumeTransient(ELBAudioVolumeGroup::Music, 1.f);
		Screen->SwitchTab(ELBSettingsTab::Audio);
		Test->TestEqual(TEXT("Six volume sliders and Back"), Screen->GetItemCount(), 7);
		const int32 Music = 3;
		Screen->SelectItem(Music, false);
		Screen->AdjustItem(Music, -1);
		Test->TestTrue(FString::Printf(TEXT("Music went down one step (%.2f)"), Settings->MusicVolume), FMath::Abs(Settings->MusicVolume - 0.95f) < 0.011f);

		// Accessibility: toggles and the FOV slider.
		Settings->FieldOfView = LBUILogic::DefaultFOV;
		Settings->bMotionBlur = false;
		Settings->bHighContrastPrompts = false;
		Screen->SwitchTab(ELBSettingsTab::Accessibility);
		Test->TestEqual(TEXT("FOV, blur, grain, high contrast, brightness at launch, Back"), Screen->GetItemCount(), 6);
		Screen->AdjustItem(0, 1);
		Test->TestEqual(TEXT("FOV went up one degree"), Settings->FieldOfView, LBUILogic::DefaultFOV + 1.f);
		Screen->ActivateItem(1);
		Test->TestTrue(TEXT("Motion blur toggled on"), Settings->bMotionBlur);
		Screen->ActivateItem(3);
		Test->TestTrue(TEXT("High-contrast prompts toggled on"), Settings->bHighContrastPrompts);

		// Graphics: changing one group reads as Custom; Back discards it.
		Screen->SwitchTab(ELBSettingsTab::Graphics);
		const FLBGraphicsSnapshot Baseline = FLBGraphicsSettings::Capture();
		Screen->SetPresetForTest(2);
		Test->TestEqual(TEXT("Choosing the High preset sets every group to it"), FLBGraphicsSettings::GetPreset(), 2);
		const int32 Shadows = Screen->GetGroupItemForTest(ELBGraphicsGroup::Shadows);
		Screen->AdjustItem(Shadows, -1);
		Test->TestEqual(TEXT("One group differs: the preset is Custom"), FLBGraphicsSettings::GetPreset(), -1);
		Screen->HandleBack();
		Test->TestEqual(TEXT("Back closed the screen"), Subsystem->GetScreenCount(), 0);
		Test->TestTrue(TEXT("Unapplied graphics changes were discarded"), FLBGraphicsSettings::Capture().Groups[static_cast<int32>(ELBGraphicsGroup::Shadows)] == Screen->GetBaselineForTest().Groups[static_cast<int32>(ELBGraphicsGroup::Shadows)]);
		FLBGraphicsSettings::Restore(Baseline);
		return true;
	});

	UIEnqueue(R);
	return true;
}


// =====================================================================================================================
// Dialogs and credits
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUIKeepDialogTest, "LastBell.Functional.UI.Confirm.KeepDialogRevertsOnTimeout", LB_UIFUNC_FLAGS)
bool FLBUIKeepDialogTest::RunTest(const FString& Parameters)
{
	TSharedRef<FUIRunner> R = UIStartSession(this);
	const TSharedRef<FUIState> S = R->S;
	FAutomationTestBase* Test = this;
	UIAddReady(*R);

	R->Add(TEXT("The keep dialog counts down in real time and answers Cancel (revert) when it ends; Keep stops the countdown"), [S, Test](FUICtx& C)
	{
		ULBUISubsystem* Subsystem = UIGet(C.W);
		if (!Test->TestNotNull(TEXT("The UI subsystem"), Subsystem))
		{
			return true;
		}
		TSharedRef<int32> Confirmed = MakeShared<int32>(0);
		TSharedRef<int32> Cancelled = MakeShared<int32>(0);
		FLBConfirmRequest Request;
		Request.Title = FText::FromString(TEXT("Keep these display settings?"));
		Request.Message = FText::FromString(TEXT("The display mode changed."));
		Request.TimeoutSeconds = LBUILogic::KeepDialogSeconds;
		Request.OnConfirm = [Confirmed]() { ++*Confirmed; };
		Request.OnCancel = [Cancelled]() { ++*Cancelled; };

		// Timeout: reverts.
		ULBConfirmWidget* Dialog = Cast<ULBConfirmWidget>(Subsystem->ShowConfirm(Request));
		if (!Test->TestNotNull(TEXT("The dialog"), Dialog))
		{
			return true;
		}
		Test->TestTrue(TEXT("The countdown runs"), Dialog->IsCountdownActive());
		Test->TestEqual(TEXT("It starts at 15"), Dialog->GetCountdownSecondsShown(), 15);
		Dialog->AdvanceCountdownForTest(14.f);
		Test->TestFalse(TEXT("Not answered after 14 s"), Dialog->HasAnswered());
		Test->TestEqual(TEXT("1 s shown"), Dialog->GetCountdownSecondsShown(), 1);
		Dialog->AdvanceCountdownForTest(1.5f);
		Test->TestTrue(TEXT("Answered when the time is up"), Dialog->HasAnswered());
		Test->TestEqual(TEXT("It reverted (Cancel ran once)"), *Cancelled, 1);
		Test->TestEqual(TEXT("It did not keep"), *Confirmed, 0);
		Test->TestEqual(TEXT("The dialog is gone"), Subsystem->GetScreenCount(), 0);

		// Keep: stops the countdown, runs Confirm once, and a late tick does nothing.
		Dialog = Cast<ULBConfirmWidget>(Subsystem->ShowConfirm(Request));
		if (Test->TestNotNull(TEXT("The second dialog"), Dialog))
		{
			Dialog->AdvanceCountdownForTest(5.f);
			Dialog->Confirm();
			Dialog->AdvanceCountdownForTest(60.f);
			Test->TestEqual(TEXT("Keep ran Confirm once"), *Confirmed, 1);
			Test->TestEqual(TEXT("...and the timeout did not revert it"), *Cancelled, 1);
			Test->TestEqual(TEXT("No dialog left"), Subsystem->GetScreenCount(), 0);
		}
		return true;
	});

	UIEnqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUICreditsTest, "LastBell.Functional.UI.Credits.RollsFromCinematicCredits", LB_UIFUNC_FLAGS)
bool FLBUICreditsTest::RunTest(const FString& Parameters)
{
	TSharedRef<FUIRunner> R = UIStartSession(this);
	const TSharedRef<FUIState> S = R->S;
	FAutomationTestBase* Test = this;
	UIAddReady(*R);

	R->Add(TEXT("The Credits screen builds the ending's lines and closes on Back"), [S, Test](FUICtx& C)
	{
		ULBUISubsystem* Subsystem = UIGet(C.W);
		if (!Test->TestNotNull(TEXT("The UI subsystem"), Subsystem))
		{
			return true;
		}
		if (S->Phase == 0)
		{
			Subsystem->OpenCredits();
			ULBCreditsWidget* Credits = Cast<ULBCreditsWidget>(Subsystem->GetTopWidget());
			if (!Test->TestNotNull(TEXT("The credits screen"), Credits))
			{
				return true;
			}
			Test->TestTrue(TEXT("It built the credit lines from DA_Cinematics"), Credits->GetCreditLineCountForTest() > 0);
			S->Phase = 1;
			S->Counter = C.Frames;
			return false;
		}
		const ULBCreditsWidget* Credits = Cast<ULBCreditsWidget>(Subsystem->GetTopWidget());
		if (!Credits)
		{
			Test->AddError(TEXT("The credits screen is gone"));
			return true;
		}
		if (C.Frames < S->Counter + 10)
		{
			return false;
		}
		Subsystem->HandleBack();
		Test->TestEqual(TEXT("Back closes it"), Subsystem->GetScreenCount(), 0);
		return true;
	});

	UIEnqueue(R);
	return true;
}

// =====================================================================================================================
// HUD (P18-3)
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUIHUDTest, "LastBell.Functional.UI.HUD.PromptKeyAndObjective", LB_UIFUNC_FLAGS)
bool FLBUIHUDTest::RunTest(const FString& Parameters)
{
	TSharedRef<FUIRunner> R = UIStartSession(this);
	const TSharedRef<FUIState> S = R->S;
	FAutomationTestBase* Test = this;
	UIAddReady(*R);

	R->Add(TEXT("The HUD is the C++ one and binds to the pawn and the objectives"), [S, Test](FUICtx& C)
	{
		ALBPlayerController* PC = UILBController(C.W);
		ULBHUDWidget* HUD = PC ? Cast<ULBHUDWidget>(PC->GetHUDWidget()) : nullptr;
		if (!Test->TestNotNull(TEXT("P18-3: BP_LBPlayerController.HUDWidgetClass is ULBHUDWidget"), HUD))
		{
			return true;
		}
		if (!HUD->IsBoundForTest())
		{
			if (C.Elapsed > 3.0)
			{
				Test->AddError(TEXT("The HUD did not bind to the pawn and the objective subsystem within 3 s"));
				return true;
			}
			return false;
		}
		Test->TestFalse(TEXT("Nothing is prompted at the start"), HUD->IsPromptVisibleForTest());
		Test->TestTrue(TEXT("The crosshair shows"), HUD->IsCrosshairVisibleForTest());
		Test->TestFalse(TEXT("No inspection overlay"), HUD->IsInspectOverlayVisibleForTest());
		Test->TestFalse(TEXT("No relight message"), HUD->IsCandleTextVisibleForTest());
		return true;
	});

	R->Add(TEXT("The prompt shows the current Interact key and the interactable's text; a denied prompt names no key; the objective text follows"), [S, Test](FUICtx& C)
	{
		ALBPlayerController* PC = UILBController(C.W);
		ULBHUDWidget* HUD = PC ? Cast<ULBHUDWidget>(PC->GetHUDWidget()) : nullptr;
		ALBCharacter* Pawn = LBPie::Pawn();
		ULocalPlayer* LocalPlayer = PC ? PC->GetLocalPlayer() : nullptr;
		if (!HUD || !Pawn || !Pawn->GetInteractor() || !LocalPlayer)
		{
			Test->AddError(TEXT("The HUD, the pawn or its interactor is missing"));
			return true;
		}
		ULBInteractorComponent* Interactor = Pawn->GetInteractor();

		AActor* Door = C.W->SpawnActor<AActor>(Pawn->GetActorLocation() + FVector(500.0, 0.0, 0.0), FRotator::ZeroRotator);
		if (!Test->TestNotNull(TEXT("A door actor"), Door))
		{
			return true;
		}
		S->Actors.Add(Door);
		USceneComponent* DoorRoot = NewObject<USceneComponent>(Door);
		Door->SetRootComponent(DoorRoot);
		DoorRoot->RegisterComponent();
		ULBInteractableComponent* Interactable = NewObject<ULBInteractableComponent>(Door);
		Interactable->PromptText = FText::FromString(TEXT("Open"));
		Interactable->DeniedPromptText = FText::FromString(TEXT("Locked"));
		Door->AddInstanceComponent(Interactable);
		Interactable->RegisterComponent();

		// A usable prompt: the key of the Interact binding and the text.
		Interactor->OnFocusChanged.Broadcast(Interactable, Interactable->PromptText);
		Test->TestTrue(TEXT("The prompt shows"), HUD->IsPromptVisibleForTest());
		Test->TestEqual(TEXT("...with the interactable's text"), HUD->GetPromptTextForTest().ToString(), FString(TEXT("Open")));
		Test->TestTrue(TEXT("...and the key"), HUD->IsPromptKeyVisibleForTest());
		const ULBKeyIconWidget* Key = HUD->GetPromptKeyIconForTest();
		if (Test->TestNotNull(TEXT("The prompt has a key icon"), Key))
		{
			Test->TestEqual(TEXT("It shows the current Interact key"), Key->GetKey(), LBKeyBindings::GetKey(LocalPlayer, ELBBindAction::Interact));
			Test->TestEqual(TEXT("...E by default"), Key->GetKey(), EKeys::E);
		}

		// Rebind: the prompt follows (P18-2 registered the mappings).
		const LBKeyBindings::FRebindResult Done = LBKeyBindings::Rebind(LocalPlayer, ELBBindAction::Interact, EKeys::R);
		Test->TestTrue(TEXT("Interact rebinds to R"), Done.bOk);
		if (Key)
		{
			Test->TestEqual(TEXT("The prompt now shows R"), Key->GetKey(), EKeys::R);
		}
		LBKeyBindings::ResetAll(LocalPlayer);
		if (Key)
		{
			Test->TestEqual(TEXT("Reset: E again"), Key->GetKey(), EKeys::E);
		}

		// A denied prompt: the text without the key.
		Interactor->OnFocusChanged.Broadcast(Interactable, Interactable->DeniedPromptText);
		Test->TestTrue(TEXT("The denied prompt shows"), HUD->IsPromptVisibleForTest());
		Test->TestEqual(TEXT("...with the denied text"), HUD->GetPromptTextForTest().ToString(), FString(TEXT("Locked")));
		Test->TestFalse(TEXT("...and no key"), HUD->IsPromptKeyVisibleForTest());

		// Nothing focused.
		Interactor->OnFocusChanged.Broadcast(nullptr, FText::GetEmpty());
		Test->TestFalse(TEXT("The prompt hides"), HUD->IsPromptVisibleForTest());

		// High contrast.
		Interactor->OnFocusChanged.Broadcast(Interactable, Interactable->PromptText);
		Test->TestFalse(TEXT("Normal prompt is not high-contrast"), HUD->IsPromptHighContrastForTest());
		ULBUserSettings::GetUserSettings()->SetHighContrastPrompts(true);
		Test->TestTrue(TEXT("High-contrast prompts switch the prompt's look"), HUD->IsPromptHighContrastForTest());
		if (Key)
		{
			Test->TestTrue(TEXT("...and the key glyph's"), Key->IsHighContrastForTest());
		}
		ULBUserSettings::GetUserSettings()->SetHighContrastPrompts(false);
		Interactor->OnFocusChanged.Broadcast(nullptr, FText::GetEmpty());

		// The objective.
		ULBObjectiveSubsystem* Objectives = C.W->GetSubsystem<ULBObjectiveSubsystem>();
		if (Test->TestNotNull(TEXT("The objective subsystem"), Objectives))
		{
			Objectives->OnObjectiveChanged.Broadcast(3, FText::FromString(TEXT("Find the bell key")));
			Test->TestTrue(TEXT("The objective shows"), HUD->IsObjectiveVisibleForTest());
			Test->TestEqual(TEXT("...with its text"), HUD->GetObjectiveTextForTest().ToString(), FString(TEXT("Find the bell key")));
			Objectives->OnObjectiveChanged.Broadcast(INDEX_NONE, FText::GetEmpty());
			Test->TestFalse(TEXT("An empty objective hides"), HUD->IsObjectiveVisibleForTest());
		}

		// The candle.
		if (ULBCandleComponent* Candle = Pawn->GetCandle())
		{
			Candle->OnRelightStarted.Broadcast();
			Test->TestTrue(TEXT("Relighting shows the message"), HUD->IsCandleTextVisibleForTest());
			Candle->OnCandleStateChanged.Broadcast(true);
			Test->TestFalse(TEXT("The candle lit hides it"), HUD->IsCandleTextVisibleForTest());
		}
		return true;
	});

	R->Add(TEXT("The inspection overlay shows the item's name and text and hides the crosshair, then goes away"), [S, Test](FUICtx& C)
	{
		ALBPlayerController* PC = UILBController(C.W);
		ULBHUDWidget* HUD = PC ? Cast<ULBHUDWidget>(PC->GetHUDWidget()) : nullptr;
		ALBCharacter* Pawn = LBPie::Pawn();
		if (!HUD || !Pawn || !Pawn->GetInspection())
		{
			Test->AddError(TEXT("The HUD, the pawn or its inspection component is missing"));
			return true;
		}
		const FVector Base = Pawn->GetActorLocation() + FVector(300.0, 0.0, 100.0);
		AStaticMeshActor* Note = C.W->SpawnActor<AStaticMeshActor>(Base, FRotator::ZeroRotator);
		if (!Test->TestNotNull(TEXT("The note actor"), Note))
		{
			return true;
		}
		S->Actors.Add(Note);
		Note->SetMobility(EComponentMobility::Movable);
		Note->SetActorLocation(Base);
		ULBInspectableComponent* Inspectable = NewObject<ULBInspectableComponent>(Note);
		Inspectable->DisplayName = FText::FromString(TEXT("Torn page"));
		Inspectable->BodyText = FText::FromString(TEXT("The bell must not ring."));
		Note->AddInstanceComponent(Inspectable);
		Inspectable->RegisterComponent();
		if (!Test->TestTrue(TEXT("BeginInspect succeeded"), Pawn->GetInspection()->BeginInspect(Inspectable)))
		{
			return true;
		}
		Test->TestTrue(TEXT("The overlay shows"), HUD->IsInspectOverlayVisibleForTest());
		Test->TestEqual(TEXT("...with the name"), HUD->GetInspectNameForTest().ToString(), FString(TEXT("Torn page")));
		Test->TestEqual(TEXT("...and the text"), HUD->GetInspectBodyForTest().ToString(), FString(TEXT("The bell must not ring.")));
		Test->TestFalse(TEXT("The crosshair hides while inspecting"), HUD->IsCrosshairVisibleForTest());
		Pawn->GetInspection()->CancelInspect();
		Test->TestFalse(TEXT("The overlay goes away"), HUD->IsInspectOverlayVisibleForTest());
		Test->TestTrue(TEXT("The crosshair is back"), HUD->IsCrosshairVisibleForTest());
		return true;
	});

	UIEnqueue(R);
	return true;
}

// =====================================================================================================================
// Loading screen
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUILoadingTest, "LastBell.Functional.UI.Loading.ScreenShownOnTravel", LB_UIFUNC_FLAGS)
bool FLBUILoadingTest::RunTest(const FString& Parameters)
{
	TSharedRef<FUIRunner> R = UIStartSession(this);
	const TSharedRef<FUIState> S = R->S;
	FAutomationTestBase* Test = this;
	UIAddReady(*R);

	R->Add(TEXT("Return to main menu arms the loading screen, blocks the pause, and the screen is taken back after the load"), [S, Test](FUICtx& C)
	{
		if (S->Phase == 0)
		{
			ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(C.W);
			ULBUISubsystem* Subsystem = UIGet(C.W);
			if (!Save || !Subsystem)
			{
				Test->AddError(TEXT("The save or the UI subsystem is missing"));
				return true;
			}
			Test->TestTrue(TEXT("The project's game instance is the LB one"), Cast<ULBGameInstance>(C.W->GetGameInstance()) != nullptr);
			Test->TestTrue(TEXT("The loading screen attributes are valid"), LBLoadingScreen::ValidateAttributes());
			S->ArmCount = LBLoadingScreen::GetArmCount();
			S->OldWorld = C.W;
			Save->ReturnToMainMenu();
			Test->TestTrue(TEXT("A travel started"), Save->IsTravelPending());
			Test->TestEqual(TEXT("The loading screen was armed once for it"), LBLoadingScreen::GetArmCount(), S->ArmCount + 1);
			Test->TestTrue(TEXT("It reads as armed"), LBLoadingScreen::IsArmed());
			FString Why;
			Test->TestFalse(TEXT("The pause is refused during the travel"), Subsystem->CanOpenPause(&Why));
			Test->TestTrue(TEXT("...because of the travel"), Why.Contains(TEXT("travel")));
			Test->TestFalse(TEXT("OpenPause refuses"), Subsystem->OpenPause());
			S->Phase = 1;
			return false;
		}
		// The menu map is up: the movie player's screen was taken back.
		if (!C.W || C.W == S->OldWorld.Get() || !C.W->HasBegunPlay() || FPackageName::GetShortName(LBPie::MapShortName()) != TEXT("L_MainMenu"))
		{
			return false;
		}
		Test->TestFalse(TEXT("The loading screen is no longer armed after the load"), LBLoadingScreen::IsArmed());
		return true;
	}, 90.f);

	UIEnqueue(R);
	return true;
}

#endif
