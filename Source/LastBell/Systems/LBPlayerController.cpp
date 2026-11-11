#include "Systems/LBPlayerController.h"
#include "Blueprint/UserWidget.h"
#include "Engine/LocalPlayer.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "UI/LBMenuWidgetBase.h"
#include "UI/LBUISubsystem.h"
#include "LBLog.h"

void ALBPlayerController::BeginPlay()
{
	Super::BeginPlay();

	if (!IsLocalController())
	{
		return;
	}

	if (UEnhancedInputLocalPlayerSubsystem* Input = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer()))
	{
		// A context left active by a previous pawn (death, travel) must not leak into this one.
		if (InspectMappingContext)
		{
			Input->RemoveMappingContext(InspectMappingContext);
		}
		for (const TObjectPtr<UInputMappingContext>& Context : MappingContexts)
		{
			if (Context)
			{
				Input->AddMappingContext(Context, 0);
			}
		}
	}

	ULBUISubsystem* UI = ULocalPlayer::GetSubsystem<ULBUISubsystem>(GetLocalPlayer());
	if (HUDWidgetClass && HUDWidgetClass->IsChildOf(ULBMenuWidgetBase::StaticClass()) && UI)
	{
		// A menu map: the C++ main menu is the root screen of the UI stack, not a HUD.
		UI->PushScreen(ELBScreen::MainMenu, HUDWidgetClass.Get());
	}
	else if (HUDWidgetClass)
	{
		HUDWidget = CreateWidget<UUserWidget>(this, HUDWidgetClass);
		if (HUDWidget)
		{
			HUDWidget->AddToViewport();
			if (bHUDHidden)
			{
				HUDWidget->SetVisibility(ESlateVisibility::Collapsed);
			}
		}
	}
	else if (bMenuMode && UI && !UI->IsScreenOpen(ELBScreen::MainMenu))
	{
		// A menu map with no widget class assigned still gets the main menu.
		UI->PushScreen(ELBScreen::MainMenu);
	}
	else
	{
		UE_LOG(LogLB, Verbose, TEXT("%s has no HUDWidgetClass"), *GetName());
	}

	// Always apply this controller's mode: UI-only input from the previous map (main menu)
	// sets the viewport to ignore game input, and that survives travel (D-033).
	SetMenuMode(bMenuMode);
}

void ALBPlayerController::SetInspectionContextActive(bool bActive)
{
	if (!IsLocalController() || !InspectMappingContext)
	{
		return;
	}
	if (UEnhancedInputLocalPlayerSubsystem* Input = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer()))
	{
		if (bActive)
		{
			Input->AddMappingContext(InspectMappingContext, InspectMappingPriority);
		}
		else
		{
			Input->RemoveMappingContext(InspectMappingContext);
		}
	}
}

void ALBPlayerController::SetHUDHidden(bool bInHidden)
{
	bHUDHidden = bInHidden;
	if (HUDWidget)
	{
		HUDWidget->SetVisibility(bInHidden ? ESlateVisibility::Collapsed : ESlateVisibility::SelfHitTestInvisible);
	}
}

void ALBPlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();
	if (!IsLocalController())
	{
		return;
	}
	if (!PauseAction)
	{
		UE_LOG(LogLB, Verbose, TEXT("%s has no PauseAction (IA_Pause): the pause key is not bound"), *GetName());
		return;
	}
	if (UEnhancedInputComponent* Enhanced = Cast<UEnhancedInputComponent>(InputComponent))
	{
		Enhanced->BindAction(PauseAction, ETriggerEvent::Started, this, &ALBPlayerController::HandlePausePressed);
	}
}

void ALBPlayerController::HandlePausePressed(const FInputActionValue& Value)
{
	if (ULBUISubsystem* UI = ULocalPlayer::GetSubsystem<ULBUISubsystem>(GetLocalPlayer()))
	{
		UI->HandleBack();
	}
}

void ALBPlayerController::SetMenuMode(bool bInMenuMode)
{
	bMenuMode = bInMenuMode;
	if (!IsLocalController())
	{
		return;
	}
	// A screen on the UI stack, a menu map and plain play are all decided by the UI subsystem.
	if (ULBUISubsystem* UI = ULocalPlayer::GetSubsystem<ULBUISubsystem>(GetLocalPlayer()))
	{
		UI->SetMenuMode(bMenuMode);
		if (UI->HasAnyScreen() || !HUDWidget)
		{
			return;
		}
		// A menu map still using a UMG widget as its HUD (before P18-2): fall through to give that widget the focus.
	}
	if (bMenuMode)
	{
		bShowMouseCursor = true;
		FInputModeUIOnly Mode;
		// Only menu widgets take focus; focusing the gameplay HUD logs an engine error.
		if (HUDWidget && HUDWidget->IsFocusable())
		{
			Mode.SetWidgetToFocus(HUDWidget->TakeWidget());
		}
		Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
		SetInputMode(Mode);
	}
	else
	{
		bShowMouseCursor = false;
		SetInputMode(FInputModeGameOnly());
	}
}
