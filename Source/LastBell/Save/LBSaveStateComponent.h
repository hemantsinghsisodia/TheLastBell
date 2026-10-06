#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Save/LBSaveGame.h"
#include "LBSaveStateComponent.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FLBRestoreSignature, const FLBActorSaveRecord&, Record);

/** Persists one small record for an actor whose state cannot be expressed as a tag. */
UCLASS(ClassGroup = "LastBell", meta = (BlueprintSpawnableComponent))
class LASTBELL_API ULBSaveStateComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	/** Hand-authored, unique, required. */
	UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category = "LastBell|Save")
	FName SaveId;

	UFUNCTION(BlueprintCallable, Category = "LastBell|Save")
	void SetRecord(const FLBActorSaveRecord& NewRecord) { CurrentRecord = NewRecord; }

	UFUNCTION(BlueprintPure, Category = "LastBell|Save")
	FLBActorSaveRecord GetRecord() const { return CurrentRecord; }

	/** Fired once on BeginPlay when a restore is pending and has a record for SaveId. Snap instantly, no effects. */
	UPROPERTY(BlueprintAssignable, Category = "LastBell|Save")
	FLBRestoreSignature OnRestore;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	UPROPERTY(Transient)
	FLBActorSaveRecord CurrentRecord;

	bool bRegistered = false;
};
