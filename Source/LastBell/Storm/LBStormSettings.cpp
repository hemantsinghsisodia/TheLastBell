#include "Storm/LBStormSettings.h"
#include "LBLog.h"

namespace
{
	/** Resolves a tag by name without an error when the project does not know it. An invalid tag is skipped by the caller. */
	FGameplayTag FindTag(const TCHAR* Name)
	{
		const FGameplayTag Tag = FGameplayTag::RequestGameplayTag(FName(Name), /*ErrorIfNotFound*/ false);
		if (!Tag.IsValid())
		{
			UE_LOG(LogLB, Warning, TEXT("ULBStormSettings::FillPlanTagDefaults: tag '%s' is not registered; its entry is skipped"), Name);
		}
		return Tag;
	}
}

void ULBStormSettings::FillPlanTagDefaults()
{
	StoryIntensity.Reset();
	ScriptedStrikes.Reset();

	// Plan 5.2: the story arc, in story order.
	struct FStoryRow
	{
		const TCHAR* Tag;
		float Intensity;
	};
	static const FStoryRow Story[] = {
		{ TEXT("State.Event.CourtyardEntered"), 0.60f },
		{ TEXT("State.Ritual.1"), 0.55f },
		{ TEXT("State.Event.CryptEntered"), 0.50f },
		{ TEXT("State.Ritual.2"), 0.65f },
		{ TEXT("State.Event.CloisterEntered"), 0.80f },
		{ TEXT("State.Ritual.3"), 0.90f },
		{ TEXT("State.Event.TowerTop"), 1.00f },
		{ TEXT("State.Event.Finale"), 1.00f },
	};
	for (const FStoryRow& Row : Story)
	{
		const FGameplayTag Tag = FindTag(Row.Tag);
		if (Tag.IsValid())
		{
			FLBStormStoryStep& Step = StoryIntensity.AddDefaulted_GetRef();
			Step.Tag = Tag;
			Step.Intensity = Row.Intensity;
		}
	}

	// Plan 5.6b: the scripted strikes. Profile Double throughout, Triple for the second TowerTop strike. P15: the arrival and TowerTop
	// strikes hit the actor tagged LB_StrikeTarget_Tower (the top of the bell tower).
	auto AddStrike = [this](const TCHAR* TagName, float Delay, int32 Count, float Spacing) -> FLBStormStrike*
	{
		const FGameplayTag Tag = FindTag(TagName);
		if (!Tag.IsValid())
		{
			return nullptr;
		}
		FLBStormStrike& Strike = ScriptedStrikes.AddDefaulted_GetRef();
		Strike.TriggerTag = Tag;
		Strike.Delay = Delay;
		Strike.Count = Count;
		Strike.Spacing = Spacing;
		Strike.Brightness = 1.f;
		Strike.Profile = ELBFlashProfile::Double;
		return &Strike;
	};

	if (FLBStormStrike* Arrival = AddStrike(TEXT("State.Event.CourtyardEntered"), 0.4f, 2, 1.6f))
	{
		Arrival->bLookGate = true;
		Arrival->LookTarget = FVector(12500.0, 2000.0, 3800.0);
		Arrival->LookConeDegrees = 20.f;
		Arrival->LookTimeout = 90.f;
		Arrival->StrikeTargetTag = TEXT("LB_StrikeTarget_Tower");
	}
	AddStrike(TEXT("State.Ritual.1"), 1.2f, 1, 0.f);
	AddStrike(TEXT("State.Ritual.2"), 1.2f, 1, 0.f);
	AddStrike(TEXT("State.Ritual.3"), 1.2f, 1, 0.f);
	if (FLBStormStrike* TowerTop = AddStrike(TEXT("State.Event.TowerTop"), 2.0f, 3, 2.5f))
	{
		TowerTop->ProfileOverrides = { ELBFlashProfile::Double, ELBFlashProfile::Triple, ELBFlashProfile::Double };
		TowerTop->StrikeTargetTag = TEXT("LB_StrikeTarget_Tower");
	}
	AddStrike(TEXT("State.Event.Finale"), 0.3f, 2, 0.8f);
}

LBStormLogic::FEnvelope ULBStormSettings::MakeEnvelope() const
{
	LBStormLogic::FEnvelope Out;
	Out.SheetAttack = SheetAttack;
	Out.SheetHold = SheetHold;
	Out.SheetDecay = SheetDecay;
	Out.MultiAttack = MultiAttack;
	Out.MultiHold = MultiHold;
	Out.MultiDecay = MultiDecay;
	Out.DoubleFirstPeak = DoubleFirstPeak;
	Out.TripleFirstPeak = TripleFirstPeak;
	Out.TripleLastPeak = TripleLastPeak;
	return Out;
}

LBStormLogic::FScheduleParams ULBStormSettings::MakeScheduleParams() const
{
	LBStormLogic::FScheduleParams Out;
	Out.MinIntervalLow = MinIntervalLow;
	Out.MinIntervalHigh = MinIntervalHigh;
	Out.MaxIntervalLow = MaxIntervalLow;
	Out.MaxIntervalHigh = MaxIntervalHigh;
	Out.FirstFlashScale = FirstFlashScale;
	return Out;
}

LBStormLogic::FWindParams ULBStormSettings::MakeWindParams() const
{
	LBStormLogic::FWindParams Out;
	Out.BaseLow = WindBaseLow;
	Out.BaseHigh = WindBaseHigh;
	Out.GustLow = GustLow;
	Out.GustHigh = GustHigh;
	Out.GustFrequency = GustFrequency;
	Out.PhaseSpeedLow = PhaseSpeedLow;
	Out.PhaseSpeedHigh = PhaseSpeedHigh;
	return Out;
}
