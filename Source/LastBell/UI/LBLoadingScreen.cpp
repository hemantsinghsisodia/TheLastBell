#include "UI/LBLoadingScreen.h"
#include "MoviePlayer.h"
#include "Containers/Ticker.h"
#include "HAL/PlatformTime.h"
#include "Styling/CoreStyle.h"
#include "Styling/SlateBrush.h"
#include "UI/LBUIBuild.h"
#include "UI/LBUILogic.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"
#include "LBLog.h"

namespace
{
	int32 GArmCount = 0;
	int32 GHandedCount = 0;
	bool GArmed = false;

	const FLinearColor CandleAmber(1.f, 0.62f, 0.2f, 1.f);
	const FLinearColor TitleColour(0.85f, 0.82f, 0.76f, 0.9f);

	float FlameFlicker()
	{
		return LBUILogic::CandleFlicker(static_cast<float>(FPlatformTime::Seconds()), 1.8f, 0.4f);
	}

	/** Black, the title and a candle that flickers. No UObjects: the movie player draws it on its own thread. */
	class SLBLoadingScreen : public SCompoundWidget
	{
	public:
		SLATE_BEGIN_ARGS(SLBLoadingScreen) {}
		SLATE_END_ARGS()

		void Construct(const FArguments& InArgs)
		{
			WaxBrush = LBUIBuild::RoundedBrush(FLinearColor(0.78f, 0.74f, 0.64f, 1.f), 3.f);
			FlameBrush = LBUIBuild::RoundedBrush(FLinearColor::White, 9.f);
			GlowBrush = LBUIBuild::RoundedBrush(FLinearColor::White, 40.f);

			ChildSlot
			[
				SNew(SOverlay)
				+ SOverlay::Slot()
				[
					SNew(SBorder)
					.BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
					.BorderBackgroundColor(FLinearColor::Black)
				]
				+ SOverlay::Slot()
				.HAlign(HAlign_Center)
				.VAlign(VAlign_Center)
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot()
					.AutoHeight()
					.HAlign(HAlign_Center)
					[
						SNew(STextBlock)
						.Text(NSLOCTEXT("LastBellUI", "LoadingTitle", "THE LAST BELL"))
						.Font(FCoreStyle::GetDefaultFontStyle("Light", 44))
						.ColorAndOpacity(TitleColour)
					]
					+ SVerticalBox::Slot()
					.AutoHeight()
					.HAlign(HAlign_Center)
					.Padding(0.f, 70.f, 0.f, 0.f)
					[
						SNew(SOverlay)
						+ SOverlay::Slot()
						.HAlign(HAlign_Center)
						.VAlign(VAlign_Top)
						[
							SNew(SBox)
							.WidthOverride(80.f)
							.HeightOverride(80.f)
							[
								SNew(SImage)
								.Image(&GlowBrush)
								.ColorAndOpacity(this, &SLBLoadingScreen::GetGlowColour)
							]
						]
						+ SOverlay::Slot()
						.HAlign(HAlign_Center)
						.VAlign(VAlign_Top)
						[
							SNew(SVerticalBox)
							+ SVerticalBox::Slot()
							.AutoHeight()
							.HAlign(HAlign_Center)
							.Padding(0.f, 12.f, 0.f, 2.f)
							[
								SNew(SBox)
								.WidthOverride(14.f)
								.HeightOverride(this, &SLBLoadingScreen::GetFlameHeight)
								[
									SNew(SImage)
									.Image(&FlameBrush)
									.ColorAndOpacity(this, &SLBLoadingScreen::GetFlameColour)
								]
							]
							+ SVerticalBox::Slot()
							.AutoHeight()
							.HAlign(HAlign_Center)
							[
								SNew(SBox)
								.WidthOverride(16.f)
								.HeightOverride(48.f)
								[
									SNew(SImage)
									.Image(&WaxBrush)
								]
							]
						]
					]
				]
			];
		}

	private:
		FSlateColor GetFlameColour() const
		{
			const float Flicker = FlameFlicker();
			return FSlateColor(FLinearColor(CandleAmber.R, CandleAmber.G * (0.8f + 0.2f * Flicker), CandleAmber.B, Flicker));
		}

		FSlateColor GetGlowColour() const
		{
			return FSlateColor(FLinearColor(CandleAmber.R, CandleAmber.G, CandleAmber.B, 0.10f * FlameFlicker()));
		}

		FOptionalSize GetFlameHeight() const
		{
			return FOptionalSize(18.f + 8.f * FlameFlicker());
		}

		FSlateBrush WaxBrush;
		FSlateBrush FlameBrush;
		FSlateBrush GlowBrush;
	};
}

TSharedRef<SWidget> LBLoadingScreen::CreateWidget()
{
	return SNew(SLBLoadingScreen);
}

FLoadingScreenAttributes LBLoadingScreen::MakeAttributes()
{
	FLoadingScreenAttributes Attributes;
	Attributes.bAutoCompleteWhenLoadingCompletes = true;
	Attributes.bMoviesAreSkippable = false;
	Attributes.bWaitForManualStop = false;
	Attributes.MinimumLoadingScreenDisplayTime = MinimumDisplaySeconds;
	Attributes.WidgetLoadingScreen = CreateWidget();
	return Attributes;
}

bool LBLoadingScreen::ValidateAttributes()
{
	const FLoadingScreenAttributes Attributes = MakeAttributes();
	return Attributes.IsValid() && Attributes.bAutoCompleteWhenLoadingCompletes && !Attributes.bWaitForManualStop
		&& FMath::IsNearlyEqual(Attributes.MinimumLoadingScreenDisplayTime, MinimumDisplaySeconds);
}

bool LBLoadingScreen::ArmForTravel()
{
	++GArmCount;
	GArmed = true;
	IGameMoviePlayer* MoviePlayer = (!GIsEditor && IsMoviePlayerEnabled()) ? GetMoviePlayer() : nullptr;
	if (!MoviePlayer)
	{
		UE_LOG(LogLB, Verbose, TEXT("Loading screen: no movie player here (editor or disabled); nothing to arm"));
		return false;
	}
	MoviePlayer->SetupLoadingScreen(MakeAttributes());
	++GHandedCount;
	return true;
}

void LBLoadingScreen::OnTravelFinished()
{
	if (!GArmed)
	{
		return;
	}
	GArmed = false;
	if (GIsEditor || !IsMoviePlayerEnabled())
	{
		return;
	}
	// The movie player is still showing the screen until the map's post-load wait ends; take the attributes back one tick later.
	FTSTicker::GetCoreTicker().AddTicker(TEXT("LBLoadingScreenClear"), 0.f, [](float)
	{
		if (!GArmed)
		{
			if (IGameMoviePlayer* MoviePlayer = GetMoviePlayer())
			{
				MoviePlayer->SetupLoadingScreen(FLoadingScreenAttributes());
			}
		}
		return false;
	});
}

bool LBLoadingScreen::IsArmed()
{
	return GArmed;
}

int32 LBLoadingScreen::GetArmCount()
{
	return GArmCount;
}

int32 LBLoadingScreen::GetHandedToMoviePlayerCount()
{
	return GHandedCount;
}
