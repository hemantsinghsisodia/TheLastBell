#include "CoreMinimal.h"

#if !UE_BUILD_SHIPPING

#include "HAL/IConsoleManager.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "GameplayTagContainer.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "Save/LBSaveSubsystem.h"
#include "Character/LBCharacter.h"
#include "GameFramework/PlayerController.h"
#include "LBLog.h"

namespace LBConsole
{
	static FGameplayTag ParseTag(const TArray<FString>& Args, const TCHAR* Cmd)
	{
		if (Args.Num() < 1)
		{
			UE_LOG(LogLB, Error, TEXT("%s: missing tag argument"), Cmd);
			return FGameplayTag();
		}
		const FGameplayTag Tag = FGameplayTag::RequestGameplayTag(FName(*Args[0]), false);
		if (!Tag.IsValid())
		{
			UE_LOG(LogLB, Error, TEXT("%s: unknown gameplay tag '%s'"), Cmd, *Args[0]);
		}
		return Tag;
	}

	static void StateAdd(const TArray<FString>& Args, UWorld* World)
	{
		ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(World);
		const FGameplayTag Tag = ParseTag(Args, TEXT("lb.State.Add"));
		if (State && Tag.IsValid())
		{
			State->AddState(Tag);
		}
	}

	static void StateRemove(const TArray<FString>& Args, UWorld* World)
	{
		ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(World);
		const FGameplayTag Tag = ParseTag(Args, TEXT("lb.State.Remove"));
		if (State && Tag.IsValid())
		{
			State->RemoveState(Tag);
		}
	}

	static void StateDump(const TArray<FString>& Args, UWorld* World)
	{
		if (const ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(World))
		{
			const FGameplayTagContainer Tags = State->GetState();
			UE_LOG(LogLB, Display, TEXT("World state (%d tags):"), Tags.Num());
			for (const FGameplayTag& Tag : Tags)
			{
				UE_LOG(LogLB, Display, TEXT("  %s"), *Tag.ToString());
			}
		}
	}

	static void NewGame(const TArray<FString>& Args, UWorld* World)
	{
		if (ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(World))
		{
			const FString Map = Args.Num() > 0 ? Args[0] : UWorld::RemovePIEPrefix(World->GetOutermost()->GetName());
			Save->NewGame(Map);
		}
	}

	static void CheckpointLoad(const TArray<FString>& Args, UWorld* World)
	{
		if (ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(World))
		{
			if (!Save->LoadLastCheckpoint())
			{
				UE_LOG(LogLB, Warning, TEXT("lb.Checkpoint.Load: no valid save"));
			}
		}
	}

	static void Menu(const TArray<FString>& Args, UWorld* World)
	{
		if (ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(World))
		{
			Save->ReturnToMainMenu();
		}
	}

	static void CompleteGame(const TArray<FString>& Args, UWorld* World)
	{
		if (ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(World))
		{
			Save->CompleteGame();
		}
	}

	static void Kill(const TArray<FString>& Args, UWorld* World)
	{
		const APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
		if (ALBCharacter* Character = PC ? Cast<ALBCharacter>(PC->GetPawn()) : nullptr)
		{
			Character->Kill();
		}
		else
		{
			UE_LOG(LogLB, Error, TEXT("lb.Kill: no ALBCharacter pawn"));
		}
	}

	static FAutoConsoleCommandWithWorldAndArgs CmdStateAdd(TEXT("lb.State.Add"), TEXT("lb.State.Add <Tag>"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&StateAdd));
	static FAutoConsoleCommandWithWorldAndArgs CmdStateRemove(TEXT("lb.State.Remove"), TEXT("lb.State.Remove <Tag>"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&StateRemove));
	static FAutoConsoleCommandWithWorldAndArgs CmdStateDump(TEXT("lb.State.Dump"), TEXT("Log all world state tags"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&StateDump));
	static FAutoConsoleCommandWithWorldAndArgs CmdNewGame(TEXT("lb.NewGame"), TEXT("lb.NewGame [LongPackageName]: delete save, reset state, open map"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&NewGame));
	static FAutoConsoleCommandWithWorldAndArgs CmdCheckpointLoad(TEXT("lb.Checkpoint.Load"), TEXT("Load the last checkpoint"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CheckpointLoad));
	static FAutoConsoleCommandWithWorldAndArgs CmdMenu(TEXT("lb.Menu"), TEXT("Return to the main menu (save untouched)"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&Menu));
	static FAutoConsoleCommandWithWorldAndArgs CmdCompleteGame(TEXT("lb.CompleteGame"), TEXT("Delete save, reset progress, return to the main menu"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CompleteGame));
	static FAutoConsoleCommandWithWorldAndArgs CmdKill(TEXT("lb.Kill"), TEXT("Kill the local player (death path)"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&Kill));
}

#endif // !UE_BUILD_SHIPPING
