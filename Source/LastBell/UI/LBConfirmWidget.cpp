#include "UI/LBConfirmWidget.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/BorderSlot.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "UI/LBUIBuild.h"
#include "UI/LBUISubsystem.h"

void ULBConfirmWidget::BuildScreen(UOverlay& RootOverlay)
{
	const ULBUIStyle& Style = GetStyle();
	RowTextSize = Style.BodySize + 4;

	// The dialog covers the screen below with a dim veil and a centred plate.
	Backdrop->SetColorAndOpacity(FLinearColor(0.f, 0.f, 0.f, 0.6f));

	UBorder* Plate = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("Plate"));
	Plate->SetBrush(LBUIBuild::RoundedBrush(FLinearColor(Style.Plate.R, Style.Plate.G, Style.Plate.B, 0.95f), 10.f, Style.Dim, 1.5f));
	Plate->SetPadding(FMargin(56.f, 40.f));
	if (UOverlaySlot* PlateSlot = RootOverlay.AddChildToOverlay(Plate))
	{
		PlateSlot->SetHorizontalAlignment(HAlign_Center);
		PlateSlot->SetVerticalAlignment(VAlign_Center);
	}

	USizeBox* Width = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
	Width->SetMinDesiredWidth(640.f);
	Width->SetMaxDesiredWidth(900.f);
	Plate->SetContent(Width);

	UVerticalBox* Column = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("Column"));
	Width->AddChild(Column);

	TitleText = LBUIBuild::MakeText(*WidgetTree, FText::GetEmpty(), Style.HeadingFont(), Style.Ink);
	if (UVerticalBoxSlot* TitleSlot = Column->AddChildToVerticalBox(TitleText))
	{
		TitleSlot->SetPadding(FMargin(0.f, 0.f, 0.f, 18.f));
	}

	MessageText = LBUIBuild::MakeText(*WidgetTree, FText::GetEmpty(), Style.BodyFont(), Style.Ink);
	MessageText->SetAutoWrapText(true);
	if (UVerticalBoxSlot* MessageSlot = Column->AddChildToVerticalBox(MessageText))
	{
		MessageSlot->SetPadding(FMargin(0.f, 0.f, 0.f, 8.f));
	}

	CountdownText = LBUIBuild::MakeText(*WidgetTree, FText::GetEmpty(), Style.SmallFont(), Style.Accent);
	CountdownText->SetVisibility(ESlateVisibility::Collapsed);
	if (UVerticalBoxSlot* CountdownSlot = Column->AddChildToVerticalBox(CountdownText))
	{
		CountdownSlot->SetPadding(FMargin(0.f, 0.f, 0.f, 18.f));
	}

	TWeakObjectPtr<ULBConfirmWidget> WeakThis(this);
	ConfirmItem = AddButtonItem(*Column, Request.ConfirmLabel, [WeakThis]()
	{
		if (WeakThis.IsValid())
		{
			WeakThis->Confirm();
		}
	});
	CancelItem = AddButtonItem(*Column, Request.CancelLabel, [WeakThis]()
	{
		if (WeakThis.IsValid())
		{
			WeakThis->Cancel();
		}
	});
}

void ULBConfirmWidget::Configure(const FLBConfirmRequest& InRequest)
{
	Request = InRequest;
	bAnswered = false;
	if (TitleText)
	{
		TitleText->SetText(Request.Title);
	}
	if (MessageText)
	{
		MessageText->SetText(Request.Message);
	}
	SetItemLabel(ConfirmItem, Request.ConfirmLabel);
	SetItemLabel(CancelItem, Request.CancelLabel);
	SetItemDanger(ConfirmItem, Request.bDanger);
	// A dangerous question starts on its safe answer.
	SelectItem(Request.bDanger ? CancelItem : ConfirmItem, false);

	Timer.Begin(Request.TimeoutSeconds);
	UpdateCountdownText();
}

void ULBConfirmWidget::UpdateCountdownText()
{
	if (!CountdownText)
	{
		return;
	}
	if (Timer.bActive)
	{
		const FText Format = Request.bTimeoutConfirms ? NSLOCTEXT("LastBellUI", "ConfirmingIn", "Confirming in {0} s")
													  : NSLOCTEXT("LastBellUI", "RevertingIn", "Reverting in {0} s");
		CountdownText->SetText(FText::Format(Format, FText::AsNumber(Timer.SecondsShown())));
		CountdownText->SetVisibility(ESlateVisibility::HitTestInvisible);
	}
	else
	{
		CountdownText->SetVisibility(ESlateVisibility::Collapsed);
	}
}

FText ULBConfirmWidget::GetMessageTextForTest() const
{
	return MessageText ? MessageText->GetText() : FText::GetEmpty();
}

void ULBConfirmWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);
	// Slate's delta is real time, so the countdown also runs while the game is paused.
	TickCountdown(InDeltaTime);
}

void ULBConfirmWidget::TickCountdown(float DeltaSeconds)
{
	if (bAnswered || !Timer.bActive)
	{
		return;
	}
	const bool bExpired = Timer.Tick(DeltaSeconds);
	UpdateCountdownText();
	if (bExpired)
	{
		Answer(Request.bTimeoutConfirms);
	}
}

void ULBConfirmWidget::Confirm()
{
	Answer(true);
}

void ULBConfirmWidget::Cancel()
{
	Answer(false);
}

bool ULBConfirmWidget::HandleBack()
{
	Answer(false);
	return true;
}

void ULBConfirmWidget::Answer(bool bConfirmed)
{
	if (bAnswered)
	{
		return;
	}
	bAnswered = true;
	Timer.Cancel();
	PlaySound(bConfirmed ? ELBUISound::Select : ELBUISound::Back);

	// Copy the callback out: the dialog is removed first so a callback that clears the stack or travels finds a consistent state.
	const TFunction<void()> Callback = bConfirmed ? Request.OnConfirm : Request.OnCancel;
	if (ULBUISubsystem* UI = GetUI())
	{
		if (UI->GetTopWidget() == this)
		{
			UI->PopScreen();
		}
		else
		{
			RemoveFromParent();
		}
	}
	else
	{
		RemoveFromParent();
	}
	if (Callback)
	{
		Callback();
	}
}
