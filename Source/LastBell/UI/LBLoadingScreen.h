#pragma once

#include "CoreMinimal.h"

class SWidget;
struct FLoadingScreenAttributes;

/**
 * The black loading screen with a small flickering candle and the title (plan P18 section 1.7), shown between the menu and the game by the engine's
 * movie player, so it also works in packaged builds. It is a plain Slate widget with no UObjects (the movie player renders it on its own thread), so it
 * uses the engine font and fixed colours rather than DA_UIStyle. The save subsystem arms it before the travels between the menu and the game; ULBGameInstance clears it after the map has loaded.
 *
 * The editor does not play loading screens; there Arm() builds the attributes and returns false.
 */
namespace LBLoadingScreen
{
	/** The minimum time the screen stays up, seconds. */
	constexpr float MinimumDisplaySeconds = 1.0f;

	/** The Slate widget: black, the title, a candle. */
	LASTBELL_API TSharedRef<SWidget> CreateWidget();

	/** The attributes handed to the movie player (auto-completes when loading completes; not skippable). */
	LASTBELL_API FLoadingScreenAttributes MakeAttributes();

	/** The attributes are valid (a widget is set), auto-complete on, and the minimum display time is MinimumDisplaySeconds: for tests. */
	LASTBELL_API bool ValidateAttributes();

	/**
	 * Called just before a travel between the menu and the game (New Game, Continue, Return to main menu, the ending): builds the attributes and gives
	 * them to the movie player when there is one. Returns true when the movie player took them. Checkpoint reloads after a death do not call it, so they
	 * show no loading screen. The attributes are cleared again after the next map has loaded (OnTravelFinished).
	 */
	LASTBELL_API bool ArmForTravel();

	/** The travel's map has loaded: takes the attributes back from the movie player (a tick later, after it has finished with them). */
	LASTBELL_API void OnTravelFinished();

	/** ArmForTravel ran and the travel has not finished yet. */
	LASTBELL_API bool IsArmed();

	/** How many times ArmForTravel ran / how many times a movie player took the attributes (for tests). */
	LASTBELL_API int32 GetArmCount();
	LASTBELL_API int32 GetHandedToMoviePlayerCount();
}
