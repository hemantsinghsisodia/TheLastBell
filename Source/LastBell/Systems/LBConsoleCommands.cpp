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
#include "Systems/LBUserSettings.h"
#include "Storm/LBStormSubsystem.h"
#include "Storm/LBStormFXSubsystem.h"
#include "Misc/DefaultValueHelper.h"
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

	static bool ParseFloat(const TArray<FString>& Args, const TCHAR* Cmd, float& Out)
	{
		if (Args.Num() < 1 || !FDefaultValueHelper::ParseFloat(Args[0], Out))
		{
			UE_LOG(LogLB, Error, TEXT("%s: expected a number"), Cmd);
			return false;
		}
		return true;
	}

	static bool ParseBool(const TArray<FString>& Args, const TCHAR* Cmd, bool& Out)
	{
		if (Args.Num() < 1 || (Args[0] != TEXT("0") && Args[0] != TEXT("1")))
		{
			UE_LOG(LogLB, Error, TEXT("%s: expected 0 or 1"), Cmd);
			return false;
		}
		Out = Args[0] == TEXT("1");
		return true;
	}

	static void Sensitivity(const TArray<FString>& Args)
	{
		float Value = 1.f;
		if (ParseFloat(Args, TEXT("lb.Sensitivity"), Value))
		{
			ULBUserSettings::GetUserSettings()->SetMouseSensitivity(Value);
			UE_LOG(LogLB, Display, TEXT("lb.Sensitivity = %.2f"), ULBUserSettings::Get()->MouseSensitivity);
		}
	}

	static void InvertY(const TArray<FString>& Args)
	{
		bool bValue = false;
		if (ParseBool(Args, TEXT("lb.InvertY"), bValue))
		{
			ULBUserSettings::GetUserSettings()->SetInvertY(bValue);
		}
	}

	static void HeadBob(const TArray<FString>& Args)
	{
		bool bValue = true;
		if (ParseBool(Args, TEXT("lb.HeadBob"), bValue))
		{
			ULBUserSettings::GetUserSettings()->SetHeadBob(bValue);
		}
	}

	static ULBStormSubsystem* GetStorm(UWorld* World, const TCHAR* Cmd)
	{
		ULBStormSubsystem* Storm = World ? World->GetSubsystem<ULBStormSubsystem>() : nullptr;
		if (!Storm || !Storm->IsActive())
		{
			UE_LOG(LogLB, Warning, TEXT("%s: the storm is not active in this world (needs an actor tagged LB_StormMoon and DA_StormSettings)"), Cmd);
			return nullptr;
		}
		return Storm;
	}

	/** lb.Storm.Flash [brightness=1] [profile=-1]: profile -1 is random, 0 sheet, 1 double, 2 triple. */
	static void StormFlash(const TArray<FString>& Args, UWorld* World)
	{
		ULBStormSubsystem* Storm = GetStorm(World, TEXT("lb.Storm.Flash"));
		if (!Storm)
		{
			return;
		}
		float Brightness = 1.f;
		int32 Profile = -1;
		if (Args.Num() > 0 && !FDefaultValueHelper::ParseFloat(Args[0], Brightness))
		{
			UE_LOG(LogLB, Error, TEXT("lb.Storm.Flash: expected [brightness] [profile]"));
			return;
		}
		if (Args.Num() > 1 && !FDefaultValueHelper::ParseInt(Args[1], Profile))
		{
			UE_LOG(LogLB, Error, TEXT("lb.Storm.Flash: profile must be -1 (random), 0 (sheet), 1 (double) or 2 (triple)"));
			return;
		}
		const ELBFlashProfile Chosen = Profile == 0 ? ELBFlashProfile::Sheet : Profile == 1 ? ELBFlashProfile::Double : Profile == 2 ? ELBFlashProfile::Triple : ELBFlashProfile::Auto;
		Storm->RequestFlash(FMath::Clamp(Brightness, 0.f, 1.f), 0.f, ELBFlashReason::Debug, Chosen);
	}

	/** lb.Storm.Intensity <0..1 | -1>: overrides the story intensity (-1 clears it). */
	static void StormIntensity(const TArray<FString>& Args, UWorld* World)
	{
		ULBStormSubsystem* Storm = GetStorm(World, TEXT("lb.Storm.Intensity"));
		float Value = -1.f;
		if (Storm && ParseFloat(Args, TEXT("lb.Storm.Intensity"), Value))
		{
			Storm->SetConsoleIntensityOverride(Value < 0.f ? -1.f : FMath::Clamp(Value, 0.f, 1.f));
			UE_LOG(LogLB, Display, TEXT("lb.Storm.Intensity = %.2f%s"), Value, Value < 0.f ? TEXT(" (cleared)") : TEXT(""));
		}
	}

	/** lb.Storm.Freeze <0..1 | -1>: holds the flash value there and pauses the schedule (-1 clears it). */
	static void StormFreeze(const TArray<FString>& Args, UWorld* World)
	{
		ULBStormSubsystem* Storm = GetStorm(World, TEXT("lb.Storm.Freeze"));
		float Value = -1.f;
		if (Storm && ParseFloat(Args, TEXT("lb.Storm.Freeze"), Value))
		{
			Storm->SetConsoleFreeze(Value < 0.f ? -1.f : FMath::Clamp(Value, 0.f, 1.f));
			UE_LOG(LogLB, Display, TEXT("lb.Storm.Freeze = %.2f%s"), Value, Value < 0.f ? TEXT(" (cleared)") : TEXT(""));
		}
	}

	static FAutoConsoleCommand CmdSensitivity(TEXT("lb.Sensitivity"), TEXT("lb.Sensitivity <float>: mouse sensitivity (saved)"),
		FConsoleCommandWithArgsDelegate::CreateStatic(&Sensitivity));
	static FAutoConsoleCommand CmdInvertY(TEXT("lb.InvertY"), TEXT("lb.InvertY 0|1: invert look Y (saved)"),
		FConsoleCommandWithArgsDelegate::CreateStatic(&InvertY));
	static FAutoConsoleCommand CmdHeadBob(TEXT("lb.HeadBob"), TEXT("lb.HeadBob 0|1: head bob (saved)"),
		FConsoleCommandWithArgsDelegate::CreateStatic(&HeadBob));

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
	/** lb.StormFX.Bolt [0|1]: a debug flash with a bolt. 0 a sky bolt, 1 a tower strike (at the actor tagged LB_StrikeTarget_Tower). */
	static void StormFXBolt(const TArray<FString>& Args, UWorld* World)
	{
		ULBStormFXSubsystem* FX = World ? World->GetSubsystem<ULBStormFXSubsystem>() : nullptr;
		if (!FX)
		{
			UE_LOG(LogLB, Warning, TEXT("lb.StormFX.Bolt: there is no storm FX subsystem in this world"));
			return;
		}
		int32 Kind = 0;
		if (Args.Num() > 0 && (!FDefaultValueHelper::ParseInt(Args[0], Kind) || (Kind != 0 && Kind != 1)))
		{
			UE_LOG(LogLB, Error, TEXT("lb.StormFX.Bolt: expected [0|1] (0 a sky bolt, 1 a tower strike)"));
			return;
		}
		FX->RequestDebugBolt(Kind);
	}

	static FAutoConsoleCommandWithWorldAndArgs CmdStormFXBolt(TEXT("lb.StormFX.Bolt"), TEXT("lb.StormFX.Bolt [0|1]: a debug flash with a bolt (0 a sky bolt, 1 a tower strike). lb.StormFX.Enabled 0|1 turns the storm FX off or on"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&StormFXBolt));
	static FAutoConsoleCommandWithWorldAndArgs CmdStormFlash(TEXT("lb.Storm.Flash"), TEXT("lb.Storm.Flash [brightness=1] [profile=-1]: a lightning flash now (profile -1 random, 0 sheet, 1 double, 2 triple)"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&StormFlash));
	static FAutoConsoleCommandWithWorldAndArgs CmdStormIntensity(TEXT("lb.Storm.Intensity"), TEXT("lb.Storm.Intensity <0..1 | -1>: override the storm intensity, -1 clears"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&StormIntensity));
	static FAutoConsoleCommandWithWorldAndArgs CmdStormFreeze(TEXT("lb.Storm.Freeze"), TEXT("lb.Storm.Freeze <0..1 | -1>: hold the flash value and pause the schedule, -1 clears"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&StormFreeze));
	static FAutoConsoleCommandWithWorldAndArgs CmdKill(TEXT("lb.Kill"), TEXT("Kill the local player (death path)"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&Kill));
}

#endif // !UE_BUILD_SHIPPING
