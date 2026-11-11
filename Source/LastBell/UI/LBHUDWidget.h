#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "LBHUDWidget.generated.h"

class ALBCharacter;
class APawn;
class APlayerController;
class UBorder;
class UCanvasPanel;
class UHorizontalBox;
class UImage;
class ULBCandleComponent;
class ULBInspectableComponent;
class ULBInteractableComponent;
class ULBInspectionComponent;
class ULBInteractorComponent;
class ULBKeyIconWidget;
class ULBObjectiveSubsystem;
class UTextBlock;

/**
 * The gameplay HUD (plan P18 sections 1.5 and 1.6), built as a C++ tree like the other P18 widgets; it replaces WBP_HUD and WBP_Inspect. It shows:
 * - the crosshair dot, brighter and larger while something can be interacted with;
 * - the interact prompt: a ULBKeyIconWidget bound to the Interact action plus the interactable's prompt text (the denied text, e.g. "Locked", shows
 *   without the key because the press does nothing);
 * - the active objective (top left);
 * - "Lighting..." while the candle is being relit;
 * - the inspection overlay (vignette, name, body text, "Drag to rotate - [E] / [RMB] to close").
 * Fonts and colours come from DA_UIStyle (with none linked: the engine font and the built-in colours). High-contrast prompts draw the prompt white on a
 * dark plate with an outline. It binds the pawn's interactor, candle and inspection and the objective subsystem itself (retrying until the pawn exists),
 * so the player controller only has to create it.
 */
UCLASS()
class LASTBELL_API ULBHUDWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	/** Test and Blueprint-free access to what is shown. */
	FText GetPromptTextForTest() const;
	bool IsPromptVisibleForTest() const;
	bool IsPromptKeyVisibleForTest() const;
	const ULBKeyIconWidget* GetPromptKeyIconForTest() const { return PromptKey; }
	FText GetObjectiveTextForTest() const;
	bool IsObjectiveVisibleForTest() const;
	bool IsCandleTextVisibleForTest() const;
	bool IsInspectOverlayVisibleForTest() const;
	FText GetInspectNameForTest() const;
	FText GetInspectBodyForTest() const;
	bool IsCrosshairVisibleForTest() const;
	float GetCrosshairFocusAlphaForTest() const { return FocusAlpha; }
	bool IsPromptHighContrastForTest() const { return bPromptHighContrast; }
	bool IsBoundForTest() const { return bBound; }

	// The handlers are public so a test can drive them; the bound delegates call them.
	UFUNCTION()
	void HandlePossessedPawnChanged(APawn* OldPawn, APawn* NewPawn);

	UFUNCTION()
	void HandleFocusChanged(ULBInteractableComponent* NewFocus, FText Prompt);

	UFUNCTION()
	void HandleObjectiveChanged(int32 Index, FText Text);

	UFUNCTION()
	void HandleCandleStateChanged(bool bLit);

	UFUNCTION()
	void HandleRelightStarted();

	UFUNCTION()
	void HandleInspectBegin(ULBInspectableComponent* Inspectable);

	UFUNCTION()
	void HandleInspectEnd(bool bKept);

	/** Re-reads the style and the accessibility option (the settings screen calls it through OnUserSettingsChanged). */
	void ApplyLook();

protected:
	virtual void NativeOnInitialized() override;
	virtual void NativeConstruct() override;
	virtual void NativeDestruct() override;
	virtual void BeginDestroy() override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;

private:
	void BuildTree();
	void TryBind();
	void BindController();
	void UnbindController();
	void BindPawn(ALBCharacter* Pawn);
	void UnbindPawn();
	void BindObjective();
	void UnbindObjective();
	void BindSettings();
	void UnbindSettings();
	void RefreshPromptVisibility();
	void SetFocusTarget(bool bFocused);
	void HandleSettingsChanged();

	UPROPERTY(Transient)
	TObjectPtr<UCanvasPanel> Root;

	UPROPERTY(Transient)
	TObjectPtr<UImage> Crosshair;

	UPROPERTY(Transient)
	TObjectPtr<UBorder> PromptPlate;

	UPROPERTY(Transient)
	TObjectPtr<UHorizontalBox> PromptRow;

	UPROPERTY(Transient)
	TObjectPtr<ULBKeyIconWidget> PromptKey;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> PromptText;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> ObjectiveText;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> CandleText;

	UPROPERTY(Transient)
	TObjectPtr<UCanvasPanel> InspectOverlay;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> InspectName;

	UPROPERTY(Transient)
	TObjectPtr<UBorder> InspectBodyPanel;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> InspectBody;

	UPROPERTY(Transient)
	TObjectPtr<UHorizontalBox> InspectHint;

	TWeakObjectPtr<APlayerController> BoundController;
	TWeakObjectPtr<ALBCharacter> BoundPawn;
	TWeakObjectPtr<ULBInteractorComponent> BoundInteractor;
	TWeakObjectPtr<ULBCandleComponent> BoundCandle;
	TWeakObjectPtr<ULBInspectionComponent> BoundInspection;
	TWeakObjectPtr<ULBObjectiveSubsystem> BoundObjectives;

	FDelegateHandle SettingsHandle;
	bool bBound = false;
	bool bInspecting = false;
	bool bPromptUsable = true;
	bool bPromptHighContrast = false;
	float BindRetryClock = 100.f;
	float FocusAlpha = 0.f;
	float FocusTarget = 0.f;
};
