#pragma once

#include "CoreMinimal.h"
#include "Cinematics/LBCinematicTypes.h"

class UCanvasPanelSlot;
class ULBUIStyle;
class UUserWidget;
class UVerticalBox;
class UWidgetTree;

/**
 * The credits roll layout shared by the cinematic overlay (the ending) and the Credits menu screen (plan P18 section 2): one vertical box of styled
 * lines in a canvas slot, scrolled from below the screen to above it over a duration. The widget that owns the box owns this struct; it only
 * borrows the box and the slot for the calls.
 */
struct LASTBELL_API FLBCreditsRoll
{
	static constexpr float CreditsWidth = 1200.f;
	static constexpr float GapHeight = 40.f;
	static constexpr float FallbackViewportHeight = 1080.f;

	int32 LineCount = 0;

	/** Replaces the box's children with these lines (Style fonts and colours) and parks the box below the screen. */
	void Build(UWidgetTree& Tree, UVerticalBox& Box, UCanvasPanelSlot* Slot, const TArray<FLBCreditLine>& Lines, const ULBUIStyle& Style);

	void Clear(UVerticalBox& Box);

	/** Moves the box for a roll of TotalSeconds that has run ElapsedSeconds. ViewportHeight 0 reads it from the widget or the viewport. */
	void SetProgress(UVerticalBox& Box, UCanvasPanelSlot* Slot, const UUserWidget& Owner, float ElapsedSeconds, float TotalSeconds);

	/** The viewport height in Slate units: the owner's geometry, else the game viewport, else 1080. */
	static float ResolveViewportHeight(const UUserWidget& Owner);

private:
	/** The box content height, measured once after the first layout pass in which it is non-zero (0 = not measured yet). */
	float CachedHeight = 0.f;
	bool bPrepassDone = false;
};
