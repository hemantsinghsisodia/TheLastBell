#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "Audio/LBAudioTypes.h"
#include "LBUserSettings.generated.h"

/**
 * Per-user settings (sensitivity, invert Y, head bob).
 * A config UDeveloperSettings stored in GameUserSettings.ini under Saved/: no change to DefaultEngine.ini
 * (GameUserSettingsClassName) is needed, it is per user, and the C++ and Blueprint API is two lines.
 */
UCLASS(Config = GameUserSettings, meta = (DisplayName = "The Last Bell (User)"))
class LASTBELL_API ULBUserSettings : public UDeveloperSettings
{
	GENERATED_BODY()

public:
	static const ULBUserSettings* Get() { return GetDefault<ULBUserSettings>(); }

	UFUNCTION(BlueprintPure, Category = "LastBell|Settings")
	static ULBUserSettings* GetUserSettings() { return GetMutableDefault<ULBUserSettings>(); }

	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Input", meta = (ClampMin = "0.05", ClampMax = "10"))
	float MouseSensitivity = 1.0f;

	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Input")
	bool bInvertY = false;

	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Camera")
	bool bHeadBob = true;

	// ---- Audio (P16): linear volumes 0..1 by group. Master is the parent of the other five SoundClasses. ----

	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Audio", meta = (ClampMin = "0", ClampMax = "1"))
	float MasterVolume = 1.0f;

	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Audio", meta = (ClampMin = "0", ClampMax = "1"))
	float SFXVolume = 1.0f;

	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Audio", meta = (ClampMin = "0", ClampMax = "1"))
	float AmbienceVolume = 1.0f;

	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Audio", meta = (ClampMin = "0", ClampMax = "1"))
	float MusicVolume = 1.0f;

	/** The Warden's voice and breath. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Audio", meta = (ClampMin = "0", ClampMax = "1"))
	float VoiceVolume = 1.0f;

	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Audio", meta = (ClampMin = "0", ClampMax = "1"))
	float UIVolume = 1.0f;

	/** The volume of a group (clamped 0..1). */
	UFUNCTION(BlueprintPure, Category = "LastBell|Settings")
	float GetVolume(ELBAudioVolumeGroup Group) const;

	/** Sets a group's volume (clamped 0..1), persists it to GameUserSettings.ini and tells the audio subsystem. This is the Phase 18 settings menu's entry point. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Settings")
	void SetVolume(ELBAudioVolumeGroup Group, float NewValue);

	/** Sets a group's volume without saving it (the lb.Audio.Volume console command, tests) and tells the audio subsystem. */
	void SetVolumeTransient(ELBAudioVolumeGroup Group, float NewValue);

	/** Fires after any audio volume changed. ULBAudioSubsystem listens to it to push the SoundMix. */
	static FSimpleMulticastDelegate& OnAudioVolumesChanged();

	/** Setters clamp, then persist to GameUserSettings.ini. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Settings")
	void SetMouseSensitivity(float NewValue);

	UFUNCTION(BlueprintCallable, Category = "LastBell|Settings")
	void SetInvertY(bool bNewValue);

	UFUNCTION(BlueprintCallable, Category = "LastBell|Settings")
	void SetHeadBob(bool bNewValue);

	static constexpr float MinSensitivity = 0.05f;
	static constexpr float MaxSensitivity = 10.f;
};
