#include "Tests/LBRouteBot.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Editor.h"
#include "Tests/AutomationEditorCommon.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "PlatformFeatures.h"
#include "SaveGameSystem.h"
#include "Misc/PackageName.h"
#include "Math/RandomStream.h"
#include "Character/LBCharacter.h"
#include "Components/LBInteractableComponent.h"
#include "Components/LBInteractorComponent.h"
#include "Puzzles/LBDialComponent.h"
#include "Puzzles/LBSequencePuzzleComponent.h"
#include "Save/LBSaveGame.h"
#include "Save/LBSaveSubsystem.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "Tests/LBTestSink.h"
#include "UObject/StrongObjectPtr.h"
#include "LBLog.h"

// Save hardening (P4-004): LastBell.Functional.Save.*
//
//   CorruptSave               garbage, truncated and wrong-version slot files are "no save", never a crash or a travel
//   QuitMidPuzzle_Continue    two candles lit, checkpoint, quit to the menu, Continue: the partial puzzle is restored and solvable
//   DeathMidPuzzle            lever A solved and saved, lever B moved afterwards (unsaved), death: A kept, B back to its saved position
//   RevisitSolved             candles solved and the altar used, saved, reloaded: everything stays solved and inert
//   NewGameClears             progress, then New Game: nothing survives
//
// The Monastery tests drive the real L_Monastery puzzle actors. Presses go through the real interactor (TryInteract) from the
// route bot's approach points; the bot itself (goal tags, no checkpoints) performs the steps that are not the subject of a test.
// Every test deletes the save slot at its start and at its end.

namespace LBSaveT
{
	const TCHAR* GMicroMap = TEXT("/Game/LastBell/Maps/L_Test_MicroSlice");
	const TCHAR* GMonasteryMap = TEXT("/Game/LastBell/Maps/L_Monastery");
	const TCHAR* GMenuMap = TEXT("/Game/LastBell/Maps/L_MainMenu");
	const FName GSaveCheckpoint(TEXT("CP_SaveTest"));

	void Note(const FString& Text) { UE_LOG(LogLB, Display, TEXT("[SaveTests] %s"), *Text); }

	struct FCtx
	{
		UWorld* W = nullptr;
		ALBCharacter* Pawn = nullptr;
		int32 Frames = 0;
		bool bFirst = false;
	};

	/** Runs steps (each returns true when done) one per frame with per-step wall timeouts; never hangs; always tears PIE down and clears the slot. */
	class FRunner : public IAutomationLatentCommand
	{
	public:
		using FStepFn = TFunction<bool(FCtx&)>;

		explicit FRunner(FAutomationTestBase* InTest) : Test(InTest) {}

		void Add(const FString& Name, FStepFn Fn, float WallTimeout = 30.f) { Steps.Add({ Name, WallTimeout, MoveTemp(Fn) }); }

		void Abort(const FString& Why)
		{
			Test->AddError(Why);
			bAbort = true;
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

			FStep& Step = Steps[StepIndex];
			if (!bEntered)
			{
				bEntered = true;
				Frames = 0;
				WallStart = FPlatformTime::Seconds();
				ErrorsAtStart = ErrCount();
				Note(FString::Printf(TEXT("STEP %d begin: %s"), StepIndex + 1, *Step.Name));
			}

			FCtx Ctx;
			Ctx.W = LBPie::World();
			Ctx.Pawn = LBPie::Pawn();
			Ctx.Frames = Frames;
			Ctx.bFirst = (Frames == 0);
			++Frames;

			const bool bDone = Step.Fn(Ctx);
			const bool bTimedOut = !bDone && (FPlatformTime::Seconds() - WallStart) > Step.Timeout;
			if (bTimedOut)
			{
				Test->AddError(FString::Printf(TEXT("Step '%s' timed out after %.0fs (map %s)"), *Step.Name, Step.Timeout, *LBPie::MapShortName()));
			}
			if (bDone || bTimedOut)
			{
				Note(FString::Printf(TEXT("STEP %d %s: %s"), StepIndex + 1, ErrCount() == ErrorsAtStart ? TEXT("PASS") : TEXT("FAIL"), *Step.Name));
				if (bTimedOut)
				{
					bAbort = true;
				}
				++StepIndex;
				bEntered = false;
			}
			return false;
		}

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
		TArray<FStep> Steps;
		int32 StepIndex = 0;
		int32 Frames = 0;
		bool bEntered = false;
		bool bAbort = false;
		bool bTearingDown = false;
		double WallStart = 0.0;
		double TeardownStart = 0.0;
		int32 ErrorsAtStart = 0;
	};

	using FRunnerPtr = TSharedRef<FRunner>;

	FRunnerPtr StartSession(FAutomationTestBase* Test, const TCHAR* Map)
	{
		LBPie::ClearSlot();
		FAutomationEditorCommonUtils::LoadMap(Map);
		FRequestPlaySessionParams PlayParams;
		PlayParams.WorldType = EPlaySessionWorldType::PlayInEditor;
		GEditor->RequestPlaySession(PlayParams);
		return MakeShared<FRunner>(Test);
	}

	void Enqueue(const FRunnerPtr& Runner) { FAutomationTestFramework::Get().EnqueueLatentCommand(Runner); }

	// ---- slot file helpers --------------------------------------------------------------------------------------------

	ISaveGameSystem* SaveSys() { return IPlatformFeaturesModule::Get().GetSaveGameSystem(); }
	bool SlotExists() { return UGameplayStatics::DoesSaveGameExist(ULBSaveSubsystem::SlotName, ULBSaveSubsystem::UserIndex); }

	bool WriteRaw(const TArray<uint8>& Bytes)
	{
		ISaveGameSystem* Sys = SaveSys();
		return Sys && Sys->SaveGame(false, *ULBSaveSubsystem::SlotName, ULBSaveSubsystem::UserIndex, Bytes);
	}

	bool ReadRaw(TArray<uint8>& Out)
	{
		ISaveGameSystem* Sys = SaveSys();
		return Sys && Sys->LoadGame(false, *ULBSaveSubsystem::SlotName, ULBSaveSubsystem::UserIndex, Out);
	}

	/** The slot as the game would read it (null when absent or unreadable). */
	const ULBSaveGame* ReadDiskSave()
	{
		return SlotExists() ? Cast<ULBSaveGame>(UGameplayStatics::LoadGameFromSlot(ULBSaveSubsystem::SlotName, ULBSaveSubsystem::UserIndex)) : nullptr;
	}

	bool SameTags(const FGameplayTagContainer& A, const FGameplayTagContainer& B) { return A.Num() == B.Num() && A.HasAllExact(B); }

	// ---- shared state of one test -------------------------------------------------------------------------------------

	struct FState
	{
		TStrongObjectPtr<ULBTestSink> Sink;
		TWeakObjectPtr<UWorld> OldWorld;
		int32 Settle = 0;
		bool bIssued = false;
		FTransform SavedTransform;

		// tags
		FGameplayTag Candle[4];
		FGameplayTag CandlesSolved;
		FGameplayTag Ritual1;
		FGameplayTag Crank;
		FGameplayTag Dial[3][3]; // [lever A/B/C][position]

		// placed actors (re-resolved after every world change)
		TWeakObjectPtr<AActor> CandleActor[4];
		TWeakObjectPtr<AActor> SeqActor;
		TWeakObjectPtr<AActor> DialActor[3];
		TWeakObjectPtr<AActor> Winch;
		TWeakObjectPtr<AActor> Altar;

		ULBSequencePuzzleComponent* Seq() const { return SeqActor.IsValid() ? SeqActor->FindComponentByClass<ULBSequencePuzzleComponent>() : nullptr; }
		ULBDialComponent* DialComp(int32 L) const { return DialActor[L].IsValid() ? DialActor[L]->FindComponentByClass<ULBDialComponent>() : nullptr; }
		static ULBInteractableComponent* Inter(const AActor* A) { return A ? A->FindComponentByClass<ULBInteractableComponent>() : nullptr; }
		ULBInteractableComponent* CandleInter(int32 I) const { return Inter(CandleActor[I].Get()); }
	};

	bool HasState(const FGameplayTag& Tag) { return LBPie::HasState(Tag); }

	/** Looks up every tag the tests use; they exist in the ini, so this works before any world does. */
	bool ResolveTags(FAutomationTestBase* Test, FState& S)
	{
		bool bOk = true;
		auto Need = [&](const FString& Name, FGameplayTag& Out)
		{
			Out = LBPie::Tag(*Name);
			bOk &= Test->TestTrue(FString::Printf(TEXT("Tag %s exists in the ini"), *Name), Out.IsValid());
		};
		for (int32 i = 0; i < 4; ++i)
		{
			Need(FString::Printf(TEXT("State.Chapel.Candle.%d"), i + 1), S.Candle[i]);
		}
		Need(TEXT("State.Chapel.CandlesSolved"), S.CandlesSolved);
		Need(TEXT("State.Ritual.1"), S.Ritual1);
		Need(TEXT("State.Item.Crank"), S.Crank);
		for (int32 L = 0; L < 3; ++L)
		{
			for (int32 P = 0; P < 3; ++P)
			{
				Need(FString::Printf(TEXT("State.Crypt.Dial.%c.%d"), TEXT('A') + L, P), S.Dial[L][P]);
			}
		}
		return bOk;
	}

	/** Finds the placed puzzle actors by what they do (granted/required tags), not by name. */
	bool Resolve(FAutomationTestBase* Test, UWorld* W, FState& S)
	{
		bool bOk = true;
		for (int32 i = 0; i < 4; ++i) { S.CandleActor[i].Reset(); }
		for (int32 L = 0; L < 3; ++L) { S.DialActor[L].Reset(); }
		S.SeqActor.Reset();
		S.Winch.Reset();
		S.Altar.Reset();

		for (TActorIterator<AActor> It(W); It; ++It)
		{
			AActor* A = *It;
			if (const ULBSequencePuzzleComponent* Seq = A->FindComponentByClass<ULBSequencePuzzleComponent>())
			{
				if (Seq->SolvedTags.HasTagExact(S.CandlesSolved))
				{
					S.SeqActor = A;
				}
			}
			if (const ULBDialComponent* Dial = A->FindComponentByClass<ULBDialComponent>())
			{
				for (int32 L = 0; L < 3; ++L)
				{
					if (Dial->PositionTags.Contains(S.Dial[L][0]))
					{
						S.DialActor[L] = A;
					}
				}
			}
			if (const ULBInteractableComponent* Comp = A->FindComponentByClass<ULBInteractableComponent>())
			{
				for (int32 i = 0; i < 4; ++i)
				{
					if (Comp->GrantedStateTags.HasTagExact(S.Candle[i]))
					{
						S.CandleActor[i] = A;
					}
				}
				if (Comp->RequiredStateTags.HasTagExact(S.Crank) && Comp->RequiredStateTags.HasTagExact(S.Dial[0][2]))
				{
					S.Winch = A;
				}
				if (Comp->GrantedStateTags.HasTagExact(S.Ritual1))
				{
					S.Altar = A;
				}
			}
		}

		for (int32 i = 0; i < 4; ++i)
		{
			bOk &= Test->TestTrue(FString::Printf(TEXT("Candle %d actor found"), i + 1), S.CandleActor[i].IsValid());
		}
		bOk &= Test->TestTrue(TEXT("Candle sequence puzzle found"), S.Seq() != nullptr);
		for (int32 L = 0; L < 3; ++L)
		{
			bOk &= Test->TestTrue(FString::Printf(TEXT("Crypt lever %c found"), TEXT('A') + L), S.DialComp(L) != nullptr);
		}
		bOk &= Test->TestTrue(TEXT("Winch (crank + dial combination) found"), S.Winch.IsValid());
		bOk &= Test->TestTrue(TEXT("Altar mechanism (grants Ritual.1) found"), S.Altar.IsValid());
		return bOk;
	}

	/** Binds the sink to the candle puzzle and every interactable we watch (call once per world). */
	void BindSink(FState& S)
	{
		S.Sink.Reset(NewObject<ULBTestSink>(GetTransientPackage()));
		if (ULBSequencePuzzleComponent* Seq = S.Seq())
		{
			Seq->OnStepAccepted.AddDynamic(S.Sink.Get(), &ULBTestSink::HandleStepAccepted);
			Seq->OnPuzzleFailed.AddDynamic(S.Sink.Get(), &ULBTestSink::HandlePuzzleFailed);
			Seq->OnPuzzleSolved.AddDynamic(S.Sink.Get(), &ULBTestSink::HandlePuzzleSolved);
		}
	}

	void CheckCandle(FAutomationTestBase* Test, FState& S, int32 I, bool bLit, ALBCharacter* Pawn, const TCHAR* When)
	{
		Test->TestEqual(FString::Printf(TEXT("%s: Candle.%d tag %s"), When, I + 1, bLit ? TEXT("present") : TEXT("absent")), HasState(S.Candle[I]), bLit);
		ULBInteractableComponent* Comp = S.CandleInter(I);
		Test->TestTrue(FString::Printf(TEXT("%s: Candle.%d has an interactable"), When, I + 1), Comp != nullptr);
		if (Comp)
		{
			Test->TestEqual(FString::Printf(TEXT("%s: Candle.%d %s"), When, I + 1, bLit ? TEXT("not interactable") : TEXT("interactable")),
				Comp->CanInteract(Pawn), !bLit);
		}
	}

	int32 DialIndex(FState& S, int32 L) { return S.DialComp(L) ? S.DialComp(L)->GetCurrentIndex() : -2; }

	// ---- steps --------------------------------------------------------------------------------------------------------

	/** True once a fresh gameplay world of Map is up and has settled for a few frames. */
	bool GameWorldReady(FCtx& C, FState& S, const TCHAR* Map)
	{
		if (C.W && C.W != S.OldWorld.Get() && LBPie::MapShortName() == Map && LBPie::WorldReady())
		{
			return ++S.Settle >= 12;
		}
		S.Settle = 0;
		return false;
	}

	bool MenuWorldReady(FCtx& C, FState& S)
	{
		if (C.W && C.W != S.OldWorld.Get() && LBPie::MapShortName() == GMenuMap && C.W->HasBegunPlay())
		{
			return ++S.Settle >= 10;
		}
		S.Settle = 0;
		return false;
	}

	void AddReadyStep(FRunner& R, const TSharedRef<FState>& S, FAutomationTestBase* Test)
	{
		R.Add(TEXT("PIE ready, resolve puzzle actors"), [S, Test, &R](FCtx& C)
		{
			if (!LBPie::WorldReady() || C.Frames < 8)
			{
				return false;
			}
			if (!Resolve(Test, C.W, *S))
			{
				R.Abort(TEXT("Setup failed: puzzle actors or tags missing"));
				return true;
			}
			BindSink(*S);
			Test->TestFalse(TEXT("Fresh game: no save slot"), SlotExists());
			Test->TestFalse(TEXT("Fresh game: candles not solved"), HasState(S->CandlesSolved));
			return true;
		}, 90.f);
	}

	/** Runs the route bot toward the goal tags (no checkpoint stops, so it never saves behind the test's back). */
	void AddBot(FRunner& R, FAutomationTestBase* Test, const FString& Name, TArray<FGameplayTag> Goal, float Timeout = 60.f)
	{
		TSharedRef<TSharedPtr<FLBRouteBot>> Bot = MakeShared<TSharedPtr<FLBRouteBot>>();
		FRunner* Runner = &R;
		R.Add(Name, [Bot, Goal, Test, Runner](FCtx&)
		{
			if (!Bot->IsValid())
			{
				FLBRouteBot::FConfig Config;
				Config.GoalTags = Goal;
				Config.CheckpointRadius = 0.f;
				Config.ObjectiveTimeout = 45.f;
				*Bot = MakeShared<FLBRouteBot>(Test, Config);
			}
			switch ((*Bot)->Tick())
			{
			case FLBRouteBot::EStatus::Failed:
				Runner->Abort(TEXT("Route bot failed (see the [RouteBot] error above)"));
				return true;
			case FLBRouteBot::EStatus::Done:
				return true;
			default:
				return false;
			}
		}, Timeout);
	}

	/** Stands at the first usable route-bot approach point from FromAttempt on and points the camera at the actor. OutAttempt is the point used. */
	bool StandAndAim(FAutomationTestBase* Test, const AActor* Target, int32 FromAttempt, int32& OutAttempt, FString& OutWhere)
	{
		FLBRouteBot Probe(Test, FLBRouteBot::FConfig());
		FVector Origin, Extent;
		Target->GetActorBounds(true, Origin, Extent);
		for (int32 Attempt = FromAttempt; Attempt < 4; ++Attempt)
		{
			FVector Loc;
			if (Probe.FindApproachPoint(Target, Attempt, Loc))
			{
				LBPie::Teleport(Loc, FRotator::ZeroRotator);
				if (const ALBCharacter* P = LBPie::Pawn())
				{
					if (AController* Ctl = P->GetController())
					{
						Ctl->SetControlRotation((Origin - (P->GetActorLocation() + FVector(0, 0, 64.f))).Rotation());
					}
				}
				OutAttempt = Attempt;
				OutWhere = FString::Printf(TEXT("approach %d at %s"), Attempt, *Loc.ToString());
				return true;
			}
		}
		return false;
	}

	struct FPressProgress
	{
		int32 Attempt = 0;
		int32 FramesSinceAim = -1;
	};

	/**
	 * Stand where the route bot would stand, aim, let the camera and focus catch up and press once through the real interactor. If the
	 * interactor does not focus the target from one approach point (another prop in the way), the next approach point is tried. After()
	 * runs right after the press, with whether the target was focused.
	 */
	void AddPress(FRunner& R, const TSharedRef<FState>& S, FAutomationTestBase* Test, const FString& Label,
		TFunction<AActor*(FState&)> GetTarget, TFunction<void(FCtx&, bool bFocusedTarget)> After = nullptr)
	{
		TSharedRef<FPressProgress> Progress = MakeShared<FPressProgress>();
		R.Add(Label + TEXT(": stand, aim, press"), [S, Test, GetTarget, Label, After, Progress](FCtx& C)
		{
			AActor* Target = GetTarget(*S);
			if (!C.Pawn || !Test->TestNotNull(*FString::Printf(TEXT("%s: target exists"), *Label), Target))
			{
				return true;
			}
			if (Progress->FramesSinceAim < 0)
			{
				FString Where;
				if (!StandAndAim(Test, Target, Progress->Attempt, Progress->Attempt, Where))
				{
					Test->AddError(FString::Printf(TEXT("%s: no usable approach point gives the interactor a view of the target"), *Label));
					return true;
				}
				Note(FString::Printf(TEXT("%s: %s"), *Label, *Where));
				Progress->FramesSinceAim = 0;
				return false;
			}
			if (++Progress->FramesSinceAim < 12)
			{
				return false;
			}
			const ULBInteractableComponent* Seen = C.Pawn->GetInteractor()->GetFocusedComponent();
			if ((!Seen || Seen->GetOwner() != Target) && Progress->Attempt < 3)
			{
				Note(FString::Printf(TEXT("%s: focus=%s from approach %d, trying the next one"), *Label, *GetNameSafe(Seen ? Seen->GetOwner() : nullptr), Progress->Attempt));
				++Progress->Attempt;
				Progress->FramesSinceAim = -1;
				return false;
			}
			C.Pawn->GetInteractor()->TryInteract();
			const ULBInteractableComponent* Focus = C.Pawn->GetInteractor()->GetFocusedComponent();
			const bool bFocused = Focus && Focus->GetOwner() == Target;
			Test->TestTrue(FString::Printf(TEXT("%s: the interactor focuses the target (focus=%s)"), *Label, *GetNameSafe(Focus ? Focus->GetOwner() : nullptr)), bFocused);
			if (After)
			{
				After(C, bFocused);
			}
			return true;
		}, 30.f);
	}

	void AddSettle(FRunner& R, const FString& Name, int32 Frames)
	{
		R.Add(Name, [Frames](FCtx& C) { return C.Frames >= Frames; });
	}

	void AddCheck(FRunner& R, const FString& Name, TFunction<void(FCtx&)> Fn)
	{
		R.Add(Name, [Fn](FCtx& C)
		{
			Fn(C);
			return true;
		});
	}

	/** SaveCheckpoint with the pawn's transform; asserts the slot then holds a valid, readable save. */
	void SaveNow(FAutomationTestBase* Test, FCtx& C, FState& S)
	{
		ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(C.W);
		if (!Test->TestNotNull(TEXT("Save subsystem"), Save) || !Test->TestNotNull(TEXT("Pawn"), C.Pawn))
		{
			return;
		}
		S.SavedTransform = C.Pawn->GetActorTransform();
		Test->TestTrue(TEXT("SaveCheckpoint"), Save->SaveCheckpoint(GSaveCheckpoint, S.SavedTransform));
		Test->TestTrue(TEXT("HasValidSave after saving"), Save->HasValidSave());
	}

	void CheckDistToSaved(FAutomationTestBase* Test, FCtx& C, FState& S)
	{
		if (Test->TestNotNull(TEXT("Pawn after the reload"), C.Pawn))
		{
			const double Dist = FVector::Dist(C.Pawn->GetActorLocation(), S.SavedTransform.GetLocation());
			Test->TestTrue(FString::Printf(TEXT("Pawn respawned at the saved checkpoint transform (%.1f cm away)"), Dist), Dist <= 150.0);
		}
	}
}

using namespace LBSaveT;

// =====================================================================================================================
// 1. Corrupt save files
// =====================================================================================================================
namespace LBSaveT
{
	/** Every flavour of broken slot must read as "no save" without touching the running game. */
	void CheckRejected(FAutomationTestBase* Test, FCtx& C, const FString& Case)
	{
		ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(C.W);
		if (!Test->TestNotNull(TEXT("Save subsystem"), Save))
		{
			return;
		}
		const FGameplayTagContainer StateBefore = ULBWorldStateSubsystem::Get(C.W)->GetStateRef();
		Test->TestTrue(FString::Printf(TEXT("[%s] the slot file exists (so the loader really sees the broken bytes)"), *Case), SlotExists());
		Test->TestFalse(FString::Printf(TEXT("[%s] HasValidSave is false"), *Case), Save->HasValidSave());
		Test->TestFalse(FString::Printf(TEXT("[%s] ContinueGame returns false"), *Case), Save->ContinueGame());
		Test->TestFalse(FString::Printf(TEXT("[%s] LoadLastCheckpoint returns false"), *Case), Save->LoadLastCheckpoint());
		Test->TestFalse(FString::Printf(TEXT("[%s] no travel started"), *Case), Save->IsTravelPending());
		Test->TestFalse(FString::Printf(TEXT("[%s] no restore pending"), *Case), Save->HasPendingRestore());
		Test->TestTrue(FString::Printf(TEXT("[%s] still in the same world"), *Case), LBPie::World() == C.W);
		Test->TestTrue(FString::Printf(TEXT("[%s] world state untouched"), *Case), SameTags(ULBWorldStateSubsystem::Get(C.W)->GetStateRef(), StateBefore));
	}

	TArray<uint8> Truncate(const TArray<uint8>& Bytes, double Fraction)
	{
		TArray<uint8> Out;
		Out.Append(Bytes.GetData(), FMath::Clamp(static_cast<int32>(Bytes.Num() * Fraction), 0, Bytes.Num()));
		return Out;
	}

	TArray<uint8> GarbageBytes(int32 Count)
	{
		FRandomStream Rand(1234);
		TArray<uint8> Out;
		for (int32 i = 0; i < Count; ++i)
		{
			Out.Add(static_cast<uint8>(Rand.RandRange(0, 255)));
		}
		return Out;
	}

	/** A structurally perfect save of the given version. */
	TArray<uint8> SaveBytesWithVersion(int32 Version)
	{
		ULBSaveGame* Save = NewObject<ULBSaveGame>(GetTransientPackage());
		Save->SaveVersion = Version;
		Save->CheckpointId = TEXT("CP_Versioned");
		Save->MapName = GMonasteryMap;
		Save->WorldState.AddTag(LBPie::Tag(TEXT("State.Chapel.Candle.1")));
		TArray<uint8> Bytes;
		ULBSaveSubsystem::EncodeSave(Save, Bytes);
		return Bytes;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBSaveCorruptTest, "LastBell.Functional.Save.CorruptSave",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBSaveCorruptTest::RunTest(const FString& Parameters)
{
	// The loader logs a warning for each rejected slot (and nothing at error level, which would fail the test).
	AddExpectedMessagePlain(TEXT("treating as no save"), ELogVerbosity::Warning, EAutomationExpectedMessageFlags::Contains, 0);

	FRunnerPtr R = StartSession(this, GMicroMap);
	TSharedRef<FState> S = MakeShared<FState>();
	TSharedRef<TArray<uint8>> Real = MakeShared<TArray<uint8>>();
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, write a real save"), [S, Real, Test, &R = *R](FCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 8)
		{
			return false;
		}
		ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(C.W);
		ULBWorldStateSubsystem* WS = ULBWorldStateSubsystem::Get(C.W);
		if (!Test->TestNotNull(TEXT("Save subsystem"), Save) || !Test->TestNotNull(TEXT("World state subsystem"), WS))
		{
			R.Abort(TEXT("Setup failed"));
			return true;
		}
		// A substantial world state, so a truncated file loses real content.
		FGameplayTagContainer Tags;
		for (const TCHAR* Name : { TEXT("State.Chapel.Candle.1"), TEXT("State.Chapel.Candle.2"), TEXT("State.Chapel.Candle.3"), TEXT("State.Crypt.Dial.A.2"),
			TEXT("State.Crypt.Dial.B.1"), TEXT("State.Crypt.Dial.C.0"), TEXT("State.Ritual.1"), TEXT("State.Item.Crank"), TEXT("State.Door.ChapelMain.Open") })
		{
			if (const FGameplayTag Tag = LBPie::Tag(Name); Tag.IsValid())
			{
				Tags.AddTag(Tag);
			}
		}
		WS->AddStates(Tags);
		Test->TestTrue(TEXT("SaveCheckpoint (control: a real save)"), Save->SaveCheckpoint(GSaveCheckpoint, C.Pawn->GetActorTransform()));
		Test->TestTrue(TEXT("Control: the real save is valid"), Save->HasValidSave());
		Test->TestTrue(TEXT("Read the slot bytes"), ReadRaw(*Real));
		Test->TestTrue(FString::Printf(TEXT("The real save has some size (%d bytes)"), Real->Num()), Real->Num() > 200);
		return true;
	}, 90.f);

	// Rejected without leaving the world (no travel, so many shapes can be checked quickly).
	R->Add(TEXT("Broken files that are not travelled over"), [S, Real, Test](FCtx& C)
	{
		struct FCase { FString Name; TArray<uint8> Bytes; };
		TArray<FCase> Cases;
		Cases.Add({ TEXT("empty file"), TArray<uint8>() });
		Cases.Add({ TEXT("one byte"), TArray<uint8>({ 0x42 }) });
		Cases.Add({ TEXT("garbage 4 KiB"), GarbageBytes(4096) });
		for (const double Fraction : { 0.9, 0.75, 0.25, 0.1, 0.03 })
		{
			Cases.Add({ FString::Printf(TEXT("truncated to %.0f%%"), Fraction * 100.0), Truncate(*Real, Fraction) });
		}
		Cases.Add({ TEXT("last byte missing"), Truncate(*Real, 1.0 - 1.0 / FMath::Max(Real->Num(), 1)) });
		{
			TArray<uint8> Smashed = *Real; // header intact, the body replaced by 0xFF
			for (int32 i = Smashed.Num() / 3; i < Smashed.Num(); ++i)
			{
				Smashed[i] = 0xFF;
			}
			Cases.Add({ TEXT("body overwritten with 0xFF"), MoveTemp(Smashed) });
		}
		{
			TArray<uint8> Zeroed = *Real; // header intact, the body zeroed
			for (int32 i = Zeroed.Num() / 3; i < Zeroed.Num(); ++i)
			{
				Zeroed[i] = 0;
			}
			Cases.Add({ TEXT("body zeroed"), MoveTemp(Zeroed) });
		}

		for (const FCase& Case : Cases)
		{
			Note(FString::Printf(TEXT("case: %s (%d bytes)"), *Case.Name, Case.Bytes.Num()));
			if (!Test->TestTrue(FString::Printf(TEXT("[%s] wrote the file"), *Case.Name), WriteRaw(Case.Bytes)))
			{
				continue;
			}
			CheckRejected(Test, C, Case.Name);
		}
		// Control: the untouched bytes are still a valid save.
		Test->TestTrue(TEXT("Control: writing the real bytes back gives a valid save"), WriteRaw(*Real) && ULBSaveSubsystem::Get(C.W)->HasValidSave());
		return true;
	});

	// The three required shapes, each followed by a real StartNewGame (travels; it must succeed and remove the broken file).
	struct FTravelCase { FString Name; TFunction<TArray<uint8>(const TArray<uint8>&)> Make; };
	TArray<FTravelCase> TravelCases;
	TravelCases.Add({ TEXT("garbage bytes"), [](const TArray<uint8>&) { return GarbageBytes(777); } });
	TravelCases.Add({ TEXT("truncated: first half of a real save"), [](const TArray<uint8>& Bytes) { return Truncate(Bytes, 0.5); } });
	TravelCases.Add({ TEXT("valid save, wrong SaveVersion (newer)"), [](const TArray<uint8>&) { return SaveBytesWithVersion(ULBSaveGame::CurrentVersion + 1); } });
	TravelCases.Add({ TEXT("valid save, wrong SaveVersion (older)"), [](const TArray<uint8>&) { return SaveBytesWithVersion(ULBSaveGame::CurrentVersion - 1); } });

	for (const FTravelCase& Case : TravelCases)
	{
		R->Add(FString::Printf(TEXT("%s: rejected, then StartNewGame works"), *Case.Name), [S, Real, Test, Case](FCtx& C)
		{
			if (C.bFirst)
			{
				if (!C.W || !Test->TestTrue(TEXT("wrote the broken file"), WriteRaw(Case.Make(*Real))))
				{
					return true;
				}
				CheckRejected(Test, C, Case.Name);
				ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(C.W);
				S->OldWorld = C.W;
				S->Settle = 0;
				Save->StartNewGame();
				Test->TestTrue(FString::Printf(TEXT("[%s] StartNewGame started a travel"), *Case.Name), Save->IsTravelPending());
				return false;
			}
			if (!GameWorldReady(C, *S, GMonasteryMap))
			{
				return false;
			}
			Test->TestFalse(FString::Printf(TEXT("[%s] the broken file was replaced by the new game (no slot)"), *Case.Name), SlotExists());
			ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(C.W);
			Test->TestFalse(FString::Printf(TEXT("[%s] no valid save after New Game"), *Case.Name), Save && Save->HasValidSave());
			Test->TestFalse(FString::Printf(TEXT("[%s] no restore pending in the new game"), *Case.Name), Save && Save->HasPendingRestore());
			Test->TestFalse(FString::Printf(TEXT("[%s] candles not solved in the new game"), *Case.Name), HasState(LBPie::Tag(TEXT("State.Chapel.CandlesSolved"))));
			return true;
		}, 120.f);
	}

	R->Add(TEXT("No broken file left behind"), [Test](FCtx&)
	{
		Test->TestFalse(TEXT("Slot is clean at the end"), SlotExists());
		return true;
	});

	Enqueue(R);
	return true;
}

// 1b. The file format (no world needed): every damaged shape is rejected before the engine's loader sees it
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBSaveFileIntegrityTest, "LastBell.Save.FileIntegrity", (EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter))
bool FLBSaveFileIntegrityTest::RunTest(const FString& Parameters)
{
	ULBSaveGame* Save = NewObject<ULBSaveGame>(GetTransientPackage());
	Save->CheckpointId = TEXT("CP_Integrity");
	Save->MapName = TEXT("/Game/LastBell/Maps/L_Monastery");
	Save->CheckpointTransform = FTransform(FRotator(0.f, 45.f, 0.f), FVector(1.f, 2.f, 3.f));
	for (const TCHAR* Name : { TEXT("State.Chapel.Candle.1"), TEXT("State.Chapel.Candle.3"), TEXT("State.Crypt.Dial.A.2"), TEXT("State.Ritual.1") })
	{
		Save->WorldState.AddTag(LBPie::Tag(Name));
	}
	Save->ReachedCheckpoints.Add(TEXT("CP_A"));
	Save->PlayTimeSeconds = 99.5f;

	TArray<uint8> File;
	if (!TestTrue(TEXT("EncodeSave"), ULBSaveSubsystem::EncodeSave(Save, File)))
	{
		return false;
	}
	FString Reason;
	const ULBSaveGame* Back = ULBSaveSubsystem::DecodeSave(File, Reason);
	if (TestNotNull(TEXT("An intact file decodes"), Back))
	{
		TestEqual(TEXT("CheckpointId survives"), Back->CheckpointId, Save->CheckpointId);
		TestEqual(TEXT("MapName survives"), Back->MapName, Save->MapName);
		TestTrue(TEXT("WorldState survives"), Back->WorldState.Num() == Save->WorldState.Num() && Back->WorldState.HasAllExact(Save->WorldState));
		TestEqual(TEXT("PlayTime survives"), Back->PlayTimeSeconds, 99.5f);
	}

	// Every strict prefix of the file (all lengths from 0 to N-1) must be rejected, none may reach the engine's loader (which can assert).
	int32 PrefixesRejected = 0;
	for (int32 Len = 0; Len < File.Num(); ++Len)
	{
		TArray<uint8> Prefix;
		Prefix.Append(File.GetData(), Len);
		FString PrefixReason;
		if (ULBSaveSubsystem::DecodeSave(Prefix, PrefixReason) == nullptr && !PrefixReason.IsEmpty())
		{
			++PrefixesRejected;
		}
	}
	TestEqual(TEXT("Every truncation is rejected with a reason"), PrefixesRejected, File.Num());

	// Every single-byte change of the file is rejected (the CRC covers the payload, the footer fields are checked).
	int32 FlipsRejected = 0;
	for (int32 i = 0; i < File.Num(); ++i)
	{
		TArray<uint8> Flipped = File;
		Flipped[i] ^= 0xA5;
		FString FlipReason;
		if (ULBSaveSubsystem::DecodeSave(Flipped, FlipReason) == nullptr && !FlipReason.IsEmpty())
		{
			++FlipsRejected;
		}
	}
	TestEqual(TEXT("Every single-byte corruption is rejected"), FlipsRejected, File.Num());

	// Trailing junk and a missing footer.
	TArray<uint8> Extended = File;
	Extended.Add(0x00);
	TestNull(TEXT("A file with an extra trailing byte is rejected"), ULBSaveSubsystem::DecodeSave(Extended, Reason));
	TArray<uint8> NoFooter;
	NoFooter.Append(File.GetData(), File.Num() - 12);
	TestNull(TEXT("A raw engine save without the footer (older build) is rejected"), ULBSaveSubsystem::DecodeSave(NoFooter, Reason));
	return true;
}

// =====================================================================================================================
// 2. Quit to the menu mid-puzzle, Continue
// =====================================================================================================================
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBSaveQuitMidPuzzleTest, "LastBell.Functional.Save.QuitMidPuzzle_Continue",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBSaveQuitMidPuzzleTest::RunTest(const FString& Parameters)
{
	FRunnerPtr R = StartSession(this, GMonasteryMap);
	TSharedRef<FState> S = MakeShared<FState>();
	FAutomationTestBase* Test = this;
	if (!ResolveTags(Test, *S))
	{
		return false;
	}

	AddReadyStep(*R, S, Test);
	AddCheck(*R, TEXT("Start state: all four candles unlit and interactable; the order is 3,1,4,2"), [S, Test](FCtx& C)
	{
		for (int32 i = 0; i < 4; ++i)
		{
			CheckCandle(Test, *S, i, false, C.Pawn, TEXT("Start"));
		}
		const TArray<FGameplayTag>& Steps = S->Seq()->Steps;
		Test->TestTrue(TEXT("The sequence is Candle.3, Candle.1, Candle.4, Candle.2"),
			Steps.Num() == 4 && Steps[0] == S->Candle[2] && Steps[1] == S->Candle[0] && Steps[2] == S->Candle[3] && Steps[3] == S->Candle[1]);
		Test->TestEqual(TEXT("Progress 0"), S->Seq()->GetProgress(), 0);
	});

	// 2 candles in the correct order (3, then 1), each with the real interactor.
	AddBot(*R, Test, TEXT("Light Candle.3 then Candle.1 (route bot, real interactor)"), { S->Candle[2], S->Candle[0] });
	AddSettle(*R, TEXT("Settle"), 4);
	AddCheck(*R, TEXT("Two candles lit in order, then SaveCheckpoint"), [S, Test](FCtx& C)
	{
		CheckCandle(Test, *S, 2, true, C.Pawn, TEXT("Before the save"));
		CheckCandle(Test, *S, 0, true, C.Pawn, TEXT("Before the save"));
		CheckCandle(Test, *S, 3, false, C.Pawn, TEXT("Before the save"));
		CheckCandle(Test, *S, 1, false, C.Pawn, TEXT("Before the save"));
		Test->TestEqual(TEXT("Sequence progress 2"), S->Seq()->GetProgress(), 2);
		Test->TestTrue(TEXT("OnStepAccepted(0), OnStepAccepted(1)"), S->Sink->AcceptedSteps == TArray<int32>({ 0, 1 }));
		Test->TestEqual(TEXT("No failure"), S->Sink->FailedWith.Num(), 0);
		SaveNow(Test, C, *S);
		if (const ULBSaveGame* Disk = ReadDiskSave())
		{
			Test->TestTrue(TEXT("The slot holds Candle.3 and Candle.1"), Disk->WorldState.HasTagExact(S->Candle[2]) && Disk->WorldState.HasTagExact(S->Candle[0]));
			Test->TestFalse(TEXT("The slot holds neither Candle.2 nor Candle.4"), Disk->WorldState.HasTagExact(S->Candle[1]) || Disk->WorldState.HasTagExact(S->Candle[3]));
		}
	});

	// Quit to the menu.
	R->Add(TEXT("ReturnToMainMenu, wait for L_MainMenu"), [S, Test](FCtx& C)
	{
		if (C.bFirst)
		{
			ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(C.W);
			if (!Test->TestNotNull(TEXT("Save subsystem"), Save))
			{
				return true;
			}
			S->OldWorld = C.W;
			S->Settle = 0;
			Save->ReturnToMainMenu();
			Test->TestTrue(TEXT("ReturnToMainMenu started a travel"), Save->IsTravelPending());
			return false;
		}
		return MenuWorldReady(C, *S);
	}, 90.f);

	// Continue from the menu. The world state is reset first: a fresh process starts with an empty state and must get everything from disk.
	R->Add(TEXT("In the menu: Continue loads the slot"), [S, Test](FCtx& C)
	{
		if (C.bFirst)
		{
			ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(C.W);
			if (!Test->TestNotNull(TEXT("Save subsystem in the menu"), Save))
			{
				return true;
			}
			Test->TestTrue(TEXT("The menu sees a valid save (Continue would be shown)"), Save->HasValidSave());
			ULBWorldStateSubsystem::Get(C.W)->ResetState();
			Test->TestFalse(TEXT("Menu state reset: Candle.3 not in memory"), HasState(S->Candle[2]));
			S->OldWorld = C.W;
			S->Settle = 0;
			Test->TestTrue(TEXT("ContinueGame returns true"), Save->ContinueGame());
			return false;
		}
		return GameWorldReady(C, *S, GMonasteryMap);
	}, 120.f);

	AddCheck(*R, TEXT("After Continue: the partial puzzle is restored"), [S, Test, &R = *R](FCtx& C)
	{
		if (!Resolve(Test, C.W, *S))
		{
			R.Abort(TEXT("Could not find the puzzle actors after Continue"));
			return;
		}
		BindSink(*S);
		CheckCandle(Test, *S, 2, true, C.Pawn, TEXT("After Continue"));
		CheckCandle(Test, *S, 0, true, C.Pawn, TEXT("After Continue"));
		CheckCandle(Test, *S, 3, false, C.Pawn, TEXT("After Continue"));
		CheckCandle(Test, *S, 1, false, C.Pawn, TEXT("After Continue"));
		Test->TestEqual(TEXT("Sequence progress is 2"), S->Seq()->GetProgress(), 2);
		Test->TestFalse(TEXT("Not solved"), S->Seq()->IsSolved());
		Test->TestFalse(TEXT("CandlesSolved absent"), HasState(S->CandlesSolved));
		Test->TestEqual(TEXT("No failure or events on load"), S->Sink->FailedWith.Num() + S->Sink->AcceptedSteps.Num(), 0);
		CheckDistToSaved(Test, C, *S);
	});

	// Finish the remaining two in order: 4 then 2.
	AddBot(*R, Test, TEXT("Finish the puzzle (Candle.4, Candle.2)"), { S->CandlesSolved });
	AddSettle(*R, TEXT("Settle after solving"), 6);
	AddCheck(*R, TEXT("Solved after finishing the remaining two"), [S, Test](FCtx& C)
	{
		Test->TestTrue(TEXT("CandlesSolved present"), HasState(S->CandlesSolved));
		for (int32 i = 0; i < 4; ++i)
		{
			CheckCandle(Test, *S, i, true, C.Pawn, TEXT("Solved"));
		}
		Test->TestTrue(TEXT("Steps accepted were 2 then 3"), S->Sink->AcceptedSteps == TArray<int32>({ 2, 3 }));
		Test->TestEqual(TEXT("No failure"), S->Sink->FailedWith.Num(), 0);
		Test->TestEqual(TEXT("OnPuzzleSolved fired once"), S->Sink->SolvedCount, 1);
		Test->TestTrue(TEXT("Puzzle reports solved"), S->Seq()->IsSolved());
	});

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// 3. Death mid-puzzle: the unsaved lever move is lost, the saved one stays
// =====================================================================================================================
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBSaveDeathMidPuzzleTest, "LastBell.Functional.Save.DeathMidPuzzle",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBSaveDeathMidPuzzleTest::RunTest(const FString& Parameters)
{
	FRunnerPtr R = StartSession(this, GMonasteryMap);
	TSharedRef<FState> S = MakeShared<FState>();
	FAutomationTestBase* Test = this;
	if (!ResolveTags(Test, *S))
	{
		return false;
	}

	AddReadyStep(*R, S, Test);
	AddCheck(*R, TEXT("Start state: every lever at its InitialIndex, the winch unusable"), [S, Test](FCtx& C)
	{
		for (int32 L = 0; L < 3; ++L)
		{
			Test->TestEqual(FString::Printf(TEXT("Lever %c at InitialIndex"), TEXT('A') + L), DialIndex(*S, L), S->DialComp(L)->InitialIndex);
		}
		ULBInteractableComponent* Winch = FState::Inter(S->Winch.Get());
		Test->TestFalse(TEXT("The winch cannot be used at the start"), Winch && Winch->CanInteract(C.Pawn));
	});

	// Lever A to its solution (A.2), then save.
	AddBot(*R, Test, TEXT("Set lever A to A.2 (route bot, real interactor)"), { S->Dial[0][2] });
	AddSettle(*R, TEXT("Settle"), 4);
	AddCheck(*R, TEXT("Lever A solved: SaveCheckpoint"), [S, Test](FCtx& C)
	{
		Test->TestEqual(TEXT("Lever A at index 2"), DialIndex(*S, 0), 2);
		Test->TestTrue(TEXT("A.2 present"), HasState(S->Dial[0][2]));
		SaveNow(Test, C, *S);
	});

	// Lever B to a wrong position afterwards, NOT saved. B starts at 1 (the saved position), one press takes it to 2.
	AddBot(*R, Test, TEXT("Move lever B to B.2 (wrong, unsaved)"), { S->Dial[1][2] });
	AddSettle(*R, TEXT("Settle"), 4);
	R->Add(TEXT("B moved in memory only, then Kill"), [S, Test](FCtx& C)
	{
		if (C.bFirst)
		{
			Test->TestEqual(TEXT("Lever B moved to index 2 in memory"), DialIndex(*S, 1), 2);
			Test->TestTrue(TEXT("B.2 present in memory"), HasState(S->Dial[1][2]));
			if (const ULBSaveGame* Disk = ReadDiskSave())
			{
				Test->TestTrue(TEXT("The slot still has A.2"), Disk->WorldState.HasTagExact(S->Dial[0][2]));
				Test->TestFalse(TEXT("The slot does not have B.2 (never saved)"), Disk->WorldState.HasTagExact(S->Dial[1][2]));
			}
			if (!Test->TestNotNull(TEXT("Pawn"), C.Pawn))
			{
				return true;
			}
			S->OldWorld = C.W;
			S->Settle = 0;
			C.Pawn->Kill();
			return false;
		}
		return GameWorldReady(C, *S, GMonasteryMap);
	}, 120.f);

	AddCheck(*R, TEXT("After the death reload: A kept, B back to its saved position, the winch still unusable"), [S, Test, &R = *R](FCtx& C)
	{
		if (!Resolve(Test, C.W, *S))
		{
			R.Abort(TEXT("Could not find the puzzle actors after the reload"));
			return;
		}
		Test->TestEqual(TEXT("Lever A is still A.2 (the saved state)"), DialIndex(*S, 0), 2);
		Test->TestTrue(TEXT("A.2 present"), HasState(S->Dial[0][2]));
		Test->TestEqual(TEXT("Lever B is back at its saved/initial position (1), not the unsaved 2"), DialIndex(*S, 1), 1);
		Test->TestTrue(TEXT("B.1 present"), HasState(S->Dial[1][1]));
		Test->TestFalse(TEXT("B.2 absent"), HasState(S->Dial[1][2]));
		Test->TestEqual(TEXT("Lever C unchanged (1)"), DialIndex(*S, 2), 1);
		Test->TestFalse(TEXT("The crank is not held"), HasState(S->Crank));
		ULBInteractableComponent* Winch = FState::Inter(S->Winch.Get());
		Test->TestFalse(TEXT("The winch is not usable (wrong combination, no crank)"), Winch && Winch->CanInteract(C.Pawn));
		CheckDistToSaved(Test, C, *S);
	});

	// The winch needs the combination AND the crank.
	AddBot(*R, Test, TEXT("Set lever B to B.0 (the solution)"), { S->Dial[1][0] });
	AddSettle(*R, TEXT("Settle"), 4);
	AddCheck(*R, TEXT("Combination A.2/B.0/C.1 set, no crank: still unusable"), [S, Test](FCtx& C)
	{
		Test->TestTrue(TEXT("A.2, B.0, C.1 present"), HasState(S->Dial[0][2]) && HasState(S->Dial[1][0]) && HasState(S->Dial[2][1]));
		ULBInteractableComponent* Winch = FState::Inter(S->Winch.Get());
		Test->TestFalse(TEXT("The winch needs the crank too"), Winch && Winch->CanInteract(C.Pawn));
		ULBWorldStateSubsystem::Get(C.W)->AddState(S->Crank);
	});
	AddSettle(*R, TEXT("Settle"), 2);
	AddCheck(*R, TEXT("Combination plus crank: the winch is usable"), [S, Test](FCtx& C)
	{
		ULBInteractableComponent* Winch = FState::Inter(S->Winch.Get());
		Test->TestTrue(TEXT("The winch is usable with the combination and the crank"), Winch && Winch->CanInteract(C.Pawn));
	});

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// 4. Revisit solved puzzles: still solved, still inert
// =====================================================================================================================
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBSaveRevisitSolvedTest, "LastBell.Functional.Save.RevisitSolved",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBSaveRevisitSolvedTest::RunTest(const FString& Parameters)
{
	FRunnerPtr R = StartSession(this, GMonasteryMap);
	TSharedRef<FState> S = MakeShared<FState>();
	FAutomationTestBase* Test = this;
	if (!ResolveTags(Test, *S))
	{
		return false;
	}

	AddReadyStep(*R, S, Test);
	AddBot(*R, Test, TEXT("Solve the candles and use the altar (route bot, real interactor)"), { S->CandlesSolved, S->Ritual1 }, 90.f);
	AddSettle(*R, TEXT("Settle"), 4);
	R->Add(TEXT("Solved and consumed: SaveCheckpoint, LoadLastCheckpoint"), [S, Test](FCtx& C)
	{
		if (C.bFirst)
		{
			Test->TestTrue(TEXT("CandlesSolved present before the save"), HasState(S->CandlesSolved));
			Test->TestTrue(TEXT("Ritual.1 present before the save"), HasState(S->Ritual1));
			if (!Test->TestNotNull(TEXT("Pawn (alive)"), C.Pawn))
			{
				return true;
			}
			SaveNow(Test, C, *S);
			S->OldWorld = C.W;
			S->Settle = 0;
			Test->TestTrue(TEXT("LoadLastCheckpoint accepted"), ULBSaveSubsystem::Get(C.W)->LoadLastCheckpoint());
			return false;
		}
		return GameWorldReady(C, *S, GMonasteryMap);
	}, 120.f);

	AddCheck(*R, TEXT("After the reload: candles lit and not interactable, altar consumed, sequence inert"), [S, Test, &R = *R](FCtx& C)
	{
		if (!Resolve(Test, C.W, *S))
		{
			R.Abort(TEXT("Could not find the puzzle actors after the reload"));
			return;
		}
		BindSink(*S);
		for (int32 i = 0; i < 4; ++i)
		{
			CheckCandle(Test, *S, i, true, C.Pawn, TEXT("After reload"));
			if (ULBInteractableComponent* Comp = S->CandleInter(i))
			{
				Comp->OnInteracted.AddDynamic(S->Sink.Get(), &ULBTestSink::HandleInteracted);
			}
		}
		Test->TestTrue(TEXT("CandlesSolved present"), HasState(S->CandlesSolved));
		Test->TestTrue(TEXT("The sequence comes back solved (inert)"), S->Seq()->IsSolved());
		Test->TestEqual(TEXT("Progress 4"), S->Seq()->GetProgress(), 4);
		Test->TestTrue(TEXT("Ritual.1 present"), HasState(S->Ritual1));
		ULBInteractableComponent* Altar = FState::Inter(S->Altar.Get());
		if (Test->TestNotNull(TEXT("Altar interactable"), Altar))
		{
			Test->TestFalse(TEXT("The altar mechanism is consumed (not usable)"), Altar->CanInteract(C.Pawn));
			Altar->OnInteracted.AddDynamic(S->Sink.Get(), &ULBTestSink::HandleInteracted);
		}
		Test->TestEqual(TEXT("No puzzle events on load"), S->Sink->FailedWith.Num() + S->Sink->AcceptedSteps.Num() + S->Sink->SolvedCount, 0);
	});

	// Try to light a candle again (the first step of the original order, and a "wrong" one) with the real interactor.
	AddPress(*R, S, Test, TEXT("Candle.3 (already lit)"), [](FState& St) { return St.CandleActor[2].Get(); }, [S, Test](FCtx&, bool)
	{
		Test->TestEqual(TEXT("Pressing a lit candle did not interact"), S->Sink->InteractedCount, 0);
	});
	AddPress(*R, S, Test, TEXT("Candle.2 (out of the original order)"), [](FState& St) { return St.CandleActor[1].Get(); }, [S, Test](FCtx&, bool)
	{
		Test->TestEqual(TEXT("Pressing a lit candle out of order did not interact"), S->Sink->InteractedCount, 0);
	});
	AddPress(*R, S, Test, TEXT("The altar again"), [](FState& St) { return St.Altar.Get(); }, [S, Test](FCtx&, bool)
	{
		Test->TestEqual(TEXT("Pressing the used altar did not interact"), S->Sink->InteractedCount, 0);
	});
	AddSettle(*R, TEXT("Let any (wrong) reaction run"), 8);
	AddCheck(*R, TEXT("Still solved, nothing reset, no events"), [S, Test](FCtx& C)
	{
		for (int32 i = 0; i < 4; ++i)
		{
			CheckCandle(Test, *S, i, true, C.Pawn, TEXT("After the presses"));
		}
		Test->TestTrue(TEXT("CandlesSolved still present"), HasState(S->CandlesSolved));
		Test->TestTrue(TEXT("Ritual.1 still present"), HasState(S->Ritual1));
		Test->TestEqual(TEXT("No OnPuzzleFailed"), S->Sink->FailedWith.Num(), 0);
		Test->TestEqual(TEXT("No OnStepAccepted"), S->Sink->AcceptedSteps.Num(), 0);
		Test->TestEqual(TEXT("No OnPuzzleSolved"), S->Sink->SolvedCount, 0);
		Test->TestTrue(TEXT("Still solved"), S->Seq()->IsSolved());
		Test->TestEqual(TEXT("Progress still 4"), S->Seq()->GetProgress(), 4);
	});

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// 5. New Game clears everything
// =====================================================================================================================
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBSaveNewGameClearsTest, "LastBell.Functional.Save.NewGameClears",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBSaveNewGameClearsTest::RunTest(const FString& Parameters)
{
	FRunnerPtr R = StartSession(this, GMonasteryMap);
	TSharedRef<FState> S = MakeShared<FState>();
	FAutomationTestBase* Test = this;
	if (!ResolveTags(Test, *S))
	{
		return false;
	}

	AddReadyStep(*R, S, Test);
	AddBot(*R, Test, TEXT("Make progress: Candle.3, Candle.1 and lever A to A.2"), { S->Candle[2], S->Candle[0], S->Dial[0][2] }, 90.f);
	AddSettle(*R, TEXT("Settle"), 4);
	R->Add(TEXT("Save the progress, then StartNewGame"), [S, Test](FCtx& C)
	{
		if (C.bFirst)
		{
			Test->TestTrue(TEXT("Progress exists: Candle.3, Candle.1, A.2"), HasState(S->Candle[2]) && HasState(S->Candle[0]) && HasState(S->Dial[0][2]));
			SaveNow(Test, C, *S);
			ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(C.W);
			if (!Save)
			{
				return true;
			}
			Test->TestTrue(TEXT("The checkpoint counts as reached"), Save->HasReachedCheckpoint(GSaveCheckpoint));
			S->OldWorld = C.W;
			S->Settle = 0;
			Save->StartNewGame();
			return false;
		}
		return GameWorldReady(C, *S, GMonasteryMap);
	}, 120.f);

	AddCheck(*R, TEXT("After New Game: no candle lit, every lever at InitialIndex, no puzzle tags, no save"), [S, Test, &R = *R](FCtx& C)
	{
		if (!Resolve(Test, C.W, *S))
		{
			R.Abort(TEXT("Could not find the puzzle actors after New Game"));
			return;
		}
		ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(C.W);
		Test->TestFalse(TEXT("No slot file"), SlotExists());
		Test->TestFalse(TEXT("HasValidSave is false"), Save && Save->HasValidSave());
		Test->TestFalse(TEXT("ContinueGame is false"), Save && Save->ContinueGame());
		Test->TestFalse(TEXT("The saved checkpoint is no longer reached"), Save && Save->HasReachedCheckpoint(GSaveCheckpoint));
		Test->TestFalse(TEXT("No restore pending"), Save && Save->HasPendingRestore());

		for (int32 i = 0; i < 4; ++i)
		{
			CheckCandle(Test, *S, i, false, C.Pawn, TEXT("New Game"));
		}
		Test->TestEqual(TEXT("Sequence progress 0"), S->Seq()->GetProgress(), 0);
		Test->TestFalse(TEXT("Sequence not solved"), S->Seq()->IsSolved());
		for (int32 L = 0; L < 3; ++L)
		{
			const ULBDialComponent* Dial = S->DialComp(L);
			Test->TestEqual(FString::Printf(TEXT("Lever %c at its InitialIndex"), TEXT('A') + L), Dial->GetCurrentIndex(), Dial->InitialIndex);
			int32 Present = 0;
			for (int32 P = 0; P < 3; ++P)
			{
				Present += HasState(S->Dial[L][P]) ? 1 : 0;
			}
			Test->TestEqual(FString::Printf(TEXT("Lever %c has exactly one position tag"), TEXT('A') + L), Present, 1);
		}

		const ULBWorldStateSubsystem* WS = ULBWorldStateSubsystem::Get(C.W);
		for (const TCHAR* Parent : { TEXT("State.Chapel"), TEXT("State.Ritual"), TEXT("State.Tower"), TEXT("State.Cloister"), TEXT("State.Item") })
		{
			const FGameplayTag ParentTag = LBPie::Tag(Parent);
			Test->TestTrue(FString::Printf(TEXT("Parent tag %s exists"), Parent), ParentTag.IsValid());
			Test->TestFalse(FString::Printf(TEXT("No %s.* tag survives New Game"), Parent), ParentTag.IsValid() && WS->GetStateRef().HasTag(ParentTag));
		}
		ULBInteractableComponent* Winch = FState::Inter(S->Winch.Get());
		Test->TestFalse(TEXT("The winch is unusable"), Winch && Winch->CanInteract(C.Pawn));
	});

	Enqueue(R);
	return true;
}

#endif
