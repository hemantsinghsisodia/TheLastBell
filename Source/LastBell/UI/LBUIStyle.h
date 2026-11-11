#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "Fonts/SlateFontInfo.h"
#include "InputCoreTypes.h"
#include "LBUIStyle.generated.h"

class UFont;
class UMediaSource;
class USoundBase;
class UTexture2D;

UENUM(BlueprintType)
enum class ELBFontWeight : uint8
{
	Regular,
	Italic,
	SemiBold,
	Bold
};

/** The look of a key prompt: normal, or the high-contrast accessibility variant (white on a dark plate with an outline). */
struct FLBPromptLook
{
	FLinearColor Text = FLinearColor::White;
	FLinearColor Plate = FLinearColor(0.f, 0.f, 0.f, 0.f);
	int32 OutlineSize = 0;
	FLinearColor Outline = FLinearColor::Black;
};

/**
 * DA_UIStyle (plan P18 section 2): every font, colour, size, key icon, UI sound and the menu video of the C++ UI, in one data asset.
 * Everything is a soft reference. With no style linked (ULBGameSettings::UIStyle), or with a field unset, the widgets still work with the
 * engine's default font and no icons: Resolve() falls back to this class's defaults and nothing crashes.
 */
UCLASS(BlueprintType)
class LASTBELL_API ULBUIStyle : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	// ---- Fonts: EB Garamond (SIL OFL 1.1). Each is a UFont asset whose composite font holds the face. ----
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Fonts")
	TSoftObjectPtr<UFont> FontRegular;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Fonts")
	TSoftObjectPtr<UFont> FontItalic;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Fonts")
	TSoftObjectPtr<UFont> FontSemiBold;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Fonts")
	TSoftObjectPtr<UFont> FontBold;

	// ---- Colours ----
	/** The main text colour. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Colours")
	FLinearColor Ink = FLinearColor(0.85f, 0.82f, 0.76f, 1.f);

	/** Secondary text and the unselected items. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Colours")
	FLinearColor Dim = FLinearColor(0.55f, 0.52f, 0.47f, 1.f);

	/** Candle amber: the selected item, sliders and focus. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Colours")
	FLinearColor Accent = FLinearColor(1.f, 0.62f, 0.2f, 1.f);

	/** Panels and plates behind text. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Colours")
	FLinearColor Plate = FLinearColor(0.02f, 0.02f, 0.03f, 0.82f);

	/** Destructive confirmations and errors. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Colours")
	FLinearColor Danger = FLinearColor(0.78f, 0.2f, 0.16f, 1.f);

	/** The high-contrast prompt plate (near-black, opaque). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Colours")
	FLinearColor HighContrastPlate = FLinearColor(0.f, 0.f, 0.f, 0.92f);

	// ---- Sizes in Slate units at 1080p; the viewport's DPI scale does the rest ----
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sizes", meta = (ClampMin = "8"))
	int32 TitleSize = 96;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sizes", meta = (ClampMin = "8"))
	int32 HeadingSize = 40;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sizes", meta = (ClampMin = "8"))
	int32 ItemSize = 34;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sizes", meta = (ClampMin = "8"))
	int32 BodySize = 24;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sizes", meta = (ClampMin = "8"))
	int32 SmallSize = 18;

	// ---- The candle flicker of the selected item ----
	/** Cycles per second. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Flicker", meta = (ClampMin = "0"))
	float FlickerSpeed = 1.6f;

	/** 0 = steady, 1 = the light drops to nothing at the low point. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Flicker", meta = (ClampMin = "0", ClampMax = "1"))
	float FlickerAmplitude = 0.3f;

	// ---- Text ----
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Text")
	FText GameTitle = NSLOCTEXT("LastBellUI", "GameTitle", "THE LAST BELL");

	// ---- Key icons: one texture per key (T_Key_<Key>) ----
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "KeyIcons")
	TMap<FKey, TSoftObjectPtr<UTexture2D>> KeyIcons;

	// ---- UI sounds (SCL_LB_UI) ----
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sounds")
	TSoftObjectPtr<USoundBase> HoverSound;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sounds")
	TSoftObjectPtr<USoundBase> SelectSound;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sounds")
	TSoftObjectPtr<USoundBase> BackSound;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sounds")
	TSoftObjectPtr<USoundBase> SliderTickSound;

	// ---- Menu background ----
	/** The looping video behind the main menu (a file media source in Content/Movies). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Menu")
	TSoftObjectPtr<UMediaSource> MenuVideo;

	/** A still shown when the video is unset or cannot play (a slow drift is applied to it). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Menu")
	TSoftObjectPtr<UTexture2D> MenuFallbackImage;

	/** The brightness screen's symbol (a sigil in mid-grey, barely visible on a dark field). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Menu")
	TSoftObjectPtr<UTexture2D> BrightnessSymbol;

	// ---- Queries ----

	/**
	 * The style to use: the one linked in ULBGameSettings::UIStyle, or this class's defaults (the class default object) when none is
	 * linked or it cannot load. Never null. Logs once when none is linked.
	 */
	static const ULBUIStyle* Resolve();

	/** True when ULBGameSettings::UIStyle is set and loaded. */
	static bool IsStyleLinked();

	/** A font of this weight and size. With no UFont assigned for the weight: the engine's default font of the same weight. */
	FSlateFontInfo MakeFont(ELBFontWeight Weight, int32 Size, int32 LetterSpacing = 0) const;

	FSlateFontInfo TitleFont() const { return MakeFont(ELBFontWeight::SemiBold, TitleSize, 200); }
	FSlateFontInfo HeadingFont() const { return MakeFont(ELBFontWeight::SemiBold, HeadingSize, 60); }
	FSlateFontInfo ItemFont() const { return MakeFont(ELBFontWeight::Regular, ItemSize); }
	FSlateFontInfo BodyFont() const { return MakeFont(ELBFontWeight::Regular, BodySize); }
	FSlateFontInfo SmallFont() const { return MakeFont(ELBFontWeight::Italic, SmallSize); }

	/** The icon entry exists in KeyIcons (the soft path is set). It does not load the texture. */
	bool HasKeyIcon(const FKey& Key) const;

	/** The key's icon texture (loaded synchronously: icons are small), or null when none is set. */
	UTexture2D* FindKeyIcon(const FKey& Key) const;

	/** The prompt colours and outline for the normal or the high-contrast look. */
	FLBPromptLook GetPromptLook(bool bHighContrast) const;
};
