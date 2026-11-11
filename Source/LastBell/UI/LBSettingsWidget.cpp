#include "UI/LBSettingsWidget.h"
#include "Audio/LBAudioTypes.h"
#include "Blueprint/WidgetTree.h"
#include "Brushes/SlateNoResource.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/LocalPlayer.h"
#include "Input/Events.h"
#include "Systems/LBUserSettings.h"
#include "UI/LBKeyBindings.h"
#include "UI/LBUIBuild.h"
#include "UI/LBUILogic.h"
#include "UI/LBUISubsystem.h"

namespace
{
	FText TabName(ELBSettingsTab Tab)
	{
		switch (Tab)
		{
		case ELBSettingsTab::Graphics: return NSLOCTEXT("LastBellUI", "TabGraphics", "Graphics");
		case ELBSettingsTab::Display: return NSLOCTEXT("LastBellUI", "TabDisplay", "Display");
		case ELBSettingsTab::Audio: return NSLOCTEXT("LastBellUI", "TabAudio", "Audio");
		case ELBSettingsTab::Controls: return NSLOCTEXT("LastBellUI", "TabControls", "Controls");
		case ELBSettingsTab::Accessibility: return NSLOCTEXT("LastBellUI", "TabAccessibility", "Accessibility");
		}
		return FText::GetEmpty();
	}

	constexpr int32 TabCount = 5;

	FText Percent(float Value)
	{
		return FText::Format(NSLOCTEXT("LastBellUI", "PercentFormat", "{0}%"), FText::AsNumber(FMath::RoundToInt(Value)));
	}

	FText OneDecimal(float Value)
	{
		return FText::AsNumber(Value, &FNumberFormattingOptions().SetMinimumFractionalDigits(1).SetMaximumFractionalDigits(1));
	}

	FText Resolution(const FIntPoint& Size)
	{
		return FText::FromString(FString::Printf(TEXT("%d x %d"), Size.X, Size.Y));
	}

	int32 WindowModeToIndex(EWindowMode::Type Mode)
	{
		switch (Mode)
		{
		case EWindowMode::Fullscreen: return 0;
		case EWindowMode::WindowedFullscreen: return 1;
		default: return 2;
		}
	}

	EWindowMode::Type IndexToWindowMode(int32 Index)
	{
		switch (Index)
		{
		case 0: return EWindowMode::Fullscreen;
		case 1: return EWindowMode::WindowedFullscreen;
		default: return EWindowMode::Windowed;
		}
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Frame
// ---------------------------------------------------------------------------------------------------------------------

void ULBSettingsWidget::BuildScreen(UOverlay& RootOverlay)
{
	const ULBUIStyle& Style = GetStyle();
	RowTextSize = Style.BodySize + 2;
	Backdrop->SetColorAndOpacity(FLinearColor(0.f, 0.f, 0.f, 0.9f));
	GfxBaseline = FLBGraphicsSettings::Capture();

	UVerticalBox* Frame = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("Frame"));
	USizeBox* FrameWidth = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
	FrameWidth->SetWidthOverride(1100.f);
	FrameWidth->AddChild(Frame);
	if (UOverlaySlot* FrameSlot = RootOverlay.AddChildToOverlay(FrameWidth))
	{
		FrameSlot->SetHorizontalAlignment(HAlign_Center);
		FrameSlot->SetVerticalAlignment(VAlign_Top);
		FrameSlot->SetPadding(FMargin(0.f, 56.f, 0.f, 0.f));
	}

	UTextBlock* Title = LBUIBuild::MakeText(*WidgetTree, NSLOCTEXT("LastBellUI", "SettingsTitle", "Settings"), Style.HeadingFont(), Style.Ink);
	if (UVerticalBoxSlot* TitleSlot = Frame->AddChildToVerticalBox(Title))
	{
		TitleSlot->SetPadding(FMargin(0.f, 0.f, 0.f, 18.f));
	}

	// The tab bar: five clickable names.
	TabBar = WidgetTree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass(), TEXT("TabBar"));
	if (UVerticalBoxSlot* BarSlot = Frame->AddChildToVerticalBox(TabBar))
	{
		BarSlot->SetPadding(FMargin(0.f, 0.f, 0.f, 22.f));
	}
	for (int32 Index = 0; Index < TabCount; ++Index)
	{
		ULBMenuButton* Button = WidgetTree->ConstructWidget<ULBMenuButton>(ULBMenuButton::StaticClass());
		FButtonStyle ButtonStyle;
		ButtonStyle.SetNormal(FSlateNoResource());
		ButtonStyle.SetHovered(FSlateNoResource());
		ButtonStyle.SetPressed(FSlateNoResource());
		ButtonStyle.SetDisabled(FSlateNoResource());
		ButtonStyle.SetNormalPadding(FMargin(0.f));
		ButtonStyle.SetPressedPadding(FMargin(0.f));
		Button->SetStyle(ButtonStyle);
		Button->OnClickNative = [this, Index]() { SwitchTab(static_cast<ELBSettingsTab>(Index)); };
		UTextBlock* Label = LBUIBuild::MakeText(*WidgetTree, TabName(static_cast<ELBSettingsTab>(Index)), Style.MakeFont(ELBFontWeight::SemiBold, Style.BodySize + 2), Style.Dim);
		Button->SetContent(Label);
		if (UHorizontalBoxSlot* TabSlot = TabBar->AddChildToHorizontalBox(Button))
		{
			TabSlot->SetPadding(FMargin(0.f, 0.f, 44.f, 0.f));
		}
		TabButtons.Add(Button);
		TabLabels.Add(Label);
	}

	TabContent = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("TabContent"));
	Frame->AddChildToVerticalBox(TabContent);

	StatusText = LBUIBuild::MakeText(*WidgetTree, FText::GetEmpty(), Style.BodyFont(), Style.Danger);
	if (UVerticalBoxSlot* StatusSlot = Frame->AddChildToVerticalBox(StatusText))
	{
		StatusSlot->SetPadding(FMargin(0.f, 14.f, 0.f, 0.f));
	}

	RebuildTab();
}

void ULBSettingsWidget::RefreshTabBar()
{
	const ULBUIStyle& Style = GetStyle();
	for (int32 Index = 0; Index < TabLabels.Num(); ++Index)
	{
		if (TabLabels[Index])
		{
			TabLabels[Index]->SetColorAndOpacity(FSlateColor(Index == static_cast<int32>(ActiveTab) ? Style.Accent : Style.Dim));
		}
	}
}

void ULBSettingsWidget::SwitchTab(ELBSettingsTab Tab)
{
	if (IsCapturingKey())
	{
		EndKeyCapture();
	}
	if (Tab == ActiveTab)
	{
		return;
	}
	// Unapplied graphics changes do not follow the player to another tab.
	if (ActiveTab == ELBSettingsTab::Graphics || ActiveTab == ELBSettingsTab::Display)
	{
		FLBGraphicsSettings::Restore(GfxBaseline);
	}
	ActiveTab = Tab;
	PlaySound(ELBUISound::Select);
	RebuildTab();
}

void ULBSettingsWidget::RebuildTab()
{
	if (!TabContent)
	{
		return;
	}
	TabContent->ClearChildren();
	ClearItems();
	GroupItems.Reset();
	PresetItem = INDEX_NONE;
	SetStatus(FText::GetEmpty());
	RefreshTabBar();

	switch (ActiveTab)
	{
	case ELBSettingsTab::Graphics: BuildGraphicsTab(); break;
	case ELBSettingsTab::Display: BuildDisplayTab(); break;
	case ELBSettingsTab::Audio: BuildAudioTab(); break;
	case ELBSettingsTab::Controls: BuildControlsTab(); break;
	case ELBSettingsTab::Accessibility: BuildAccessibilityTab(); break;
	}
	MoveSelection(1);
}

void ULBSettingsWidget::SetStatus(const FText& Text)
{
	if (StatusText)
	{
		StatusText->SetText(Text);
	}
}

FText ULBSettingsWidget::GetStatusTextForTest() const
{
	return StatusText ? StatusText->GetText() : FText::GetEmpty();
}

void ULBSettingsWidget::AddCaption(const FText& Text)
{
	const ULBUIStyle& Style = GetStyle();
	UTextBlock* Caption = LBUIBuild::MakeText(*WidgetTree, Text, Style.SmallFont(), Style.Dim);
	if (UVerticalBoxSlot* CaptionSlot = TabContent->AddChildToVerticalBox(Caption))
	{
		CaptionSlot->SetPadding(FMargin(0.f, 12.f, 0.f, 4.f));
	}
}

void ULBSettingsWidget::AddFooter(bool bApplyRevert)
{
	TWeakObjectPtr<ULBSettingsWidget> WeakThis(this);
	if (bApplyRevert)
	{
		AddButtonItem(*TabContent, NSLOCTEXT("LastBellUI", "SettingsApply", "Apply"), [WeakThis]()
		{
			if (WeakThis.IsValid())
			{
				WeakThis->ApplyGraphics();
			}
		});
		AddButtonItem(*TabContent, NSLOCTEXT("LastBellUI", "SettingsRevert", "Revert"), [WeakThis]()
		{
			if (WeakThis.IsValid())
			{
				WeakThis->RevertGraphics();
			}
		});
	}
	AddButtonItem(*TabContent, NSLOCTEXT("LastBellUI", "SettingsBack", "Back"), [WeakThis]()
	{
		if (WeakThis.IsValid())
		{
			WeakThis->HandleBack();
		}
	});
}

bool ULBSettingsWidget::HandleBack()
{
	if (IsCapturingKey())
	{
		EndKeyCapture();
		return true;
	}
	// Unapplied graphics and display changes are discarded.
	FLBGraphicsSettings::Restore(GfxBaseline);
	return Super::HandleBack();
}

FReply ULBSettingsWidget::NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent)
{
	if (!IsCapturingKey() && !InKeyEvent.IsRepeat())
	{
		const FKey Key = InKeyEvent.GetKey();
		const int32 Current = static_cast<int32>(ActiveTab);
		if (Key == EKeys::PageUp || Key == EKeys::Q || (Key == EKeys::Tab && InKeyEvent.IsShiftDown()))
		{
			SwitchTab(static_cast<ELBSettingsTab>((Current + TabCount - 1) % TabCount));
			return FReply::Handled();
		}
		if (Key == EKeys::PageDown || Key == EKeys::E || Key == EKeys::Tab)
		{
			SwitchTab(static_cast<ELBSettingsTab>((Current + 1) % TabCount));
			return FReply::Handled();
		}
	}
	return Super::NativeOnKeyDown(InGeometry, InKeyEvent);
}

// ---------------------------------------------------------------------------------------------------------------------
// Graphics
// ---------------------------------------------------------------------------------------------------------------------

void ULBSettingsWidget::UpdatePresetItem()
{
	if (PresetItem != INDEX_NONE)
	{
		const int32 Preset = FLBGraphicsSettings::GetPreset();
		SetChoiceIndex(PresetItem, Preset < 0 ? 4 : Preset, false);
	}
}

void ULBSettingsWidget::RefreshGroupRows()
{
	for (int32 Group = 0; Group < GroupItems.Num(); ++Group)
	{
		SetChoiceIndex(GroupItems[Group], FLBGraphicsSettings::GetGroupLevel(static_cast<ELBGraphicsGroup>(Group)), false);
	}
	UpdatePresetItem();
}

void ULBSettingsWidget::BuildGraphicsTab()
{
	const TArray<FText>& Levels = FLBGraphicsSettings::QualityLevelNames();
	TArray<FText> PresetOptions = Levels;
	PresetOptions.Add(FLBGraphicsSettings::PresetName(-1));

	const int32 Preset = FLBGraphicsSettings::GetPreset();
	PresetItem = AddChoiceItem(*TabContent, NSLOCTEXT("LastBellUI", "GfxPreset", "Quality preset"), PresetOptions, Preset < 0 ? 4 : Preset, [this](int32 NewIndex)
	{
		if (NewIndex <= 3)
		{
			FLBGraphicsSettings::SetPreset(NewIndex);
			RefreshGroupRows();
		}
		else
		{
			// "Custom" is a state, not a choice: it shows when the groups differ.
			UpdatePresetItem();
		}
	}, /*SelectableCount*/ 4);

	AddSliderItem(*TabContent, NSLOCTEXT("LastBellUI", "GfxResolutionScale", "Resolution scale"), LBUILogic::MinResolutionScale, LBUILogic::MaxResolutionScale, 5.f,
		FLBGraphicsSettings::GetResolutionScalePercent(), [](float Value) { return Percent(Value); },
		[](float Value, bool) { FLBGraphicsSettings::SetResolutionScalePercent(Value); });

	for (int32 Group = 0; Group < static_cast<int32>(ELBGraphicsGroup::Count); ++Group)
	{
		const ELBGraphicsGroup GroupId = static_cast<ELBGraphicsGroup>(Group);
		GroupItems.Add(AddChoiceItem(*TabContent, FLBGraphicsSettings::GroupName(GroupId), Levels, FLBGraphicsSettings::GetGroupLevel(GroupId), [this, GroupId](int32 NewIndex)
		{
			FLBGraphicsSettings::SetGroupLevel(GroupId, NewIndex);
			UpdatePresetItem();
		}));
	}
	AddFooter(true);
}

void ULBSettingsWidget::ApplyGraphics()
{
	const bool bNeedsKeep = FLBGraphicsSettings::Apply(GfxBaseline);
	if (!bNeedsKeep)
	{
		GfxBaseline = FLBGraphicsSettings::Capture();
		return;
	}

	const FLBGraphicsSnapshot Previous = GfxBaseline;
	TWeakObjectPtr<ULBSettingsWidget> WeakThis(this);
	FLBConfirmRequest Request;
	Request.Title = NSLOCTEXT("LastBellUI", "KeepTitle", "Keep these display settings?");
	Request.Message = NSLOCTEXT("LastBellUI", "KeepMessage", "The display mode changed.");
	Request.ConfirmLabel = NSLOCTEXT("LastBellUI", "KeepConfirm", "Keep");
	Request.CancelLabel = NSLOCTEXT("LastBellUI", "KeepRevert", "Revert");
	Request.TimeoutSeconds = LBUILogic::KeepDialogSeconds;
	Request.bTimeoutConfirms = false;
	Request.OnConfirm = [WeakThis]()
	{
		FLBGraphicsSettings::Confirm();
		if (WeakThis.IsValid())
		{
			WeakThis->GfxBaseline = FLBGraphicsSettings::Capture();
		}
	};
	Request.OnCancel = [WeakThis, Previous]()
	{
		FLBGraphicsSettings::Revert(Previous);
		if (WeakThis.IsValid())
		{
			WeakThis->GfxBaseline = Previous;
			WeakThis->RebuildTab();
		}
	};
	if (ULBUISubsystem* UI = GetUI())
	{
		UI->ShowConfirm(Request);
	}
	else
	{
		// No UI to ask: keep nothing that was not confirmed.
		Request.OnCancel();
	}
}

void ULBSettingsWidget::RevertGraphics()
{
	FLBGraphicsSettings::Restore(GfxBaseline);
	RebuildTab();
}

// ---------------------------------------------------------------------------------------------------------------------
// Display
// ---------------------------------------------------------------------------------------------------------------------

void ULBSettingsWidget::BuildDisplayTab()
{
	const TArray<FText> ModeNames = {
		NSLOCTEXT("LastBellUI", "ModeFullscreen", "Fullscreen"),
		NSLOCTEXT("LastBellUI", "ModeBorderless", "Windowed fullscreen"),
		NSLOCTEXT("LastBellUI", "ModeWindowed", "Windowed") };
	AddChoiceItem(*TabContent, NSLOCTEXT("LastBellUI", "DisplayWindowMode", "Window mode"), ModeNames, WindowModeToIndex(FLBGraphicsSettings::GetWindowMode()), [this](int32 NewIndex)
	{
		FLBGraphicsSettings::SetWindowMode(IndexToWindowMode(NewIndex));
		// The resolution list depends on the mode.
		RebuildTab();
	});

	const EWindowMode::Type Mode = FLBGraphicsSettings::GetWindowMode();
	ResolutionOptions = FLBGraphicsSettings::GetResolutionOptions(Mode);
	TArray<FText> ResolutionNames;
	for (const FIntPoint& Size : ResolutionOptions)
	{
		ResolutionNames.Add(Resolution(Size));
	}
	if (!ResolutionNames.IsEmpty())
	{
		const int32 Current = ResolutionOptions.IndexOfByKey(FLBGraphicsSettings::GetResolution());
		AddChoiceItem(*TabContent, NSLOCTEXT("LastBellUI", "DisplayResolution", "Resolution"), ResolutionNames, Current == INDEX_NONE ? 0 : Current, [this](int32 NewIndex)
		{
			if (ResolutionOptions.IsValidIndex(NewIndex))
			{
				FLBGraphicsSettings::SetResolution(ResolutionOptions[NewIndex]);
			}
		});
	}

	AddToggleItem(*TabContent, NSLOCTEXT("LastBellUI", "DisplayVSync", "VSync"), FLBGraphicsSettings::GetVSync(), [](bool bOn) { FLBGraphicsSettings::SetVSync(bOn); });

	TArray<FText> LimitNames;
	for (const int32 Limit : LBUILogic::FrameLimitOptions())
	{
		LimitNames.Add(Limit == 0 ? NSLOCTEXT("LastBellUI", "FrameUnlimited", "Unlimited") : FText::AsNumber(Limit));
	}
	AddChoiceItem(*TabContent, NSLOCTEXT("LastBellUI", "DisplayFrameLimit", "Frame-rate limit"), LimitNames,
		LBUILogic::NearestFrameLimitIndex(FLBGraphicsSettings::GetFrameRateLimit()), [](int32 NewIndex)
	{
		const TArray<int32>& Options = LBUILogic::FrameLimitOptions();
		if (Options.IsValidIndex(NewIndex))
		{
			FLBGraphicsSettings::SetFrameRateLimit(static_cast<float>(Options[NewIndex]));
		}
	});

	// Saves at once, like the other settings that are not Apply / Revert: a counter in the HUD's top-right corner.
	const ULBUserSettings* User = ULBUserSettings::Get();
	AddToggleItem(*TabContent, NSLOCTEXT("LastBellUI", "DisplayShowFPS", "Show FPS counter"), User && User->bShowFPS, [](bool bOn)
	{
		if (ULBUserSettings* Settings = ULBUserSettings::GetUserSettings())
		{
			Settings->SetShowFPS(bOn);
		}
	});

	TWeakObjectPtr<ULBSettingsWidget> WeakThis(this);
	AddButtonItem(*TabContent, NSLOCTEXT("LastBellUI", "DisplayBrightness", "Brightness..."), [WeakThis]()
	{
		if (ULBUISubsystem* UI = WeakThis.IsValid() ? WeakThis->GetUI() : nullptr)
		{
			UI->OpenBrightness(/*bFirstLaunch*/ false);
		}
	});
	AddFooter(true);
}

// ---------------------------------------------------------------------------------------------------------------------
// Audio
// ---------------------------------------------------------------------------------------------------------------------

void ULBSettingsWidget::BuildAudioTab()
{
	struct FGroup
	{
		ELBAudioVolumeGroup Group;
		FText Name;
	};
	const TArray<FGroup> Groups = {
		{ ELBAudioVolumeGroup::Master, NSLOCTEXT("LastBellUI", "VolMaster", "Master") },
		{ ELBAudioVolumeGroup::SFX, NSLOCTEXT("LastBellUI", "VolSFX", "Effects") },
		{ ELBAudioVolumeGroup::Ambience, NSLOCTEXT("LastBellUI", "VolAmbience", "Ambience") },
		{ ELBAudioVolumeGroup::Music, NSLOCTEXT("LastBellUI", "VolMusic", "Music") },
		{ ELBAudioVolumeGroup::Voice, NSLOCTEXT("LastBellUI", "VolVoice", "Voice") },
		{ ELBAudioVolumeGroup::UI, NSLOCTEXT("LastBellUI", "VolUI", "Interface") } };

	const ULBUserSettings* User = ULBUserSettings::Get();
	for (const FGroup& Entry : Groups)
	{
		const ELBAudioVolumeGroup Group = Entry.Group;
		AddSliderItem(*TabContent, Entry.Name, 0.f, 100.f, 5.f, User ? User->GetVolume(Group) * 100.f : 100.f, [](float Value) { return Percent(Value); },
			[Group](float Value, bool bFinal)
		{
			if (ULBUserSettings* Settings = ULBUserSettings::GetUserSettings())
			{
				// Live while dragging, saved on release.
				if (bFinal)
				{
					Settings->SetVolume(Group, Value / 100.f);
				}
				else
				{
					Settings->SetVolumeTransient(Group, Value / 100.f);
				}
			}
		});
	}
	AddFooter(false);
}

// ---------------------------------------------------------------------------------------------------------------------
// Controls
// ---------------------------------------------------------------------------------------------------------------------

void ULBSettingsWidget::BuildControlsTab()
{
	const ULBUserSettings* User = ULBUserSettings::Get();
	AddSliderItem(*TabContent, NSLOCTEXT("LastBellUI", "CtrlSensitivity", "Mouse sensitivity"), 0.1f, 5.f, 0.1f, User ? User->MouseSensitivity : 1.f,
		[](float Value) { return OneDecimal(Value); },
		[](float Value, bool bFinal)
	{
		if (ULBUserSettings* Settings = ULBUserSettings::GetUserSettings())
		{
			if (bFinal)
			{
				Settings->SetMouseSensitivity(Value);
			}
			else
			{
				Settings->SetMouseSensitivityTransient(Value);
			}
		}
	});
	AddToggleItem(*TabContent, NSLOCTEXT("LastBellUI", "CtrlInvertY", "Invert Y"), User && User->bInvertY, [](bool bOn)
	{
		if (ULBUserSettings* Settings = ULBUserSettings::GetUserSettings())
		{
			Settings->SetInvertY(bOn);
		}
	});
	AddToggleItem(*TabContent, NSLOCTEXT("LastBellUI", "CtrlHeadBob", "Head bob"), !User || User->bHeadBob, [](bool bOn)
	{
		if (ULBUserSettings* Settings = ULBUserSettings::GetUserSettings())
		{
			Settings->SetHeadBob(bOn);
		}
	});

	AddCaption(NSLOCTEXT("LastBellUI", "CtrlKeys", "Key bindings (select a row and press the new key; Esc cancels)"));
	for (const ELBBindAction Action : LBUILogic::RebindableActions())
	{
		AddKeyItem(*TabContent, LBUILogic::DisplayNameFor(Action), Action);
	}

	TWeakObjectPtr<ULBSettingsWidget> WeakThis(this);
	AddButtonItem(*TabContent, NSLOCTEXT("LastBellUI", "CtrlReset", "Reset to defaults"), [WeakThis]()
	{
		if (WeakThis.IsValid())
		{
			WeakThis->ResetControls();
		}
	});
	AddFooter(false);
}

void ULBSettingsWidget::ResetControls()
{
	if (ULBUserSettings* Settings = ULBUserSettings::GetUserSettings())
	{
		Settings->ResetControlsToDefaults();
	}
	LBKeyBindings::ResetAll(GetOwningLocalPlayer());
	RebuildTab();
}

bool ULBSettingsWidget::OnKeyCaptured(int32 ItemIndex, const FKey& Key)
{
	const FLBMenuItem* Item = GetItem(ItemIndex);
	if (!Item || Item->Kind != ELBMenuItemKind::KeyBinding)
	{
		return true;
	}
	const ELBBindAction Action = Item->BindAction;
	if (Key == EKeys::Escape && Action != ELBBindAction::Pause)
	{
		// Escape cancels a capture (only the Pause action can take it).
		SetStatus(FText::GetEmpty());
		return true;
	}
	const LBKeyBindings::FRebindResult Result = LBKeyBindings::Rebind(GetOwningLocalPlayer(), Action, Key);
	SetStatus(Result.bOk ? FText::GetEmpty() : Result.Message);
	PlaySound(Result.bOk ? ELBUISound::Select : ELBUISound::Back);
	RefreshKeyItem(ItemIndex);
	return true;
}

int32 ULBSettingsWidget::FindKeyItem(ELBBindAction Action) const
{
	for (int32 Index = 0; Index < GetItemCount(); ++Index)
	{
		const FLBMenuItem* Item = GetItem(Index);
		if (Item && Item->Kind == ELBMenuItemKind::KeyBinding && Item->BindAction == Action)
		{
			return Index;
		}
	}
	return INDEX_NONE;
}

void ULBSettingsWidget::CaptureKeyForTest(ELBBindAction Action, const FKey& Key)
{
	const int32 Item = FindKeyItem(Action);
	if (Item == INDEX_NONE)
	{
		return;
	}
	BeginKeyCapture(Item);
	if (OnKeyCaptured(Item, Key))
	{
		EndKeyCapture();
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Accessibility
// ---------------------------------------------------------------------------------------------------------------------

void ULBSettingsWidget::BuildAccessibilityTab()
{
	const ULBUserSettings* User = ULBUserSettings::Get();
	AddSliderItem(*TabContent, NSLOCTEXT("LastBellUI", "AccFOV", "Field of view"), LBUILogic::MinFOV, LBUILogic::MaxFOV, 1.f, User ? User->FieldOfView : LBUILogic::DefaultFOV,
		[](float Value) { return FText::Format(NSLOCTEXT("LastBellUI", "DegreesFormat", "{0} deg"), FText::AsNumber(FMath::RoundToInt(Value))); },
		[](float Value, bool bFinal)
	{
		if (ULBUserSettings* Settings = ULBUserSettings::GetUserSettings())
		{
			if (bFinal)
			{
				Settings->SetFieldOfView(Value);
			}
			else
			{
				Settings->SetFieldOfViewTransient(Value);
			}
		}
	});
	AddToggleItem(*TabContent, NSLOCTEXT("LastBellUI", "AccMotionBlur", "Motion blur"), User && User->bMotionBlur, [](bool bOn)
	{
		if (ULBUserSettings* Settings = ULBUserSettings::GetUserSettings())
		{
			Settings->SetMotionBlur(bOn);
		}
	});
	AddToggleItem(*TabContent, NSLOCTEXT("LastBellUI", "AccFilmGrain", "Film grain"), !User || User->bFilmGrain, [](bool bOn)
	{
		if (ULBUserSettings* Settings = ULBUserSettings::GetUserSettings())
		{
			Settings->SetFilmGrain(bOn);
		}
	});
	AddToggleItem(*TabContent, NSLOCTEXT("LastBellUI", "AccHighContrast", "High-contrast prompts"), User && User->bHighContrastPrompts, [](bool bOn)
	{
		if (ULBUserSettings* Settings = ULBUserSettings::GetUserSettings())
		{
			Settings->SetHighContrastPrompts(bOn);
		}
	});
	AddToggleItem(*TabContent, NSLOCTEXT("LastBellUI", "AccShowBrightness", "Show brightness screen at next launch"), User && !User->bBrightnessCalibrated, [](bool bOn)
	{
		if (ULBUserSettings* Settings = ULBUserSettings::GetUserSettings())
		{
			Settings->SetBrightnessCalibrated(!bOn);
		}
	});
	AddFooter(false);
}
