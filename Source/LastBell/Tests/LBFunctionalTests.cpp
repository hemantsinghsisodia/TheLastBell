#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Editor.h"
#include "EngineUtils.h"
#include "Tests/AutomationEditorCommon.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerController.h"
#include "Components/ArrowComponent.h"
#include "Kismet/GameplayStatics.h"
#include "GameplayTagContainer.h"
#include "Character/LBCharacter.h"
#include "Components/LBInteractorComponent.h"
#include "Components/LBInteractableComponent.h"
#include "Objectives/LBObjectiveSubsystem.h"
#include "Save/LBCheckpoint.h"
#include "Save/LBSaveGame.h"
#include "Save/LBSaveSubsystem.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "LBLog.h"

namespace
{
	const TCHAR* GMapPath = TEXT("/Game/LastBell/Maps/L_Test_MicroSlice");
	const TCHAR* GSlot = TEXT("LB_Slot0");

	FGameplayTag Tag(const TCHAR* Name)
	{
		return FGameplayTag::RequestGameplayTag(FName(Name), false);
	}

	class FLBMicroSliceCommand : public IAutomationLatentCommand
	{
	public:
		explicit FLBMicroSliceCommand(FAutomationTestBase* InTest) : Test(InTest)
		{
			BuildSteps();
		}

		virtual bool Update() override
		{
			if (bFinished)
			{
				return true;
			}
			if (StepIndex >= Steps.Num())
			{
				bFinished = true;
				return true;
			}

			FStep& Step = Steps[StepIndex];
			if (!bStepEntered)
			{
				bStepEntered = true;
				StepStart = FPlatformTime::Seconds();
				FramesInStep = 0;
				Aux = 0;
				ErrorsAtStepStart = ErrCount();
				UE_LOG(LogLB, Display, TEXT("[MicroSlice] STEP %d begin: %s"), StepIndex + 1, *Step.Name);
			}

			const bool bDone = Step.Fn();
			++FramesInStep;

			const bool bTimedOut = !bDone && (FPlatformTime::Seconds() - StepStart) > Step.TimeoutSeconds;
			if (bDone || bTimedOut)
			{
				if (bTimedOut)
				{
					Test->AddError(FString::Printf(TEXT("Step %d '%s' timed out after %.0fs. %s"), StepIndex + 1, *Step.Name, Step.TimeoutSeconds, *Diagnostics()));
				}
				const bool bPass = ErrCount() == ErrorsAtStepStart;
				UE_LOG(LogLB, Display, TEXT("[MicroSlice] STEP %d %s: %s"), StepIndex + 1, bPass ? TEXT("PASS") : TEXT("FAIL"), *Step.Name);
				if (bTimedOut || bAbort)
				{
					Abort();
					return true;
				}
				++StepIndex;
				bStepEntered = false;
			}
			return false;
		}

	private:
		struct FStep
		{
			FString Name;
			float TimeoutSeconds;
			TFunction<bool()> Fn;
		};

		FAutomationTestBase* Test;
		TArray<FStep> Steps;
		int32 StepIndex = 0;
		bool bStepEntered = false;
		bool bFinished = false;
		bool bAbort = false;
		double StepStart = 0.0;
		int32 FramesInStep = 0;
		int32 Aux = 0;
		int32 ErrorsAtStepStart = 0;
		TWeakObjectPtr<UWorld> OldWorld;

		// ---- helpers
		int32 ErrCount() const
		{
			FAutomationTestExecutionInfo Info;
			Test->GetExecutionInfo(Info);
			return Info.GetErrorTotal();
		}

		UWorld* World() const { return GEditor ? GEditor->PlayWorld.Get() : nullptr; }

		ALBCharacter* Pawn() const
		{
			UWorld* W = World();
			APlayerController* PC = W ? W->GetFirstPlayerController() : nullptr;
			return PC ? Cast<ALBCharacter>(PC->GetPawn()) : nullptr;
		}

		bool WorldReady() const
		{
			UWorld* W = World();
			return W && W->HasBegunPlay() && Pawn() != nullptr && W->GetSubsystem<ULBObjectiveSubsystem>() != nullptr;
		}

		ULBWorldStateSubsystem* State() const { return ULBWorldStateSubsystem::Get(World()); }
		ULBSaveSubsystem* Save() const { return ULBSaveSubsystem::Get(World()); }

		int32 ObjIndex() const
		{
			const ULBObjectiveSubsystem* Obj = World() ? World()->GetSubsystem<ULBObjectiveSubsystem>() : nullptr;
			return Obj ? Obj->GetActiveIndex() : -999;
		}

		bool Has(const TCHAR* Name) const
		{
			const ULBWorldStateSubsystem* S = State();
			return S && S->HasState(Tag(Name));
		}

		FString Diagnostics() const
		{
			FString Out;
			if (const ALBCharacter* P = Pawn())
			{
				Out += FString::Printf(TEXT("Pawn=%s Yaw/Pitch=%s. "), *P->GetActorLocation().ToString(),
					*P->GetControlRotation().ToString());
				if (const ULBInteractableComponent* F = P->GetInteractor()->GetFocusedComponent())
				{
					Out += FString::Printf(TEXT("Focus=%s. "), *GetNameSafe(F->GetOwner()));
				}
				else
				{
					Out += TEXT("Focus=none. ");
				}
			}
			else
			{
				Out += TEXT("No pawn. ");
			}
			if (const ULBWorldStateSubsystem* S = State())
			{
				Out += FString::Printf(TEXT("State=%s. ObjIndex=%d."), *S->GetState().ToStringSimple(), ObjIndex());
			}
			return Out;
		}

		void Abort()
		{
			bAbort = true;
			bFinished = true;
			if (GEditor)
			{
				GEditor->RequestEndPlayMap();
			}
			UGameplayStatics::DeleteGameInSlot(GSlot, 0);
		}

		void Teleport(const FVector& Location, float Yaw)
		{
			if (ALBCharacter* P = Pawn())
			{
				P->SetActorLocation(Location, false, nullptr, ETeleportType::TeleportPhysics);
				if (AController* C = P->GetController())
				{
					C->SetControlRotation(FRotator(0.f, Yaw, 0.f));
				}
			}
		}

		void AimAt(const AActor* Target)
		{
			ALBCharacter* P = Pawn();
			if (!P || !Target)
			{
				return;
			}
			FVector Origin, Extent;
			Target->GetActorBounds(true, Origin, Extent);
			FVector Eye = P->GetActorLocation() + FVector(0, 0, 64.f);
			if (AController* C = P->GetController())
			{
				C->SetControlRotation((Origin - Eye).Rotation());
			}
		}

		AActor* FindActor(const TCHAR* ClassPrefix, const FVector& ApproxLocation) const
		{
			UWorld* W = World();
			if (!W)
			{
				return nullptr;
			}
			for (TActorIterator<AActor> It(W); It; ++It)
			{
				if (It->GetClass()->GetName().StartsWith(ClassPrefix) && FVector::DistXY(It->GetActorLocation(), ApproxLocation) < 60.f)
				{
					return *It;
				}
			}
			return nullptr;
		}

		float HingeYaw(const FVector& DoorLoc) const
		{
			AActor* Door = FindActor(TEXT("BP_Door_Base"), DoorLoc);
			if (!Door)
			{
				return -999.f;
			}
			TInlineComponentArray<USceneComponent*> Comps(Door);
			for (USceneComponent* C : Comps)
			{
				if (C->GetName() == TEXT("Hinge"))
				{
					return C->GetRelativeRotation().Yaw;
				}
			}
			return -998.f;
		}

		FString SavedCheckpointId(const ULBSaveGame*& OutSave) const
		{
			OutSave = nullptr;
			if (!UGameplayStatics::DoesSaveGameExist(GSlot, 0))
			{
				return FString();
			}
			OutSave = Cast<ULBSaveGame>(UGameplayStatics::LoadGameFromSlot(GSlot, 0));
			return OutSave ? OutSave->CheckpointId.ToString() : FString();
		}

		/** Teleport, aim at the actor, wait for the camera to update, then interact (retrying) until Cond holds. */
		TFunction<bool()> InteractStep(FVector From, const TCHAR* ClassPrefix, FVector ActorLoc, TFunction<bool()> Cond)
		{
			return [this, From, ClassPrefix, ActorLoc, Cond]() -> bool
			{
				if (Aux == 0)
				{
					Teleport(From, 0.f);
					AActor* Target = FindActor(ClassPrefix, ActorLoc);
					if (!Test->TestNotNull(FString::Printf(TEXT("Find %s near %s"), ClassPrefix, *ActorLoc.ToString()), Target))
					{
						bAbort = true;
						return true;
					}
					AimAt(Target);
					Aux = 1;
					FramesInStep = 0;
					return false;
				}
				if (Cond())
				{
					return true;
				}
				// Wait for the camera manager to pick up the new view, retry every 30 frames.
				if (FramesInStep >= 6 && (FramesInStep - 6) % 30 == 0)
				{
					if (AActor* Target = FindActor(ClassPrefix, ActorLoc))
					{
						AimAt(Target);
					}
					UE_LOG(LogLB, Display, TEXT("[MicroSlice] TryInteract from %s toward %s"), *From.ToString(), ClassPrefix);
					if (ALBCharacter* P = Pawn())
					{
						P->GetInteractor()->TryInteract();
					}
				}
				return false;
			};
		}

		void BuildSteps()
		{
			const FVector Door1Loc(600, -55, 0), Door2Loc(1400, -55, 0), LeverLoc(1000, -485, 0);

			// 1. PIE start
			Steps.Add({ TEXT("PIE start, clean state"), 60.f, [this]()
			{
				if (!WorldReady() || FramesInStep < 5)
				{
					return false;
				}
				Test->TestEqual(TEXT("Initial objective index"), ObjIndex(), 0);
				Test->TestEqual(TEXT("Initial world state empty"), State()->GetState().Num(), 0);
				Test->TestFalse(TEXT("No save at start"), UGameplayStatics::DoesSaveGameExist(GSlot, 0));
				return true;
			} });

			// 2. Door 1
			Steps.Add({ TEXT("Interact Door1"), 30.f, [this, Door1Loc]()
			{
				static TFunction<bool()> Impl;
				if (Aux == 0) { Impl = InteractStep(FVector(450, 0, 92), TEXT("BP_Door_Base"), Door1Loc, [this]() { return Has(TEXT("State.Test.Door1Open")); }); }
				if (!Impl()) { return false; }
				Test->TestTrue(TEXT("Door1Open"), Has(TEXT("State.Test.Door1Open")));
				// Objective may need a frame.
				if (ObjIndex() != 1 && FramesInStep < 400) { return false; }
				Test->TestEqual(TEXT("Objective index after Door1"), ObjIndex(), 1);
				return true;
			} });

			// 3. CP_Room
			Steps.Add({ TEXT("Checkpoint CP_Room saves"), 20.f, [this]()
			{
				if (Aux == 0) { Teleport(FVector(750, 0, 92), 0.f); Aux = 1; return false; }
				const ULBSaveGame* S = nullptr;
				if (SavedCheckpointId(S) != TEXT("CP_Room")) { return false; }
				Test->TestTrue(TEXT("Save contains Door1Open"), S->WorldState.HasTagExact(Tag(TEXT("State.Test.Door1Open"))));
				Test->TestTrue(TEXT("HasValidSave"), Save() && Save()->HasValidSave());
				return true;
			} });

			// 4. Lever
			Steps.Add({ TEXT("Interact Lever (pulls, opens Door2)"), 30.f, [this, LeverLoc]()
			{
				static TFunction<bool()> Impl;
				if (Aux == 0) { Impl = InteractStep(FVector(1000, -380, 92), TEXT("BP_Lever"), LeverLoc, [this]() { return Has(TEXT("State.Test.LeverPulled")); }); }
				if (!Impl()) { return false; }
				Test->TestTrue(TEXT("LeverPulled"), Has(TEXT("State.Test.LeverPulled")));
				if (!Has(TEXT("State.Test.Door2Open")) && FramesInStep < 400) { return false; }
				Test->TestTrue(TEXT("Door2Open (auto)"), Has(TEXT("State.Test.Door2Open")));
				if (ObjIndex() != 2 && FramesInStep < 400) { return false; }
				Test->TestEqual(TEXT("Objective index after lever"), ObjIndex(), 2);
				return true;
			} });

			// 5. CP_Exit
			Steps.Add({ TEXT("Checkpoint CP_Exit saves"), 20.f, [this]()
			{
				if (Aux == 0) { Teleport(FVector(1550, 0, 92), 0.f); Aux = 1; return false; }
				const ULBSaveGame* S = nullptr;
				if (SavedCheckpointId(S) != TEXT("CP_Exit")) { return false; }
				Test->TestTrue(TEXT("CP_Exit save contains LeverPulled"), S->WorldState.HasTagExact(Tag(TEXT("State.Test.LeverPulled"))));
				return true;
			} });

			// 6. Kill -> reload at checkpoint
			Steps.Add({ TEXT("Kill and restore from CP_Exit"), 60.f, [this, Door1Loc, Door2Loc, LeverLoc]()
			{
				if (Aux == 0)
				{
					OldWorld = World();
					Pawn()->Kill();
					Aux = 1;
					return false;
				}
				if (World() == OldWorld.Get() || !WorldReady()) { return false; }
				if (Aux == 1) { Aux = 2; FramesInStep = 0; return false; }
				if (FramesInStep < 15) { return false; }

				Test->TestTrue(TEXT("Restored Door1Open"), Has(TEXT("State.Test.Door1Open")));
				Test->TestTrue(TEXT("Restored LeverPulled"), Has(TEXT("State.Test.LeverPulled")));
				Test->TestTrue(TEXT("Restored Door2Open"), Has(TEXT("State.Test.Door2Open")));
				Test->TestEqual(TEXT("Restored objective index"), ObjIndex(), 2);

				for (TActorIterator<ALBCheckpoint> It(World()); It; ++It)
				{
					if (It->CheckpointId == TEXT("CP_Exit"))
					{
						const UArrowComponent* Arrow = It->FindComponentByClass<UArrowComponent>();
						const FVector Expected = Arrow ? Arrow->GetComponentLocation() : It->GetActorLocation();
						const float Dist = FVector::Dist(Pawn()->GetActorLocation(), Expected);
						Test->TestTrue(FString::Printf(TEXT("Pawn within 50cm of CP_Exit arrow (dist %.1f, pawn %s, arrow %s)"), Dist,
							*Pawn()->GetActorLocation().ToString(), *Expected.ToString()), Dist <= 50.f);
					}
				}
				Test->TestTrue(FString::Printf(TEXT("Door1 hinge yaw ~90 (was %.1f)"), HingeYaw(Door1Loc)), FMath::IsNearlyEqual(HingeYaw(Door1Loc), 90.f, 2.f));
				Test->TestTrue(FString::Printf(TEXT("Door2 hinge yaw ~90 (was %.1f)"), HingeYaw(Door2Loc)), FMath::IsNearlyEqual(HingeYaw(Door2Loc), 90.f, 2.f));
				if (AActor* Lever = FindActor(TEXT("BP_Lever"), LeverLoc))
				{
					const ULBInteractableComponent* Comp = Lever->FindComponentByClass<ULBInteractableComponent>();
					Test->TestTrue(TEXT("Lever interactable disabled after restore"), Comp && !Comp->bEnabled);
				}
				else
				{
					Test->AddError(TEXT("Lever not found after reload"));
				}
				return true;
			} });

			// 7. Exit trigger
			Steps.Add({ TEXT("Exit trigger completes objectives"), 20.f, [this]()
			{
				if (Aux == 0) { Teleport(FVector(2000, 0, 150), 0.f); Aux = 1; return false; }
				if (!Has(TEXT("State.Test.ExitReached"))) { return false; }
				if (ObjIndex() != INDEX_NONE && FramesInStep < 300) { return false; }
				Test->TestEqual(TEXT("All objectives complete"), ObjIndex(), static_cast<int32>(INDEX_NONE));
				return true;
			} });

			// 8. NewGame
			Steps.Add({ TEXT("NewGame resets everything"), 60.f, [this, Door1Loc]()
			{
				if (Aux == 0)
				{
					OldWorld = World();
					const FString Map = UWorld::RemovePIEPrefix(World()->GetOutermost()->GetName());
					Save()->NewGame(Map);
					Aux = 1;
					return false;
				}
				if (World() == OldWorld.Get() || !WorldReady()) { return false; }
				if (Aux == 1) { Aux = 2; FramesInStep = 0; return false; }
				if (FramesInStep < 15) { return false; }

				Test->TestEqual(TEXT("State empty after NewGame"), State()->GetState().Num(), 0);
				Test->TestEqual(TEXT("Objective index 0 after NewGame"), ObjIndex(), 0);
				Test->TestFalse(TEXT("No save after NewGame"), UGameplayStatics::DoesSaveGameExist(GSlot, 0));
				Test->TestTrue(FString::Printf(TEXT("Door1 hinge yaw ~0 (was %.1f)"), HingeYaw(Door1Loc)), FMath::IsNearlyEqual(HingeYaw(Door1Loc), 0.f, 2.f));
				return true;
			} });

			// 9. End PIE
			Steps.Add({ TEXT("End PIE and clean up"), 30.f, [this]()
			{
				if (Aux == 0) { GEditor->RequestEndPlayMap(); Aux = 1; return false; }
				if (World()) { return false; }
				UGameplayStatics::DeleteGameInSlot(GSlot, 0);
				Test->TestFalse(TEXT("Save cleaned"), UGameplayStatics::DoesSaveGameExist(GSlot, 0));
				return true;
			} });
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBMicroSliceFunctionalTest, "LastBell.Functional.MicroSlice",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBMicroSliceFunctionalTest::RunTest(const FString& Parameters)
{
	UGameplayStatics::DeleteGameInSlot(GSlot, 0);

	FAutomationEditorCommonUtils::LoadMap(GMapPath);

	FRequestPlaySessionParams PlayParams;
	PlayParams.WorldType = EPlaySessionWorldType::PlayInEditor;
	GEditor->RequestPlaySession(PlayParams);

	ADD_LATENT_AUTOMATION_COMMAND(FLBMicroSliceCommand(this));
	return true;
}

#endif
