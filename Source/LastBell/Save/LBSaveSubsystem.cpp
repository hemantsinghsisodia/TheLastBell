#include "Save/LBSaveSubsystem.h"
#include "Save/LBSaveStateComponent.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"
#include "LBLog.h"

const FString ULBSaveSubsystem::SlotName = TEXT("LB_Slot0");

ULBSaveSubsystem* ULBSaveSubsystem::Get(const UObject* WorldContextObject)
{
	const UWorld* World = WorldContextObject ? WorldContextObject->GetWorld() : nullptr;
	UGameInstance* GameInstance = World ? World->GetGameInstance() : nullptr;
	return GameInstance ? GameInstance->GetSubsystem<ULBSaveSubsystem>() : nullptr;
}

void ULBSaveSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	Collection.InitializeDependency<ULBWorldStateSubsystem>();
	PlayTimeSegmentStart = FPlatformTime::Seconds();
	PostWorldInitHandle = FWorldDelegates::OnPostWorldInitialization.AddUObject(this, &ULBSaveSubsystem::OnPostWorldInitialization);
}

void ULBSaveSubsystem::Deinitialize()
{
	FWorldDelegates::OnPostWorldInitialization.Remove(PostWorldInitHandle);
	Super::Deinitialize();
}

float ULBSaveSubsystem::GetPlayTime() const
{
	return PlayTimeBase + static_cast<float>(FPlatformTime::Seconds() - PlayTimeSegmentStart);
}

void ULBSaveSubsystem::OnPostWorldInitialization(UWorld* World, const UWorld::InitializationValues IVS)
{
	if (!World || !World->IsGameWorld() || World->GetGameInstance() != GetGameInstance())
	{
		return;
	}
	TWeakObjectPtr<UWorld> WeakWorld(World);
	World->OnWorldBeginPlay.AddWeakLambda(this, [this, WeakWorld]()
	{
		// Clear one tick after BeginPlay so every actor's BeginPlay can pull its record first.
		if (UWorld* W = WeakWorld.Get())
		{
			W->GetTimerManager().SetTimerForNextTick(FTimerDelegate::CreateUObject(this, &ULBSaveSubsystem::ClearPendingRestore));
		}
	});
}

void ULBSaveSubsystem::ClearPendingRestore()
{
	if (bPendingRestore)
	{
		UE_LOG(LogLB, Log, TEXT("Pending restore cleared"));
	}
	bPendingRestore = false;
	PendingRecords.Reset();
}

void ULBSaveSubsystem::NewGame(const FString& MapName)
{
	UE_LOG(LogLB, Log, TEXT("New game: %s"), *MapName);
	DeleteSave();
	if (ULBWorldStateSubsystem* WorldState = GetGameInstance()->GetSubsystem<ULBWorldStateSubsystem>())
	{
		WorldState->ResetState();
	}
	ReachedCheckpoints.Reset();
	PendingRecords.Reset();
	bPendingRestore = false;
	PlayTimeBase = 0.f;
	PlayTimeSegmentStart = FPlatformTime::Seconds();
	UGameplayStatics::OpenLevel(GetGameInstance(), FName(*MapName));
}

bool ULBSaveSubsystem::SaveCheckpoint(FName Id, const FTransform& Transform)
{
	UWorld* World = GetGameInstance()->GetWorld();
	if (!World)
	{
		return false;
	}

	ReachedCheckpoints.Add(Id);

	ULBSaveGame* Save = NewObject<ULBSaveGame>(GetTransientPackage());
	Save->CheckpointId = Id;
	Save->CheckpointTransform = Transform;
	Save->MapName = UWorld::RemovePIEPrefix(World->GetOutermost()->GetName());
	Save->ReachedCheckpoints = ReachedCheckpoints;
	Save->PlayTimeSeconds = GetPlayTime();
	if (const ULBWorldStateSubsystem* WorldState = GetGameInstance()->GetSubsystem<ULBWorldStateSubsystem>())
	{
		Save->WorldState = WorldState->GetState();
	}
	for (const TPair<FName, TWeakObjectPtr<ULBSaveStateComponent>>& Pair : SaveComponents)
	{
		if (const ULBSaveStateComponent* Comp = Pair.Value.Get())
		{
			Save->ActorRecords.Add(Pair.Key, Comp->GetRecord());
		}
	}

	const bool bOk = UGameplayStatics::SaveGameToSlot(Save, SlotName, UserIndex);
	UE_LOG(LogLB, Log, TEXT("SaveCheckpoint '%s' map=%s tags=%d records=%d -> %s"), *Id.ToString(), *Save->MapName,
		Save->WorldState.Num(), Save->ActorRecords.Num(), bOk ? TEXT("ok") : TEXT("FAILED"));
	return bOk;
}

ULBSaveGame* ULBSaveSubsystem::ReadValidSaveFromDisk() const
{
	if (!UGameplayStatics::DoesSaveGameExist(SlotName, UserIndex))
	{
		return nullptr;
	}
	ULBSaveGame* Save = Cast<ULBSaveGame>(UGameplayStatics::LoadGameFromSlot(SlotName, UserIndex));
	if (!Save)
	{
		UE_LOG(LogLB, Warning, TEXT("Save slot '%s' is corrupt or of the wrong class; treating as no save"), *SlotName);
		return nullptr;
	}
	if (!ULBSaveGame::IsVersionCompatible(Save->SaveVersion))
	{
		UE_LOG(LogLB, Warning, TEXT("Save version %d != %d; treating as no save"), Save->SaveVersion, ULBSaveGame::CurrentVersion);
		return nullptr;
	}
	if (Save->MapName.IsEmpty())
	{
		UE_LOG(LogLB, Warning, TEXT("Save has no map name; treating as no save"));
		return nullptr;
	}
	return Save;
}

bool ULBSaveSubsystem::LoadLastCheckpoint()
{
	const ULBSaveGame* Save = ReadValidSaveFromDisk();
	if (!Save)
	{
		return false;
	}

	if (ULBWorldStateSubsystem* WorldState = GetGameInstance()->GetSubsystem<ULBWorldStateSubsystem>())
	{
		WorldState->ReplaceState(Save->WorldState);
	}
	ReachedCheckpoints = Save->ReachedCheckpoints;
	PendingRecords = Save->ActorRecords;
	PendingTransform = Save->CheckpointTransform;
	bPendingRestore = true;
	PlayTimeBase = Save->PlayTimeSeconds;
	PlayTimeSegmentStart = FPlatformTime::Seconds();

	UE_LOG(LogLB, Log, TEXT("LoadLastCheckpoint '%s' -> %s"), *Save->CheckpointId.ToString(), *Save->MapName);
	UGameplayStatics::OpenLevel(GetGameInstance(), FName(*Save->MapName));
	return true;
}

bool ULBSaveSubsystem::HasValidSave() const
{
	return ReadValidSaveFromDisk() != nullptr;
}

void ULBSaveSubsystem::DeleteSave()
{
	if (UGameplayStatics::DoesSaveGameExist(SlotName, UserIndex))
	{
		UGameplayStatics::DeleteGameInSlot(SlotName, UserIndex);
	}
}

bool ULBSaveSubsystem::TryGetPendingRecord(FName SaveId, FLBActorSaveRecord& OutRecord) const
{
	if (!bPendingRestore)
	{
		return false;
	}
	if (const FLBActorSaveRecord* Found = PendingRecords.Find(SaveId))
	{
		OutRecord = *Found;
		return true;
	}
	return false;
}

bool ULBSaveSubsystem::RegisterSaveState(ULBSaveStateComponent* Component)
{
	if (!Component || !IdRegistry.Register(Component->SaveId))
	{
		return false;
	}
	SaveComponents.Add(Component->SaveId, Component);
	return true;
}

void ULBSaveSubsystem::UnregisterSaveState(ULBSaveStateComponent* Component)
{
	if (!Component)
	{
		return;
	}
	const TWeakObjectPtr<ULBSaveStateComponent>* Existing = SaveComponents.Find(Component->SaveId);
	if (Existing && Existing->Get() == Component)
	{
		SaveComponents.Remove(Component->SaveId);
		IdRegistry.Unregister(Component->SaveId);
	}
}
