#pragma once

#include "CoreMinimal.h"
#include "UI/LBMenuWidgetBase.h"
#include "LBMainMenuWidget.generated.h"

class UImage;
class UMediaPlayer;
class UMediaTexture;
class UTexture2D;

/**
 * The main menu (plan P18 section 1.1): the title and a text menu over a looping video of the monastery in the storm (DA_UIStyle MenuVideo; a slowly
 * drifting still when the video is unset or cannot play; plain dark when neither exists). Items: Continue (only when a save exists), New Game,
 * Settings, Credits, Quit. Escape does nothing here. The first-launch brightness screen is pushed on top by the UI subsystem when this screen is pushed.
 */
UCLASS()
class LASTBELL_API ULBMainMenuWidget : public ULBMenuWidgetBase
{
	GENERATED_BODY()

public:
	virtual ELBScreen GetScreenType() const override { return ELBScreen::MainMenu; }
	virtual bool HandleBack() override;

	/** The video is playing (false: the fallback still or the plain background). */
	bool IsVideoPlayingForTest() const;
	bool IsShowingFallbackStillForTest() const { return bShowingStill; }

protected:
	virtual void BuildScreen(UOverlay& RootOverlay) override;
	virtual void NativeConstruct() override;
	virtual void NativeDestruct() override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;

private:
	void StartBackground();
	void StopBackground();

	UPROPERTY(Transient)
	TObjectPtr<UImage> BackgroundImage;

	UPROPERTY(Transient)
	TObjectPtr<UMediaPlayer> MediaPlayer;

	UPROPERTY(Transient)
	TObjectPtr<UMediaTexture> MediaTexture;

	bool bShowingStill = false;
	float DriftClock = 0.f;
};
