#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
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
