#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "Engine/World.h"
#include "LBGameSettings.generated.h"

class ULBStormSettings;

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
};
