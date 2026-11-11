#pragma once

#include "CoreMinimal.h"
#include "Subsystems/LocalPlayerSubsystem.h"
#include "UI/LBUITypes.h"
#include "LBUISubsystem.generated.h"

class APlayerController;
class ULBMenuWidgetBase;
class UUserWidget;

/** Fires when the UI pauses or unpauses the game. */
DECLARE_MULTICAST_DELEGATE_OneParam(FLBPauseChangedSignature, bool /*bPaused*/);

/**
 * The UI director of one local player (plan P18 section 2): the screen stack, the input mode and cursor, pause, confirm dialogs, the
 * first-launch brightness gate, Escape routing and the UI sounds. Menu screens are C++ widget trees (ULBMenuWidgetBase) styled from DA_UIStyle.
 *
 * Pause (D-128): OpenPause sets the world paused and pushes the Pause screen; ClosePause pops everything and unpauses. The world, the Warden,
 * the storm, the audio schedule, the bell and the cinematics all freeze with the world (they are not tickable when paused); only UI sounds play.
 * Pause is refused on the main menu, during a level travel, a death, a checkpoint restore and when something else paused the game.
 *
 * NEVER Live Code LBUISubsystem.cpp: it holds file-static state.
 */
UCLASS()
class LASTBELL_API ULBUISubsystem : public ULocalPlayerSubsystem
{
	GENERATED_BODY()

public:
	/** The first local player's UI subsystem for this world context, or null (dedicated server, no local player). */
	static ULBUISubsystem* Get(const UObject* WorldContextObject);

	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	// ---- The screen stack ----

	/** Creates the screen's widget (the class from the screen type, or the override), adds it to the viewport and puts it on top. Null on failure. */
	ULBMenuWidgetBase* PushScreen(ELBScreen Screen, TSubclassOf<ULBMenuWidgetBase> ClassOverride = nullptr);

	/** Removes the top screen. The one below becomes the top again. */
	void PopScreen();

	/** Removes every screen above and including the first of this type; nothing if it is not open. */
	void PopToAndIncluding(ELBScreen Screen);

	/** Removes all screens and restores the input mode of the world. */
	void ClearScreens();

	ELBScreen GetTopScreen() const;
	ULBMenuWidgetBase* GetTopWidget() const;
	ULBMenuWidgetBase* FindScreen(ELBScreen Screen) const;
	bool IsScreenOpen(ELBScreen Screen) const { return FindScreen(Screen) != nullptr; }
	int32 GetScreenCount() const { return Stack.Num(); }
	bool HasAnyScreen() const { return !Stack.IsEmpty(); }

	// ---- Flow ----

	/**
	 * Escape / the Pause action. The top screen handles Back; with none open: an inspection closes first; otherwise the pause menu opens when it
	 * may. Returns true when the press was used (even if the pause was refused, so Escape never leaks into gameplay).
	 */
	bool HandleBack();

	/** The pause menu may open now. Why (when given) says which rule refused. */
	bool CanOpenPause(FString* OutWhy = nullptr) const;

	bool OpenPause();
	/** Closes every screen and unpauses. Safe when not paused. */
	void ClosePause();
	bool IsPauseOpen() const { return bPausedByUI; }

	/** A modal question on top of the stack. */
	ULBMenuWidgetBase* ShowConfirm(const FLBConfirmRequest& Request);

	/** A short notice on top of the stack (OK / Back both close it). */
	ULBMenuWidgetBase* ShowMessage(const FText& Title, const FText& Message);

	void OpenSettings();
	void OpenCredits();
	/** bFirstLaunch: Back is ignored and Confirm marks the brightness as calibrated. */
	void OpenBrightness(bool bFirstLaunch);

	/** Main menu actions. */
	void StartNewGameFlow();
	void ContinueFlow();
	/** Pause menu actions: unpause, then travel to the main menu (the save is kept). */
	void ReturnToMainMenuFlow();
	void QuitGameFlow();

	/** The main menu was shown: pushes the brightness screen first when it was never calibrated. Returns true if it did. */
	bool ApplyBrightnessGate();
	/** True while the brightness screen is the first-launch one (Back is ignored). */
	bool IsFirstLaunchBrightnessOpen() const;

	FLBPauseChangedSignature OnPauseChanged;

	// ---- Input mode and cursor ----

	/** Menu maps: visible cursor and UI-only input; otherwise game-only input. A screen on the stack always wins. */
	void SetMenuMode(bool bInMenuMode);
	void RefreshInputMode();

	// ---- Sounds ----
	void PlaySound(ELBUISound Sound) const;
	/** The sounds played so far this session (for tests: counts of requests made, whether or not an audio device or asset exists). */
	int32 GetSoundRequestCount(ELBUISound Sound) const;

	// ---- Window focus ----
	/** The window lost (false) or gained (true) focus: losing it during play opens the pause menu (standalone game only). */
	void HandleApplicationActivation(bool bActive);

	/** Test hook: the cinematic skip hold is cancelled through this when the pause opens or the window loses focus. */
	void CancelSkipHold() const;

	// ---- Test hooks ----
	/** Lets a test open the pause outside a standalone game (the editor never pauses on focus loss). */
	bool bPauseOnFocusLossInEditor = false;

private:
	APlayerController* GetPC() const;
	UWorld* GetUIWorld() const;
	void RemoveWidgetAt(int32 Index);
	/** After a removal: shows the new top screen, or unpauses and restores the input mode when none is left. */
	void AfterRemoval();
	void PruneStale();
	ULBMenuWidgetBase* FindScreenNoPrune(ELBScreen Screen) const;
	void SetWorldPaused(bool bPaused);

	/** Bottom first. The type of a screen is its widget's GetScreenType(). */
	UPROPERTY(Transient)
	TArray<TObjectPtr<ULBMenuWidgetBase>> Stack;

	bool bPausedByUI = false;
	bool bMenuModeWanted = false;
	bool bFirstLaunchBrightness = false;
	int32 SoundRequests[4] = {};
	FDelegateHandle ActivationHandle;
};
