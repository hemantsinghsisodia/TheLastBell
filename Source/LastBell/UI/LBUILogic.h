#pragma once

#include "CoreMinimal.h"
#include "InputCoreTypes.h"
#include "UI/LBUITypes.h"

/**
 * Pure logic of the UI (plan P18 section 9 unit tests): clamps, preset detection, key conflicts, the keep-dialog timer, option lists.
 * No UObjects, so the automation tests cover it without a world.
 */
namespace LBUILogic
{
	constexpr float MinFOV = 70.f;
	constexpr float MaxFOV = 110.f;
	/** Matches the first-person camera's FOV before Phase 18 (the component default, 90). */
	constexpr float DefaultFOV = 90.f;
	constexpr float MinGamma = 1.8f;
	constexpr float MaxGamma = 2.6f;
	constexpr float DefaultGamma = 2.2f;
	constexpr float MinResolutionScale = 50.f;
	constexpr float MaxResolutionScale = 100.f;
	/** The keep dialog after a display-mode change. */
	constexpr float KeepDialogSeconds = 15.f;

	LASTBELL_API float ClampFOV(float Value);
	LASTBELL_API float ClampGamma(float Value);
	LASTBELL_API float ClampResolutionScale(float Percent);

	/**
	 * The overall preset (0 Low .. 3 Epic) when every group has that same level, else -1 ("Custom"). Levels outside 0..3 (the engine's
	 * Cinematic, 4) are not a preset the menu offers, so they read as Custom.
	 */
	LASTBELL_API int32 DetectPreset(const TArray<int32>& GroupLevels);

	/** Frame-rate limit options in the order shown; 0 is Unlimited. */
	LASTBELL_API const TArray<int32>& FrameLimitOptions();
	/** The index in FrameLimitOptions() nearest to this limit (0 = unlimited maps to the Unlimited entry). */
	LASTBELL_API int32 NearestFrameLimitIndex(float Limit);

	/** The mapping name an action carries in IMC_LB_Gameplay (P18-2 sets exactly these as player-mappable names). */
	LASTBELL_API FName MappingNameFor(ELBBindAction Action);
	LASTBELL_API FText DisplayNameFor(ELBBindAction Action);
	/** The key the action has with no rebinding (the fallback when Enhanced Input user settings are off or the IMC is missing). */
	LASTBELL_API FKey DefaultKeyFor(ELBBindAction Action);
	/** All actions the Controls tab lists, in order. */
	LASTBELL_API const TArray<ELBBindAction>& RebindableActions();

	/**
	 * Why a key may not be bound to an action, or an empty text when it may. Keyboard and mouse only: gamepad and touch keys are refused;
	 * Pause refuses the mouse buttons; mouse movement and the wheel axes are never bindable.
	 */
	LASTBELL_API FText KeyRefusalReason(ELBBindAction Action, const FKey& Key);

	/**
	 * The action (other than this one) that already uses NewKey, or Count when none does. Current maps each action to its key.
	 * A key is a conflict across every action, Pause included.
	 */
	LASTBELL_API ELBBindAction FindKeyConflict(const TMap<ELBBindAction, FKey>& Current, ELBBindAction Action, const FKey& NewKey);

	/** Every key that needs a glyph in the key-icon set: letters, digits, arrows, Shift, Ctrl, Alt, Space, Esc, Tab, Enter and the mouse buttons. */
	LASTBELL_API const TArray<FKey>& IconKeys();
	/** A short text for a key when no icon exists (E, Shift, Ctrl, Esc, LMB). Never empty for a valid key. */
	LASTBELL_API FText KeyFallbackLabel(const FKey& Key);

	/** Windowed resolutions are clamped to the desktop: sorted, unique, none larger than the desktop in either axis. */
	LASTBELL_API TArray<FIntPoint> ClampResolutionsToDesktop(const TArray<FIntPoint>& Supported, const FIntPoint& Desktop);

	/**
	 * The flicker of a lit candle: a smooth, bounded value around 1 (1 - Amplitude .. 1). Speed is in cycles per second. Deterministic in Time.
	 */
	LASTBELL_API float CandleFlicker(float TimeSeconds, float Speed, float Amplitude);

	/** The "Keep these settings? Reverting in N s" countdown. Real time, ticked by the dialog. */
	struct FKeepTimer
	{
		bool bActive = false;
		float Remaining = 0.f;

		void Begin(float Seconds)
		{
			bActive = Seconds > 0.f;
			Remaining = FMath::Max(Seconds, 0.f);
		}

		/** True exactly once, on the tick the countdown reaches zero. */
		bool Tick(float DeltaSeconds)
		{
			if (!bActive)
			{
				return false;
			}
			Remaining -= FMath::Max(DeltaSeconds, 0.f);
			if (Remaining <= 0.f)
			{
				Remaining = 0.f;
				bActive = false;
				return true;
			}
			return false;
		}

		/** Keep pressed: the timer stops and will not fire. */
		void Cancel()
		{
			bActive = false;
		}

		/** Whole seconds left for the label (rounded up, never below 1 while active). */
		int32 SecondsShown() const
		{
			return bActive ? FMath::Max(1, FMath::CeilToInt(Remaining)) : 0;
		}
	};
}
