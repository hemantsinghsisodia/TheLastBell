#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Components/Button.h"
#include "Components/Slider.h"
#include "UI/LBUITypes.h"
#include "UI/LBUIStyle.h"
#include "LBMenuWidgetBase.generated.h"

class UBorder;
class UImage;
class UOverlay;
class UTextBlock;
class UVerticalBox;
class UHorizontalBox;
class ULBKeyIconWidget;
class ULBUISubsystem;

/** A transparent, non-focusable button: the clickable and hoverable shell of a menu row (focus stays on the screen so the keys keep working). */
UCLASS()
class LASTBELL_API ULBMenuButton : public UButton
{
	GENERATED_BODY()

public:
	ULBMenuButton();

	/** Called on a click and on the pointer entering the row. Native functions: the dynamic delegates cannot say which row they belong to. */
	TFunction<void()> OnClickNative;
	TFunction<void()> OnHoverNative;

protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;
};

/** Receives a USlider's dynamic delegate calls and forwards them to native functions (one proxy per slider, so a call knows its row). */
UCLASS()
class LASTBELL_API ULBSliderProxy : public UObject
{
	GENERATED_BODY()

public:
	TFunction<void(float)> OnValueNative;
	TFunction<void()> OnCaptureEndNative;

	UFUNCTION()
	void HandleValueChanged(float NewValue);

	UFUNCTION()
	void HandleCaptureEnd();
};

/** One row of a menu: what it is, how it looks and what it does. Rows are built by the base widget's Add*Item helpers. */
USTRUCT()
struct FLBMenuItem
{
	GENERATED_BODY()

	UPROPERTY(Transient)
	TObjectPtr<ULBMenuButton> Button;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> Label;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> ValueText;

	UPROPERTY(Transient)
	TObjectPtr<UImage> Marker;

	UPROPERTY(Transient)
	TObjectPtr<USlider> Slider;

	UPROPERTY(Transient)
	TObjectPtr<ULBSliderProxy> SliderProxy;

	UPROPERTY(Transient)
	TObjectPtr<ULBKeyIconWidget> KeyIcon;

	ELBMenuItemKind Kind = ELBMenuItemKind::Button;
	/** KeyBinding rows: the action this row rebinds. */
	ELBBindAction BindAction = ELBBindAction::Count;
	bool bEnabled = true;
	bool bDanger = false;

	// Slider
	float Value = 0.f;
	/** The value last reported as final (released or keyboard). */
	float FinalValue = 0.f;
	float Min = 0.f;
	float Max = 1.f;
	float Step = 0.05f;
	// Choice and toggle
	int32 Index = 0;
	TArray<FText> Options;
	/**
	 * Choice rows: how many of the first Options can be stepped to. Options beyond that are display-only states (the preset row's "Custom"):
	 * stepping forward from one goes to option 0, stepping back to the last selectable option. -1 = all of them.
	 */
	int32 SelectableCount = -1;

	TFunction<void()> OnActivate;
	TFunction<void(float /*Value*/, bool /*bFinal*/)> OnSlide;
	TFunction<void(int32 /*NewIndex*/)> OnChoose;
	TFunction<FText(float)> FormatValue;
};

/**
 * The base of every menu screen (plan P18 section 2). Its widget tree is built in C++ in NativeOnInitialized, like ULBCinematicWidget (no WBP).
 * It owns the item list with keyboard focus (Up/Down select, Left/Right adjust, Enter activates, Escape goes back), mouse hover and click, the
 * candle-flicker highlight of the selected item, the UI sounds and the style access. A screen is pushed on the ULBUISubsystem stack.
 */
UCLASS()
class LASTBELL_API ULBMenuWidgetBase : public UUserWidget
{
	GENERATED_BODY()

public:
	virtual ELBScreen GetScreenType() const { return ELBScreen::None; }

	/** Back (Escape). Returns true when the screen handled it. The default pops this screen. */
	virtual bool HandleBack();

	/** The screen became the top of the stack (pushed, or the one above was popped). */
	virtual void OnScreenShown() {}

	/** Another screen was pushed on top of this one. */
	virtual void OnScreenCovered() {}

	/** The style in use (never null). */
	const ULBUIStyle& GetStyle() const;

	ULBUISubsystem* GetUI() const;

	// ---- Items (also the test surface) ----
	int32 GetItemCount() const { return Items.Num(); }
	int32 GetSelectedIndex() const { return SelectedIndex; }
	const FLBMenuItem* GetItem(int32 Index) const { return Items.IsValidIndex(Index) ? &Items[Index] : nullptr; }
	FText GetItemLabel(int32 Index) const;
	bool IsItemEnabled(int32 Index) const { return Items.IsValidIndex(Index) && Items[Index].bEnabled; }
	/** Finds the first item whose label text equals this one; INDEX_NONE if none. */
	int32 FindItemByLabel(const FText& Label) const;

	void SelectItem(int32 Index, bool bPlaySound = true);
	/** Same as pressing Enter on the item. */
	void ActivateItem(int32 Index);
	/** Same as pressing Left (-1) or Right (+1) on the item. */
	void AdjustItem(int32 Index, int32 Direction);
	/** Moves the selection to the next enabled item in this direction (wraps). */
	void MoveSelection(int32 Direction);

protected:
	virtual void NativeOnInitialized() override;
	virtual void NativeConstruct() override;
	virtual void NativeDestruct() override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;
	virtual FReply NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent) override;
	virtual FReply NativeOnPreviewMouseButtonDown(const FGeometry& InGeometry, const FPointerEvent& InMouseEvent) override;

	/** Builds the screen's own widgets under the root overlay and registers its items. Called once. */
	virtual void BuildScreen(UOverlay& RootOverlay) {}

	/** A key was captured by a key-binding row. Return true if the capture is finished (false: keep capturing). */
	virtual bool OnKeyCaptured(int32 ItemIndex, const FKey& Key) { return true; }

	// ---- Builders: each adds a row to Parent and returns its item index ----
	int32 AddButtonItem(UPanelWidget& Parent, const FText& Label, TFunction<void()> OnActivate, bool bDanger = false);
	int32 AddToggleItem(UPanelWidget& Parent, const FText& Label, bool bInitial, TFunction<void(bool)> OnChanged);
	int32 AddChoiceItem(UPanelWidget& Parent, const FText& Label, const TArray<FText>& Options, int32 Initial, TFunction<void(int32)> OnChanged, int32 SelectableCount = -1);
	int32 AddSliderItem(UPanelWidget& Parent, const FText& Label, float Min, float Max, float Step, float Initial, TFunction<FText(float)> Format, TFunction<void(float, bool)> OnSlide);
	/** A row showing a key icon; activating it starts capturing the next key press (OnKeyCaptured). */
	int32 AddKeyItem(UPanelWidget& Parent, const FText& Label, ELBBindAction Action);

	// ---- Updating rows ----
	void SetChoiceIndex(int32 ItemIndex, int32 NewIndex, bool bNotify);
	void SetToggleValue(int32 ItemIndex, bool bOn, bool bNotify);
	void SetSliderValue(int32 ItemIndex, float NewValue, bool bNotify);
	void SetItemEnabled(int32 ItemIndex, bool bEnabled);
	void SetItemLabel(int32 ItemIndex, const FText& Label);
	void SetItemDanger(int32 ItemIndex, bool bDanger);
	void RefreshKeyItem(int32 ItemIndex);

	/** Removes all rows (the caller clears the container panel). */
	void ClearItems();

	// ---- Capture ----
	void BeginKeyCapture(int32 ItemIndex);
	void EndKeyCapture();
	bool IsCapturingKey() const { return CaptureItem != INDEX_NONE; }

	// ---- Helpers for derived screens ----
	UTextBlock* MakeLabel(const FText& Text, ELBFontWeight Weight, int32 Size, const FLinearColor& Colour, ETextJustify::Type Justify = ETextJustify::Left);
	void PlaySound(ELBUISound Sound) const;

	UPROPERTY(Transient)
	TObjectPtr<UOverlay> Root;

	/** The font size of the rows the Add*Item helpers build (0 = the style's item size). */
	int32 RowTextSize = 0;

	/** The full-screen dimming plate the derived screens may use. */
	UPROPERTY(Transient)
	TObjectPtr<UImage> Backdrop;

private:
	void BuildBase();
	void ApplyItemVisuals(int32 Index, float Flicker);
	void UpdateValueText(int32 Index);
	void HandleSliderMoved(int32 Index, float NewValue);
	void HandleSliderReleased(int32 Index);
	void HandleRowClicked(int32 Index);
	void HandleRowHovered(int32 Index);
	FLBMenuItem& NewRow(UPanelWidget& Parent, ELBMenuItemKind Kind, const FText& Label, UHorizontalBox*& OutRow);

	UPROPERTY(Transient)
	TArray<FLBMenuItem> Items;

	int32 SelectedIndex = INDEX_NONE;
	int32 CaptureItem = INDEX_NONE;
	float FlickerClock = 0.f;
	float LastSliderTickValue = TNumericLimits<float>::Lowest();
	bool bBuilt = false;
	/** Slider events caused by code (setting the value) must not call the item's handler. */
	bool bSuppressSliderEvents = false;
};
