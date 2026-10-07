#include "Tests/LBRouteBot.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Editor.h"
#include "Tests/AutomationEditorCommon.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/LocalPlayer.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "EnhancedInputSubsystems.h"
#include "InputActionValue.h"
#include "Character/LBCandleComponent.h"
#include "Character/LBCharacter.h"
#include "Character/LBFootstepComponent.h"
#include "Character/LBInspectionComponent.h"
#include "Character/LBPlayerTuningData.h"
#include "Components/LBInspectableComponent.h"
#include "Components/LBInteractableComponent.h"
#include "Components/LBInteractorComponent.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "Tests/LBTestSink.h"
#include "UObject/StrongObjectPtr.h"
#include "LBLog.h"

// Phase 3 player-feel functional tests. Each test runs one PIE session on L_Test_MicroSlice (BP_LBGameMode ->
// BP_LBCharacter). Movement tests run on a large flat test floor spawned far below the level so they never depend
// on level geometry, and drive the pawn through the real Enhanced Input path (injected Move / Sprint / Crouch
// actions each frame). All expected numbers come from the pawn's own tuning asset.

namespace
{
	const TCHAR* GFeelMap = TEXT("/Game/LastBell/Maps/L_Test_MicroSlice");
	const TCHAR* GNoteClassPath = TEXT("/Game/LastBell/Blueprints/Interactables/BP_Inspectable_Note.BP_Inspectable_Note_C");
	const TCHAR* GTagInteractableClassPath = TEXT("/Game/LastBell/Blueprints/Interactables/BP_TagInteractable.BP_TagInteractable_C");
	const TCHAR* GKeepTagName = TEXT("State.Test.Door1Open");

	constexpr float GFloorTopZ = -20000.f;
	constexpr float GStartX = -6000.f;
	constexpr float GSpeedTolerance = 0.08f;

	void Note(const FString& Text)
	{
		UE_LOG(LogLB, Display, TEXT("[PlayerFeel] %s"), *Text);
	}

	struct FFeelInput
	{
		FVector2D Move = FVector2D::ZeroVector;
		bool bSprint = false;
		bool bCrouch = false;
	};

	struct FStepCtx
	{
		UWorld* W = nullptr;
		ALBCharacter* Pawn = nullptr;
		FFeelInput& Input;
		double Now = 0.0;     // world time
		double Elapsed = 0.0; // world seconds since the step began
		int32 Frames = 0;
		bool bFirst = false;
	};

	/** Shared scratch state for the lambdas of one test. */
	struct FState
	{
		TStrongObjectPtr<ULBTestSink> Sink;

		FVector P0 = FVector::ZeroVector;
		double T0 = 0.0;
		bool bMarked = false;
		float StandEye = 0.f;
		float StandHalf = 0.f;

		// samples
		double Sum = 0.0;
		int32 N = 0;
		float Max = 0.f;
		float IdleMean = 0.f;

		// footsteps
		int32 StepCount = 0;
		float Distance = 0.f;

		// inspection
		TWeakObjectPtr<AActor> Item;
		FTransform ItemOriginal;
		FGameplayTagContainer StateBefore;
		FVector PawnBefore = FVector::ZeroVector;
		double LastTry = -1.0;
		bool bCrouchSeen = false;

		void ResetSamples()
		{
			Sum = 0.0;
			N = 0;
			Max = 0.f;
		}
		float Mean() const { return N > 0 ? static_cast<float>(Sum / N) : 0.f; }
	};

	class FFeelRunner : public IAutomationLatentCommand
	{
	public:
		using FStepFn = TFunction<bool(FStepCtx&)>;

		explicit FFeelRunner(FAutomationTestBase* InTest) : Test(InTest) {}

		void Add(const TCHAR* Name, FStepFn Fn, float WallTimeout = 40.f)
		{
			Steps.Add({ Name, WallTimeout, MoveTemp(Fn) });
		}

		virtual bool Update() override
		{
			if (bTearingDown)
			{
				return TickTeardown();
			}
			if (StepIndex >= Steps.Num())
			{
				BeginTeardown();
				return false;
			}

			UWorld* W = LBPie::World();
			ALBCharacter* P = LBPie::Pawn();
			FStep& Step = Steps[StepIndex];
			if (!bEntered)
			{
				if (StepIndex > 0 && (!W || !P))
				{
					Test->AddError(FString::Printf(TEXT("Step '%s': PIE world or pawn is gone"), *Step.Name));
					BeginTeardown();
					return false;
				}
				bEntered = true;
				Frames = 0;
				WallStart = FPlatformTime::Seconds();
				WorldStart = W ? W->GetTimeSeconds() : 0.0;
				ErrorsAtStart = ErrCount();
				Note(FString::Printf(TEXT("STEP %d begin: %s"), StepIndex + 1, *Step.Name));
			}

			FStepCtx Ctx{ W, P, Input };
			Ctx.Now = W ? W->GetTimeSeconds() : 0.0;
			Ctx.Elapsed = Ctx.Now - WorldStart;
			Ctx.Frames = Frames;
			Ctx.bFirst = (Frames == 0);
			++Frames;

			const bool bDone = Step.Fn(Ctx);
			if (P)
			{
				Inject(P);
			}

			const bool bTimedOut = !bDone && (FPlatformTime::Seconds() - WallStart) > Step.Timeout;
			if (bDone || bTimedOut)
			{
				if (bTimedOut)
				{
					Test->AddError(FString::Printf(TEXT("Step '%s' timed out after %.0fs"), *Step.Name, Step.Timeout));
				}
				Note(FString::Printf(TEXT("STEP %d %s: %s"), StepIndex + 1, ErrCount() == ErrorsAtStart ? TEXT("PASS") : TEXT("FAIL"), *Step.Name));
				if (bTimedOut)
				{
					BeginTeardown();
					return false;
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

		/** Re-sent every frame: injected input only lives for one input tick. Releasing = not injecting. */
		void Inject(ALBCharacter* P)
		{
			const APlayerController* PC = Cast<APlayerController>(P->GetController());
			const ULocalPlayer* LP = PC ? PC->GetLocalPlayer() : nullptr;
			UEnhancedInputLocalPlayerSubsystem* Subsystem = LP ? LP->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>() : nullptr;
			if (!Subsystem)
			{
				return;
			}
			const TArray<UInputModifier*> NoModifiers;
			const TArray<UInputTrigger*> NoTriggers;
			if (!Input.Move.IsNearlyZero() && P->MoveAction)
			{
				Subsystem->InjectInputForAction(P->MoveAction, FInputActionValue(Input.Move), NoModifiers, NoTriggers);
			}
			if (Input.bSprint && P->SprintAction)
			{
				Subsystem->InjectInputForAction(P->SprintAction, FInputActionValue(true), NoModifiers, NoTriggers);
			}
			if (Input.bCrouch && P->CrouchAction)
			{
				Subsystem->InjectInputForAction(P->CrouchAction, FInputActionValue(true), NoModifiers, NoTriggers);
			}
		}

		void BeginTeardown()
		{
			bTearingDown = true;
			Input = FFeelInput();
			TeardownStart = FPlatformTime::Seconds();
			if (GEditor && LBPie::World())
			{
				GEditor->RequestEndPlayMap();
			}
			LBPie::ClearSlot();
		}

		bool TickTeardown()
		{
			return !LBPie::World() || (FPlatformTime::Seconds() - TeardownStart) > 30.0;
		}

		FAutomationTestBase* Test;
		TArray<FStep> Steps;
		FFeelInput Input;
		int32 StepIndex = 0;
		int32 Frames = 0;
		bool bEntered = false;
		bool bTearingDown = false;
		double WallStart = 0.0;
		double WorldStart = 0.0;
		double TeardownStart = 0.0;
		int32 ErrorsAtStart = 0;
	};

	// ---- helpers ------------------------------------------------------------------------------------------------

	float HalfHeight(const ALBCharacter* P) { return P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight(); }

	UCameraComponent* Camera(const ALBCharacter* P) { return P->FindComponentByClass<UCameraComponent>(); }

	/** Eye height above the floor under the feet. */
	float EyeAboveFeet(const ALBCharacter* P)
	{
		const UCameraComponent* Cam = Camera(P);
		if (!Cam)
		{
			return 0.f;
		}
		return static_cast<float>(Cam->GetComponentLocation().Z - (P->GetActorLocation().Z - HalfHeight(P)));
	}

	float Speed2D(const ALBCharacter* P) { return static_cast<float>(P->GetVelocity().Size2D()); }

	bool OnGround(const ALBCharacter* P)
	{
		const UCharacterMovementComponent* M = P->GetCharacterMovement();
		return M && M->IsMovingOnGround();
	}

	/** Stands the pawn on the test floor at X facing +X, at rest. Keeps the current crouch state. */
	void Place(ALBCharacter* P, float X)
	{
		const float Z = GFloorTopZ + HalfHeight(P) + 0.1f;
		P->SetActorLocationAndRotation(FVector(X, 0.f, Z), FRotator::ZeroRotator, false, nullptr, ETeleportType::TeleportPhysics);
		if (UCharacterMovementComponent* M = P->GetCharacterMovement())
		{
			M->StopMovementImmediately();
		}
		if (AController* C = P->GetController())
		{
			C->SetControlRotation(FRotator::ZeroRotator);
		}
	}

	bool PctWithin(float Measured, float Expected, float Pct)
	{
		return FMath::Abs(Measured - Expected) <= Expected * Pct;
	}

	/** Tests the pawn's wiring and spawns the floor. Returns false when the pawn cannot be driven. */
	bool SpawnFloor(UWorld* W)
	{
		UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
		if (!Cube)
		{
			return false;
		}
		// 100 cm cube scaled to 20000 x 6000 x 200: the top face sits at GFloorTopZ.
		AStaticMeshActor* Floor = W->SpawnActor<AStaticMeshActor>(FVector(0.f, 0.f, GFloorTopZ - 100.f), FRotator::ZeroRotator);
		if (!Floor)
		{
			return false;
		}
		Floor->SetMobility(EComponentMobility::Movable);
		Floor->GetStaticMeshComponent()->SetStaticMesh(Cube);
		Floor->SetActorScale3D(FVector(200.f, 60.f, 2.f));
		return true;
	}

	void AddSetupSteps(FFeelRunner& R, const TSharedRef<FState>& S, FAutomationTestBase* Test)
	{
		R.Add(TEXT("PIE ready, test floor"), [S, Test](FStepCtx& C)
		{
			if (!LBPie::WorldReady() || C.Frames < 5)
			{
				return false;
			}
			Test->TestNotNull(TEXT("BP_LBCharacter has a Tuning asset (DA_PlayerTuning)"), C.Pawn->Tuning.Get());
			Test->TestNotNull(TEXT("BP_LBCharacter MoveAction"), C.Pawn->MoveAction.Get());
			Test->TestNotNull(TEXT("BP_LBCharacter SprintAction"), C.Pawn->SprintAction.Get());
			Test->TestNotNull(TEXT("BP_LBCharacter CrouchAction"), C.Pawn->CrouchAction.Get());
			Test->TestTrue(TEXT("Spawned the flat test floor"), SpawnFloor(C.W));
			Place(C.Pawn, GStartX);
			return true;
		}, 60.f);

		R.Add(TEXT("Settle on the floor"), [S, Test](FStepCtx& C)
		{
			if (C.Elapsed < 0.6 || !OnGround(C.Pawn))
			{
				return false;
			}
			S->StandEye = EyeAboveFeet(C.Pawn);
			S->StandHalf = HalfHeight(C.Pawn);
			Note(FString::Printf(TEXT("standing eye height above feet %.2f, capsule half height %.2f"), S->StandEye, S->StandHalf));
			return true;
		});
	}

	void AddStopStep(FFeelRunner& R, const TCHAR* Name)
	{
		R.Add(Name, [](FStepCtx& C)
		{
			C.Input = FFeelInput();
			return C.Elapsed >= 0.4 && Speed2D(C.Pawn) < 5.f;
		});
	}

	TSharedPtr<FFeelRunner> StartSession(FAutomationTestBase* Test)
	{
		LBPie::ClearSlot();
		FAutomationEditorCommonUtils::LoadMap(GFeelMap);
		FRequestPlaySessionParams PlayParams;
		PlayParams.WorldType = EPlaySessionWorldType::PlayInEditor;
		GEditor->RequestPlaySession(PlayParams);
		return MakeShared<FFeelRunner>(Test);
	}

	void Enqueue(const TSharedPtr<FFeelRunner>& Runner)
	{
		FAutomationTestFramework::Get().EnqueueLatentCommand(Runner);
	}

	const TCHAR* GaitName(ELBGait Gait)
	{
		switch (Gait)
		{
		case ELBGait::Walk: return TEXT("Walk");
		case ELBGait::Sprint: return TEXT("Sprint");
		case ELBGait::Crouch: return TEXT("Crouch");
		default: return TEXT("Idle");
		}
	}

	void DriveInput(FFeelInput& Input, ELBGait Gait)
	{
		Input.Move = FVector2D(0.0, 1.0);
		Input.bSprint = (Gait == ELBGait::Sprint);
		Input.bCrouch = (Gait == ELBGait::Crouch);
	}
}

// =====================================================================================================================
// 1. Gaits
// =====================================================================================================================
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBFeelGaitsTest, "LastBell.Functional.PlayerFeel.Gaits",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBFeelGaitsTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FFeelRunner> R = StartSession(this);
	const TSharedRef<FState> S = MakeShared<FState>();
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, S, Test);

	for (const ELBGait Gait : { ELBGait::Walk, ELBGait::Sprint })
	{
		R->Add(*FString::Printf(TEXT("Drive %s for 1.5s"), GaitName(Gait)), [S, Test, Gait](FStepCtx& C)
		{
			if (C.bFirst)
			{
				Place(C.Pawn, GStartX);
				S->bMarked = false;
			}
			DriveInput(C.Input, Gait);
			if (!S->bMarked && C.Elapsed >= 0.5)
			{
				S->bMarked = true;
				S->P0 = C.Pawn->GetActorLocation();
				S->T0 = C.Now;
			}
			if (C.Elapsed < 1.5)
			{
				return false;
			}
			const ULBPlayerTuningData& T = C.Pawn->GetTuning();
			const float Expected = T.GetGaitSpeed(Gait);
			const float Measured = static_cast<float>(FVector::DistXY(S->P0, C.Pawn->GetActorLocation()) / (C.Now - S->T0));
			Note(FString::Printf(TEXT("%s: measured %.1f cm/s, expected %.1f (%.1f%%), gait=%s, camera FOV %.2f"), GaitName(Gait), Measured, Expected,
				100.f * (Measured - Expected) / Expected, GaitName(C.Pawn->GetGait()), Camera(C.Pawn) ? Camera(C.Pawn)->FieldOfView : 0.f));
			Test->TestTrue(FString::Printf(TEXT("%s speed %.1f within 8%% of tuning %.1f"), GaitName(Gait), Measured, Expected),
				PctWithin(Measured, Expected, GSpeedTolerance));
			Test->TestEqual(*FString::Printf(TEXT("%s gait reported"), GaitName(Gait)), static_cast<int32>(C.Pawn->GetGait()), static_cast<int32>(Gait));
			return true;
		});
		AddStopStep(*R, *FString::Printf(TEXT("Stop after %s"), GaitName(Gait)));
	}

	R->Add(TEXT("Drive Crouch for 1.5s, capsule and eye height"), [S, Test](FStepCtx& C)
	{
		if (C.bFirst)
		{
			Place(C.Pawn, GStartX);
			S->bMarked = false;
		}
		DriveInput(C.Input, ELBGait::Crouch);
		if (!S->bMarked && C.Elapsed >= 0.5)
		{
			S->bMarked = true;
			S->P0 = C.Pawn->GetActorLocation();
			S->T0 = C.Now;
		}
		if (C.Elapsed < 1.5)
		{
			return false;
		}
		const ULBPlayerTuningData& T = C.Pawn->GetTuning();
		const float Measured = static_cast<float>(FVector::DistXY(S->P0, C.Pawn->GetActorLocation()) / (C.Now - S->T0));
		const float Half = HalfHeight(C.Pawn);
		const float Eye = EyeAboveFeet(C.Pawn);
		const float Drop = S->StandEye - Eye;
		const float ExpectedDrop = S->StandHalf - T.CrouchedHalfHeight;
		Note(FString::Printf(TEXT("Crouch: measured %.1f cm/s, expected %.1f; capsule half %.2f (tuning %.2f); eye %.2f vs standing %.2f (drop %.2f, expected %.2f)"),
			Measured, T.CrouchSpeed, Half, T.CrouchedHalfHeight, Eye, S->StandEye, Drop, ExpectedDrop));
		Test->TestTrue(FString::Printf(TEXT("Crouch speed %.1f within 8%% of tuning %.1f"), Measured, T.CrouchSpeed), PctWithin(Measured, T.CrouchSpeed, GSpeedTolerance));
		Test->TestTrue(TEXT("Pawn is crouched"), C.Pawn->bIsCrouched);
		Test->TestEqual(TEXT("Crouch gait reported"), static_cast<int32>(C.Pawn->GetGait()), static_cast<int32>(ELBGait::Crouch));
		Test->TestTrue(FString::Printf(TEXT("Crouched capsule half height %.2f equals tuning %.2f"), Half, T.CrouchedHalfHeight), FMath::IsNearlyEqual(Half, T.CrouchedHalfHeight, 0.5f));
		Test->TestTrue(FString::Printf(TEXT("Camera eye ends lower when crouched (%.2f < %.2f)"), Eye, S->StandEye), Eye < S->StandEye - 1.f);
		Test->TestTrue(FString::Printf(TEXT("Eye drop %.2f is about the capsule shrink %.2f"), Drop, ExpectedDrop), FMath::IsNearlyEqual(Drop, ExpectedDrop, 3.f));
		return true;
	});

	R->Add(TEXT("Release crouch: stands back up"), [S, Test](FStepCtx& C)
	{
		C.Input = FFeelInput();
		if (C.Elapsed < 0.8)
		{
			return false;
		}
		Test->TestFalse(TEXT("Not crouched after release"), C.Pawn->bIsCrouched);
		Test->TestTrue(FString::Printf(TEXT("Standing half height %.2f restored (%.2f)"), HalfHeight(C.Pawn), S->StandHalf), FMath::IsNearlyEqual(HalfHeight(C.Pawn), S->StandHalf, 0.5f));
		Test->TestTrue(FString::Printf(TEXT("Standing eye %.2f restored (%.2f)"), EyeAboveFeet(C.Pawn), S->StandEye), FMath::IsNearlyEqual(EyeAboveFeet(C.Pawn), S->StandEye, 2.f));
		return true;
	});

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// 2. Footsteps
// =====================================================================================================================
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBFeelFootstepsTest, "LastBell.Functional.PlayerFeel.Footsteps",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBFeelFootstepsTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FFeelRunner> R = StartSession(this);
	const TSharedRef<FState> S = MakeShared<FState>();
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, S, Test);

	for (const ELBGait Gait : { ELBGait::Walk, ELBGait::Sprint, ELBGait::Crouch })
	{
		// Let the pawn come to rest on the floor first, so the landing from the teleport is not counted.
		R->Add(*FString::Printf(TEXT("%s: place and settle"), GaitName(Gait)), [S, Gait](FStepCtx& C)
		{
			if (C.bFirst)
			{
				C.Input = FFeelInput();
				C.Input.bCrouch = (Gait == ELBGait::Crouch);
				Place(C.Pawn, GStartX);
			}
			C.Input.bCrouch = (Gait == ELBGait::Crouch);
			return C.Elapsed >= 0.6 && OnGround(C.Pawn) && Speed2D(C.Pawn) < 5.f && (Gait != ELBGait::Crouch || C.Pawn->bIsCrouched);
		});

		R->Add(*FString::Printf(TEXT("%s: walk 10 m, count OnFootstep"), GaitName(Gait)), [S, Test, Gait](FStepCtx& C)
		{
			ULBFootstepComponent* Footsteps = C.Pawn->FindComponentByClass<ULBFootstepComponent>();
			if (C.bFirst)
			{
				if (!Test->TestNotNull(TEXT("Pawn has a footstep component"), Footsteps))
				{
					return true;
				}
				S->Sink.Reset(NewObject<ULBTestSink>(GetTransientPackage()));
				Footsteps->OnFootstep.AddDynamic(S->Sink.Get(), &ULBTestSink::HandleFootstep);
				S->P0 = C.Pawn->GetActorLocation();
			}
			if (!Footsteps)
			{
				return true;
			}
			DriveInput(C.Input, Gait);
			const float Travelled = static_cast<float>(FVector::DistXY(S->P0, C.Pawn->GetActorLocation()));
			if (Travelled < 1000.f)
			{
				return false;
			}

			Footsteps->OnFootstep.RemoveDynamic(S->Sink.Get(), &ULBTestSink::HandleFootstep);
			const ULBPlayerTuningData& T = C.Pawn->GetTuning();
			const float Stride = T.GetStride(Gait);
			const float Loudness = T.GetLoudness(Gait);
			const int32 Count = S->Sink->FootstepLoudness.Num();
			const int32 Expected = FMath::FloorToInt(Travelled / Stride);
			float MinL = TNumericLimits<float>::Max(), MaxL = 0.f;
			for (const float L : S->Sink->FootstepLoudness)
			{
				MinL = FMath::Min(MinL, L);
				MaxL = FMath::Max(MaxL, L);
			}
			Note(FString::Printf(TEXT("%s: travelled %.0f cm, stride %.0f -> expected ~%d steps, counted %d; loudness min %.2f max %.2f (tuning %.2f)"),
				GaitName(Gait), Travelled, Stride, Expected, Count, Count ? MinL : 0.f, MaxL, Loudness));
			Test->TestTrue(FString::Printf(TEXT("%s step count %d within +-1 of %d"), GaitName(Gait), Count, Expected), FMath::Abs(Count - Expected) <= 1);
			Test->TestTrue(FString::Printf(TEXT("%s emitted at least one step"), GaitName(Gait)), Count > 0);
			for (const float L : S->Sink->FootstepLoudness)
			{
				if (!FMath::IsNearlyEqual(L, Loudness, 0.001f))
				{
					Test->AddError(FString::Printf(TEXT("%s step loudness %.3f != gait loudness %.3f"), GaitName(Gait), L, Loudness));
					break;
				}
			}
			C.Input.Move = FVector2D::ZeroVector;
			return true;
		}, 60.f);

		AddStopStep(*R, *FString::Printf(TEXT("%s: stop"), GaitName(Gait)));
	}

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// 3. Candle
// =====================================================================================================================
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBFeelCandleTest, "LastBell.Functional.PlayerFeel.Candle",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBFeelCandleTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FFeelRunner> R = StartSession(this);
	const TSharedRef<FState> S = MakeShared<FState>();
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, S, Test);

	R->Add(TEXT("Lit at start, idle intensity for 1s"), [S, Test](FStepCtx& C)
	{
		ULBCandleComponent* Candle = C.Pawn->GetCandle();
		if (!Test->TestNotNull(TEXT("Pawn has a candle"), Candle))
		{
			return true;
		}
		UPointLightComponent* Light = Candle->GetLight();
		if (!Test->TestNotNull(TEXT("Candle point light exists"), Light))
		{
			return true;
		}
		if (C.bFirst)
		{
			S->ResetSamples();
			Test->TestTrue(TEXT("Candle IsLit at start"), Candle->IsLit());
			Test->TestTrue(TEXT("Candle light visible at start"), Light->IsVisible());
			S->Sink.Reset(NewObject<ULBTestSink>(GetTransientPackage()));
			Candle->OnCandleStateChanged.AddDynamic(S->Sink.Get(), &ULBTestSink::HandleCandleState);
		}
		S->Sum += Light->Intensity;
		++S->N;
		S->Max = FMath::Max(S->Max, Light->Intensity);
		if (C.Elapsed < 1.0)
		{
			return false;
		}
		S->IdleMean = S->Mean();
		const float Base = C.Pawn->GetTuning().CandleIntensity;
		Note(FString::Printf(TEXT("Candle idle: mean intensity %.2f, max %.2f (tuning base %.2f)"), S->IdleMean, S->Max, Base));
		Test->TestTrue(FString::Printf(TEXT("Idle mean intensity %.2f near tuning %.2f"), S->IdleMean, Base), PctWithin(S->IdleMean, Base, 0.2f));
		return true;
	});

	R->Add(TEXT("ToggleCandle snuffs"), [S, Test](FStepCtx& C)
	{
		ULBCandleComponent* Candle = C.Pawn->GetCandle();
		UPointLightComponent* Light = Candle ? Candle->GetLight() : nullptr;
		if (!Candle || !Light)
		{
			return true;
		}
		if (C.bFirst)
		{
			Test->TestTrue(TEXT("ToggleCandle accepted (lit -> snuffed)"), Candle->ToggleCandle());
			Test->TestFalse(TEXT("IsLit false after snuff"), Candle->IsLit());
			Test->TestTrue(TEXT("Light hidden or zero intensity right after snuff"), !Light->IsVisible() || Light->Intensity <= KINDA_SMALL_NUMBER);
			return false;
		}
		if (C.Elapsed < 0.3)
		{
			return false;
		}
		Test->TestFalse(TEXT("Candle stays snuffed"), Candle->IsLit());
		Test->TestTrue(TEXT("Light stays hidden or zero"), !Light->IsVisible() || Light->Intensity <= KINDA_SMALL_NUMBER);
		Test->TestEqual(TEXT("OnCandleStateChanged(false) fired once"), S->Sink->CandleStateEvents.Num(), 1);
		return true;
	});

	R->Add(TEXT("ToggleCandle relights after RelightDelay + 0.2s"), [S, Test](FStepCtx& C)
	{
		ULBCandleComponent* Candle = C.Pawn->GetCandle();
		UPointLightComponent* Light = Candle ? Candle->GetLight() : nullptr;
		if (!Candle || !Light)
		{
			return true;
		}
		const float Delay = C.Pawn->GetTuning().CandleRelightDelay;
		if (C.bFirst)
		{
			Test->TestTrue(TEXT("ToggleCandle accepted (snuffed -> relighting)"), Candle->ToggleCandle());
			Test->TestFalse(TEXT("Not yet lit while relighting"), Candle->IsLit());
			Test->TestTrue(TEXT("IsRelighting"), Candle->IsRelighting());
			return false;
		}
		if (C.Elapsed < Delay * 0.5)
		{
			Test->TestFalse(TEXT("Still not lit before the delay has passed"), Candle->IsLit());
		}
		if (C.Elapsed < Delay + 0.2)
		{
			return false;
		}
		Note(FString::Printf(TEXT("Candle relit after %.2fs (delay %.2f), light visible=%d intensity %.2f"), C.Elapsed, Delay, Light->IsVisible(), Light->Intensity));
		Test->TestTrue(TEXT("IsLit after RelightDelay + 0.2s"), Candle->IsLit());
		Test->TestTrue(TEXT("Light visible after relight"), Light->IsVisible());
		Test->TestEqual(TEXT("OnCandleStateChanged fired snuff + relit"), S->Sink->CandleStateEvents.Num(), 2);
		if (S->Sink->CandleStateEvents.Num() == 2)
		{
			Test->TestTrue(TEXT("Last state event was lit"), S->Sink->CandleStateEvents[1]);
		}
		return true;
	});

	R->Add(TEXT("Let the relight fade in and settle"), [](FStepCtx& C)
	{
		Place(C.Pawn, GStartX);
		return C.Elapsed >= 0.5;
	});

	R->Add(TEXT("Sprint 1.5s, then sample guttering intensity for 1s"), [S, Test](FStepCtx& C)
	{
		ULBCandleComponent* Candle = C.Pawn->GetCandle();
		UPointLightComponent* Light = Candle ? Candle->GetLight() : nullptr;
		if (!Candle || !Light)
		{
			return true;
		}
		if (C.bFirst)
		{
			Place(C.Pawn, GStartX);
			S->ResetSamples();
		}
		DriveInput(C.Input, ELBGait::Sprint);
		if (C.Elapsed < 1.5)
		{
			return false;
		}
		S->Sum += Light->Intensity;
		++S->N;
		S->Max = FMath::Max(S->Max, Light->Intensity);
		if (C.Elapsed < 2.5)
		{
			return false;
		}
		const float Base = C.Pawn->GetTuning().CandleIntensity;
		const float Mean = S->Mean();
		Note(FString::Printf(TEXT("Candle sprinting: mean %.2f max %.2f (idle mean %.2f, base %.2f), gait=%s guttering=%d"),
			Mean, S->Max, S->IdleMean, Base, GaitName(C.Pawn->GetGait()), Candle->IsGuttering()));
		Test->TestEqual(TEXT("Gait is sprint while sampling"), static_cast<int32>(C.Pawn->GetGait()), static_cast<int32>(ELBGait::Sprint));
		Test->TestTrue(TEXT("Candle IsGuttering while sprinting"), Candle->IsGuttering());
		Test->TestTrue(FString::Printf(TEXT("Max guttering intensity %.2f below base %.2f"), S->Max, Base), S->Max < Base);
		Test->TestTrue(FString::Printf(TEXT("Guttering mean %.2f well below idle mean %.2f"), Mean, S->IdleMean), Mean < S->IdleMean * 0.85f);
		return true;
	});

	AddStopStep(*R, TEXT("Stop sprinting"));

	R->Add(TEXT("Guttering ends when not sprinting"), [Test](FStepCtx& C)
	{
		if (C.Elapsed < 0.8)
		{
			return false;
		}
		if (const ULBCandleComponent* Candle = C.Pawn->GetCandle())
		{
			Test->TestFalse(TEXT("Not guttering once sprint ended"), Candle->IsGuttering());
		}
		return true;
	});

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// 4. Inspection
// =====================================================================================================================
namespace
{
	struct FInspectCase
	{
		FString Label;
		const TCHAR* ClassPath;
		bool bKeep;
	};

	bool SetBoolProp(UObject* O, const TCHAR* Name, bool bValue)
	{
		if (FBoolProperty* P = FindFProperty<FBoolProperty>(O->GetClass(), Name))
		{
			P->SetPropertyValue_InContainer(O, bValue);
			return true;
		}
		return false;
	}

	bool SetTagProp(UObject* O, const TCHAR* Name, const FGameplayTag& Tag)
	{
		FStructProperty* P = FindFProperty<FStructProperty>(O->GetClass(), Name);
		if (P && P->Struct == FGameplayTag::StaticStruct())
		{
			*P->ContainerPtrToValuePtr<FGameplayTag>(O) = Tag;
			return true;
		}
		return false;
	}

	void AddInspectCase(FFeelRunner& R, const TSharedRef<FState>& S, FAutomationTestBase* Test, const FInspectCase& Case)
	{
		const FString L = Case.Label;
		const TCHAR* ClassPath = Case.ClassPath;
		const bool bKeep = Case.bKeep;

		R.Add(*FString::Printf(TEXT("%s: place pawn"), *L), [](FStepCtx& C)
		{
			if (C.bFirst)
			{
				C.Input = FFeelInput();
				Place(C.Pawn, GStartX);
			}
			return C.Elapsed >= 0.5 && OnGround(C.Pawn) && Speed2D(C.Pawn) < 5.f;
		});

		R.Add(*FString::Printf(TEXT("%s: spawn item in front of the pawn"), *L), [S, Test, L, ClassPath, bKeep](FStepCtx& C)
		{
			if (!C.bFirst)
			{
				return C.Elapsed >= 0.4;
			}
			UClass* Class = LoadClass<AActor>(nullptr, ClassPath);
			if (!Test->TestNotNull(*FString::Printf(TEXT("%s: Blueprint class loads (%s)"), *L, ClassPath), Class))
			{
				return true;
			}
			FVector ViewLoc;
			FRotator ViewRot;
			C.Pawn->GetController()->GetPlayerViewPoint(ViewLoc, ViewRot);
			// Within interact range (TraceDistance 200) and with an odd rotation so the restore check means something.
			const FTransform Spawn(FRotator(8.f, 33.f, 5.f), ViewLoc + ViewRot.Vector() * 100.f);

			AActor* Item = C.W->SpawnActorDeferred<AActor>(Class, Spawn, nullptr, nullptr, ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
			if (!Test->TestNotNull(*FString::Printf(TEXT("%s: item spawned"), *L), Item))
			{
				return true;
			}
			if (bKeep)
			{
				const FGameplayTag KeepTag = FGameplayTag::RequestGameplayTag(FName(GKeepTagName), false);
				Test->TestTrue(TEXT("Keep tag exists"), KeepTag.IsValid());
				Test->TestTrue(TEXT("BP_TagInteractable.bInspectable"), SetBoolProp(Item, TEXT("bInspectable"), true));
				Test->TestTrue(TEXT("BP_TagInteractable.bHideOnUse"), SetBoolProp(Item, TEXT("bHideOnUse"), true));
				Test->TestTrue(TEXT("BP_TagInteractable.UseStateTag"), SetTagProp(Item, TEXT("UseStateTag"), KeepTag));
			}
			Item->FinishSpawning(Spawn);

			// A tag-interactable stand-in can have no mesh: give it a collider the interactor can hit.
			if (bKeep)
			{
				TInlineComponentArray<UStaticMeshComponent*> Meshes(Item);
				if (Meshes.Num() > 0 && !Meshes[0]->GetStaticMesh())
				{
					Note(TEXT("BP_TagInteractable has no mesh assigned: test assigns the engine cube (content problem, reported)"));
					Meshes[0]->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube")));
					Meshes[0]->SetWorldScale3D(FVector(0.3f));
				}
			}

			S->Item = Item;
			S->ItemOriginal = Item->GetActorTransform();
			S->StateBefore = ULBWorldStateSubsystem::Get(C.W) ? ULBWorldStateSubsystem::Get(C.W)->GetState() : FGameplayTagContainer();
			S->PawnBefore = C.Pawn->GetActorLocation();
			S->Sink.Reset(NewObject<ULBTestSink>(GetTransientPackage()));
			C.Pawn->GetInspection()->OnInspectBegin.AddDynamic(S->Sink.Get(), &ULBTestSink::HandleInspectBegin);
			C.Pawn->GetInspection()->OnInspectEnd.AddDynamic(S->Sink.Get(), &ULBTestSink::HandleInspectEnd);
			S->LastTry = -1.0;
			Note(FString::Printf(TEXT("%s: item %s at %s"), *L, *GetNameSafe(Item), *Spawn.GetLocation().ToString()));
			return false;
		});

		R.Add(*FString::Printf(TEXT("%s: TryInteract starts the inspection"), *L), [S, Test, L](FStepCtx& C)
		{
			AActor* Item = S->Item.Get();
			if (!Item)
			{
				return true;
			}
			ULBInspectionComponent* Inspection = C.Pawn->GetInspection();
			if (Inspection->IsInspecting())
			{
				Test->TestEqual(TEXT("OnInspectBegin fired once"), S->Sink->InspectBeginCount, 1);
				Test->TestTrue(TEXT("Inspecting the spawned item"), Inspection->GetInspected() && Inspection->GetInspected()->GetOwner() == Item);
				return true;
			}
			if (C.Elapsed - S->LastTry >= 0.25 || S->LastTry < 0.0)
			{
				S->LastTry = C.Elapsed;
				C.Pawn->GetInteractor()->TryInteract();
			}
			if (C.Elapsed > 4.0)
			{
				const ULBInteractableComponent* Focus = C.Pawn->GetInteractor()->GetFocusedComponent();
				Test->AddError(FString::Printf(TEXT("%s: TryInteract never started an inspection. Focus=%s Item=%s at %s, pawn %s"), *L,
					*GetNameSafe(Focus ? Focus->GetOwner() : nullptr), *GetNameSafe(Item), *Item->GetActorLocation().ToString(), *C.Pawn->GetActorLocation().ToString()));
				return true;
			}
			return false;
		});

		R.Add(*FString::Printf(TEXT("%s: item travels to the hold point"), *L), [S, Test, L](FStepCtx& C)
		{
			AActor* Item = S->Item.Get();
			if (!Item || !C.Pawn->GetInspection()->IsInspecting())
			{
				return true;
			}
			const float Blend = C.Pawn->GetTuning().InspectBlendTime;
			if (C.Elapsed < Blend + 0.3)
			{
				return false;
			}
			FVector ViewLoc;
			FRotator ViewRot;
			C.Pawn->GetController()->GetPlayerViewPoint(ViewLoc, ViewRot);
			const float Hold = C.Pawn->GetTuning().InspectHoldDistance;
			const FVector Expected = ViewLoc + ViewRot.Vector() * Hold;
			FVector Origin, Extent;
			Item->GetActorBounds(false, Origin, Extent);
			const float Err = static_cast<float>(FVector::Dist(Origin, Expected));
			const float Moved = static_cast<float>(FVector::Dist(Item->GetActorLocation(), S->ItemOriginal.GetLocation()));
			Note(FString::Printf(TEXT("%s: bounds centre %s, hold point %s, error %.2f cm (hold distance %.0f), item moved %.1f cm"), *L, *Origin.ToString(), *Expected.ToString(), Err, Hold, Moved));
			Test->TestTrue(FString::Printf(TEXT("Item bounds centre within 3 cm of the hold point (error %.2f)"), Err), Err < 3.f);
			Test->TestTrue(TEXT("Item actually moved"), Moved > 10.f);
			return true;
		});

		R.Add(*FString::Printf(TEXT("%s: movement input does not move the pawn"), *L), [S, Test, L](FStepCtx& C)
		{
			if (!C.Pawn->GetInspection()->IsInspecting())
			{
				return true;
			}
			if (C.bFirst)
			{
				S->PawnBefore = C.Pawn->GetActorLocation();
			}
			DriveInput(C.Input, ELBGait::Sprint);
			S->bCrouchSeen |= C.Pawn->bIsCrouched;
			if (C.Elapsed < 0.6)
			{
				return false;
			}
			C.Input = FFeelInput();
			const float Moved = static_cast<float>(FVector::Dist(S->PawnBefore, C.Pawn->GetActorLocation()));
			Note(FString::Printf(TEXT("%s: pawn moved %.3f cm over 0.6s of forward+sprint input while inspecting, speed %.2f"), *L, Moved, Speed2D(C.Pawn)));
			Test->TestTrue(FString::Printf(TEXT("Pawn did not move while inspecting (%.3f cm)"), Moved), Moved < 1.f);
			Test->TestTrue(TEXT("Pawn speed ~0 while inspecting"), Speed2D(C.Pawn) < 1.f);
			Test->TestTrue(TEXT("Still inspecting"), C.Pawn->GetInspection()->IsInspecting());
			return true;
		});

		R.Add(*FString::Printf(TEXT("%s: close the inspection"), *L), [S, Test, L, bKeep](FStepCtx& C)
		{
			AActor* Item = S->Item.Get();
			ULBInspectionComponent* Inspection = C.Pawn->GetInspection();
			if (!Item || !Inspection->IsInspecting())
			{
				return true;
			}
			if (!Inspection->RequestClose())
			{
				return C.Elapsed > 2.0; // too early: retry next frame
			}

			Test->TestFalse(TEXT("No longer inspecting"), Inspection->IsInspecting());
			Test->TestEqual(TEXT("OnInspectEnd fired once"), S->Sink->InspectEndCount, 1);
			Test->TestEqual(TEXT("OnInspectEnd bKept"), S->Sink->LastInspectKept, bKeep);

			const FTransform After = Item->GetActorTransform();
			const bool bLoc = After.GetLocation().Equals(S->ItemOriginal.GetLocation(), 0.01f);
			const bool bRot = After.GetRotation().Equals(S->ItemOriginal.GetRotation(), 1e-5f);
			const bool bScale = After.GetScale3D().Equals(S->ItemOriginal.GetScale3D(), 1e-4f);
			Note(FString::Printf(TEXT("%s: restored location error %.4f cm, rotation dot %.8f"), *L,
				FVector::Dist(After.GetLocation(), S->ItemOriginal.GetLocation()), After.GetRotation() | S->ItemOriginal.GetRotation()));
			Test->TestTrue(TEXT("Item location restored exactly"), bLoc);
			Test->TestTrue(TEXT("Item rotation restored exactly"), bRot);
			Test->TestTrue(TEXT("Item scale restored exactly"), bScale);

			const ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(C.W);
			const FGameplayTagContainer StateAfter = State ? State->GetState() : FGameplayTagContainer();
			if (bKeep)
			{
				const FGameplayTag KeepTag = FGameplayTag::RequestGameplayTag(FName(GKeepTagName), false);
				Test->TestTrue(TEXT("Kept item granted its UseStateTag"), StateAfter.HasTagExact(KeepTag));
				Test->TestTrue(TEXT("Kept item is hidden"), Item->IsHidden());
			}
			else
			{
				Test->TestTrue(TEXT("Put-back item granted no tags"), StateAfter.Num() == S->StateBefore.Num() && StateAfter.HasAllExact(S->StateBefore));
				Test->TestFalse(TEXT("Put-back item is not hidden"), Item->IsHidden());
				Test->TestTrue(TEXT("Put-back item collision restored"), Item->GetActorEnableCollision());
			}
			C.Pawn->GetInspection()->OnInspectBegin.RemoveDynamic(S->Sink.Get(), &ULBTestSink::HandleInspectBegin);
			C.Pawn->GetInspection()->OnInspectEnd.RemoveDynamic(S->Sink.Get(), &ULBTestSink::HandleInspectEnd);
			// Remove it so the next case's item is not shadowed by this one at the same spot.
			Item->Destroy();
			S->Item.Reset();
			return true;
		});
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBFeelInspectionTest, "LastBell.Functional.PlayerFeel.Inspection",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBFeelInspectionTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FFeelRunner> R = StartSession(this);
	const TSharedRef<FState> S = MakeShared<FState>();
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, S, Test);

	AddInspectCase(*R, S, Test, { TEXT("Note (put back)"), GNoteClassPath, false });

	R->Add(TEXT("Keep item: tag must not be set yet"), [Test](FStepCtx& C)
	{
		const FGameplayTag KeepTag = FGameplayTag::RequestGameplayTag(FName(GKeepTagName), false);
		Test->TestFalse(TEXT("Keep tag absent before the keep item is inspected"), LBPie::HasState(KeepTag));
		return true;
	});

	AddInspectCase(*R, S, Test, { TEXT("BP_TagInteractable (keep)"), GTagInteractableClassPath, true });

	Enqueue(R);
	return true;
}

#endif
