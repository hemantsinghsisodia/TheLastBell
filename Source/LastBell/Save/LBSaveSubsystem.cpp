#include "Save/LBSaveSubsystem.h"
#include "Save/LBSaveStateComponent.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"
#include "Systems/LBGameSettings.h"
#include "Misc/PackageName.h"
#include "Misc/Crc.h"
#include "LBLog.h"

namespace
{
	constexpr uint32 GFooterMagic = 0x5653424C; // 'LBSV'
	constexpr int32 GFooterSize = 12;

	bool IsTravelTargetValid(const FString& LongPackageName, const TCHAR* Context)
	{
		if (LongPackageName.IsEmpty() || !FPackageName::IsValidLongPackageName(LongPackageName) || !FPackageName::DoesPackageExist(LongPackageName))
		{
			UE_LOG(LogLB, Error, TEXT("%s: target map '%s' is empty or does not exist; nothing changed"), Context, *LongPackageName);
			return false;
		}
		return true;
	}
}

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
	bTravelPending = false;
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
}

void ULBSaveSubsystem::NewGame(const FString& MapName)
{
	if (bTravelPending)
	{
		UE_LOG(LogLB, Log, TEXT("NewGame ignored: travel already pending"));
		return;
	}
	if (!IsTravelTargetValid(MapName, TEXT("NewGame")))
	{
		return;
	}
	UE_LOG(LogLB, Log, TEXT("New game: %s"), *MapName);
	DeleteSave();
	if (ULBWorldStateSubsystem* WorldState = GetGameInstance()->GetSubsystem<ULBWorldStateSubsystem>())
	{
		WorldState->ResetState();
	}
	ReachedCheckpoints.Reset();
	KnownRecords.Reset();
	bPendingRestore = false;
	PlayTimeBase = 0.f;
	PlayTimeSegmentStart = FPlatformTime::Seconds();
	bTravelPending = true;
	UGameplayStatics::OpenLevel(GetGameInstance(), FName(*MapName));
}

bool ULBSaveSubsystem::SaveCheckpoint(FName Id, const FTransform& Transform)
{
	UWorld* World = GetGameInstance()->GetWorld();
	if (!World)
	{
		return false;
	}

	ULBSaveGame* Save = NewObject<ULBSaveGame>(GetTransientPackage());
	Save->CheckpointId = Id;
	Save->CheckpointTransform = FTransform(Transform.GetRotation(), Transform.GetLocation()); // scale stripped
	Save->MapName = UWorld::RemovePIEPrefix(World->GetOutermost()->GetName());
	Save->ReachedCheckpoints = ReachedCheckpoints;
	Save->ReachedCheckpoints.Add(Id);
	Save->PlayTimeSeconds = GetPlayTime();
	if (const ULBWorldStateSubsystem* WorldState = GetGameInstance()->GetSubsystem<ULBWorldStateSubsystem>())
	{
		Save->WorldState = WorldState->GetStateRef();
	}
	TMap<FName, FLBActorSaveRecord> Live;
	for (const TPair<FName, TWeakObjectPtr<ULBSaveStateComponent>>& Pair : SaveComponents)
	{
		if (const ULBSaveStateComponent* Comp = Pair.Value.Get())
		{
			Live.Add(Pair.Key, Comp->GetRecord());
		}
	}
	Save->ActorRecords = MergeRecords(KnownRecords, Live);

	TArray<uint8> FileBytes;
	const bool bOk = EncodeSave(Save, FileBytes) && UGameplayStatics::SaveDataToSlot(FileBytes, SlotName, UserIndex);
	if (bOk)
	{
		ReachedCheckpoints.Add(Id);
		KnownRecords = Save->ActorRecords;
	}
	UE_LOG(LogLB, Log, TEXT("SaveCheckpoint '%s' map=%s tags=%d records=%d -> %s"), *Id.ToString(), *Save->MapName,
		Save->WorldState.Num(), Save->ActorRecords.Num(), bOk ? TEXT("ok") : TEXT("FAILED"));
	return bOk;
}

bool ULBSaveSubsystem::EncodeSave(ULBSaveGame* Save, TArray<uint8>& OutFileBytes)
{
	OutFileBytes.Reset();
	USaveGame* AsSave = Save;
	if (!AsSave || !UGameplayStatics::SaveGameToMemory(AsSave, OutFileBytes))
	{
		OutFileBytes.Reset();
		return false;
	}
	const uint32 Magic = GFooterMagic;
	const uint32 Length = static_cast<uint32>(OutFileBytes.Num());
	const uint32 Crc = FCrc::MemCrc32(OutFileBytes.GetData(), OutFileBytes.Num());
	OutFileBytes.AddUninitialized(GFooterSize);
	uint8* Footer = OutFileBytes.GetData() + Length;
	FMemory::Memcpy(Footer, &Magic, 4);
	FMemory::Memcpy(Footer + 4, &Length, 4);
	FMemory::Memcpy(Footer + 8, &Crc, 4);
	return true;
}

ULBSaveGame* ULBSaveSubsystem::DecodeSave(const TArray<uint8>& FileBytes, FString& OutReason)
{
	if (FileBytes.Num() <= GFooterSize)
	{
		OutReason = FString::Printf(TEXT("file too short (%d bytes)"), FileBytes.Num());
		return nullptr;
	}
	const int32 PayloadLength = FileBytes.Num() - GFooterSize;
	const uint8* Footer = FileBytes.GetData() + PayloadLength;
	uint32 Magic = 0, Length = 0, Crc = 0;
	FMemory::Memcpy(&Magic, Footer, 4);
	FMemory::Memcpy(&Length, Footer + 4, 4);
	FMemory::Memcpy(&Crc, Footer + 8, 4);
	if (Magic != GFooterMagic)
	{
		OutReason = TEXT("no integrity footer (truncated, damaged or not a save file)");
		return nullptr;
	}
	if (Length != static_cast<uint32>(PayloadLength))
	{
		OutReason = FString::Printf(TEXT("length mismatch (footer says %u bytes, file holds %d)"), Length, PayloadLength);
		return nullptr;
	}
	if (Crc != FCrc::MemCrc32(FileBytes.GetData(), PayloadLength))
	{
		OutReason = TEXT("checksum mismatch");
		return nullptr;
	}
	TArray<uint8> Payload;
	Payload.Append(FileBytes.GetData(), PayloadLength);
	ULBSaveGame* Save = Cast<ULBSaveGame>(UGameplayStatics::LoadGameFromMemory(Payload));
	if (!Save)
	{
		OutReason = TEXT("not a LastBell save");
	}
	return Save;
}

ULBSaveGame* ULBSaveSubsystem::ReadValidSaveFromDisk() const
{
	if (!UGameplayStatics::DoesSaveGameExist(SlotName, UserIndex))
	{
		return nullptr;
	}
	TArray<uint8> FileBytes;
	FString Reason;
	ULBSaveGame* Save = UGameplayStatics::LoadDataFromSlot(FileBytes, SlotName, UserIndex) ? DecodeSave(FileBytes, Reason) : nullptr;
	if (!Save)
	{
		UE_LOG(LogLB, Warning, TEXT("Save slot '%s' is corrupt (%s); treating as no save"), *SlotName, Reason.IsEmpty() ? TEXT("unreadable") : *Reason);
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
	if (bTravelPending)
	{
		UE_LOG(LogLB, Log, TEXT("LoadLastCheckpoint ignored: travel already pending"));
		return false;
	}
	const ULBSaveGame* Save = ReadValidSaveFromDisk();
	if (!Save)
	{
		return false;
	}
	if (!IsTravelTargetValid(Save->MapName, TEXT("LoadLastCheckpoint")))
	{
		return false;
	}

	if (ULBWorldStateSubsystem* WorldState = GetGameInstance()->GetSubsystem<ULBWorldStateSubsystem>())
	{
		WorldState->ReplaceState(Save->WorldState);
	}
	ReachedCheckpoints = Save->ReachedCheckpoints;
	KnownRecords = Save->ActorRecords;
	PendingTransform = Save->CheckpointTransform;
	bPendingRestore = true;
	bTravelPending = true;
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

TMap<FName, FLBActorSaveRecord> ULBSaveSubsystem::MergeRecords(const TMap<FName, FLBActorSaveRecord>& Known, const TMap<FName, FLBActorSaveRecord>& Live)
{
	TMap<FName, FLBActorSaveRecord> Result = Known;
	for (const TPair<FName, FLBActorSaveRecord>& Pair : Live)
	{
		Result.Add(Pair.Key, Pair.Value);
	}
	return Result;
}

bool ULBSaveSubsystem::TryGetRecord(FName SaveId, FLBActorSaveRecord& OutRecord) const
{
	if (const FLBActorSaveRecord* Found = KnownRecords.Find(SaveId))
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

void ULBSaveSubsystem::StartNewGame()
{
	if (bTravelPending)
	{
		UE_LOG(LogLB, Log, TEXT("StartNewGame ignored: travel already pending"));
		return;
	}
	const ULBGameSettings* Settings = ULBGameSettings::Get();
	if (Settings->NewGameMap.IsNull())
	{
		UE_LOG(LogLB, Error, TEXT("StartNewGame: NewGameMap is not set in Project Settings > The Last Bell"));
		return;
	}
	NewGame(Settings->NewGameMap.GetLongPackageName());
}

bool ULBSaveSubsystem::ContinueGame()
{
	if (bTravelPending)
	{
		UE_LOG(LogLB, Log, TEXT("ContinueGame ignored: travel already pending"));
		return false;
	}
	return LoadLastCheckpoint();
}

bool ULBSaveSubsystem::OpenMainMenuMap()
{
	const ULBGameSettings* Settings = ULBGameSettings::Get();
	if (Settings->MainMenuMap.IsNull())
	{
		UE_LOG(LogLB, Error, TEXT("MainMenuMap is not set in Project Settings > The Last Bell"));
		return false;
	}
	if (bTravelPending)
	{
		UE_LOG(LogLB, Log, TEXT("OpenMainMenuMap ignored: travel already pending"));
		return false;
	}
	if (!IsTravelTargetValid(Settings->MainMenuMap.GetLongPackageName(), TEXT("OpenMainMenuMap")))
	{
		return false;
	}
	bTravelPending = true;
	UGameplayStatics::OpenLevel(GetGameInstance(), FName(*Settings->MainMenuMap.GetLongPackageName()));
	return true;
}

void ULBSaveSubsystem::CompleteGame()
{
	if (bTravelPending)
	{
		UE_LOG(LogLB, Log, TEXT("CompleteGame ignored: travel already pending"));
		return;
	}
	if (ULBGameSettings::Get()->MainMenuMap.IsNull())
	{
		UE_LOG(LogLB, Error, TEXT("CompleteGame: MainMenuMap is not set; nothing done"));
		return;
	}
	if (!IsTravelTargetValid(ULBGameSettings::Get()->MainMenuMap.GetLongPackageName(), TEXT("CompleteGame")))
	{
		return;
	}
	UE_LOG(LogLB, Log, TEXT("Game complete: deleting save and returning to main menu"));
	DeleteSave();
	if (ULBWorldStateSubsystem* WorldState = GetGameInstance()->GetSubsystem<ULBWorldStateSubsystem>())
	{
		WorldState->ResetState();
	}
	ReachedCheckpoints.Reset();
	KnownRecords.Reset();
	bPendingRestore = false;
	PlayTimeBase = 0.f;
	PlayTimeSegmentStart = FPlatformTime::Seconds();
	OpenMainMenuMap();
}

void ULBSaveSubsystem::ReturnToMainMenu()
{
	if (bTravelPending)
	{
		UE_LOG(LogLB, Log, TEXT("ReturnToMainMenu ignored: travel already pending"));
		return;
	}
	UE_LOG(LogLB, Log, TEXT("Returning to main menu"));
	OpenMainMenuMap();
}
