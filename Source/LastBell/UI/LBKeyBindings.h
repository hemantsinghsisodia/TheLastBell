#pragma once

#include "CoreMinimal.h"
#include "InputCoreTypes.h"
#include "UI/LBUITypes.h"

class UEnhancedInputUserSettings;
class UInputAction;
class ULocalPlayer;

/**
 * Key rebinding through Enhanced Input user settings (plan P18 section 2, R-92). Every gameplay action has a player-mappable name in
 * IMC_LB_Gameplay (LBUILogic::MappingNameFor; P18-2 sets them); the Controls tab reads and writes the first key slot of each. Move is four
 * separate keys. Conflicts are checked here against the other rebindable actions, because the engine accepts duplicates.
 *
 * When user settings are off or the mapping names are missing (before P18-2), reads fall back to the default keys, Rebind fails with a
 * message and one log line, and nothing crashes.
 */
namespace LBKeyBindings
{
	struct FRebindResult
	{
		bool bOk = false;
		/** Why it failed, or empty. */
		FText Message;
		/** The action that already uses the key, or Count. */
		ELBBindAction Conflict = ELBBindAction::Count;
	};

	/** The player's Enhanced Input user settings, or null (user settings disabled in the project, no local player). */
	LASTBELL_API UEnhancedInputUserSettings* GetUserSettings(const ULocalPlayer* LocalPlayer);

	/** True when the action's player-mappable name is registered, so Rebind can work. */
	LASTBELL_API bool IsRebindable(const ULocalPlayer* LocalPlayer, ELBBindAction Action);

	/** The key the action has now (the first slot), or its default when it is not registered. */
	LASTBELL_API FKey GetKey(const ULocalPlayer* LocalPlayer, ELBBindAction Action);

	/** The key now mapped to an Input Action, from the player's live mappings (any rebinding included), or Invalid. */
	LASTBELL_API FKey GetKeyForInputAction(const ULocalPlayer* LocalPlayer, const UInputAction* Action);

	LASTBELL_API TMap<ELBBindAction, FKey> GetAll(const ULocalPlayer* LocalPlayer);

	/** Checks, maps, applies and saves. Refuses invalid keys and conflicts with a message. */
	LASTBELL_API FRebindResult Rebind(ULocalPlayer* LocalPlayer, ELBBindAction Action, const FKey& NewKey);

	/** Resets every gameplay mapping to the IMC defaults, applies and saves. */
	LASTBELL_API void ResetAll(ULocalPlayer* LocalPlayer);

	/** Fires after a rebind or a reset (the key-icon widgets refresh on it). */
	LASTBELL_API FSimpleMulticastDelegate& OnBindingsChanged();
}
