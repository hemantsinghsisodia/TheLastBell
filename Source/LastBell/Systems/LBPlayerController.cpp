#include "Systems/LBPlayerController.h"
#include "Blueprint/UserWidget.h"
#include "Engine/LocalPlayer.h"
#include "EnhancedInputSubsystems.h"
#include "InputMappingContext.h"
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

	if (HUDWidgetClass)
	{
		HUDWidget = CreateWidget<UUserWidget>(this, HUDWidgetClass);
		if (HUDWidget)
		{
			HUDWidget->AddToViewport();
		}
	}
	else
	{
		UE_LOG(LogLB, Verbose, TEXT("%s has no HUDWidgetClass"), *GetName());
	}

	if (bMenuMode)
	{
		SetMenuMode(true);
	}
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

void ALBPlayerController::SetMenuMode(bool bInMenuMode)
{
	bMenuMode = bInMenuMode;
	if (!IsLocalController())
	{
		return;
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
