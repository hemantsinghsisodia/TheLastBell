#include "Cinematics/LBCinematicWidget.h"
#include "Cinematics/LBCinematicLogic.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/ProgressBar.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "UI/LBKeyIconWidget.h"
#include "UI/LBUIBuild.h"
#include "UI/LBUIStyle.h"

namespace
{
	constexpr float CreditsWidth = FLBCreditsRoll::CreditsWidth;
	constexpr float FallbackViewportHeight = FLBCreditsRoll::FallbackViewportHeight;

	UTextBlock* MakeCentred(UWidgetTree& Tree, const FSlateFontInfo& Font, const FLinearColor& Colour)
	{
		return LBUIBuild::MakeText(Tree, FText::GetEmpty(), Font, Colour, ETextJustify::Center);
	}
}

void ULBCinematicWidget::NativeOnInitialized()
{
	Super::NativeOnInitialized();
	BuildTree();
}

void ULBCinematicWidget::BuildTree()
{
	if (Root || !WidgetTree)
	{
		return;
	}
	// Fonts and colours come from DA_UIStyle; with none linked this is the engine font and the P17 colours.
	const ULBUIStyle& Style = *ULBUIStyle::Resolve();

	Root = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("Root"));
	WidgetTree->RootWidget = Root;

	// The story card: centred, wraps at 1400.
	CardText = MakeCentred(*WidgetTree, Style.MakeFont(ELBFontWeight::Regular, Style.ItemSize), Style.Ink);
	CardText->SetAutoWrapText(true);
	CardText->SetWrapTextAt(1400.f);
	CardText->SetRenderOpacity(0.f);
	if (UCanvasPanelSlot* PanelSlot = Root->AddChildToCanvas(CardText))
	{
		PanelSlot->SetAnchors(FAnchors(0.5f, 0.5f));
		PanelSlot->SetAlignment(FVector2D(0.5, 0.5));
		PanelSlot->SetPosition(FVector2D::ZeroVector);
		PanelSlot->SetAutoSize(true);
	}

	// The title: large, letter-spaced.
	TitleText = MakeCentred(*WidgetTree, Style.TitleFont(), Style.Ink);
	TitleText->SetRenderOpacity(0.f);
	if (UCanvasPanelSlot* PanelSlot = Root->AddChildToCanvas(TitleText))
	{
		PanelSlot->SetAnchors(FAnchors(0.5f, 0.5f));
		PanelSlot->SetAlignment(FVector2D(0.5, 0.5));
		PanelSlot->SetPosition(FVector2D::ZeroVector);
		PanelSlot->SetAutoSize(true);
	}

	// The credits box: top-centre, 1200 wide, parked below the screen until a roll starts.
	CreditsBox = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	if (UCanvasPanelSlot* PanelSlot = Root->AddChildToCanvas(CreditsBox))
	{
		PanelSlot->SetAnchors(FAnchors(0.5f, 0.f));
		PanelSlot->SetAlignment(FVector2D(0.5, 0.0));
		PanelSlot->SetPosition(FVector2D(0.0, FallbackViewportHeight * 2.0));
		PanelSlot->SetAutoSize(false);
		PanelSlot->SetSize(FVector2D(CreditsWidth, 100.0));
	}

	// The skip prompt "Hold [key] to skip" and its bar: bottom-right, 48 px margin.
	SkipRow = WidgetTree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	SkipRow->SetRenderOpacity(0.f);
	{
		const FSlateFontInfo SkipFont = Style.MakeFont(ELBFontWeight::Regular, Style.SmallSize);
		UTextBlock* Hold = LBUIBuild::MakeText(*WidgetTree, NSLOCTEXT("LastBellCinematics", "SkipHold", "Hold"), SkipFont, Style.Ink);
		if (UHorizontalBoxSlot* BoxSlot = SkipRow->AddChildToHorizontalBox(Hold))
		{
			BoxSlot->SetVerticalAlignment(VAlign_Center);
			BoxSlot->SetPadding(FMargin(0.f, 0.f, 8.f, 0.f));
		}
		SkipKeyIcon = WidgetTree->ConstructWidget<ULBKeyIconWidget>(ULBKeyIconWidget::StaticClass());
		SkipKeyIcon->SetPlayerContext(GetPlayerContext());
		SkipKeyIcon->SetGlyphHeight(static_cast<float>(Style.SmallSize) * 1.5f);
		SkipKeyIcon->SetBoundAction(ELBBindAction::Interact);
		if (UHorizontalBoxSlot* BoxSlot = SkipRow->AddChildToHorizontalBox(SkipKeyIcon))
		{
			BoxSlot->SetVerticalAlignment(VAlign_Center);
			BoxSlot->SetPadding(FMargin(0.f, 0.f, 8.f, 0.f));
		}
		UTextBlock* ToSkip = LBUIBuild::MakeText(*WidgetTree, NSLOCTEXT("LastBellCinematics", "SkipTo", "to skip"), SkipFont, Style.Ink);
		if (UHorizontalBoxSlot* BoxSlot = SkipRow->AddChildToHorizontalBox(ToSkip))
		{
			BoxSlot->SetVerticalAlignment(VAlign_Center);
		}
	}
	if (UCanvasPanelSlot* PanelSlot = Root->AddChildToCanvas(SkipRow))
	{
		PanelSlot->SetAnchors(FAnchors(1.f, 1.f));
		PanelSlot->SetAlignment(FVector2D(1.0, 1.0));
		PanelSlot->SetPosition(FVector2D(-48.0, -57.0));
		PanelSlot->SetAutoSize(true);
	}

	SkipBar = WidgetTree->ConstructWidget<UProgressBar>(UProgressBar::StaticClass());
	SkipBar->SetPercent(0.f);
	SkipBar->SetFillColorAndOpacity(Style.Ink);
	SkipBar->SetRenderOpacity(0.f);
	if (UCanvasPanelSlot* PanelSlot = Root->AddChildToCanvas(SkipBar))
	{
		PanelSlot->SetAnchors(FAnchors(1.f, 1.f));
		PanelSlot->SetAlignment(FVector2D(1.0, 1.0));
		PanelSlot->SetPosition(FVector2D(-48.0, -48.0));
		PanelSlot->SetAutoSize(false);
		PanelSlot->SetSize(FVector2D(120.0, 3.0));
	}

	// Nothing here takes the mouse or focus.
	SetVisibility(ESlateVisibility::HitTestInvisible);
}

void ULBCinematicWidget::SetCard(const FText& Text, ELBCineCardStyle Style, float Opacity)
{
	if (!CardText || !TitleText)
	{
		return;
	}
	ShownStyle = Style;
	UTextBlock* Shown = Style == ELBCineCardStyle::Title ? TitleText : CardText;
	UTextBlock* Hidden = Style == ELBCineCardStyle::Title ? CardText : TitleText;
	Shown->SetText(Text);
	Shown->SetRenderOpacity(FMath::Clamp(Opacity, 0.f, 1.f));
	Hidden->SetText(FText::GetEmpty());
	Hidden->SetRenderOpacity(0.f);
}

void ULBCinematicWidget::ClearCard()
{
	if (CardText)
	{
		CardText->SetText(FText::GetEmpty());
		CardText->SetRenderOpacity(0.f);
	}
	if (TitleText)
	{
		TitleText->SetText(FText::GetEmpty());
		TitleText->SetRenderOpacity(0.f);
	}
}

void ULBCinematicWidget::SetSkipState(bool bSkippable, float Fraction)
{
	if (SkipRow)
	{
		SkipRow->SetRenderOpacity(bSkippable ? 0.6f : 0.f);
	}
	if (SkipBar)
	{
		SkipBar->SetRenderOpacity(bSkippable ? 0.6f : 0.f);
		SkipBar->SetPercent(bSkippable ? FMath::Clamp(Fraction, 0.f, 1.f) : 0.f);
	}
}

bool ULBCinematicWidget::IsSkipPromptVisibleForTest() const
{
	return SkipRow && SkipRow->GetRenderOpacity() > 0.f;
}

void ULBCinematicWidget::BuildCredits(const TArray<FLBCreditLine>& Lines)
{
	if (!CreditsBox || !WidgetTree)
	{
		return;
	}
	CreditsRoll.Build(*WidgetTree, *CreditsBox, Cast<UCanvasPanelSlot>(CreditsBox->Slot), Lines, *ULBUIStyle::Resolve());
}

void ULBCinematicWidget::ClearCredits()
{
	if (CreditsBox)
	{
		CreditsRoll.Clear(*CreditsBox);
	}
}

void ULBCinematicWidget::SetCreditsProgress(float ElapsedSeconds, float TotalSeconds)
{
	if (!CreditsBox)
	{
		return;
	}
	CreditsRoll.SetProgress(*CreditsBox, Cast<UCanvasPanelSlot>(CreditsBox->Slot), *this, ElapsedSeconds, TotalSeconds);
}

FText ULBCinematicWidget::GetCardTextForTest() const
{
	const UTextBlock* Shown = ShownStyle == ELBCineCardStyle::Title ? TitleText.Get() : CardText.Get();
	return Shown ? Shown->GetText() : FText::GetEmpty();
}

float ULBCinematicWidget::GetCardOpacityForTest() const
{
	const UTextBlock* Shown = ShownStyle == ELBCineCardStyle::Title ? TitleText.Get() : CardText.Get();
	return Shown ? Shown->GetRenderOpacity() : 0.f;
}
