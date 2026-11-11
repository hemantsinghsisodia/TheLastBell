#pragma once

#include "CoreMinimal.h"
#include "UI/LBMenuWidgetBase.h"
#include "UI/LBUILogic.h"
#include "LBConfirmWidget.generated.h"

class UBorder;
class UTextBlock;

/**
 * A modal question on top of the stack (plan P18 section 2): Quit, New Game over a save, Return to main menu, and the "Keep these settings?
 * Reverting in N s" dialog after a display-mode change (FLBConfirmRequest::TimeoutSeconds). Exactly one of the request's callbacks runs, after the
 * dialog has been removed. Back answers Cancel. A dangerous request selects Cancel first.
 */
UCLASS()
class LASTBELL_API ULBConfirmWidget : public ULBMenuWidgetBase
{
	GENERATED_BODY()

public:
	virtual ELBScreen GetScreenType() const override { return ELBScreen::Confirm; }
	virtual bool HandleBack() override;

	/** Sets the texts and callbacks and starts the countdown when the request has a timeout. */
	void Configure(const FLBConfirmRequest& InRequest);

	/** Test and flow access: answer as if the player pressed the button / the countdown ended. */
	void Confirm();
	void Cancel();

	bool HasAnswered() const { return bAnswered; }
	bool IsCountdownActive() const { return Timer.bActive; }
	int32 GetCountdownSecondsShown() const { return Timer.SecondsShown(); }
	FText GetMessageTextForTest() const;
	/** Ticks the countdown as if this much real time passed (the widget's own tick does this each frame). */
	void AdvanceCountdownForTest(float DeltaSeconds) { TickCountdown(DeltaSeconds); }

protected:
	virtual void BuildScreen(UOverlay& RootOverlay) override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;

private:
	void TickCountdown(float DeltaSeconds);
	void Answer(bool bConfirmed);
	void UpdateCountdownText();

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> TitleText;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> MessageText;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> CountdownText;

	FLBConfirmRequest Request;
	LBUILogic::FKeepTimer Timer;
	int32 ConfirmItem = INDEX_NONE;
	int32 CancelItem = INDEX_NONE;
	bool bAnswered = false;
};
