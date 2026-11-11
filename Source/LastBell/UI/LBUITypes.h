#pragma once

#include "CoreMinimal.h"
#include "InputCoreTypes.h"
#include "LBUITypes.generated.h"

/** The screens the UI subsystem's stack can hold (plan P18 section 2). */
UENUM(BlueprintType)
enum class ELBScreen : uint8
{
	None,
	MainMenu,
	Pause,
	Settings,
	Credits,
	Brightness,
	Confirm,
	Loading
};

/** The five tabs of the settings screen. */
UENUM(BlueprintType)
enum class ELBSettingsTab : uint8
{
	Graphics,
	Display,
	Audio,
	Controls,
	Accessibility
};

/** The scalability groups the Graphics tab can override one by one (after the overall preset). */
enum class ELBGraphicsGroup : uint8
{
	ViewDistance,
	AntiAliasing,
	Shadows,
	GlobalIllumination,
	Reflections,
	PostProcessing,
	Textures,
	Effects,
	Foliage,
	Shading,
	Count
};

/** The UI sounds (SCL_LB_UI; they keep playing while the game is paused). */
enum class ELBUISound : uint8
{
	Hover,
	Select,
	Back,
	SliderTick
};

/** The gameplay actions the player can rebind. Move is four separate keys (R-92). */
enum class ELBBindAction : uint8
{
	MoveForward,
	MoveBack,
	MoveLeft,
	MoveRight,
	Sprint,
	Crouch,
	Interact,
	Candle,
	Pause,
	Count
};

/** How a menu item behaves (the base widget's keyboard handling depends on it). */
enum class ELBMenuItemKind : uint8
{
	Button,
	Toggle,
	Slider,
	Choice,
	KeyBinding
};

/**
 * A modal question (Quit, New Game over a save, Return to menu, the display-mode keep dialog). Callbacks are plain functions; the widget
 * calls exactly one of them. A TimeoutSeconds above 0 counts down on the dialog and then answers as Cancel (the keep dialog reverts), or as
 * Confirm when bTimeoutConfirms is set.
 */
struct FLBConfirmRequest
{
	FText Title;
	FText Message;
	FText ConfirmLabel = NSLOCTEXT("LastBellUI", "Confirm", "Confirm");
	FText CancelLabel = NSLOCTEXT("LastBellUI", "Cancel", "Cancel");
	/** The confirm button is drawn in the danger colour and the cancel button is selected first. */
	bool bDanger = false;
	float TimeoutSeconds = 0.f;
	bool bTimeoutConfirms = false;
	TFunction<void()> OnConfirm;
	TFunction<void()> OnCancel;
};
