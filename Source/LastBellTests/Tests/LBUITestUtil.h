#pragma once

#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

#include "CoreMinimal.h"
#include "Engine/Engine.h"
#include "Systems/LBUserSettings.h"

/**
 * Test helper (P18): snapshots every field of ULBUserSettings and puts it back (in memory and in GameUserSettings.ini) when it goes out of scope, so a
 * test that changes the player's settings leaves them as it found them. Also puts GEngine->DisplayGamma back.
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
		}
		EngineGamma = GEngine ? GEngine->DisplayGamma : 2.2f;
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
			Settings->SaveConfig();
			ULBUserSettings::OnUserSettingsChanged().Broadcast();
		}
		if (GEngine)
		{
			GEngine->DisplayGamma = EngineGamma;
		}
	}

	FLBUserSettingsGuard(const FLBUserSettingsGuard&) = delete;
	FLBUserSettingsGuard& operator=(const FLBUserSettingsGuard&) = delete;

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
	float EngineGamma = 2.2f;
};

#endif
