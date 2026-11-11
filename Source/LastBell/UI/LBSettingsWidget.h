#pragma once

#include "CoreMinimal.h"
#include "UI/LBMenuWidgetBase.h"
#include "UI/LBGraphicsSettings.h"
#include "LBSettingsWidget.generated.h"

class UTextBlock;
class UVerticalBox;
class UHorizontalBox;

/**
 * The settings screen (plan P18 section 1.4): five tabs, each a panel of rows built by the menu base.
 * Graphics (preset, ten groups, resolution scale) and Display (window mode, resolution, VSync, frame cap, brightness) use Apply / Revert; a display
 * mode change then asks "Keep these settings? Reverting in 15 s". Audio, Controls (sensitivity, invert Y, head bob, key rebinding) and Accessibility
 * (FOV, motion blur, film grain, high-contrast prompts, the brightness screen at next launch) apply and save at once. Tab / Q / E / PageUp / PageDown
 * switch tabs. Back discards unapplied graphics changes.
 */
UCLASS()
class LASTBELL_API ULBSettingsWidget : public ULBMenuWidgetBase
{
	GENERATED_BODY()

public:
	virtual ELBScreen GetScreenType() const override { return ELBScreen::Settings; }
	virtual bool HandleBack() override;

	void SwitchTab(ELBSettingsTab Tab);
	ELBSettingsTab GetActiveTab() const { return ActiveTab; }

	/** Applies the pending graphics and display changes (the Apply button). Shows the keep dialog when the display mode changed. */
	void ApplyGraphics();
	/** Puts the pending changes back to the last applied state (the Revert button). */
	void RevertGraphics();

	/** Resets the controls settings and the key bindings (the Reset to defaults button). */
	void ResetControls();

	// ---- Test surface ----
	/** The item index of the key row of this action in the Controls tab, or INDEX_NONE. */
	int32 FindKeyItem(ELBBindAction Action) const;
	/** Does what capturing a key press on that row does. */
	void CaptureKeyForTest(ELBBindAction Action, const FKey& Key);
	FText GetStatusTextForTest() const;
	/** The row index of the preset choice (Graphics tab) or INDEX_NONE. */
	int32 GetPresetItemForTest() const { return PresetItem; }
	int32 GetGroupItemForTest(ELBGraphicsGroup Group) const { return GroupItems.IsValidIndex(static_cast<int32>(Group)) ? GroupItems[static_cast<int32>(Group)] : INDEX_NONE; }
	const FLBGraphicsSnapshot& GetBaselineForTest() const { return GfxBaseline; }
	/** Does what choosing this overall preset in the Graphics tab does (sets every group, refreshes the rows). */
	void SetPresetForTest(int32 Preset) { SetChoiceIndex(PresetItem, Preset, /*bNotify*/ true); }

protected:
	virtual void BuildScreen(UOverlay& RootOverlay) override;
	virtual bool OnKeyCaptured(int32 ItemIndex, const FKey& Key) override;
	virtual FReply NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent) override;

private:
	void RebuildTab();
	void BuildGraphicsTab();
	void BuildDisplayTab();
	void BuildAudioTab();
	void BuildControlsTab();
	void BuildAccessibilityTab();
	void AddFooter(bool bApplyRevert);
	void RefreshTabBar();
	void RefreshGroupRows();
	void UpdatePresetItem();
	void SetStatus(const FText& Text);
	void AddCaption(const FText& Text);

	UPROPERTY(Transient)
	TObjectPtr<UVerticalBox> TabContent;

	UPROPERTY(Transient)
	TObjectPtr<UHorizontalBox> TabBar;

	UPROPERTY(Transient)
	TArray<TObjectPtr<ULBMenuButton>> TabButtons;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UTextBlock>> TabLabels;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> StatusText;

	ELBSettingsTab ActiveTab = ELBSettingsTab::Graphics;
	FLBGraphicsSnapshot GfxBaseline;
	TArray<int32> GroupItems;
	TArray<FIntPoint> ResolutionOptions;
	int32 PresetItem = INDEX_NONE;
};
