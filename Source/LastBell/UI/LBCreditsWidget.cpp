#include "UI/LBCreditsWidget.h"
#include "Blueprint/WidgetTree.h"
#include "Cinematics/LBCinematicSettings.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Input/Events.h"
#include "Systems/LBGameSettings.h"
#include "UI/LBUIBuild.h"
#include "UI/LBUISubsystem.h"
#include "LBLog.h"

void ULBCreditsWidget::BuildScreen(UOverlay& RootOverlay)
{
	const ULBUIStyle& Style = GetStyle();
	Backdrop->SetColorAndOpacity(FLinearColor(0.f, 0.f, 0.f, 0.97f));

	Canvas = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("Canvas"));
	if (UOverlaySlot* CanvasSlot = RootOverlay.AddChildToOverlay(Canvas))
	{
		CanvasSlot->SetHorizontalAlignment(HAlign_Fill);
		CanvasSlot->SetVerticalAlignment(VAlign_Fill);
	}

	CreditsBox = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("CreditsBox"));
	UCanvasPanelSlot* BoxSlot = Canvas->AddChildToCanvas(CreditsBox);
	if (BoxSlot)
	{
		BoxSlot->SetAnchors(FAnchors(0.5f, 0.f));
		BoxSlot->SetAlignment(FVector2D(0.5, 0.0));
		BoxSlot->SetAutoSize(false);
		BoxSlot->SetSize(FVector2D(FLBCreditsRoll::CreditsWidth, 100.0));
		BoxSlot->SetPosition(FVector2D(0.0, FLBCreditsRoll::FallbackViewportHeight * 2.0));
	}

	const ULBCinematicSettings* Cinematics = nullptr;
	if (const ULBGameSettings* Game = ULBGameSettings::Get())
	{
		Cinematics = Game->CinematicSettings.IsNull() ? nullptr : Game->CinematicSettings.LoadSynchronous();
	}
	if (Cinematics && !Cinematics->Credits.IsEmpty())
	{
		Duration = FMath::Max(Cinematics->CreditsSeconds, 1.f);
		Roll.Build(*WidgetTree, *CreditsBox, BoxSlot, Cinematics->Credits, Style);
	}
	else
	{
		UE_LOG(LogLB, Log, TEXT("Credits screen: no credits in DA_Cinematics, nothing to roll"));
		Duration = 1.f;
	}

	UTextBlock* Hint = LBUIBuild::MakeText(*WidgetTree, NSLOCTEXT("LastBellUI", "CreditsHint", "Esc to return"), Style.SmallFont(), Style.Dim);
	if (UOverlaySlot* HintSlot = RootOverlay.AddChildToOverlay(Hint))
	{
		HintSlot->SetHorizontalAlignment(HAlign_Right);
		HintSlot->SetVerticalAlignment(VAlign_Bottom);
		HintSlot->SetPadding(FMargin(0.f, 0.f, 48.f, 40.f));
	}
}

void ULBCreditsWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);
	if (!CreditsBox)
	{
		return;
	}
	Elapsed += InDeltaTime;
	Roll.SetProgress(*CreditsBox, Cast<UCanvasPanelSlot>(CreditsBox->Slot), *this, Elapsed, Duration);
	if (Elapsed >= Duration + 1.f)
	{
		HandleBack();
	}
}

FReply ULBCreditsWidget::NativeOnMouseButtonDown(const FGeometry& InGeometry, const FPointerEvent& InMouseEvent)
{
	HandleBack();
	return FReply::Handled();
}
