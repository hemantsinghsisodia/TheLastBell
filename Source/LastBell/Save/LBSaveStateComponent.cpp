#include "Save/LBSaveStateComponent.h"
#include "Save/LBSaveSubsystem.h"
#include "LBLog.h"

void ULBSaveStateComponent::BeginPlay()
{
	Super::BeginPlay();

	ULBSaveSubsystem* Subsystem = ULBSaveSubsystem::Get(this);
	if (!Subsystem)
	{
		return;
	}

	bRegistered = Subsystem->RegisterSaveState(this);
	if (!bRegistered)
	{
		UE_LOG(LogLB, Error, TEXT("Save state component on '%s' has a None or duplicate SaveId '%s'"),
			*GetNameSafe(GetOwner()), *SaveId.ToString());
		return;
	}

	FLBActorSaveRecord Pending;
	if (Subsystem->TryGetRecord(SaveId, Pending))
	{
		CurrentRecord = Pending;
		OnRestore.Broadcast(CurrentRecord);
	}
}

void ULBSaveStateComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (bRegistered)
	{
		if (ULBSaveSubsystem* Subsystem = ULBSaveSubsystem::Get(this))
		{
			Subsystem->UnregisterSaveState(this);
		}
		bRegistered = false;
	}
	Super::EndPlay(EndPlayReason);
}
