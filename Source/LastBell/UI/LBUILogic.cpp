#include "UI/LBUILogic.h"

float LBUILogic::ClampFOV(float Value)
{
	return FMath::Clamp(Value, MinFOV, MaxFOV);
}

float LBUILogic::ClampGamma(float Value)
{
	return FMath::Clamp(Value, MinGamma, MaxGamma);
}

float LBUILogic::ClampResolutionScale(float Percent)
{
	return FMath::Clamp(Percent, MinResolutionScale, MaxResolutionScale);
}

int32 LBUILogic::DetectPreset(const TArray<int32>& GroupLevels)
{
	if (GroupLevels.IsEmpty())
	{
		return -1;
	}
	const int32 First = GroupLevels[0];
	for (const int32 Level : GroupLevels)
	{
		if (Level != First)
		{
			return -1;
		}
	}
	return (First >= 0 && First <= 3) ? First : -1;
}

const TArray<int32>& LBUILogic::FrameLimitOptions()
{
	static const TArray<int32> Options = { 30, 60, 90, 120, 144, 0 };
	return Options;
}

int32 LBUILogic::NearestFrameLimitIndex(float Limit)
{
	const TArray<int32>& Options = FrameLimitOptions();
	if (Limit <= 0.f)
	{
		return Options.Num() - 1;
	}
	int32 Best = 0;
	float BestDistance = TNumericLimits<float>::Max();
	for (int32 Index = 0; Index < Options.Num() - 1; ++Index)
	{
		const float Distance = FMath::Abs(static_cast<float>(Options[Index]) - Limit);
		if (Distance < BestDistance)
		{
			BestDistance = Distance;
			Best = Index;
		}
	}
	return Best;
}

FName LBUILogic::MappingNameFor(ELBBindAction Action)
{
	switch (Action)
	{
	case ELBBindAction::MoveForward: return FName(TEXT("LB_Move_Forward"));
	case ELBBindAction::MoveBack: return FName(TEXT("LB_Move_Back"));
	case ELBBindAction::MoveLeft: return FName(TEXT("LB_Move_Left"));
	case ELBBindAction::MoveRight: return FName(TEXT("LB_Move_Right"));
	case ELBBindAction::Sprint: return FName(TEXT("LB_Sprint"));
	case ELBBindAction::Crouch: return FName(TEXT("LB_Crouch"));
	case ELBBindAction::Interact: return FName(TEXT("LB_Interact"));
	case ELBBindAction::Candle: return FName(TEXT("LB_Candle"));
	case ELBBindAction::Pause: return FName(TEXT("LB_Pause"));
	default: return NAME_None;
	}
}

FText LBUILogic::DisplayNameFor(ELBBindAction Action)
{
	switch (Action)
	{
	case ELBBindAction::MoveForward: return NSLOCTEXT("LastBellUI", "BindForward", "Move forward");
	case ELBBindAction::MoveBack: return NSLOCTEXT("LastBellUI", "BindBack", "Move back");
	case ELBBindAction::MoveLeft: return NSLOCTEXT("LastBellUI", "BindLeft", "Move left");
	case ELBBindAction::MoveRight: return NSLOCTEXT("LastBellUI", "BindRight", "Move right");
	case ELBBindAction::Sprint: return NSLOCTEXT("LastBellUI", "BindSprint", "Sprint");
	case ELBBindAction::Crouch: return NSLOCTEXT("LastBellUI", "BindCrouch", "Crouch");
	case ELBBindAction::Interact: return NSLOCTEXT("LastBellUI", "BindInteract", "Interact");
	case ELBBindAction::Candle: return NSLOCTEXT("LastBellUI", "BindCandle", "Candle");
	case ELBBindAction::Pause: return NSLOCTEXT("LastBellUI", "BindPause", "Pause");
	default: return FText::GetEmpty();
	}
}

FKey LBUILogic::DefaultKeyFor(ELBBindAction Action)
{
	switch (Action)
	{
	case ELBBindAction::MoveForward: return EKeys::W;
	case ELBBindAction::MoveBack: return EKeys::S;
	case ELBBindAction::MoveLeft: return EKeys::A;
	case ELBBindAction::MoveRight: return EKeys::D;
	case ELBBindAction::Sprint: return EKeys::LeftShift;
	case ELBBindAction::Crouch: return EKeys::C;
	case ELBBindAction::Interact: return EKeys::E;
	case ELBBindAction::Candle: return EKeys::F;
	case ELBBindAction::Pause: return EKeys::Escape;
	default: return EKeys::Invalid;
	}
}

const TArray<ELBBindAction>& LBUILogic::RebindableActions()
{
	static const TArray<ELBBindAction> Actions = {
		ELBBindAction::MoveForward, ELBBindAction::MoveBack, ELBBindAction::MoveLeft, ELBBindAction::MoveRight,
		ELBBindAction::Sprint, ELBBindAction::Crouch, ELBBindAction::Interact, ELBBindAction::Candle, ELBBindAction::Pause };
	return Actions;
}

ELBBindAction LBUILogic::FixedKeyAction(const FKey& Key)
{
	if (Key == EKeys::Up) { return ELBBindAction::MoveForward; }
	if (Key == EKeys::Down) { return ELBBindAction::MoveBack; }
	if (Key == EKeys::Left) { return ELBBindAction::MoveLeft; }
	if (Key == EKeys::Right) { return ELBBindAction::MoveRight; }
	if (Key == EKeys::LeftControl) { return ELBBindAction::Crouch; }
	return ELBBindAction::Count;
}

FText LBUILogic::FixedKeyUseName(const FKey& Key)
{
	return FixedKeyAction(Key) == ELBBindAction::Crouch ? NSLOCTEXT("LastBellUI", "FixedCrouch", "Crouch") : NSLOCTEXT("LastBellUI", "FixedMove", "Move");
}

bool LBUILogic::DisplayDiffersFromConfirmed(int32 Mode, const FIntPoint& Resolution, int32 ConfirmedMode, const FIntPoint& ConfirmedResolution)
{
	if (Mode != ConfirmedMode)
	{
		return true;
	}
	// 1 = EWindowMode::WindowedFullscreen: it always uses the desktop size.
	return Mode != 1 && Resolution != ConfirmedResolution;
}

FText LBUILogic::KeyRefusalReason(ELBBindAction Action, const FKey& Key)
{
	if (!Key.IsValid())
	{
		return NSLOCTEXT("LastBellUI", "KeyInvalid", "That is not a key.");
	}
	if (Key.IsGamepadKey() || Key.IsTouch() || Key.IsGesture())
	{
		return NSLOCTEXT("LastBellUI", "KeyNotKeyboard", "Only the keyboard and the mouse can be used.");
	}
	if (Key.IsAxis1D() || Key.IsAxis2D() || Key.IsAxis3D() || Key == EKeys::MouseScrollUp || Key == EKeys::MouseScrollDown)
	{
		return NSLOCTEXT("LastBellUI", "KeyAxis", "Mouse movement and the wheel cannot be used.");
	}
	if (Key == EKeys::Tilde)
	{
		return NSLOCTEXT("LastBellUI", "KeyConsole", "That key opens the console.");
	}
	const ELBBindAction FixedOwner = FixedKeyAction(Key);
	if (FixedOwner != ELBBindAction::Count && FixedOwner != Action)
	{
		return FText::Format(NSLOCTEXT("LastBellUI", "KeyFixed", "{0} is fixed for {1}."), KeyFallbackLabel(Key), FixedKeyUseName(Key));
	}
	if (Action == ELBBindAction::Pause && Key.IsMouseButton())
	{
		return NSLOCTEXT("LastBellUI", "KeyPauseMouse", "Pause cannot be a mouse button.");
	}
	return FText::GetEmpty();
}

ELBBindAction LBUILogic::FindKeyConflict(const TMap<ELBBindAction, FKey>& Current, ELBBindAction Action, const FKey& NewKey)
{
	if (!NewKey.IsValid())
	{
		return ELBBindAction::Count;
	}
	for (const TPair<ELBBindAction, FKey>& Pair : Current)
	{
		if (Pair.Key != Action && Pair.Value == NewKey)
		{
			return Pair.Key;
		}
	}
	return ELBBindAction::Count;
}

const TArray<FKey>& LBUILogic::IconKeys()
{
	static TArray<FKey> Keys;
	if (Keys.IsEmpty())
	{
		for (TCHAR Letter = TEXT('A'); Letter <= TEXT('Z'); ++Letter)
		{
			Keys.Add(FKey(FName(*FString::Chr(Letter))));
		}
		Keys.Append({ EKeys::Zero, EKeys::One, EKeys::Two, EKeys::Three, EKeys::Four, EKeys::Five, EKeys::Six, EKeys::Seven, EKeys::Eight, EKeys::Nine });
		Keys.Append({ EKeys::Up, EKeys::Down, EKeys::Left, EKeys::Right });
		Keys.Append({ EKeys::LeftShift, EKeys::RightShift, EKeys::LeftControl, EKeys::RightControl, EKeys::LeftAlt, EKeys::RightAlt });
		Keys.Append({ EKeys::SpaceBar, EKeys::Escape, EKeys::Tab, EKeys::Enter });
		Keys.Append({ EKeys::LeftMouseButton, EKeys::RightMouseButton, EKeys::MiddleMouseButton, EKeys::ThumbMouseButton, EKeys::ThumbMouseButton2 });
	}
	return Keys;
}

FText LBUILogic::KeyFallbackLabel(const FKey& Key)
{
	if (!Key.IsValid())
	{
		return NSLOCTEXT("LastBellUI", "KeyNone", "None");
	}
	if (Key == EKeys::LeftMouseButton) { return NSLOCTEXT("LastBellUI", "KeyLMB", "LMB"); }
	if (Key == EKeys::RightMouseButton) { return NSLOCTEXT("LastBellUI", "KeyRMB", "RMB"); }
	if (Key == EKeys::MiddleMouseButton) { return NSLOCTEXT("LastBellUI", "KeyMMB", "MMB"); }
	if (Key == EKeys::Escape) { return NSLOCTEXT("LastBellUI", "KeyEsc", "Esc"); }
	if (Key == EKeys::LeftShift || Key == EKeys::RightShift) { return NSLOCTEXT("LastBellUI", "KeyShift", "Shift"); }
	if (Key == EKeys::LeftControl || Key == EKeys::RightControl) { return NSLOCTEXT("LastBellUI", "KeyCtrl", "Ctrl"); }
	if (Key == EKeys::LeftAlt || Key == EKeys::RightAlt) { return NSLOCTEXT("LastBellUI", "KeyAlt", "Alt"); }
	if (Key == EKeys::SpaceBar) { return NSLOCTEXT("LastBellUI", "KeySpace", "Space"); }
	const FText Display = Key.GetDisplayName(false);
	return Display.IsEmpty() ? FText::FromName(Key.GetFName()) : Display;
}

TArray<FIntPoint> LBUILogic::ClampResolutionsToDesktop(const TArray<FIntPoint>& Supported, const FIntPoint& Desktop)
{
	TArray<FIntPoint> Result;
	for (const FIntPoint& Resolution : Supported)
	{
		if (Resolution.X <= 0 || Resolution.Y <= 0)
		{
			continue;
		}
		if (Desktop.X > 0 && Desktop.Y > 0 && (Resolution.X > Desktop.X || Resolution.Y > Desktop.Y))
		{
			continue;
		}
		Result.AddUnique(Resolution);
	}
	Result.Sort([](const FIntPoint& A, const FIntPoint& B) { return A.X != B.X ? A.X < B.X : A.Y < B.Y; });
	return Result;
}

float LBUILogic::CandleFlicker(float TimeSeconds, float Speed, float Amplitude)
{
	const float Phase = TimeSeconds * Speed * UE_TWO_PI;
	const float Wave = 0.5f * FMath::Sin(Phase) + 0.3f * FMath::Sin(Phase * 2.3f + 1.1f) + 0.2f * FMath::Sin(Phase * 5.1f + 2.7f);
	const float Unit = 0.5f + 0.5f * Wave; // 0..1
	return 1.f - FMath::Clamp(Amplitude, 0.f, 1.f) * (1.f - Unit);
}
