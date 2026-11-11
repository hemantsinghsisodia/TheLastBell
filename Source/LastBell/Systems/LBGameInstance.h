#pragma once

#include "CoreMinimal.h"
#include "Engine/GameInstance.h"
#include "LBGameInstance.generated.h"

/**
 * The game instance (plan P18 section 2): applies the saved gamma at startup, before the brightness screen is decided, and takes the black loading
 * screen (UI/LBLoadingScreen) back from the engine's movie player after a map has loaded (the save subsystem arms it before the menu <-> game travels).
 * Set as GameInstanceClass in DefaultEngine.ini.
 */
UCLASS()
class LASTBELL_API ULBGameInstance : public UGameInstance
{
	GENERATED_BODY()

public:
	virtual void Init() override;
	virtual void Shutdown() override;

private:
	void HandlePostLoadMap(UWorld* LoadedWorld);

	FDelegateHandle PostLoadMapHandle;
};
