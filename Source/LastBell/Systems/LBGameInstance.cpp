#include "Systems/LBGameInstance.h"
#include "Systems/LBUserSettings.h"
#include "UI/LBLoadingScreen.h"
#include "UObject/UObjectGlobals.h"
#include "LBLog.h"

void ULBGameInstance::Init()
{
	Super::Init();

	// The saved gamma, before anything is drawn and before the first-launch brightness screen is decided.
	if (const ULBUserSettings* Settings = ULBUserSettings::Get())
	{
		Settings->ApplyGamma();
	}

	// The loading screen is armed by the save subsystem just before a menu <-> game travel (before the engine's own pre-load hook runs, which is
	// why it is not armed from a PreLoadMap handler here); this takes it back once the map has loaded.
	PostLoadMapHandle = FCoreUObjectDelegates::PostLoadMapWithWorld.AddUObject(this, &ULBGameInstance::HandlePostLoadMap);
}

void ULBGameInstance::Shutdown()
{
	FCoreUObjectDelegates::PostLoadMapWithWorld.Remove(PostLoadMapHandle);
	PostLoadMapHandle.Reset();
	Super::Shutdown();
}

void ULBGameInstance::HandlePostLoadMap(UWorld* LoadedWorld)
{
	LBLoadingScreen::OnTravelFinished();
}
