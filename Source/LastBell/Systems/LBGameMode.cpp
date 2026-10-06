#include "Systems/LBGameMode.h"
#include "Systems/LBPlayerController.h"
#include "Character/LBCharacter.h"
#include "Save/LBSaveSubsystem.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "LBLog.h"

ALBGameMode::ALBGameMode()
{
	DefaultPawnClass = ALBCharacter::StaticClass();
	PlayerControllerClass = ALBPlayerController::StaticClass();
}

void ALBGameMode::RestartPlayer(AController* NewPlayer)
{
	const ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(this);
	if (NewPlayer && Save && Save->HasPendingRestore())
	{
		UE_LOG(LogLB, Log, TEXT("Spawning player at pending checkpoint transform"));
		RestartPlayerAtTransform(NewPlayer, Save->GetPendingTransform());
		return;
	}
	Super::RestartPlayer(NewPlayer);
}

void ALBGameMode::HandlePlayerDeath(AController* Controller)
{
	ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(this);
	if (!Save)
	{
		UE_LOG(LogLB, Error, TEXT("HandlePlayerDeath: no save subsystem"));
		return;
	}
	if (Save->LoadLastCheckpoint())
	{
		return;
	}
	const FString MapName = UWorld::RemovePIEPrefix(GetOutermost()->GetName());
	UE_LOG(LogLB, Log, TEXT("No valid save on death; starting new game on %s"), *MapName);
	Save->NewGame(MapName);
}
