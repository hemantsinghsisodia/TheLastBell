#include "UI/LBUIStyle.h"
#include "Engine/Font.h"
#include "Engine/Texture2D.h"
#include "Styling/CoreStyle.h"
#include "Systems/LBGameSettings.h"
#include "LBLog.h"

namespace
{
	const TCHAR* EngineFaceFor(ELBFontWeight Weight)
	{
		switch (Weight)
		{
		case ELBFontWeight::Italic: return TEXT("Italic");
		case ELBFontWeight::SemiBold: return TEXT("Bold");
		case ELBFontWeight::Bold: return TEXT("Bold");
		default: return TEXT("Regular");
		}
	}
}

const ULBUIStyle* ULBUIStyle::Resolve()
{
	static bool bLoggedMissing = false;
	const ULBGameSettings* Settings = ULBGameSettings::Get();
	if (Settings && !Settings->UIStyle.IsNull())
	{
		if (const ULBUIStyle* Style = Settings->UIStyle.LoadSynchronous())
		{
			return Style;
		}
		if (!bLoggedMissing)
		{
			bLoggedMissing = true;
			UE_LOG(LogLB, Warning, TEXT("UI style %s could not be loaded: the UI uses its built-in defaults"), *Settings->UIStyle.ToString());
		}
	}
	else if (!bLoggedMissing)
	{
		bLoggedMissing = true;
		UE_LOG(LogLB, Log, TEXT("No UI style linked (ULBGameSettings::UIStyle): the UI uses its built-in defaults and the engine font"));
	}
	return GetDefault<ULBUIStyle>();
}

bool ULBUIStyle::IsStyleLinked()
{
	const ULBGameSettings* Settings = ULBGameSettings::Get();
	return Settings && !Settings->UIStyle.IsNull() && Settings->UIStyle.LoadSynchronous() != nullptr;
}

FSlateFontInfo ULBUIStyle::MakeFont(ELBFontWeight Weight, int32 Size, int32 LetterSpacing) const
{
	const TSoftObjectPtr<UFont>* Ref = nullptr;
	switch (Weight)
	{
	case ELBFontWeight::Italic: Ref = &FontItalic; break;
	case ELBFontWeight::SemiBold: Ref = &FontSemiBold; break;
	case ELBFontWeight::Bold: Ref = &FontBold; break;
	default: Ref = &FontRegular; break;
	}

	FSlateFontInfo Info;
	const UFont* Font = (Ref && !Ref->IsNull()) ? Ref->LoadSynchronous() : nullptr;
	if (!Font && Weight != ELBFontWeight::Regular && !FontRegular.IsNull())
	{
		// A missing weight falls back to the regular face of the same family.
		Font = FontRegular.LoadSynchronous();
	}
	if (Font)
	{
		Info = FSlateFontInfo(Font, Size);
	}
	else
	{
		Info = FCoreStyle::GetDefaultFontStyle(FName(EngineFaceFor(Weight)), Size);
	}
	Info.LetterSpacing = LetterSpacing;
	return Info;
}

bool ULBUIStyle::HasKeyIcon(const FKey& Key) const
{
	const TSoftObjectPtr<UTexture2D>* Found = KeyIcons.Find(Key);
	return Found && !Found->IsNull();
}

UTexture2D* ULBUIStyle::FindKeyIcon(const FKey& Key) const
{
	const TSoftObjectPtr<UTexture2D>* Found = KeyIcons.Find(Key);
	return (Found && !Found->IsNull()) ? Found->LoadSynchronous() : nullptr;
}

FLBPromptLook ULBUIStyle::GetPromptLook(bool bHighContrast) const
{
	FLBPromptLook Look;
	if (bHighContrast)
	{
		Look.Text = FLinearColor::White;
		Look.Plate = HighContrastPlate;
		Look.OutlineSize = 2;
		Look.Outline = FLinearColor::Black;
	}
	else
	{
		Look.Text = Ink;
		Look.Plate = FLinearColor(0.f, 0.f, 0.f, 0.f);
		Look.OutlineSize = 0;
		Look.Outline = FLinearColor::Black;
	}
	return Look;
}
