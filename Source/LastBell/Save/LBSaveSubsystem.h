#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Save/LBSaveGame.h"
#include "Save/LBSaveIdRegistry.h"
#include "LBSaveSubsystem.generated.h"

class ULBSaveStateComponent;

UCLASS()
class LASTBELL_API ULBSaveSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	static ULBSaveSubsystem* Get(const UObject* WorldContextObject);

	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	/** Deletes the save, resets world state and progress, then opens the map. MapName is a long package name. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Save")
	void NewGame(const FString& MapName);

	/** Flow API for menus: new game on the configured NewGameMap. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Flow")
	void StartNewGame();

	/** Loads the last checkpoint; false when there is no valid save. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Flow")
	bool ContinueGame();

	/** Deletes the save, resets all progress and returns to the main menu. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Flow")
	void CompleteGame();

	/** Opens the main menu map without touching the save. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Flow")
	void ReturnToMainMenu();

	/** Marks the checkpoint reached and writes the slot synchronously. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Save")
	bool SaveCheckpoint(FName Id, const FTransform& Transform);

	/** Reads the slot from disk, restores world state, sets the pending restore and opens the saved map. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Save")
	bool LoadLastCheckpoint();

	UFUNCTION(BlueprintPure, Category = "LastBell|Save")
	bool HasValidSave() const;

	UFUNCTION(BlueprintCallable, Category = "LastBell|Save")
	void DeleteSave();

	UFUNCTION(BlueprintPure, Category = "LastBell|Save")
	bool HasReachedCheckpoint(FName Id) const { return ReachedCheckpoints.Contains(Id); }

	UFUNCTION(BlueprintPure, Category = "LastBell|Save")
	bool HasPendingRestore() const { return bPendingRestore; }

	UFUNCTION(BlueprintPure, Category = "LastBell|Save")
	FTransform GetPendingTransform() const { return PendingTransform; }

	UFUNCTION(BlueprintCallable, Category = "LastBell|Save")
	bool TryGetRecord(FName SaveId, FLBActorSaveRecord& OutRecord) const;

	/** True between starting a level travel and the next world's initialization. */
	UFUNCTION(BlueprintPure, Category = "LastBell|Save")
	bool IsTravelPending() const { return bTravelPending; }

	/** Returns false (and does nothing) for None or duplicate ids. */
	bool RegisterSaveState(ULBSaveStateComponent* Component);
	void UnregisterSaveState(ULBSaveStateComponent* Component);

	/** Pure: known records overlaid by live ones (live wins). */
	static TMap<FName, FLBActorSaveRecord> MergeRecords(const TMap<FName, FLBActorSaveRecord>& Known, const TMap<FName, FLBActorSaveRecord>& Live);

	/**
	 * The slot file is the engine's save-game bytes followed by a 12 byte footer: magic, payload length, CRC32 of the payload.
	 * The engine's loader trusts its input (a truncated or damaged file can assert inside it, e.g. a garbage FName length), so
	 * every file is verified here BEFORE it reaches the loader. Encode fails only if the engine can't serialize the object.
	 */
	static bool EncodeSave(ULBSaveGame* Save, TArray<uint8>& OutFileBytes);
	/** Verifies the footer and returns the save, or null with a reason when the bytes are not an intact, complete save file. */
	static ULBSaveGame* DecodeSave(const TArray<uint8>& FileBytes, FString& OutReason);

	static const FString SlotName;
	static constexpr int32 UserIndex = 0;

private:
	ULBSaveGame* ReadValidSaveFromDisk() const;
	void OnPostWorldInitialization(UWorld* World, const UWorld::InitializationValues IVS);
	void ClearPendingRestore();
	bool OpenMainMenuMap();
	float GetPlayTime() const;

	FLBSaveIdRegistry IdRegistry;
	TMap<FName, TWeakObjectPtr<ULBSaveStateComponent>> SaveComponents;

	bool bPendingRestore = false;
	bool bTravelPending = false;
	FTransform PendingTransform;
	/** Last known records (from load or last save). Lets late-streamed components restore. */
	TMap<FName, FLBActorSaveRecord> KnownRecords;

	TSet<FName> ReachedCheckpoints;

	float PlayTimeBase = 0.f;
	double PlayTimeSegmentStart = 0.0;

	FDelegateHandle PostWorldInitHandle;
};
