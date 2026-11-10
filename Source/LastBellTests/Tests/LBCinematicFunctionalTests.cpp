#include "Tests/LBRouteBot.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Editor.h"
#include "EngineUtils.h"
#include "Tests/AutomationEditorCommon.h"
#include "AI/LBWardenBrainComponent.h"
#include "AI/LBWardenController.h"
#include "Audio/LBAudioSubsystem.h"
#include "Audio/LBAudioTypes.h"
#include "Camera/PlayerCameraManager.h"
#include "Character/LBCharacter.h"
#include "Cinematics/LBCinematicLogic.h"
#include "Cinematics/LBCinematicSettings.h"
#include "Cinematics/LBCinematicSubsystem.h"
#include "Cinematics/LBCinematicWidget.h"
#include "Components/CapsuleComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "LevelSequence.h"
#include "MovieScene.h"
#include "Misc/PackageName.h"
#include "Save/LBCheckpoint.h"
#include "Save/LBSaveSubsystem.h"
#include "Systems/LBGameSettings.h"
#include "Systems/LBPlayerController.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "UObject/StrongObjectPtr.h"
#include "LBLog.h"

// P17-1 functional tests of the cinematic subsystem (LastBell.Functional.Cine.*).
//
// Content-free tests (NoCheckpointDuringCinematic, DisabledByCVar, MissingSequenceFailsSafe, BellSwingPieces) load L_Test_Warden and play a
// transient ULevelSequence built here (marked frames through UMovieScene::AddMarkedFrame), handed over with OverrideSettings + Rearm, so they
// need none of the LS_LB_* sequences or DA_Cinematics. The others open L_Monastery and need the content of P17-2 to P17-5b: they are EXPECTED
// TO FAIL until it exists (Monastery.CinematicSetup, IntroOnNewGame, NoIntroOnContinue, IntroSkip, FinaleOnBell, BellSwingsOnStrike).
// lb.Warden.Enabled is 0 for the sessions; lb.Cine.Enabled and lb.Cine.Rate are put back afterwards.

#define LB_CINEFUNC_FLAGS (EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

namespace LBCineTest
{
	const TCHAR* GCineTestMap = TEXT("/Game/LastBell/Maps/L_Test_Warden");
	const TCHAR* GCineMonasteryMap = TEXT("/Game/LastBell/Maps/L_Monastery");
	const TCHAR* GCineMainMenuMap = TEXT("/Game/LastBell/Maps/L_MainMenu");

	void CineNote(const FString& Text) { UE_LOG(LogLB, Display, TEXT("[CineTest] %s"), *Text); }

	struct FCineCtx
	{
		UWorld* W = nullptr;
		double Elapsed = 0.0; // world seconds since the step began
		double Now = 0.0;
		int32 Frames = 0;
	};

	struct FCineState
	{
		TStrongObjectPtr<ULBCinematicSettings> Settings;
		TArray<TStrongObjectPtr<ULevelSequence>> Sequences;
		TArray<FString> Fired;
		TArray<TWeakObjectPtr<AActor>> Actors;
		TWeakObjectPtr<UWorld> OldWorld;
		FQuat BellRest = FQuat::Identity;
		FQuat HeadRest = FQuat::Identity;
		FVector BellRestLoc = FVector::ZeroVector;
		FVector HeadRestLoc = FVector::ZeroVector;
		FVector RopeRestLoc = FVector::ZeroVector;
		FVector MarkLoc = FVector::ZeroVector;
		double T0 = 0.0;
		double TSkip = 0.0;
		int32 Phase = 0;
		int32 Counter = 0;
		bool bFlagA = false;
		bool bFlagB = false;
		bool bFlagC = false;
		float Number = 0.f;
	};

	ULBCinematicSubsystem* Cine(UWorld* W) { return W ? W->GetSubsystem<ULBCinematicSubsystem>() : nullptr; }

	void SetCVar(const TCHAR* Name, float Value)
	{
		if (IConsoleVariable* Var = IConsoleManager::Get().FindConsoleVariable(Name))
		{
			Var->Set(Value, ECVF_SetByCode);
		}
	}

	AActor* FindTagged(UWorld* W, const TCHAR* Tag)
	{
		for (TActorIterator<AActor> It(W); It; ++It)
		{
			if (It->ActorHasTag(FName(Tag)))
			{
				return *It;
			}
		}
		return nullptr;
	}

	int32 CountTagged(UWorld* W, const TCHAR* Tag)
	{
		int32 Count = 0;
		for (TActorIterator<AActor> It(W); It; ++It)
		{
			Count += It->ActorHasTag(FName(Tag)) ? 1 : 0;
		}
		return Count;
	}

	/** A transient level sequence of the given length (30 fps display, 24000 tick resolution) with marked frames. */
	TSoftObjectPtr<ULevelSequence> MakeSequence(FCineState& S, double Seconds, const TArray<TPair<double, FString>>& Markers)
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

	/** A settings object with one definition. The caller hands it over with OverrideSettings + Rearm. */
	ULBCinematicSettings* MakeSettings(FCineState& S, const FLBCinematicDef& Def)
	{
		S.Settings.Reset(NewObject<ULBCinematicSettings>(GetTransientPackage()));
		S.Settings->Cinematics.Add(Def);
		return S.Settings.Get();
	}

	class FCineRunner : public IAutomationLatentCommand
	{
	public:
		using FStepFn = TFunction<bool(FCineCtx&)>;

		FCineRunner(FAutomationTestBase* InTest, bool bCineEnabled, float Rate)
			: S(MakeShared<FCineState>()), Test(InTest), WardenOff(false), CineSwitch(bCineEnabled), CineRate(Rate)
		{
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
				CineNote(FString::Printf(TEXT("STEP %d begin: %s"), StepIndex + 1, *Step.Name));
			}

			FCineCtx Ctx;
			Ctx.W = W;
			Ctx.Now = W ? W->GetTimeSeconds() : 0.0;
			Ctx.Elapsed = Ctx.Now - WorldStart;
			Ctx.Frames = Frames;
			++Frames;

			const bool bDone = Step.Fn(Ctx);
			const bool bTimedOut = !bDone && (FPlatformTime::Seconds() - WallStart) > Step.Timeout;
			if (bTimedOut)
			{
				Test->AddError(FString::Printf(TEXT("Step '%s' timed out after %.0fs (map %s, phase %d)"), *Step.Name, Step.Timeout, *LBPie::MapShortName(), S->Phase));
			}
			if (bDone || bTimedOut)
			{
				CineNote(FString::Printf(TEXT("STEP %d %s: %s"), StepIndex + 1, ErrCount() == ErrorsAtStart ? TEXT("PASS") : TEXT("FAIL"), *Step.Name));
				if (bTimedOut || ErrCount() != ErrorsAtStart)
				{
					bAbort = true;
				}
				++StepIndex;
				bEntered = false;
			}
			return false;
		}

		TSharedRef<FCineState> S;

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
			LBPie::ClearSlot();
		}

		FAutomationTestBase* Test;
		LBPie::FWardenSwitch WardenOff;
		LBPie::FCineSwitch CineSwitch;
		LBPie::FCineRate CineRate;
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

	TSharedRef<FCineRunner> StartSession(FAutomationTestBase* Test, const TCHAR* Map, bool bCineEnabled, float Rate)
	{
		LBPie::ClearSlot();
		TSharedRef<FCineRunner> Runner = MakeShared<FCineRunner>(Test, bCineEnabled, Rate);
		FAutomationEditorCommonUtils::LoadMap(Map);
		FRequestPlaySessionParams PlayParams;
		PlayParams.WorldType = EPlaySessionWorldType::PlayInEditor;
		GEditor->RequestPlaySession(PlayParams);
		return Runner;
	}

	void Enqueue(const TSharedRef<FCineRunner>& Runner)
	{
		FAutomationTestFramework::Get().EnqueueLatentCommand(Runner);
	}

	/** The first step of every test: the PIE world is up and has ticked a few frames. */
	void AddReady(FCineRunner& R)
	{
		R.Add(TEXT("PIE ready"), [](FCineCtx& C) { return LBPie::WorldReady() && C.Frames >= 5; }, 90.f);
	}

	ALBPlayerController* LBController(UWorld* W)
	{
		return W ? Cast<ALBPlayerController>(W->GetFirstPlayerController()) : nullptr;
	}

	bool FadeIsClear(UWorld* W)
	{
		const APlayerController* PC = W ? W->GetFirstPlayerController() : nullptr;
		return !PC || !PC->PlayerCameraManager || !PC->PlayerCameraManager->bEnableFading || PC->PlayerCameraManager->FadeAmount <= 0.01f;
	}
}

using namespace LBCineTest;

// =====================================================================================================================
// Content-free
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBCineNoCheckpointDuringCinematicTest, "LastBell.Functional.Cine.NoCheckpointDuringCinematic", LB_CINEFUNC_FLAGS)
bool FLBCineNoCheckpointDuringCinematicTest::RunTest(const FString& Parameters)
{
	TSharedRef<FCineRunner> R = StartSession(this, GCineTestMap, /*bCineEnabled*/ true, /*Rate*/ 8.f);
	const TSharedRef<FCineState> S = R->S;
	FAutomationTestBase* Test = this;
	AddReady(*R);

	R->Add(TEXT("A cinematic plays: markers fire in order, the player is locked, nothing is saved"), [S, Test](FCineCtx& C)
	{
		ULBCinematicSubsystem* Sub = Cine(C.W);
		if (!Sub)
		{
			Test->AddError(TEXT("The cinematic subsystem is missing"));
			return true;
		}
		if (S->Phase == 0)
		{
			FLBCinematicDef Def;
			Def.Id = TEXT("Test");
			Def.InitialLock = ELBInputLock::Full;
			Def.Sequence = MakeSequence(*S, 6.0, {
				{ 0.0, TEXT("skip:1") }, { 1.0, TEXT("tag:State.Test.Door1Open") }, { 2.0, TEXT("lock:Look") },
				{ 3.0, TEXT("!lock:None") }, { 5.0, TEXT("!tag:State.Test.Door2Open") } });
			Sub->OverrideSettings(MakeSettings(*S, Def));
			Sub->Rearm();
			Sub->OnMarkerFired.AddLambda([S](const FString& Label) { S->Fired.Add(Label); });

			ALBCheckpoint* Checkpoint = C.W->SpawnActor<ALBCheckpoint>(FVector(0.0, 0.0, -90000.0), FRotator::ZeroRotator);
			S->Actors.Add(Checkpoint);
			if (!Test->TestNotNull(TEXT("A checkpoint was spawned"), Checkpoint) || !Test->TestTrue(TEXT("Play starts the cinematic"), Sub->Play(TEXT("Test"))))
			{
				return true;
			}
			Test->TestTrue(TEXT("IsPlaying"), Sub->IsPlaying());
			Test->TestEqual(TEXT("The active id"), Sub->GetActiveId(), FName(TEXT("Test")));
			Test->TestTrue(TEXT("The input is locked Full"), LBPie::Pawn()->GetInputLock() == ELBInputLock::Full);
			Test->TestTrue(TEXT("The HUD is hidden"), LBController(C.W) && LBController(C.W)->IsHUDHidden());
			Test->TestNotNull(TEXT("The overlay widget exists"), Sub->GetWidget());
			Test->TestFalse(TEXT("A checkpoint cannot save while it plays"), Checkpoint->CanSaveNow());
			const TCHAR* Reason = Checkpoint->GetSaveRefusalReason();
			Test->TestTrue(TEXT("...and says why"), Reason && FCString::Strstr(Reason, TEXT("cinematic")) != nullptr);
			Test->TestFalse(TEXT("A second Play is refused while one plays"), Sub->Play(TEXT("Test")));
			S->Phase = 1;
			return false;
		}
		if (Sub->IsPlaying())
		{
			return false;
		}
		const TArray<FString> Expected = { TEXT("skip:1"), TEXT("tag:State.Test.Door1Open"), TEXT("lock:Look"), TEXT("!lock:None"), TEXT("!tag:State.Test.Door2Open") };
		Test->TestTrue(TEXT("Every marker fired once, in order"), S->Fired == Expected);
		Test->TestTrue(TEXT("The tag marker added its tag"), LBPie::HasState(LBPie::Tag(TEXT("State.Test.Door1Open"))));
		Test->TestTrue(TEXT("The must tag marker added its tag"), LBPie::HasState(LBPie::Tag(TEXT("State.Test.Door2Open"))));
		Test->TestTrue(TEXT("The input is free again"), LBPie::Pawn()->GetInputLock() == ELBInputLock::None);
		Test->TestFalse(TEXT("The HUD is back"), LBController(C.W)->IsHUDHidden());
		Test->TestNull(TEXT("The overlay widget is gone"), Sub->GetWidget());
		Test->TestTrue(TEXT("No fade is left on the camera"), FadeIsClear(C.W));
		if (const ALBCheckpoint* Checkpoint = Cast<ALBCheckpoint>(S->Actors.IsValidIndex(0) ? S->Actors[0].Get() : nullptr))
		{
			Test->TestTrue(TEXT("The checkpoint can save again"), Checkpoint->CanSaveNow());
		}
		return true;
	}, 60.f);

	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBCineDisabledByCVarTest, "LastBell.Functional.Cine.DisabledByCVar", LB_CINEFUNC_FLAGS)
bool FLBCineDisabledByCVarTest::RunTest(const FString& Parameters)
{
	TSharedRef<FCineRunner> R = StartSession(this, GCineTestMap, /*bCineEnabled*/ true, /*Rate*/ 1.f);
	const TSharedRef<FCineState> S = R->S;
	FAutomationTestBase* Test = this;
	AddReady(*R);

	R->Add(TEXT("lb.Cine.Enabled 0 stops a running cinematic at once (no must markers) and nothing starts afterwards"), [S, Test](FCineCtx& C)
	{
		ULBCinematicSubsystem* Sub = Cine(C.W);
		if (!Sub)
		{
			Test->AddError(TEXT("The cinematic subsystem is missing"));
			return true;
		}
		if (S->Phase == 0)
		{
			FLBCinematicDef Def;
			Def.Id = TEXT("Test");
			Def.InitialLock = ELBInputLock::Full;
			Def.Sequence = MakeSequence(*S, 60.0, { { 59.0, TEXT("!tag:State.Test.Door2Open") } });
			Sub->OverrideSettings(MakeSettings(*S, Def));
			Sub->Rearm();
			if (!Test->TestTrue(TEXT("Play starts the cinematic"), Sub->Play(TEXT("Test"))))
			{
				return true;
			}
			S->T0 = C.Now;
			S->Phase = 1;
			return false;
		}
		if (S->Phase == 1)
		{
			if (C.Now - S->T0 < 0.3)
			{
				return false;
			}
			Test->TestTrue(TEXT("Still playing after 0.3 s"), Sub->IsPlaying());
			SetCVar(TEXT("lb.Cine.Enabled"), 0.f);
			S->Counter = 0;
			S->Phase = 2;
			return false;
		}
		if (S->Phase == 2)
		{
			if (Sub->IsPlaying() && ++S->Counter < 10)
			{
				return false;
			}
			Test->TestFalse(TEXT("The cinematic stopped"), Sub->IsPlaying());
			Test->TestTrue(TEXT("The input is free again"), LBPie::Pawn()->GetInputLock() == ELBInputLock::None);
			Test->TestFalse(TEXT("The HUD is back"), LBController(C.W)->IsHUDHidden());
			Test->TestFalse(TEXT("No must marker fired on the way out"), LBPie::HasState(LBPie::Tag(TEXT("State.Test.Door2Open"))));
			Test->TestTrue(TEXT("No fade is left on the camera"), FadeIsClear(C.W));
			Test->AddExpectedError(TEXT("lb.Cine.Enabled is 0"), EAutomationExpectedErrorFlags::Contains, 1);
			Test->TestFalse(TEXT("Play is refused while disabled"), Sub->Play(TEXT("Test")));
			Test->TestFalse(TEXT("No intro is pending"), Sub->IsStartPending());
			Test->TestFalse(TEXT("Nothing is playing"), Sub->IsPlaying());
			SetCVar(TEXT("lb.Cine.Enabled"), 1.f);
			return true;
		}
		return true;
	}, 60.f);

	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBCineMissingSequenceFailsSafeTest, "LastBell.Functional.Cine.MissingSequenceFailsSafe", LB_CINEFUNC_FLAGS)
bool FLBCineMissingSequenceFailsSafeTest::RunTest(const FString& Parameters)
{
	TSharedRef<FCineRunner> R = StartSession(this, GCineTestMap, /*bCineEnabled*/ true, /*Rate*/ 8.f);
	const TSharedRef<FCineState> S = R->S;
	FAutomationTestBase* Test = this;
	AddReady(*R);

	R->Add(TEXT("A definition whose sequence is missing: the must markers fire, the lock and the view come back"), [S, Test](FCineCtx& C)
	{
		ULBCinematicSubsystem* Sub = Cine(C.W);
		if (!Sub)
		{
			Test->AddError(TEXT("The cinematic subsystem is missing"));
			return true;
		}
		FLBCinematicDef Def;
		Def.Id = TEXT("Missing");
		Def.Sequence = TSoftObjectPtr<ULevelSequence>(FSoftObjectPath(TEXT("/Game/LastBell/Cinematics/LS_DoesNotExist.LS_DoesNotExist")));
		Def.InitialLock = ELBInputLock::Full;
		Def.bStartBlack = true;
		Def.bSkippableAtStart = true;
		Def.GrantOnStart.AddTag(LBPie::Tag(TEXT("State.Test.Door1Open")));
		Def.FailSafeMarkers = { TEXT("!tag:State.Test.Door2Open"), TEXT("!lock:None") };
		Sub->OverrideSettings(MakeSettings(*S, Def));
		Sub->Rearm();

		S->Counter = 0;
		Sub->OnCinematicFinished.AddLambda([S](FName) { ++S->Counter; });
		Test->AddExpectedError(TEXT("failed (the sequence did not load)"), EAutomationExpectedErrorFlags::Contains, 1);
		Sub->Play(TEXT("Missing"));

		Test->TestFalse(TEXT("It is not left playing"), Sub->IsPlaying());
		Test->TestEqual(TEXT("It finished (once)"), S->Counter, 1);
		Test->TestTrue(TEXT("GrantOnStart was added"), LBPie::HasState(LBPie::Tag(TEXT("State.Test.Door1Open"))));
		Test->TestTrue(TEXT("The fail-safe must marker fired"), LBPie::HasState(LBPie::Tag(TEXT("State.Test.Door2Open"))));
		Test->TestTrue(TEXT("The input lock is None"), LBPie::Pawn()->GetInputLock() == ELBInputLock::None);
		Test->TestFalse(TEXT("The HUD is shown"), LBController(C.W)->IsHUDHidden());
		Test->TestNull(TEXT("There is no overlay"), Sub->GetWidget());
		Test->TestTrue(TEXT("The screen is not left black"), FadeIsClear(C.W));
		return true;
	}, 30.f);

	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBCineBellSwingPiecesTest, "LastBell.Functional.Cine.BellSwingPieces", LB_CINEFUNC_FLAGS)
bool FLBCineBellSwingPiecesTest::RunTest(const FString& Parameters)
{
	TSharedRef<FCineRunner> R = StartSession(this, GCineTestMap, /*bCineEnabled*/ true, /*Rate*/ 1.f);
	const TSharedRef<FCineState> S = R->S;
	FAutomationTestBase* Test = this;
	AddReady(*R);

	R->Add(TEXT("Three movable stand-ins swing together on a great-bell strike and are back at rest after 20 s"), [S, Test](FCineCtx& C)
	{
		ULBCinematicSubsystem* Sub = Cine(C.W);
		ULBAudioSubsystem* Audio = C.W->GetSubsystem<ULBAudioSubsystem>();
		if (!Sub || !Audio)
		{
			Test->AddError(TEXT("The cinematic or the audio subsystem is missing"));
			return true;
		}
		auto Angle = [](const FQuat& A, const FQuat& B) { return static_cast<float>(FMath::RadiansToDegrees(A.AngularDistance(B))); };
		AStaticMeshActor* Bell = Cast<AStaticMeshActor>(S->Actors.IsValidIndex(0) ? S->Actors[0].Get() : nullptr);
		AStaticMeshActor* Head = Cast<AStaticMeshActor>(S->Actors.IsValidIndex(1) ? S->Actors[1].Get() : nullptr);
		AStaticMeshActor* Rope = Cast<AStaticMeshActor>(S->Actors.IsValidIndex(2) ? S->Actors[2].Get() : nullptr);

		if (S->Phase == 0)
		{
			// The F0 layout: the axle at the headstock, the bell's crown 20 cm below it, the rope's top on the east rim.
			auto Spawn = [&](const FVector& Location, const TCHAR* Tag)
			{
				AStaticMeshActor* Actor = C.W->SpawnActor<AStaticMeshActor>(Location, FRotator::ZeroRotator);
				if (Actor)
				{
					Actor->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
					Actor->Tags.Add(FName(Tag));
				}
				S->Actors.Add(Actor);
			};
			Spawn(FVector(12420.0, 2000.0, 2860.0), TEXT("LB_Cine_Bell"));
			Spawn(FVector(12420.0, 2000.0, 2880.0), TEXT("LB_Cine_BellHeadstock"));
			Spawn(FVector(12550.0, 1835.0, 2750.0), TEXT("LB_Cine_BellRope"));
			Bell = Cast<AStaticMeshActor>(S->Actors[0].Get());
			Head = Cast<AStaticMeshActor>(S->Actors[1].Get());
			Rope = Cast<AStaticMeshActor>(S->Actors[2].Get());
			if (!Bell || !Head || !Rope)
			{
				Test->AddError(TEXT("Could not spawn the stand-ins"));
				return true;
			}
			S->BellRest = Bell->GetActorQuat();
			S->HeadRest = Head->GetActorQuat();
			S->BellRestLoc = Bell->GetActorLocation();
			S->HeadRestLoc = Head->GetActorLocation();
			S->RopeRestLoc = Rope->GetActorLocation();

			ULBCinematicSettings* Settings = NewObject<ULBCinematicSettings>(GetTransientPackage());
			Settings->BellComponentName = TEXT("StaticMeshComponent0");
			S->Settings.Reset(Settings);
			Sub->OverrideSettings(Settings);
			Sub->Rearm();
			Test->TestTrue(TEXT("The bell piece was found"), Sub->HasBell());
			Test->TestTrue(TEXT("The headstock was found"), Sub->HasHeadstock());
			Test->TestTrue(TEXT("The rope was found"), Sub->HasRope());
			Test->TestFalse(TEXT("At rest"), Sub->IsBellSwinging());

			S->T0 = C.Now;
			Audio->OnGreatBellStrike.Broadcast(5, 1.f);
			Test->TestTrue(TEXT("A strike starts the swing"), Sub->IsBellSwinging());
			S->Phase = 1;
			return false;
		}
		if (!Bell || !Head || !Rope)
		{
			Test->AddError(TEXT("A stand-in is gone"));
			return true;
		}
		if (S->Phase == 1)
		{
			if (C.Now - S->T0 < 0.5)
			{
				return false;
			}
			const float BellAngle = Angle(Bell->GetActorQuat(), S->BellRest);
			const float HeadAngle = Angle(Head->GetActorQuat(), S->HeadRest);
			Test->TestTrue(FString::Printf(TEXT("The bell turned more than 2 degrees (%.2f)"), BellAngle), BellAngle > 2.f);
			Test->TestTrue(FString::Printf(TEXT("The headstock turned by the same angle (%.2f vs %.2f)"), HeadAngle, BellAngle), FMath::Abs(HeadAngle - BellAngle) <= 0.1f);
			const FVector RopeNow = Rope->GetActorLocation();
			Test->TestTrue(TEXT("The rope moved only in Z"), FMath::Abs(RopeNow.X - S->RopeRestLoc.X) <= 0.1 && FMath::Abs(RopeNow.Y - S->RopeRestLoc.Y) <= 0.1);
			Test->TestTrue(FString::Printf(TEXT("...and did move in Z (%.2f cm)"), RopeNow.Z - S->RopeRestLoc.Z), FMath::Abs(RopeNow.Z - S->RopeRestLoc.Z) > 1.0);
			Test->TestTrue(TEXT("The bell crown stays 20 cm from the axle"), FMath::IsNearlyEqual(FVector::Dist(Bell->GetActorLocation(), S->HeadRestLoc), 20.0, 0.05));

			// Many strikes in a row never swing past the maximum.
			for (int32 Index = 0; Index < 6; ++Index)
			{
				Audio->OnGreatBellStrike.Broadcast(5, 1.f);
			}
			Test->TestTrue(TEXT("The angle stays inside the maximum"), FMath::Abs(Sub->GetBellAngleDegrees()) <= S->Settings->BellSwingMaxDegrees + 0.01f);
			S->T0 = C.Now;
			S->Phase = 2;
			return false;
		}
		// 16 degrees decays below 0.05 degrees in ln(320) / 0.25 = 23 s.
		if (C.Now - S->T0 < 25.0)
		{
			return false;
		}
		Test->TestFalse(TEXT("The swing has stopped"), Sub->IsBellSwinging());
		Test->TestTrue(TEXT("The bell is back within 0.5 degrees"), Angle(Bell->GetActorQuat(), S->BellRest) <= 0.5f);
		Test->TestTrue(TEXT("The headstock is back within 0.5 degrees"), Angle(Head->GetActorQuat(), S->HeadRest) <= 0.5f);
		Test->TestTrue(TEXT("The bell is back within 0.5 cm"), FVector::Dist(Bell->GetActorLocation(), S->BellRestLoc) <= 0.5);
		Test->TestTrue(TEXT("The headstock is back within 0.5 cm"), FVector::Dist(Head->GetActorLocation(), S->HeadRestLoc) <= 0.5);
		Test->TestTrue(TEXT("The rope is back within 0.5 cm"), FVector::Dist(Rope->GetActorLocation(), S->RopeRestLoc) <= 0.5);
		return true;
	}, 90.f);

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// L_Monastery: need the content of P17-2 to P17-5b. EXPECTED TO FAIL until it exists.
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBCineMonasteryCinematicSetupTest, "LastBell.Functional.Cine.Monastery.CinematicSetup", LB_CINEFUNC_FLAGS)
bool FLBCineMonasteryCinematicSetupTest::RunTest(const FString& Parameters)
{
	if (!FPackageName::DoesPackageExist(GCineMonasteryMap))
	{
		AddWarning(TEXT("L_Monastery does not exist: the cinematic setup check is skipped"));
		return true;
	}
	TSharedRef<FCineRunner> R = StartSession(this, GCineMonasteryMap, /*bCineEnabled*/ false, /*Rate*/ 1.f);
	FAutomationTestBase* Test = this;
	AddReady(*R);

	R->Add(TEXT("L_Monastery: the tagged actors, DA_Cinematics, both sequences and their markers"), [Test](FCineCtx& C)
	{
		UWorld* W = C.W;
		for (const TCHAR* Tag : { TEXT("LB_Cine_FinaleMark"), TEXT("LB_Cine_StairTop"), TEXT("LB_Cine_Bell"), TEXT("LB_Cine_BellHeadstock"), TEXT("LB_Cine_BellRope") })
		{
			Test->TestEqual(FString::Printf(TEXT("Exactly one actor tagged %s (P17-5b places or tags it)"), Tag), CountTagged(W, Tag), 1);
		}
		for (const TCHAR* Tag : { TEXT("LB_Cine_Bell"), TEXT("LB_Cine_BellHeadstock"), TEXT("LB_Cine_BellRope") })
		{
			const AActor* Actor = FindTagged(W, Tag);
			const USceneComponent* Root = Actor ? Actor->GetRootComponent() : nullptr;
			Test->TestTrue(FString::Printf(TEXT("%s is Movable (P17-5b)"), Tag), Root && Root->Mobility == EComponentMobility::Movable);
		}
		int32 EndingTriggers = 0;
		for (TActorIterator<AActor> It(W); It; ++It)
		{
			EndingTriggers += It->GetClass()->GetName().Contains(TEXT("EndingTrigger")) ? 1 : 0;
		}
		Test->TestEqual(TEXT("EndingTrigger is gone from the level (P17-5b)"), EndingTriggers, 0);

		const ULBGameSettings* GameSettings = ULBGameSettings::Get();
		const ULBCinematicSettings* Settings = GameSettings && !GameSettings->CinematicSettings.IsNull() ? GameSettings->CinematicSettings.LoadSynchronous() : nullptr;
		if (!Test->TestNotNull(TEXT("DA_Cinematics loads through the project settings (P17-2)"), Settings))
		{
			return true;
		}

		struct FRequirement { const TCHAR* Id; TArray<FString> Must; bool bNeedsCameraCut; };
		const TArray<FRequirement> Requirements = {
			{ TEXT("Intro"), { TEXT("!tag:State.Event.Arrival"), TEXT("!lock:None") }, false },
			{ TEXT("Finale"), { TEXT("!end") }, true } };
		for (const FRequirement& Req : Requirements)
		{
			const FLBCinematicDef* Def = Settings->FindDef(FName(Req.Id));
			if (!Test->TestNotNull(*FString::Printf(TEXT("DA_Cinematics has the %s row"), Req.Id), Def))
			{
				continue;
			}
			const ULevelSequence* Sequence = Def->Sequence.IsNull() ? nullptr : Def->Sequence.LoadSynchronous();
			if (!Test->TestNotNull(*FString::Printf(TEXT("The %s sequence loads (P17-5a)"), Req.Id), Sequence))
			{
				continue;
			}
			const UMovieScene* MovieScene = Sequence->GetMovieScene();
			TSet<FString> Labels;
			for (const FMovieSceneMarkedFrame& Frame : MovieScene->GetMarkedFrames())
			{
				FLBCineMarker Marker;
				FString Error;
				const bool bParsed = LBCinematicLogic::ParseMarker(Frame.Label, Marker, Error);
				Test->TestTrue(FString::Printf(TEXT("%s: marker '%s' parses (%s)"), Req.Id, *Frame.Label, *Error), bParsed);
				Labels.Add(Frame.Label);
			}
			for (const FString& Must : Req.Must)
			{
				Test->TestTrue(FString::Printf(TEXT("%s has the must marker '%s'"), Req.Id, *Must), Labels.Contains(Must));
			}
			if (Req.bNeedsCameraCut)
			{
				Test->TestNotNull(*FString::Printf(TEXT("%s has a camera cut track"), Req.Id), MovieScene->GetCameraCutTrack());
			}
			for (const TPair<FName, FLBCineCard>& Pair : Settings->Cards)
			{
				Test->TestFalse(*FString::Printf(TEXT("Card %s has text"), *Pair.Key.ToString()), Pair.Value.Text.IsEmpty());
			}
		}
		return true;
	}, 60.f);

	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBCineIntroOnNewGameTest, "LastBell.Functional.Cine.IntroOnNewGame", LB_CINEFUNC_FLAGS)
bool FLBCineIntroOnNewGameTest::RunTest(const FString& Parameters)
{
	if (!FPackageName::DoesPackageExist(GCineMonasteryMap))
	{
		AddWarning(TEXT("L_Monastery does not exist: IntroOnNewGame is skipped"));
		return true;
	}
	TSharedRef<FCineRunner> R = StartSession(this, GCineMonasteryMap, /*bCineEnabled*/ true, /*Rate*/ 8.f);
	const TSharedRef<FCineState> S = R->S;
	FAutomationTestBase* Test = this;
	R->Add(TEXT("PIE ready"), [](FCineCtx& C) { return LBPie::WorldReady(); }, 90.f);

	R->Add(TEXT("New Game on L_Monastery plays the Intro: locked, HUD hidden"), [S, Test](FCineCtx& C)
	{
		ULBCinematicSubsystem* Sub = Cine(C.W);
		if (!Sub)
		{
			Test->AddError(TEXT("The cinematic subsystem is missing"));
			return true;
		}
		if (!Sub->IsPlaying())
		{
			if (C.Frames > 120)
			{
				Test->AddError(TEXT("The intro did not start (needs DA_Cinematics, LS_LB_Intro and the CinematicSettings entry)"));
				return true;
			}
			return false;
		}
		Test->TestEqual(TEXT("The Intro is playing"), Sub->GetActiveId(), FName(TEXT("Intro")));
		Test->TestTrue(TEXT("The player is locked Full"), LBPie::Pawn()->GetInputLock() == ELBInputLock::Full);
		Test->TestTrue(TEXT("The HUD is hidden"), LBController(C.W) && LBController(C.W)->IsHUDHidden());
		Sub->OnMarkerFired.AddLambda([S](const FString& Label)
		{
			if (Label == TEXT("!tag:State.Event.Arrival"))
			{
				++S->Counter;
			}
		});
		return true;
	}, 60.f);

	R->Add(TEXT("The Intro ends: Arrival set once, input and view back with the player"), [S, Test](FCineCtx& C)
	{
		ULBCinematicSubsystem* Sub = Cine(C.W);
		if (!Sub || Sub->IsPlaying())
		{
			return !Sub;
		}
		Test->TestTrue(TEXT("State.Event.Arrival is set"), LBPie::HasState(LBPie::Tag(TEXT("State.Event.Arrival"))));
		Test->TestEqual(TEXT("The Arrival marker fired once"), S->Counter, 1);
		Test->TestTrue(TEXT("The lock is None"), LBPie::Pawn()->GetInputLock() == ELBInputLock::None);
		Test->TestFalse(TEXT("The HUD is back"), LBController(C.W)->IsHUDHidden());
		Test->TestTrue(TEXT("The view is the player's own camera"), C.W->GetFirstPlayerController()->GetViewTarget() == LBPie::Pawn());
		Test->TestTrue(TEXT("No fade is left on the camera"), FadeIsClear(C.W));
		return true;
	}, 90.f);

	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBCineNoIntroOnContinueTest, "LastBell.Functional.Cine.NoIntroOnContinue", LB_CINEFUNC_FLAGS)
bool FLBCineNoIntroOnContinueTest::RunTest(const FString& Parameters)
{
	if (!FPackageName::DoesPackageExist(GCineMonasteryMap))
	{
		AddWarning(TEXT("L_Monastery does not exist: NoIntroOnContinue is skipped"));
		return true;
	}
	// Cinematics are off while the first world starts (so it gets no intro); they are switched on before Continue.
	TSharedRef<FCineRunner> R = StartSession(this, GCineMonasteryMap, /*bCineEnabled*/ false, /*Rate*/ 8.f);
	const TSharedRef<FCineState> S = R->S;
	FAutomationTestBase* Test = this;
	AddReady(*R);

	R->Add(TEXT("A save with Arrival, then Continue: no intro and no stage-1 toll"), [S, Test](FCineCtx& C)
	{
		ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(C.W);
		if (S->Phase == 0)
		{
			if (!Save)
			{
				Test->AddError(TEXT("No save subsystem"));
				return true;
			}
			ULBWorldStateSubsystem::Get(C.W)->AddState(LBPie::Tag(TEXT("State.Event.Arrival")));
			Test->TestTrue(TEXT("The checkpoint saved"), Save->SaveCheckpoint(TEXT("CP_Approach"), LBPie::Pawn()->GetActorTransform()));
			Test->TestTrue(TEXT("There is a valid save"), Save->HasValidSave());
			S->OldWorld = C.W;
			SetCVar(TEXT("lb.Cine.Enabled"), 1.f);
			Test->TestTrue(TEXT("Continue starts"), Save->ContinueGame());
			S->Phase = 1;
			return false;
		}
		if (LBPie::World() == S->OldWorld.Get() || !LBPie::WorldReady())
		{
			S->Counter = 0;
			return false;
		}
		if (++S->Counter < 40)
		{
			return false;
		}
		const ULBCinematicSubsystem* Sub = Cine(C.W);
		Test->TestNotNull(TEXT("The cinematic subsystem exists in the restored world"), Sub);
		Test->TestFalse(TEXT("No intro is pending"), Sub && Sub->IsStartPending());
		Test->TestFalse(TEXT("No intro is playing"), Sub && Sub->IsPlaying());
		Test->TestTrue(TEXT("The player is free"), LBPie::Pawn()->GetInputLock() == ELBInputLock::None);
		Test->TestTrue(TEXT("Arrival is still set"), LBPie::HasState(LBPie::Tag(TEXT("State.Event.Arrival"))));
		if (const ULBAudioSubsystem* Audio = C.W->GetSubsystem<ULBAudioSubsystem>())
		{
			Test->TestEqual(TEXT("No bell was requested (no stage-1 toll)"), Audio->CountRequests(LBAudioCue::Bell), 0);
		}
		return true;
	}, 120.f);

	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBCineIntroSkipTest, "LastBell.Functional.Cine.IntroSkip", LB_CINEFUNC_FLAGS)
bool FLBCineIntroSkipTest::RunTest(const FString& Parameters)
{
	if (!FPackageName::DoesPackageExist(GCineMonasteryMap))
	{
		AddWarning(TEXT("L_Monastery does not exist: IntroSkip is skipped"));
		return true;
	}
	TSharedRef<FCineRunner> R = StartSession(this, GCineMonasteryMap, /*bCineEnabled*/ true, /*Rate*/ 8.f);
	const TSharedRef<FCineState> S = R->S;
	FAutomationTestBase* Test = this;
	R->Add(TEXT("PIE ready"), [](FCineCtx& C) { return LBPie::WorldReady(); }, 90.f);

	R->Add(TEXT("Hold Interact for 1.0 s at 2 s of the intro: Arrival once, the player free, the fade back within 1 s"), [S, Test](FCineCtx& C)
	{
		ULBCinematicSubsystem* Sub = Cine(C.W);
		if (!Sub)
		{
			Test->AddError(TEXT("The cinematic subsystem is missing"));
			return true;
		}
		if (S->Phase == 0)
		{
			if (!Sub->IsPlaying())
			{
				if (C.Frames > 120)
				{
					Test->AddError(TEXT("The intro did not start (needs P17-2 to P17-5b)"));
					return true;
				}
				return false;
			}
			Sub->OnMarkerFired.AddLambda([S](const FString& Label)
			{
				if (Label == TEXT("!tag:State.Event.Arrival"))
				{
					++S->Counter;
				}
			});
			S->Phase = 1;
			return false;
		}
		if (S->Phase == 1)
		{
			if (!Sub->IsPlaying())
			{
				Test->AddError(TEXT("The intro ended before the skip"));
				return true;
			}
			if (Sub->GetSequenceSeconds() < 2.0)
			{
				return false;
			}
			Test->TestTrue(TEXT("The intro is skippable at 2 s"), Sub->IsSkippable());
			S->Number = static_cast<float>(Sub->GetSequenceSeconds());
			Sub->BeginSkipHold();
			S->Phase = 2;
			return false;
		}
		if (S->Phase == 2)
		{
			if (Sub->IsPlaying())
			{
				return false;
			}
			S->T0 = C.Now;
			S->Phase = 3;
			Test->TestTrue(FString::Printf(TEXT("It ended long before its natural end (held from %.1f s)"), S->Number), Sub->GetSequenceSeconds() < 20.0);
			Test->TestEqual(TEXT("Arrival fired once"), S->Counter, 1);
			Test->TestTrue(TEXT("State.Event.Arrival is set"), LBPie::HasState(LBPie::Tag(TEXT("State.Event.Arrival"))));
			Test->TestTrue(TEXT("The lock is None"), LBPie::Pawn()->GetInputLock() == ELBInputLock::None);
			Test->TestFalse(TEXT("The HUD is back"), LBController(C.W)->IsHUDHidden());
			return false;
		}
		if (FadeIsClear(C.W))
		{
			return true;
		}
		if (C.Now - S->T0 > 1.0)
		{
			Test->AddError(TEXT("The camera fade is not back to 0 within 1 s"));
			return true;
		}
		return false;
	}, 90.f);

	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBCineFinaleOnBellTest, "LastBell.Functional.Cine.FinaleOnBell", LB_CINEFUNC_FLAGS)
bool FLBCineFinaleOnBellTest::RunTest(const FString& Parameters)
{
	if (!FPackageName::DoesPackageExist(GCineMonasteryMap))
	{
		AddWarning(TEXT("L_Monastery does not exist: FinaleOnBell is skipped"));
		return true;
	}
	// Cinematics are off while the world starts (no intro) and on before the bell is rung.
	TSharedRef<FCineRunner> R = StartSession(this, GCineMonasteryMap, /*bCineEnabled*/ false, /*Rate*/ 8.f);
	const TSharedRef<FCineState> S = R->S;
	FAutomationTestBase* Test = this;
	AddReady(*R);

	R->Add(TEXT("State.Event.Finale: Stage 6, the figure takes over, Look then Full, the mark, the credits"), [S, Test](FCineCtx& C)
	{
		ULBCinematicSubsystem* Sub = Cine(C.W);
		ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(C.W);
		if (!Sub || !Save)
		{
			Test->AddError(TEXT("The cinematic or the save subsystem is missing"));
			return true;
		}
		const AActor* Mark = FindTagged(C.W, TEXT("LB_Cine_FinaleMark"));
		if (S->Phase == 0)
		{
			if (!Test->TestNotNull(TEXT("LB_Cine_FinaleMark exists (P17-5b)"), Mark))
			{
				return true;
			}
			const float HalfHeight = LBPie::Pawn()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
			S->MarkLoc = Mark->GetActorLocation() + FVector(0.0, 0.0, HalfHeight);
			Save->SaveCheckpoint(TEXT("CP_TowerTop"), LBPie::Pawn()->GetActorTransform());
			Test->TestTrue(TEXT("There is a save to be deleted"), Save->HasValidSave());
			SetCVar(TEXT("lb.Cine.Enabled"), 1.f);
			ULBWorldStateSubsystem::Get(C.W)->AddState(LBPie::Tag(TEXT("State.Event.Finale")));
			Test->TestTrue(TEXT("The Finale plays"), Sub->IsPlaying() && Sub->GetActiveId() == FName(TEXT("Finale")));
			Test->TestTrue(TEXT("State.Warden.Stage.6 is present (GrantOnStart)"), LBPie::HasState(LBPie::Tag(TEXT("State.Warden.Stage.6"))));
			Test->TestTrue(TEXT("The player is locked Full at the start"), LBPie::Pawn()->GetInputLock() == ELBInputLock::Full);
			S->Phase = 1;
			return false;
		}
		if (S->Phase == 1)
		{
			if (C.Frames == 5)
			{
				for (FConstControllerIterator It = C.W->GetControllerIterator(); It; ++It)
				{
					const ALBWardenController* Controller = Cast<ALBWardenController>(It->Get());
					if (const ULBWardenBrainComponent* Brain = Controller ? Controller->GetBrain() : nullptr)
					{
						Test->TestTrue(TEXT("The Warden brain is Dormant at stage 6"), Brain->GetState() == ELBWardenState::Dormant);
					}
				}
			}
			const ELBInputLock Lock = LBPie::Pawn()->GetInputLock();
			if (Lock == ELBInputLock::Look && !S->bFlagA)
			{
				S->bFlagA = true;
				const double Distance = FVector::Dist(LBPie::Pawn()->GetActorLocation(), S->MarkLoc);
				Test->TestTrue(FString::Printf(TEXT("The pawn is within 5 cm of the mark when the lock goes Look (%.1f cm)"), Distance), Distance <= 5.0);
			}
			if (Lock == ELBInputLock::Full && S->bFlagA)
			{
				S->bFlagB = true;
			}
			if (!Sub->IsCreditsRolling())
			{
				return false;
			}
			Test->TestTrue(TEXT("The lock went Look"), S->bFlagA);
			Test->TestTrue(TEXT("...and then Full"), S->bFlagB);
			Test->TestTrue(TEXT("The credits have lines"), Sub->GetWidget() && Sub->GetWidget()->GetCreditLineCountForTest() > 0);
			Test->TestTrue(TEXT("The credits can be skipped"), Sub->IsSkippable());
			S->OldWorld = C.W;
			Sub->RequestSkip();
			S->Phase = 2;
			return false;
		}
		if (LBPie::MapShortName() != GCineMainMenuMap)
		{
			return false;
		}
		const ULBSaveSubsystem* MenuSave = ULBSaveSubsystem::Get(LBPie::World());
		Test->TestTrue(TEXT("CompleteGame travelled to L_MainMenu"), MenuSave != nullptr);
		Test->TestFalse(TEXT("The save is gone"), MenuSave && MenuSave->HasValidSave());
		return true;
	}, 150.f);

	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBCineBellSwingsOnStrikeTest, "LastBell.Functional.Cine.BellSwingsOnStrike", LB_CINEFUNC_FLAGS)
bool FLBCineBellSwingsOnStrikeTest::RunTest(const FString& Parameters)
{
	if (!FPackageName::DoesPackageExist(GCineMonasteryMap))
	{
		AddWarning(TEXT("L_Monastery does not exist: BellSwingsOnStrike is skipped"));
		return true;
	}
	TSharedRef<FCineRunner> R = StartSession(this, GCineMonasteryMap, /*bCineEnabled*/ false, /*Rate*/ 1.f);
	const TSharedRef<FCineState> S = R->S;
	FAutomationTestBase* Test = this;
	AddReady(*R);

	R->Add(TEXT("PlayBell(5, 1) swings the real bell, headstock and rope; after 20 s they are back at rest"), [S, Test](FCineCtx& C)
	{
		ULBCinematicSubsystem* Sub = Cine(C.W);
		ULBAudioSubsystem* Audio = C.W->GetSubsystem<ULBAudioSubsystem>();
		AActor* Bell = FindTagged(C.W, TEXT("LB_Cine_Bell"));
		AActor* Head = FindTagged(C.W, TEXT("LB_Cine_BellHeadstock"));
		AActor* Rope = FindTagged(C.W, TEXT("LB_Cine_BellRope"));
		if (!Sub || !Audio || !Test->TestNotNull(TEXT("The bell is tagged LB_Cine_Bell (P17-5b)"), Bell) || !Test->TestNotNull(TEXT("The headstock is tagged (P17-5b)"), Head)
			|| !Test->TestNotNull(TEXT("The rope is tagged (P17-5b)"), Rope))
		{
			return true;
		}
		auto Angle = [](const FQuat& A, const FQuat& B) { return static_cast<float>(FMath::RadiansToDegrees(A.AngularDistance(B))); };
		if (S->Phase == 0)
		{
			if (!Test->TestTrue(TEXT("The audio director is active in L_Monastery"), Audio->IsActive()))
			{
				return true;
			}
			Sub->Rearm();
			S->BellRest = Bell->GetActorQuat();
			S->HeadRest = Head->GetActorQuat();
			S->BellRestLoc = Bell->GetActorLocation();
			S->HeadRestLoc = Head->GetActorLocation();
			S->RopeRestLoc = Rope->GetActorLocation();
			S->T0 = C.Now;
			Audio->PlayBell(5, 1);
			S->Phase = 1;
			return false;
		}
		if (S->Phase == 1)
		{
			if (C.Now - S->T0 < 0.5)
			{
				return false;
			}
			const float BellAngle = Angle(Bell->GetActorQuat(), S->BellRest);
			const float HeadAngle = Angle(Head->GetActorQuat(), S->HeadRest);
			Test->TestTrue(FString::Printf(TEXT("Within 0.5 s the bell turned more than 2 degrees (%.2f)"), BellAngle), BellAngle > 2.f);
			Test->TestTrue(FString::Printf(TEXT("The headstock turned by the same angle (%.2f vs %.2f)"), HeadAngle, BellAngle), FMath::Abs(HeadAngle - BellAngle) <= 0.1f);
			const FVector RopeNow = Rope->GetActorLocation();
			Test->TestTrue(TEXT("The rope moved in Z only"), FMath::Abs(RopeNow.X - S->RopeRestLoc.X) <= 0.1 && FMath::Abs(RopeNow.Y - S->RopeRestLoc.Y) <= 0.1);
			S->T0 = C.Now;
			S->Phase = 2;
			return false;
		}
		if (C.Now - S->T0 < 20.0)
		{
			return false;
		}
		Test->TestTrue(TEXT("After 20 s the bell is back within 0.5 degrees"), Angle(Bell->GetActorQuat(), S->BellRest) <= 0.5f);
		Test->TestTrue(TEXT("...and the headstock"), Angle(Head->GetActorQuat(), S->HeadRest) <= 0.5f);
		Test->TestTrue(TEXT("...and the bell within 0.5 cm"), FVector::Dist(Bell->GetActorLocation(), S->BellRestLoc) <= 0.5);
		Test->TestTrue(TEXT("...and the headstock within 0.5 cm"), FVector::Dist(Head->GetActorLocation(), S->HeadRestLoc) <= 0.5);
		Test->TestTrue(TEXT("...and the rope within 0.5 cm"), FVector::Dist(Rope->GetActorLocation(), S->RopeRestLoc) <= 0.5);
		return true;
	}, 90.f);

	Enqueue(R);
	return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
