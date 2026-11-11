#include "Systems/LBGameInstance.h"
#include "Engine/Engine.h"
#include "GameFramework/GameUserSettings.h"
#include "Systems/LBUserSettings.h"
#include "UI/LBLoadingScreen.h"
#include "UI/LBUILogic.h"
#include "UObject/UObjectGlobals.h"
#include "LBLog.h"

void ULBGameInstance::Init()
{
	Super::Init();

	// A request from the previous session ("Show brightness screen at next launch") acts now, before the main menu decides whether to show it.
	if (ULBUserSettings* Settings = ULBUserSettings::GetUserSettings())
	{
		Settings->ConsumeBrightnessRequest();
	}

	// The saved gamma, before anything is drawn and before the first-launch brightness screen is decided. The editor keeps its own gamma: it is put
	// back when the play session ends.
	SavedEngineGamma = GEngine ? GEngine->DisplayGamma : 2.2f;
	if (const ULBUserSettings* Settings = ULBUserSettings::Get())
	{
		Settings->ApplyGamma();
	}

	RevertUnconfirmedDisplayMode();

	// The loading screen is armed by the save subsystem just before a menu <-> game travel (before the engine's own pre-load hook runs, which is
	// why it is not armed from a PreLoadMap handler here); this takes it back once the map has loaded.
	PostLoadMapHandle = FCoreUObjectDelegates::PostLoadMapWithWorld.AddUObject(this, &ULBGameInstance::HandlePostLoadMap);
}

void ULBGameInstance::Shutdown()
{
	FCoreUObjectDelegates::PostLoadMapWithWorld.Remove(PostLoadMapHandle);
	PostLoadMapHandle.Reset();
	// In the editor the play session must not leave the game's gamma (the brightness setting) on the editor viewports.
	if (GIsEditor && GEngine)
	{
		GEngine->DisplayGamma = SavedEngineGamma;
	}
	Super::Shutdown();
}

void ULBGameInstance::RevertUnconfirmedDisplayMode()
{
	// The keep dialog saves the new mode before the player answers it, so a quit or a crash inside its 15 s would leave an unconfirmed mode on disk:
	// at startup, a mode or resolution that differs from the last confirmed one goes back to the confirmed one. Not in the editor (it has its own window).
	if (GIsEditor || !GEngine)
	{
		return;
	}
	UGameUserSettings* GameSettings = GEngine->GetGameUserSettings();
	if (!GameSettings)
	{
		return;
	}
	if (LBUILogic::DisplayDiffersFromConfirmed(static_cast<int32>(GameSettings->GetFullscreenMode()), GameSettings->GetScreenResolution(),
		static_cast<int32>(GameSettings->GetLastConfirmedFullscreenMode()), GameSettings->GetLastConfirmedScreenResolution()))
	{
		UE_LOG(LogLB, Warning, TEXT("The display mode was not confirmed last time: going back to the confirmed one"));
		GameSettings->RevertVideoMode();
		GameSettings->ApplyResolutionSettings(false);
		GameSettings->SaveSettings();
	}
}

void ULBGameInstance::HandlePostLoadMap(UWorld* LoadedWorld)
{
	LBLoadingScreen::OnTravelFinished();
}
