#include "Systems/LBUserSettings.h"
#include "Engine/Engine.h"

void ULBUserSettings::SetMouseSensitivityTransient(float NewValue)
{
	MouseSensitivity = FMath::Clamp(NewValue, MinSensitivity, MaxSensitivity);
	OnUserSettingsChanged().Broadcast();
}

void ULBUserSettings::SetMouseSensitivity(float NewValue)
{
	SetMouseSensitivityTransient(NewValue);
	SaveConfig();
}

void ULBUserSettings::SetInvertY(bool bNewValue)
{
	bInvertY = bNewValue;
	SaveConfig();
	OnUserSettingsChanged().Broadcast();
}

void ULBUserSettings::SetHeadBob(bool bNewValue)
{
	bHeadBob = bNewValue;
	SaveConfig();
	OnUserSettingsChanged().Broadcast();
}

void ULBUserSettings::ApplyGamma() const
{
	if (GEngine)
	{
		GEngine->DisplayGamma = LBUILogic::ClampGamma(Gamma);
	}
}

void ULBUserSettings::SetGammaTransient(float NewValue)
{
	Gamma = LBUILogic::ClampGamma(NewValue);
	ApplyGamma();
	OnUserSettingsChanged().Broadcast();
}

void ULBUserSettings::SetGamma(float NewValue)
{
	SetGammaTransient(NewValue);
	SaveConfig();
}

void ULBUserSettings::SetFieldOfViewTransient(float NewValue)
{
	FieldOfView = LBUILogic::ClampFOV(NewValue);
	OnUserSettingsChanged().Broadcast();
}

void ULBUserSettings::SetFieldOfView(float NewValue)
{
	SetFieldOfViewTransient(NewValue);
	SaveConfig();
}

void ULBUserSettings::SetMotionBlur(bool bNewValue)
{
	bMotionBlur = bNewValue;
	SaveConfig();
	OnUserSettingsChanged().Broadcast();
}

void ULBUserSettings::SetFilmGrain(bool bNewValue)
{
	bFilmGrain = bNewValue;
	SaveConfig();
	OnUserSettingsChanged().Broadcast();
}

void ULBUserSettings::SetHighContrastPrompts(bool bNewValue)
{
	bHighContrastPrompts = bNewValue;
	SaveConfig();
	OnUserSettingsChanged().Broadcast();
}

void ULBUserSettings::SetBrightnessCalibrated(bool bNewValue)
{
	bBrightnessCalibrated = bNewValue;
	SaveConfig();
	OnUserSettingsChanged().Broadcast();
}

void ULBUserSettings::SetShowFPS(bool bNewValue)
{
	bShowFPS = bNewValue;
	SaveConfig();
	OnUserSettingsChanged().Broadcast();
}

void ULBUserSettings::SetResolutionScalePercent(float NewPercent)
{
	ResolutionScalePercent = LBUILogic::ClampResolutionScale(NewPercent);
	SaveConfig();
	OnUserSettingsChanged().Broadcast();
}

void ULBUserSettings::SetShowBrightnessNextLaunch(bool bNewValue)
{
	bShowBrightnessNextLaunch = bNewValue;
	SaveConfig();
	OnUserSettingsChanged().Broadcast();
}

bool ULBUserSettings::ConsumeBrightnessRequest()
{
	if (!bShowBrightnessNextLaunch)
	{
		return false;
	}
	bShowBrightnessNextLaunch = false;
	bBrightnessCalibrated = false;
	SaveConfig();
	OnUserSettingsChanged().Broadcast();
	return true;
}

void ULBUserSettings::ResetControlsToDefaults()
{
	MouseSensitivity = 1.0f;
	bInvertY = false;
	bHeadBob = true;
	SaveConfig();
	OnUserSettingsChanged().Broadcast();
}

void ULBUserSettings::Persist()
{
	SaveConfig();
}

FSimpleMulticastDelegate& ULBUserSettings::OnUserSettingsChanged()
{
	static FSimpleMulticastDelegate Delegate;
	return Delegate;
}

namespace
{
	float* VolumeField(ULBUserSettings& Settings, ELBAudioVolumeGroup Group)
	{
		switch (Group)
		{
		case ELBAudioVolumeGroup::Master: return &Settings.MasterVolume;
		case ELBAudioVolumeGroup::SFX: return &Settings.SFXVolume;
		case ELBAudioVolumeGroup::Ambience: return &Settings.AmbienceVolume;
		case ELBAudioVolumeGroup::Music: return &Settings.MusicVolume;
		case ELBAudioVolumeGroup::Voice: return &Settings.VoiceVolume;
		case ELBAudioVolumeGroup::UI: return &Settings.UIVolume;
		}
		return nullptr;
	}
}

float ULBUserSettings::GetVolume(ELBAudioVolumeGroup Group) const
{
	const float* Field = VolumeField(*const_cast<ULBUserSettings*>(this), Group);
	return Field ? FMath::Clamp(*Field, 0.f, 1.f) : 1.f;
}

void ULBUserSettings::SetVolumeTransient(ELBAudioVolumeGroup Group, float NewValue)
{
	if (float* Field = VolumeField(*this, Group))
	{
		*Field = FMath::Clamp(NewValue, 0.f, 1.f);
		OnAudioVolumesChanged().Broadcast();
	}
}

void ULBUserSettings::SetVolume(ELBAudioVolumeGroup Group, float NewValue)
{
	SetVolumeTransient(Group, NewValue);
	SaveConfig();
}

FSimpleMulticastDelegate& ULBUserSettings::OnAudioVolumesChanged()
{
	static FSimpleMulticastDelegate Delegate;
	return Delegate;
}
