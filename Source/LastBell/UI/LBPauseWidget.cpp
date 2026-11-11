#include "UI/LBPauseWidget.h"
#include "Blueprint/WidgetTree.h"
#include "Components/BackgroundBlur.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "UI/LBUIBuild.h"
#include "UI/LBUISubsystem.h"

bool ULBPauseWidget::HandleBack()
{
	PlaySound(ELBUISound::Back);
	if (ULBUISubsystem* UI = GetUI())
	{
		UI->ClosePause();
		return true;
	}
	RemoveFromParent();
	return true;
}

void ULBPauseWidget::BuildScreen(UOverlay& RootOverlay)
{
	const ULBUIStyle& Style = GetStyle();

	// The game darkens to 60 % and blurs 6 px.
	UBackgroundBlur* Blur = WidgetTree->ConstructWidget<UBackgroundBlur>(UBackgroundBlur::StaticClass(), TEXT("Blur"));
	Blur->SetBlurStrength(6.f);
	if (UOverlaySlot* BlurSlot = RootOverlay.AddChildToOverlay(Blur))
	{
		BlurSlot->SetHorizontalAlignment(HAlign_Fill);
		BlurSlot->SetVerticalAlignment(VAlign_Fill);
	}
	Backdrop->SetColorAndOpacity(FLinearColor(0.f, 0.f, 0.f, 0.6f));
	RootOverlay.RemoveChild(Backdrop);
	if (UOverlaySlot* BackdropSlot = RootOverlay.AddChildToOverlay(Backdrop))
	{
		BackdropSlot->SetHorizontalAlignment(HAlign_Fill);
		BackdropSlot->SetVerticalAlignment(VAlign_Fill);
	}

	UVerticalBox* Column = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("Column"));
	if (UOverlaySlot* ColumnSlot = RootOverlay.AddChildToOverlay(Column))
	{
		ColumnSlot->SetHorizontalAlignment(HAlign_Left);
		ColumnSlot->SetVerticalAlignment(VAlign_Center);
		ColumnSlot->SetPadding(FMargin(180.f, 0.f, 0.f, 40.f));
	}

	UTextBlock* Title = LBUIBuild::MakeText(*WidgetTree, NSLOCTEXT("LastBellUI", "PauseTitle", "Paused"), Style.HeadingFont(), Style.Ink);
	if (UVerticalBoxSlot* TitleSlot = Column->AddChildToVerticalBox(Title))
	{
		TitleSlot->SetPadding(FMargin(0.f, 0.f, 0.f, 50.f));
	}

	TWeakObjectPtr<ULBPauseWidget> WeakThis(this);
	AddButtonItem(*Column, NSLOCTEXT("LastBellUI", "PauseResume", "Resume"), [WeakThis]()
	{
		if (ULBUISubsystem* UI = WeakThis.IsValid() ? WeakThis->GetUI() : nullptr)
		{
			UI->ClosePause();
		}
	});
	AddButtonItem(*Column, NSLOCTEXT("LastBellUI", "PauseSettings", "Settings"), [WeakThis]()
	{
		if (ULBUISubsystem* UI = WeakThis.IsValid() ? WeakThis->GetUI() : nullptr)
		{
			UI->OpenSettings();
		}
	});
	AddButtonItem(*Column, NSLOCTEXT("LastBellUI", "PauseReturn", "Return to main menu"), [WeakThis]()
	{
		if (ULBUISubsystem* UI = WeakThis.IsValid() ? WeakThis->GetUI() : nullptr)
		{
			UI->ReturnToMainMenuFlow();
		}
	});
	AddButtonItem(*Column, NSLOCTEXT("LastBellUI", "PauseQuit", "Quit to desktop"), [WeakThis]()
	{
		if (ULBUISubsystem* UI = WeakThis.IsValid() ? WeakThis->GetUI() : nullptr)
		{
			UI->QuitGameFlow();
		}
	});
}
