#include "UI/LBUISubsystem.h"
#include "Blueprint/UserWidget.h"
#include "Character/LBCharacter.h"
#include "Character/LBInspectionComponent.h"
#include "Cinematics/LBCinematicSubsystem.h"
#include "Engine/GameInstance.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Save/LBSaveSubsystem.h"
#include "Sound/SoundBase.h"
#include "Systems/LBPlayerController.h"
#include "Systems/LBUserSettings.h"
#include "UI/LBBrightnessWidget.h"
#include "UI/LBConfirmWidget.h"
#include "UI/LBCreditsWidget.h"
#include "UI/LBMainMenuWidget.h"
#include "UI/LBMenuWidgetBase.h"
#include "UI/LBPauseWidget.h"
#include "UI/LBSettingsWidget.h"
#include "UI/LBUIStyle.h"
#include "LBLog.h"

namespace
{
	constexpr int32 BaseZOrder = 500;
	constexpr int32 ZOrderPerScreen = 10;

	TSubclassOf<ULBMenuWidgetBase> DefaultClassFor(ELBScreen Screen)
	{
		switch (Screen)
		{
		case ELBScreen::MainMenu: return ULBMainMenuWidget::StaticClass();
		case ELBScreen::Pause: return ULBPauseWidget::StaticClass();
		case ELBScreen::Settings: return ULBSettingsWidget::StaticClass();
		case ELBScreen::Credits: return ULBCreditsWidget::StaticClass();
		case ELBScreen::Brightness: return ULBBrightnessWidget::StaticClass();
		case ELBScreen::Confirm: return ULBConfirmWidget::StaticClass();
		default: return nullptr;
		}
	}
}

ULBUISubsystem* ULBUISubsystem::Get(const UObject* WorldContextObject)
{
	const UWorld* World = WorldContextObject ? WorldContextObject->GetWorld() : nullptr;
	const ULocalPlayer* LocalPlayer = World ? World->GetFirstLocalPlayerFromController() : nullptr;
	if (!LocalPlayer && World)
	{
		if (const UGameInstance* GameInstance = World->GetGameInstance())
		{
			LocalPlayer = GameInstance->GetFirstGamePlayer();
		}
	}
	return LocalPlayer ? LocalPlayer->GetSubsystem<ULBUISubsystem>() : nullptr;
}

void ULBUISubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	if (FSlateApplication::IsInitialized())
	{
		ActivationHandle = FSlateApplication::Get().OnApplicationActivationStateChanged().AddUObject(this, &ULBUISubsystem::HandleApplicationActivation);
	}
}

void ULBUISubsystem::Deinitialize()
{
	if (FSlateApplication::IsInitialized() && ActivationHandle.IsValid())
	{
		FSlateApplication::Get().OnApplicationActivationStateChanged().Remove(ActivationHandle);
	}
	ActivationHandle.Reset();
	for (ULBMenuWidgetBase* Widget : Stack)
	{
		if (Widget)
		{
			Widget->RemoveFromParent();
		}
	}
	Stack.Reset();
	Super::Deinitialize();
}

APlayerController* ULBUISubsystem::GetPC() const
{
	const ULocalPlayer* LocalPlayer = GetLocalPlayer();
	return LocalPlayer ? LocalPlayer->GetPlayerController(GetUIWorld()) : nullptr;
}

UWorld* ULBUISubsystem::GetUIWorld() const
{
	const ULocalPlayer* LocalPlayer = GetLocalPlayer();
	return LocalPlayer ? LocalPlayer->GetWorld() : nullptr;
}

// ---------------------------------------------------------------------------------------------------------------------
// Stack
// ---------------------------------------------------------------------------------------------------------------------

void ULBUISubsystem::PruneStale()
{
	// A level travel destroys the viewport widgets: forget the screens that went with the old world.
	const UWorld* CurrentWorld = GetUIWorld();
	for (int32 Index = Stack.Num() - 1; Index >= 0; --Index)
	{
		const ULBMenuWidgetBase* Widget = Stack[Index];
		if (!IsValid(Widget) || !Widget->IsInViewport() || Widget->GetWorld() != CurrentWorld)
		{
			Stack.RemoveAt(Index);
		}
	}
	if (bPausedByUI)
	{
		const UWorld* World = GetUIWorld();
		if (!World || !World->IsPaused())
		{
			bPausedByUI = false;
		}
	}
}

ULBMenuWidgetBase* ULBUISubsystem::FindScreenNoPrune(ELBScreen Screen) const
{
	for (int32 Index = Stack.Num() - 1; Index >= 0; --Index)
	{
		if (Stack[Index] && Stack[Index]->GetScreenType() == Screen)
		{
			return Stack[Index];
		}
	}
	return nullptr;
}

ELBScreen ULBUISubsystem::GetTopScreen() const
{
	const ULBMenuWidgetBase* Top = GetTopWidget();
	return Top ? Top->GetScreenType() : ELBScreen::None;
}

ULBMenuWidgetBase* ULBUISubsystem::GetTopWidget() const
{
	const_cast<ULBUISubsystem*>(this)->PruneStale();
	return Stack.IsEmpty() ? nullptr : Stack.Last().Get();
}

ULBMenuWidgetBase* ULBUISubsystem::FindScreen(ELBScreen Screen) const
{
	const_cast<ULBUISubsystem*>(this)->PruneStale();
	return FindScreenNoPrune(Screen);
}

ULBMenuWidgetBase* ULBUISubsystem::PushScreen(ELBScreen Screen, TSubclassOf<ULBMenuWidgetBase> ClassOverride)
{
	PruneStale();
	APlayerController* PC = GetPC();
	const TSubclassOf<ULBMenuWidgetBase> Class = ClassOverride ? ClassOverride : DefaultClassFor(Screen);
	if (!PC || !Class)
	{
		UE_LOG(LogLB, Warning, TEXT("UI: cannot push screen %d (controller %s, class %s)"), static_cast<int32>(Screen), *GetNameSafe(PC), *GetNameSafe(Class));
		return nullptr;
	}
	ULBMenuWidgetBase* Widget = CreateWidget<ULBMenuWidgetBase>(PC, Class);
	if (!Widget)
	{
		UE_LOG(LogLB, Warning, TEXT("UI: could not create the widget for screen %d"), static_cast<int32>(Screen));
		return nullptr;
	}

	if (ULBMenuWidgetBase* Below = Stack.IsEmpty() ? nullptr : Stack.Last().Get())
	{
		Below->OnScreenCovered();
		// A dialog overlays the screen below; any other screen replaces it on show.
		if (Screen != ELBScreen::Confirm)
		{
			Below->SetVisibility(ESlateVisibility::Collapsed);
		}
		else
		{
			Below->SetVisibility(ESlateVisibility::HitTestInvisible);
		}
	}

	Stack.Add(Widget);
	Widget->AddToViewport(BaseZOrder + ZOrderPerScreen * Stack.Num());
	Widget->SetVisibility(ESlateVisibility::Visible);
	RefreshInputMode();
	Widget->OnScreenShown();

	if (Screen == ELBScreen::MainMenu)
	{
		ApplyBrightnessGate();
	}
	return Widget;
}

void ULBUISubsystem::RemoveWidgetAt(int32 Index)
{
	if (!Stack.IsValidIndex(Index))
	{
		return;
	}
	ULBMenuWidgetBase* Widget = Stack[Index];
	Stack.RemoveAt(Index);
	if (Widget)
	{
		if (Widget->GetScreenType() == ELBScreen::Brightness)
		{
			bFirstLaunchBrightness = false;
		}
		Widget->RemoveFromParent();
	}
}

void ULBUISubsystem::AfterRemoval()
{
	if (ULBMenuWidgetBase* Top = Stack.IsEmpty() ? nullptr : Stack.Last().Get())
	{
		Top->SetVisibility(ESlateVisibility::Visible);
		RefreshInputMode();
		Top->OnScreenShown();
		return;
	}
	if (bPausedByUI)
	{
		SetWorldPaused(false);
	}
	RefreshInputMode();
}

void ULBUISubsystem::PopScreen()
{
	PruneStale();
	if (Stack.IsEmpty())
	{
		return;
	}
	RemoveWidgetAt(Stack.Num() - 1);
	AfterRemoval();
}

void ULBUISubsystem::PopToAndIncluding(ELBScreen Screen)
{
	PruneStale();
	int32 Found = INDEX_NONE;
	for (int32 Index = Stack.Num() - 1; Index >= 0; --Index)
	{
		if (Stack[Index] && Stack[Index]->GetScreenType() == Screen)
		{
			Found = Index;
			break;
		}
	}
	if (Found == INDEX_NONE)
	{
		return;
	}
	while (Stack.Num() > Found)
	{
		RemoveWidgetAt(Stack.Num() - 1);
	}
	AfterRemoval();
}

void ULBUISubsystem::ClearScreens()
{
	PruneStale();
	while (!Stack.IsEmpty())
	{
		RemoveWidgetAt(Stack.Num() - 1);
	}
	AfterRemoval();
}

// ---------------------------------------------------------------------------------------------------------------------
// Pause
// ---------------------------------------------------------------------------------------------------------------------

void ULBUISubsystem::SetWorldPaused(bool bPaused)
{
	UWorld* World = GetUIWorld();
	if (bPausedByUI == bPaused && (!World || World->IsPaused() == bPaused))
	{
		return;
	}
	bPausedByUI = bPaused;
	if (World)
	{
		UGameplayStatics::SetGamePaused(World, bPaused);
	}
	OnPauseChanged.Broadcast(bPaused);
}

bool ULBUISubsystem::CanOpenPause(FString* OutWhy) const
{
	auto Refuse = [OutWhy](const TCHAR* Why)
	{
		if (OutWhy)
		{
			*OutWhy = Why;
		}
		return false;
	};

	const UWorld* World = GetUIWorld();
	const APlayerController* PC = GetPC();
	if (!World || !PC || !World->IsGameWorld())
	{
		return Refuse(TEXT("no game world or controller"));
	}
	if (bPausedByUI)
	{
		return Refuse(TEXT("already paused by the UI"));
	}
	if (World->IsPaused())
	{
		return Refuse(TEXT("the game is paused by something else"));
	}
	const ALBPlayerController* LBPC = Cast<ALBPlayerController>(PC);
	if ((LBPC && LBPC->bMenuMode) || IsScreenOpen(ELBScreen::MainMenu))
	{
		return Refuse(TEXT("on the main menu"));
	}
	if (const ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(World))
	{
		if (Save->IsTravelPending())
		{
			return Refuse(TEXT("a level travel is pending"));
		}
		if (Save->HasPendingRestore())
		{
			return Refuse(TEXT("a checkpoint is loading"));
		}
	}
	const ALBCharacter* Character = Cast<ALBCharacter>(PC->GetPawn());
	if (!Character)
	{
		return Refuse(TEXT("no player character"));
	}
	if (Character->IsDead())
	{
		return Refuse(TEXT("the player is dead"));
	}
	return true;
}

bool ULBUISubsystem::OpenPause()
{
	FString Why;
	if (!CanOpenPause(&Why))
	{
		UE_LOG(LogLB, Verbose, TEXT("UI: pause refused: %s"), *Why);
		return false;
	}
	CancelSkipHold();
	SetWorldPaused(true);
	if (!PushScreen(ELBScreen::Pause))
	{
		SetWorldPaused(false);
		return false;
	}
	return true;
}

void ULBUISubsystem::ClosePause()
{
	ClearScreens();
	if (bPausedByUI)
	{
		SetWorldPaused(false);
	}
}

void ULBUISubsystem::CancelSkipHold() const
{
	if (const UWorld* World = GetUIWorld())
	{
		if (ULBCinematicSubsystem* Cinematics = World->GetSubsystem<ULBCinematicSubsystem>())
		{
			Cinematics->EndSkipHold();
		}
	}
}

bool ULBUISubsystem::HandleBack()
{
	PruneStale();
	if (ULBMenuWidgetBase* Top = Stack.IsEmpty() ? nullptr : Stack.Last().Get())
	{
		Top->HandleBack();
		return true;
	}
	const APlayerController* PC = GetPC();
	const ALBCharacter* Character = PC ? Cast<ALBCharacter>(PC->GetPawn()) : nullptr;
	ULBInspectionComponent* Inspection = Character ? Character->GetInspection() : nullptr;
	if (Inspection && Inspection->IsInspecting())
	{
		// Escape closes the note first; the next press opens the pause menu.
		Inspection->RequestClose();
		return true;
	}
	OpenPause();
	return true;
}

void ULBUISubsystem::HandleApplicationActivation(bool bActive)
{
	if (bActive)
	{
		return;
	}
	CancelSkipHold();
	if (GIsEditor && !bPauseOnFocusLossInEditor)
	{
		return;
	}
	PruneStale();
	if (Stack.IsEmpty() && CanOpenPause())
	{
		OpenPause();
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Dialogs and flows
// ---------------------------------------------------------------------------------------------------------------------

ULBMenuWidgetBase* ULBUISubsystem::ShowConfirm(const FLBConfirmRequest& Request)
{
	ULBMenuWidgetBase* Widget = PushScreen(ELBScreen::Confirm);
	if (ULBConfirmWidget* Confirm = Cast<ULBConfirmWidget>(Widget))
	{
		Confirm->Configure(Request);
	}
	return Widget;
}

ULBMenuWidgetBase* ULBUISubsystem::ShowMessage(const FText& Title, const FText& Message)
{
	FLBConfirmRequest Request;
	Request.Title = Title;
	Request.Message = Message;
	Request.ConfirmLabel = NSLOCTEXT("LastBellUI", "MessageOK", "OK");
	Request.CancelLabel = NSLOCTEXT("LastBellUI", "MessageBack", "Back");
	return ShowConfirm(Request);
}

void ULBUISubsystem::OpenSettings()
{
	PushScreen(ELBScreen::Settings);
}

void ULBUISubsystem::OpenCredits()
{
	PushScreen(ELBScreen::Credits);
}

void ULBUISubsystem::OpenBrightness(bool bFirstLaunch)
{
	if (IsScreenOpen(ELBScreen::Brightness))
	{
		return;
	}
	bFirstLaunchBrightness = bFirstLaunch;
	if (!PushScreen(ELBScreen::Brightness))
	{
		bFirstLaunchBrightness = false;
	}
}

bool ULBUISubsystem::IsFirstLaunchBrightnessOpen() const
{
	return bFirstLaunchBrightness && IsScreenOpen(ELBScreen::Brightness);
}

bool ULBUISubsystem::ApplyBrightnessGate()
{
	const ULBUserSettings* Settings = ULBUserSettings::Get();
	if (!Settings || Settings->bBrightnessCalibrated || IsScreenOpen(ELBScreen::Brightness))
	{
		return false;
	}
	OpenBrightness(/*bFirstLaunch*/ true);
	return true;
}

void ULBUISubsystem::StartNewGameFlow()
{
	ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(GetUIWorld());
	if (!Save)
	{
		UE_LOG(LogLB, Warning, TEXT("UI: New Game without a save subsystem"));
		return;
	}
	TWeakObjectPtr<ULBUISubsystem> WeakThis(this);
	auto Start = [WeakThis]()
	{
		if (ULBUISubsystem* UI = WeakThis.Get())
		{
			if (ULBSaveSubsystem* SaveNow = ULBSaveSubsystem::Get(UI->GetUIWorld()))
			{
				// The menu stays until the save subsystem has taken the travel: a refusal (a bad map, a travel already pending) must not leave an empty screen.
				SaveNow->StartNewGame();
				if (SaveNow->IsTravelPending())
				{
					UI->ClearScreens();
				}
				else
				{
					UI->ShowMessage(NSLOCTEXT("LastBellUI", "NewGameFailedTitle", "New Game"), NSLOCTEXT("LastBellUI", "NewGameFailedMessage", "The game could not be started. Please try again."));
				}
			}
		}
	};
	if (!Save->HasValidSave())
	{
		Start();
		return;
	}
	FLBConfirmRequest Request;
	Request.Title = NSLOCTEXT("LastBellUI", "NewGameTitle", "New Game");
	Request.Message = NSLOCTEXT("LastBellUI", "NewGameMessage", "This will erase your progress.");
	Request.ConfirmLabel = NSLOCTEXT("LastBellUI", "NewGameConfirm", "Erase and start");
	Request.CancelLabel = NSLOCTEXT("LastBellUI", "Cancel", "Cancel");
	Request.bDanger = true;
	Request.OnConfirm = Start;
	ShowConfirm(Request);
}

void ULBUISubsystem::ContinueFlow()
{
	if (ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(GetUIWorld()))
	{
		// Only once the save subsystem has accepted: a missing or damaged save keeps the menu and says so.
		if (Save->ContinueGame())
		{
			ClearScreens();
		}
		else
		{
			UE_LOG(LogLB, Warning, TEXT("UI: Continue found no valid save"));
			ShowMessage(NSLOCTEXT("LastBellUI", "ContinueFailedTitle", "Continue"), NSLOCTEXT("LastBellUI", "ContinueFailedMessage", "The saved game could not be loaded."));
		}
	}
}

void ULBUISubsystem::ReturnToMainMenuFlow()
{
	TWeakObjectPtr<ULBUISubsystem> WeakThis(this);
	FLBConfirmRequest Request;
	Request.Title = NSLOCTEXT("LastBellUI", "ReturnTitle", "Return to main menu");
	Request.Message = NSLOCTEXT("LastBellUI", "ReturnMessage", "Unsaved progress since the last checkpoint will be lost.");
	Request.ConfirmLabel = NSLOCTEXT("LastBellUI", "ReturnConfirm", "Return to menu");
	Request.bDanger = true;
	Request.OnConfirm = [WeakThis]()
	{
		if (ULBUISubsystem* UI = WeakThis.Get())
		{
			// The world unpauses first; the save is kept.
			UI->ClosePause();
			if (ULBSaveSubsystem* Save = ULBSaveSubsystem::Get(UI->GetUIWorld()))
			{
				Save->ReturnToMainMenu();
			}
		}
	};
	ShowConfirm(Request);
}

void ULBUISubsystem::QuitGameFlow()
{
	TWeakObjectPtr<ULBUISubsystem> WeakThis(this);
	FLBConfirmRequest Request;
	Request.Title = NSLOCTEXT("LastBellUI", "QuitTitle", "Quit");
	Request.Message = NSLOCTEXT("LastBellUI", "QuitMessage", "Quit to the desktop?");
	Request.ConfirmLabel = NSLOCTEXT("LastBellUI", "QuitConfirm", "Quit");
	Request.bDanger = true;
	Request.OnConfirm = [WeakThis]()
	{
		if (const ULBUISubsystem* UI = WeakThis.Get())
		{
			UKismetSystemLibrary::QuitGame(UI->GetUIWorld(), UI->GetPC(), EQuitPreference::Quit, false);
		}
	};
	ShowConfirm(Request);
}

// ---------------------------------------------------------------------------------------------------------------------
// Input mode
// ---------------------------------------------------------------------------------------------------------------------

void ULBUISubsystem::SetMenuMode(bool bInMenuMode)
{
	bMenuModeWanted = bInMenuMode;
	RefreshInputMode();
}

void ULBUISubsystem::RefreshInputMode()
{
	PruneStale();
	APlayerController* PC = GetPC();
	if (!PC || !PC->IsLocalController())
	{
		return;
	}
	ULBMenuWidgetBase* Top = Stack.IsEmpty() ? nullptr : Stack.Last().Get();
	if (Top)
	{
		PC->bShowMouseCursor = true;
		FInputModeUIOnly Mode;
		Mode.SetWidgetToFocus(Top->TakeWidget());
		Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
		PC->SetInputMode(Mode);
		return;
	}
	if (bMenuModeWanted)
	{
		PC->bShowMouseCursor = true;
		FInputModeUIOnly Mode;
		Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
		PC->SetInputMode(Mode);
	}
	else
	{
		PC->bShowMouseCursor = false;
		PC->SetInputMode(FInputModeGameOnly());
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Sounds
// ---------------------------------------------------------------------------------------------------------------------

int32 ULBUISubsystem::GetSoundRequestCount(ELBUISound Sound) const
{
	return SoundRequests[static_cast<int32>(Sound)];
}

void ULBUISubsystem::PlaySound(ELBUISound Sound) const
{
	const int32 Index = static_cast<int32>(Sound);
	const_cast<ULBUISubsystem*>(this)->SoundRequests[Index]++;

	const ULBUIStyle* Style = ULBUIStyle::Resolve();
	const TSoftObjectPtr<USoundBase>* Ref = nullptr;
	switch (Sound)
	{
	case ELBUISound::Hover: Ref = &Style->HoverSound; break;
	case ELBUISound::Select: Ref = &Style->SelectSound; break;
	case ELBUISound::Back: Ref = &Style->BackSound; break;
	case ELBUISound::SliderTick: Ref = &Style->SliderTickSound; break;
	}
	USoundBase* Asset = (Ref && !Ref->IsNull()) ? Ref->LoadSynchronous() : nullptr;
	UWorld* World = GetUIWorld();
	if (!Asset || !World)
	{
		return;
	}
	// A UI sound plays on while the game is paused.
	UGameplayStatics::PlaySound2D(World, Asset, 1.f, 1.f, 0.f, nullptr, nullptr, /*bIsUISound*/ true);
}
