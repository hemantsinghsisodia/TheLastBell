#include "UI/LBCreditsLayout.h"
#include "Blueprint/UserWidget.h"
#include "Blueprint/WidgetTree.h"
#include "Cinematics/LBCinematicLogic.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/Spacer.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "UI/LBUIBuild.h"
#include "UI/LBUIStyle.h"

float FLBCreditsRoll::ResolveViewportHeight(const UUserWidget& Owner)
{
	// The canvas fills the viewport, so the owner's own size is it. Before the first layout pass, ask the viewport.
	float ViewportHeight = static_cast<float>(Owner.GetCachedGeometry().GetLocalSize().Y);
	if (ViewportHeight < 1.f && GEngine && GEngine->GameViewport)
	{
		FVector2D Size = FVector2D::ZeroVector;
		GEngine->GameViewport->GetViewportSize(Size);
		ViewportHeight = static_cast<float>(Size.Y);
	}
	return ViewportHeight < 1.f ? FallbackViewportHeight : ViewportHeight;
}

void FLBCreditsRoll::Build(UWidgetTree& Tree, UVerticalBox& Box, UCanvasPanelSlot* Slot, const TArray<FLBCreditLine>& Lines, const ULBUIStyle& Style)
{
	Box.ClearChildren();
	LineCount = 0;
	CachedHeight = 0.f;
	bPrepassDone = false;
	for (const FLBCreditLine& Line : Lines)
	{
		UWidget* Child = nullptr;
		switch (Line.Style)
		{
		case ELBCreditStyle::Heading:
			Child = LBUIBuild::MakeText(Tree, Line.Text, Style.HeadingFont(), Style.Ink, ETextJustify::Center);
			break;
		case ELBCreditStyle::Name:
			Child = LBUIBuild::MakeText(Tree, Line.Text, Style.MakeFont(ELBFontWeight::Regular, Style.BodySize + 2), Style.Ink, ETextJustify::Center);
			break;
		case ELBCreditStyle::Small:
			Child = LBUIBuild::MakeText(Tree, Line.Text, Style.SmallFont(), Style.Dim, ETextJustify::Center);
			break;
		case ELBCreditStyle::Gap:
		{
			USpacer* Gap = Tree.ConstructWidget<USpacer>(USpacer::StaticClass());
			Gap->SetSize(FVector2D(1.0, GapHeight));
			Child = Gap;
			break;
		}
		}
		if (Child)
		{
			if (UVerticalBoxSlot* BoxSlot = Box.AddChildToVerticalBox(Child))
			{
				BoxSlot->SetHorizontalAlignment(HAlign_Center);
				BoxSlot->SetPadding(FMargin(0.f, 3.f));
			}
			++LineCount;
		}
	}
	// Parked below the screen until SetProgress moves it.
	if (Slot)
	{
		Slot->SetPosition(FVector2D(0.0, FallbackViewportHeight * 2.0));
	}
}

void FLBCreditsRoll::Clear(UVerticalBox& Box)
{
	Box.ClearChildren();
	LineCount = 0;
	CachedHeight = 0.f;
	bPrepassDone = false;
}

void FLBCreditsRoll::SetProgress(UVerticalBox& Box, UCanvasPanelSlot* Slot, const UUserWidget& Owner, float ElapsedSeconds, float TotalSeconds)
{
	if (LineCount == 0 || !Slot)
	{
		return;
	}
	const float ViewportHeight = ResolveViewportHeight(Owner);

	// Measured once: the first layout pass in which the content has a height. Until then the box stays parked below the screen.
	if (CachedHeight <= 0.f)
	{
		if (!bPrepassDone)
		{
			bPrepassDone = true;
			Box.ForceLayoutPrepass();
		}
		const float Measured = static_cast<float>(Box.GetDesiredSize().Y);
		if (Measured <= 1.f)
		{
			return;
		}
		CachedHeight = Measured;
		Slot->SetSize(FVector2D(CreditsWidth, CachedHeight));
	}

	const float Speed = LBCinematicLogic::CreditsPixelsPerSecond(CachedHeight, ViewportHeight, TotalSeconds);
	Slot->SetPosition(FVector2D(0.0, ViewportHeight - FMath::Clamp(ElapsedSeconds, 0.f, TotalSeconds) * Speed));
}
