#include "Tests/LBRouteBot.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Editor.h"
#include "Tests/AutomationEditorCommon.h"
#include "Engine/World.h"
#include "Misc/PackageName.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "EnhancedInputSubsystems.h"
#include "InputActionValue.h"
#include "Character/LBCharacter.h"
#include "Save/LBSaveSubsystem.h"
#include "Systems/LBPlayerController.h"
#include "LBLog.h"

// D-033 regression: Main Menu -> New Game left the player unable to move or look. The menu controller's UI-only input
// mode (viewport ignores game input) survives travel, and the gameplay controller never restored game input.
// Flow under test: PIE on L_MainMenu -> ULBSaveSubsystem::StartNewGame (what the New Game button calls) -> L_Monastery.

namespace
{
	const TCHAR* GMenuMap = TEXT("/Game/LastBell/Maps/L_MainMenu");
	const TCHAR* GGameMapShort = TEXT("L_Monastery");

	void MenuNote(const FString& Text)
	{
		UE_LOG(LogLB, Display, TEXT("[MenuToGame] %s"), *Text);
	}

	FString ShortMap()
	{
		return FPackageName::GetShortName(LBPie::MapShortName());
	}

	UGameViewportClient* PieViewport()
	{
		UWorld* W = LBPie::World();
		UGameViewportClient* VP = W ? W->GetGameViewport() : nullptr;
		return VP ? VP : (GEngine ? GEngine->GameViewport.Get() : nullptr);
	}

	class FLBMenuToGameCommand : public IAutomationLatentCommand
	{
	public:
		explicit FLBMenuToGameCommand(FAutomationTestBase* InTest) : Test(InTest) {}

		virtual bool Update() override
		{
			if (Phase == EPhase::Teardown)
			{
				return !LBPie::World() || (FPlatformTime::Seconds() - PhaseStartWall) > 30.0;
			}

			const double Wall = FPlatformTime::Seconds();
			if (!bStarted)
			{
				bStarted = true;
				PhaseStartWall = Wall;
			}
			UWorld* W = LBPie::World();

			// Per-phase wall-clock timeout.
			const double Timeouts[] = { 60.0, 60.0, 30.0 };
			if (Phase != EPhase::Done && (Wall - PhaseStartWall) > Timeouts[static_cast<int32>(Phase)])
			{
				const ALBCharacter* P = LBPie::Pawn();
				Test->AddError(FString::Printf(TEXT("Phase %d timed out (map '%s', pawn %s, onGround %d, begunPlay %d)"), static_cast<int32>(Phase), *ShortMap(),
					*GetNameSafe(P), P && P->GetCharacterMovement() && P->GetCharacterMovement()->IsMovingOnGround(), W && W->HasBegunPlay()));
				BeginTeardown();
				return false;
			}

			switch (Phase)
			{
			case EPhase::MenuReady:
			{
				APlayerController* PC = W && W->HasBegunPlay() ? W->GetFirstPlayerController() : nullptr;
				if (!PC || ++Frames < 10)
				{
					return false;
				}
				MenuNote(FString::Printf(TEXT("menu world %s, controller %s"), *LBPie::MapShortName(), *GetNameSafe(PC)));
				Test->TestEqual(TEXT("Started on the main menu map"), ShortMap(), FString(TEXT("L_MainMenu")));
				ALBPlayerController* LBPC = Cast<ALBPlayerController>(PC);
				if (!Test->TestNotNull(TEXT("Menu PlayerController is an ALBPlayerController"), LBPC))
				{
					BeginTeardown();
					return false;
				}
				Test->TestTrue(TEXT("Menu controller bMenuMode"), LBPC->bMenuMode);
				UGameViewportClient* VP = PieViewport();
				if (Test->TestNotNull(TEXT("PIE game viewport (menu)"), VP))
				{
					Test->TestTrue(TEXT("Precondition: menu ignores game input"), VP->IgnoreInput());
				}

				ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(W);
				if (!Test->TestNotNull(TEXT("ULBSaveSubsystem"), Save))
				{
					BeginTeardown();
					return false;
				}
				OldWorld = W;
				Save->StartNewGame();
				EnterPhase(EPhase::GameReady);
				return false;
			}

			case EPhase::GameReady:
			{
				if (!W || W == OldWorld.Get() || !W->HasBegunPlay() || ShortMap() != GGameMapShort)
				{
					return false;
				}
				ALBCharacter* Pawn = LBPie::Pawn();
				if (!Pawn || !Pawn->GetCharacterMovement() || !Pawn->GetCharacterMovement()->IsMovingOnGround())
				{
					return false;
				}
				// Let BeginPlay settle and the pawn rest on the floor.
				if (++Frames < 30 || W->GetTimeSeconds() - FirstReadyTime(W) < 0.6)
				{
					return false;
				}

				MenuNote(FString::Printf(TEXT("game world %s, pawn %s"), *LBPie::MapShortName(), *GetNameSafe(Pawn)));
				APlayerController* PC = W->GetFirstPlayerController();
				ALBPlayerController* LBPC = Cast<ALBPlayerController>(PC);
				UGameViewportClient* VP = PieViewport();
				if (Test->TestNotNull(TEXT("PIE game viewport (game)"), VP))
				{
					Test->TestFalse(TEXT("Game input restored: viewport must not ignore input"), VP->IgnoreInput());
				}
				if (Test->TestNotNull(TEXT("Gameplay PlayerController is an ALBPlayerController"), LBPC))
				{
					Test->TestFalse(TEXT("Gameplay controller bMenuMode"), LBPC->bMenuMode);
					Test->TestFalse(TEXT("Mouse cursor hidden in game"), LBPC->bShowMouseCursor);
				}
				Test->TestNotNull(TEXT("Pawn is an ALBCharacter"), Pawn);
				Test->TestTrue(TEXT("Pawn is possessed by the player controller"), PC && Pawn->GetController() == PC);

				Start = Pawn->GetActorLocation();
				MoveStartWorldTime = W->GetTimeSeconds();
				EnterPhase(EPhase::Move);
				return false;
			}

			case EPhase::Move:
			{
				ALBCharacter* Pawn = LBPie::Pawn();
				if (!W || !Pawn)
				{
					Test->AddError(TEXT("Pawn lost during the move step"));
					BeginTeardown();
					return false;
				}
				InjectMove(Pawn);
				if (W->GetTimeSeconds() - MoveStartWorldTime < 1.0)
				{
					return false;
				}
				const double Moved = FVector::Dist2D(Start, Pawn->GetActorLocation());
				MenuNote(FString::Printf(TEXT("pawn moved %.1f cm in 1 s of injected Move"), Moved));
				Test->TestTrue(FString::Printf(TEXT("Injected Move for 1 s moves the pawn more than 50 cm (moved %.1f)"), Moved), Moved > 50.0);
				BeginTeardown();
				return false;
			}

			default:
				return true;
			}
		}

	private:
		enum class EPhase { MenuReady, GameReady, Move, Teardown, Done };

		void EnterPhase(EPhase Next)
		{
			Phase = Next;
			PhaseStartWall = FPlatformTime::Seconds();
			Frames = 0;
			ReadyTime = -1.0;
		}

		/** World time at which the game world first satisfied the ready conditions. */
		double FirstReadyTime(const UWorld* W)
		{
			if (ReadyTime < 0.0)
			{
				ReadyTime = W->GetTimeSeconds();
			}
			return ReadyTime;
		}

		void InjectMove(ALBCharacter* Pawn)
		{
			const APlayerController* PC = Cast<APlayerController>(Pawn->GetController());
			const ULocalPlayer* LP = PC ? PC->GetLocalPlayer() : nullptr;
			UEnhancedInputLocalPlayerSubsystem* Subsystem = LP ? LP->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>() : nullptr;
			if (!Subsystem || !Pawn->MoveAction)
			{
				return;
			}
			const TArray<UInputModifier*> NoModifiers;
			const TArray<UInputTrigger*> NoTriggers;
			Subsystem->InjectInputForAction(Pawn->MoveAction, FInputActionValue(FVector2D(0.0, 1.0)), NoModifiers, NoTriggers);
		}

		void BeginTeardown()
		{
			Phase = EPhase::Teardown;
			PhaseStartWall = FPlatformTime::Seconds();
			if (GEditor && LBPie::World())
			{
				GEditor->RequestEndPlayMap();
			}
			LBPie::ClearSlot();
		}

		FAutomationTestBase* Test;
		EPhase Phase = EPhase::MenuReady;
		bool bStarted = false;
		double PhaseStartWall = 0.0;
		double ReadyTime = -1.0;
		int32 Frames = 0;
		TWeakObjectPtr<UWorld> OldWorld;
		FVector Start = FVector::ZeroVector;
		double MoveStartWorldTime = 0.0;
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBMenuToGameInputTest, "LastBell.Functional.Flow.MenuToGameInput",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBMenuToGameInputTest::RunTest(const FString& Parameters)
{
	LBPie::ClearSlot();
	FAutomationEditorCommonUtils::LoadMap(GMenuMap);

	FRequestPlaySessionParams PlayParams;
	PlayParams.WorldType = EPlaySessionWorldType::PlayInEditor;
	GEditor->RequestPlaySession(PlayParams);

	ADD_LATENT_AUTOMATION_COMMAND(FLBMenuToGameCommand(this));
	return true;
}

#endif
