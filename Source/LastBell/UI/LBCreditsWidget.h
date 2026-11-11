#pragma once

#include "CoreMinimal.h"
#include "UI/LBMenuWidgetBase.h"
#include "UI/LBCreditsLayout.h"
#include "LBCreditsWidget.generated.h"

class UCanvasPanel;
class UVerticalBox;

/**
 * The Credits screen of the main menu (plan P18 section 1.1): the same roll as the ending, from DA_Cinematics.Credits, on a black field. It runs
 * once and closes itself; Back (Escape or a click) closes it early. The layout is the shared FLBCreditsRoll.
 */
UCLASS()
class LASTBELL_API ULBCreditsWidget : public ULBMenuWidgetBase
{
	GENERATED_BODY()

public:
	virtual ELBScreen GetScreenType() const override { return ELBScreen::Credits; }

	int32 GetCreditLineCountForTest() const { return Roll.LineCount; }
	float GetElapsedForTest() const { return Elapsed; }

protected:
	virtual void BuildScreen(UOverlay& RootOverlay) override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;
	virtual FReply NativeOnMouseButtonDown(const FGeometry& InGeometry, const FPointerEvent& InMouseEvent) override;

private:
	UPROPERTY(Transient)
	TObjectPtr<UCanvasPanel> Canvas;

	UPROPERTY(Transient)
	TObjectPtr<UVerticalBox> CreditsBox;

	FLBCreditsRoll Roll;
	float Elapsed = 0.f;
	float Duration = 40.f;
};
