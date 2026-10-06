#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "Engine/World.h"
#include "LBGameSettings.generated.h"

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
};
