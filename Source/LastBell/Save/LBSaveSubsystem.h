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

	static const FString SlotName;
	static constexpr int32 UserIndex = 0;

private:
	ULBSaveGame* ReadValidSaveFromDisk() const;
	void OnPostWorldInitialization(UWorld* World, const UWorld::InitializationValues IVS);
	void ClearPendingRestore();
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
