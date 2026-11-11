#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "Engine/World.h"
#include "LBGameSettings.generated.h"

class ULBAudioSettings;
class ULBCinematicSettings;
class ULBStormSettings;
class ULBUIStyle;

/** Project Settings > Game > The Last Bell. */
UCLASS(Config = Game, defaultconfig, meta = (DisplayName = "The Last Bell"))
class LASTBELL_API ULBGameSettings : public UDeveloperSettings
{
	GENERATED_BODY()

public:
	ULBGameSettings();

	static const ULBGameSettings* Get() { return GetDefault<ULBGameSettings>(); }

	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Maps")
	TSoftObjectPtr<UWorld> MainMenuMap;

	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Maps")
	TSoftObjectPtr<UWorld> NewGameMap;

	/** DA_StormSettings: every number of the storm (P14). Unset: the storm subsystem stays inactive. */
	UPROPERTY(Config, EditAnywhere, Category = "Storm")
	TSoftObjectPtr<ULBStormSettings> StormSettings;

	/** DA_Audio: every sound and number of the audio director (P16). Unset: the audio subsystem stays silent. */
	UPROPERTY(Config, EditAnywhere, Category = "Audio")
	TSoftObjectPtr<ULBAudioSettings> AudioSettings;

	/** DA_Cinematics: the intro, the finale, the cards and the credits (P17). Unset: the cinematic subsystem does nothing. */
	UPROPERTY(Config, EditAnywhere, Category = "Cinematics")
	TSoftObjectPtr<ULBCinematicSettings> CinematicSettings;

	/** DA_UIStyle: fonts, colours, key icons, UI sounds and the menu video of the C++ UI (P18). Unset: the UI uses its built-in defaults and the engine font. */
	UPROPERTY(Config, EditAnywhere, Category = "UI")
	TSoftObjectPtr<ULBUIStyle> UIStyle;
};
