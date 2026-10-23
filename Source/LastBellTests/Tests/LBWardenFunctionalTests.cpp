#include "Tests/LBRouteBot.h"
#include "Tests/LBWardenTestSink.h"
#include "AI/LBWardenBrainComponent.h"

void ULBWardenTestSink::Bind(ULBWardenBrainComponent* Brain, UWorld* InWorld)
{
	World = InWorld;
	if (Brain)
	{
		Brain->OnStateChanged.AddDynamic(this, &ULBWardenTestSink::HandleStateChanged);
		Brain->OnAttackWindup.AddDynamic(this, &ULBWardenTestSink::HandleAttackWindup);
		Brain->OnPlayerSpotted.AddDynamic(this, &ULBWardenTestSink::HandleSpotted);
		Brain->OnPlayerLost.AddDynamic(this, &ULBWardenTestSink::HandleLost);
	}
}

void ULBWardenTestSink::HandleStateChanged(ELBWardenState OldState, ELBWardenState NewState)
{
	FTransitionRecord Record;
	Record.Time = Now();
	Record.Old = OldState;
	Record.New = NewState;
	Transitions.Add(Record);
}

void ULBWardenTestSink::HandleAttackWindup(float Seconds)
{
	WindupTimes.Add(Now());
	WindupSeconds.Add(Seconds);
}

void ULBWardenTestSink::HandleSpotted()
{
	SpottedTimes.Add(Now());
}

void ULBWardenTestSink::HandleLost()
{
	LostTimes.Add(Now());
}

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Editor.h"
#include "EngineUtils.h"
#include "Tests/AutomationEditorCommon.h"
#include "Engine/World.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/TargetPoint.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "EnhancedInputSubsystems.h"
#include "InputActionValue.h"
#include "Kismet/GameplayStatics.h"
#include "NavigationSystem.h"
#include "AIController.h"
#include "Perception/AIPerceptionComponent.h"
#include "NavMesh/RecastNavMesh.h"
#include "AI/Navigation/NavigationTypes.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "Misc/OutputDevice.h"
#include "Misc/PackageName.h"
#include "AI/LBWarden.h"
#include "AI/LBWardenController.h"
#include "AI/LBWardenMarkers.h"
#include "AI/LBWardenTuningData.h"
#include "Character/LBCandleComponent.h"
#include "Character/LBCharacter.h"
#include "Character/LBPlayerTuningData.h"
#include "Components/LBInteractableComponent.h"
#include "Components/LBInteractorComponent.h"
#include "Save/LBCheckpoint.h"
#include "Save/LBSaveSubsystem.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "UObject/StrongObjectPtr.h"
#include "LBLog.h"

// P5-004 Warden functional tests. Every test loads /Game/LastBell/Maps/L_Test_Warden fresh (one PIE session each) and plays it
// through real injected player input and the Warden's real perception (sight, hearing). The test map has no C++ markers: the
// tests spawn ALBSearchPoint / ALBWardenSpawnPoint / ALBPatrolPoint at the labelled TargetPoints at runtime, and set the
// escalation stage by adding State.Warden.Stage.N tags. The Warden is never moved by a test; only the player is repositioned
// (teleport) when a scenario needs a start position or an escape.

namespace
{
	const TCHAR* GWardenMap = TEXT("/Game/LastBell/Maps/L_Test_Warden");
	const TCHAR* GMonasteryMapPath = TEXT("/Game/LastBell/Maps/L_Monastery");

	void Note(const FString& Text)
	{
		UE_LOG(LogLB, Display, TEXT("[WardenTest] %s"), *Text);
	}

	// ---- Log capture: counts Warden warnings/errors and the stuck-recovery lines ------------------------------------------------
	class FWLogCapture : public FOutputDevice
	{
	public:
		FWLogCapture() { GLog->AddOutputDevice(this); }
		virtual ~FWLogCapture() override { GLog->RemoveOutputDevice(this); }

		virtual void Serialize(const TCHAR* V, ELogVerbosity::Type Verbosity, const FName& Category) override
		{
			if (Category != TEXT("LogLBWarden"))
			{
				return;
			}
			FScopeLock Lock(&Mutex);
			if (Verbosity == ELogVerbosity::Warning)
			{
				++Warnings;
				LastWarning = V;
			}
			else if (Verbosity <= ELogVerbosity::Error)
			{
				++Errors;
				LastWarning = V;
			}
			const FString Line(V);
			if (Line.Contains(TEXT("stuck in")))
			{
				++StuckRepaths;
			}
			if (Line.Contains(TEXT("giving this target up")))
			{
				++StuckGiveUps;
			}
		}

		FCriticalSection Mutex;
		int32 Warnings = 0;
		int32 Errors = 0;
		int32 StuckRepaths = 0;
		int32 StuckGiveUps = 0;
		FString LastWarning;
	};

	struct FWInput
	{
		FVector2D Move = FVector2D::ZeroVector;
		bool bSprint = false;
		bool bCrouch = false;
	};

	/** Shared scratch state for the steps of one test. */
	struct FWS
	{
		TStrongObjectPtr<ULBWardenTestSink> Sink;
		TMap<FString, FTransform> Pts;
		TWeakObjectPtr<ALBWarden> Warden;
		TWeakObjectPtr<ULBWardenBrainComponent> Brain;
		TArray<TFunction<void()>> Cleanups;
		TUniquePtr<FWLogCapture> Log;
		TWeakObjectPtr<UWorld> OldWorld;
		TWeakObjectPtr<AActor> Door;
		TWeakObjectPtr<AActor> Aux;

		// Generic scratch values, named per test where used.
		double T0 = 0.0, T1 = 0.0, T2 = 0.0, T3 = 0.0;
		double Acc0 = 0.0, Acc1 = 0.0;
		float F0 = 0.f, F1 = 0.f;
		int32 I0 = 0, I1 = 0, N0 = 0;
		bool B0 = false, B1 = false;
		FVector V0 = FVector::ZeroVector;
		TArray<FVector> Path;
		TSet<int32> Visited;
		TArray<float> Samples;
		TArray<float> Samples2;
		TArray<FVector> Extra;

		FVector Loc(const TCHAR* Label) const
		{
			const FTransform* T = Pts.Find(Label);
			return T ? T->GetLocation() : FVector::ZeroVector;
		}
		float Yaw(const TCHAR* Label) const
		{
			const FTransform* T = Pts.Find(Label);
			return T ? static_cast<float>(T->Rotator().Yaw) : 0.f;
		}
		bool Has(const TCHAR* Label) const { return Pts.Contains(Label); }
	};

	struct FWCtx
	{
		UWorld* W = nullptr;
		ALBCharacter* Pawn = nullptr;
		FWInput& Input;
		FWS& S;
		FAutomationTestBase* T = nullptr;
		double Now = 0.0;
		double Elapsed = 0.0;
		int32 Frames = 0;
		bool bFirst = false;

		ULBWardenBrainComponent* Brain() const { return S.Brain.Get(); }
		ALBWarden* Warden() const { return S.Warden.Get(); }
		ELBWardenState State() const { return S.Brain.IsValid() ? S.Brain->GetState() : ELBWardenState::Dormant; }
		FVector WardenLoc() const { return S.Warden.IsValid() ? S.Warden->GetActorLocation() : FVector::ZeroVector; }
	};

	/** Runs the steps in order. A step returns true when finished. Wall-clock timeout per step; tears the session down at the end. */
	class FWRunner : public IAutomationLatentCommand
	{
	public:
		using FStepFn = TFunction<bool(FWCtx&)>;

		explicit FWRunner(FAutomationTestBase* InTest)
			: S(MakeShared<FWS>()), Test(InTest), WardenOn(true)
		{
			S->Log = MakeUnique<FWLogCapture>();
		}

		void Add(const TCHAR* Name, FStepFn Fn, float WallTimeout = 40.f, bool bTolerateNoPawn = false)
		{
			Steps.Add({ Name, WallTimeout, bTolerateNoPawn, MoveTemp(Fn) });
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
				if (StepIndex > 0 && !Step.bTolerateNoPawn && (!W || !P))
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

			FWCtx Ctx{ W, P, Input, *S, Test };
			Ctx.Now = W ? W->GetTimeSeconds() : 0.0;
			Ctx.Elapsed = Ctx.Now - WorldStart;
			Ctx.Frames = Frames;
			Ctx.bFirst = (Frames == 0);
			++Frames;

			const bool bDone = Step.Fn(Ctx);
			if (P && !P->IsDead())
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

		TSharedRef<FWS> S;

	private:
		struct FStep
		{
			FString Name;
			float Timeout;
			bool bTolerateNoPawn;
			FStepFn Fn;
		};

		int32 ErrCount() const
		{
			FAutomationTestExecutionInfo Info;
			Test->GetExecutionInfo(Info);
			return Info.GetErrorTotal();
		}

		/** Re-sent every frame: injected input only lives for one input tick. */
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
			Input = FWInput();
			TeardownStart = FPlatformTime::Seconds();
			for (const TFunction<void()>& Cleanup : S->Cleanups)
			{
				Cleanup();
			}
			S->Cleanups.Reset();
			// Warden warnings/errors are never expected in any scenario.
			Test->TestEqual(TEXT("LogLBWarden errors during the test"), S->Log->Errors, 0);
			Test->TestEqual(TEXT("LogLBWarden warnings during the test"), S->Log->Warnings, 0);
			if (S->Log->Warnings > 0)
			{
				Test->AddInfo(FString::Printf(TEXT("Last LogLBWarden warning: %s"), *S->Log->LastWarning));
			}
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
		LBPie::FWardenSwitch WardenOn;
		TArray<FStep> Steps;
		FWInput Input;
		int32 StepIndex = 0;
		int32 Frames = 0;
		bool bEntered = false;
		bool bTearingDown = false;
		double WallStart = 0.0;
		double WorldStart = 0.0;
		double TeardownStart = 0.0;
		int32 ErrorsAtStart = 0;
	};

	TSharedPtr<FWRunner> StartSession(FAutomationTestBase* Test, const TCHAR* Map = nullptr)
	{
		LBPie::ClearSlot();
		FAutomationEditorCommonUtils::LoadMap(Map ? Map : GWardenMap);
		FRequestPlaySessionParams PlayParams;
		PlayParams.WorldType = EPlaySessionWorldType::PlayInEditor;
		GEditor->RequestPlaySession(PlayParams);
		return MakeShared<FWRunner>(Test);
	}

	void Enqueue(const TSharedPtr<FWRunner>& Runner)
	{
		FAutomationTestFramework::Get().EnqueueLatentCommand(Runner);
	}

	// ---- Scenario helpers -------------------------------------------------------------------------------------------------------

	FGameplayTag StageTag(int32 Stage)
	{
		return LBPie::Tag(*FString::Printf(TEXT("State.Warden.Stage.%d"), Stage));
	}

	void SetStage(UWorld* W, int32 Stage)
	{
		if (ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(W))
		{
			State->AddState(StageTag(Stage));
		}
	}

	float Dist2D(const FVector& A, const FVector& B)
	{
		return static_cast<float>(FVector::DistXY(A, B));
	}

	/** Floor height under XY (traces from above, ignoring the pawns). */
	float FloorZ(UWorld* W, const FVector& XY, const AActor* IgnoreA, const AActor* IgnoreB)
	{
		FCollisionQueryParams Params(SCENE_QUERY_STAT(LBWardenFloor), false, IgnoreA);
		Params.AddIgnoredActor(IgnoreB);
		FHitResult Hit;
		if (W->LineTraceSingleByChannel(Hit, FVector(XY.X, XY.Y, 800.f), FVector(XY.X, XY.Y, -300.f), ECC_Visibility, Params))
		{
			return static_cast<float>(Hit.ImpactPoint.Z);
		}
		return 0.f;
	}

	/** Teleports the player onto the floor at XY facing Yaw, at rest. No fall, so no landing noise. */
	void PlacePlayer(FWCtx& C, const FVector& XY, float Yaw)
	{
		ALBCharacter* P = C.Pawn;
		const float Half = P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
		const float Z = FloorZ(C.W, XY, P, C.Warden()) + Half + 1.f;
		P->SetActorLocationAndRotation(FVector(XY.X, XY.Y, Z), FRotator(0.f, Yaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
		if (UCharacterMovementComponent* M = P->GetCharacterMovement())
		{
			M->StopMovementImmediately();
		}
		if (AController* PC = P->GetController())
		{
			PC->SetControlRotation(FRotator(0.f, Yaw, 0.f));
		}
		C.Input = FWInput();
	}

	void LookYaw(FWCtx& C, float Yaw)
	{
		if (AController* PC = C.Pawn->GetController())
		{
			PC->SetControlRotation(FRotator(0.f, Yaw, 0.f));
		}
	}

	/** Steers toward Target: aims the control rotation at it and holds forward. Returns the remaining flat distance. */
	float DriveToward(FWCtx& C, const FVector& Target, bool bSprint, bool bCrouch = false)
	{
		const FVector To = Target - C.Pawn->GetActorLocation();
		const float Dist = static_cast<float>(FVector(To.X, To.Y, 0.0).Size());
		if (Dist > 1.f)
		{
			LookYaw(C, static_cast<float>(FVector(To.X, To.Y, 0.0).Rotation().Yaw));
		}
		C.Input.Move = FVector2D(0.0, 1.0);
		C.Input.bSprint = bSprint && !bCrouch;
		C.Input.bCrouch = bCrouch;
		return Dist;
	}

	void StandStill(FWCtx& C)
	{
		C.Input = FWInput();
	}

	/** Walks the path point by point (index kept in Index). Returns true after the last point is reached. */
	bool FollowPath(FWCtx& C, const TArray<FVector>& Path, int32& Index, bool bSprint, float Reach = 120.f)
	{
		if (Index >= Path.Num())
		{
			StandStill(C);
			return true;
		}
		if (DriveToward(C, Path[Index], bSprint) <= Reach)
		{
			++Index;
		}
		return false;
	}

	/** Paces back and forth between A and B. */
	void Pace(FWCtx& C, const FVector& A, const FVector& B, bool bSprint, bool bCrouch, int32& Leg)
	{
		const FVector& Target = (Leg % 2 == 0) ? B : A;
		if (DriveToward(C, Target, bSprint, bCrouch) <= 40.f)
		{
			++Leg;
		}
	}

	float Speed2D(const AActor* A) { return static_cast<float>(A->GetVelocity().Size2D()); }

	bool OnGround(const ACharacter* Ch)
	{
		const UCharacterMovementComponent* M = Ch->GetCharacterMovement();
		return M && M->IsMovingOnGround();
	}

	AStaticMeshActor* SpawnBox(UWorld* W, const FVector& Center, const FVector& SizeCm, const TCHAR* Label)
	{
		UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
		if (!Cube)
		{
			return nullptr;
		}
		AStaticMeshActor* Box = W->SpawnActor<AStaticMeshActor>(Center, FRotator::ZeroRotator);
		if (!Box)
		{
			return nullptr;
		}
		Box->SetMobility(EComponentMobility::Movable);
		Box->GetStaticMeshComponent()->SetStaticMesh(Cube);
		Box->SetActorScale3D(SizeCm / 100.f);
		Box->SetActorLabel(Label);
		return Box;
	}

	/** Diagnostic: what can the Warden's eyes see of the player right now. */
	void DumpSight(FWCtx& C)
	{
		ALBWarden* Warden = C.Warden();
		ALBCharacter* Player = C.Pawn;
		if (!Warden || !Player)
		{
			return;
		}
		FVector Eye;
		FRotator EyeRot;
		Warden->GetActorEyesViewPoint(Eye, EyeRot);
		const FVector Fwd = Warden->GetActorRotation().Vector();
		const FVector To = Player->GetActorLocation() - Eye;
		const float AngleDeg = FMath::RadiansToDegrees(FMath::Acos(FVector::DotProduct(Fwd, To.GetSafeNormal())));
		FCollisionQueryParams Params(SCENE_QUERY_STAT(LBWardenDump), false, Warden);
		FHitResult Hit;
		const bool bHit = C.W->LineTraceSingleByChannel(Hit, Eye, Player->GetActorLocation(), ECC_Visibility, Params);
		FString Info = FString::Printf(TEXT("DumpSight: eye %s, warden yaw %.0f, angle to player %.0f deg, dist %.0f, trace hit %d (%s / %s)"), *Eye.ToCompactString(),
			Warden->GetActorRotation().Yaw, AngleDeg, To.Size(), bHit ? 1 : 0, bHit ? *GetNameSafe(Hit.GetActor()) : TEXT("-"), bHit ? *GetNameSafe(Hit.GetComponent()) : TEXT("-"));
		if (const AAIController* AI = Cast<AAIController>(Warden->GetController()))
		{
			if (const UAIPerceptionComponent* Perception = AI->GetAIPerceptionComponent())
			{
				TArray<AActor*> Known;
				Perception->GetKnownPerceivedActors(nullptr, Known);
				Info += FString::Printf(TEXT("; perception known actors %d"), Known.Num());
				if (const FActorPerceptionInfo* ActorInfo = Perception->GetActorInfo(*Player))
				{
					for (const FAIStimulus& St : ActorInfo->LastSensedStimuli)
					{
						Info += FString::Printf(TEXT(" [stim type %d sensed %d age %.1f strength %.2f]"), (int32)St.Type.Index, St.WasSuccessfullySensed() ? 1 : 0, St.GetAge(), St.Strength);
					}
				}
				else
				{
					Info += TEXT("; player not in perception info");
				}
			}
		}
		Note(Info);
	}

	// ---- Setup -----------------------------------------------------------------------------------------------------------------

	struct FSetup
	{
		/** TargetPoint label where the ALBWardenSpawnPoint goes (the test map's Warden-side post). */
		const TCHAR* SpawnLabel = TEXT("Spawn_Warden");
		/** Facing of the spawn point; NaN = the TargetPoint's yaw. */
		float SpawnYaw = TNumericLimits<float>::Max();
		bool bSearchPoints = true;
		/** Three extra search points packed along the far loop corridor (the TargetPoints are 1.6 km apart: more than a 12 s search can cover). */
		bool bSearchCluster = false;
		bool bPatrolRoute = false;
		const TCHAR* PlayerLabel = TEXT("Spawn_Player");
		int32 MinStage = 3;
	};

	static const FVector SearchClusterPoints[] = { FVector(500.0, 4650.0, 0.0), FVector(-500.0, 4650.0, 0.0), FVector(0.0, 4300.0, 0.0) };

	void AddSetupSteps(FWRunner& R, const FSetup& Setup, FAutomationTestBase* Test)
	{
		const TSharedRef<FWS> S = R.S;
		R.Add(TEXT("PIE ready, markers spawned"), [S, Test, Setup](FWCtx& C)
		{
			if (!LBPie::WorldReady() || C.Frames < 5)
			{
				return false;
			}
			for (TActorIterator<ALBWarden> It(C.W); It; ++It)
			{
				S->Warden = *It;
			}
			if (!S->Warden.IsValid())
			{
				Test->AddError(TEXT("No ALBWarden in L_Test_Warden"));
				return true;
			}
			S->Brain = S->Warden->GetBrain();
			if (!S->Brain.IsValid())
			{
				// The controller possesses the pawn during BeginPlay; give it a few frames.
				return C.Frames > 60;
			}
			S->Sink.Reset(NewObject<ULBWardenTestSink>());
			S->Sink->Bind(S->Brain.Get(), C.W);

			for (TActorIterator<ATargetPoint> It(C.W); It; ++It)
			{
				S->Pts.Add(It->GetActorLabel(), It->GetActorTransform());
			}
			Test->TestTrue(TEXT("Test map has Spawn_Warden and Spawn_Player"), S->Has(TEXT("Spawn_Warden")) && S->Has(TEXT("Spawn_Player")));


			FActorSpawnParameters Params;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			if (Setup.bSearchPoints)
			{
				for (const TCHAR* Label : { TEXT("Search_1"), TEXT("Search_2"), TEXT("Search_3"), TEXT("Search_4") })
				{
					const FVector L = S->Loc(Label);
					C.W->SpawnActor<ALBSearchPoint>(FVector(L.X, L.Y, 0.0), FRotator::ZeroRotator, Params);
				}
			}
			if (Setup.bSearchCluster)
			{
				for (const FVector& L : SearchClusterPoints)
				{
					C.W->SpawnActor<ALBSearchPoint>(L, FRotator::ZeroRotator, Params);
				}
			}
			const FVector SpawnLoc = S->Loc(Setup.SpawnLabel);
			const float Yaw = Setup.SpawnYaw == TNumericLimits<float>::Max() ? S->Yaw(Setup.SpawnLabel) : Setup.SpawnYaw;
			if (ALBWardenSpawnPoint* Spawn = C.W->SpawnActor<ALBWardenSpawnPoint>(FVector(SpawnLoc.X, SpawnLoc.Y, 0.0), FRotator(0.f, Yaw, 0.f), Params))
			{
				Spawn->MinStage = Setup.MinStage;
				Spawn->RouteId = Setup.bPatrolRoute ? FName(TEXT("Test")) : NAME_None;
			}
			if (Setup.bPatrolRoute)
			{
				// Order 0: the far-east corner (Loop_NE), order 1: back at the post (Loop_NW).
				const TCHAR* Route[] = { TEXT("Loop_NE"), TEXT("Loop_NW") };
				for (int32 i = 0; i < 2; ++i)
				{
					const FVector L = S->Loc(Route[i]);
					if (ALBPatrolPoint* Point = C.W->SpawnActor<ALBPatrolPoint>(FVector(L.X, L.Y, 0.0), FRotator::ZeroRotator, Params))
					{
						Point->RouteId = TEXT("Test");
						Point->Order = i;
						Point->WaitSeconds = 0.5f;
					}
				}
			}
			return true;
		}, 60.f);

		// Navigation is generated at runtime (RuntimeGeneration=Dynamic): the Warden cannot path until the tiles exist.
		R.Add(TEXT("Navmesh generated"), [S, Test](FWCtx& C)
		{
			UNavigationSystemV1* NavSys = FNavigationSystem::GetCurrent<UNavigationSystemV1>(C.W);
			if (!NavSys)
			{
				Test->AddError(TEXT("No navigation system in the PIE world"));
				return true;
			}
			FNavLocation Projected;
			if (C.Frames == 1)
			{
				// The headless automation session does not auto-build the Dynamic navmesh: build it synchronously once.
				NavSys->Build();
			}
			const FVector Extent(50.0, 50.0, 250.0);
			const bool bReady = !NavSys->IsNavigationBuildInProgress()
				&& NavSys->ProjectPointToNavigation(FVector(0.0, -300.0, 0.0), Projected, Extent)
				&& NavSys->ProjectPointToNavigation(FVector(850.0, 3300.0, 0.0), Projected, Extent)
				&& NavSys->ProjectPointToNavigation(FVector(2000.0, 0.0, 0.0), Projected, Extent);
			if (bReady)
			{
				Note(FString::Printf(TEXT("navmesh ready after %.2fs"), C.Elapsed));
				return true;
			}
			if (C.Elapsed > 40.0)
			{
				Test->AddError(FString::Printf(TEXT("The runtime navmesh never covered the hall, the ring and the dead end (building %d, hall %d, ring %d, deadend %d)"), NavSys->IsNavigationBuildInProgress() ? 1 : 0, NavSys->ProjectPointToNavigation(FVector(0.0, -300.0, 0.0), Projected, Extent) ? 1 : 0, NavSys->ProjectPointToNavigation(FVector(850.0, 3300.0, 0.0), Projected, Extent) ? 1 : 0, NavSys->ProjectPointToNavigation(FVector(2000.0, 0.0, 0.0), Projected, Extent) ? 1 : 0));
				return true;
			}
			return false;
		}, 90.f);

		R.Add(TEXT("Settle the player"), [S, Setup](FWCtx& C)
		{
			if (C.bFirst)
			{
				PlacePlayer(C, S->Loc(Setup.PlayerLabel), S->Yaw(Setup.PlayerLabel));
			}
			if (C.Elapsed < 1.0 || !OnGround(C.Pawn))
			{
				return false;
			}
			S->Sink->Clear();
			return true;
		});
	}

	/** Waits until the Warden has materialized (Patrol, visible). */
	void AddWaitForWarden(FWRunner& R, FAutomationTestBase* Test, float Seconds = 6.f)
	{
		const TSharedRef<FWS> S = R.S;
		R.Add(TEXT("Warden materializes at its post"), [S, Test, Seconds](FWCtx& C)
		{
			if (C.State() == ELBWardenState::Patrol && !C.Warden()->IsHidden())
			{
				Note(FString::Printf(TEXT("Warden up after %.2fs at %s"), C.Elapsed, *C.WardenLoc().ToCompactString()));
				S->Sink->Clear(); // the appearance itself is not part of any scenario
				return true;
			}
			if (C.Elapsed > Seconds)
			{
				Test->AddError(FString::Printf(TEXT("Warden did not appear within %.0fs (state %s)"), Seconds, LBWardenLogic::StateName(C.State())));
				return true;
			}
			return false;
		});
	}

	// Ring scenario: the Warden spawns at the near end of the east corridor, facing +Y.
	FSetup RingSetup()
	{
		FSetup Setup;
		Setup.SpawnLabel = TEXT("Loop_NW");
		Setup.SpawnYaw = 90.f;
		return Setup;
	}

	const FVector RingStand(850.0, 2850.0, 0.0);
}

// =====================================================================================================================
// Gating
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenGateDormantTest, "LastBell.Functional.Warden.Gating.StageTwoDormantAndUnseenAppearance",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenGateDormantTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FWRunner> R = StartSession(this);
	const TSharedRef<FWS> S = R->S;
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, FSetup(), Test);

	R->Add(TEXT("Stage 1 then 2: dormant, hidden, harmless even next to the player"), [S, Test](FWCtx& C)
	{
		if (C.bFirst)
		{
			PlacePlayer(C, FVector(650.0, 0.0, 0.0), 180.f); // 150 cm from the (hidden) Warden's placed location
			SetStage(C.W, 1);
			SetStage(C.W, 2);
		}
		if (C.Elapsed < 3.0)
		{
			return false;
		}
		Test->TestEqual(TEXT("Stage 2 brain stage"), C.Brain()->GetStage(), 2);
		Test->TestEqual(TEXT("Stage 2: Dormant"), static_cast<int32>(C.State()), static_cast<int32>(ELBWardenState::Dormant));
		Test->TestTrue(TEXT("Stage 2: hidden"), C.Warden()->IsHidden());
		Test->TestFalse(TEXT("Stage 2: no collision"), C.Warden()->GetActorEnableCollision());
		Test->TestFalse(TEXT("Stage 2: the player is alive"), C.Pawn->IsDead());
		Test->TestEqual(TEXT("Stage 2: no state change ever"), S->Sink->Transitions.Num(), 0);
		Test->TestEqual(TEXT("Stage 2: never spotted anyone"), S->Sink->SpottedTimes.Num(), 0);
		return true;
	});

	R->Add(TEXT("Stage 3 while the player looks at the spawn point: stays dormant"), [S, Test](FWCtx& C)
	{
		if (C.bFirst)
		{
			PlacePlayer(C, FVector(300.0, 0.0, 0.0), 0.f); // faces +X, the spawn point at (800, 0) is 500 cm ahead, nothing in between
		}
		if (C.Frames == 15)
		{
			SetStage(C.W, 3); // after the camera has caught up with the teleport
		}
		if (C.Elapsed < 2.0)
		{
			return false;
		}
		Test->TestEqual(TEXT("Stage 3 in view: still Dormant"), static_cast<int32>(C.State()), static_cast<int32>(ELBWardenState::Dormant));
		Test->TestTrue(TEXT("Stage 3 in view: still hidden"), C.Warden()->IsHidden());
		return true;
	});

	R->Add(TEXT("The player looks away: it appears at the spawn point"), [S, Test](FWCtx& C)
	{
		if (C.bFirst)
		{
			LookYaw(C, 180.f);
		}
		if (C.State() != ELBWardenState::Dormant)
		{
			Note(FString::Printf(TEXT("Appeared %.2fs after the player looked away, at %s"), C.Elapsed, *C.WardenLoc().ToCompactString()));
			Test->TestFalse(TEXT("Visible once it appears"), C.Warden()->IsHidden());
			Test->TestTrue(TEXT("Appeared at the spawn point"), Dist2D(C.WardenLoc(), S->Loc(TEXT("Spawn_Warden"))) < 60.f);
			Test->TestEqual(TEXT("Entered Patrol (hold the post)"), static_cast<int32>(C.State()), static_cast<int32>(ELBWardenState::Patrol));
			return true;
		}
		if (C.Elapsed > 3.0)
		{
			Test->AddError(TEXT("The Warden did not appear after the player looked away"));
			return true;
		}
		return false;
	});

	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenGateStage3NoiseTest, "LastBell.Functional.Warden.Gating.StageThreeInvestigatesNoise",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenGateStage3NoiseTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FWRunner> R = StartSession(this);
	const TSharedRef<FWS> S = R->S;
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, FSetup(), Test);
	R->Add(TEXT("Stage 3"), [](FWCtx& C) { SetStage(C.W, 3); return true; });
	AddWaitForWarden(*R, Test);

	// Behind Pillar_1 the player is out of sight (the pillar is between the post at X=800 and the run at X=-450).
	R->Add(TEXT("Sprint behind the pillar: heard, investigates; not seen"), [S, Test](FWCtx& C)
	{
		if (C.bFirst)
		{
			PlacePlayer(C, FVector(-450.0, -150.0, 0.0), 90.f);
			S->I0 = 0;
		}
		Pace(C, FVector(-450.0, -150.0, 0.0), FVector(-450.0, 150.0, 0.0), true, false, S->I0);
		if (C.State() == ELBWardenState::Investigate)
		{
			const float ToLkl = Dist2D(C.Brain()->GetLastKnownLocation(), C.Pawn->GetActorLocation());
			Note(FString::Printf(TEXT("Investigate after %.2fs of sprinting; last-known is %.0f cm from the player"), C.Elapsed, ToLkl));
			Test->TestTrue(TEXT("Last-known location is where the noise was"), ToLkl < 350.f);
			Test->TestEqual(TEXT("It never saw the player (heard only)"), S->Sink->SpottedTimes.Num(), 0);
			Test->TestEqual(TEXT("Never Chase at stage 3"), S->Sink->CountEntries(ELBWardenState::Chase), 0);
			StandStill(C);
			return true;
		}
		if (C.Elapsed > 8.0)
		{
			Test->AddError(TEXT("Stage 3 Warden did not investigate a sprinting player 1250 cm away"));
			return true;
		}
		return false;
	});

	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenGateStage3NoChaseTest, "LastBell.Functional.Warden.Gating.StageThreeNeverChases",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenGateStage3NoChaseTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FWRunner> R = StartSession(this);
	const TSharedRef<FWS> S = R->S;
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, FSetup(), Test);
	R->Add(TEXT("Stage 3"), [](FWCtx& C) { SetStage(C.W, 3); return true; });
	AddWaitForWarden(*R, Test);

	R->Add(TEXT("Player in the open at 1400 cm: seen, investigates, never chases"), [S, Test](FWCtx& C)
	{
		if (C.bFirst)
		{
			PlacePlayer(C, FVector(-600.0, -300.0, 0.0), 0.f);
		}
		if (C.Elapsed < 4.5)
		{
			return false;
		}
		Test->TestTrue(TEXT("Spotted"), S->Sink->SpottedTimes.Num() >= 1);
		Test->TestEqual(TEXT("Never Chase at stage 3"), S->Sink->CountEntries(ELBWardenState::Chase), 0);
		Test->TestTrue(TEXT("Investigated"), S->Sink->CountEntries(ELBWardenState::Investigate) >= 1);
		Test->TestFalse(TEXT("Still alive (1400 cm away)"), C.Pawn->IsDead());
		const double Spotted = S->Sink->SpottedTimes.Num() ? S->Sink->SpottedTimes[0] : -1.0;
		const double Investigate = S->Sink->FirstEntry(ELBWardenState::Investigate);
		Note(FString::Printf(TEXT("spotted at %.2f, Investigate at %.2f (lead %.2fs)"), Spotted, Investigate, Investigate - Spotted));
		return true;
	});

	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenGateStage5Test, "LastBell.Functional.Warden.Gating.StageFiveChases",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenGateStage5Test::RunTest(const FString& Parameters)
{
	TSharedPtr<FWRunner> R = StartSession(this);
	const TSharedRef<FWS> S = R->S;
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, FSetup(), Test);
	R->Add(TEXT("Stage 5"), [](FWCtx& C) { SetStage(C.W, 5); return true; });
	AddWaitForWarden(*R, Test);

	// Sight: the player stands in the open, in front of the Warden (cone 90 deg, nothing in between).
	R->Add(TEXT("Player in the open ahead: spotted, tell leads the chase by about the confirm time"), [S, Test](FWCtx& C)
	{
		if (C.bFirst)
		{
			PlacePlayer(C, FVector(200.0, 300.0, 0.0), 0.f);
			S->T0 = C.Now;
		}
		if (C.Frames == 120) { DumpSight(C); }
		const double Chase = S->Sink->FirstEntry(ELBWardenState::Chase);
		if (Chase >= 0.0)
		{
			Test->TestTrue(TEXT("Spotted fired"), S->Sink->SpottedTimes.Num() >= 1);
			const double Spotted = S->Sink->SpottedTimes.Num() ? S->Sink->SpottedTimes[0] : Chase;
			const float Confirm = C.Warden()->GetTuning().SightConfirmTime;
			Note(FString::Printf(TEXT("placed t=0, spotted +%.2fs, chase +%.2fs (tell lead %.2fs, confirm time %.2f)"), Spotted - S->T0, Chase - S->T0, Chase - Spotted, Confirm));
			Test->TestTrue(FString::Printf(TEXT("Audible tell leads the chase by at least 0.5 s (%.2f)"), Chase - Spotted), Chase - Spotted >= 0.5);
			Test->TestTrue(FString::Printf(TEXT("Chase starts about the confirm time after sight (%.2f vs %.2f)"), Chase - Spotted, Confirm),
				FMath::Abs((Chase - Spotted) - Confirm) < 0.25);
			Test->TestTrue(TEXT("Chase never before the spotted tell"), Spotted <= Chase);
			return true;
		}
		if (C.Elapsed > 6.0)
		{
			Test->AddError(TEXT("Stage 5 Warden did not chase a player standing in the open 670 cm ahead"));
			return true;
		}
		return false;
	});

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// Sight
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenSightBlockedTest, "LastBell.Functional.Warden.Sight.BlockedByPillar",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenSightBlockedTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FWRunner> R = StartSession(this);
	const TSharedRef<FWS> S = R->S;
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, FSetup(), Test);
	R->Add(TEXT("Stage 5"), [](FWCtx& C) { SetStage(C.W, 5); return true; });
	AddWaitForWarden(*R, Test);

	R->Add(TEXT("Behind Pillar_1, 1100 cm away inside the cone: no sight for 5 s"), [S, Test](FWCtx& C)
	{
		if (C.bFirst)
		{
			PlacePlayer(C, FVector(-300.0, 0.0, 0.0), 0.f);
		}
		if (C.Elapsed < 5.0)
		{
			return false;
		}
		Test->TestEqual(TEXT("Never spotted behind the pillar"), S->Sink->SpottedTimes.Num(), 0);
		Test->TestEqual(TEXT("Still holding the post (Patrol)"), static_cast<int32>(C.State()), static_cast<int32>(ELBWardenState::Patrol));
		Test->TestEqual(TEXT("No state change at all"), S->Sink->Transitions.Num(), 0);
		return true;
	});

	R->Add(TEXT("Walk out from behind the pillar: now it sees and chases"), [S, Test](FWCtx& C)
	{
		if (C.bFirst)
		{
			S->T0 = C.Now;
		}
		DriveToward(C, FVector(-300.0, -300.0, 0.0), false);
		if (C.State() == ELBWardenState::Chase)
		{
			Note(FString::Printf(TEXT("Chase %.2fs after stepping out; spotted %d"), C.Now - S->T0, S->Sink->SpottedTimes.Num()));
			Test->TestTrue(TEXT("Spotted fired before the chase"), S->Sink->SpottedTimes.Num() >= 1);
			StandStill(C);
			return true;
		}
		if (C.Elapsed > 8.0)
		{
			Test->AddError(TEXT("The Warden never saw the player after they stepped out from behind the pillar"));
			return true;
		}
		return false;
	});

	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenSightCandleTest, "LastBell.Functional.Warden.Sight.CandleExtendsDetectionDistance",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenSightCandleTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FWRunner> R = StartSession(this);
	const TSharedRef<FWS> S = R->S;
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, FSetup(), Test);
	R->Add(TEXT("Stage 3"), [](FWCtx& C) { SetStage(C.W, 3); return true; });
	AddWaitForWarden(*R, Test);

	// Stage 3 sight radius is 1500 cm, times 1.25 with the candle lit. The player stands at about 1665 cm in front.
	R->Add(TEXT("Snuff the candle"), [S, Test](FWCtx& C)
	{
		ULBCandleComponent* Candle = C.Pawn->GetCandle();
		if (!Candle)
		{
			Test->AddError(TEXT("Player has no candle"));
			return true;
		}
		if (C.bFirst)
		{
			S->F0 = C.Warden()->GetTuning().GetSightRadiusForStage(3);
			S->F1 = S->F0 * C.Warden()->GetTuning().CandleLitSightMultiplier;
			Note(FString::Printf(TEXT("stage 3 sight radius unlit %.0f, lit %.0f"), S->F0, S->F1));
		}
		if (Candle->IsLit())
		{
			Candle->ToggleCandle();
			return false;
		}
		return !Candle->IsRelighting() && C.Elapsed > 0.3;
	});

	R->Add(TEXT("Candle out at 1690 cm (beyond the unlit radius): not seen for 3.5 s"), [S, Test](FWCtx& C)
	{
		if (C.bFirst)
		{
			PlacePlayer(C, FVector(-850.0, -350.0, 0.0), 0.f);
			const float Distance = Dist2D(C.WardenLoc(), C.Pawn->GetActorLocation());
			Note(FString::Printf(TEXT("player %.0f cm from the Warden"), Distance));
			Test->TestTrue(TEXT("Test distance sits between the unlit and the lit radius"), Distance > S->F0 + 40.f && Distance < S->F1 - 40.f);
		}
		if (C.Elapsed < 3.5)
		{
			return false;
		}
		Test->TestFalse(TEXT("Candle is out"), C.Pawn->GetCandle()->IsLit());
		Test->TestEqual(TEXT("Candle out: never spotted at the edge"), S->Sink->SpottedTimes.Num(), 0);
		return true;
	});

	R->Add(TEXT("Candle relit: the same spot is now inside the sight radius"), [S, Test](FWCtx& C)
	{
		ULBCandleComponent* Candle = C.Pawn->GetCandle();
		if (C.bFirst)
		{
			Candle->ToggleCandle();
			S->T0 = C.Now;
		}
		if (S->Sink->SpottedTimes.Num() >= 1)
		{
			Test->TestTrue(TEXT("Candle is lit when it was spotted"), Candle->IsLit());
			Note(FString::Printf(TEXT("spotted %.2fs after pressing relight (candle lit: %d)"), S->Sink->SpottedTimes[0] - S->T0, Candle->IsLit() ? 1 : 0));
			return true;
		}
		if (C.Elapsed > 5.0)
		{
			Test->AddError(TEXT("The lit candle did not make the player visible beyond the unlit radius"));
			return true;
		}
		return false;
	});

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// Hearing
// =====================================================================================================================

namespace
{
	// Sound_Outside is in the hall 220 cm from the door, about 1130 cm from the post. The diagonal from the post to it
	// runs through Pillar_3, so a player there cannot be seen: it is heard or nothing.
	const FVector PaceA(-100.0, -800.0, 0.0);
	const FVector PaceB(100.0, -800.0, 0.0);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenHearSprintTest, "LastBell.Functional.Warden.Hearing.SprintIsHeardAndInvestigated",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenHearSprintTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FWRunner> R = StartSession(this);
	const TSharedRef<FWS> S = R->S;
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, FSetup(), Test);
	R->Add(TEXT("Stage 3"), [](FWCtx& C) { SetStage(C.W, 3); return true; });
	AddWaitForWarden(*R, Test);

	R->Add(TEXT("Sprint near Sound_Outside: heard, investigates, walks towards the noise"), [S, Test](FWCtx& C)
	{
		const FVector Noise = S->Loc(TEXT("Sound_Outside"));
		if (C.bFirst)
		{
			PlacePlayer(C, PaceA, 0.f);
			S->I0 = 0;
			S->T1 = -1.0;
			S->F0 = 0.f;
		}
		Pace(C, PaceA, PaceB, true, false, S->I0);
		if (S->T1 < 0.0 && C.State() == ELBWardenState::Investigate)
		{
			S->T1 = C.Now;
			S->F0 = Dist2D(C.WardenLoc(), Noise);
			Note(FString::Printf(TEXT("Investigate %.2fs after the first sprint step; Warden %.0f cm from the noise"), C.Elapsed, S->F0));
			const float LklToNoise = Dist2D(C.Brain()->GetLastKnownLocation(), Noise);
			Test->TestTrue(FString::Printf(TEXT("Investigating the noise location (last-known %.0f cm from Sound_Outside)"), LklToNoise), LklToNoise < 250.f);
			Test->TestEqual(TEXT("Heard, not seen"), S->Sink->SpottedTimes.Num(), 0);
		}
		if (S->T1 >= 0.0 && C.Now - S->T1 >= 3.0)
		{
			const float Now = Dist2D(C.WardenLoc(), Noise);
			Note(FString::Printf(TEXT("3 s later the Warden is %.0f cm from the noise (was %.0f)"), Now, S->F0));
			Test->TestTrue(TEXT("The Warden walks towards the noise"), Now < S->F0 - 300.f);
			Test->TestEqual(TEXT("Never Chase"), S->Sink->CountEntries(ELBWardenState::Chase), 0);
			StandStill(C);
			return true;
		}
		if (C.Elapsed > 10.0)
		{
			Test->AddError(TEXT("Sprinting 1130 cm away was not heard by the Stage 3 Warden"));
			return true;
		}
		return false;
	});

	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenHearCrouchTest, "LastBell.Functional.Warden.Hearing.CrouchIsNotHeard",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenHearCrouchTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FWRunner> R = StartSession(this);
	const TSharedRef<FWS> S = R->S;
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, FSetup(), Test);
	R->Add(TEXT("Stage 3"), [](FWCtx& C) { SetStage(C.W, 3); return true; });
	AddWaitForWarden(*R, Test);

	R->Add(TEXT("Crouch-walk at the same spot for 7 s: no reaction"), [S, Test](FWCtx& C)
	{
		if (C.bFirst)
		{
			PlacePlayer(C, PaceA, 0.f);
			S->I0 = 0;
			S->V0 = C.WardenLoc();
			S->N0 = 0;
		}
		Pace(C, PaceA, PaceB, false, true, S->I0);
		if (C.Pawn->bIsCrouched && Speed2D(C.Pawn) > 20.f)
		{
			++S->N0;
		}
		if (C.Elapsed < 7.0)
		{
			return false;
		}
		Test->TestTrue(FString::Printf(TEXT("The player really was crouch-walking (%d moving frames)"), S->N0), S->N0 > 100);
		Test->TestEqual(TEXT("Crouch noise: no state change"), S->Sink->Transitions.Num(), 0);
		Test->TestEqual(TEXT("Crouch noise: still holding the post"), static_cast<int32>(C.State()), static_cast<int32>(ELBWardenState::Patrol));
		Test->TestTrue(TEXT("The Warden did not move"), Dist2D(C.WardenLoc(), S->V0) < 30.f);
		return true;
	});

	R->Add(TEXT("Control: sprinting at the same spot is heard"), [S, Test](FWCtx& C)
	{
		if (C.bFirst)
		{
			S->I0 = 0;
		}
		Pace(C, PaceA, PaceB, true, false, S->I0);
		if (C.State() == ELBWardenState::Investigate)
		{
			StandStill(C);
			return true;
		}
		if (C.Elapsed > 8.0)
		{
			Test->AddError(TEXT("Control failed: sprinting at the same spot was not heard either"));
			return true;
		}
		return false;
	});

	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenHearDoorTest, "LastBell.Functional.Warden.Hearing.DoorInteractionIsHeard",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenHearDoorTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FWRunner> R = StartSession(this);
	const TSharedRef<FWS> S = R->S;
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, FSetup(), Test);
	R->Add(TEXT("Stage 3"), [](FWCtx& C) { SetStage(C.W, 3); return true; });
	AddWaitForWarden(*R, Test);

	R->Add(TEXT("Face Door_Sound, silent for a second"), [S, Test](FWCtx& C)
	{
		if (C.bFirst)
		{
			for (TActorIterator<AActor> It(C.W); It; ++It)
			{
				if (It->GetActorLabel() == TEXT("Door_Sound"))
				{
					S->Door = *It;
				}
			}
			if (!S->Door.IsValid())
			{
				Test->AddError(TEXT("Door_Sound not found"));
				return true;
			}
			ULBInteractableComponent* Interactable = S->Door->FindComponentByClass<ULBInteractableComponent>();
			if (!Interactable)
			{
				Test->AddError(TEXT("Door_Sound has no ULBInteractableComponent"));
				return true;
			}
			Note(FString::Printf(TEXT("Door_Sound NoiseLoudness = %.2f"), Interactable->NoiseLoudness));
			if (Interactable->NoiseLoudness <= 0.f)
			{
				// The test map door ships silent; the suggested door loudness (design) is 0.6.
				Test->AddInfo(TEXT("Door_Sound NoiseLoudness is 0 in the test map: using the design value 0.6 for this test"));
				Interactable->NoiseLoudness = 0.6f;
			}
			PlacePlayer(C, FVector(0.0, -900.0, 0.0), -90.f); // 120 cm in front of the door, facing it (-Y)
		}
		if (C.Elapsed < 1.0)
		{
			return false;
		}
		Test->TestEqual(TEXT("Silent before the door: no reaction"), S->Sink->Transitions.Num(), 0);
		return true;
	});

	R->Add(TEXT("Open the door: the noise is heard"), [S, Test](FWCtx& C)
	{
		const FGameplayTag DoorOpen = LBPie::Tag(TEXT("State.Test.Door1Open"));
		if (C.bFirst)
		{
			C.Pawn->GetInteractor()->TryInteract();
			S->T0 = C.Now;
		}
		if (!LBPie::HasState(DoorOpen) && C.Elapsed > 1.0)
		{
			Test->AddError(TEXT("The interaction did not open the door (not focused?)"));
			return true;
		}
		if (C.State() == ELBWardenState::Investigate)
		{
			const FVector DoorLoc = S->Door->GetActorLocation();
			const float Lkl = Dist2D(C.Brain()->GetLastKnownLocation(), DoorLoc);
			Note(FString::Printf(TEXT("Investigate %.2fs after the door opened; last-known %.0f cm from the door"), C.Now - S->T0, Lkl));
			Test->TestTrue(TEXT("It investigates the door, not the player"), Lkl < 150.f);
			Test->TestTrue(TEXT("Door state tag added"), LBPie::HasState(DoorOpen));
			Test->TestEqual(TEXT("It heard the door, it did not see the player"), S->Sink->SpottedTimes.Num(), 0);
			return true;
		}
		if (C.Elapsed > 4.0)
		{
			Test->AddError(TEXT("The door interaction noise was not heard"));
			return true;
		}
		return false;
	});

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// Losing the player, repeated chases, chase speed
// =====================================================================================================================

namespace
{
	/** All search point locations used by the ring scenarios (flat). */
	TArray<FVector> RingSearchPoints(const FWS& S)
	{
		TArray<FVector> Points;
		for (const TCHAR* Label : { TEXT("Search_1"), TEXT("Search_2"), TEXT("Search_3"), TEXT("Search_4") })
		{
			Points.Add(S.Loc(Label));
		}
		for (const FVector& L : SearchClusterPoints)
		{
			Points.Add(L);
		}
		return Points;
	}

	/**
	 * One full lose-the-player cycle on the ring: stand in view -> Chase -> run round the far corner until sight is lost -> vanish
	 * (the player is teleported out of the Warden's senses) -> memory runs out -> Search visits points -> Return -> back on post.
	 */
	void AddLoseCycle(FWRunner& R, FAutomationTestBase* Test, int32 Cycle, int32 MinSearchVisits)
	{
		const TSharedRef<FWS> S = R.S;
		const FString Tag = FString::Printf(TEXT("Cycle %d: "), Cycle);

		R.Add(*(Tag + TEXT("player in view ahead: chase starts")), [S, Test, Cycle](FWCtx& C)
		{
			if (C.bFirst)
			{
				PlacePlayer(C, RingStand, 90.f);
				S->T0 = C.Now;
				S->Path = { FVector(850.0, 4650.0, 0.0), FVector(300.0, 4650.0, 0.0) };
				S->I0 = 0;
				S->T1 = -1.0;
				S->Visited.Reset();
				Test->TestTrue(TEXT("Warden is on post before the cycle"), C.State() == ELBWardenState::Patrol);
			}
			if (S->Sink->FirstEntry(ELBWardenState::Chase, S->T0) >= 0.0)
			{
				S->T2 = S->Sink->FirstEntry(ELBWardenState::Chase, S->T0);
				Note(FString::Printf(TEXT("cycle %d: chase began %.2fs after the player appeared"), Cycle, S->T2 - S->T0));
				return true;
			}
			if (C.Elapsed > 8.0)
			{
				Test->AddError(TEXT("The Warden never began a chase"));
				return true;
			}
			return false;
		});

		R.Add(*(Tag + TEXT("sprint round the corner until the Warden loses sight")), [S, Test, Cycle](FWCtx& C)
		{
			FollowPath(C, S->Path, S->I0, true, 100.f);
			if (S->T1 < 0.0)
			{
				for (const double Lost : S->Sink->LostTimes)
				{
					if (Lost >= S->T2 && C.Pawn->GetActorLocation().Y > 4300.0)
					{
						S->T1 = Lost;
						Note(FString::Printf(TEXT("cycle %d: sight lost %.2fs into the chase at player %s (Warden %s)"), Cycle, Lost - S->T2,
							*C.Pawn->GetActorLocation().ToCompactString(), *C.WardenLoc().ToCompactString()));
						break;
					}
				}
			}
			if (S->T1 >= 0.0 && C.Now - S->T1 >= 0.4)
			{
				return true;
			}
			if (C.Elapsed > 20.0)
			{
				Test->AddError(TEXT("Sight was never lost round the corner"));
				return true;
			}
			return false;
		});

		R.Add(*(Tag + TEXT("player vanishes; memory expires and the Warden searches")), [S, Test, Cycle](FWCtx& C)
		{
			if (C.bFirst)
			{
				PlacePlayer(C, S->Loc(TEXT("Spawn_Player")), 0.f);
			}
			if (C.State() == ELBWardenState::Search)
			{
				const double Lag = C.Now - S->T1;
				Note(FString::Printf(TEXT("cycle %d: Search began %.2fs after sight was lost (memory %.1fs)"), Cycle, Lag, C.Warden()->GetTuning().LastKnownMemorySeconds));
				const float Memory = C.Warden()->GetTuning().LastKnownMemorySeconds;
				Test->TestTrue(FString::Printf(TEXT("Search starts after the memory time (%.2f vs %.1f)"), Lag, Memory), Lag >= Memory - 0.3 && Lag <= Memory + 2.5);
				Test->TestTrue(TEXT("The Warden knows where it last saw the player"), C.Brain()->HasLastKnownLocation());
				return true;
			}
			if (C.Elapsed > 20.0)
			{
				Test->AddError(TEXT("The Warden never moved from Chase to Search after losing the player"));
				return true;
			}
			return false;
		});

		R.Add(*(Tag + TEXT("search visits points")), [S, Test, Cycle, MinSearchVisits](FWCtx& C)
		{
			const TArray<FVector> Points = RingSearchPoints(*S);
			if (C.State() == ELBWardenState::Search)
			{
				for (int32 i = 0; i < Points.Num(); ++i)
				{
					if (Dist2D(C.WardenLoc(), Points[i]) < 130.f)
					{
						S->Visited.Add(i);
					}
				}
				return false;
			}
			const float SearchSeconds = static_cast<float>(C.Now - S->Sink->LastEntry(ELBWardenState::Search));
			Note(FString::Printf(TEXT("cycle %d: Search over after %.1fs having visited %d point(s); now %s"), Cycle, SearchSeconds, S->Visited.Num(), LBWardenLogic::StateName(C.State())));
			Test->TestTrue(FString::Printf(TEXT("Search visited at least %d point(s) (visited %d)"), MinSearchVisits, S->Visited.Num()), S->Visited.Num() >= MinSearchVisits);
			Test->TestTrue(TEXT("Search ended with Return"), C.State() == ELBWardenState::Return);
			return true;
		}, 60.f);

		R.Add(*(Tag + TEXT("returns to its post")), [S, Test, Cycle](FWCtx& C)
		{
			if (C.State() == ELBWardenState::Patrol)
			{
				const double Total = C.Now - S->T1;
				const float Home = Dist2D(C.WardenLoc(), S->Loc(TEXT("Loop_NW")));
				Note(FString::Printf(TEXT("cycle %d: back on post %.1fs after sight was lost, %.0f cm from the post"), Cycle, Total, Home));
				Test->TestTrue(FString::Printf(TEXT("Back on post within 75 s of losing the player (%.1f)"), Total), Total <= 75.0);
				Test->TestTrue(FString::Printf(TEXT("Back at the post (%.0f cm)"), Home), Home < 150.f);
				Test->TestEqual(TEXT("No stuck recovery needed"), S->Log->StuckRepaths, 0);
				return true;
			}
			if (C.Elapsed > 70.0)
			{
				Test->AddError(FString::Printf(TEXT("The Warden never returned to Patrol (stuck in %s at %s)"), LBWardenLogic::StateName(C.State()), *C.WardenLoc().ToCompactString()));
				return true;
			}
			return false;
		}, 90.f);
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenLoseTargetTest, "LastBell.Functional.Warden.Chase.LoseTargetSearchReturn",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenLoseTargetTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FWRunner> R = StartSession(this);
	FAutomationTestBase* Test = this;
	FSetup Setup = RingSetup();
	Setup.bSearchCluster = true;
	AddSetupSteps(*R, Setup, Test);
	R->Add(TEXT("Stage 5"), [](FWCtx& C) { SetStage(C.W, 5); return true; });
	AddWaitForWarden(*R, Test);
	AddLoseCycle(*R, Test, 1, 2);
	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenRepeatedChaseTest, "LastBell.Functional.Warden.Chase.RepeatedChasesAreStable",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenRepeatedChaseTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FWRunner> R = StartSession(this);
	FAutomationTestBase* Test = this;
	FSetup Setup = RingSetup();
	Setup.bSearchCluster = true;
	AddSetupSteps(*R, Setup, Test);
	R->Add(TEXT("Stage 5"), [](FWCtx& C) { SetStage(C.W, 5); return true; });
	AddWaitForWarden(*R, Test);
	for (int32 Cycle = 1; Cycle <= 3; ++Cycle)
	{
		AddLoseCycle(*R, Test, Cycle, 1);
	}
	const TSharedRef<FWS> S = R->S;
	R->Add(TEXT("Three chases done: clean"), [S, Test](FWCtx& C)
	{
		Test->TestEqual(TEXT("Three chases entered"), S->Sink->CountEntries(ELBWardenState::Chase), 3);
		Test->TestEqual(TEXT("Returned to Patrol after each of the three chases"), S->Sink->CountEntries(ELBWardenState::Patrol), 3);
		Test->TestEqual(TEXT("No stuck re-paths"), S->Log->StuckRepaths, 0);
		Test->TestEqual(TEXT("No stuck give-ups"), S->Log->StuckGiveUps, 0);
		Test->TestFalse(TEXT("The player was never caught"), C.Pawn->IsDead());
		return true;
	});
	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenChaseSpeedTest, "LastBell.Functional.Warden.Chase.SpeedBetweenWalkAndSprint",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenChaseSpeedTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FWRunner> R = StartSession(this);
	const TSharedRef<FWS> S = R->S;
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, RingSetup(), Test);
	R->Add(TEXT("Stage 5"), [](FWCtx& C) { SetStage(C.W, 5); return true; });
	AddWaitForWarden(*R, Test);

	R->Add(TEXT("Chase starts"), [S, Test](FWCtx& C)
	{
		if (C.bFirst)
		{
			PlacePlayer(C, RingStand, 90.f);
			S->T0 = C.Now;
		}
		if (C.State() == ELBWardenState::Chase)
		{
			S->T1 = C.Now;
			S->Path = { FVector(850.0, 4650.0, 0.0), FVector(-850.0, 4650.0, 0.0) };
			S->I0 = 0;
			S->Samples.Reset();
			S->Samples2.Reset();
			return true;
		}
		if (C.Elapsed > 8.0)
		{
			Test->AddError(TEXT("No chase"));
			return true;
		}
		return false;
	});

	R->Add(TEXT("Player sprints away along the straight corridor; sample both speeds"), [S, Test](FWCtx& C)
	{
		FollowPath(C, S->Path, S->I0, true, 100.f);
		const double SinceChase = C.Now - S->T1;
		if (SinceChase >= 1.0 && SinceChase <= 3.5 && C.State() == ELBWardenState::Chase)
		{
			S->Samples.Add(Speed2D(C.Warden()));
			S->Samples2.Add(Speed2D(C.Pawn));
		}
		if (SinceChase < 3.6)
		{
			return false;
		}
		const ULBPlayerTuningData& Player = C.Pawn->GetTuning();
		const ULBWardenTuningData& Tuning = C.Warden()->GetTuning();
		double SumW = 0.0, SumP = 0.0;
		float MaxW = 0.f;
		for (const float V : S->Samples) { SumW += V; MaxW = FMath::Max(MaxW, V); }
		for (const float V : S->Samples2) { SumP += V; }
		const int32 N = S->Samples.Num();
		const float MeanW = N > 0 ? static_cast<float>(SumW / N) : 0.f;
		const float MeanP = S->Samples2.Num() > 0 ? static_cast<float>(SumP / S->Samples2.Num()) : 0.f;
		Note(FString::Printf(TEXT("chase speed: Warden mean %.1f max %.1f cm/s over %d samples; player sprint mean %.1f; tuning chase %.0f walk %.0f sprint %.0f"),
			MeanW, MaxW, N, MeanP, Tuning.ChaseSpeed, Player.WalkSpeed, Player.SprintSpeed));
		Test->TestTrue(TEXT("Enough samples"), N > 60);
		Test->TestTrue(FString::Printf(TEXT("Chase speed %.1f is above the player's walk speed %.0f"), MeanW, Player.WalkSpeed), MeanW > Player.WalkSpeed);
		Test->TestTrue(FString::Printf(TEXT("Chase speed %.1f (max %.1f) is below the player's sprint speed %.0f"), MeanW, MaxW, Player.SprintSpeed), MaxW < Player.SprintSpeed);
		Test->TestTrue(FString::Printf(TEXT("Chase speed %.1f is below the measured sprint %.1f"), MeanW, MeanP), MeanW < MeanP);
		Test->TestTrue(FString::Printf(TEXT("Chase speed %.1f is the tuned chase speed %.0f"), MeanW, Tuning.ChaseSpeed), FMath::Abs(MeanW - Tuning.ChaseSpeed) < Tuning.ChaseSpeed * 0.08f);
		return true;
	});

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// Unreachable player, stuck recovery
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenUnreachableTest, "LastBell.Functional.Warden.Chase.UnreachablePlayerSearchesAndNeverStares",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenUnreachableTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FWRunner> R = StartSession(this);
	const TSharedRef<FWS> S = R->S;
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, FSetup(), Test);
	R->Add(TEXT("Stage 5"), [](FWCtx& C) { SetStage(C.W, 5); return true; });
	AddWaitForWarden(*R, Test);

	R->Add(TEXT("Player on Ledge_Top (off the navmesh): observe 45 s"), [S, Test](FWCtx& C)
	{
		const FVector Ledge = S->Loc(TEXT("Ledge_Top"));
		if (C.bFirst)
		{
			PlacePlayer(C, Ledge, 26.f);
			Note(FString::Printf(TEXT("player on the ledge at %s"), *C.Pawn->GetActorLocation().ToCompactString()));
			S->T0 = C.Now;
			S->T1 = -1.0;           // last frame time
			S->Acc0 = 0.0;          // current still run
			S->Acc1 = 0.0;          // longest still run
			S->F0 = 1.0e9f;         // closest flat distance to the ledge
			S->T2 = -1.0;           // first chase
		}
		const double Dt = S->T1 < 0.0 ? 0.0 : C.Now - S->T1;
		S->T1 = C.Now;
		S->F0 = FMath::Min(S->F0, Dist2D(C.WardenLoc(), Ledge));
		if (S->T2 < 0.0 && S->Sink->FirstEntry(ELBWardenState::Chase) >= 0.0)
		{
			S->T2 = S->Sink->FirstEntry(ELBWardenState::Chase);
		}
		if (S->T2 >= 0.0 && C.Now >= S->T2)
		{
			// Standing still (not mid-windup) while there is a target and nothing to do is "staring".
			const bool bStill = Speed2D(C.Warden()) < 8.f && C.State() != ELBWardenState::Attack;
			S->Acc0 = bStill ? S->Acc0 + Dt : 0.0;
			S->Acc1 = FMath::Max(S->Acc1, S->Acc0);
		}
		if (C.Elapsed < 45.0)
		{
			return false;
		}

		FString Timeline;
		for (const ULBWardenTestSink::FTransitionRecord& Rec : S->Sink->Transitions)
		{
			Timeline += FString::Printf(TEXT("%s@%.1f "), LBWardenLogic::StateName(Rec.New), Rec.Time - S->T0);
		}
		Note(FString::Printf(TEXT("ledge timeline: %s"), *Timeline));
		Note(FString::Printf(TEXT("closest approach to the ledge %.0f cm; longest still run %.1fs"), S->F0, S->Acc1));
		Test->TestTrue(TEXT("Spotted the player on the ledge"), S->Sink->SpottedTimes.Num() >= 1);
		Test->TestTrue(TEXT("It chased (or tried to)"), S->Sink->CountEntries(ELBWardenState::Chase) >= 1);
		Test->TestTrue(TEXT("It went near the ledge"), S->F0 < 600.f);
		Test->TestTrue(TEXT("It gave up reaching the player and searched"), S->Sink->CountEntries(ELBWardenState::Search) >= 1);
		Test->TestEqual(TEXT("It never attacked an unreachable player"), S->Sink->CountEntries(ELBWardenState::Attack), 0);
		Test->TestFalse(TEXT("The player is alive"), C.Pawn->IsDead());
		Test->TestTrue(FString::Printf(TEXT("Never stood still for long once hunting (%.1fs)"), S->Acc1), S->Acc1 <= 6.0);
		return true;
	}, 120.f);

	Enqueue(R);
	return true;
}

namespace
{
	/**
	 * Patrol Loop_NE -> Loop_NW along the east corridor with a solid box across it. bAffectsNavigation = true is a box the dynamic
	 * navmesh knows about (it carves the corridor: the route must go round the ring); false is a blocker the navmesh does not see
	 * (a door slammed by script): the Warden walks into it and the stuck detector must re-path, then give the point up.
	 */
	void BuildStuckScenario(FAutomationTestBase* Test, bool bAffectsNavigation)
	{
	TSharedPtr<FWRunner> R = StartSession(Test);
	const TSharedRef<FWS> S = R->S;
	FSetup Setup = RingSetup();
	Setup.bPatrolRoute = true;
	Setup.bSearchPoints = false;
	AddSetupSteps(*R, Setup, Test);

	R->Add(TEXT("Block the east corridor with a box, stage 4 (patrol)"), [S, Test, bAffectsNavigation](FWCtx& C)
	{
		AStaticMeshActor* Box = SpawnBox(C.W, FVector(850.0, 3300.0, 150.0), FVector(420.0, 60.0, 300.0), TEXT("Test_Blocker"));
		if (Test->TestNotNull(TEXT("Blocker spawned"), Box))
		{
			Box->GetStaticMeshComponent()->SetCanEverAffectNavigation(bAffectsNavigation);
		}
		SetStage(C.W, 4);
		return true;
	});
	AddWaitForWarden(*R, Test);

	// Route: Loop_NE (beyond the blocker), then Loop_NW (back at the post).
	R->Add(TEXT("Patrols into the blocker and recovers"), [S, Test, bAffectsNavigation](FWCtx& C)
	{
		const FVector BlockerFlat(850.0, 3300.0, 0.0);
		if (C.bFirst)
		{
			S->T0 = C.Now;
			S->T1 = -1.0;      // last frame
			S->T2 = -1.0;      // first time near the blocker
			S->Acc0 = 0.0;
			S->Acc1 = 0.0;
			S->B0 = false;     // reached the far side
			S->B1 = false;     // gave up and came back to the post
		}
		const double Dt = S->T1 < 0.0 ? 0.0 : C.Now - S->T1;
		S->T1 = C.Now;
		const FVector Warden = C.WardenLoc();
		if (S->T2 < 0.0 && Dist2D(Warden, BlockerFlat) < 140.f)
		{
			S->T2 = C.Now;
			Note(FString::Printf(TEXT("reached the blocker at +%.1fs"), C.Now - S->T0));
		}
		const bool bMovingState = C.State() == ELBWardenState::Patrol;
		const bool bStill = Speed2D(C.Warden()) < 8.f && bMovingState;
		S->Acc0 = bStill ? S->Acc0 + Dt : 0.0;
		S->Acc1 = FMath::Max(S->Acc1, S->Acc0);
		if (Warden.Y > 3600.0)
		{
			S->B0 = true; // got past: the navmesh routed round or the box carved the way
		}
		if (S->T2 >= 0.0 && Dist2D(Warden, S->Loc(TEXT("Loop_NW"))) < 150.f && C.Now - S->T2 > 3.0)
		{
			S->B1 = true;
		}
		if (S->B0 || S->B1)
		{
			Note(FString::Printf(TEXT("blocked-corridor outcome: %s at +%.1fs; re-paths %d, give-ups %d, longest still run %.1fs"),
				S->B1 ? TEXT("gave the point up and went on") : TEXT("passed the blocker (navmesh routed round)"), C.Now - S->T0, S->Log->StuckRepaths, S->Log->StuckGiveUps, S->Acc1));
			Test->TestTrue(FString::Printf(TEXT("Never stood still longer than the stuck window plus slack (%.1fs)"), S->Acc1),
				S->Acc1 <= 2.0 * C.Warden()->GetTuning().StuckSeconds + 2.0);
			if (!bAffectsNavigation)
			{
				Test->TestTrue(TEXT("A blocker the navmesh cannot see: stuck recovery gave the point up and the Warden went on"), S->B1);
			}
			if (S->B1)
			{
				Test->TestTrue(TEXT("Stuck recovery logged a re-path"), S->Log->StuckRepaths >= 1);
				Test->TestTrue(TEXT("Stuck recovery gave the point up"), S->Log->StuckGiveUps >= 1);
			}
			return true;
		}
		if (C.Elapsed > 75.0)
		{
			Test->AddError(FString::Printf(TEXT("The Warden never recovered from the blocked corridor (at %s, state %s, longest still run %.1fs)"),
				*Warden.ToCompactString(), LBWardenLogic::StateName(C.State()), S->Acc1));
			return true;
		}
		return false;
	}, 120.f);

	Enqueue(R);
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenStuckInvisibleBlockerTest, "LastBell.Functional.Warden.Stuck.InvisibleBlockerRecovers",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenStuckInvisibleBlockerTest::RunTest(const FString& Parameters)
{
	BuildStuckScenario(this, false);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenStuckNavBlockerTest, "LastBell.Functional.Warden.Stuck.NavmeshReroutesAroundBlockedCorridor",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenStuckNavBlockerTest::RunTest(const FString& Parameters)
{
	BuildStuckScenario(this, true);
	return true;
}

// =====================================================================================================================
// Attack, escape, checkpoint, flip-flop
// =====================================================================================================================

namespace
{
	// 300 cm from the post, in the open, with a clear run-away line towards -X.
	const FVector AttackStand(500.0, -100.0, 0.0);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenCatchTest, "LastBell.Functional.Warden.Attack.CatchKillsAfterWindupAndReloads",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenCatchTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FWRunner> R = StartSession(this);
	const TSharedRef<FWS> S = R->S;
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, FSetup(), Test);
	R->Add(TEXT("Stage 5"), [](FWCtx& C) { SetStage(C.W, 5); return true; });
	AddWaitForWarden(*R, Test);

	R->Add(TEXT("Player stands still 300 cm from the Warden: attack windup"), [S, Test](FWCtx& C)
	{
		if (C.bFirst)
		{
			PlacePlayer(C, AttackStand, 180.f);
		}
		if (S->Sink->WindupTimes.Num() > 0)
		{
			S->T0 = S->Sink->WindupTimes[0];
			Note(FString::Printf(TEXT("windup began %.2fs after placing the player, announced %.2fs"), S->T0 - (C.Now - C.Elapsed), S->Sink->WindupSeconds[0]));
			Test->TestEqual(TEXT("State is Attack during the windup"), static_cast<int32>(C.State()), static_cast<int32>(ELBWardenState::Attack));
			Test->TestFalse(TEXT("Not dead yet at the start of the windup"), C.Pawn->IsDead());
			return true;
		}
		if (C.Elapsed > 10.0)
		{
			Test->AddError(TEXT("The Warden never started an attack"));
			return true;
		}
		return false;
	});

	R->Add(TEXT("The windup ends: the player dies"), [S, Test](FWCtx& C)
	{
		if (C.Pawn->IsDead())
		{
			const double Delay = C.Now - S->T0;
			const float Windup = S->Sink->WindupSeconds.Num() ? S->Sink->WindupSeconds[0] : 0.6f;
			Note(FString::Printf(TEXT("player died %.2fs after the windup began (windup %.2fs)"), Delay, Windup));
			Test->TestTrue(FString::Printf(TEXT("Died after the windup, not before (%.2f vs %.2f)"), Delay, Windup), Delay >= Windup - 0.05 && Delay <= Windup + 0.35);
			Test->TestEqual(TEXT("Exactly one windup"), S->Sink->WindupTimes.Num(), 1);
			S->OldWorld = C.W;
			return true;
		}
		if (C.Elapsed > 3.0)
		{
			Test->AddError(TEXT("The attack never killed the player"));
			return true;
		}
		return false;
	});

	R->Add(TEXT("Death reload: the level restarts with a living player and a dormant Warden"), [S, Test](FWCtx& C)
	{
		if (!C.W || C.W == S->OldWorld.Get() || !LBPie::WorldReady())
		{
			return false;
		}
		if (C.Frames < 20)
		{
			return false;
		}
		Test->TestFalse(TEXT("New pawn is alive"), C.Pawn->IsDead());
		ALBWarden* NewWarden = nullptr;
		for (TActorIterator<ALBWarden> It(C.W); It; ++It)
		{
			NewWarden = *It;
		}
		if (Test->TestNotNull(TEXT("A Warden exists in the reloaded level"), NewWarden) && NewWarden->GetBrain())
		{
			Test->TestEqual(TEXT("Warden is Dormant after the reload (stage tags reset)"), static_cast<int32>(NewWarden->GetBrain()->GetState()), static_cast<int32>(ELBWardenState::Dormant));
			Test->TestTrue(TEXT("...and hidden"), NewWarden->IsHidden());
		}
		Note(TEXT("death reload confirmed"));
		return true;
	}, 60.f, true);

	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenEscapeTest, "LastBell.Functional.Warden.Attack.SprintingAwayInsideTheWindupEscapes",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenEscapeTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FWRunner> R = StartSession(this);
	const TSharedRef<FWS> S = R->S;
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, FSetup(), Test);
	R->Add(TEXT("Stage 5"), [](FWCtx& C) { SetStage(C.W, 5); return true; });
	AddWaitForWarden(*R, Test);

	R->Add(TEXT("Wait for the windup, then sprint away inside it"), [S, Test](FWCtx& C)
	{
		if (C.bFirst)
		{
			PlacePlayer(C, AttackStand, 180.f);
			S->T0 = -1.0;
		}
		if (S->T0 < 0.0 && C.State() == ELBWardenState::Attack)
		{
			S->T0 = C.Now;
			Note(FString::Printf(TEXT("windup started, player %.0f cm from the Warden: sprinting away"), Dist2D(C.WardenLoc(), C.Pawn->GetActorLocation())));
		}
		if (S->T0 >= 0.0)
		{
			// Away from the Warden, keep going.
			const FVector Away = (C.Pawn->GetActorLocation() - C.WardenLoc()).GetSafeNormal2D();
			DriveToward(C, C.Pawn->GetActorLocation() + Away * 600.0, true);
			if (C.State() != ELBWardenState::Attack)
			{
				Note(FString::Printf(TEXT("attack ended %.2fs after it began in %s, player %.0f cm away"), C.Now - S->T0, LBWardenLogic::StateName(C.State()),
					Dist2D(C.WardenLoc(), C.Pawn->GetActorLocation())));
				Test->TestEqual(TEXT("Escaped: back to Chase"), static_cast<int32>(C.State()), static_cast<int32>(ELBWardenState::Chase));
				Test->TestFalse(TEXT("Escaped: the player is alive"), C.Pawn->IsDead());
				Test->TestEqual(TEXT("No landed attack (never Return from Attack)"), S->Sink->CountEntries(ELBWardenState::Return), 0);
				S->T1 = C.Now;
				return true;
			}
		}
		if (C.Elapsed > 10.0)
		{
			Test->AddError(TEXT("The Warden never began an attack"));
			return true;
		}
		return false;
	});

	R->Add(TEXT("Keeps running; still alive a second later"), [S, Test](FWCtx& C)
	{
		const FVector Away = (C.Pawn->GetActorLocation() - C.WardenLoc()).GetSafeNormal2D();
		DriveToward(C, C.Pawn->GetActorLocation() + Away * 600.0, true);
		if (C.Now - S->T1 < 1.0)
		{
			return false;
		}
		Test->TestFalse(TEXT("Alive after the escape"), C.Pawn->IsDead());
		Test->TestEqual(TEXT("Still chasing"), static_cast<int32>(C.State()), static_cast<int32>(ELBWardenState::Chase));
		Test->TestEqual(TEXT("Exactly one windup"), S->Sink->WindupTimes.Num(), 1);
		return true;
	});

	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenCheckpointTest, "LastBell.Functional.Warden.Checkpoint.RefusedWhileChasingSavesAfter",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenCheckpointTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FWRunner> R = StartSession(this);
	const TSharedRef<FWS> S = R->S;
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, RingSetup(), Test);
	R->Add(TEXT("Stage 5"), [](FWCtx& C) { SetStage(C.W, 5); return true; });
	AddWaitForWarden(*R, Test);

	R->Add(TEXT("Player in view 1750 cm away: chase starts"), [S, Test](FWCtx& C)
	{
		if (C.bFirst)
		{
			PlacePlayer(C, FVector(850.0, 3700.0, 0.0), -90.f);
		}
		if (C.State() == ELBWardenState::Chase)
		{
			return true;
		}
		if (C.Elapsed > 8.0)
		{
			Test->AddError(TEXT("No chase"));
			return true;
		}
		return false;
	});

	R->Add(TEXT("A checkpoint where the player stands, during the chase: refused"), [S, Test](FWCtx& C)
	{
		ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(C.W);
		if (!Test->TestNotNull(TEXT("Save subsystem"), Save))
		{
			return true;
		}
		if (C.bFirst)
		{
			const FTransform At(FRotator::ZeroRotator, C.Pawn->GetActorLocation());
			ALBCheckpoint* Checkpoint = C.W->SpawnActorDeferred<ALBCheckpoint>(ALBCheckpoint::StaticClass(), At);
			if (Checkpoint)
			{
				Checkpoint->CheckpointId = TEXT("CP_WardenTest");
				Checkpoint->FinishSpawning(At);
				S->Aux = Checkpoint;
			}
			Test->TestTrue(TEXT("The Warden is chasing when the checkpoint is entered"), C.Brain()->IsChasingOrAttacking());
			Test->TestTrue(TEXT("Checkpoint says no (CanSaveNow)"), S->Aux.IsValid() && !static_cast<ALBCheckpoint*>(S->Aux.Get())->CanSaveNow());
		}
		Test->TestFalse(TEXT("Not saved while chased"), Save->HasReachedCheckpoint(TEXT("CP_WardenTest")));
		if (C.Elapsed < 1.5)
		{
			return false;
		}
		Test->TestTrue(TEXT("Still chasing 1.5 s later"), C.Brain()->IsChasingOrAttacking());
		return true;
	});

	R->Add(TEXT("Line of sight is cut; the chase ends; the retry now saves"), [S, Test](FWCtx& C)
	{
		ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(C.W);
		if (C.bFirst)
		{
			// The Warden is well short of Y=3150 by now; this opaque wall hides the player from it.
			SpawnBox(C.W, FVector(850.0, 3150.0, 150.0), FVector(420.0, 60.0, 300.0), TEXT("Test_SightWall"));
			S->T0 = -1.0;
		}
		if (C.Brain()->IsChasingOrAttacking())
		{
			Test->TestFalse(TEXT("Never saved during the chase"), Save->HasReachedCheckpoint(TEXT("CP_WardenTest")));
			Test->TestFalse(TEXT("The player has not been caught"), C.Pawn->IsDead());
			return false;
		}
		if (S->T0 < 0.0)
		{
			S->T0 = C.Now;
			Note(FString::Printf(TEXT("chase ended after %.1fs, state %s"), C.Elapsed, LBWardenLogic::StateName(C.State())));
		}
		if (Save->HasReachedCheckpoint(TEXT("CP_WardenTest")))
		{
			Note(FString::Printf(TEXT("checkpoint saved %.2fs after the chase ended"), C.Now - S->T0));
			Test->TestTrue(TEXT("Saved within the 0.5 s retry interval plus a frame"), C.Now - S->T0 <= 1.2);
			return true;
		}
		if (C.Now - S->T0 > 2.0)
		{
			Test->AddError(TEXT("The checkpoint did not save after the chase ended"));
			return true;
		}
		return false;
	}, 60.f);

	Enqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenFlipFlopTest, "LastBell.Functional.Warden.Transitions.NoInvestigateSuspiciousFlipFlop",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenFlipFlopTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FWRunner> R = StartSession(this);
	const TSharedRef<FWS> S = R->S;
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, FSetup(), Test);
	R->Add(TEXT("Stage 3 (no chase); a long attack cooldown keeps the visible player un-attackable"), [S](FWCtx& C)
	{
		ULBWardenTuningData& Tuning = const_cast<ULBWardenTuningData&>(C.Warden()->GetTuning());
		const float Old = Tuning.AttackCooldownSeconds;
		const TWeakObjectPtr<ULBWardenTuningData> WeakTuning = &Tuning;
		S->Cleanups.Add([WeakTuning, Old]() { if (WeakTuning.IsValid()) { WeakTuning->AttackCooldownSeconds = Old; } });
		Tuning.AttackCooldownSeconds = 8.f;
		SetStage(C.W, 3);
		return true;
	});
	AddWaitForWarden(*R, Test);

	R->Add(TEXT("Stand in front, let the attack start, step away in the windup, stand still"), [S, Test](FWCtx& C)
	{
		if (C.bFirst)
		{
			PlacePlayer(C, FVector(700.0, 0.0, 0.0), 180.f);
			S->B0 = false;
		}
		if (!S->B0 && C.State() == ELBWardenState::Attack)
		{
			S->B0 = true;
		}
		if (S->B0)
		{
			if (DriveToward(C, FVector(400.0, 0.0, 0.0), true) <= 60.f || Dist2D(C.WardenLoc(), C.Pawn->GetActorLocation()) > 330.f)
			{
				StandStill(C);
			}
		}
		if (S->Sink->FirstEntry(ELBWardenState::Suspicious) >= 0.0)
		{
			S->T0 = S->Sink->FirstEntry(ELBWardenState::Suspicious);
			return true;
		}
		if (C.Elapsed > 15.0)
		{
			Test->AddError(TEXT("The Warden never reached Suspicious (attack cancelled -> investigate -> arrive)"));
			S->T0 = C.Now;
			return true;
		}
		return false;
	});

	R->Add(TEXT("3.5 s with the player visible and attack on cooldown: no Investigate <-> Suspicious oscillation"), [S, Test](FWCtx& C)
	{
		StandStill(C);
		if (C.Now - S->T0 < 3.5)
		{
			return false;
		}
		int32 Changes = 0;
		int32 InvestigateEntries = 0;
		for (const ULBWardenTestSink::FTransitionRecord& Rec : S->Sink->Transitions)
		{
			if (Rec.Time >= S->T0 + 0.001)
			{
				++Changes;
				InvestigateEntries += Rec.New == ELBWardenState::Investigate ? 1 : 0;
			}
		}
		Note(FString::Printf(TEXT("%d state change(s), %d Investigate entr(ies) in the 3.5 s after the first Suspicious; now %s"), Changes, InvestigateEntries, LBWardenLogic::StateName(C.State())));
		Test->TestTrue(FString::Printf(TEXT("At most a few state changes in 3.5 s (%d)"), Changes), Changes <= 3);
		Test->TestTrue(FString::Printf(TEXT("Investigate was not re-entered over and over (%d)"), InvestigateEntries), InvestigateEntries <= 1);
		Test->TestEqual(TEXT("The cooldown held: no second attack"), S->Sink->CountEntries(ELBWardenState::Attack, S->T0), 0);
		Test->TestFalse(TEXT("The player is alive"), C.Pawn->IsDead());
		return true;
	});

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// Close range sight
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenSightCloseRangeTest, "LastBell.Functional.Warden.Sight.NoBlindSpotRightInFrontOfIt",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenSightCloseRangeTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FWRunner> R = StartSession(this);
	const TSharedRef<FWS> S = R->S;
	FAutomationTestBase* Test = this;
	AddSetupSteps(*R, FSetup(), Test);
	R->Add(TEXT("Stage 5"), [](FWCtx& C) { SetStage(C.W, 5); return true; });
	AddWaitForWarden(*R, Test);

	// The sight cone is 3D: with the origin at the eyes, a body 70 cm ahead and 107 cm below them is 57 degrees down: unseen.
	R->Add(TEXT("Player 70 cm in front of the Warden, crouched and silent: seen and attacked"), [S, Test](FWCtx& C)
	{
		if (C.bFirst)
		{
			PlacePlayer(C, FVector(730.0, 0.0, 0.0), 0.f);
			S->T0 = C.Now;
		}
		C.Input.bCrouch = true; // lowest body: the hardest case for the vertical angle; no move input = no footsteps
		if (S->Sink->WindupTimes.Num() > 0 || C.State() == ELBWardenState::Attack)
		{
			Test->TestTrue(TEXT("Spotted at close range"), S->Sink->SpottedTimes.Num() >= 1);
			Note(FString::Printf(TEXT("spotted %.2fs after placement at 70 cm, attack windup began"), S->Sink->SpottedTimes.Num() ? S->Sink->SpottedTimes[0] - S->T0 : -1.0));
			return true;
		}
		if (C.Elapsed > 4.0)
		{
			Test->AddError(FString::Printf(TEXT("The Warden never noticed a player 70 cm in front of it (spotted %d, state %s)"), S->Sink->SpottedTimes.Num(), LBWardenLogic::StateName(C.State())));
			return true;
		}
		return false;
	});

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// Monastery patrol reachability
// =====================================================================================================================

namespace
{
	struct FRoutePoint
	{
		int32 Order = 0;
		FVector Loc = FVector::ZeroVector;
		FString Label;
	};

	struct FMonasteryRoute
	{
		FName Id;
		TArray<FRoutePoint> Points;
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenMonasteryReachabilityTest, "LastBell.Functional.Warden.MonasteryReachability",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenMonasteryReachabilityTest::RunTest(const FString& Parameters)
{
	if (!FPackageName::DoesPackageExist(GMonasteryMapPath))
	{
		AddWarning(TEXT("L_Monastery does not exist: Warden reachability skipped"));
		return true;
	}
	TSharedPtr<FWRunner> R = StartSession(this, GMonasteryMapPath);
	const TSharedRef<FWS> S = R->S;
	FAutomationTestBase* Test = this;
	const TSharedRef<TArray<FMonasteryRoute>> Routes = MakeShared<TArray<FMonasteryRoute>>();
	const TSharedRef<TArray<TPair<FString, FVector>>> Spawns = MakeShared<TArray<TPair<FString, FVector>>>();
	const TSharedRef<TMap<FString, FName>> SpawnRoute = MakeShared<TMap<FString, FName>>();

	R->Add(TEXT("PIE ready, markers read, navmesh generated"), [S, Test, Routes, Spawns, SpawnRoute](FWCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 10)
		{
			return false;
		}
		UNavigationSystemV1* NavSys = FNavigationSystem::GetCurrent<UNavigationSystemV1>(C.W);
		if (S->I0 == 0)
		{
			S->I0 = 1;
			for (TActorIterator<ALBWarden> It(C.W); It; ++It)
			{
				S->Warden = *It;
			}
			if (S->Warden.IsValid())
			{
				S->Brain = S->Warden->GetBrain();
			}
			for (TActorIterator<ALBPatrolPoint> It(C.W); It; ++It)
			{
				FMonasteryRoute* Route = nullptr;
				for (FMonasteryRoute& Existing : *Routes)
				{
					if (Existing.Id == It->RouteId)
					{
						Route = &Existing;
					}
				}
				if (!Route)
				{
					Route = &Routes->AddDefaulted_GetRef();
					Route->Id = It->RouteId;
				}
				FRoutePoint Point;
				Point.Order = It->Order;
				Point.Loc = It->GetActorLocation();
				Point.Label = It->GetActorLabel();
				Route->Points.Add(Point);
			}
			for (FMonasteryRoute& Route : *Routes)
			{
				Route.Points.StableSort([](const FRoutePoint& A, const FRoutePoint& B) { return A.Order < B.Order; });
			}
			for (TActorIterator<ALBWardenSpawnPoint> It(C.W); It; ++It)
			{
				Spawns->Add(TPair<FString, FVector>(It->GetActorLabel(), It->GetActorLocation()));
				SpawnRoute->Add(It->GetActorLabel(), It->RouteId);
			}
			Note(FString::Printf(TEXT("%d patrol route(s), %d spawn point(s), Warden %s"), Routes->Num(), Spawns->Num(), S->Warden.IsValid() ? TEXT("placed") : TEXT("MISSING")));
			if (NavSys)
			{
				NavSys->Build();
			}
		}
		if (!NavSys)
		{
			Test->AddError(TEXT("No navigation system in the PIE world"));
			return true;
		}
		FNavLocation Projected;
		const bool bSpawnsOnNav = Spawns->Num() == 0 || NavSys->ProjectPointToNavigation((*Spawns)[0].Value, Projected, FVector(50.0, 50.0, 250.0));
		if (!NavSys->IsNavigationBuildInProgress() && bSpawnsOnNav)
		{
			Note(FString::Printf(TEXT("Monastery navmesh ready after %.1fs"), C.Elapsed));
			return true;
		}
		if (C.Elapsed > 120.0)
		{
			Test->AddError(TEXT("The Monastery runtime navmesh did not finish"));
			return true;
		}
		return false;
	}, 240.f);

	R->Add(TEXT("Every patrol segment and spawn-to-route start has a complete path for the Warden agent"), [S, Test, Routes, Spawns, SpawnRoute](FWCtx& C)
	{
		UNavigationSystemV1* NavSys = FNavigationSystem::GetCurrent<UNavigationSystemV1>(C.W);
		ALBWarden* Warden = C.Warden();
		if (!NavSys || !Warden)
		{
			Test->AddWarning(TEXT("No navigation system or no placed Warden: path checks skipped"));
			return true;
		}
		const FVector Extent(50.0, 50.0, 250.0);
		int32 Checked = 0;
		int32 Failed = 0;
		auto CheckSegment = [&](const FString& From, const FVector& A, const FString& To, const FVector& B)
		{
			++Checked;
			UNavigationPath* Path = UNavigationSystemV1::FindPathToLocationSynchronously(C.W, A, B, Warden);
			const bool bOk = Path && Path->IsValid() && !Path->IsPartial();
			if (bOk)
			{
				Note(FString::Printf(TEXT("path OK     %s -> %s : %.0f cm, %d points"), *From, *To, Path->GetPathLength(), Path->PathPoints.Num()));
				return;
			}
			++Failed;
			FNavLocation Dummy;
			const bool bFromOn = NavSys->ProjectPointToNavigation(A, Dummy, Extent);
			const bool bToOn = NavSys->ProjectPointToNavigation(B, Dummy, Extent);
			const FString Why = !Path ? TEXT("no path object") : (!Path->IsValid() ? TEXT("no path") : TEXT("PARTIAL path"));
			const FString Last = (Path && Path->PathPoints.Num() > 0) ? Path->PathPoints.Last().ToCompactString() : FString(TEXT("-"));
			const double Short = (Path && Path->PathPoints.Num() > 0) ? FVector::Dist(Path->PathPoints.Last(), B) : -1.0;
			Test->AddError(FString::Printf(TEXT("path FAILED %s %s -> %s %s: %s (start on navmesh %d, end on navmesh %d, path ends at %s, %.0f cm short of the goal)"),
				*From, *A.ToCompactString(), *To, *B.ToCompactString(), *Why, bFromOn ? 1 : 0, bToOn ? 1 : 0, *Last, Short));
		};

		for (const FMonasteryRoute& Route : *Routes)
		{
			const int32 N = Route.Points.Num();
			for (int32 i = 0; i < N; ++i)
			{
				const FRoutePoint& A = Route.Points[i];
				const FRoutePoint& B = Route.Points[(i + 1) % N];
				CheckSegment(A.Label, A.Loc, i + 1 == N ? B.Label + TEXT(" (wrap-around)") : B.Label, B.Loc);
			}
		}
		for (const TPair<FString, FVector>& Spawn : *Spawns)
		{
			const FName* RouteId = SpawnRoute->Find(Spawn.Key);
			if (!RouteId || RouteId->IsNone())
			{
				continue;
			}
			for (const FMonasteryRoute& Route : *Routes)
			{
				if (Route.Id == *RouteId && Route.Points.Num() > 0)
				{
					CheckSegment(Spawn.Key, Spawn.Value, Route.Points[0].Label, Route.Points[0].Loc);
				}
			}
		}
		Note(FString::Printf(TEXT("reachability: %d segment(s) checked, %d failed"), Checked, Failed));
		Test->TestTrue(TEXT("There were routes to check"), Checked > 0);
		return true;
	}, 120.f);

	R->Add(TEXT("Stage 4: patrol the Crypt route for up to 100 s; a full loop without a stuck event"), [S, Test, Routes](FWCtx& C)
	{
		const FMonasteryRoute* Crypt = nullptr;
		for (const FMonasteryRoute& Route : *Routes)
		{
			if (Route.Id == TEXT("Crypt"))
			{
				Crypt = &Route;
			}
		}
		if (!Crypt || Crypt->Points.Num() == 0 || !C.Warden() || !C.Brain())
		{
			Test->AddWarning(TEXT("No Crypt route or no Warden: patrol run skipped"));
			return true;
		}
		if (C.bFirst)
		{
			S->Sink.Reset(NewObject<ULBWardenTestSink>());
			S->Sink->Bind(C.Brain(), C.W);
			SetStage(C.W, 4);
			S->I0 = 0;       // next route index expected
			S->I1 = 0;       // points reached in order
			S->T0 = C.Now;
			S->T1 = -1.0;
			S->T2 = -1.0;
		}
		if (C.State() == ELBWardenState::Patrol && !C.Warden()->IsHidden() && S->T1 < 0.0)
		{
			S->T1 = C.Now;
			S->Sink->Clear();
			Note(FString::Printf(TEXT("Warden up on the Crypt route after %.1fs at %s"), C.Now - S->T0, *C.WardenLoc().ToCompactString()));
		}
		if (S->T1 >= 0.0)
		{
			const FVector Wl = C.WardenLoc();
			const int32 N = Crypt->Points.Num();
			if (S->I1 == 0)
			{
				for (int32 i = 0; i < N; ++i)
				{
					if (Dist2D(Wl, Crypt->Points[i].Loc) < 160.f && FMath::Abs(Wl.Z - Crypt->Points[i].Loc.Z) < 250.0)
					{
						S->I0 = (i + 1) % N;
						S->I1 = 1;
						S->T2 = C.Now;
						Note(FString::Printf(TEXT("first route point reached: %s at +%.1fs"), *Crypt->Points[i].Label, C.Now - S->T1));
						break;
					}
				}
			}
			else if (Dist2D(Wl, Crypt->Points[S->I0].Loc) < 160.f && FMath::Abs(Wl.Z - Crypt->Points[S->I0].Loc.Z) < 250.0)
			{
				Note(FString::Printf(TEXT("reached %s (%d in order) at +%.1fs"), *Crypt->Points[S->I0].Label, S->I1 + 1, C.Now - S->T1));
				S->I0 = (S->I0 + 1) % N;
				++S->I1;
			}
			if (S->I1 >= N + 1)
			{
				const double LoopSeconds = C.Now - S->T2;
				Note(FString::Printf(TEXT("full Crypt loop (%d points + wrap) in %.1fs; stuck re-paths %d, give-ups %d; state changes %d"), N, LoopSeconds, S->Log->StuckRepaths, S->Log->StuckGiveUps, S->Sink->Transitions.Num()));
				Test->TestEqual(TEXT("No stuck re-path on the Crypt route"), S->Log->StuckRepaths, 0);
				Test->TestEqual(TEXT("No stuck give-up on the Crypt route"), S->Log->StuckGiveUps, 0);
				Test->TestEqual(TEXT("The patrol was never interrupted (no state change)"), S->Sink->Transitions.Num(), 0);
				return true;
			}
		}
		if (S->T1 >= 0.0 && C.Frames % 300 == 0)
		{
			Note(FString::Printf(TEXT("Crypt patrol +%.0fs: Warden %s state %s speed %.0f"), C.Now - S->T1, *C.WardenLoc().ToCompactString(), LBWardenLogic::StateName(C.State()), Speed2D(C.Warden())));
		}
		if (C.Now - S->T0 > 100.0)
		{
			Test->AddError(FString::Printf(TEXT("The Warden did not complete a Crypt patrol loop in 100 s: %d of %d points reached in order, now at %s in state %s; stuck re-paths %d, give-ups %d"),
				S->I1, Crypt->Points.Num() + 1, *C.WardenLoc().ToCompactString(), LBWardenLogic::StateName(C.State()), S->Log->StuckRepaths, S->Log->StuckGiveUps));
			return true;
		}
		return false;
	}, 200.f);

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// Monastery smoke
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWardenMonasterySmokeTest, "LastBell.Functional.Warden.Monastery.StagesRelocateTheWarden",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWardenMonasterySmokeTest::RunTest(const FString& Parameters)
{
	if (!FPackageName::DoesPackageExist(GMonasteryMapPath))
	{
		AddWarning(TEXT("L_Monastery does not exist: Warden Monastery smoke skipped"));
		return true;
	}
	TSharedPtr<FWRunner> R = StartSession(this, GMonasteryMapPath);
	const TSharedRef<FWS> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready; find the Warden and WSpawn_Crypt / WSpawn_Cloister"), [S, Test](FWCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 10)
		{
			return false;
		}
		for (TActorIterator<ALBWarden> It(C.W); It; ++It)
		{
			S->Warden = *It;
		}
		for (TActorIterator<ALBWardenSpawnPoint> It(C.W); It; ++It)
		{
			S->Pts.Add(It->GetActorLabel(), It->GetActorTransform());
		}
		if (!S->Warden.IsValid() || !S->Warden->GetBrain() || !S->Has(TEXT("WSpawn_Crypt")) || !S->Has(TEXT("WSpawn_Cloister")))
		{
			Test->AddWarning(TEXT("L_Monastery has no Warden / WSpawn_Crypt / WSpawn_Cloister yet: smoke skipped"));
			S->B1 = true; // skip
			return true;
		}
		S->Brain = S->Warden->GetBrain();
		S->Sink.Reset(NewObject<ULBWardenTestSink>());
		S->Sink->Bind(S->Brain.Get(), C.W);
		Test->TestEqual(TEXT("Dormant at game start"), static_cast<int32>(S->Brain->GetState()), static_cast<int32>(ELBWardenState::Dormant));
		Test->TestTrue(TEXT("Hidden at game start"), S->Warden->IsHidden());
		return true;
	}, 90.f);

	R->Add(TEXT("Stage 3: relocates to WSpawn_Crypt"), [S, Test](FWCtx& C)
	{
		if (S->B1)
		{
			return true;
		}
		if (C.bFirst)
		{
			SetStage(C.W, 3);
		}
		if (C.State() != ELBWardenState::Dormant)
		{
			const float D = Dist2D(C.WardenLoc(), S->Loc(TEXT("WSpawn_Crypt")));
			Note(FString::Printf(TEXT("stage 3: up after %.1fs at %s, %.0f cm from WSpawn_Crypt"), C.Elapsed, *C.WardenLoc().ToCompactString(), D));
			Test->TestTrue(FString::Printf(TEXT("Warden stands at WSpawn_Crypt (%.0f cm off)"), D), D < 150.f);
			Test->TestFalse(TEXT("...visible"), C.Warden()->IsHidden());
			return true;
		}
		if (C.Elapsed > 30.0)
		{
			Test->AddError(TEXT("Stage 3: the Warden never appeared (player may be watching the spawn for 30 s)"));
			return true;
		}
		return false;
	}, 60.f);

	R->Add(TEXT("Stage 5: relocates to WSpawn_Cloister"), [S, Test](FWCtx& C)
	{
		if (S->B1)
		{
			return true;
		}
		if (C.bFirst)
		{
			SetStage(C.W, 5);
		}
		const float D = Dist2D(C.WardenLoc(), S->Loc(TEXT("WSpawn_Cloister")));
		if (D < 150.f && C.State() != ELBWardenState::Return)
		{
			Note(FString::Printf(TEXT("stage 5: at WSpawn_Cloister after %.1fs, state %s"), C.Elapsed, LBWardenLogic::StateName(C.State())));
			return true;
		}
		if (C.Elapsed > 90.0)
		{
			Test->AddError(FString::Printf(TEXT("Stage 5: the Warden never reached WSpawn_Cloister (at %s, %.0f cm away, state %s)"), *C.WardenLoc().ToCompactString(), D, LBWardenLogic::StateName(C.State())));
			return true;
		}
		return false;
	}, 150.f);

	Enqueue(R);
	return true;
}

#endif
