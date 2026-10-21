#include "Tests/LBRouteBot.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Editor.h"
#include "Tests/AutomationEditorCommon.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/LocalPlayer.h"
#include "Camera/CameraComponent.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"
#include "Camera/CameraTypes.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/GameViewportClient.h"
#include "GenericPlatform/GenericPlatformInputDeviceMapper.h"
#include "InputKeyEventArgs.h"
#include "SceneView.h"
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
#include "Systems/LBPlayerController.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "InputMappingContext.h"
#include "InputAction.h"
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
		int32 SpamCalls = 0;
		TWeakObjectPtr<UWorld> OldWorld;

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

	/** True when the player controller's inspect mapping context is currently on the local player's input subsystem. */
	bool InspectContextActive(const ALBCharacter* P)
	{
		const ALBPlayerController* PC = P ? Cast<ALBPlayerController>(P->GetController()) : nullptr;
		const ULocalPlayer* LP = PC ? PC->GetLocalPlayer() : nullptr;
		const UEnhancedInputLocalPlayerSubsystem* Subsystem = LP ? LP->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>() : nullptr;
		return Subsystem && PC->InspectMappingContext && Subsystem->HasMappingContext(PC->InspectMappingContext);
	}

	bool InspectContextConfigured(const ALBCharacter* P)
	{
		const ALBPlayerController* PC = P ? Cast<ALBPlayerController>(P->GetController()) : nullptr;
		return PC && PC->InspectMappingContext;
	}

	/** Spawns the item 100 cm in front of the view and binds the test sink to the inspection and interactable delegates. */
	AActor* SpawnInspectItem(FStepCtx& C, FState& S, FAutomationTestBase* Test, const FString& L, const TCHAR* ClassPath, bool bKeep)
	{
		UClass* Class = LoadClass<AActor>(nullptr, ClassPath);
		if (!Test->TestNotNull(*FString::Printf(TEXT("%s: Blueprint class loads (%s)"), *L, ClassPath), Class))
		{
			return nullptr;
		}
		FVector ViewLoc;
		FRotator ViewRot;
		C.Pawn->GetController()->GetPlayerViewPoint(ViewLoc, ViewRot);
		// Within interact range (TraceDistance 200) and with an odd rotation so the restore check means something.
		const FTransform Spawn(FRotator(8.f, 33.f, 5.f), ViewLoc + ViewRot.Vector() * 100.f);

		AActor* Item = C.W->SpawnActorDeferred<AActor>(Class, Spawn, nullptr, nullptr, ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
		if (!Test->TestNotNull(*FString::Printf(TEXT("%s: item spawned"), *L), Item))
		{
			return nullptr;
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

		// The spawn transform (scale 1) replaces the root scale authored in the Blueprint: put the authored scale back, so a flat
		// note really is a flat note (0.2 x 0.28 x 0.003 in BP_Inspectable_Note), as it is when placed in a level.
		if (const UBlueprintGeneratedClass* BPClass = Cast<UBlueprintGeneratedClass>(Class))
		{
			if (BPClass->SimpleConstructionScript)
			{
				for (const USCS_Node* Node : BPClass->SimpleConstructionScript->GetRootNodes())
				{
					const USceneComponent* Template = Node ? Cast<USceneComponent>(Node->ComponentTemplate) : nullptr;
					if (Template && Item->GetRootComponent() && !Template->GetRelativeScale3D().Equals(FVector::OneVector))
					{
						Item->SetActorScale3D(Template->GetRelativeScale3D());
						break;
					}
				}
			}
		}

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

		S.Item = Item;
		S.ItemOriginal = Item->GetActorTransform();
		S.StateBefore = ULBWorldStateSubsystem::Get(C.W) ? ULBWorldStateSubsystem::Get(C.W)->GetState() : FGameplayTagContainer();
		S.PawnBefore = C.Pawn->GetActorLocation();
		ULBInspectionComponent* Inspection = C.Pawn->GetInspection();
		if (S.Sink.IsValid())
		{
			Inspection->OnInspectBegin.RemoveDynamic(S.Sink.Get(), &ULBTestSink::HandleInspectBegin);
			Inspection->OnInspectEnd.RemoveDynamic(S.Sink.Get(), &ULBTestSink::HandleInspectEnd);
		}
		S.Sink.Reset(NewObject<ULBTestSink>(GetTransientPackage()));
		Inspection->OnInspectBegin.AddDynamic(S.Sink.Get(), &ULBTestSink::HandleInspectBegin);
		Inspection->OnInspectEnd.AddDynamic(S.Sink.Get(), &ULBTestSink::HandleInspectEnd);
		if (ULBInteractableComponent* Interactable = Item->FindComponentByClass<ULBInteractableComponent>())
		{
			Interactable->OnInteracted.AddDynamic(S.Sink.Get(), &ULBTestSink::HandleInteracted);
		}
		S.LastTry = -1.0;
		Note(FString::Printf(TEXT("%s: item %s at %s"), *L, *GetNameSafe(Item), *Spawn.GetLocation().ToString()));
		return Item;
	}

	void AddPlaceStep(FFeelRunner& R, const FString& L)
	{
		R.Add(*FString::Printf(TEXT("%s: place pawn"), *L), [](FStepCtx& C)
		{
			if (C.bFirst)
			{
				C.Input = FFeelInput();
				Place(C.Pawn, GStartX);
			}
			return C.Elapsed >= 0.5 && OnGround(C.Pawn) && Speed2D(C.Pawn) < 5.f;
		});
	}

	void AddSpawnStep(FFeelRunner& R, const TSharedRef<FState>& S, FAutomationTestBase* Test, const FString& L, const TCHAR* ClassPath, bool bKeep)
	{
		R.Add(*FString::Printf(TEXT("%s: spawn item in front of the pawn"), *L), [S, Test, L, ClassPath, bKeep](FStepCtx& C)
		{
			if (!C.bFirst)
			{
				return C.Elapsed >= 0.4;
			}
			return SpawnInspectItem(C, *S, Test, L, ClassPath, bKeep) == nullptr;
		});
	}

	/** Retries TryInteract every 0.25 s until the inspection starts, then checks the begin event. */
	void AddBeginStep(FFeelRunner& R, const TSharedRef<FState>& S, FAutomationTestBase* Test, const FString& L)
	{
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
	}

	void AddInspectCase(FFeelRunner& R, const TSharedRef<FState>& S, FAutomationTestBase* Test, const FInspectCase& Case)
	{
		const FString L = Case.Label;
		const TCHAR* ClassPath = Case.ClassPath;
		const bool bKeep = Case.bKeep;

		AddPlaceStep(R, L);
		AddSpawnStep(R, S, Test, L, ClassPath, bKeep);
		AddBeginStep(R, S, Test, L);

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

// =====================================================================================================================
// 5. Inspection edge cases (REV-003 H1, M2, interact spam)
// =====================================================================================================================
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBFeelInspectEdgeCasesTest, "LastBell.Functional.PlayerFeel.InspectEdgeCases",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBFeelInspectEdgeCasesTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FFeelRunner> R = StartSession(this);
	const TSharedRef<FState> S = MakeShared<FState>();
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, S, Test);

	// ---- (a) the held item is destroyed mid-inspection ------------------------------------------------------------
	{
		const FString L = TEXT("(a) destroy held item");
		AddPlaceStep(*R, L);
		AddSpawnStep(*R, S, Test, L, GNoteClassPath, false);
		AddBeginStep(*R, S, Test, L);

		R->Add(*FString::Printf(TEXT("%s: inspection ends cleanly"), *L), [S, Test](FStepCtx& C)
		{
			ULBInspectionComponent* Inspection = C.Pawn->GetInspection();
			if (C.bFirst)
			{
				Test->TestTrue(TEXT("PlayerController has an InspectMappingContext assigned"), InspectContextConfigured(C.Pawn));
				Test->TestTrue(TEXT("Inspect input context active while inspecting"), InspectContextActive(C.Pawn));
				if (AActor* Item = S->Item.Get())
				{
					Item->Destroy();
				}
				return false;
			}
			if (Inspection->IsInspecting())
			{
				if (C.Elapsed > 2.0)
				{
					Test->AddError(TEXT("Inspection never ended after the held item was destroyed"));
					return true;
				}
				return false;
			}
			Test->TestEqual(TEXT("OnInspectEnd fired once"), S->Sink->InspectEndCount, 1);
			Test->TestFalse(TEXT("OnInspectEnd bKept is false for a vanished item"), S->Sink->LastInspectKept);
			Test->TestFalse(TEXT("Inspect input context removed"), InspectContextActive(C.Pawn));
			Test->TestFalse(TEXT("Inspection component stopped ticking"), Inspection->IsComponentTickEnabled());
			return true;
		});

		R->Add(*FString::Printf(TEXT("%s: movement input works again"), *L), [S, Test](FStepCtx& C)
		{
			if (C.bFirst)
			{
				Place(C.Pawn, GStartX);
				S->bMarked = false;
			}
			DriveInput(C.Input, ELBGait::Walk);
			if (!S->bMarked && C.Elapsed >= 0.4)
			{
				S->bMarked = true;
				S->PawnBefore = C.Pawn->GetActorLocation();
			}
			if (C.Elapsed < 1.2)
			{
				return false;
			}
			C.Input = FFeelInput();
			const float Moved = static_cast<float>(FVector::DistXY(S->PawnBefore, C.Pawn->GetActorLocation()));
			Note(FString::Printf(TEXT("(a) pawn moved %.1f cm in 0.8s after the item vanished"), Moved));
			Test->TestTrue(FString::Printf(TEXT("Pawn moves again after the item vanished (%.1f cm)"), Moved), Moved > 50.f);
			return true;
		});
		AddStopStep(*R, TEXT("(a) stop"));
	}

	// ---- (c) interact spam on consecutive frames --------------------------------------------------------------------
	{
		const FString L = TEXT("(c) interact spam");
		AddPlaceStep(*R, L);
		AddSpawnStep(*R, S, Test, L, GTagInteractableClassPath, true);

		R->Add(*FString::Printf(TEXT("%s: 10 TryInteract calls in consecutive frames"), *L), [S, Test](FStepCtx& C)
		{
			AActor* Item = S->Item.Get();
			if (!Item)
			{
				return true;
			}
			ULBInspectionComponent* Inspection = C.Pawn->GetInspection();
			if (C.bFirst)
			{
				S->SpamCalls = 0;
			}
			C.Pawn->GetInteractor()->TryInteract();
			++S->SpamCalls;
			if (S->SpamCalls == 6)
			{
				// Also hit the interactable directly while inspecting: it must be ignored, not fall back to the plain grant.
				if (ULBInteractableComponent* Interactable = Item->FindComponentByClass<ULBInteractableComponent>())
				{
					Interactable->Interact(C.Pawn);
				}
			}
			const bool bConsistent = Inspection->IsInspecting() == (S->Sink->InspectBeginCount > S->Sink->InspectEndCount);
			Test->TestTrue(FString::Printf(TEXT("Call %d: inspecting matches begin/end event balance (begin %d, end %d)"), S->SpamCalls,
				S->Sink->InspectBeginCount, S->Sink->InspectEndCount), bConsistent);
			if (S->SpamCalls < 10)
			{
				return false;
			}
			Test->TestTrue(TEXT("Inspecting after the spam"), Inspection->IsInspecting());
			Test->TestEqual(TEXT("OnInspectBegin fired exactly once"), S->Sink->InspectBeginCount, 1);
			Test->TestEqual(TEXT("No grant while the item is still held (OnInteracted count)"), S->Sink->InteractedCount, 0);
			const FGameplayTag KeepTag = FGameplayTag::RequestGameplayTag(FName(GKeepTagName), false);
			Test->TestFalse(TEXT("Keep tag not granted while inspecting"), LBPie::HasState(KeepTag));
			return true;
		});

		R->Add(*FString::Printf(TEXT("%s: close grants exactly once"), *L), [S, Test](FStepCtx& C)
		{
			ULBInspectionComponent* Inspection = C.Pawn->GetInspection();
			if (!Inspection->IsInspecting() || !Inspection->RequestClose())
			{
				// RequestClose ignores the first frames after BeginInspect: retry on later frames.
				if (Inspection->IsInspecting() && C.Elapsed <= 2.0)
				{
					return false;
				}
			}
			Test->TestFalse(TEXT("Not inspecting after close"), Inspection->IsInspecting());
			Test->TestEqual(TEXT("OnInspectEnd fired once"), S->Sink->InspectEndCount, 1);
			Test->TestTrue(TEXT("OnInspectEnd bKept"), S->Sink->LastInspectKept);
			Test->TestEqual(TEXT("Granted exactly once (OnInteracted count)"), S->Sink->InteractedCount, 1);
			const FGameplayTag KeepTag = FGameplayTag::RequestGameplayTag(FName(GKeepTagName), false);
			Test->TestTrue(TEXT("Keep tag granted on close"), LBPie::HasState(KeepTag));
			Test->TestFalse(TEXT("Inspect input context removed"), InspectContextActive(C.Pawn));
			S->SpamCalls = 0;
			return true;
		});

		R->Add(*FString::Printf(TEXT("%s: spam after the keep does not re-trigger"), *L), [S, Test](FStepCtx& C)
		{
			C.Pawn->GetInteractor()->TryInteract();
			if (++S->SpamCalls < 10)
			{
				return false;
			}
			Test->TestFalse(TEXT("Not inspecting after post-keep spam"), C.Pawn->GetInspection()->IsInspecting());
			Test->TestEqual(TEXT("Still exactly one begin"), S->Sink->InspectBeginCount, 1);
			Test->TestEqual(TEXT("Still exactly one grant"), S->Sink->InteractedCount, 1);
			// Reset the keep tag so the next scenario's fresh item is not consumed on spawn.
			if (ULBWorldStateSubsystem* WorldState = ULBWorldStateSubsystem::Get(C.W))
			{
				WorldState->RemoveState(FGameplayTag::RequestGameplayTag(FName(GKeepTagName), false));
			}
			if (AActor* Item = S->Item.Get())
			{
				Item->Destroy();
			}
			S->Item.Reset();
			return true;
		});
	}

	// ---- (b) death while inspecting: the item is restored, nothing is granted, the reload proceeds ----------------------
	{
		const FString L = TEXT("(b) kill while inspecting");
		AddPlaceStep(*R, L);
		AddSpawnStep(*R, S, Test, L, GTagInteractableClassPath, true);
		AddBeginStep(*R, S, Test, L);

		R->Add(*FString::Printf(TEXT("%s: Kill restores, grants nothing"), *L), [S, Test](FStepCtx& C)
		{
			AActor* Item = S->Item.Get();
			ULBInspectionComponent* Inspection = C.Pawn->GetInspection();
			if (!Item || !Inspection->IsInspecting())
			{
				Test->AddError(TEXT("(b) not inspecting when the kill was due"));
				return true;
			}
			if (C.Elapsed < C.Pawn->GetTuning().InspectBlendTime * 0.5f + 0.1f)
			{
				return false;
			}
			Test->TestTrue(TEXT("Item has moved away from its original spot before the kill"),
				FVector::Dist(Item->GetActorLocation(), S->ItemOriginal.GetLocation()) > 5.f);
			S->OldWorld = C.W;
			S->bMarked = true;
			C.Pawn->Kill();

			Test->TestFalse(TEXT("Not inspecting after Kill"), Inspection->IsInspecting());
			Test->TestEqual(TEXT("OnInspectEnd fired once"), S->Sink->InspectEndCount, 1);
			Test->TestFalse(TEXT("OnInspectEnd bKept is false on death"), S->Sink->LastInspectKept);
			Test->TestEqual(TEXT("No grant on death (OnInteracted count)"), S->Sink->InteractedCount, 0);
			const FGameplayTag KeepTag = FGameplayTag::RequestGameplayTag(FName(GKeepTagName), false);
			Test->TestFalse(TEXT("Keep tag not granted on death"), LBPie::HasState(KeepTag));
			Test->TestFalse(TEXT("Inspect input context removed"), InspectContextActive(C.Pawn));
			const FTransform After = Item->GetActorTransform();
			Test->TestTrue(TEXT("Item location restored"), After.GetLocation().Equals(S->ItemOriginal.GetLocation(), 0.01f));
			Test->TestTrue(TEXT("Item rotation restored"), After.GetRotation().Equals(S->ItemOriginal.GetRotation(), 1e-5f));
			Test->TestFalse(TEXT("Item not hidden (not kept)"), Item->IsHidden());
			Test->TestTrue(TEXT("Item collision restored"), Item->GetActorEnableCollision());
			return true;
		});

		R->Add(*FString::Printf(TEXT("%s: death reload proceeds"), *L), [S, Test](FStepCtx& C)
		{
			if (!S->bMarked || !C.W || !C.Pawn || C.W == S->OldWorld.Get() || !LBPie::WorldReady() || C.Frames < 20)
			{
				return false;
			}
			Test->TestFalse(TEXT("New pawn is not inspecting"), C.Pawn->GetInspection()->IsInspecting());
			Test->TestFalse(TEXT("New pawn has no inspect input context"), InspectContextActive(C.Pawn));
			Test->TestFalse(TEXT("New pawn is alive"), C.Pawn->IsDead());
			const FGameplayTag KeepTag = FGameplayTag::RequestGameplayTag(FName(GKeepTagName), false);
			Test->TestFalse(TEXT("Keep tag absent after the reload"), LBPie::HasState(KeepTag));
			return true;
		}, 90.f);
	}

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// 6. A Static-mobility item is refused
// =====================================================================================================================
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBFeelInspectStaticRefusedTest, "LastBell.Functional.PlayerFeel.InspectRefusesStatic",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBFeelInspectStaticRefusedTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FFeelRunner> R = StartSession(this);
	const TSharedRef<FState> S = MakeShared<FState>();
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, S, Test);
	AddPlaceStep(*R, TEXT("static"));

	R->Add(TEXT("BeginInspect refuses a Static item"), [S, Test](FStepCtx& C)
	{
		FVector ViewLoc;
		FRotator ViewRot;
		C.Pawn->GetController()->GetPlayerViewPoint(ViewLoc, ViewRot);
		const FVector Location = ViewLoc + ViewRot.Vector() * 100.f;
		AStaticMeshActor* Item = C.W->SpawnActor<AStaticMeshActor>(Location, FRotator::ZeroRotator);
		if (!Test->TestNotNull(TEXT("Static test actor spawned"), Item))
		{
			return true;
		}
		Test->TestTrue(TEXT("Static test actor root is Static"), Item->GetRootComponent()->Mobility == EComponentMobility::Static);
		ULBInspectableComponent* Inspectable = NewObject<ULBInspectableComponent>(Item);
		Inspectable->RegisterComponent();

		ULBInspectionComponent* Inspection = C.Pawn->GetInspection();
		S->Sink.Reset(NewObject<ULBTestSink>(GetTransientPackage()));
		Inspection->OnInspectBegin.AddDynamic(S->Sink.Get(), &ULBTestSink::HandleInspectBegin);

		Test->TestFalse(TEXT("BeginInspect returns false for a Static item"), Inspection->BeginInspect(Inspectable));
		Test->TestFalse(TEXT("Not inspecting"), Inspection->IsInspecting());
		Test->TestEqual(TEXT("OnInspectBegin did not fire"), S->Sink->InspectBeginCount, 0);
		Test->TestFalse(TEXT("Inspect input context not added"), InspectContextActive(C.Pawn));
		Test->TestTrue(TEXT("Item did not move"), Item->GetActorLocation().Equals(Location, 0.01f));
		Test->TestFalse(TEXT("Inspection component not ticking"), Inspection->IsComponentTickEnabled());

		Inspection->OnInspectBegin.RemoveDynamic(S->Sink.Get(), &ULBTestSink::HandleInspectBegin);
		Item->Destroy();
		return true;
	});

	Enqueue(R);
	return true;
}


// =====================================================================================================================
// 7. P3-BUG: the held candle must be on screen (flame in the lower-right quadrant) for any plausible window shape
// =====================================================================================================================
namespace
{
	constexpr float GFrameMargin = 0.05f;
	constexpr float GLowerRightMin = 0.55f;

	struct FAspectCase
	{
		const TCHAR* Name;
		float Aspect;
	};

	// Widescreen, classic, square and the user's PIE viewport (506 x 538).
	const FAspectCase GAspects[] = {
		{ TEXT("16:9"), 16.f / 9.f },
		{ TEXT("4:3"), 4.f / 3.f },
		{ TEXT("1:1"), 1.f },
		{ TEXT("0.94 (506x538)"), 506.f / 538.f },
	};
	constexpr int32 GNumAspects = UE_ARRAY_COUNT(GAspects);

	struct FRange2D
	{
		FVector2D Min = FVector2D(1e9, 1e9);
		FVector2D Max = FVector2D(-1e9, -1e9);
		int32 N = 0;

		void Add(const FVector2D& P)
		{
			Min.X = FMath::Min(Min.X, P.X);
			Min.Y = FMath::Min(Min.Y, P.Y);
			Max.X = FMath::Max(Max.X, P.X);
			Max.Y = FMath::Max(Max.Y, P.Y);
			++N;
		}

		bool InsideFrame() const
		{
			return N > 0 && Min.X >= GFrameMargin && Min.Y >= GFrameMargin && Max.X <= 1.f - GFrameMargin && Max.Y <= 1.f - GFrameMargin;
		}

		FString ToString() const
		{
			return FString::Printf(TEXT("x %.3f..%.3f y %.3f..%.3f"), Min.X, Max.X, Min.Y, Max.Y);
		}
	};

	struct FCandleProbe
	{
		FRange2D Flame;
		FRange2D FlameTop;
		FRange2D WaxTop;
		FRange2D WaxBottom;
		int32 Behind = 0;
	};

	struct FCandleScreenState
	{
		FCandleProbe Probes[GNumAspects];
		float MinFOV = 1e9f;
		float MaxFOV = -1e9f;
		int32 Samples = 0;
		double SampleStart = -1.0;
		FVector Offset = FVector::ZeroVector;
		FVector FlameLocal = FVector::ZeroVector;

		void Reset()
		{
			for (FCandleProbe& P : Probes)
			{
				P = FCandleProbe();
			}
			MinFOV = 1e9f;
			MaxFOV = -1e9f;
			Samples = 0;
			SampleStart = -1.0;
		}
	};

	enum class ECandleStance : uint8
	{
		Stand,
		Crouch,
		Sprint
	};

	const TCHAR* StanceName(ECandleStance Stance)
	{
		switch (Stance)
		{
		case ECandleStance::Crouch: return TEXT("crouched");
		case ECandleStance::Sprint: return TEXT("sprinting");
		default: return TEXT("standing");
		}
	}

	/** Flame = the topmost mesh under the Candle component, wax = the lowest. Returns false when there are not two meshes. */
	bool GatherCandlePoints(const ALBCharacter* Pawn, FVector& Flame, FVector& FlameTop, FVector& WaxTop, FVector& WaxBottom)
	{
		const ULBCandleComponent* Candle = Pawn->GetCandle();
		if (!Candle)
		{
			return false;
		}
		TArray<USceneComponent*> Children;
		Candle->GetChildrenComponents(true, Children);
		const UStaticMeshComponent* Top = nullptr;
		const UStaticMeshComponent* Bottom = nullptr;
		for (const USceneComponent* Child : Children)
		{
			const UStaticMeshComponent* Mesh = Cast<UStaticMeshComponent>(Child);
			if (!Mesh || !Mesh->GetStaticMesh())
			{
				continue;
			}
			if (!Top || Mesh->Bounds.Origin.Z > Top->Bounds.Origin.Z)
			{
				Top = Mesh;
			}
			if (!Bottom || Mesh->Bounds.Origin.Z < Bottom->Bounds.Origin.Z)
			{
				Bottom = Mesh;
			}
		}
		if (!Top || !Bottom || Top == Bottom)
		{
			return false;
		}
		Flame = Top->Bounds.Origin;
		FlameTop = Top->Bounds.Origin + FVector(0.0, 0.0, Top->Bounds.BoxExtent.Z);
		WaxTop = Bottom->Bounds.Origin + FVector(0.0, 0.0, Bottom->Bounds.BoxExtent.Z);
		WaxBottom = Bottom->Bounds.Origin - FVector(0.0, 0.0, Bottom->Bounds.BoxExtent.Z);
		return true;
	}

	/** The engine's own projection (same call ULocalPlayer makes), for a viewport of the given width / height ratio. */
	FMatrix BuildViewProjection(const FMinimalViewInfo& View, EAspectRatioAxisConstraint Constraint, float ViewAspect)
	{
		constexpr int32 Height = 1000;
		const FIntRect Rect(0, 0, FMath::RoundToInt(Height * ViewAspect), Height);
		FSceneViewProjectionData Data;
		Data.SetViewRectangle(Rect);
		Data.ViewOrigin = View.Location;
		Data.ViewRotationMatrix = FInverseRotationMatrix(View.Rotation) * FMatrix(
			FPlane(0, 0, 1, 0),
			FPlane(1, 0, 0, 0),
			FPlane(0, 1, 0, 0),
			FPlane(0, 0, 0, 1));
		FMinimalViewInfo Copy = View;
		FMinimalViewInfo::CalculateProjectionMatrixGivenViewRectangle(Copy, Constraint, Rect, Data);
		return Data.ComputeViewProjectionMatrix();
	}

	/** Normalized screen position, (0,0) top-left, (1,1) bottom-right. False when the point is behind the camera. */
	bool ProjectToScreen(const FMatrix& ViewProjection, const FVector& World, FVector2D& OutScreen)
	{
		const FVector4 Clip = ViewProjection.TransformFVector4(FVector4(World, 1.0));
		if (Clip.W <= 0.0)
		{
			return false;
		}
		OutScreen.X = 0.5 + 0.5 * Clip.X / Clip.W;
		OutScreen.Y = 0.5 - 0.5 * Clip.Y / Clip.W;
		return true;
	}

	bool SampleCandle(FStepCtx& C, FCandleScreenState& S)
	{
		const APlayerController* PC = Cast<APlayerController>(C.Pawn->GetController());
		if (!PC || !PC->PlayerCameraManager)
		{
			return false;
		}
		FVector Flame, FlameTop, WaxTop, WaxBottom;
		if (!GatherCandlePoints(C.Pawn, Flame, FlameTop, WaxTop, WaxBottom))
		{
			return false;
		}
		const FMinimalViewInfo View = PC->PlayerCameraManager->GetCameraCacheView();
		const ULocalPlayer* LP = PC->GetLocalPlayer();
		const EAspectRatioAxisConstraint Constraint = LP ? static_cast<EAspectRatioAxisConstraint>(LP->AspectRatioAxisConstraint.GetValue()) : AspectRatio_MaintainYFOV;

		S.MinFOV = FMath::Min(S.MinFOV, View.FOV);
		S.MaxFOV = FMath::Max(S.MaxFOV, View.FOV);
		++S.Samples;
		S.FlameLocal = View.Rotation.UnrotateVector(Flame - View.Location);

		for (int32 i = 0; i < GNumAspects; ++i)
		{
			const FMatrix VP = BuildViewProjection(View, Constraint, GAspects[i].Aspect);
			FCandleProbe& Probe = S.Probes[i];
			FVector2D P;
			bool bAllFront = true;
			if (ProjectToScreen(VP, Flame, P)) { Probe.Flame.Add(P); } else { bAllFront = false; }
			if (ProjectToScreen(VP, FlameTop, P)) { Probe.FlameTop.Add(P); } else { bAllFront = false; }
			if (ProjectToScreen(VP, WaxTop, P)) { Probe.WaxTop.Add(P); } else { bAllFront = false; }
			if (ProjectToScreen(VP, WaxBottom, P)) { Probe.WaxBottom.Add(P); } else { bAllFront = false; }
			Probe.Behind += bAllFront ? 0 : 1;
		}
		return true;
	}

	void EvaluateCandle(FAutomationTestBase* Test, const FString& Label, const FCandleScreenState& S)
	{
		Test->TestTrue(FString::Printf(TEXT("%s: gathered candle samples (%d)"), *Label, S.Samples), S.Samples >= 10);
		Note(FString::Printf(TEXT("%s: offset %s, flame in camera space %s, FOV %.2f..%.2f, %d samples"), *Label, *S.Offset.ToString(), *S.FlameLocal.ToString(), S.MinFOV, S.MaxFOV, S.Samples));
		for (int32 i = 0; i < GNumAspects; ++i)
		{
			const FCandleProbe& P = S.Probes[i];
			Note(FString::Printf(TEXT("%s @ %s: flame %s | flame top %s | wax top %s | wax bottom %s | behind camera %d"), *Label, GAspects[i].Name,
				*P.Flame.ToString(), *P.FlameTop.ToString(), *P.WaxTop.ToString(), *P.WaxBottom.ToString(), P.Behind));
			Test->TestEqual(*FString::Printf(TEXT("%s @ %s: candle never behind the camera"), *Label, GAspects[i].Name), P.Behind, 0);
			Test->TestTrue(FString::Printf(TEXT("%s @ %s: flame inside the frame with 5%% margin (%s)"), *Label, GAspects[i].Name, *P.Flame.ToString()), P.Flame.InsideFrame());
			Test->TestTrue(FString::Printf(TEXT("%s @ %s: flame top inside the frame with 5%% margin (%s)"), *Label, GAspects[i].Name, *P.FlameTop.ToString()), P.FlameTop.InsideFrame());
			Test->TestTrue(FString::Printf(TEXT("%s @ %s: wax top inside the frame with 5%% margin (%s)"), *Label, GAspects[i].Name, *P.WaxTop.ToString()), P.WaxTop.InsideFrame());
			Test->TestTrue(FString::Printf(TEXT("%s @ %s: flame in the lower-right quadrant, x>%.2f y>%.2f (%s)"), *Label, GAspects[i].Name, GLowerRightMin, GLowerRightMin, *P.Flame.ToString()),
				P.Flame.N > 0 && P.Flame.Min.X > GLowerRightMin && P.Flame.Min.Y > GLowerRightMin);
		}
	}

	/** Holds the stance, waits for it to settle, samples the candle for 0.6 s, evaluates, then restores the tuning's offset. */
	void AddCandleCase(FFeelRunner& R, const TSharedRef<FCandleScreenState>& S, FAutomationTestBase* Test, const FString& Label, ECandleStance Stance,
		TFunction<FVector(const ALBCharacter*)> OffsetFn)
	{
		const FString FullLabel = FString::Printf(TEXT("%s, %s"), *Label, StanceName(Stance));
		R.Add(*FString::Printf(TEXT("Candle on screen: %s"), *FullLabel), [S, Test, FullLabel, Stance, OffsetFn](FStepCtx& C)
		{
			ULBCandleComponent* Candle = C.Pawn->GetCandle();
			if (!Test->TestNotNull(TEXT("Pawn has a candle"), Candle))
			{
				return true;
			}
			if (C.bFirst)
			{
				C.Input = FFeelInput();
				Place(C.Pawn, GStartX);
				S->Offset = OffsetFn(C.Pawn);
				Candle->SetRelativeLocation(S->Offset);
				S->Reset();
			}
			if (Stance == ECandleStance::Crouch)
			{
				C.Input.bCrouch = true;
			}
			else if (Stance == ECandleStance::Sprint)
			{
				DriveInput(C.Input, ELBGait::Sprint);
			}
			const double Settle = Stance == ECandleStance::Stand ? 0.5 : (Stance == ECandleStance::Crouch ? 1.0 : 1.8);
			const bool bReady = C.Elapsed >= Settle
				&& (Stance != ECandleStance::Crouch || C.Pawn->bIsCrouched)
				&& (Stance != ECandleStance::Sprint || C.Pawn->GetGait() == ELBGait::Sprint);
			if (!bReady)
			{
				return false;
			}
			if (S->SampleStart < 0.0)
			{
				S->SampleStart = C.Elapsed;
			}
			SampleCandle(C, *S);
			if (C.Elapsed < S->SampleStart + 0.6)
			{
				return false;
			}
			C.Input = FFeelInput();
			EvaluateCandle(Test, FullLabel, *S);
			Candle->SetRelativeLocation(C.Pawn->GetTuning().CandleHeldOffset);
			return true;
		}, 60.f);

		if (Stance == ECandleStance::Crouch)
		{
			R.Add(TEXT("Candle on screen: stand back up"), [](FStepCtx& C)
			{
				C.Input = FFeelInput();
				return C.Elapsed >= 0.8 && !C.Pawn->bIsCrouched;
			});
		}
		else if (Stance == ECandleStance::Sprint)
		{
			AddStopStep(R, TEXT("Candle on screen: stop"));
		}
	}

	void AddCandleCases(FFeelRunner& R, const TSharedRef<FCandleScreenState>& S, FAutomationTestBase* Test, const FString& Label, const TFunction<FVector(const ALBCharacter*)>& OffsetFn)
	{
		for (const ECandleStance Stance : { ECandleStance::Stand, ECandleStance::Crouch, ECandleStance::Sprint })
		{
			AddCandleCase(R, S, Test, Label, Stance, OffsetFn);
		}
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBFeelCandleOnScreenTest, "LastBell.Functional.PlayerFeel.CandleOnScreen",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBFeelCandleOnScreenTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FFeelRunner> R = StartSession(this);
	const TSharedRef<FState> Setup = MakeShared<FState>();
	const TSharedRef<FCandleScreenState> S = MakeShared<FCandleScreenState>();
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, Setup, Test);

	// 1. The offset the pawn really uses (BP_LBCharacter -> DA_PlayerTuning).
	AddCandleCases(*R, S, Test, TEXT("DA_PlayerTuning offset"), [](const ALBCharacter* P) { return P->GetTuning().CandleHeldOffset; });

	// 2. The C++ default, so it stays a safe fallback (only when the asset overrides it).
	const ULBPlayerTuningData* Asset = LoadObject<ULBPlayerTuningData>(nullptr, TEXT("/Game/LastBell/Data/DA_PlayerTuning.DA_PlayerTuning"));
	const FVector DefaultOffset = GetDefault<ULBPlayerTuningData>()->CandleHeldOffset;
	if (!Asset)
	{
		AddError(TEXT("DA_PlayerTuning could not be loaded"));
	}
	else if (!Asset->CandleHeldOffset.Equals(DefaultOffset, 0.01))
	{
		AddCandleCases(*R, S, Test, TEXT("C++ default offset"), [DefaultOffset](const ALBCharacter*) { return DefaultOffset; });
	}
	else
	{
		UE_LOG(LogLB, Display, TEXT("[PlayerFeel] DA_PlayerTuning.CandleHeldOffset equals the C++ default %s: one pass covers both"), *DefaultOffset.ToString());
	}

	// 3. What-if sweep without touching any asset: LB_CANDLE_OFFSETS="x,y,z;x,y,z" is measured and asserted like the real offset.
	const FString Env = FPlatformMisc::GetEnvironmentVariable(TEXT("LB_CANDLE_OFFSETS"));
	if (!Env.IsEmpty())
	{
		TArray<FString> Entries;
		Env.ParseIntoArray(Entries, TEXT(";"));
		for (const FString& Entry : Entries)
		{
			FVector V;
			TArray<FString> Parts;
			Entry.ParseIntoArray(Parts, TEXT(","));
			if (Parts.Num() == 3)
			{
				V = FVector(FCString::Atod(*Parts[0]), FCString::Atod(*Parts[1]), FCString::Atod(*Parts[2]));
				AddCandleCases(*R, S, Test, FString::Printf(TEXT("what-if %s"), *V.ToString()), [V](const ALBCharacter*) { return V; });
			}
		}
	}

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// 8. P3-BUG: real raw mouse input must rotate the held note (and only the note)
// =====================================================================================================================
namespace
{
	/** One frame of raw mouse movement through the game viewport, the same entry the OS mouse uses. False when the viewport ignored it. */
	bool SendRawMouse(ALBCharacter* Pawn, float DX, float DY)
	{
		UWorld* W = Pawn->GetWorld();
		UGameViewportClient* VC = W ? W->GetGameViewport() : nullptr;
		const APlayerController* PC = Cast<APlayerController>(Pawn->GetController());
		const ULocalPlayer* LP = PC ? PC->GetLocalPlayer() : nullptr;
		if (!VC || !VC->Viewport || !LP)
		{
			return false;
		}
		const FInputDeviceId Device = IPlatformInputDeviceMapper::Get().GetPrimaryInputDeviceForUser(LP->GetPlatformUserId());
		const float DeltaTime = W->GetDeltaSeconds();
		bool bHandled = true;
		if (DX != 0.f)
		{
			bHandled &= VC->InputAxis(FInputKeyEventArgs(VC->Viewport, Device, EKeys::MouseX, DX, DeltaTime, 1, FPlatformTime::Cycles64()));
		}
		if (DY != 0.f)
		{
			bHandled &= VC->InputAxis(FInputKeyEventArgs(VC->Viewport, Device, EKeys::MouseY, DY, DeltaTime, 1, FPlatformTime::Cycles64()));
		}
		return bHandled;
	}

	FQuat ItemInCamera(const ALBCharacter* Pawn, const AActor* Item)
	{
		FVector Loc;
		FRotator Rot;
		Pawn->GetController()->GetPlayerViewPoint(Loc, Rot);
		return Rot.Quaternion().Inverse() * Item->GetActorQuat();
	}

	struct FRealInputState
	{
		FRotator ControlBefore = FRotator::ZeroRotator;
		FQuat ItemBefore = FQuat::Identity;
		int32 StartFrame = 0;
		bool bAllHandled = true;
		float OriginalRate = -1.f;
	};

	constexpr int32 GMouseFrames = 20;
	constexpr float GMouseCountsPerFrame = 5.f;
	constexpr int32 GMouseSettleFrames = 6;

	/** Drives GMouseFrames frames of raw mouse input, lets it settle, and calls Check(deltaItemDegrees, controlRotationChanged). */
	void AddMouseStep(FFeelRunner& R, const TSharedRef<FRealInputState>& St, const FString& Name, float DX, float DY,
		TFunction<void(FStepCtx&, float, const FRotator&, const FRotator&)> Check)
	{
		R.Add(*Name, [St, DX, DY, Check](FStepCtx& C)
		{
			APlayerController* PC = Cast<APlayerController>(C.Pawn->GetController());
			if (!PC)
			{
				return true;
			}
			if (C.bFirst)
			{
				St->ControlBefore = PC->GetControlRotation();
				St->bAllHandled = true;
				if (const AActor* Item = C.Pawn->GetInspection()->GetInspected() ? C.Pawn->GetInspection()->GetInspected()->GetOwner() : nullptr)
				{
					St->ItemBefore = ItemInCamera(C.Pawn, Item);
				}
			}
			if (C.Frames < GMouseFrames)
			{
				St->bAllHandled &= SendRawMouse(C.Pawn, DX, DY);
				return false;
			}
			if (C.Frames < GMouseFrames + GMouseSettleFrames)
			{
				return false;
			}
			float ItemDegrees = 0.f;
			if (const ULBInspectableComponent* Inspected = C.Pawn->GetInspection()->GetInspected())
			{
				ItemDegrees = FMath::RadiansToDegrees(static_cast<float>(St->ItemBefore.AngularDistance(ItemInCamera(C.Pawn, Inspected->GetOwner()))));
			}
			Check(C, ItemDegrees, St->ControlBefore, PC->GetControlRotation());
			return true;
		});
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBFeelInspectRealInputTest, "LastBell.Functional.PlayerFeel.InspectRealInput",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBFeelInspectRealInputTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FFeelRunner> R = StartSession(this);
	const TSharedRef<FState> S = MakeShared<FState>();
	const TSharedRef<FRealInputState> St = MakeShared<FRealInputState>();
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, S, Test);
	const FString L = TEXT("real input");

	AddPlaceStep(*R, L);

	// Harness check: with no item, raw MouseX must turn the camera through IMC_LB_MouseLook -> IA_Look. Without this the rest proves nothing.
	AddMouseStep(*R, St, TEXT("Harness: raw MouseX turns the camera when not inspecting"), GMouseCountsPerFrame, 0.f,
		[Test, St](FStepCtx& C, float, const FRotator& Before, const FRotator& After)
		{
			const float Yaw = FMath::Abs(FRotator::NormalizeAxis(After.Yaw - Before.Yaw));
			Note(FString::Printf(TEXT("Harness: IgnoreInput=%d, all raw events handled=%d, camera yaw changed %.2f deg"),
				GEngine->GameViewport ? GEngine->GameViewport->IgnoreInput() : -1, St->bAllHandled, Yaw));
			Test->TestFalse(TEXT("The game viewport does not ignore input"), GEngine->GameViewport && GEngine->GameViewport->IgnoreInput());
			Test->TestTrue(TEXT("The game viewport accepted every raw mouse event"), St->bAllHandled);
			Test->TestTrue(FString::Printf(TEXT("Raw MouseX turned the camera (yaw changed %.2f deg)"), Yaw), Yaw > 1.f);
			C.Pawn->GetController()->SetControlRotation(FRotator::ZeroRotator);
		});

	AddSpawnStep(*R, S, Test, L, GNoteClassPath, false);
	AddBeginStep(*R, S, Test, L);

	R->Add(TEXT("Inspecting: wait for the item to arrive, dump the input setup"), [S, St, Test](FStepCtx& C)
	{
		if (!C.Pawn->GetInspection()->IsInspecting())
		{
			Test->AddError(TEXT("Not inspecting when the mouse test was due"));
			return true;
		}
		if (C.Elapsed < C.Pawn->GetTuning().InspectBlendTime + 0.3)
		{
			return false;
		}
		// What-if without touching the asset: LB_INSPECT_RATE overrides DA_PlayerTuning.InspectRotateRate in memory for this run only.
		const FString RateEnv = FPlatformMisc::GetEnvironmentVariable(TEXT("LB_INSPECT_RATE"));
		if (!RateEnv.IsEmpty() && C.Pawn->Tuning && St->OriginalRate < 0.f)
		{
			St->OriginalRate = C.Pawn->Tuning->InspectRotateRate;
			C.Pawn->Tuning->InspectRotateRate = static_cast<float>(FCString::Atod(*RateEnv));
			Note(FString::Printf(TEXT("WHAT-IF: InspectRotateRate %.2f (asset has %.2f)"), C.Pawn->Tuning->InspectRotateRate, St->OriginalRate));
		}
		Note(FString::Printf(TEXT("Tuning InspectRotateRate = %.2f deg per input unit"), C.Pawn->GetTuning().InspectRotateRate));
		const ALBPlayerController* PC = Cast<ALBPlayerController>(C.Pawn->GetController());
		Test->TestTrue(TEXT("Inspect mapping context is active"), InspectContextActive(C.Pawn));
		Test->TestNotNull(TEXT("Pawn has InspectRotateAction"), C.Pawn->InspectRotateAction.Get());
		if (PC && PC->InspectMappingContext)
		{
			Note(FString::Printf(TEXT("Inspect context priority %d (gameplay contexts are added at 0)"), PC->InspectMappingPriority));
			for (const FEnhancedActionKeyMapping& M : PC->InspectMappingContext->GetMappings())
			{
				Note(FString::Printf(TEXT("  IMC_Inspect: %s -> %s (modifiers %d, triggers %d)"), *M.Key.ToString(), *GetNameSafe(M.Action), M.Modifiers.Num(), M.Triggers.Num()));
			}
			for (const TObjectPtr<UInputMappingContext>& Context : PC->MappingContexts)
			{
				for (const FEnhancedActionKeyMapping& M : Context->GetMappings())
				{
					if (M.Key == EKeys::Mouse2D)
					{
						Note(FString::Printf(TEXT("  %s: %s -> %s"), *GetNameSafe(Context), *M.Key.ToString(), *GetNameSafe(M.Action)));
					}
				}
			}
		}
		if (const UInputAction* Rotate = C.Pawn->InspectRotateAction)
		{
			Note(FString::Printf(TEXT("IA_InspectRotate: ValueType %d (Axis2D=%d), bConsumeInput %d, triggers %d, modifiers %d"), static_cast<int32>(Rotate->ValueType),
				static_cast<int32>(EInputActionValueType::Axis2D), Rotate->bConsumeInput, Rotate->Triggers.Num(), Rotate->Modifiers.Num()));
		}
		return true;
	});


	// 100 raw mouse counts (about 10% of a 1000 px drag) must visibly turn the note: at least 15 degrees, and not a wild spin either.
	// Raw counts reach the action scaled by the Mouse2D axis sensitivity (0.07), which is what the old tuning value ignored.
	auto CheckNoteRotation = [Test](const TCHAR* Axis, FStepCtx& C, float ItemDegrees, const FRotator& Before, const FRotator& After)
	{
		constexpr float TotalCounts = GMouseFrames * GMouseCountsPerFrame;
		Note(FString::Printf(TEXT("Mouse%s only: %.0f raw counts rotated the note %.2f deg (%.3f deg/count, tuning rate %.2f), control rotation %s -> %s"), Axis, TotalCounts,
			ItemDegrees, ItemDegrees / TotalCounts, C.Pawn->GetTuning().InspectRotateRate, *Before.ToString(), *After.ToString()));
		Test->TestTrue(FString::Printf(TEXT("Mouse%s rotated the held note enough (%.2f deg for %.0f counts, want 15..120)"), Axis, ItemDegrees, TotalCounts), ItemDegrees >= 15.f && ItemDegrees <= 120.f);
		Test->TestTrue(FString::Printf(TEXT("Mouse%s did not turn the camera while inspecting (%s -> %s)"), Axis, *Before.ToString(), *After.ToString()), Before.Equals(After, 0.01f));
	};

	AddMouseStep(*R, St, TEXT("Inspecting: raw MouseX rotates the note, camera stays put"), GMouseCountsPerFrame, 0.f,
		[CheckNoteRotation](FStepCtx& C, float ItemDegrees, const FRotator& Before, const FRotator& After) { CheckNoteRotation(TEXT("X"), C, ItemDegrees, Before, After); });

	AddMouseStep(*R, St, TEXT("Inspecting: raw MouseY rotates the note, camera stays put"), 0.f, GMouseCountsPerFrame,
		[CheckNoteRotation](FStepCtx& C, float ItemDegrees, const FRotator& Before, const FRotator& After) { CheckNoteRotation(TEXT("Y"), C, ItemDegrees, Before, After); });

	R->Add(TEXT("Close the inspection"), [St, Test](FStepCtx& C)
	{
		if (St->OriginalRate >= 0.f && C.Pawn->Tuning)
		{
			C.Pawn->Tuning->InspectRotateRate = St->OriginalRate; // undo the LB_INSPECT_RATE what-if
			St->OriginalRate = -1.f;
		}
		ULBInspectionComponent* Inspection = C.Pawn->GetInspection();
		if (Inspection->IsInspecting() && !Inspection->RequestClose())
		{
			return C.Elapsed > 2.0;
		}
		Test->TestFalse(TEXT("Not inspecting after close"), Inspection->IsInspecting());
		return true;
	});

	AddMouseStep(*R, St, TEXT("After closing: raw MouseX turns the camera again"), GMouseCountsPerFrame, 0.f,
		[Test](FStepCtx& C, float, const FRotator& Before, const FRotator& After)
		{
			const float Yaw = FMath::Abs(FRotator::NormalizeAxis(After.Yaw - Before.Yaw));
			Test->TestTrue(FString::Printf(TEXT("Look works again after the inspection (yaw changed %.2f deg)"), Yaw), Yaw > 1.f);
			Test->TestFalse(TEXT("Inspect context removed"), InspectContextActive(C.Pawn));
		});

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// 9. P3-BUG: a flat note is held face-on to the camera
// =====================================================================================================================
namespace
{
	struct FFaceResult
	{
		bool bValid = false;
		float FaceDot = 0.f; // |thin axis . camera forward|
		float UpDot = 0.f;   // |long axis . camera up|
		FString ThinAxis;
	};

	/** Finds the item's thinnest and longest local axes on its first visible mesh and compares them with the camera. */
	FFaceResult MeasureFaceOn(const ALBCharacter* Pawn, const AActor* Item)
	{
		FFaceResult Out;
		TInlineComponentArray<UStaticMeshComponent*> Meshes(const_cast<AActor*>(Item));
		const UStaticMeshComponent* Mesh = nullptr;
		for (const UStaticMeshComponent* M : Meshes)
		{
			if (M->GetStaticMesh())
			{
				Mesh = M;
				break;
			}
		}
		if (!Mesh)
		{
			return Out;
		}
		const FVector Extent = Mesh->GetStaticMesh()->GetBounds().BoxExtent * Mesh->GetComponentScale();
		int32 Thin = 0, Long = 0;
		for (int32 i = 1; i < 3; ++i)
		{
			if (Extent[i] < Extent[Thin]) { Thin = i; }
			if (Extent[i] > Extent[Long]) { Long = i; }
		}
		const FQuat Q = Mesh->GetComponentQuat();
		const FVector ThinWorld = Q.RotateVector(FVector(Thin == 0, Thin == 1, Thin == 2));
		const FVector LongWorld = Q.RotateVector(FVector(Long == 0, Long == 1, Long == 2));
		FVector Loc;
		FRotator Rot;
		Pawn->GetController()->GetPlayerViewPoint(Loc, Rot);
		const FRotationMatrix RM(Rot);
		Out.bValid = true;
		Out.FaceDot = static_cast<float>(FMath::Abs(FVector::DotProduct(ThinWorld, RM.GetUnitAxis(EAxis::X))));
		Out.UpDot = static_cast<float>(FMath::Abs(FVector::DotProduct(LongWorld, RM.GetUnitAxis(EAxis::Z))));
		Out.ThinAxis = FString::Printf(TEXT("local axis %d (extent %s)"), Thin, *Extent.ToString());
		return Out;
	}

	/** Mode 0: the note as authored (auto face camera). 1: auto-facing off, InitialInspectRotation hand-authored. 2: auto-facing off, rotation zero (negative control: edge-on, the original bug). */
	void AddFaceCase(FFeelRunner& R, const TSharedRef<FState>& S, FAutomationTestBase* Test, const FString& L, int32 Mode)
	{
		AddPlaceStep(R, L);
		AddSpawnStep(R, S, Test, L, GNoteClassPath, false);

		if (Mode != 0)
		{
			// Camera space is X forward, Y right, Z up; the sheet's Z (thin) axis must point back at the camera, its Y (long) axis up.
			R.Add(*FString::Printf(TEXT("%s: auto-facing off"), *L), [S, Test, L, Mode](FStepCtx& C)
			{
				AActor* Item = S->Item.Get();
				ULBInspectableComponent* Inspectable = Item ? Item->FindComponentByClass<ULBInspectableComponent>() : nullptr;
				if (!Test->TestNotNull(TEXT("Note has an inspectable component"), Inspectable))
				{
					return true;
				}
				Inspectable->bAutoFaceCamera = false;
				if (Mode == 1)
				{
					Inspectable->InitialInspectRotation = FRotationMatrix::MakeFromZY(FVector(-1.0, 0.0, 0.0), FVector(0.0, 0.0, 1.0)).Rotator();
				}
				Note(FString::Printf(TEXT("%s: InitialInspectRotation = %s (camera space)"), *L, *Inspectable->InitialInspectRotation.ToString()));
				return true;
			});
		}

		AddBeginStep(R, S, Test, L);

		R.Add(*FString::Printf(TEXT("%s: held orientation"), *L), [S, Test, L, Mode](FStepCtx& C)
		{
			AActor* Item = S->Item.Get();
			if (!Item || !C.Pawn->GetInspection()->IsInspecting())
			{
				Test->AddError(FString::Printf(TEXT("%s: not inspecting when the orientation check was due"), *L));
				return true;
			}
			if (C.Elapsed < C.Pawn->GetTuning().InspectBlendTime + 0.3)
			{
				return false;
			}
			const FFaceResult F = MeasureFaceOn(C.Pawn, Item);
			if (!Test->TestTrue(FString::Printf(TEXT("%s: note has a static mesh"), *L), F.bValid))
			{
				return true;
			}
			Note(FString::Printf(TEXT("%s: thin axis = %s; |thin . camera forward| = %.3f, |long . camera up| = %.3f"), *L, *F.ThinAxis, F.FaceDot, F.UpDot));
			if (Mode == 2)
			{
				Test->TestTrue(FString::Printf(TEXT("%s: without any alignment the sheet is edge-on (|normal . forward| %.3f < 0.2), as in the bug report"), *L, F.FaceDot), F.FaceDot < 0.2f);
				return true;
			}
			Test->TestTrue(FString::Printf(TEXT("%s: the sheet's face points at the camera (|normal . forward| %.3f >= 0.95)"), *L, F.FaceDot), F.FaceDot >= 0.95f);
			Test->TestTrue(FString::Printf(TEXT("%s: the sheet is upright (|long axis . up| %.3f >= 0.9)"), *L, F.UpDot), F.UpDot >= 0.9f);
			return true;
		});

		R.Add(*FString::Printf(TEXT("%s: close and remove the item"), *L), [S](FStepCtx& C)
		{
			ULBInspectionComponent* Inspection = C.Pawn->GetInspection();
			if (Inspection->IsInspecting() && !Inspection->RequestClose())
			{
				return C.Elapsed > 2.0;
			}
			if (AActor* Item = S->Item.Get())
			{
				Item->Destroy();
			}
			S->Item.Reset();
			return true;
		});
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBFeelInspectFaceOnTest, "LastBell.Functional.PlayerFeel.InspectFlatFacesCamera",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBFeelInspectFaceOnTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FFeelRunner> R = StartSession(this);
	const TSharedRef<FState> S = MakeShared<FState>();
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, S, Test);
	AddFaceCase(*R, S, Test, TEXT("Note as authored (auto face camera)"), 0);
	AddFaceCase(*R, S, Test, TEXT("Note, hand-authored InitialInspectRotation"), 1);
	AddFaceCase(*R, S, Test, TEXT("Note, negative control (no alignment at all)"), 2);
	Enqueue(R);
	return true;
}

#endif
