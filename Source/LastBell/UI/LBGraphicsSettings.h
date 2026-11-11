#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameUserSettings.h"
#include "UI/LBUITypes.h"

/** Everything the Graphics and Display tabs can change, captured so a Revert (or the 15 s keep timer) can put it back. */
struct LASTBELL_API FLBGraphicsSnapshot
{
	int32 Groups[static_cast<int32>(ELBGraphicsGroup::Count)] = {};
	float ResolutionScaleValue = 100.f;
	FIntPoint Resolution = FIntPoint::ZeroValue;
	EWindowMode::Type WindowMode = EWindowMode::Windowed;
	bool bVSync = false;
	float FrameRateLimit = 0.f;

	/**
	 * The window mode or the resolution differs: the changes that need the keep dialog. In Windowed fullscreen the game always draws at the desktop size,
	 * so a resolution change there is not a display change.
	 */
	bool DisplayModeDiffers(const FLBGraphicsSnapshot& Other) const
	{
		return WindowMode != Other.WindowMode || (WindowMode != EWindowMode::WindowedFullscreen && Resolution != Other.Resolution);
	}

	/** Anything differs (the settings screen asks "Apply changes?" before leaving a tab or the screen). */
	bool Differs(const FLBGraphicsSnapshot& Other) const
	{
		for (int32 Index = 0; Index < static_cast<int32>(ELBGraphicsGroup::Count); ++Index)
		{
			if (Groups[Index] != Other.Groups[Index])
			{
				return true;
			}
		}
		return !FMath::IsNearlyEqual(ResolutionScaleValue, Other.ResolutionScaleValue, 0.6f) || Resolution != Other.Resolution || WindowMode != Other.WindowMode
			|| bVSync != Other.bVSync || !FMath::IsNearlyEqual(FrameRateLimit, Other.FrameRateLimit, 0.5f);
	}
};

/**
 * A thin wrapper over UGameUserSettings for the settings screen (plan P18 section 6): the overall preset, the ten scalability groups, the
 * resolution scale, window mode, resolution, VSync and the frame cap. Setters change the user settings object only; Apply() applies and saves
 * them (GameUserSettings.ini). Revert() puts a captured snapshot back. The keep dialog around a display-mode change is the confirm widget's job
 * (FLBConfirmRequest::TimeoutSeconds): Apply returns whether it is needed.
 */
class LASTBELL_API FLBGraphicsSettings
{
public:
	/** The engine's user settings object (never null in a running game). */
	static UGameUserSettings* Get();

	static FLBGraphicsSnapshot Capture();
	/** Writes a snapshot into the user settings without applying it. */
	static void Restore(const FLBGraphicsSnapshot& Snapshot);

	static int32 GetGroupLevel(ELBGraphicsGroup Group);
	static void SetGroupLevel(ELBGraphicsGroup Group, int32 Level);
	static FText GroupName(ELBGraphicsGroup Group);

	/**
	 * Sets the overall preset like SetPreset, then keeps the resolution scale the player chose (ChosenPercent >= 0): a preset sets the scale too (the engine's
	 * Low 50, Medium 71, High 87, Epic 100), but a player who picked a scale of their own keeps it across preset changes. ChosenPercent < 0 (never chosen):
	 * the preset's scale stands.
	 */
	static void SetPresetKeepingScale(int32 Preset, float ChosenPercent);

	/** The overall preset 0..3, or -1 when the groups differ ("Custom"). */
	static int32 GetPreset();
	/** Sets every group to the preset (0 Low .. 3 Epic). */
	static void SetPreset(int32 Preset);
	static FText PresetName(int32 Preset);
	static const TArray<FText>& QualityLevelNames();

	/** Resolution scale in percent, 50..100. */
	static float GetResolutionScalePercent();
	static void SetResolutionScalePercent(float Percent);

	static EWindowMode::Type GetWindowMode();
	static void SetWindowMode(EWindowMode::Type Mode);
	static FIntPoint GetResolution();
	static void SetResolution(const FIntPoint& Resolution);
	/** The supported resolutions (windowed ones are clamped to the desktop), sorted, unique. The current one is always in the list. */
	static TArray<FIntPoint> GetResolutionOptions(EWindowMode::Type Mode);

	static bool GetVSync();
	static void SetVSync(bool bEnabled);
	static float GetFrameRateLimit();
	static void SetFrameRateLimit(float Limit);

	/**
	 * Applies and saves the pending settings. Returns true when the window mode or the resolution differs from Before: the caller then asks
	 * the player to keep them (and calls Revert(Before) if they do not answer in time).
	 */
	static bool Apply(const FLBGraphicsSnapshot& Before);

	/** Marks the applied display mode as confirmed by the player. */
	static void Confirm();

	/** Puts the snapshot back, applies and saves. */
	static void Revert(const FLBGraphicsSnapshot& Snapshot);

	/** Discards pending, unapplied changes by reloading the saved settings. */
	static void DiscardPending();
};
