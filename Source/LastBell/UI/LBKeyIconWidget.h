#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "InputCoreTypes.h"
#include "UI/LBUITypes.h"
#include "LBKeyIconWidget.generated.h"

class UBorder;
class UImage;
class USizeBox;
class UTextBlock;
class UInputAction;

/**
 * One key shown as a glyph (plan P18 section 2): the key's icon from DA_UIStyle when it has one, otherwise a rounded key-cap with the key's name,
 * so a missing icon set still reads. It can show a fixed key or follow the current binding of an action (it refreshes when the player rebinds).
 * The high-contrast accessibility option draws the cap in white on a dark plate with an outline.
 */
UCLASS()
class LASTBELL_API ULBKeyIconWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	/** Shows this key and stops following any action. */
	void SetKey(const FKey& Key);

	/** Follows the current binding of this gameplay action (Interact for the HUD prompt and the skip prompt). */
	void SetBoundAction(ELBBindAction Action);

	/** Follows the keys mapped to an Input Action in the player's live mappings. */
	void SetBoundInputAction(const UInputAction* Action);

	/** The glyph's height in Slate units (at 1080p). */
	void SetGlyphHeight(float Height);

	/** Re-reads the binding, the style and the accessibility option. */
	void Refresh();

	FKey GetKey() const { return ShownKey; }
	/** True when a style icon is shown (false: the text key-cap). */
	bool IsShowingIconForTest() const { return bShowingIcon; }
	FText GetCapTextForTest() const;
	bool IsHighContrastForTest() const { return bShownHighContrast; }

protected:
	virtual void NativeOnInitialized() override;
	virtual void NativeConstruct() override;
	virtual void NativeDestruct() override;

private:
	void BuildTree();
	const ULocalPlayer* ResolveLocalPlayer() const;
	void HandleExternalChange();

	UPROPERTY(Transient)
	TObjectPtr<USizeBox> SizeBox;

	UPROPERTY(Transient)
	TObjectPtr<UImage> Icon;

	UPROPERTY(Transient)
	TObjectPtr<UBorder> Cap;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> CapText;

	FKey ShownKey = EKeys::Invalid;
	ELBBindAction FollowedAction = ELBBindAction::Count;
	TWeakObjectPtr<UInputAction> FollowedInputAction;
	float GlyphHeight = 40.f;
	bool bShowingIcon = false;
	bool bShownHighContrast = false;
	FDelegateHandle BindingsHandle;
	FDelegateHandle SettingsHandle;
};
