#include "UI/LBMainMenuWidget.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/Texture2D.h"
#include "MediaPlayer.h"
#include "MediaSource.h"
#include "MediaTexture.h"
#include "Save/LBSaveSubsystem.h"
#include "UI/LBUIBuild.h"
#include "UI/LBUISubsystem.h"
#include "LBLog.h"

bool ULBMainMenuWidget::HandleBack()
{
	// On the main menu Escape means Back, and there is nothing behind it.
	return true;
}

void ULBMainMenuWidget::BuildScreen(UOverlay& RootOverlay)
{
	const ULBUIStyle& Style = GetStyle();

	// Background: the video (or the still) under a dark vignette.
	BackgroundImage = WidgetTree->ConstructWidget<UImage>(UImage::StaticClass(), TEXT("Background"));
	BackgroundImage->SetBrush(LBUIBuild::SolidBrush(FLinearColor::White));
	BackgroundImage->SetColorAndOpacity(FLinearColor(0.015f, 0.015f, 0.02f, 1.f));
	if (UOverlaySlot* BackgroundSlot = RootOverlay.AddChildToOverlay(BackgroundImage))
	{
		BackgroundSlot->SetHorizontalAlignment(HAlign_Fill);
		BackgroundSlot->SetVerticalAlignment(VAlign_Fill);
	}
	// The dimming plate over the background (the base Backdrop is the lowest layer, so raise it by re-adding on top).
	Backdrop->SetColorAndOpacity(FLinearColor(0.f, 0.f, 0.f, 0.45f));
	RootOverlay.RemoveChild(Backdrop);
	if (UOverlaySlot* BackdropSlot = RootOverlay.AddChildToOverlay(Backdrop))
	{
		BackdropSlot->SetHorizontalAlignment(HAlign_Fill);
		BackdropSlot->SetVerticalAlignment(VAlign_Fill);
	}

	// The menu column on the left.
	UVerticalBox* Column = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("Column"));
	if (UOverlaySlot* ColumnSlot = RootOverlay.AddChildToOverlay(Column))
	{
		ColumnSlot->SetHorizontalAlignment(HAlign_Left);
		ColumnSlot->SetVerticalAlignment(VAlign_Center);
		ColumnSlot->SetPadding(FMargin(180.f, 0.f, 0.f, 40.f));
	}

	UTextBlock* Title = LBUIBuild::MakeText(*WidgetTree, Style.GameTitle, Style.TitleFont(), Style.Ink);
	if (UVerticalBoxSlot* TitleSlot = Column->AddChildToVerticalBox(Title))
	{
		TitleSlot->SetPadding(FMargin(0.f, 0.f, 0.f, 70.f));
	}

	const ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(GetOwningPlayer());
	const bool bHasSave = Save && Save->HasValidSave();
	TWeakObjectPtr<ULBMainMenuWidget> WeakThis(this);

	if (bHasSave)
	{
		AddButtonItem(*Column, NSLOCTEXT("LastBellUI", "MenuContinue", "Continue"), [WeakThis]()
		{
			if (ULBUISubsystem* UI = WeakThis.IsValid() ? WeakThis->GetUI() : nullptr)
			{
				UI->ContinueFlow();
			}
		});
	}
	AddButtonItem(*Column, NSLOCTEXT("LastBellUI", "MenuNewGame", "New Game"), [WeakThis]()
	{
		if (ULBUISubsystem* UI = WeakThis.IsValid() ? WeakThis->GetUI() : nullptr)
		{
			UI->StartNewGameFlow();
		}
	});
	AddButtonItem(*Column, NSLOCTEXT("LastBellUI", "MenuSettings", "Settings"), [WeakThis]()
	{
		if (ULBUISubsystem* UI = WeakThis.IsValid() ? WeakThis->GetUI() : nullptr)
		{
			UI->OpenSettings();
		}
	});
	AddButtonItem(*Column, NSLOCTEXT("LastBellUI", "MenuCredits", "Credits"), [WeakThis]()
	{
		if (ULBUISubsystem* UI = WeakThis.IsValid() ? WeakThis->GetUI() : nullptr)
		{
			UI->OpenCredits();
		}
	});
	AddButtonItem(*Column, NSLOCTEXT("LastBellUI", "MenuQuit", "Quit"), [WeakThis]()
	{
		if (ULBUISubsystem* UI = WeakThis.IsValid() ? WeakThis->GetUI() : nullptr)
		{
			UI->QuitGameFlow();
		}
	});
}

void ULBMainMenuWidget::NativeConstruct()
{
	Super::NativeConstruct();
	StartBackground();
}

void ULBMainMenuWidget::NativeDestruct()
{
	StopBackground();
	Super::NativeDestruct();
}

void ULBMainMenuWidget::StartBackground()
{
	if (!BackgroundImage || MediaPlayer)
	{
		return;
	}
	const ULBUIStyle& Style = GetStyle();

	if (!Style.MenuVideo.IsNull())
	{
		UMediaSource* Source = Style.MenuVideo.LoadSynchronous();
		if (Source)
		{
			MediaPlayer = NewObject<UMediaPlayer>(this);
			MediaPlayer->SetLooping(true);
			MediaTexture = NewObject<UMediaTexture>(this);
			MediaTexture->SetMediaPlayer(MediaPlayer);
			MediaTexture->UpdateResource();
			if (MediaPlayer->OpenSource(Source))
			{
				FSlateBrush Brush;
				Brush.SetResourceObject(MediaTexture);
				Brush.DrawAs = ESlateBrushDrawType::Image;
				Brush.ImageSize = FVector2f(1920.f, 1080.f);
				BackgroundImage->SetBrush(Brush);
				BackgroundImage->SetColorAndOpacity(FLinearColor::White);
				return;
			}
			UE_LOG(LogLB, Warning, TEXT("Main menu: the video %s could not be opened: using the still"), *Style.MenuVideo.ToString());
			MediaPlayer->Close();
			MediaPlayer = nullptr;
			MediaTexture = nullptr;
		}
		else
		{
			UE_LOG(LogLB, Warning, TEXT("Main menu: the video %s could not be loaded: using the still"), *Style.MenuVideo.ToString());
		}
	}

	if (!Style.MenuFallbackImage.IsNull())
	{
		if (UTexture2D* Still = Style.MenuFallbackImage.LoadSynchronous())
		{
			FSlateBrush Brush;
			Brush.SetResourceObject(Still);
			Brush.DrawAs = ESlateBrushDrawType::Image;
			Brush.ImageSize = FVector2f(1920.f, 1080.f);
			BackgroundImage->SetBrush(Brush);
			BackgroundImage->SetColorAndOpacity(FLinearColor::White);
			bShowingStill = true;
			return;
		}
	}
	UE_LOG(LogLB, Log, TEXT("Main menu: no menu video or still in the UI style: plain dark background"));
}

void ULBMainMenuWidget::StopBackground()
{
	if (MediaPlayer)
	{
		MediaPlayer->Close();
	}
	MediaPlayer = nullptr;
	MediaTexture = nullptr;
}

bool ULBMainMenuWidget::IsVideoPlayingForTest() const
{
	return MediaPlayer && MediaPlayer->IsPlaying();
}

void ULBMainMenuWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);
	if (bShowingStill && BackgroundImage)
	{
		// A slow Ken-Burns drift over the still: scale 1.06 to 1.12 and a gentle sideways pan, on a 60 s ping-pong.
		DriftClock += InDeltaTime;
		const float Phase = 0.5f - 0.5f * FMath::Cos(DriftClock * UE_TWO_PI / 60.f);
		FWidgetTransform Transform;
		Transform.Scale = FVector2D(1.06 + 0.06 * Phase);
		Transform.Translation = FVector2D(-40.0 + 80.0 * Phase, 0.0);
		BackgroundImage->SetRenderTransform(Transform);
	}
}
