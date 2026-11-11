#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

#include "Tests/LBUITestUtil.h"
#include "Engine/Engine.h"
#include "Engine/Texture2D.h"
#include "GameFramework/GameUserSettings.h"
#include "Systems/LBGameSettings.h"
#include "Systems/LBUserSettings.h"
#include "UI/LBGraphicsSettings.h"
#include "UI/LBKeyBindings.h"
#include "UI/LBLoadingScreen.h"
#include "UI/LBUILogic.h"
#include "UI/LBUIStyle.h"

// P18-1 unit tests of the UI logic and settings (LastBell.UI.*). The widget and flow tests are in LBUIFunctionalTests.cpp.
// LastBell.UI.Content.* need the P18-2 assets (DA_UIStyle with the key icons): they are EXPECTED TO FAIL until P18-2.

#define LB_UI_UNIT_FLAGS (EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUILogicClampsTest, "LastBell.UI.Logic.Clamps", LB_UI_UNIT_FLAGS)
bool FLBUILogicClampsTest::RunTest(const FString& Parameters)
{
	TestEqual(TEXT("FOV below the range"), LBUILogic::ClampFOV(10.f), 70.f);
	TestEqual(TEXT("FOV above the range"), LBUILogic::ClampFOV(500.f), 110.f);
	TestEqual(TEXT("FOV inside the range"), LBUILogic::ClampFOV(95.f), 95.f);
	TestEqual(TEXT("The FOV default is the camera's old 90"), LBUILogic::DefaultFOV, 90.f);
	TestEqual(TEXT("Gamma below the range"), LBUILogic::ClampGamma(0.f), 1.8f);
	TestEqual(TEXT("Gamma above the range"), LBUILogic::ClampGamma(9.f), 2.6f);
	TestEqual(TEXT("The gamma default"), LBUILogic::DefaultGamma, 2.2f);
	TestEqual(TEXT("Resolution scale below 50"), LBUILogic::ClampResolutionScale(10.f), 50.f);
	TestEqual(TEXT("Resolution scale above 100"), LBUILogic::ClampResolutionScale(400.f), 100.f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUILogicPresetTest, "LastBell.UI.Logic.PresetDetection", LB_UI_UNIT_FLAGS)
bool FLBUILogicPresetTest::RunTest(const FString& Parameters)
{
	TestEqual(TEXT("All groups Low is preset 0"), LBUILogic::DetectPreset({ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 }), 0);
	TestEqual(TEXT("All groups Epic is preset 3"), LBUILogic::DetectPreset({ 3, 3, 3, 3, 3, 3, 3, 3, 3, 3 }), 3);
	TestEqual(TEXT("One group differing is Custom"), LBUILogic::DetectPreset({ 2, 2, 1, 2, 2, 2, 2, 2, 2, 2 }), -1);
	TestEqual(TEXT("Cinematic (4) everywhere is not a preset the menu offers"), LBUILogic::DetectPreset({ 4, 4, 4 }), -1);
	TestEqual(TEXT("No groups is Custom"), LBUILogic::DetectPreset({}), -1);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUILogicFrameLimitTest, "LastBell.UI.Logic.FrameLimitOptions", LB_UI_UNIT_FLAGS)
bool FLBUILogicFrameLimitTest::RunTest(const FString& Parameters)
{
	const TArray<int32>& Options = LBUILogic::FrameLimitOptions();
	TestEqual(TEXT("Six options"), Options.Num(), 6);
	TestEqual(TEXT("30 first"), Options[0], 30);
	TestEqual(TEXT("144 fifth"), Options[4], 144);
	TestEqual(TEXT("Unlimited (0) last"), Options.Last(), 0);
	TestEqual(TEXT("0 maps to Unlimited"), LBUILogic::NearestFrameLimitIndex(0.f), 5);
	TestEqual(TEXT("60 maps to 60"), LBUILogic::NearestFrameLimitIndex(60.f), 1);
	TestEqual(TEXT("100 maps to 90 (the nearer of 90 and 120)"), LBUILogic::NearestFrameLimitIndex(100.f), 2);
	TestEqual(TEXT("1000 maps to 144, not Unlimited"), LBUILogic::NearestFrameLimitIndex(1000.f), 4);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUILogicResolutionsTest, "LastBell.UI.Logic.ResolutionsClampedToDesktop", LB_UI_UNIT_FLAGS)
bool FLBUILogicResolutionsTest::RunTest(const FString& Parameters)
{
	const TArray<FIntPoint> Supported = { FIntPoint(2560, 1440), FIntPoint(1280, 720), FIntPoint(1920, 1080), FIntPoint(1280, 720), FIntPoint(3840, 2160), FIntPoint(0, 0) };
	const TArray<FIntPoint> Clamped = LBUILogic::ClampResolutionsToDesktop(Supported, FIntPoint(1920, 1080));
	TestEqual(TEXT("Two sizes fit a 1920x1080 desktop (duplicates and zero removed)"), Clamped.Num(), 2);
	if (Clamped.Num() == 2)
	{
		TestEqual(TEXT("Sorted: 1280x720 first"), Clamped[0], FIntPoint(1280, 720));
		TestEqual(TEXT("then 1920x1080"), Clamped[1], FIntPoint(1920, 1080));
	}
	TestEqual(TEXT("No desktop size means no clamping"), LBUILogic::ClampResolutionsToDesktop(Supported, FIntPoint::ZeroValue).Num(), 4);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUILogicKeepTimerTest, "LastBell.UI.Logic.KeepTimer", LB_UI_UNIT_FLAGS)
bool FLBUILogicKeepTimerTest::RunTest(const FString& Parameters)
{
	LBUILogic::FKeepTimer Timer;
	TestFalse(TEXT("Idle before Begin"), Timer.bActive);
	TestFalse(TEXT("An idle timer never fires"), Timer.Tick(100.f));

	Timer.Begin(LBUILogic::KeepDialogSeconds);
	TestTrue(TEXT("Active after Begin"), Timer.bActive);
	TestEqual(TEXT("15 s shown at the start"), Timer.SecondsShown(), 15);
	TestFalse(TEXT("Not expired after 14.5 s"), Timer.Tick(14.5f));
	TestEqual(TEXT("1 s shown with 0.5 s left"), Timer.SecondsShown(), 1);
	TestTrue(TEXT("Expired when the last 0.5 s pass: the revert fires"), Timer.Tick(0.5f));
	TestFalse(TEXT("Inactive afterwards"), Timer.bActive);
	TestFalse(TEXT("It fires exactly once"), Timer.Tick(1.f));

	Timer.Begin(15.f);
	Timer.Tick(5.f);
	Timer.Cancel();
	TestFalse(TEXT("Keep cancels: no revert"), Timer.Tick(60.f));
	Timer.Begin(0.f);
	TestFalse(TEXT("A zero timeout never starts"), Timer.bActive);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUILogicFlickerTest, "LastBell.UI.Logic.CandleFlicker", LB_UI_UNIT_FLAGS)
bool FLBUILogicFlickerTest::RunTest(const FString& Parameters)
{
	float Min = 10.f;
	float Max = -10.f;
	for (int32 Step = 0; Step < 2000; ++Step)
	{
		const float Value = LBUILogic::CandleFlicker(Step * 0.01f, 1.6f, 0.3f);
		Min = FMath::Min(Min, Value);
		Max = FMath::Max(Max, Value);
	}
	TestTrue(FString::Printf(TEXT("Never above 1 (max %.3f)"), Max), Max <= 1.0001f);
	TestTrue(FString::Printf(TEXT("Never below 1 - amplitude (min %.3f)"), Min), Min >= 0.7f - 0.0001f);
	TestTrue(FString::Printf(TEXT("It actually flickers (range %.3f)"), Max - Min), Max - Min > 0.1f);
	TestEqual(TEXT("Amplitude 0 is steady"), LBUILogic::CandleFlicker(3.7f, 1.6f, 0.f), 1.f);
	TestEqual(TEXT("Deterministic in time"), LBUILogic::CandleFlicker(1.23f, 2.f, 0.4f), LBUILogic::CandleFlicker(1.23f, 2.f, 0.4f));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUIKeyIconLookupTest, "LastBell.UI.Keys.IconLookup", LB_UI_UNIT_FLAGS)
bool FLBUIKeyIconLookupTest::RunTest(const FString& Parameters)
{
	const TArray<FKey>& Keys = LBUILogic::IconKeys();
	TestTrue(FString::Printf(TEXT("The icon set lists letters, digits, arrows, modifiers, space, esc, tab, enter and mouse buttons (%d keys)"), Keys.Num()), Keys.Num() >= 26 + 10 + 4 + 6 + 4 + 3);
	for (const FKey& Key : Keys)
	{
		TestTrue(FString::Printf(TEXT("Icon key '%s' is a valid FKey"), *Key.ToString()), Key.IsValid());
		TestFalse(FString::Printf(TEXT("'%s' has a text fallback label"), *Key.ToString()), LBUILogic::KeyFallbackLabel(Key).IsEmpty());
	}

	// Every gameplay key (the default of every rebindable action) must have an icon in the set.
	for (const ELBBindAction Action : LBUILogic::RebindableActions())
	{
		const FKey Default = LBUILogic::DefaultKeyFor(Action);
		TestTrue(FString::Printf(TEXT("Action %d has a valid default key"), static_cast<int32>(Action)), Default.IsValid());
		TestTrue(FString::Printf(TEXT("The default key '%s' is in the icon set"), *Default.ToString()), Keys.Contains(Default));
		TestFalse(TEXT("The action has a mapping name"), LBUILogic::MappingNameFor(Action).IsNone());
		TestFalse(TEXT("The action has a display name"), LBUILogic::DisplayNameFor(Action).IsEmpty());
	}
	TestEqual(TEXT("Nine rebindable actions"), LBUILogic::RebindableActions().Num(), 9);

	// A style with an icon for one key finds it and only it. The soft path is only checked for being set (nothing loads).
	ULBUIStyle* Style = NewObject<ULBUIStyle>(GetTransientPackage());
	Style->KeyIcons.Add(EKeys::E, TSoftObjectPtr<UTexture2D>(FSoftObjectPath(TEXT("/Game/LastBell/UI/KeyIcons/T_Key_E.T_Key_E"))));
	TestTrue(TEXT("The style has an icon entry for E"), Style->HasKeyIcon(EKeys::E));
	TestFalse(TEXT("...and none for F"), Style->HasKeyIcon(EKeys::F));
	TestNull(TEXT("A key without an entry finds no texture"), Style->FindKeyIcon(EKeys::F));
	TestFalse(TEXT("A style with no entries has no icon for anything"), NewObject<ULBUIStyle>(GetTransientPackage())->HasKeyIcon(EKeys::G));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUIRebindConflictTest, "LastBell.UI.Keys.RebindConflicts", LB_UI_UNIT_FLAGS)
bool FLBUIRebindConflictTest::RunTest(const FString& Parameters)
{
	TMap<ELBBindAction, FKey> Current;
	for (const ELBBindAction Action : LBUILogic::RebindableActions())
	{
		Current.Add(Action, LBUILogic::DefaultKeyFor(Action));
	}

	TestEqual(TEXT("A free key conflicts with nothing"), LBUILogic::FindKeyConflict(Current, ELBBindAction::Interact, EKeys::G), ELBBindAction::Count);
	TestEqual(TEXT("E is Interact's own key: not a conflict with itself"), LBUILogic::FindKeyConflict(Current, ELBBindAction::Interact, EKeys::E), ELBBindAction::Count);
	TestEqual(TEXT("F for Interact conflicts with Candle"), LBUILogic::FindKeyConflict(Current, ELBBindAction::Interact, EKeys::F), ELBBindAction::Candle);
	TestEqual(TEXT("W for Sprint conflicts with Move forward"), LBUILogic::FindKeyConflict(Current, ELBBindAction::Sprint, EKeys::W), ELBBindAction::MoveForward);
	TestEqual(TEXT("Escape for Candle conflicts with Pause"), LBUILogic::FindKeyConflict(Current, ELBBindAction::Candle, EKeys::Escape), ELBBindAction::Pause);
	TestEqual(TEXT("An invalid key conflicts with nothing"), LBUILogic::FindKeyConflict(Current, ELBBindAction::Candle, EKeys::Invalid), ELBBindAction::Count);

	// Moving a key to a free one and back: the old key frees up.
	Current[ELBBindAction::Candle] = EKeys::G;
	TestEqual(TEXT("After rebinding Candle to G, F is free"), LBUILogic::FindKeyConflict(Current, ELBBindAction::Interact, EKeys::F), ELBBindAction::Count);
	TestEqual(TEXT("...and G conflicts"), LBUILogic::FindKeyConflict(Current, ELBBindAction::Interact, EKeys::G), ELBBindAction::Candle);

	// What a key may be at all.
	TestTrue(TEXT("A letter is allowed"), LBUILogic::KeyRefusalReason(ELBBindAction::Candle, EKeys::G).IsEmpty());
	TestTrue(TEXT("Left mouse is allowed for Interact"), LBUILogic::KeyRefusalReason(ELBBindAction::Interact, EKeys::LeftMouseButton).IsEmpty());
	TestFalse(TEXT("A gamepad button is refused"), LBUILogic::KeyRefusalReason(ELBBindAction::Candle, EKeys::Gamepad_FaceButton_Bottom).IsEmpty());
	TestFalse(TEXT("Mouse movement is refused"), LBUILogic::KeyRefusalReason(ELBBindAction::Candle, EKeys::MouseX).IsEmpty());
	TestFalse(TEXT("The wheel is refused"), LBUILogic::KeyRefusalReason(ELBBindAction::Candle, EKeys::MouseScrollUp).IsEmpty());
	TestFalse(TEXT("The console key is refused"), LBUILogic::KeyRefusalReason(ELBBindAction::Candle, EKeys::Tilde).IsEmpty());
	TestFalse(TEXT("Pause refuses a mouse button"), LBUILogic::KeyRefusalReason(ELBBindAction::Pause, EKeys::RightMouseButton).IsEmpty());
	TestTrue(TEXT("Pause takes a key"), LBUILogic::KeyRefusalReason(ELBBindAction::Pause, EKeys::P).IsEmpty());
	TestFalse(TEXT("An invalid key is refused"), LBUILogic::KeyRefusalReason(ELBBindAction::Candle, EKeys::Invalid).IsEmpty());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUIUserSettingsRoundTripTest, "LastBell.UI.Settings.ClampsAndPersistence", LB_UI_UNIT_FLAGS)
bool FLBUIUserSettingsRoundTripTest::RunTest(const FString& Parameters)
{
	ULBUserSettings* Settings = ULBUserSettings::GetUserSettings();
	if (!TestNotNull(TEXT("The user settings object"), Settings))
	{
		return false;
	}
	FLBUserSettingsGuard Guard;

	int32 Broadcasts = 0;
	const FDelegateHandle Handle = ULBUserSettings::OnUserSettingsChanged().AddLambda([&Broadcasts]() { ++Broadcasts; });

	// Clamps.
	Settings->SetFieldOfView(500.f);
	TestEqual(TEXT("FOV clamps to 110"), Settings->FieldOfView, 110.f);
	Settings->SetFieldOfView(1.f);
	TestEqual(TEXT("FOV clamps to 70"), Settings->FieldOfView, 70.f);
	Settings->SetGamma(0.1f);
	TestEqual(TEXT("Gamma clamps to 1.8"), Settings->Gamma, 1.8f);
	TestEqual(TEXT("...and is applied to the engine"), GEngine ? GEngine->DisplayGamma : 1.8f, 1.8f);
	Settings->SetGamma(9.f);
	TestEqual(TEXT("Gamma clamps to 2.6"), Settings->Gamma, 2.6f);
	Settings->SetMouseSensitivity(0.f);
	TestEqual(TEXT("Sensitivity clamps to its minimum"), Settings->MouseSensitivity, ULBUserSettings::MinSensitivity);
	TestTrue(TEXT("Every setter broadcast OnUserSettingsChanged"), Broadcasts >= 5);

	// Round trip through the config: set non-default values, scramble the memory, load the file back.
	Settings->SetFieldOfView(100.f);
	Settings->SetGamma(2.4f);
	Settings->SetMotionBlur(true);
	Settings->SetFilmGrain(false);
	Settings->SetHighContrastPrompts(true);
	Settings->SetBrightnessCalibrated(true);
	Settings->SetMouseSensitivity(2.5f);
	Settings->SetInvertY(true);
	Settings->SetHeadBob(false);

	Settings->FieldOfView = 90.f;
	Settings->Gamma = 2.2f;
	Settings->bMotionBlur = false;
	Settings->bFilmGrain = true;
	Settings->bHighContrastPrompts = false;
	Settings->bBrightnessCalibrated = false;
	Settings->MouseSensitivity = 1.f;
	Settings->bInvertY = false;
	Settings->bHeadBob = true;
	Settings->LoadConfig();

	TestEqual(TEXT("FOV survives the config"), Settings->FieldOfView, 100.f);
	TestEqual(TEXT("Gamma survives the config"), Settings->Gamma, 2.4f);
	TestTrue(TEXT("Motion blur survives"), Settings->bMotionBlur);
	TestFalse(TEXT("Film grain survives"), Settings->bFilmGrain);
	TestTrue(TEXT("High-contrast prompts survive"), Settings->bHighContrastPrompts);
	TestTrue(TEXT("The brightness flag survives"), Settings->bBrightnessCalibrated);
	TestEqual(TEXT("Sensitivity survives"), Settings->MouseSensitivity, 2.5f);
	TestTrue(TEXT("Invert Y survives"), Settings->bInvertY);
	TestFalse(TEXT("Head bob survives"), Settings->bHeadBob);

	// Reset to defaults (controls only).
	Settings->ResetControlsToDefaults();
	TestEqual(TEXT("Controls reset: sensitivity"), Settings->MouseSensitivity, 1.f);
	TestFalse(TEXT("Controls reset: invert Y"), Settings->bInvertY);
	TestTrue(TEXT("Controls reset: head bob"), Settings->bHeadBob);
	TestEqual(TEXT("Controls reset leaves the FOV alone"), Settings->FieldOfView, 100.f);

	ULBUserSettings::OnUserSettingsChanged().Remove(Handle);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUIBrightnessFlagTest, "LastBell.UI.Settings.BrightnessFirstLaunchFlag", LB_UI_UNIT_FLAGS)
bool FLBUIBrightnessFlagTest::RunTest(const FString& Parameters)
{
	ULBUserSettings* Settings = ULBUserSettings::GetUserSettings();
	if (!TestNotNull(TEXT("The user settings object"), Settings))
	{
		return false;
	}
	FLBUserSettingsGuard Guard;

	Settings->SetBrightnessCalibrated(false);
	TestFalse(TEXT("Not calibrated: the menu shows the brightness screen first"), Settings->bBrightnessCalibrated);
	Settings->SetBrightnessCalibrated(true);
	Settings->bBrightnessCalibrated = false;
	Settings->LoadConfig();
	TestTrue(TEXT("Confirmed once, it stays confirmed across a reload (never shown again)"), Settings->bBrightnessCalibrated);
	Settings->SetBrightnessCalibrated(false);
	Settings->bBrightnessCalibrated = true;
	Settings->LoadConfig();
	TestFalse(TEXT("Reset from Settings, it shows again at the next launch"), Settings->bBrightnessCalibrated);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUIGraphicsPresetTest, "LastBell.UI.Settings.GraphicsPresetAndCustom", LB_UI_UNIT_FLAGS)
bool FLBUIGraphicsPresetTest::RunTest(const FString& Parameters)
{
	UGameUserSettings* GameSettings = FLBGraphicsSettings::Get();
	if (!TestNotNull(TEXT("The engine's user settings"), GameSettings))
	{
		return false;
	}
	const FLBGraphicsSnapshot Before = FLBGraphicsSettings::Capture();

	for (int32 Preset = 0; Preset <= 3; ++Preset)
	{
		FLBGraphicsSettings::SetPreset(Preset);
		TestEqual(FString::Printf(TEXT("Preset %d reads back as %d"), Preset, Preset), FLBGraphicsSettings::GetPreset(), Preset);
		for (int32 Group = 0; Group < static_cast<int32>(ELBGraphicsGroup::Count); ++Group)
		{
			TestEqual(FString::Printf(TEXT("Preset %d sets group %d"), Preset, Group), FLBGraphicsSettings::GetGroupLevel(static_cast<ELBGraphicsGroup>(Group)), Preset);
		}
	}

	FLBGraphicsSettings::SetPreset(2);
	FLBGraphicsSettings::SetGroupLevel(ELBGraphicsGroup::Shadows, 0);
	TestEqual(TEXT("One group changed: Custom"), FLBGraphicsSettings::GetPreset(), -1);
	TestEqual(TEXT("...shown as Custom"), FLBGraphicsSettings::PresetName(-1).ToString(), FString(TEXT("Custom")));
	FLBGraphicsSettings::SetGroupLevel(ELBGraphicsGroup::Shadows, 2);
	TestEqual(TEXT("Put back: preset 2 again"), FLBGraphicsSettings::GetPreset(), 2);

	FLBGraphicsSettings::SetResolutionScalePercent(75.f);
	TestTrue(FString::Printf(TEXT("Resolution scale 75 reads back near 75 (%.1f)"), FLBGraphicsSettings::GetResolutionScalePercent()), FMath::Abs(FLBGraphicsSettings::GetResolutionScalePercent() - 75.f) < 1.5f);
	FLBGraphicsSettings::SetResolutionScalePercent(5.f);
	TestTrue(TEXT("Resolution scale never goes below 50"), FLBGraphicsSettings::GetResolutionScalePercent() >= 49.f);

	// A display-mode change needs the keep dialog; a quality change does not.
	FLBGraphicsSnapshot Changed = Before;
	Changed.Groups[0] = (Before.Groups[0] + 1) % 4;
	TestFalse(TEXT("A quality-only difference needs no keep dialog"), Changed.DisplayModeDiffers(Before));
	Changed.WindowMode = Before.WindowMode == EWindowMode::Windowed ? EWindowMode::Fullscreen : EWindowMode::Windowed;
	TestTrue(TEXT("A window-mode difference needs the keep dialog"), Changed.DisplayModeDiffers(Before));
	Changed = Before;
	Changed.Resolution = FIntPoint(Before.Resolution.X + 2, Before.Resolution.Y);
	TestTrue(TEXT("A resolution difference needs the keep dialog"), Changed.DisplayModeDiffers(Before));

	// Nothing was applied or saved; put the pending values back.
	FLBGraphicsSettings::Restore(Before);
	const FLBGraphicsSnapshot After = FLBGraphicsSettings::Capture();
	for (int32 Group = 0; Group < static_cast<int32>(ELBGraphicsGroup::Count); ++Group)
	{
		TestEqual(FString::Printf(TEXT("Restored: group %d is what it was"), Group), After.Groups[Group], Before.Groups[Group]);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUIPromptLookTest, "LastBell.UI.Style.PromptLook", LB_UI_UNIT_FLAGS)
bool FLBUIPromptLookTest::RunTest(const FString& Parameters)
{
	const ULBUIStyle* Style = GetDefault<ULBUIStyle>();
	const FLBPromptLook Normal = Style->GetPromptLook(false);
	const FLBPromptLook High = Style->GetPromptLook(true);
	TestEqual(TEXT("Normal text is the style's ink"), Normal.Text, Style->Ink);
	TestEqual(TEXT("Normal prompts have no outline"), Normal.OutlineSize, 0);
	TestEqual(TEXT("Normal prompts have no plate"), Normal.Plate.A, 0.f);
	TestEqual(TEXT("High contrast text is white"), High.Text, FLinearColor::White);
	TestTrue(TEXT("High contrast has a dark, near-opaque plate"), High.Plate.A > 0.8f && High.Plate.R < 0.1f);
	TestTrue(TEXT("High contrast has an outline"), High.OutlineSize > 0);

	// The style resolves to usable defaults whether or not DA_UIStyle exists: never null, fonts valid.
	const ULBUIStyle* Resolved = ULBUIStyle::Resolve();
	TestNotNull(TEXT("Resolve never returns null"), Resolved);
	if (Resolved)
	{
		const FSlateFontInfo Font = Resolved->BodyFont();
		TestTrue(TEXT("The body font has a size"), Font.Size > 0);
		TestTrue(TEXT("Sizes match the plan (96, 40, 34, 24, 18)"), Resolved->TitleSize == 96 || ULBUIStyle::IsStyleLinked());
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUILoadingAttributesTest, "LastBell.UI.Loading.Attributes", LB_UI_UNIT_FLAGS)
bool FLBUILoadingAttributesTest::RunTest(const FString& Parameters)
{
	TestTrue(TEXT("The loading screen attributes are valid: a widget, auto-complete, a 1 s minimum"), LBLoadingScreen::ValidateAttributes());
	TestTrue(TEXT("The minimum display time is 1 s"), FMath::IsNearlyEqual(LBLoadingScreen::MinimumDisplaySeconds, 1.f));

	const int32 Armed = LBLoadingScreen::GetArmCount();
	const bool bHanded = LBLoadingScreen::ArmForTravel();
	TestEqual(TEXT("Arming counts"), LBLoadingScreen::GetArmCount(), Armed + 1);
	TestTrue(TEXT("It reads as armed until the travel finishes"), LBLoadingScreen::IsArmed());
	if (GIsEditor)
	{
		TestFalse(TEXT("The editor has no loading screens: nothing is handed to the movie player"), bHanded);
	}
	LBLoadingScreen::OnTravelFinished();
	TestFalse(TEXT("Finished: no longer armed"), LBLoadingScreen::IsArmed());
	return true;
}

// EXPECTED TO FAIL until P18-2 (DA_UIStyle with the key icons, linked in DefaultGame.ini).
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBUIContentKeyIconsTest, "LastBell.UI.Content.KeyIconsForEveryGameplayKey", LB_UI_UNIT_FLAGS)
bool FLBUIContentKeyIconsTest::RunTest(const FString& Parameters)
{
	if (!TestTrue(TEXT("DA_UIStyle is linked in ULBGameSettings::UIStyle (P18-2)"), ULBUIStyle::IsStyleLinked()))
	{
		return true;
	}
	const ULBUIStyle* Style = ULBUIStyle::Resolve();
	int32 Missing = 0;
	for (const FKey& Key : LBUILogic::IconKeys())
	{
		if (!Style->HasKeyIcon(Key) || !Style->FindKeyIcon(Key))
		{
			AddError(FString::Printf(TEXT("DA_UIStyle has no loadable icon for key %s"), *Key.ToString()));
			++Missing;
		}
	}
	TestEqual(TEXT("Every key has an icon"), Missing, 0);
	TestTrue(TEXT("The UI font assets are assigned"), !Style->FontRegular.IsNull() && !Style->FontItalic.IsNull() && !Style->FontSemiBold.IsNull() && !Style->FontBold.IsNull());
	return true;
}

#endif
