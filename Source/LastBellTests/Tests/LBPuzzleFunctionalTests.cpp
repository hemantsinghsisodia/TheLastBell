#include "Tests/LBRouteBot.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Editor.h"
#include "Tests/AutomationEditorCommon.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Character/LBCharacter.h"
#include "Components/LBInteractableComponent.h"
#include "Components/LBInteractorComponent.h"
#include "Puzzles/LBDialComponent.h"
#include "Puzzles/LBSequencePuzzleComponent.h"
#include "Save/LBSaveSubsystem.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "Tests/LBTestSink.h"
#include "UObject/StrongObjectPtr.h"
#include "LBTraceChannels.h"
#include "LBLog.h"

// Phase 4 puzzle framework functional tests (P4-001). Each test runs one PIE session on L_Test_MicroSlice. The puzzle rigs are
// spawned at runtime on a flat floor far below the level (so no level geometry or Blueprint reacts to them), from the same
// components a Blueprint puzzle uses: ULBInteractableComponent + ULBSequencePuzzleComponent / ULBDialComponent. All presses go
// through the real interactor (TryInteract). The tags are existing ini tags nothing in the micro slice reacts to:
// State.Chapel.Candle.1-3 (steps), State.Ritual.1 (solved), State.Cloister.Weight.1-3 (dial positions).

namespace
{
	const TCHAR* GMap = TEXT("/Game/LastBell/Maps/L_Test_MicroSlice");
	const TCHAR* GCheckpoint = TEXT("CP_PuzzleTest");

	constexpr float GFloorTopZ = -20000.f;
	constexpr float GStartX = -6000.f;
	constexpr float GPropX = GStartX + 130.f;
	constexpr float GPropZ = GFloorTopZ + 120.f;
	constexpr float GSequenceY[3] = { -300.f, 0.f, 300.f };
	constexpr float GDialY = 900.f;

	void Note(const FString& Text) { UE_LOG(LogLB, Display, TEXT("[Puzzles] %s"), *Text); }

	struct FPuzzleCtx
	{
		UWorld* W = nullptr;
		ALBCharacter* Pawn = nullptr;
		int32 Frames = 0;
		bool bFirst = false;
	};

	/** Shared scratch state of one test. */
	struct FPuzzleState
	{
		TStrongObjectPtr<ULBTestSink> Sink;
		TWeakObjectPtr<AActor> Host;
		TWeakObjectPtr<AActor> Candles[3];
		TWeakObjectPtr<AActor> DialActor;
		TWeakObjectPtr<UWorld> OldWorld;
		TSharedPtr<FLBRouteBot> Bot;

		FGameplayTag Candle[3];
		FGameplayTag Solved;
		FGameplayTag Weight[3];

		int32 Presses = 0;
		bool bSabotaged = false;
		bool bLoadIssued = false;

		ULBSequencePuzzleComponent* Seq() const { return Host.IsValid() ? Host->FindComponentByClass<ULBSequencePuzzleComponent>() : nullptr; }
		ULBDialComponent* Dial() const { return DialActor.IsValid() ? DialActor->FindComponentByClass<ULBDialComponent>() : nullptr; }
		ULBInteractableComponent* Interactable(const AActor* A) const { return A ? A->FindComponentByClass<ULBInteractableComponent>() : nullptr; }
	};

	class FPuzzleRunner : public IAutomationLatentCommand
	{
	public:
		using FStepFn = TFunction<bool(FPuzzleCtx&)>;

		explicit FPuzzleRunner(FAutomationTestBase* InTest) : Test(InTest) {}

		void Add(const FString& Name, FStepFn Fn, float WallTimeout = 30.f)
		{
			Steps.Add({ Name, WallTimeout, MoveTemp(Fn) });
		}

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

			FPuzzleCtx Ctx;
			Ctx.W = LBPie::World();
			Ctx.Pawn = LBPie::Pawn();
			Ctx.Frames = Frames;
			Ctx.bFirst = (Frames == 0);
			++Frames;

			const bool bDone = Step.Fn(Ctx);
			const bool bTimedOut = !bDone && (FPlatformTime::Seconds() - WallStart) > Step.Timeout;
			if (bTimedOut)
			{
				Test->AddError(FString::Printf(TEXT("Step '%s' timed out after %.0fs"), *Step.Name, Step.Timeout));
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

	using FRunnerPtr = TSharedRef<FPuzzleRunner>;

	// ---- world helpers ------------------------------------------------------------------------------------------------

	float HalfHeight(const ALBCharacter* P) { return P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight(); }

	void Place(ALBCharacter* P, float X, float Y)
	{
		P->SetActorLocationAndRotation(FVector(X, Y, GFloorTopZ + HalfHeight(P) + 0.1f), FRotator::ZeroRotator, false, nullptr, ETeleportType::TeleportPhysics);
		if (UCharacterMovementComponent* M = P->GetCharacterMovement())
		{
			M->StopMovementImmediately();
		}
	}

	/** Stands the pawn in front of the actor (same Y, facing +X) and points the controller at its centre. */
	void StandAndAim(ALBCharacter* P, const AActor* Target)
	{
		FVector Origin, Extent;
		Target->GetActorBounds(true, Origin, Extent);
		Place(P, GStartX, Origin.Y);
		const UCameraComponent* Cam = P->FindComponentByClass<UCameraComponent>();
		const FVector Eye = Cam ? Cam->GetComponentLocation() : P->GetActorLocation() + FVector(0, 0, 64.f);
		if (AController* C = P->GetController())
		{
			C->SetControlRotation((Origin - Eye).Rotation());
		}
	}

	bool SpawnFloor(UWorld* W)
	{
		UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
		AStaticMeshActor* Floor = Cube ? W->SpawnActor<AStaticMeshActor>(FVector(0.f, 0.f, GFloorTopZ - 100.f), FRotator::ZeroRotator) : nullptr;
		if (!Floor)
		{
			return false;
		}
		Floor->SetMobility(EComponentMobility::Movable);
		Floor->GetStaticMeshComponent()->SetStaticMesh(Cube);
		Floor->SetActorScale3D(FVector(200.f, 60.f, 2.f));
		return true;
	}

	/** A 40 cm cube the Interaction trace channel hits. */
	AStaticMeshActor* SpawnProp(UWorld* W, const FVector& Location, const TCHAR* Label)
	{
		UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
		AStaticMeshActor* Prop = Cube ? W->SpawnActor<AStaticMeshActor>(Location, FRotator::ZeroRotator) : nullptr;
		if (Prop)
		{
			Prop->SetMobility(EComponentMobility::Movable);
			UStaticMeshComponent* Mesh = Prop->GetStaticMeshComponent();
			Mesh->SetStaticMesh(Cube);
			Mesh->SetCollisionProfileName(TEXT("BlockAll"));
			Mesh->SetCollisionResponseToChannel(LB_TRACE_INTERACTION, ECR_Block);
			Prop->SetActorScale3D(FVector(0.4f));
			Prop->SetActorLabel(Label);
		}
		return Prop;
	}

	/** Components added after the actor began play get BeginPlay on RegisterComponent, so configure first, then register. */
	template <typename T>
	T* AddComponent(AActor* Owner, const TCHAR* Name)
	{
		T* Comp = NewObject<T>(Owner, Name);
		Owner->AddInstanceComponent(Comp);
		return Comp;
	}

	bool ResolveTags(FPuzzleState& S, FAutomationTestBase* Test)
	{
		const TCHAR* Candles[3] = { TEXT("State.Chapel.Candle.1"), TEXT("State.Chapel.Candle.2"), TEXT("State.Chapel.Candle.3") };
		const TCHAR* Weights[3] = { TEXT("State.Cloister.Weight.1"), TEXT("State.Cloister.Weight.2"), TEXT("State.Cloister.Weight.3") };
		bool bOk = true;
		for (int32 i = 0; i < 3; ++i)
		{
			S.Candle[i] = LBPie::Tag(Candles[i]);
			S.Weight[i] = LBPie::Tag(Weights[i]);
			bOk &= Test->TestTrue(FString::Printf(TEXT("Tag %s exists in the ini"), Candles[i]), S.Candle[i].IsValid());
			bOk &= Test->TestTrue(FString::Printf(TEXT("Tag %s exists in the ini"), Weights[i]), S.Weight[i].IsValid());
		}
		S.Solved = LBPie::Tag(TEXT("State.Ritual.1"));
		bOk &= Test->TestTrue(TEXT("Tag State.Ritual.1 exists in the ini"), S.Solved.IsValid());
		return bOk;
	}

	/** Host with the sequence component plus three single-use candle interactables (the BP_PuzzleCandle shape). */
	bool SpawnSequenceRig(UWorld* W, FPuzzleState& S, FAutomationTestBase* Test)
	{
		AStaticMeshActor* Host = W->SpawnActor<AStaticMeshActor>(FVector(GStartX + 800.f, 0.f, GPropZ), FRotator::ZeroRotator);
		if (!Test->TestNotNull(TEXT("Sequence host spawned"), Host))
		{
			return false;
		}
		Host->SetActorLabel(TEXT("Test_SequenceHost"));
		ULBSequencePuzzleComponent* Seq = AddComponent<ULBSequencePuzzleComponent>(Host, TEXT("SequencePuzzle"));
		Seq->Steps = { S.Candle[0], S.Candle[1], S.Candle[2] };
		Seq->SolvedTags.AddTag(S.Solved);
		if (S.Sink.IsValid())
		{
			Seq->OnStepAccepted.AddDynamic(S.Sink.Get(), &ULBTestSink::HandleStepAccepted);
			Seq->OnPuzzleFailed.AddDynamic(S.Sink.Get(), &ULBTestSink::HandlePuzzleFailed);
			Seq->OnPuzzleSolved.AddDynamic(S.Sink.Get(), &ULBTestSink::HandlePuzzleSolved);
		}
		Seq->RegisterComponent();
		S.Host = Host;

		for (int32 i = 0; i < 3; ++i)
		{
			AStaticMeshActor* Candle = SpawnProp(W, FVector(GPropX, GSequenceY[i], GPropZ), *FString::Printf(TEXT("Test_Candle%d"), i + 1));
			if (!Test->TestNotNull(TEXT("Candle spawned"), Candle))
			{
				return false;
			}
			ULBInteractableComponent* Interactable = AddComponent<ULBInteractableComponent>(Candle, TEXT("Interactable"));
			Interactable->GrantedStateTags.AddTag(S.Candle[i]);
			Interactable->bSingleUse = true;
			Interactable->ConsumedStateTag = S.Candle[i];
			Interactable->RegisterComponent();
			S.Candles[i] = Candle;
		}
		return true;
	}

	/** A cube with a plain (non single-use) interactable and a three-position dial. */
	bool SpawnDialRig(UWorld* W, FPuzzleState& S, FAutomationTestBase* Test, int32 InitialIndex, float Y = GDialY)
	{
		AStaticMeshActor* Actor = SpawnProp(W, FVector(GPropX, Y, GPropZ), TEXT("Test_Dial"));
		if (!Test->TestNotNull(TEXT("Dial spawned"), Actor))
		{
			return false;
		}
		ULBInteractableComponent* Interactable = AddComponent<ULBInteractableComponent>(Actor, TEXT("Interactable"));
		Interactable->RegisterComponent();
		ULBDialComponent* Dial = AddComponent<ULBDialComponent>(Actor, TEXT("Dial"));
		Dial->PositionTags = { S.Weight[0], S.Weight[1], S.Weight[2] };
		Dial->InitialIndex = InitialIndex;
		if (S.Sink.IsValid())
		{
			Dial->OnDialChanged.AddDynamic(S.Sink.Get(), &ULBTestSink::HandleDialChanged);
		}
		Dial->RegisterComponent();
		S.DialActor = Actor;
		return true;
	}

	/** PIE ready, tags resolved, floor, sink. Spawning the rigs is left to the caller. */
	void AddSetupStep(FPuzzleRunner& R, const TSharedRef<FPuzzleState>& S, FAutomationTestBase* Test, TFunction<bool(FPuzzleCtx&)> SpawnRigs)
	{
		R.Add(TEXT("PIE ready, floor, rigs"), [&R, S, Test, SpawnRigs](FPuzzleCtx& C)
		{
			if (!LBPie::WorldReady() || C.Frames < 5)
			{
				return false;
			}
			S->Sink.Reset(NewObject<ULBTestSink>(GetTransientPackage()));
			if (!ResolveTags(*S, Test) || !Test->TestTrue(TEXT("Floor spawned"), SpawnFloor(C.W)) || !SpawnRigs(C))
			{
				R.Abort(TEXT("Setup failed"));
				return true;
			}
			Place(C.Pawn, GStartX, 0.f);
			return true;
		}, 90.f);
	}

	void AddCheck(FPuzzleRunner& R, const FString& Name, TFunction<void(FPuzzleCtx&)> Fn)
	{
		R.Add(Name, [Fn](FPuzzleCtx& C)
		{
			Fn(C);
			return true;
		});
	}

	void AddSettle(FPuzzleRunner& R, const FString& Name, int32 Frames)
	{
		R.Add(Name, [Frames](FPuzzleCtx& C) { return C.Frames >= Frames; });
	}

	/** Stand in front of the target, wait for the camera to catch up, then press through the real interactor. */
	void AddPress(FPuzzleRunner& R, const TSharedRef<FPuzzleState>& S, FAutomationTestBase* Test, const FString& Label,
		TFunction<AActor*(FPuzzleState&)> GetTarget, TFunction<void(FPuzzleCtx&)> SameFrameCheck = nullptr)
	{
		R.Add(Label + TEXT(": stand and aim"), [S, Test, GetTarget](FPuzzleCtx& C)
		{
			AActor* Target = GetTarget(*S);
			if (!C.Pawn || !Test->TestNotNull(TEXT("Press target exists"), Target))
			{
				return true;
			}
			if (C.bFirst)
			{
				StandAndAim(C.Pawn, Target);
			}
			return C.Frames >= 8;
		});
		R.Add(Label + TEXT(": press"), [S, Test, GetTarget, Label, SameFrameCheck](FPuzzleCtx& C)
		{
			AActor* Target = GetTarget(*S);
			if (!C.Pawn || !Target)
			{
				return true;
			}
			C.Pawn->GetInteractor()->TryInteract();
			const ULBInteractableComponent* Focus = C.Pawn->GetInteractor()->GetFocusedComponent();
			Test->TestTrue(FString::Printf(TEXT("%s: the interactor focuses the target (focus=%s)"), *Label, *GetNameSafe(Focus ? Focus->GetOwner() : nullptr)),
				Focus && Focus->GetOwner() == Target);
			if (SameFrameCheck)
			{
				SameFrameCheck(C);
			}
			return true;
		});
	}

	TFunction<AActor*(FPuzzleState&)> CandleTarget(int32 Index)
	{
		return [Index](FPuzzleState& S) { return S.Candles[Index].Get(); };
	}

	bool HasState(const FGameplayTag& Tag) { return LBPie::HasState(Tag); }

	bool Available(const FPuzzleState& S, int32 CandleIndex, ALBCharacter* Pawn)
	{
		ULBInteractableComponent* Comp = S.Interactable(S.Candles[CandleIndex].Get());
		return Comp && Comp->CanInteract(Pawn);
	}

	TSharedRef<FPuzzleRunner> StartSession(FAutomationTestBase* Test)
	{
		LBPie::ClearSlot();
		FAutomationEditorCommonUtils::LoadMap(GMap);
		FRequestPlaySessionParams PlayParams;
		PlayParams.WorldType = EPlaySessionWorldType::PlayInEditor;
		GEditor->RequestPlaySession(PlayParams);
		return MakeShared<FPuzzleRunner>(Test);
	}

	void Enqueue(const TSharedRef<FPuzzleRunner>& Runner)
	{
		FAutomationTestFramework::Get().EnqueueLatentCommand(Runner);
	}

	/** True once a map reload has produced a fresh, ready world (after the first frames of the new world). */
	bool NewWorldReady(FPuzzleCtx& C, const TWeakObjectPtr<UWorld>& Old)
	{
		return C.W && C.W != Old.Get() && LBPie::WorldReady() && C.Frames >= 15;
	}
}

// =====================================================================================================================
// 1. Sequence puzzle: wrong step resets (and re-enables the steps), correct order solves
// =====================================================================================================================
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBPuzzleSequenceTest, "LastBell.Functional.Puzzles.Sequence",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBPuzzleSequenceTest::RunTest(const FString& Parameters)
{
	FRunnerPtr R = StartSession(this);
	TSharedRef<FPuzzleState> S = MakeShared<FPuzzleState>();
	FAutomationTestBase* Test = this;

	AddSetupStep(*R, S, Test, [S, Test](FPuzzleCtx& C) { return SpawnSequenceRig(C.W, *S, Test); });

	AddCheck(*R, TEXT("Initial state"), [S, Test](FPuzzleCtx& C)
	{
		Test->TestNotNull(TEXT("Sequence component found"), S->Seq());
		Test->TestEqual(TEXT("Initial progress"), S->Seq() ? S->Seq()->GetProgress() : -1, 0);
		for (int32 i = 0; i < 3; ++i)
		{
			Test->TestFalse(TEXT("No candle tag at start"), HasState(S->Candle[i]));
			Test->TestTrue(TEXT("Every candle is available at start"), Available(*S, i, C.Pawn));
		}
	});

	// Step 1 in order.
	AddPress(*R, S, Test, TEXT("Candle 1 (correct)"), CandleTarget(0), [S, Test](FPuzzleCtx& C)
	{
		Test->TestTrue(TEXT("Candle.1 granted"), HasState(S->Candle[0]));
		Test->TestEqual(TEXT("Progress 1"), S->Seq()->GetProgress(), 1);
		Test->TestTrue(TEXT("OnStepAccepted(0) fired"), S->Sink->AcceptedSteps == TArray<int32>({ 0 }));
		Test->TestFalse(TEXT("Candle 1 unavailable once consumed (derived from the tag)"), Available(*S, 0, C.Pawn));
		Test->TestTrue(TEXT("...but bEnabled was not cleared"), S->Interactable(S->Candles[0].Get())->bEnabled);
	});

	// Out of order: candle 3 while only 1 is lit.
	AddPress(*R, S, Test, TEXT("Candle 3 (wrong)"), CandleTarget(2), [S, Test](FPuzzleCtx&)
	{
		Test->TestTrue(TEXT("Wrong step tag is still present in the same frame (the reset is deferred, no re-entrancy)"), HasState(S->Candle[2]));
		Test->TestEqual(TEXT("No failure broadcast yet"), S->Sink->FailedWith.Num(), 0);
	});
	AddSettle(*R, TEXT("Let the deferred reset run"), 4);
	AddCheck(*R, TEXT("Wrong step reset every step and re-enabled the candles"), [S, Test](FPuzzleCtx& C)
	{
		for (int32 i = 0; i < 3; ++i)
		{
			Test->TestFalse(TEXT("Step tag removed by the reset"), HasState(S->Candle[i]));
			Test->TestTrue(TEXT("Candle usable again after the reset (no permanent bEnabled=false)"), Available(*S, i, C.Pawn));
		}
		Test->TestEqual(TEXT("OnPuzzleFailed fired once"), S->Sink->FailedWith.Num(), 1);
		if (S->Sink->FailedWith.Num() == 1)
		{
			Test->TestEqual(TEXT("OnPuzzleFailed reports the wrong step"), S->Sink->FailedWith[0], S->Candle[2]);
		}
		Test->TestEqual(TEXT("Progress back to 0"), S->Seq()->GetProgress(), 0);
		Test->TestFalse(TEXT("Not solved"), HasState(S->Solved));
		Test->TestEqual(TEXT("Not solved (callbacks)"), S->Sink->SolvedCount, 0);
	});

	// Now the correct order.
	AddPress(*R, S, Test, TEXT("Candle 1"), CandleTarget(0));
	AddPress(*R, S, Test, TEXT("Candle 2"), CandleTarget(1));
	AddPress(*R, S, Test, TEXT("Candle 3 (solves)"), CandleTarget(2), [S, Test](FPuzzleCtx&)
	{
		Test->TestTrue(TEXT("SolvedTags added synchronously by the last step"), HasState(S->Solved));
		Test->TestEqual(TEXT("OnPuzzleSolved fired once"), S->Sink->SolvedCount, 1);
		Test->TestTrue(TEXT("Solved flag"), S->Seq()->IsSolved());
	});
	AddSettle(*R, TEXT("Settle after solving"), 4);
	AddCheck(*R, TEXT("Solved and inert"), [S, Test](FPuzzleCtx& C)
	{
		const TArray<int32> Expected = { 0, 0, 1, 2 };
		Test->TestTrue(FString::Printf(TEXT("OnStepAccepted fired 0 (first try), then 0,1,2 (got %d events)"), S->Sink->AcceptedSteps.Num()), S->Sink->AcceptedSteps == Expected);
		Test->TestEqual(TEXT("Still exactly one failure"), S->Sink->FailedWith.Num(), 1);
		Test->TestTrue(TEXT("All step tags stay after solving"), HasState(S->Candle[0]) && HasState(S->Candle[1]) && HasState(S->Candle[2]));
		// A solved puzzle stopped listening: tampering with a step now neither fails nor un-solves it.
		ULBWorldStateSubsystem::Get(C.W)->RemoveState(S->Candle[1]);
	});
	AddSettle(*R, TEXT("Let any (wrong) reaction run"), 4);
	AddCheck(*R, TEXT("Solved puzzle ignores later changes"), [S, Test](FPuzzleCtx&)
	{
		Test->TestEqual(TEXT("No new failure after solving"), S->Sink->FailedWith.Num(), 1);
		Test->TestTrue(TEXT("Solved tag still present"), HasState(S->Solved));
		Test->TestTrue(TEXT("Other step tags untouched"), HasState(S->Candle[0]) && HasState(S->Candle[2]));
	});

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// 2. Dial
// =====================================================================================================================
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBPuzzleDialTest, "LastBell.Functional.Puzzles.Dial",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBPuzzleDialTest::RunTest(const FString& Parameters)
{
	FRunnerPtr R = StartSession(this);
	TSharedRef<FPuzzleState> S = MakeShared<FPuzzleState>();
	FAutomationTestBase* Test = this;

	auto DialOnlyOne = [S, Test](int32 Expected)
	{
		int32 Count = 0;
		for (int32 i = 0; i < 3; ++i)
		{
			Count += HasState(S->Weight[i]) ? 1 : 0;
		}
		Test->TestEqual(TEXT("Exactly one position tag present"), Count, 1);
		Test->TestTrue(FString::Printf(TEXT("Position tag %d present"), Expected), HasState(S->Weight[Expected]));
		Test->TestEqual(TEXT("Dial reports the index"), S->Dial() ? S->Dial()->GetCurrentIndex() : -2, Expected);
	};

	// A corrupt state (two positions present) is repaired on BeginPlay: lowest index kept.
	AddSetupStep(*R, S, Test, [S, Test](FPuzzleCtx& C)
	{
		FGameplayTagContainer Corrupt;
		Corrupt.AddTag(S->Weight[1]);
		Corrupt.AddTag(S->Weight[2]);
		ULBWorldStateSubsystem::Get(C.W)->AddStates(Corrupt);
		return SpawnDialRig(C.W, *S, Test, 0, GDialY + 600.f);
	});
	AddCheck(*R, TEXT("Corrupt multi-position state cleaned up"), [S, Test, DialOnlyOne](FPuzzleCtx& C)
	{
		DialOnlyOne(1);
		// Throw the repaired rig away and start from a clean state.
		if (S->DialActor.IsValid())
		{
			S->DialActor->Destroy();
		}
		ULBWorldStateSubsystem::Get(C.W)->ResetState();
		Test->TestTrue(TEXT("Second dial rig spawned"), SpawnDialRig(C.W, *S, Test, 1));
	});
	AddCheck(*R, TEXT("Initial position comes from InitialIndex"), [S, Test, DialOnlyOne](FPuzzleCtx&) { DialOnlyOne(1); });

	AddPress(*R, S, Test, TEXT("Dial press"), [](FPuzzleState& St) { return St.DialActor.Get(); }, [S, Test, DialOnlyOne](FPuzzleCtx&)
	{
		DialOnlyOne(2);
		Test->TestTrue(TEXT("OnDialChanged(2)"), S->Sink->DialIndices == TArray<int32>({ 2 }));
	});

	// Wrap, then walk to a target position with repeated presses.
	R->Add(TEXT("Press until the dial reaches position 1 (index), through the wrap"), [S, Test, DialOnlyOne](FPuzzleCtx& C)
	{
		ULBDialComponent* Dial = S->Dial();
		if (!C.Pawn || !Dial)
		{
			return false;
		}
		if (C.bFirst)
		{
			StandAndAim(C.Pawn, S->DialActor.Get());
			S->Presses = 0;
		}
		if (C.Frames < 8)
		{
			return false;
		}
		if (Dial->GetCurrentIndex() == 1)
		{
			DialOnlyOne(1);
			Test->TestEqual(TEXT("Needed 2 presses from index 2 (wrap to 0, then 1)"), S->Presses, 2);
			Test->TestTrue(TEXT("OnDialChanged sequence"), S->Sink->DialIndices == TArray<int32>({ 2, 0, 1 }));
			return true;
		}
		if ((C.Frames - 8) % 6 == 0)
		{
			if (S->Presses >= 4)
			{
				Test->AddError(TEXT("Dial never reached the target position"));
				return true;
			}
			C.Pawn->GetInteractor()->TryInteract();
			++S->Presses;
		}
		return false;
	});

	// Locked: the interactable still fires but the dial does not cycle.
	AddCheck(*R, TEXT("Lock the dial"), [S](FPuzzleCtx&) { S->Dial()->bLocked = true; });
	AddPress(*R, S, Test, TEXT("Locked dial press"), [](FPuzzleState& St) { return St.DialActor.Get(); }, [S, Test, DialOnlyOne](FPuzzleCtx&)
	{
		DialOnlyOne(1);
		Test->TestEqual(TEXT("No OnDialChanged while locked"), S->Sink->DialIndices.Num(), 3);
		Test->TestEqual(TEXT("CycleNext returns INDEX_NONE while locked"), S->Dial()->CycleNext(), static_cast<int32>(INDEX_NONE));
	});
	AddCheck(*R, TEXT("Unlock and cycle from Blueprint"), [S, Test, DialOnlyOne](FPuzzleCtx&)
	{
		S->Dial()->bLocked = false;
		Test->TestEqual(TEXT("CycleNext returns the new index"), S->Dial()->CycleNext(), 2);
		DialOnlyOne(2);
	});

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// 3. Route bot: sequence + dial providers, including a re-plan after the puzzle resets itself mid-run
// =====================================================================================================================
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBPuzzleRouteBotTest, "LastBell.Functional.Puzzles.RouteBotProviders",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBPuzzleRouteBotTest::RunTest(const FString& Parameters)
{
	FRunnerPtr R = StartSession(this);
	TSharedRef<FPuzzleState> S = MakeShared<FPuzzleState>();
	FAutomationTestBase* Test = this;

	AddSetupStep(*R, S, Test, [S, Test](FPuzzleCtx& C)
	{
		return SpawnSequenceRig(C.W, *S, Test) && SpawnDialRig(C.W, *S, Test, 0);
	});

	R->Add(TEXT("Bot solves the sequence (with one induced reset) and sets the dial"), [S, Test, &R = *R](FPuzzleCtx& C)
	{
		if (!S->Bot.IsValid())
		{
			FLBRouteBot::FConfig Config;
			Config.GoalTags = { S->Solved, S->Weight[2] };
			S->Bot = MakeShared<FLBRouteBot>(Test, Config);
		}
		// Sabotage once: while the bot is on step 2, throw a later step in. The puzzle resets itself and the bot must re-plan from step 1.
		ULBSequencePuzzleComponent* Seq = S->Seq();
		if (!S->bSabotaged && Seq && Seq->GetProgress() == 1)
		{
			S->bSabotaged = true;
			Note(TEXT("Sabotage: adding Candle.3 out of order"));
			ULBWorldStateSubsystem::Get(C.W)->AddState(S->Candle[2]);
		}
		switch (S->Bot->Tick())
		{
		case FLBRouteBot::EStatus::Failed:
			R.Abort(TEXT("Route bot failed (see [RouteBot] error above)"));
			return true;
		case FLBRouteBot::EStatus::Done:
			return true;
		default:
			return false;
		}
	}, 90.f);

	AddCheck(*R, TEXT("Both goals reached"), [S, Test](FPuzzleCtx&)
	{
		Test->TestTrue(TEXT("Sequence solved"), HasState(S->Solved));
		Test->TestTrue(TEXT("Dial reached position 3 (Weight.3)"), HasState(S->Weight[2]));
		Test->TestTrue(TEXT("The sabotage happened (the re-plan path was exercised)"), S->bSabotaged);
		Test->TestEqual(TEXT("Exactly the one induced failure"), S->Sink->FailedWith.Num(), 1);
		Test->TestEqual(TEXT("Solved once"), S->Sink->SolvedCount, 1);
		Test->TestEqual(TEXT("Dial index 2"), S->Dial() ? S->Dial()->GetCurrentIndex() : -2, 2);
	});

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// 4. Save mid-puzzle: 1 correct step, checkpoint, reload the map, the remaining steps solve it
// =====================================================================================================================
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBPuzzleSaveMidPuzzleTest, "LastBell.Functional.Puzzles.SaveMidPuzzle",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBPuzzleSaveMidPuzzleTest::RunTest(const FString& Parameters)
{
	FRunnerPtr R = StartSession(this);
	TSharedRef<FPuzzleState> S = MakeShared<FPuzzleState>();
	FAutomationTestBase* Test = this;

	AddSetupStep(*R, S, Test, [S, Test](FPuzzleCtx& C)
	{
		return SpawnSequenceRig(C.W, *S, Test) && SpawnDialRig(C.W, *S, Test, 1);
	});

	AddPress(*R, S, Test, TEXT("Candle 1"), CandleTarget(0));
	AddPress(*R, S, Test, TEXT("Dial press"), [](FPuzzleState& St) { return St.DialActor.Get(); });

	R->Add(TEXT("SaveCheckpoint mid-puzzle, then LoadLastCheckpoint"), [S, Test](FPuzzleCtx& C)
	{
		if (!C.bFirst || !C.Pawn)
		{
			return S->bLoadIssued && NewWorldReady(C, S->OldWorld);
		}
		Test->TestEqual(TEXT("One step taken before saving"), S->Seq()->GetProgress(), 1);
		Test->TestEqual(TEXT("Dial at index 2 before saving"), S->Dial()->GetCurrentIndex(), 2);
		ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(C.W);
		if (!Test->TestNotNull(TEXT("Save subsystem"), Save))
		{
			return true;
		}
		Test->TestTrue(TEXT("SaveCheckpoint"), Save->SaveCheckpoint(GCheckpoint, C.Pawn->GetActorTransform()));
		S->OldWorld = C.W;
		S->bLoadIssued = true;
		Test->TestTrue(TEXT("LoadLastCheckpoint accepted"), Save->LoadLastCheckpoint());
		return false;
	}, 90.f);

	// Fresh world: the runtime rigs are gone, so rebuild them. Their BeginPlay must derive everything from the restored tags.
	R->Add(TEXT("Rebuild the rigs in the reloaded world"), [S, Test, &R = *R](FPuzzleCtx& C)
	{
		if (!NewWorldReady(C, S->OldWorld))
		{
			return false;
		}
		Test->TestTrue(TEXT("Restored world state still has Candle.1"), HasState(S->Candle[0]));
		Test->TestFalse(TEXT("Restored world state has no Candle.2"), HasState(S->Candle[1]));
		Test->TestTrue(TEXT("Restored world state keeps the dial position (Weight.3)"), HasState(S->Weight[2]));
		S->Sink.Reset(NewObject<ULBTestSink>(GetTransientPackage()));
		if (!Test->TestTrue(TEXT("Floor spawned"), SpawnFloor(C.W)) || !SpawnSequenceRig(C.W, *S, Test) || !SpawnDialRig(C.W, *S, Test, 1))
		{
			R.Abort(TEXT("Rebuild failed"));
			return true;
		}
		Place(C.Pawn, GStartX, 0.f);
		return true;
	}, 60.f);
	AddSettle(*R, TEXT("Let the pawn settle"), 10);

	AddCheck(*R, TEXT("Progress and dial are derived from the loaded tags"), [S, Test](FPuzzleCtx& C)
	{
		Test->TestEqual(TEXT("Sequence resumes at step 1"), S->Seq()->GetProgress(), 1);
		Test->TestFalse(TEXT("Not solved"), S->Seq()->IsSolved());
		Test->TestEqual(TEXT("Dial keeps its saved position (not reset to InitialIndex)"), S->Dial()->GetCurrentIndex(), 2);
		Test->TestFalse(TEXT("Candle 1 still consumed"), Available(*S, 0, C.Pawn));
		Test->TestTrue(TEXT("Candle 2 available"), Available(*S, 1, C.Pawn));
		Test->TestTrue(TEXT("Candle 3 available"), Available(*S, 2, C.Pawn));
		Test->TestEqual(TEXT("No failure on load"), S->Sink->FailedWith.Num(), 0);
	});

	AddPress(*R, S, Test, TEXT("Candle 2 after load"), CandleTarget(1), [S, Test](FPuzzleCtx&)
	{
		Test->TestEqual(TEXT("Progress 2"), S->Seq()->GetProgress(), 2);
		Test->TestTrue(TEXT("OnStepAccepted(1)"), S->Sink->AcceptedSteps == TArray<int32>({ 1 }));
	});
	AddPress(*R, S, Test, TEXT("Candle 3 after load (solves)"), CandleTarget(2), [S, Test](FPuzzleCtx&)
	{
		Test->TestTrue(TEXT("Puzzle solved after finishing the remaining steps"), HasState(S->Solved));
		Test->TestEqual(TEXT("OnPuzzleSolved fired once"), S->Sink->SolvedCount, 1);
	});
	AddSettle(*R, TEXT("Settle"), 4);
	AddCheck(*R, TEXT("No failure, still solved"), [S, Test](FPuzzleCtx&)
	{
		Test->TestEqual(TEXT("No failure"), S->Sink->FailedWith.Num(), 0);
		Test->TestTrue(TEXT("Solved tag present"), HasState(S->Solved));
	});

	Enqueue(R);
	return true;
}

#endif
