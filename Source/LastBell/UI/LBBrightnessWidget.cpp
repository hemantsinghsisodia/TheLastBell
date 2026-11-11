#include "UI/LBBrightnessWidget.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/Texture2D.h"
#include "Systems/LBUserSettings.h"
#include "UI/LBUIBuild.h"
#include "UI/LBUILogic.h"
#include "UI/LBUISubsystem.h"

void ULBBrightnessWidget::BuildScreen(UOverlay& RootOverlay)
{
	const ULBUIStyle& Style = GetStyle();
	RowTextSize = Style.BodySize + 2;

	ULBUserSettings* User = ULBUserSettings::GetUserSettings();
	InitialGamma = User ? User->Gamma : LBUILogic::DefaultGamma;

	// A near-black field: the symbol must be barely visible on it.
	Backdrop->SetColorAndOpacity(FLinearColor(0.01f, 0.01f, 0.012f, 1.f));

	UVerticalBox* Column = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("Column"));
	if (UOverlaySlot* ColumnSlot = RootOverlay.AddChildToOverlay(Column))
	{
		ColumnSlot->SetHorizontalAlignment(HAlign_Center);
		ColumnSlot->SetVerticalAlignment(VAlign_Center);
	}

	UTextBlock* Title = LBUIBuild::MakeText(*WidgetTree, NSLOCTEXT("LastBellUI", "BrightnessTitle", "Brightness"), Style.HeadingFont(), Style.Ink, ETextJustify::Center);
	if (UVerticalBoxSlot* ColumnEntry = Column->AddChildToVerticalBox(Title))
	{
		ColumnEntry->SetHorizontalAlignment(HAlign_Center);
		ColumnEntry->SetPadding(FMargin(0.f, 0.f, 0.f, 24.f));
	}

	// The symbol: the style's texture (a sigil in mid-grey), or a dim ring when the texture is missing.
	Symbol = WidgetTree->ConstructWidget<UImage>(UImage::StaticClass(), TEXT("Symbol"));
	UTexture2D* Texture = Style.BrightnessSymbol.IsNull() ? nullptr : Style.BrightnessSymbol.LoadSynchronous();
	if (Texture)
	{
		FSlateBrush Brush;
		Brush.SetResourceObject(Texture);
		Brush.DrawAs = ESlateBrushDrawType::Image;
		Brush.ImageSize = FVector2f(256.f, 256.f);
		Symbol->SetBrush(Brush);
		Symbol->SetColorAndOpacity(FLinearColor::White);
	}
	else
	{
		Symbol->SetBrush(LBUIBuild::RoundedBrush(FLinearColor(0.f, 0.f, 0.f, 0.f), 128.f, FLinearColor(0.08f, 0.08f, 0.09f, 1.f), 10.f));
		Symbol->SetDesiredSizeOverride(FVector2D(256.0, 256.0));
	}
	if (UVerticalBoxSlot* ColumnEntry = Column->AddChildToVerticalBox(Symbol))
	{
		ColumnEntry->SetHorizontalAlignment(HAlign_Center);
		ColumnEntry->SetPadding(FMargin(0.f, 0.f, 0.f, 24.f));
	}

	UTextBlock* Hint = LBUIBuild::MakeText(*WidgetTree, NSLOCTEXT("LastBellUI", "BrightnessHint", "Raise the brightness until the symbol is barely visible."), Style.BodyFont(), Style.Dim, ETextJustify::Center);
	if (UVerticalBoxSlot* ColumnEntry = Column->AddChildToVerticalBox(Hint))
	{
		ColumnEntry->SetHorizontalAlignment(HAlign_Center);
		ColumnEntry->SetPadding(FMargin(0.f, 0.f, 0.f, 28.f));
	}

	TWeakObjectPtr<ULBBrightnessWidget> WeakThis(this);
	SliderItem = AddSliderItem(*Column, NSLOCTEXT("LastBellUI", "BrightnessSlider", "Brightness"), LBUILogic::MinGamma, LBUILogic::MaxGamma, 0.05f, InitialGamma,
		[](float Value) { return FText::AsNumber(Value, &FNumberFormattingOptions().SetMinimumFractionalDigits(2).SetMaximumFractionalDigits(2)); },
		[](float Value, bool bFinal)
		{
			if (ULBUserSettings* Settings = ULBUserSettings::GetUserSettings())
			{
				if (bFinal)
				{
					Settings->SetGamma(Value);
				}
				else
				{
					Settings->SetGammaTransient(Value);
				}
			}
		});
	AddButtonItem(*Column, NSLOCTEXT("LastBellUI", "BrightnessConfirm", "Confirm"), [WeakThis]()
	{
		if (WeakThis.IsValid())
		{
			WeakThis->ConfirmBrightness();
		}
	});
}

void ULBBrightnessWidget::ConfirmBrightness()
{
	if (ULBUserSettings* Settings = ULBUserSettings::GetUserSettings())
	{
		const FLBMenuItem* Item = GetItem(SliderItem);
		Settings->SetGamma(Item ? Item->Value : Settings->Gamma);
		Settings->SetBrightnessCalibrated(true);
	}
	PlaySound(ELBUISound::Select);
	if (ULBUISubsystem* UI = GetUI())
	{
		if (UI->GetTopWidget() == this)
		{
			UI->PopScreen();
			return;
		}
	}
	RemoveFromParent();
}

bool ULBBrightnessWidget::HandleBack()
{
	ULBUISubsystem* UI = GetUI();
	if (UI && UI->IsFirstLaunchBrightnessOpen())
	{
		// First launch: the player must confirm.
		return true;
	}
	// From Settings: put the gamma back to what it was.
	if (ULBUserSettings* Settings = ULBUserSettings::GetUserSettings())
	{
		Settings->SetGamma(InitialGamma);
	}
	return Super::HandleBack();
}
