#pragma once

#include "CoreMinimal.h"
#include "Fonts/SlateFontInfo.h"
#include "Styling/SlateBrush.h"
#include "Components/SlateWrapperTypes.h"

class UTextBlock;
class UWidgetTree;

/** Small helpers for building C++ widget trees (no WBP assets): used by the menu widgets, the key icon and the cinematic overlay. */
namespace LBUIBuild
{
	/** A solid filled rectangle brush. */
	LASTBELL_API FSlateBrush SolidBrush(const FLinearColor& Fill);

	/** A rounded box with an optional outline. */
	LASTBELL_API FSlateBrush RoundedBrush(const FLinearColor& Fill, float Radius, const FLinearColor& Outline = FLinearColor::Transparent, float OutlineWidth = 0.f);

	/** A text block with a font and a colour. */
	LASTBELL_API UTextBlock* MakeText(UWidgetTree& Tree, const FText& Text, const FSlateFontInfo& Font, const FLinearColor& Colour, ETextJustify::Type Justify = ETextJustify::Left);

	/** The font with an outline (the high-contrast prompts). */
	LASTBELL_API FSlateFontInfo WithOutline(FSlateFontInfo Font, int32 OutlineSize, const FLinearColor& OutlineColour);
}
