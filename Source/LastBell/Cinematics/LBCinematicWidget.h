#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Cinematics/LBCinematicTypes.h"
#include "LBCinematicWidget.generated.h"

class UCanvasPanel;
class UProgressBar;
class UTextBlock;
class UVerticalBox;

/**
 * The cinematic overlay (plan P17 section 2.9): story cards, the credits roll and the skip prompt. It builds its own widget tree in C++
 * (no WBP asset; Phase 18 restyles it) and draws no black of its own: black comes from the camera fade. The cinematic subsystem drives
 * it every tick (card opacity, credits progress, skip hold fraction), so the widget has no timers of its own.
 */
UCLASS()
class LASTBELL_API ULBCinematicWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	/** Shows a card's text in its style at this opacity 0..1 (the other style's text is hidden). */
	void SetCard(const FText& Text, ELBCineCardStyle Style, float Opacity);

	/** Hides the card and forgets its text. */
	void ClearCard();

	/** The skip prompt shows only while Skippable; Fraction (0..1) fills the bar under it. */
	void SetSkipState(bool bSkippable, float Fraction);

	void SetSkipPromptText(const FText& Text);

	/** Replaces the credits box with these lines, parked below the screen. */
	void BuildCredits(const TArray<FLBCreditLine>& Lines);

	/** Moves the credits box for a roll of TotalSeconds that has run ElapsedSeconds (the box travels its own height plus the viewport's). */
	void SetCreditsProgress(float ElapsedSeconds, float TotalSeconds);

	/** Removes the credits lines. */
	void ClearCredits();

	/** The text of the card now shown (empty when none): for tests. */
	FText GetCardTextForTest() const;
	float GetCardOpacityForTest() const;
	int32 GetCreditLineCountForTest() const { return CreditLineCount; }
	bool IsSkipPromptVisibleForTest() const;

protected:
	virtual void NativeOnInitialized() override;

private:
	void BuildTree();

	UPROPERTY(Transient)
	TObjectPtr<UCanvasPanel> Root;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> CardText;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> TitleText;

	UPROPERTY(Transient)
	TObjectPtr<UVerticalBox> CreditsBox;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> SkipText;

	UPROPERTY(Transient)
	TObjectPtr<UProgressBar> SkipBar;

	int32 CreditLineCount = 0;
	/** The style of the card now shown. */
	ELBCineCardStyle ShownStyle = ELBCineCardStyle::Line;
};
