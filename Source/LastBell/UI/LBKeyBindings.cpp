#include "UI/LBKeyBindings.h"
#include "Engine/LocalPlayer.h"
#include "EnhancedInputSubsystems.h"
#include "EnhancedActionKeyMapping.h"
#include "EnhancedPlayerInput.h"
#include "InputAction.h"
#include "UI/LBUILogic.h"
#include "UserSettings/EnhancedInputUserSettings.h"
#include "LBLog.h"

namespace
{
	UEnhancedInputLocalPlayerSubsystem* InputSubsystem(const ULocalPlayer* LocalPlayer)
	{
		return LocalPlayer ? ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(LocalPlayer) : nullptr;
	}

	const FPlayerKeyMapping* FirstSlot(const UEnhancedInputUserSettings* Settings, ELBBindAction Action)
	{
		return Settings ? Settings->FindCurrentMappingForSlot(LBUILogic::MappingNameFor(Action), EPlayerMappableKeySlot::First) : nullptr;
	}

	/**
	 * A key that IMC_LB_Gameplay maps WITHOUT a player-mappable name is fixed: the Controls tab cannot move it, so giving it to another action would make it
	 * do both. Read from the player's live mappings; empty when the key is free (or the mappings cannot be read, then LBUILogic's table has already refused).
	 */
	FText LiveFixedKeyRefusal(const ULocalPlayer* LocalPlayer, ELBBindAction Action, const FKey& Key)
	{
		const UEnhancedInputLocalPlayerSubsystem* Input = InputSubsystem(LocalPlayer);
		const UEnhancedPlayerInput* PlayerInput = Input ? Input->GetPlayerInput() : nullptr;
		if (!PlayerInput)
		{
			return FText::GetEmpty();
		}
		const UEnhancedInputUserSettings* Settings = Input->GetUserSettings();
		const UInputAction* OwnAction = Settings ? Settings->FindInputActionForMapping(LBUILogic::MappingNameFor(Action)) : nullptr;
		const bool bOwnIsMove = Action == ELBBindAction::MoveForward || Action == ELBBindAction::MoveBack || Action == ELBBindAction::MoveLeft || Action == ELBBindAction::MoveRight;
		for (const FEnhancedActionKeyMapping& Mapping : PlayerInput->GetEnhancedActionMappingsView())
		{
			if (Mapping.Key != Key || !Mapping.Action || Mapping.IsPlayerMappable())
			{
				continue;
			}
			// The action's own second key may stay (Ctrl for Crouch, the natural arrow for a Move direction).
			if (LBUILogic::FixedKeyAction(Key) == Action || (!bOwnIsMove && OwnAction && Mapping.Action == OwnAction))
			{
				continue;
			}
			FString Name = Mapping.Action->GetName();
			Name.RemoveFromStart(TEXT("IA_"));
			return FText::Format(NSLOCTEXT("LastBellUI", "KeyFixedLive", "{0} is fixed for {1}."), LBUILogic::KeyFallbackLabel(Key), FText::FromString(Name));
		}
		return FText::GetEmpty();
	}

	void LogOnce(const TCHAR* Text)
	{
		static bool bLogged = false;
		if (!bLogged)
		{
			bLogged = true;
			UE_LOG(LogLB, Warning, TEXT("Key rebinding: %s (P18-2 enables Enhanced Input user settings and names the IMC_LB_Gameplay mappings)"), Text);
		}
	}
}

FSimpleMulticastDelegate& LBKeyBindings::OnBindingsChanged()
{
	static FSimpleMulticastDelegate Delegate;
	return Delegate;
}

UEnhancedInputUserSettings* LBKeyBindings::GetUserSettings(const ULocalPlayer* LocalPlayer)
{
	const UEnhancedInputLocalPlayerSubsystem* Input = InputSubsystem(LocalPlayer);
	return Input ? Input->GetUserSettings() : nullptr;
}

bool LBKeyBindings::IsRebindable(const ULocalPlayer* LocalPlayer, ELBBindAction Action)
{
	const FPlayerKeyMapping* Mapping = FirstSlot(GetUserSettings(LocalPlayer), Action);
	return Mapping && Mapping->IsValid();
}

FKey LBKeyBindings::GetKey(const ULocalPlayer* LocalPlayer, ELBBindAction Action)
{
	const FPlayerKeyMapping* Mapping = FirstSlot(GetUserSettings(LocalPlayer), Action);
	if (Mapping && Mapping->IsValid())
	{
		return Mapping->GetCurrentKey();
	}
	return LBUILogic::DefaultKeyFor(Action);
}

FKey LBKeyBindings::GetKeyForInputAction(const ULocalPlayer* LocalPlayer, const UInputAction* Action)
{
	const UEnhancedInputLocalPlayerSubsystem* Input = InputSubsystem(LocalPlayer);
	if (!Input || !Action)
	{
		return EKeys::Invalid;
	}
	for (const FKey& Key : Input->QueryKeysMappedToAction(Action))
	{
		// Keyboard and mouse only; the first such key is the one a prompt shows.
		if (Key.IsValid() && !Key.IsGamepadKey())
		{
			return Key;
		}
	}
	return EKeys::Invalid;
}

TMap<ELBBindAction, FKey> LBKeyBindings::GetAll(const ULocalPlayer* LocalPlayer)
{
	TMap<ELBBindAction, FKey> Result;
	for (const ELBBindAction Action : LBUILogic::RebindableActions())
	{
		Result.Add(Action, GetKey(LocalPlayer, Action));
	}
	return Result;
}

LBKeyBindings::FRebindResult LBKeyBindings::Rebind(ULocalPlayer* LocalPlayer, ELBBindAction Action, const FKey& NewKey)
{
	FRebindResult Result;

	const FText Refusal = LBUILogic::KeyRefusalReason(Action, NewKey);
	if (!Refusal.IsEmpty())
	{
		Result.Message = Refusal;
		return Result;
	}

	const FText FixedRefusal = LiveFixedKeyRefusal(LocalPlayer, Action, NewKey);
	if (!FixedRefusal.IsEmpty())
	{
		Result.Message = FixedRefusal;
		return Result;
	}

	UEnhancedInputUserSettings* Settings = GetUserSettings(LocalPlayer);
	if (!Settings || !IsRebindable(LocalPlayer, Action))
	{
		LogOnce(TEXT("user settings are off or the mapping is not registered; the key cannot be changed"));
		Result.Message = NSLOCTEXT("LastBellUI", "RebindUnavailable", "This key cannot be changed right now.");
		return Result;
	}

	const FKey Current = GetKey(LocalPlayer, Action);
	if (Current == NewKey)
	{
		Result.bOk = true;
		return Result;
	}

	const ELBBindAction Conflict = LBUILogic::FindKeyConflict(GetAll(LocalPlayer), Action, NewKey);
	if (Conflict != ELBBindAction::Count)
	{
		Result.Conflict = Conflict;
		Result.Message = FText::Format(NSLOCTEXT("LastBellUI", "RebindConflict", "{0} is already used for {1}."),
			LBUILogic::KeyFallbackLabel(NewKey), LBUILogic::DisplayNameFor(Conflict));
		return Result;
	}

	FMapPlayerKeyArgs Args;
	Args.MappingName = LBUILogic::MappingNameFor(Action);
	Args.Slot = EPlayerMappableKeySlot::First;
	Args.NewKey = NewKey;
	FGameplayTagContainer Failure;
	Settings->MapPlayerKey(Args, Failure);
	if (!Failure.IsEmpty())
	{
		UE_LOG(LogLB, Warning, TEXT("Key rebinding: mapping %s to %s failed: %s"), *Args.MappingName.ToString(), *NewKey.ToString(), *Failure.ToString());
		Result.Message = NSLOCTEXT("LastBellUI", "RebindFailed", "That key could not be set.");
		return Result;
	}
	Settings->ApplySettings();
	Settings->SaveSettings();
	OnBindingsChanged().Broadcast();
	Result.bOk = true;
	return Result;
}

void LBKeyBindings::ResetAll(ULocalPlayer* LocalPlayer)
{
	UEnhancedInputUserSettings* Settings = GetUserSettings(LocalPlayer);
	if (!Settings)
	{
		LogOnce(TEXT("user settings are off; nothing to reset"));
		return;
	}
	FGameplayTagContainer Failure;
	Settings->ResetKeyProfileIdToDefault(Settings->GetActiveKeyProfileId(), Failure);
	if (!Failure.IsEmpty())
	{
		UE_LOG(LogLB, Warning, TEXT("Key rebinding: reset failed: %s"), *Failure.ToString());
	}
	Settings->ApplySettings();
	Settings->SaveSettings();
	OnBindingsChanged().Broadcast();
}
