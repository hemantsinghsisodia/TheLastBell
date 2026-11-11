#pragma once

#include "CoreMinimal.h"
#include "UI/LBMenuWidgetBase.h"
#include "LBPauseWidget.generated.h"

/**
 * The pause menu (plan P18 section 1.3): the game behind darkens to 60 % with a 6 px gaussian blur, and a short text menu: Resume, Settings,
 * Return to main menu (confirm), Quit to desktop (confirm). Back (Escape) resumes. The UI subsystem pauses the world; this screen only asks it to.
 */
UCLASS()
class LASTBELL_API ULBPauseWidget : public ULBMenuWidgetBase
{
	GENERATED_BODY()

public:
	virtual ELBScreen GetScreenType() const override { return ELBScreen::Pause; }
	virtual bool HandleBack() override;

protected:
	virtual void BuildScreen(UOverlay& RootOverlay) override;
};
