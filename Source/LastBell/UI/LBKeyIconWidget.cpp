#include "UI/LBKeyIconWidget.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/BorderSlot.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Engine/LocalPlayer.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "InputAction.h"
#include "Systems/LBUserSettings.h"
#include "UI/LBKeyBindings.h"
#include "UI/LBUIBuild.h"
#include "UI/LBUILogic.h"
#include "UI/LBUIStyle.h"

void ULBKeyIconWidget::NativeOnInitialized()
{
	Super::NativeOnInitialized();
	BuildTree();
	// Bound from creation (NativeConstruct never runs for a widget that is not in the viewport), so the glyph follows a rebinding at any time.
	BindExternalEvents();
	Refresh();
}

void ULBKeyIconWidget::NativeConstruct()
{
	Super::NativeConstruct();
	// A widget removed and added again was unbound by NativeDestruct.
	BindExternalEvents();
	Refresh();
}

void ULBKeyIconWidget::NativeDestruct()
{
	UnbindExternalEvents();
	Super::NativeDestruct();
}

void ULBKeyIconWidget::BeginDestroy()
{
	UnbindExternalEvents();
	Super::BeginDestroy();
}

void ULBKeyIconWidget::BindExternalEvents()
{
	if (!BindingsHandle.IsValid())
	{
		BindingsHandle = LBKeyBindings::OnBindingsChanged().AddUObject(this, &ULBKeyIconWidget::HandleExternalChange);
	}
	if (!SettingsHandle.IsValid())
	{
		SettingsHandle = ULBUserSettings::OnUserSettingsChanged().AddUObject(this, &ULBKeyIconWidget::HandleExternalChange);
	}
}

void ULBKeyIconWidget::UnbindExternalEvents()
{
	if (BindingsHandle.IsValid())
	{
		LBKeyBindings::OnBindingsChanged().Remove(BindingsHandle);
		BindingsHandle.Reset();
	}
	if (SettingsHandle.IsValid())
	{
		ULBUserSettings::OnUserSettingsChanged().Remove(SettingsHandle);
		SettingsHandle.Reset();
	}
}

void ULBKeyIconWidget::BuildTree()
{
	if (SizeBox || !WidgetTree)
	{
		return;
	}
	SizeBox = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("Size"));
	WidgetTree->RootWidget = SizeBox;

	UOverlay* Overlay = WidgetTree->ConstructWidget<UOverlay>(UOverlay::StaticClass());
	SizeBox->AddChild(Overlay);

	Cap = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("Cap"));
	Cap->SetPadding(FMargin(10.f, 2.f));
	CapText = LBUIBuild::MakeText(*WidgetTree, FText::GetEmpty(), FSlateFontInfo(), FLinearColor::White, ETextJustify::Center);
	Cap->SetContent(CapText);
	if (UBorderSlot* CapContent = Cast<UBorderSlot>(CapText->Slot))
	{
		CapContent->SetHorizontalAlignment(HAlign_Center);
		CapContent->SetVerticalAlignment(VAlign_Center);
	}
	if (UOverlaySlot* CapSlot = Overlay->AddChildToOverlay(Cap))
	{
		CapSlot->SetHorizontalAlignment(HAlign_Fill);
		CapSlot->SetVerticalAlignment(VAlign_Fill);
	}

	// The icon is added last so it sits above the high-contrast plate.
	Icon = WidgetTree->ConstructWidget<UImage>(UImage::StaticClass(), TEXT("Icon"));
	Icon->SetVisibility(ESlateVisibility::Collapsed);
	if (UOverlaySlot* IconSlot = Overlay->AddChildToOverlay(Icon))
	{
		IconSlot->SetHorizontalAlignment(HAlign_Fill);
		IconSlot->SetVerticalAlignment(VAlign_Fill);
	}

	SetVisibility(ESlateVisibility::HitTestInvisible);
}

const ULocalPlayer* ULBKeyIconWidget::ResolveLocalPlayer() const
{
	if (const ULocalPlayer* LocalPlayer = GetOwningLocalPlayer())
	{
		return LocalPlayer;
	}
	const UWorld* World = GetWorld();
	return World ? World->GetFirstLocalPlayerFromController() : nullptr;
}

void ULBKeyIconWidget::HandleExternalChange()
{
	Refresh();
}

void ULBKeyIconWidget::SetKey(const FKey& Key)
{
	FollowedAction = ELBBindAction::Count;
	FollowedInputAction.Reset();
	ShownKey = Key;
	Refresh();
}

void ULBKeyIconWidget::SetBoundAction(ELBBindAction Action)
{
	FollowedAction = Action;
	FollowedInputAction.Reset();
	Refresh();
}

void ULBKeyIconWidget::SetBoundInputAction(const UInputAction* Action)
{
	FollowedAction = ELBBindAction::Count;
	FollowedInputAction = const_cast<UInputAction*>(Action);
	Refresh();
}

void ULBKeyIconWidget::SetGlyphHeight(float Height)
{
	GlyphHeight = FMath::Max(Height, 8.f);
	Refresh();
}

FText ULBKeyIconWidget::GetCapTextForTest() const
{
	return CapText ? CapText->GetText() : FText::GetEmpty();
}

void ULBKeyIconWidget::Refresh()
{
	if (!SizeBox || !Icon || !Cap || !CapText)
	{
		return;
	}

	if (FollowedAction != ELBBindAction::Count)
	{
		ShownKey = LBKeyBindings::GetKey(ResolveLocalPlayer(), FollowedAction);
	}
	else if (const UInputAction* InputAction = FollowedInputAction.Get())
	{
		const FKey Found = LBKeyBindings::GetKeyForInputAction(ResolveLocalPlayer(), InputAction);
		if (Found.IsValid())
		{
			ShownKey = Found;
		}
	}

	const ULBUIStyle* Style = ULBUIStyle::Resolve();
	const ULBUserSettings* User = ULBUserSettings::Get();
	bShownHighContrast = User && User->bHighContrastPrompts;
	const FLBPromptLook Look = Style->GetPromptLook(bShownHighContrast);

	SizeBox->SetHeightOverride(GlyphHeight);

	UTexture2D* Texture = ShownKey.IsValid() ? Style->FindKeyIcon(ShownKey) : nullptr;
	bShowingIcon = Texture != nullptr;
	if (Texture)
	{
		const float Aspect = Texture->GetSizeY() > 0 ? static_cast<float>(Texture->GetSizeX()) / static_cast<float>(Texture->GetSizeY()) : 1.f;
		FSlateBrush Brush;
		Brush.SetResourceObject(Texture);
		Brush.DrawAs = ESlateBrushDrawType::Image;
		Brush.ImageSize = FVector2f(GlyphHeight * Aspect, GlyphHeight);
		Icon->SetBrush(Brush);
		// The high-contrast plate sits behind the glyph so a light icon stays readable.
		Icon->SetColorAndOpacity(FLinearColor::White);
		SizeBox->SetWidthOverride(GlyphHeight * Aspect);
		Icon->SetVisibility(ESlateVisibility::HitTestInvisible);
		CapText->SetVisibility(ESlateVisibility::Collapsed);
		if (bShownHighContrast)
		{
			Cap->SetBrush(LBUIBuild::RoundedBrush(Look.Plate, 6.f, Look.Text, 2.f));
			Cap->SetVisibility(ESlateVisibility::HitTestInvisible);
		}
		else
		{
			Cap->SetVisibility(ESlateVisibility::Collapsed);
		}
		return;
	}

	// No icon: a key-cap with the key's name.
	Icon->SetVisibility(ESlateVisibility::Collapsed);
	SizeBox->ClearWidthOverride();
	SizeBox->SetMinDesiredWidth(GlyphHeight);

	const FLinearColor CapFill = bShownHighContrast ? Look.Plate : FLinearColor(0.05f, 0.05f, 0.06f, 0.85f);
	const FLinearColor CapOutline = bShownHighContrast ? Look.Text : Style->Dim;
	Cap->SetBrush(LBUIBuild::RoundedBrush(CapFill, 6.f, CapOutline, bShownHighContrast ? 2.f : 1.5f));
	CapText->SetVisibility(ESlateVisibility::HitTestInvisible);
	FSlateFontInfo Font = Style->MakeFont(ELBFontWeight::SemiBold, FMath::RoundToInt(GlyphHeight * 0.55f));
	if (bShownHighContrast)
	{
		Font = LBUIBuild::WithOutline(Font, Look.OutlineSize, Look.Outline);
	}
	CapText->SetFont(Font);
	CapText->SetColorAndOpacity(FSlateColor(bShownHighContrast ? Look.Text : Style->Ink));
	CapText->SetText(LBUILogic::KeyFallbackLabel(ShownKey));
	Cap->SetVisibility(ESlateVisibility::HitTestInvisible);
}
