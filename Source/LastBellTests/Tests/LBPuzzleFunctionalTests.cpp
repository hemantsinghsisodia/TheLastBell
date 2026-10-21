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
#include "Components/LightComponent.h"
#include "UObject/StructOnScope.h"
#include "UObject/UnrealType.h"
#include "EngineUtils.h"
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

	TSharedRef<FPuzzleRunner> StartSession(FAutomationTestBase* Test, const TCHAR* Map = GMap)
	{
		LBPie::ClearSlot();
		FAutomationEditorCommonUtils::LoadMap(Map);
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


// =====================================================================================================================
// 5. Blueprint puzzles (P4-BPTEST): BP_PuzzleCandle + BP_SequencePuzzle, BP_DialLever, BP_SmallBell on L_Test_Puzzles
// =====================================================================================================================
namespace
{
	const TCHAR* GBpMap = TEXT("/Game/LastBell/Maps/L_Test_Puzzles");
	const TCHAR* GBellClass = TEXT("/Game/LastBell/Blueprints/Puzzles/BP_SmallBell.BP_SmallBell_C");

	// ---- reflection helpers (the Blueprints expose their configuration as plain properties) -----------------------------

	bool BpReadTag(const UObject* O, const TCHAR* Name, FGameplayTag& Out)
	{
		const FStructProperty* P = O ? FindFProperty<FStructProperty>(O->GetClass(), Name) : nullptr;
		if (!P || P->Struct != FGameplayTag::StaticStruct())
		{
			return false;
		}
		Out = *P->ContainerPtrToValuePtr<FGameplayTag>(O);
		return true;
	}

	bool BpWriteTag(UObject* O, const TCHAR* Name, const FGameplayTag& In)
	{
		const FStructProperty* P = O ? FindFProperty<FStructProperty>(O->GetClass(), Name) : nullptr;
		if (!P || P->Struct != FGameplayTag::StaticStruct())
		{
			return false;
		}
		*P->ContainerPtrToValuePtr<FGameplayTag>(O) = In;
		return true;
	}

	bool BpReadFloat(const UObject* O, const TCHAR* Name, float& Out)
	{
		const FNumericProperty* P = O ? FindFProperty<FNumericProperty>(O->GetClass(), Name) : nullptr;
		if (!P || !P->IsFloatingPoint())
		{
			return false;
		}
		Out = static_cast<float>(P->GetFloatingPointPropertyValue(P->ContainerPtrToValuePtr<void>(O)));
		return true;
	}

	bool BpReadBool(const UObject* O, const TCHAR* Name, bool& Out)
	{
		const FBoolProperty* P = O ? FindFProperty<FBoolProperty>(O->GetClass(), Name) : nullptr;
		if (!P)
		{
			return false;
		}
		Out = P->GetPropertyValue(P->ContainerPtrToValuePtr<void>(O));
		return true;
	}

	/** Calls a no-argument Blueprint function by name. */
	bool BpCall(AActor* A, const TCHAR* Name)
	{
		UFunction* Fn = A ? A->FindFunction(FName(Name)) : nullptr;
		if (!Fn)
		{
			return false;
		}
		A->ProcessEvent(Fn, nullptr);
		return true;
	}

	/** BP_DialLever::PitchForIndex(int) -> float, found by name (case-insensitive) so a renamed pure function still resolves. */
	bool BpPitchForIndex(AActor* Lever, int32 Index, float& OutPitch)
	{
		UFunction* Fn = nullptr;
		for (TFieldIterator<UFunction> It(Lever->GetClass()); It; ++It)
		{
			if (It->GetName().Equals(TEXT("PitchForIndex"), ESearchCase::IgnoreCase))
			{
				Fn = *It;
				break;
			}
		}
		if (!Fn)
		{
			return false;
		}
		FStructOnScope Params(Fn);
		const FIntProperty* In = nullptr;
		const FNumericProperty* Out = nullptr;
		for (TFieldIterator<FProperty> It(Fn); It; ++It)
		{
			if (It->HasAnyPropertyFlags(CPF_ReturnParm))
			{
				Out = CastField<FNumericProperty>(*It);
			}
			else if (It->HasAnyPropertyFlags(CPF_Parm) && !In)
			{
				In = CastField<FIntProperty>(*It);
			}
		}
		if (!In || !Out || !Out->IsFloatingPoint())
		{
			return false;
		}
		In->SetPropertyValue_InContainer(Params.GetStructMemory(), Index);
		Lever->ProcessEvent(Fn, Params.GetStructMemory());
		OutPitch = static_cast<float>(Out->GetFloatingPointPropertyValue(Out->ContainerPtrToValuePtr<void>(Params.GetStructMemory())));
		return true;
	}

	// ---- component discovery ------------------------------------------------------------------------------------------

	void LogComponents(const AActor* A)
	{
		TInlineComponentArray<UActorComponent*> Comps(A);
		FString List;
		for (const UActorComponent* C : Comps)
		{
			const USceneComponent* Scene = Cast<USceneComponent>(C);
			List += FString::Printf(TEXT("\n    %s (%s)%s"), *C->GetName(), *C->GetClass()->GetName(),
				Scene ? *FString::Printf(TEXT(" visible=%d rel=%s attach=%s"), Scene->IsVisible(), *Scene->GetRelativeRotation().ToString(), *GetNameSafe(Scene->GetAttachParent())) : TEXT(""));
		}
		Note(FString::Printf(TEXT("Components of %s [%s]:%s"), *A->GetActorLabel(), *A->GetClass()->GetName(), *List));
	}

	USceneComponent* FindSceneByName(const AActor* A, std::initializer_list<const TCHAR*> Needles)
	{
		TInlineComponentArray<USceneComponent*> Comps(A);
		for (const TCHAR* Needle : Needles)
		{
			for (USceneComponent* C : Comps)
			{
				if (C->GetName().Contains(Needle, ESearchCase::IgnoreCase))
				{
					return C;
				}
			}
		}
		return nullptr;
	}

	bool IsShown(const USceneComponent* C)
	{
		if (!C || !C->IsVisible())
		{
			return false;
		}
		const UPrimitiveComponent* Prim = Cast<UPrimitiveComponent>(C);
		return !Prim || !Prim->bHiddenInGame;
	}

	TArray<USceneComponent*> FlameParts(const AActor* A)
	{
		TArray<USceneComponent*> Out;
		TInlineComponentArray<USceneComponent*> Comps(A);
		for (USceneComponent* C : Comps)
		{
			if (!Cast<ULightComponent>(C) && C->GetName().Contains(TEXT("flame"), ESearchCase::IgnoreCase))
			{
				Out.Add(C);
			}
		}
		return Out;
	}

	TArray<ULightComponent*> Lights(const AActor* A)
	{
		TArray<ULightComponent*> Out;
		TInlineComponentArray<ULightComponent*> Comps(A);
		Out.Append(Comps);
		return Out;
	}

	float AngleDeg(const FQuat& A, const FQuat& B) { return FMath::RadiansToDegrees(A.AngularDistance(B)); }

	// ---- state ------------------------------------------------------------------------------------------------------------

	struct FBpState
	{
		TStrongObjectPtr<ULBTestSink> Sink;
		TWeakObjectPtr<AActor> Candles[3];
		TWeakObjectPtr<AActor> SeqActor;
		TWeakObjectPtr<AActor> Lever;
		TWeakObjectPtr<AActor> Bell;
		TWeakObjectPtr<UWorld> OldWorld;

		FGameplayTag Step[3];
		FGameplayTag Solved;
		FGameplayTag BellTag;
		FGameplayTag LockTag;

		bool bLoadIssued = false;
		bool bLockPreset = false;
		int32 DialStart = INDEX_NONE;
		int32 DialBeforeSave = INDEX_NONE;
		float MoveDuration = 1.f;
		float SwingDuration = 1.f;
		float SwingDegrees = 0.f;

		double StrikeTime = 0.0;
		float BellMaxDev = 0.f;
		double BellLastDevTime = 0.0;
		FQuat BellRest = FQuat::Identity;

		ULBSequencePuzzleComponent* Seq() const { return SeqActor.IsValid() ? SeqActor->FindComponentByClass<ULBSequencePuzzleComponent>() : nullptr; }
		ULBDialComponent* Dial() const { return Lever.IsValid() ? Lever->FindComponentByClass<ULBDialComponent>() : nullptr; }
		ULBInteractableComponent* LeverInteract() const { return Lever.IsValid() ? Lever->FindComponentByClass<ULBInteractableComponent>() : nullptr; }
		ULBInteractableComponent* CandleInteract(int32 I) const { return Candles[I].IsValid() ? Candles[I]->FindComponentByClass<ULBInteractableComponent>() : nullptr; }
		USceneComponent* HandlePivot() const { return Lever.IsValid() ? FindSceneByName(Lever.Get(), { TEXT("HandlePivot"), TEXT("Pivot"), TEXT("Handle") }) : nullptr; }
		USceneComponent* BellPivot() const { return Bell.IsValid() ? FindSceneByName(Bell.Get(), { TEXT("BellPivot"), TEXT("Pivot"), TEXT("Swing") }) : nullptr; }
	};

	/** Finds the placed puzzle actors by class name. The candles are matched to the sequence's steps through their LitTag. */
	bool ResolveBpActors(UWorld* W, FBpState& S, FAutomationTestBase* Test, bool bLogComponents)
	{
		TArray<AActor*> CandleActors;
		for (TActorIterator<AActor> It(W); It; ++It)
		{
			const FString ClassName = It->GetClass()->GetName();
			if (ClassName.Contains(TEXT("BP_PuzzleCandle")))
			{
				CandleActors.Add(*It);
			}
			else if (ClassName.Contains(TEXT("BP_SequencePuzzle")))
			{
				S.SeqActor = *It;
			}
			else if (ClassName.Contains(TEXT("BP_DialLever")) && !S.Lever.IsValid())
			{
				S.Lever = *It;
			}
		}
		bool bOk = Test->TestEqual(TEXT("Three BP_PuzzleCandle placed"), CandleActors.Num(), 3);
		bOk &= Test->TestNotNull(TEXT("BP_SequencePuzzle placed"), S.SeqActor.Get());
		bOk &= Test->TestNotNull(TEXT("BP_DialLever placed"), S.Lever.Get());
		if (!bOk)
		{
			return false;
		}
		const ULBSequencePuzzleComponent* Seq = S.Seq();
		const ULBDialComponent* Dial = S.Dial();
		bOk &= Test->TestNotNull(TEXT("Sequence puzzle has a ULBSequencePuzzleComponent"), Seq);
		bOk &= Test->TestNotNull(TEXT("Lever has a ULBDialComponent"), Dial);
		if (!Seq || !Dial || !Test->TestEqual(TEXT("Sequence has 3 steps"), Seq->Steps.Num(), 3))
		{
			return false;
		}
		for (int32 i = 0; i < 3; ++i)
		{
			S.Step[i] = Seq->Steps[i];
			for (AActor* Candle : CandleActors)
			{
				FGameplayTag Lit;
				if (BpReadTag(Candle, TEXT("LitTag"), Lit) && Lit == S.Step[i])
				{
					S.Candles[i] = Candle;
				}
			}
			bOk &= Test->TestNotNull(*FString::Printf(TEXT("A candle with LitTag %s exists"), *S.Step[i].ToString()), S.Candles[i].Get());
			bOk &= Test->TestTrue(TEXT("Candle has an interactable"), S.CandleInteract(i) != nullptr);
		}
		S.Solved = Seq->SolvedTags.IsEmpty() ? FGameplayTag() : Seq->SolvedTags.First();
		bOk &= Test->TestTrue(TEXT("Sequence has a solved tag"), S.Solved.IsValid());
		bOk &= Test->TestTrue(TEXT("Lever has an interactable"), S.LeverInteract() != nullptr);
		BpReadFloat(S.Lever.Get(), TEXT("MoveDuration"), S.MoveDuration);
		if (bLogComponents)
		{
			if (S.Candles[0].IsValid()) { LogComponents(S.Candles[0].Get()); }
			LogComponents(S.SeqActor.Get());
			LogComponents(S.Lever.Get());
			Note(FString::Printf(TEXT("Lever: MoveDuration=%.3f InitialIndex=%d positions=%d"), S.MoveDuration, Dial->InitialIndex, Dial->PositionTags.Num()));
		}
		return bOk;
	}

	// ---- candle checks ----------------------------------------------------------------------------------------------------

	void CheckCandleVisual(FAutomationTestBase* Test, const AActor* Candle, bool bLit, const FString& Label)
	{
		const TArray<ULightComponent*> Ls = Lights(Candle);
		const TArray<USceneComponent*> Flames = FlameParts(Candle);
		Test->TestTrue(Label + TEXT(": has a light component"), Ls.Num() > 0);
		Test->TestTrue(Label + TEXT(": has a flame component"), Flames.Num() > 0);
		for (const ULightComponent* L : Ls)
		{
			Test->TestEqual(FString::Printf(TEXT("%s: light '%s' visible"), *Label, *L->GetName()), IsShown(L), bLit);
		}
		for (const USceneComponent* F : Flames)
		{
			Test->TestEqual(FString::Printf(TEXT("%s: flame '%s' visible"), *Label, *F->GetName()), IsShown(F), bLit);
		}
	}

	void CheckCandles(FBpState& S, FAutomationTestBase* Test, ALBCharacter* Pawn, bool bLit, bool bInteractable, const TCHAR* Phase)
	{
		for (int32 i = 0; i < 3; ++i)
		{
			const AActor* Candle = S.Candles[i].Get();
			if (!Test->TestNotNull(TEXT("Candle exists"), Candle))
			{
				continue;
			}
			const FString Label = FString::Printf(TEXT("%s candle %d (%s)"), Phase, i + 1, *S.Step[i].ToString());
			CheckCandleVisual(Test, Candle, bLit, Label);
			ULBInteractableComponent* Comp = S.CandleInteract(i);
			Test->TestEqual(Label + TEXT(": interactable available"), Comp && Comp->CanInteract(Pawn), bInteractable);
		}
	}

	// ---- standing in front of an actor ---------------------------------------------------------------------------------

	struct FStandState
	{
		TArray<FVector> Candidates;
		int32 Index = -1;
		int32 PlacedFrame = 0;
		FString LastHit;
	};

	bool FindFloorZ(UWorld* W, const FVector& From, const AActor* Ignore, float& OutZ)
	{
		FCollisionQueryParams Params(SCENE_QUERY_STAT(LBBpFloor), false, Ignore);
		FHitResult Hit;
		if (W->LineTraceSingleByChannel(Hit, From, From - FVector(0, 0, 4000.f), ECC_Visibility, Params) && !Hit.bStartPenetrating && Hit.ImpactNormal.Z > 0.6f)
		{
			OutZ = Hit.ImpactPoint.Z;
			return true;
		}
		return false;
	}

	/** Teleports the pawn around the target until the interactor's own sweep (from the controller's view point) hits the target. */
	void AddStandAndAim(FPuzzleRunner& R, const TSharedRef<FBpState>& S, FAutomationTestBase* Test, const FString& Label, TFunction<AActor*(FBpState&)> GetTarget)
	{
		TSharedRef<FStandState> St = MakeShared<FStandState>();
		R.Add(Label + TEXT(": stand and aim"), [S, St, Test, GetTarget, Label](FPuzzleCtx& C)
		{
			AActor* Target = GetTarget(*S);
			if (!C.Pawn || !Test->TestNotNull(*(Label + TEXT(": press target exists")), Target))
			{
				return true;
			}
			FVector Origin, Extent;
			Target->GetActorBounds(true, Origin, Extent);
			if (C.bFirst)
			{
				*St = FStandState();
				const float Radius = static_cast<float>(FMath::Max(Extent.X, Extent.Y));
				for (const float Dist : { 110.f, 150.f })
				{
					for (int32 k = 0; k < 8; ++k)
					{
						const FVector Dir = FRotator(0.f, k * 45.f, 0.f).Vector();
						float FloorZ;
						const FVector Col = Origin + Dir * (Radius + Dist);
						if (FindFloorZ(C.W, FVector(Col.X, Col.Y, Origin.Z + 60.f), C.Pawn, FloorZ))
						{
							St->Candidates.Add(FVector(Col.X, Col.Y, FloorZ + HalfHeight(C.Pawn) + 2.f));
						}
					}
				}
			}
			const ULBInteractorComponent* Interactor = C.Pawn->GetInteractor();
			if (St->Index >= 0 && C.Frames - St->PlacedFrame >= 6)
			{
				FVector ViewLoc;
				FRotator ViewRot;
				C.Pawn->GetController()->GetPlayerViewPoint(ViewLoc, ViewRot);
				FCollisionQueryParams Params(SCENE_QUERY_STAT(LBBpAim), false, C.Pawn);
				FHitResult Hit;
				if (C.W->SweepSingleByChannel(Hit, ViewLoc, ViewLoc + ViewRot.Vector() * Interactor->TraceDistance, FQuat::Identity, LB_TRACE_INTERACTION,
					FCollisionShape::MakeSphere(Interactor->TraceRadius), Params) && Hit.GetActor() == Target)
				{
					return true;
				}
				St->LastHit = Hit.GetActor() ? Hit.GetActor()->GetActorLabel() : FString(TEXT("nothing"));
			}
			if (C.Frames - St->PlacedFrame >= 6 || St->Index < 0)
			{
				if (++St->Index >= St->Candidates.Num())
				{
					Test->AddError(FString::Printf(TEXT("%s: no stand point reaches %s with the Interaction trace (last sweep hit %s, %d candidates). "
						"The mesh may not block the Interaction channel."), *Label, *Target->GetActorLabel(), *St->LastHit, St->Candidates.Num()));
					return true;
				}
				const FVector Loc = St->Candidates[St->Index];
				C.Pawn->SetActorLocation(Loc, false, nullptr, ETeleportType::TeleportPhysics);
				if (UCharacterMovementComponent* M = C.Pawn->GetCharacterMovement())
				{
					M->StopMovementImmediately();
				}
				const UCameraComponent* Cam = C.Pawn->FindComponentByClass<UCameraComponent>();
				const FVector Eye = Cam ? Cam->GetComponentLocation() : Loc + FVector(0, 0, 64.f);
				C.Pawn->GetController()->SetControlRotation((Origin - Eye).Rotation());
				St->PlacedFrame = C.Frames;
			}
			return false;
		}, 40.f);
	}

	void AddBpPress(FPuzzleRunner& R, const TSharedRef<FBpState>& S, FAutomationTestBase* Test, const FString& Label,
		TFunction<AActor*(FBpState&)> GetTarget, TFunction<void(FPuzzleCtx&)> SameFrameCheck = nullptr)
	{
		AddStandAndAim(R, S, Test, Label, GetTarget);
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

	TFunction<AActor*(FBpState&)> BpCandle(int32 I)
	{
		return [I](FBpState& S) { return S.Candles[I].Get(); };
	}

	void AddWaitSeconds(FPuzzleRunner& R, const FString& Name, float Seconds)
	{
		TSharedRef<double> Start = MakeShared<double>(0.0);
		R.Add(Name, [Start, Seconds](FPuzzleCtx& C)
		{
			if (C.bFirst)
			{
				*Start = C.W->GetTimeSeconds();
			}
			return C.W->GetTimeSeconds() - *Start >= Seconds && C.Frames >= 2;
		});
	}

	float HandlePitch(const FBpState& S)
	{
		const USceneComponent* H = S.HandlePivot();
		return H ? FRotator::NormalizeAxis(H->GetRelativeRotation().Pitch) : -9999.f;
	}

	float ExpectedPitch(FBpState& S, int32 Index)
	{
		float Pitch = 0.f;
		if (BpPitchForIndex(S.Lever.Get(), Index, Pitch))
		{
			return Pitch;
		}
		return (Index - 1) * 35.f; // documented fallback: -35 / 0 / +35
	}

	void CheckHandle(FBpState& S, FAutomationTestBase* Test, const FString& Label)
	{
		const int32 Index = S.Dial() ? S.Dial()->GetCurrentIndex() : -2;
		const float Expected = ExpectedPitch(S, Index);
		const float Actual = HandlePitch(S);
		Note(FString::Printf(TEXT("%s: dial index %d, handle pitch %.2f (expected %.2f)"), *Label, Index, Actual, Expected));
		Test->TestTrue(Label + TEXT(": the handle pivot component exists"), S.HandlePivot() != nullptr);
		Test->TestTrue(FString::Printf(TEXT("%s: handle pitch %.2f within 2 degrees of notch %.2f"), *Label, Actual, Expected), FMath::Abs(Actual - Expected) <= 2.f);
	}

	bool OpenSpawnPoint(UWorld* W, const ALBCharacter* Pawn, FVector& OutLoc)
	{
		for (const float Dist : { 350.f, 450.f, 550.f })
		{
			for (int32 k = 0; k < 8; ++k)
			{
				const FVector Dir = FRotator(0.f, k * 45.f, 0.f).Vector();
				const FVector Col = Pawn->GetActorLocation() + Dir * Dist;
				float FloorZ;
				if (!FindFloorZ(W, FVector(Col.X, Col.Y, Pawn->GetActorLocation().Z), Pawn, FloorZ))
				{
					continue;
				}
				FCollisionQueryParams Params(SCENE_QUERY_STAT(LBBpSpawn), false, Pawn);
				if (!W->OverlapAnyTestByChannel(FVector(Col.X, Col.Y, FloorZ + 120.f), FQuat::Identity, ECC_WorldStatic, FCollisionShape::MakeSphere(90.f), Params))
				{
					OutLoc = FVector(Col.X, Col.Y, FloorZ);
					return true;
				}
			}
		}
		return false;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBPuzzleBlueprintsTest, "LastBell.Functional.Puzzles.Blueprints",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBPuzzleBlueprintsTest::RunTest(const FString& Parameters)
{
	FRunnerPtr R = StartSession(this, GBpMap);
	TSharedRef<FBpState> S = MakeShared<FBpState>();
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, resolve placed puzzle actors"), [S, Test, &R = *R](FPuzzleCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 8)
		{
			return false;
		}
		S->Sink.Reset(NewObject<ULBTestSink>(GetTransientPackage()));
		S->BellTag = LBPie::Tag(TEXT("State.Tower.Bell.1"));
		if (!Test->TestTrue(TEXT("Tag State.Tower.Bell.1 exists"), S->BellTag.IsValid()) || !ResolveBpActors(C.W, *S, Test, true))
		{
			R.Abort(TEXT("Setup failed"));
			return true;
		}
		S->Seq()->OnPuzzleFailed.AddDynamic(S->Sink.Get(), &ULBTestSink::HandlePuzzleFailed);
		S->Seq()->OnPuzzleSolved.AddDynamic(S->Sink.Get(), &ULBTestSink::HandlePuzzleSolved);
		S->Dial()->OnDialChanged.AddDynamic(S->Sink.Get(), &ULBTestSink::HandleDialChanged);
		return true;
	}, 90.f);

	// ---- 1. candles --------------------------------------------------------------------------------------------------
	AddCheck(*R, TEXT("Candles at start: all unlit and interactable"), [S, Test](FPuzzleCtx& C)
	{
		CheckCandles(*S, Test, C.Pawn, false, true, TEXT("Start"));
		Test->TestFalse(TEXT("No solved tag at start"), HasState(S->Solved));
		Test->TestEqual(TEXT("Sequence progress 0"), S->Seq()->GetProgress(), 0);
	});

	AddBpPress(*R, S, Test, TEXT("Candle 1 (correct)"), BpCandle(0), [S, Test](FPuzzleCtx&)
	{
		Test->TestTrue(TEXT("Candle 1 step tag granted"), HasState(S->Step[0]));
	});
	AddSettle(*R, TEXT("Settle after candle 1"), 4);
	AddCheck(*R, TEXT("Candle 1 lit, others unlit"), [S, Test](FPuzzleCtx& C)
	{
		CheckCandleVisual(Test, S->Candles[0].Get(), true, TEXT("After step 1: candle 1"));
		CheckCandleVisual(Test, S->Candles[1].Get(), false, TEXT("After step 1: candle 2"));
		Test->TestFalse(TEXT("After step 1: candle 1 consumed"), S->CandleInteract(0) && S->CandleInteract(0)->CanInteract(C.Pawn));
	});
	AddBpPress(*R, S, Test, TEXT("Candle 3 (wrong)"), BpCandle(2));
	AddSettle(*R, TEXT("Let the deferred reset run"), 8);
	AddCheck(*R, TEXT("Wrong order: all unlit again, interactable again, OnPuzzleFailed fired"), [S, Test](FPuzzleCtx& C)
	{
		CheckCandles(*S, Test, C.Pawn, false, true, TEXT("After reset"));
		Test->TestEqual(TEXT("OnPuzzleFailed fired once"), S->Sink->FailedWith.Num(), 1);
		if (S->Sink->FailedWith.Num() == 1)
		{
			Test->TestEqual(TEXT("OnPuzzleFailed reports candle 3"), S->Sink->FailedWith[0], S->Step[2]);
		}
		Test->TestEqual(TEXT("Progress 0"), S->Seq()->GetProgress(), 0);
		Test->TestFalse(TEXT("Not solved"), HasState(S->Solved));
	});

	AddBpPress(*R, S, Test, TEXT("Candle 1"), BpCandle(0));
	AddBpPress(*R, S, Test, TEXT("Candle 2"), BpCandle(1));
	AddBpPress(*R, S, Test, TEXT("Candle 3 (solves)"), BpCandle(2), [S, Test](FPuzzleCtx&)
	{
		Test->TestTrue(TEXT("Solved tag added by the last candle"), HasState(S->Solved));
	});
	AddSettle(*R, TEXT("Settle after solving"), 8);
	AddCheck(*R, TEXT("Solved: all lit, none interactable"), [S, Test](FPuzzleCtx& C)
	{
		CheckCandles(*S, Test, C.Pawn, true, false, TEXT("Solved"));
		Test->TestTrue(TEXT("Solved tag present"), HasState(S->Solved));
		Test->TestEqual(TEXT("OnPuzzleSolved fired once"), S->Sink->SolvedCount, 1);
		Test->TestEqual(TEXT("Still exactly one failure"), S->Sink->FailedWith.Num(), 1);
		for (int32 i = 0; i < 3; ++i)
		{
			Test->TestTrue(TEXT("Step tag still present"), HasState(S->Step[i]));
		}
	});

	// ---- 2. dial lever -----------------------------------------------------------------------------------------------
	AddCheck(*R, TEXT("Dial at start: InitialIndex and matching handle pitch"), [S, Test](FPuzzleCtx&)
	{
		ULBDialComponent* Dial = S->Dial();
		S->DialStart = Dial->GetCurrentIndex();
		Test->TestEqual(TEXT("Dial starts at InitialIndex"), S->DialStart, Dial->InitialIndex);
		Test->TestEqual(TEXT("Dial has 3 positions"), Dial->PositionTags.Num(), 3);
		Test->TestTrue(TEXT("The lever interactable is enabled at start"), S->LeverInteract()->bEnabled);
		Test->TestFalse(TEXT("The dial is not locked at start"), Dial->bLocked);
		TArray<float> Notches;
		for (int32 i = 0; i < 3; ++i)
		{
			Notches.Add(ExpectedPitch(*S, i));
		}
		Note(FString::Printf(TEXT("Notch pitches per index: %.2f / %.2f / %.2f"), Notches[0], Notches[1], Notches[2]));
		TArray<float> Sorted = Notches;
		Sorted.Sort();
		Test->TestTrue(TEXT("Notches are -35 / 0 / +35 (any order)"),
			FMath::Abs(Sorted[0] + 35.f) <= 0.5f && FMath::Abs(Sorted[1]) <= 0.5f && FMath::Abs(Sorted[2] - 35.f) <= 0.5f);
		CheckHandle(*S, Test, TEXT("Dial at start"));
	});

	for (int32 Press = 1; Press <= 3; ++Press)
	{
		const FString Label = FString::Printf(TEXT("Lever press %d"), Press);
		AddBpPress(*R, S, Test, Label, [](FBpState& St) { return St.Lever.Get(); }, [S, Test, Press](FPuzzleCtx&)
		{
			const int32 Expected = (S->DialStart + Press) % 3;
			Test->TestEqual(TEXT("Dial index cycled immediately"), S->Dial()->GetCurrentIndex(), Expected);
			Test->TestTrue(TEXT("OnDialChanged fired with the new index"), S->Sink->DialIndices.Num() == Press && S->Sink->DialIndices.Last() == Expected);
			Test->TestTrue(TEXT("Exactly one position tag present"), HasState(S->Dial()->PositionTags[Expected]));
		});
		AddWaitSeconds(*R, Label + TEXT(": wait for the move"), S->MoveDuration + 0.35f);
		AddCheck(*R, Label + TEXT(": handle at the new notch"), [S, Test, Label](FPuzzleCtx&) { CheckHandle(*S, Test, Label); });
	}
	AddCheck(*R, TEXT("Dial wrapped around"), [S, Test](FPuzzleCtx&)
	{
		Test->TestEqual(TEXT("Three presses return to the start index (wrap)"), S->Dial()->GetCurrentIndex(), S->DialStart);
		S->DialBeforeSave = S->Dial()->GetCurrentIndex();
	});

	// Lock: if the placed lever has no LockTag, set one by reflection and refresh; if it has one, drive it through world state.
	AddCheck(*R, TEXT("Lock the lever"), [S, Test](FPuzzleCtx& C)
	{
		FGameplayTag Lock;
		Test->TestTrue(TEXT("BP_DialLever exposes a LockTag property"), BpReadTag(S->Lever.Get(), TEXT("LockTag"), Lock));
		S->bLockPreset = Lock.IsValid();
		if (!S->bLockPreset)
		{
			Lock = S->Solved;
			Test->TestTrue(TEXT("LockTag set by reflection"), BpWriteTag(S->Lever.Get(), TEXT("LockTag"), Lock));
		}
		S->LockTag = Lock;
		Note(FString::Printf(TEXT("Lever LockTag %s (%s on the placed instance)"), *Lock.ToString(), S->bLockPreset ? TEXT("preset") : TEXT("empty, set by the test")));
		ULBWorldStateSubsystem* WS = ULBWorldStateSubsystem::Get(C.W);
		if (S->bLockPreset)
		{
			// Event-driven path: remove the tag, then add it again.
			WS->RemoveState(Lock);
		}
		else
		{
			Test->TestTrue(TEXT("RefreshLock exists on the lever"), BpCall(S->Lever.Get(), TEXT("RefreshLock")));
		}
	});
	AddSettle(*R, TEXT("Settle after lock setup"), 3);
	AddCheck(*R, TEXT("Lock state"), [S, Test](FPuzzleCtx& C)
	{
		ULBWorldStateSubsystem* WS = ULBWorldStateSubsystem::Get(C.W);
		if (S->bLockPreset)
		{
			Test->TestTrue(TEXT("Preset lock removed: interactable enabled"), S->LeverInteract()->bEnabled);
			Test->TestFalse(TEXT("Preset lock removed: dial unlocked"), S->Dial()->bLocked);
			WS->AddState(S->LockTag);
		}
	});
	AddSettle(*R, TEXT("Let the lock apply"), 3);
	AddCheck(*R, TEXT("Lever is locked"), [S, Test](FPuzzleCtx& C)
	{
		Test->TestTrue(TEXT("LockTag is present"), HasState(S->LockTag));
		Test->TestFalse(TEXT("Interactable disabled by the lock"), S->LeverInteract()->bEnabled);
		Test->TestFalse(TEXT("CanInteract false when locked"), S->LeverInteract()->CanInteract(C.Pawn));
		Test->TestTrue(TEXT("Dial locked"), S->Dial()->bLocked);
	});
	AddBpPress(*R, S, Test, TEXT("Locked lever press"), [](FBpState& St) { return St.Lever.Get(); }, [S, Test](FPuzzleCtx&)
	{
		Test->TestEqual(TEXT("Locked: index unchanged"), S->Dial()->GetCurrentIndex(), S->DialBeforeSave);
		Test->TestEqual(TEXT("Locked: no further OnDialChanged"), S->Sink->DialIndices.Num(), 3);
	});

	// The lock follows world state through the Blueprint's own OnStateChanged binding: remove the tag -> unlocked, add it -> locked.
	AddCheck(*R, TEXT("Remove the lock tag"), [S](FPuzzleCtx& C) { ULBWorldStateSubsystem::Get(C.W)->RemoveState(S->LockTag); });
	AddSettle(*R, TEXT("Let the unlock apply"), 3);
	AddCheck(*R, TEXT("Lever unlocked by the event, then relock"), [S, Test](FPuzzleCtx& C)
	{
		Test->TestTrue(TEXT("Lock tag removed: interactable enabled again (event-driven)"), S->LeverInteract()->bEnabled);
		Test->TestFalse(TEXT("Lock tag removed: dial unlocked (event-driven)"), S->Dial()->bLocked);
		ULBWorldStateSubsystem::Get(C.W)->AddState(S->LockTag);
	});
	AddSettle(*R, TEXT("Let the relock apply"), 3);
	AddCheck(*R, TEXT("Lever locked again by the event"), [S, Test](FPuzzleCtx& C)
	{
		Test->TestFalse(TEXT("Lock tag re-added: interactable disabled (event-driven)"), S->LeverInteract()->bEnabled);
		Test->TestTrue(TEXT("Lock tag re-added: dial locked (event-driven)"), S->Dial()->bLocked);
		Test->TestTrue(TEXT("Solved tag is present again for the save"), HasState(S->Solved));
	});

	// ---- 3. bell ------------------------------------------------------------------------------------------------------
	AddCheck(*R, TEXT("Spawn a BP_SmallBell"), [S, Test, &R = *R](FPuzzleCtx& C)
	{
		UClass* Cls = LoadClass<AActor>(nullptr, GBellClass);
		FVector Loc;
		if (!Test->TestNotNull(TEXT("BP_SmallBell class loads"), Cls) || !Test->TestTrue(TEXT("An open spot near the pawn exists"), OpenSpawnPoint(C.W, C.Pawn, Loc)))
		{
			R.Abort(TEXT("Bell spawn failed"));
			return;
		}
		const FTransform T(FRotator(0.f, (C.Pawn->GetActorLocation() - Loc).Rotation().Yaw, 0.f), Loc);
		AActor* Bell = C.W->SpawnActorDeferred<AActor>(Cls, T, nullptr, nullptr, ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
		if (!Test->TestNotNull(TEXT("Bell spawned"), Bell) || !Test->TestTrue(TEXT("StruckTag set"), BpWriteTag(Bell, TEXT("StruckTag"), S->BellTag)))
		{
			R.Abort(TEXT("Bell spawn failed"));
			return;
		}
		Bell->FinishSpawning(T);
		S->Bell = Bell;
		BpReadFloat(Bell, TEXT("SwingDuration"), S->SwingDuration);
		BpReadFloat(Bell, TEXT("SwingDegrees"), S->SwingDegrees);
		LogComponents(Bell);
		Note(FString::Printf(TEXT("Bell at %s: SwingDuration=%.3f SwingDegrees=%.2f"), *Loc.ToString(), S->SwingDuration, S->SwingDegrees));
		Test->TestFalse(TEXT("Bell tag not present before the strike"), HasState(S->BellTag));
		Test->TestTrue(TEXT("The bell has a swinging pivot component"), S->BellPivot() != nullptr);
		Test->TestTrue(TEXT("The bell has an interactable"), Bell->FindComponentByClass<ULBInteractableComponent>() != nullptr);
		if (const USceneComponent* P = S->BellPivot())
		{
			S->BellRest = P->GetRelativeRotation().Quaternion();
		}
	});
	AddSettle(*R, TEXT("Let the bell settle"), 3);
	AddBpPress(*R, S, Test, TEXT("Strike bell"), [](FBpState& St) { return St.Bell.Get(); }, [S, Test](FPuzzleCtx& C)
	{
		Test->TestTrue(TEXT("Bell StruckTag added on strike"), HasState(S->BellTag));
		S->StrikeTime = C.W->GetTimeSeconds();
		S->BellMaxDev = 0.f;
		S->BellLastDevTime = 0.0;
	});
	R->Add(TEXT("Watch the bell swing and return to rest"), [S, Test](FPuzzleCtx& C)
	{
		const USceneComponent* P = S->BellPivot();
		if (!P)
		{
			return true;
		}
		const double T = C.W->GetTimeSeconds() - S->StrikeTime;
		const float Dev = AngleDeg(P->GetRelativeRotation().Quaternion(), S->BellRest);
		S->BellMaxDev = FMath::Max(S->BellMaxDev, Dev);
		if (Dev > 0.5f)
		{
			S->BellLastDevTime = T;
		}
		if (T < 1.55)
		{
			return false;
		}
		Note(FString::Printf(TEXT("Bell swing: max deviation %.2f deg, last deviated at t=%.2fs, final deviation %.3f deg"), S->BellMaxDev, S->BellLastDevTime, Dev));
		Test->TestTrue(FString::Printf(TEXT("The bell swung (max deviation %.2f deg > 1)"), S->BellMaxDev), S->BellMaxDev > 1.f);
		Test->TestTrue(FString::Printf(TEXT("The bell is at rest within 1.5s (last deviated at %.2fs)"), S->BellLastDevTime), S->BellLastDevTime < 1.5);
		Test->TestTrue(FString::Printf(TEXT("Final bell rotation is the rest rotation (%.3f deg off)"), Dev), Dev < 0.5f);
		return true;
	}, 30.f);

	// ---- 4. save / reload --------------------------------------------------------------------------------------------
	R->Add(TEXT("SaveCheckpoint with the candles solved, then LoadLastCheckpoint"), [S, Test](FPuzzleCtx& C)
	{
		if (!C.bFirst || !C.Pawn)
		{
			return S->bLoadIssued && NewWorldReady(C, S->OldWorld);
		}
		Test->TestTrue(TEXT("Candles solved before saving"), HasState(S->Solved));
		S->DialBeforeSave = S->Dial()->GetCurrentIndex();
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

	// The very first frame the new world is ready: the candles must already be lit (snap, no animation, no events needed).
	AddCheck(*R, TEXT("After reload: candles snap lit, CandlesSolved present"), [S, Test](FPuzzleCtx& C)
	{
		Test->TestTrue(TEXT("The reloaded world is a new world"), C.W != S->OldWorld.Get());
		S->Candles[0].Reset();
		S->Candles[1].Reset();
		S->Candles[2].Reset();
		S->SeqActor.Reset();
		S->Lever.Reset();
		if (!ResolveBpActors(C.W, *S, Test, false))
		{
			return;
		}
		Test->TestTrue(TEXT("CandlesSolved still present after reload"), HasState(S->Solved));
		CheckCandles(*S, Test, C.Pawn, true, false, TEXT("Reloaded"));
		Test->TestTrue(TEXT("The sequence puzzle comes back solved/inert"), S->Seq()->IsSolved());
		Test->TestEqual(TEXT("No puzzle failure after the reload"), S->Seq()->GetProgress(), 3);
		const int32 Index = S->Dial()->GetCurrentIndex();
		Test->TestEqual(TEXT("Dial keeps its saved position"), Index, S->DialBeforeSave);
		CheckHandle(*S, Test, TEXT("Reloaded dial"));
	});

	Enqueue(R);
	return true;
}

#endif
