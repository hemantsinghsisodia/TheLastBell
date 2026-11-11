#pragma once

#include "CoreMinimal.h"
#include "UI/LBMenuWidgetBase.h"
#include "LBBrightnessWidget.generated.h"

class UImage;

/**
 * The brightness (gamma) calibration screen (plan P18 section 1.2): a symbol "barely visible" on a dark field, a slider and Confirm. Shown on the
 * first launch before the main menu (Back is ignored there), and from Settings > Display (Back restores the gamma it had on opening).
 * Gamma applies live; Confirm saves it and marks ULBUserSettings::bBrightnessCalibrated.
 */
UCLASS()
class LASTBELL_API ULBBrightnessWidget : public ULBMenuWidgetBase
{
	GENERATED_BODY()

public:
	virtual ELBScreen GetScreenType() const override { return ELBScreen::Brightness; }
	virtual bool HandleBack() override;

	/** Saves the gamma, marks the screen as seen and closes it. */
	void ConfirmBrightness();

	float GetInitialGammaForTest() const { return InitialGamma; }

protected:
	virtual void BuildScreen(UOverlay& RootOverlay) override;

private:
	UPROPERTY(Transient)
	TObjectPtr<UImage> Symbol;

	int32 SliderItem = INDEX_NONE;
	float InitialGamma = 2.2f;
};
