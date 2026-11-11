#pragma once

#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

#include "CoreMinimal.h"
#include "Engine/Engine.h"
#include "GameFramework/GameUserSettings.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Systems/LBUserSettings.h"
#include "UI/LBGraphicsSettings.h"

/**
 * Test helper (P18): a UI test must leave the developer's own settings as it found them. On construction it snapshots every field of ULBUserSettings, the
 * engine's graphics and display settings (FLBGraphicsSettings) and the Enhanced Input key bindings file (Saved/SaveGames/EnhancedInputUserSettings.sav);
 * when it goes out of scope it puts them back (in memory and on disk) and GEngine->DisplayGamma too. So a suite run keeps the owner's real key bindings,
 * brightness flag and graphics choices.
 */
class FLBUserSettingsGuard
{
public:
	FLBUserSettingsGuard()
	{
		if (const ULBUserSettings* Settings = ULBUserSettings::Get())
		{
			Sensitivity = Settings->MouseSensitivity;
			bInvert = Settings->bInvertY;
			bBob = Settings->bHeadBob;
			Volumes[0] = Settings->MasterVolume;
			Volumes[1] = Settings->SFXVolume;
			Volumes[2] = Settings->AmbienceVolume;
			Volumes[3] = Settings->MusicVolume;
			Volumes[4] = Settings->VoiceVolume;
			Volumes[5] = Settings->UIVolume;
			Gamma = Settings->Gamma;
			FOV = Settings->FieldOfView;
			bBlur = Settings->bMotionBlur;
			bGrain = Settings->bFilmGrain;
			bHighContrast = Settings->bHighContrastPrompts;
			bCalibrated = Settings->bBrightnessCalibrated;
			bFPS = Settings->bShowFPS;
			ScalePercent = Settings->ResolutionScalePercent;
			bBrightnessNextLaunch = Settings->bShowBrightnessNextLaunch;
		}
		EngineGamma = GEngine ? GEngine->DisplayGamma : 2.2f;
		GraphicsSnapshot = FLBGraphicsSettings::Capture();
		bHadBindings = FFileHelper::LoadFileToArray(BindingBytes, *BindingsPath());
	}

	~FLBUserSettingsGuard()
	{
		if (ULBUserSettings* Settings = ULBUserSettings::GetUserSettings())
		{
			Settings->MouseSensitivity = Sensitivity;
			Settings->bInvertY = bInvert;
			Settings->bHeadBob = bBob;
			Settings->MasterVolume = Volumes[0];
			Settings->SFXVolume = Volumes[1];
			Settings->AmbienceVolume = Volumes[2];
			Settings->MusicVolume = Volumes[3];
			Settings->VoiceVolume = Volumes[4];
			Settings->UIVolume = Volumes[5];
			Settings->Gamma = Gamma;
			Settings->FieldOfView = FOV;
			Settings->bMotionBlur = bBlur;
			Settings->bFilmGrain = bGrain;
			Settings->bHighContrastPrompts = bHighContrast;
			Settings->bBrightnessCalibrated = bCalibrated;
			Settings->bShowFPS = bFPS;
			Settings->ResolutionScalePercent = ScalePercent;
			Settings->bShowBrightnessNextLaunch = bBrightnessNextLaunch;
			Settings->SaveConfig();
			ULBUserSettings::OnUserSettingsChanged().Broadcast();
		}
		if (GEngine)
		{
			GEngine->DisplayGamma = EngineGamma;
		}
		// The graphics and display values go back unapplied (nothing was applied by the guard) and are saved with the player's own numbers.
		FLBGraphicsSettings::Restore(GraphicsSnapshot);
		if (UGameUserSettings* GameSettings = FLBGraphicsSettings::Get())
		{
			GameSettings->SaveSettings();
		}
		// The key bindings: the file the Controls tab saves. Put back byte for byte, or removed if there was none.
		if (bHadBindings)
		{
			FFileHelper::SaveArrayToFile(BindingBytes, *BindingsPath());
		}
		else
		{
			IFileManager::Get().Delete(*BindingsPath(), /*RequireExists*/ false, /*EvenReadOnly*/ true, /*Quiet*/ true);
		}
	}

	FLBUserSettingsGuard(const FLBUserSettingsGuard&) = delete;
	FLBUserSettingsGuard& operator=(const FLBUserSettingsGuard&) = delete;

	/** Where the Enhanced Input user settings are saved (the default InputSettingsSaveSlotName). */
	static FString BindingsPath() { return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("SaveGames"), TEXT("EnhancedInputUserSettings.sav")); }

private:
	float Sensitivity = 1.f;
	bool bInvert = false;
	bool bBob = true;
	float Volumes[6] = { 1.f, 1.f, 1.f, 1.f, 1.f, 1.f };
	float Gamma = 2.2f;
	float FOV = 90.f;
	bool bBlur = false;
	bool bGrain = true;
	bool bHighContrast = false;
	bool bCalibrated = false;
	bool bFPS = false;
	float ScalePercent = -1.f;
	bool bBrightnessNextLaunch = false;
	float EngineGamma = 2.2f;
	FLBGraphicsSnapshot GraphicsSnapshot;
	TArray<uint8> BindingBytes;
	bool bHadBindings = false;
};

#endif
