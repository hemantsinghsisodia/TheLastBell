#include "UI/LBGraphicsSettings.h"
#include "Engine/Engine.h"
#include "Kismet/KismetSystemLibrary.h"
#include "UI/LBUILogic.h"
#include "LBLog.h"

UGameUserSettings* FLBGraphicsSettings::Get()
{
	return GEngine ? GEngine->GetGameUserSettings() : nullptr;
}

int32 FLBGraphicsSettings::GetGroupLevel(ELBGraphicsGroup Group)
{
	const UGameUserSettings* Settings = Get();
	if (!Settings)
	{
		return 0;
	}
	switch (Group)
	{
	case ELBGraphicsGroup::ViewDistance: return Settings->GetViewDistanceQuality();
	case ELBGraphicsGroup::AntiAliasing: return Settings->GetAntiAliasingQuality();
	case ELBGraphicsGroup::Shadows: return Settings->GetShadowQuality();
	case ELBGraphicsGroup::GlobalIllumination: return Settings->GetGlobalIlluminationQuality();
	case ELBGraphicsGroup::Reflections: return Settings->GetReflectionQuality();
	case ELBGraphicsGroup::PostProcessing: return Settings->GetPostProcessingQuality();
	case ELBGraphicsGroup::Textures: return Settings->GetTextureQuality();
	case ELBGraphicsGroup::Effects: return Settings->GetVisualEffectQuality();
	case ELBGraphicsGroup::Foliage: return Settings->GetFoliageQuality();
	case ELBGraphicsGroup::Shading: return Settings->GetShadingQuality();
	default: return 0;
	}
}

void FLBGraphicsSettings::SetGroupLevel(ELBGraphicsGroup Group, int32 Level)
{
	UGameUserSettings* Settings = Get();
	if (!Settings)
	{
		return;
	}
	Level = FMath::Clamp(Level, 0, 3);
	switch (Group)
	{
	case ELBGraphicsGroup::ViewDistance: Settings->SetViewDistanceQuality(Level); break;
	case ELBGraphicsGroup::AntiAliasing: Settings->SetAntiAliasingQuality(Level); break;
	case ELBGraphicsGroup::Shadows: Settings->SetShadowQuality(Level); break;
	case ELBGraphicsGroup::GlobalIllumination: Settings->SetGlobalIlluminationQuality(Level); break;
	case ELBGraphicsGroup::Reflections: Settings->SetReflectionQuality(Level); break;
	case ELBGraphicsGroup::PostProcessing: Settings->SetPostProcessingQuality(Level); break;
	case ELBGraphicsGroup::Textures: Settings->SetTextureQuality(Level); break;
	case ELBGraphicsGroup::Effects: Settings->SetVisualEffectQuality(Level); break;
	case ELBGraphicsGroup::Foliage: Settings->SetFoliageQuality(Level); break;
	case ELBGraphicsGroup::Shading: Settings->SetShadingQuality(Level); break;
	default: break;
	}
}

FText FLBGraphicsSettings::GroupName(ELBGraphicsGroup Group)
{
	switch (Group)
	{
	case ELBGraphicsGroup::ViewDistance: return NSLOCTEXT("LastBellUI", "GfxViewDistance", "View distance");
	case ELBGraphicsGroup::AntiAliasing: return NSLOCTEXT("LastBellUI", "GfxAntiAliasing", "Anti-aliasing");
	case ELBGraphicsGroup::Shadows: return NSLOCTEXT("LastBellUI", "GfxShadows", "Shadows");
	case ELBGraphicsGroup::GlobalIllumination: return NSLOCTEXT("LastBellUI", "GfxGI", "Global illumination");
	case ELBGraphicsGroup::Reflections: return NSLOCTEXT("LastBellUI", "GfxReflections", "Reflections");
	case ELBGraphicsGroup::PostProcessing: return NSLOCTEXT("LastBellUI", "GfxPost", "Post-processing");
	case ELBGraphicsGroup::Textures: return NSLOCTEXT("LastBellUI", "GfxTextures", "Textures");
	case ELBGraphicsGroup::Effects: return NSLOCTEXT("LastBellUI", "GfxEffects", "Effects");
	case ELBGraphicsGroup::Foliage: return NSLOCTEXT("LastBellUI", "GfxFoliage", "Foliage");
	case ELBGraphicsGroup::Shading: return NSLOCTEXT("LastBellUI", "GfxShading", "Shading");
	default: return FText::GetEmpty();
	}
}

int32 FLBGraphicsSettings::GetPreset()
{
	TArray<int32> Levels;
	for (int32 Index = 0; Index < static_cast<int32>(ELBGraphicsGroup::Count); ++Index)
	{
		Levels.Add(GetGroupLevel(static_cast<ELBGraphicsGroup>(Index)));
	}
	return LBUILogic::DetectPreset(Levels);
}

void FLBGraphicsSettings::SetPreset(int32 Preset)
{
	if (UGameUserSettings* Settings = Get())
	{
		Settings->SetOverallScalabilityLevel(FMath::Clamp(Preset, 0, 3));
	}
}

void FLBGraphicsSettings::SetPresetKeepingScale(int32 Preset, float ChosenPercent)
{
	SetPreset(Preset);
	if (ChosenPercent >= 0.f)
	{
		SetResolutionScalePercent(ChosenPercent);
	}
}

const TArray<FText>& FLBGraphicsSettings::QualityLevelNames()
{
	static const TArray<FText> Names = {
		NSLOCTEXT("LastBellUI", "QualityLow", "Low"), NSLOCTEXT("LastBellUI", "QualityMedium", "Medium"),
		NSLOCTEXT("LastBellUI", "QualityHigh", "High"), NSLOCTEXT("LastBellUI", "QualityEpic", "Epic") };
	return Names;
}

FText FLBGraphicsSettings::PresetName(int32 Preset)
{
	return (Preset >= 0 && Preset <= 3) ? QualityLevelNames()[Preset] : NSLOCTEXT("LastBellUI", "QualityCustom", "Custom");
}

float FLBGraphicsSettings::GetResolutionScalePercent()
{
	float Normalized = 1.f;
	float Value = 100.f;
	float Min = 25.f;
	float Max = 100.f;
	if (const UGameUserSettings* Settings = Get())
	{
		Settings->GetResolutionScaleInformationEx(Normalized, Value, Min, Max);
	}
	return LBUILogic::ClampResolutionScale(Value);
}

void FLBGraphicsSettings::SetResolutionScalePercent(float Percent)
{
	if (UGameUserSettings* Settings = Get())
	{
		float Normalized = 1.f;
		float Value = 100.f;
		float Min = 25.f;
		float Max = 100.f;
		Settings->GetResolutionScaleInformationEx(Normalized, Value, Min, Max);
		Settings->SetResolutionScaleValueEx(FMath::Clamp(LBUILogic::ClampResolutionScale(Percent), Min, Max));
	}
}

EWindowMode::Type FLBGraphicsSettings::GetWindowMode()
{
	const UGameUserSettings* Settings = Get();
	return Settings ? Settings->GetFullscreenMode() : EWindowMode::Windowed;
}

void FLBGraphicsSettings::SetWindowMode(EWindowMode::Type Mode)
{
	if (UGameUserSettings* Settings = Get())
	{
		Settings->SetFullscreenMode(Mode);
	}
}

FIntPoint FLBGraphicsSettings::GetResolution()
{
	const UGameUserSettings* Settings = Get();
	return Settings ? Settings->GetScreenResolution() : FIntPoint(1920, 1080);
}

void FLBGraphicsSettings::SetResolution(const FIntPoint& Resolution)
{
	if (UGameUserSettings* Settings = Get())
	{
		Settings->SetScreenResolution(Resolution);
	}
}

TArray<FIntPoint> FLBGraphicsSettings::GetResolutionOptions(EWindowMode::Type Mode)
{
	TArray<FIntPoint> Supported;
	UKismetSystemLibrary::GetSupportedFullscreenResolutions(Supported);
	FIntPoint Desktop = FIntPoint::ZeroValue;
	if (const UGameUserSettings* Settings = Get())
	{
		Desktop = Settings->GetDesktopResolution();
	}
	// Fullscreen offers the monitor's own list; windowed and borderless clamp it to the desktop (a window cannot be larger than the screen).
	TArray<FIntPoint> Result = LBUILogic::ClampResolutionsToDesktop(Supported, Mode == EWindowMode::Fullscreen ? FIntPoint::ZeroValue : Desktop);
	const FIntPoint Current = GetResolution();
	if (Current.X > 0 && Current.Y > 0 && !Result.Contains(Current))
	{
		Result.Add(Current);
		Result.Sort([](const FIntPoint& A, const FIntPoint& B) { return A.X != B.X ? A.X < B.X : A.Y < B.Y; });
	}
	return Result;
}

bool FLBGraphicsSettings::GetVSync()
{
	const UGameUserSettings* Settings = Get();
	return Settings && Settings->IsVSyncEnabled();
}

void FLBGraphicsSettings::SetVSync(bool bEnabled)
{
	if (UGameUserSettings* Settings = Get())
	{
		Settings->SetVSyncEnabled(bEnabled);
	}
}

float FLBGraphicsSettings::GetFrameRateLimit()
{
	const UGameUserSettings* Settings = Get();
	return Settings ? Settings->GetFrameRateLimit() : 0.f;
}

void FLBGraphicsSettings::SetFrameRateLimit(float Limit)
{
	if (UGameUserSettings* Settings = Get())
	{
		Settings->SetFrameRateLimit(FMath::Max(Limit, 0.f));
	}
}

FLBGraphicsSnapshot FLBGraphicsSettings::Capture()
{
	FLBGraphicsSnapshot Snapshot;
	for (int32 Index = 0; Index < static_cast<int32>(ELBGraphicsGroup::Count); ++Index)
	{
		Snapshot.Groups[Index] = GetGroupLevel(static_cast<ELBGraphicsGroup>(Index));
	}
	Snapshot.ResolutionScaleValue = GetResolutionScalePercent();
	Snapshot.Resolution = GetResolution();
	Snapshot.WindowMode = GetWindowMode();
	Snapshot.bVSync = GetVSync();
	Snapshot.FrameRateLimit = GetFrameRateLimit();
	return Snapshot;
}

void FLBGraphicsSettings::Restore(const FLBGraphicsSnapshot& Snapshot)
{
	for (int32 Index = 0; Index < static_cast<int32>(ELBGraphicsGroup::Count); ++Index)
	{
		SetGroupLevel(static_cast<ELBGraphicsGroup>(Index), Snapshot.Groups[Index]);
	}
	SetResolutionScalePercent(Snapshot.ResolutionScaleValue);
	SetWindowMode(Snapshot.WindowMode);
	SetResolution(Snapshot.Resolution);
	SetVSync(Snapshot.bVSync);
	SetFrameRateLimit(Snapshot.FrameRateLimit);
}

bool FLBGraphicsSettings::Apply(const FLBGraphicsSnapshot& Before)
{
	UGameUserSettings* Settings = Get();
	if (!Settings)
	{
		return false;
	}
	const bool bNeedsKeep = Capture().DisplayModeDiffers(Before);
	Settings->ApplySettings(/*bCheckForCommandLineOverrides*/ false);
	if (!bNeedsKeep)
	{
		// Nothing to confirm: the applied mode is the confirmed one.
		Settings->ConfirmVideoMode();
	}
	return bNeedsKeep;
}

void FLBGraphicsSettings::Confirm()
{
	if (UGameUserSettings* Settings = Get())
	{
		Settings->ConfirmVideoMode();
		Settings->SaveSettings();
	}
}

void FLBGraphicsSettings::Revert(const FLBGraphicsSnapshot& Snapshot)
{
	UGameUserSettings* Settings = Get();
	if (!Settings)
	{
		return;
	}
	Restore(Snapshot);
	Settings->ApplySettings(/*bCheckForCommandLineOverrides*/ false);
	Settings->ConfirmVideoMode();
}

void FLBGraphicsSettings::DiscardPending()
{
	if (UGameUserSettings* Settings = Get())
	{
		Settings->LoadSettings(/*bForceReload*/ true);
	}
}
