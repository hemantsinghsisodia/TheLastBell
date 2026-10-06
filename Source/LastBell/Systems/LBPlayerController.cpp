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

	SetMenuMode(bMenuMode);
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
		if (HUDWidget)
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
