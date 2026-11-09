#include "Systems/LBUserSettings.h"

void ULBUserSettings::SetMouseSensitivity(float NewValue)
{
	MouseSensitivity = FMath::Clamp(NewValue, MinSensitivity, MaxSensitivity);
	SaveConfig();
}

void ULBUserSettings::SetInvertY(bool bNewValue)
{
	bInvertY = bNewValue;
	SaveConfig();
}

void ULBUserSettings::SetHeadBob(bool bNewValue)
{
	bHeadBob = bNewValue;
	SaveConfig();
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
