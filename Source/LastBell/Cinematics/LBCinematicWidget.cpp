#include "Cinematics/LBCinematicWidget.h"
#include "Cinematics/LBCinematicLogic.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/ProgressBar.h"
#include "Components/Spacer.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Styling/CoreStyle.h"

namespace
{
	// Section 2.9. All text colour is this; fonts are the default Roboto faces.
	const FLinearColor TextColour(0.85f, 0.82f, 0.76f, 1.f);
	constexpr float CreditsWidth = 1200.f;
	constexpr float CreditGapHeight = 40.f;
	constexpr float FallbackViewportHeight = 1080.f;

	FSlateFontInfo Font(const TCHAR* Face, float Size, int32 LetterSpacing = 0)
	{
		FSlateFontInfo Info = FCoreStyle::GetDefaultFontStyle(FName(Face), Size);
		Info.LetterSpacing = LetterSpacing;
		return Info;
	}

	UTextBlock* MakeText(UWidgetTree& Tree, const FSlateFontInfo& InFont, const FLinearColor& Colour)
	{
		UTextBlock* Text = Tree.ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
		Text->SetFont(InFont);
		Text->SetColorAndOpacity(FSlateColor(Colour));
		Text->SetJustification(ETextJustify::Center);
		return Text;
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

	Root = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("Root"));
	WidgetTree->RootWidget = Root;

	// The story card: centred, wraps at 1400.
	CardText = MakeText(*WidgetTree, Font(TEXT("Light"), 30.f), TextColour);
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
	TitleText = MakeText(*WidgetTree, Font(TEXT("Light"), 72.f, 300), TextColour);
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

	// The skip prompt and its bar: bottom-right, 48 px margin.
	SkipText = MakeText(*WidgetTree, Font(TEXT("Regular"), 16.f), TextColour);
	SkipText->SetJustification(ETextJustify::Right);
	SkipText->SetRenderOpacity(0.f);
	if (UCanvasPanelSlot* PanelSlot = Root->AddChildToCanvas(SkipText))
	{
		PanelSlot->SetAnchors(FAnchors(1.f, 1.f));
		PanelSlot->SetAlignment(FVector2D(1.0, 1.0));
		PanelSlot->SetPosition(FVector2D(-48.0, -57.0));
		PanelSlot->SetAutoSize(true);
	}

	SkipBar = WidgetTree->ConstructWidget<UProgressBar>(UProgressBar::StaticClass());
	SkipBar->SetPercent(0.f);
	SkipBar->SetFillColorAndOpacity(TextColour);
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

void ULBCinematicWidget::SetSkipPromptText(const FText& Text)
{
	if (SkipText)
	{
		SkipText->SetText(Text);
	}
}

void ULBCinematicWidget::SetSkipState(bool bSkippable, float Fraction)
{
	if (SkipText)
	{
		SkipText->SetRenderOpacity(bSkippable ? 0.6f : 0.f);
	}
	if (SkipBar)
	{
		SkipBar->SetRenderOpacity(bSkippable ? 0.6f : 0.f);
		SkipBar->SetPercent(bSkippable ? FMath::Clamp(Fraction, 0.f, 1.f) : 0.f);
	}
}

bool ULBCinematicWidget::IsSkipPromptVisibleForTest() const
{
	return SkipText && SkipText->GetRenderOpacity() > 0.f;
}

void ULBCinematicWidget::BuildCredits(const TArray<FLBCreditLine>& Lines)
{
	if (!CreditsBox || !WidgetTree)
	{
		return;
	}
	CreditsBox->ClearChildren();
	CreditLineCount = 0;
	for (const FLBCreditLine& Line : Lines)
	{
		UWidget* Child = nullptr;
		switch (Line.Style)
		{
		case ELBCreditStyle::Heading:
		{
			UTextBlock* Text = MakeText(*WidgetTree, Font(TEXT("Light"), 36.f), TextColour);
			Text->SetText(Line.Text);
			Child = Text;
			break;
		}
		case ELBCreditStyle::Name:
		{
			UTextBlock* Text = MakeText(*WidgetTree, Font(TEXT("Light"), 26.f), TextColour);
			Text->SetText(Line.Text);
			Child = Text;
			break;
		}
		case ELBCreditStyle::Small:
		{
			// Colour x 0.7 (the alpha stays 1).
			const FLinearColor Dim(TextColour.R * 0.7f, TextColour.G * 0.7f, TextColour.B * 0.7f, 1.f);
			UTextBlock* Text = MakeText(*WidgetTree, Font(TEXT("Regular"), 18.f), Dim);
			Text->SetText(Line.Text);
			Child = Text;
			break;
		}
		case ELBCreditStyle::Gap:
		{
			USpacer* Gap = WidgetTree->ConstructWidget<USpacer>(USpacer::StaticClass());
			Gap->SetSize(FVector2D(1.0, CreditGapHeight));
			Child = Gap;
			break;
		}
		}
		if (Child)
		{
			if (UVerticalBoxSlot* BoxSlot = CreditsBox->AddChildToVerticalBox(Child))
			{
				BoxSlot->SetHorizontalAlignment(HAlign_Center);
				BoxSlot->SetPadding(FMargin(0.f, 3.f));
			}
			++CreditLineCount;
		}
	}
	// Parked below the screen until SetCreditsProgress moves it.
	if (UCanvasPanelSlot* PanelSlot = Cast<UCanvasPanelSlot>(CreditsBox->Slot))
	{
		PanelSlot->SetPosition(FVector2D(0.0, FallbackViewportHeight * 2.0));
	}
}

void ULBCinematicWidget::ClearCredits()
{
	if (CreditsBox)
	{
		CreditsBox->ClearChildren();
	}
	CreditLineCount = 0;
}

void ULBCinematicWidget::SetCreditsProgress(float ElapsedSeconds, float TotalSeconds)
{
	if (!CreditsBox || CreditLineCount == 0)
	{
		return;
	}
	UCanvasPanelSlot* PanelSlot = Cast<UCanvasPanelSlot>(CreditsBox->Slot);
	if (!PanelSlot)
	{
		return;
	}

	// The viewport height in slate units: the canvas fills the viewport, so its own size is it. Before the first layout pass, ask the viewport.
	float ViewportHeight = static_cast<float>(GetCachedGeometry().GetLocalSize().Y);
	if (ViewportHeight < 1.f && GEngine && GEngine->GameViewport)
	{
		FVector2D Size = FVector2D::ZeroVector;
		GEngine->GameViewport->GetViewportSize(Size);
		ViewportHeight = static_cast<float>(Size.Y);
	}
	if (ViewportHeight < 1.f)
	{
		ViewportHeight = FallbackViewportHeight;
	}

	CreditsBox->ForceLayoutPrepass();
	const float BoxHeight = FMath::Max(static_cast<float>(CreditsBox->GetDesiredSize().Y), 1.f);
	PanelSlot->SetSize(FVector2D(CreditsWidth, BoxHeight));

	const float Speed = LBCinematicLogic::CreditsPixelsPerSecond(BoxHeight, ViewportHeight, TotalSeconds);
	PanelSlot->SetPosition(FVector2D(0.0, ViewportHeight - FMath::Clamp(ElapsedSeconds, 0.f, TotalSeconds) * Speed));
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
