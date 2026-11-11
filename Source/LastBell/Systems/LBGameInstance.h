#pragma once

#include "CoreMinimal.h"
#include "Engine/GameInstance.h"
#include "LBGameInstance.generated.h"

/**
 * The game instance (plan P18 section 2): applies the saved gamma at startup (the editor gets its own back when play ends), reverts an unconfirmed display mode, consumes the "show brightness at next launch" request, before the brightness screen is decided, and takes the black loading
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
	void RevertUnconfirmedDisplayMode();

	/** The engine's DisplayGamma before this game instance changed it: put back in the editor when the play session ends. */
	float SavedEngineGamma = 2.2f;

	FDelegateHandle PostLoadMapHandle;
};
