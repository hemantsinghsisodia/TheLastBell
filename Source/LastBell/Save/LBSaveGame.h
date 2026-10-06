#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "GameplayTagContainer.h"
#include "LBSaveGame.generated.h"

/** Fixed struct; part of the save-version contract. Only for state that cannot be a tag. */
USTRUCT(BlueprintType)
struct LASTBELL_API FLBActorSaveRecord
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Save")
	bool bState = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Save")
	float Value = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Save")
	int32 Index = 0;
};

UCLASS()
class LASTBELL_API ULBSaveGame : public USaveGame
{
	GENERATED_BODY()

public:
	static constexpr int32 CurrentVersion = 1;

	/** True when a save of this version can be loaded by the current build. */
	static bool IsVersionCompatible(int32 Version) { return Version == CurrentVersion; }

	UPROPERTY()
	int32 SaveVersion = CurrentVersion;

	UPROPERTY()
	FName CheckpointId;

	/** Long package name of the map, e.g. /Game/LastBell/Maps/L_Test_MicroSlice. */
	UPROPERTY()
	FString MapName;

	UPROPERTY()
	FTransform CheckpointTransform;

	UPROPERTY()
	FGameplayTagContainer WorldState;

	/** Checkpoints are stored here rather than as tags: dynamic tag names cannot be registered at runtime. */
	UPROPERTY()
	TSet<FName> ReachedCheckpoints;

	UPROPERTY()
	TMap<FName, FLBActorSaveRecord> ActorRecords;

	UPROPERTY()
	float PlayTimeSeconds = 0.f;
};
