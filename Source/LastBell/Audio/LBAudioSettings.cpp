#include "Audio/LBAudioSettings.h"
#include "GameFramework/Actor.h"
#include "Sound/SoundBase.h"
#include "LBLog.h"

namespace
{
	/** Resolves a tag by name without an error when the project does not know it. An invalid tag is skipped by the caller. */
	FGameplayTag FindAudioTag(const TCHAR* Name)
	{
		const FGameplayTag Tag = FGameplayTag::RequestGameplayTag(FName(Name), /*ErrorIfNotFound*/ false);
		if (!Tag.IsValid())
		{
			UE_LOG(LogLB, Warning, TEXT("ULBAudioSettings::FillPlanDefaults: tag '%s' is not registered; its beat is skipped"), Name);
		}
		return Tag;
	}

	void AddArray(TArray<ULBAudioSettings::FSoundEntry>& Out, const TCHAR* Prefix, const TArray<TSoftObjectPtr<USoundBase>>& Refs)
	{
		for (int32 Index = 0; Index < Refs.Num(); ++Index)
		{
			Out.Add({ FString::Printf(TEXT("%s[%d]"), Prefix, Index), Refs[Index] });
		}
	}

	void AddOne(TArray<ULBAudioSettings::FSoundEntry>& Out, const TCHAR* Name, const TSoftObjectPtr<USoundBase>& Ref)
	{
		Out.Add({ Name, Ref });
	}
}

ULBAudioSettings::ULBAudioSettings()
{
}

void ULBAudioSettings::FillPlanDefaults()
{
	BellBeats.Reset();

	// Plan P16 section 5.3 and P17 section 2.6. The new-game toll is not a beat (bNewGameToll and its fields). Drone: 0 A, 1 B, 2 C.
	struct FBeatRow
	{
		const TCHAR* Tag;
		int32 Stage;
		int32 Strikes;
		float FirstDelay;
		float Spacing;
		int32 Drone;
	};
	static const FBeatRow Rows[] = {
		// P17: the intro's first toll (stage 1 x 3, the first strike at once, Drone A). bNewGameToll is off in DA_Audio since this replaces it.
		{ TEXT("State.Event.Arrival"), 1, 3, 0.f, 4.5f, 0 },
		{ TEXT("State.Ritual.1"), 2, 3, 2.f, 4.5f, 1 },
		{ TEXT("State.Event.CryptEntered"), 1, 0, 0.f, 0.f, 0 },
		{ TEXT("State.Ritual.2"), 3, 3, 2.f, 4.5f, 2 },
		{ TEXT("State.Ritual.3"), 4, 3, 2.f, 4.0f, 1 },
		{ TEXT("State.Event.TowerTop"), 4, 4, 1.f, 3.5f, 2 },
		{ TEXT("State.Event.Finale"), 5, 5, 0.f, 2.0f, -1 },
	};
	for (const FBeatRow& Row : Rows)
	{
		const FGameplayTag Tag = FindAudioTag(Row.Tag);
		if (!Tag.IsValid())
		{
			continue;
		}
		FLBBellBeat& Beat = BellBeats.AddDefaulted_GetRef();
		Beat.Trigger = Tag;
		Beat.Stage = Row.Stage;
		Beat.Strikes = Row.Strikes;
		Beat.FirstDelay = Row.FirstDelay;
		Beat.Spacing = Row.Spacing;
		Beat.Drone = Row.Drone;
	}
}

void ULBAudioSettings::CollectSounds(TArray<FSoundEntry>& Out) const
{
	AddOne(Out, TEXT("Weather.RainOut"), Weather.RainOut);
	AddOne(Out, TEXT("Weather.RainIn"), Weather.RainIn);
	AddOne(Out, TEXT("Weather.Wind"), Weather.Wind);
	AddOne(Out, TEXT("Weather.WindHowl"), Weather.WindHowl);

	AddArray(Out, TEXT("Thunder.Near"), Thunder.Near);
	AddArray(Out, TEXT("Thunder.Mid"), Thunder.Mid);
	AddArray(Out, TEXT("Thunder.Far"), Thunder.Far);
	AddArray(Out, TEXT("Thunder.StrikeCrack"), Thunder.StrikeCrack);

	AddArray(Out, TEXT("Bell.Stage"), Bell.Stage);

	AddArray(Out, TEXT("Music.Drones"), Music.Drones);
	AddOne(Out, TEXT("Music.Tension"), Music.Tension);
	AddOne(Out, TEXT("Music.Chase"), Music.Chase);
	AddOne(Out, TEXT("Music.StingSpotted"), Music.StingSpotted);
	AddOne(Out, TEXT("Music.StingCaught"), Music.StingCaught);
	AddOne(Out, TEXT("Music.StingApparition"), Music.StingApparition);

	AddArray(Out, TEXT("Player.BreathCalm"), Player.BreathCalm);
	AddArray(Out, TEXT("Player.BreathHeavy"), Player.BreathHeavy);
	AddArray(Out, TEXT("Player.BreathPanic"), Player.BreathPanic);
	AddArray(Out, TEXT("Player.BreathGasp"), Player.BreathGasp);
	AddArray(Out, TEXT("Player.CandleLight"), Player.CandleLight);
	AddArray(Out, TEXT("Player.CandleOut"), Player.CandleOut);
	AddOne(Out, TEXT("Player.CandleRelight"), Player.CandleRelight);

	AddOne(Out, TEXT("Warden.BreathSlow"), Warden.BreathSlow);
	AddOne(Out, TEXT("Warden.BreathFast"), Warden.BreathFast);
	AddOne(Out, TEXT("Warden.BreathHeavy"), Warden.BreathHeavy);
	AddArray(Out, TEXT("Warden.Steps"), Warden.Steps);
	AddArray(Out, TEXT("Warden.Chains"), Warden.Chains);
	AddOne(Out, TEXT("Warden.RobeLoop"), Warden.RobeLoop);
	AddArray(Out, TEXT("Warden.Spotted"), Warden.Spotted);
	AddArray(Out, TEXT("Warden.Roar"), Warden.Roar);
	AddArray(Out, TEXT("Warden.Windup"), Warden.Windup);
	AddArray(Out, TEXT("Warden.Exhale"), Warden.Exhale);
	AddArray(Out, TEXT("Warden.Caught"), Warden.Caught);
	AddArray(Out, TEXT("Warden.ApparitionWhisper"), Warden.ApparitionWhisper);

	for (int32 Index = 0; Index < InteractionCues.Num(); ++Index)
	{
		const FLBInteractionCue& Cue = InteractionCues[Index];
		const FString Prefix = FString::Printf(TEXT("InteractionCues[%d](%s)"), Index, *Cue.ActorClass.GetAssetName());
		AddArray(Out, *(Prefix + TEXT(".Interact")), Cue.Interact);
		AddArray(Out, *(Prefix + TEXT(".Denied")), Cue.Denied);
		AddArray(Out, *(Prefix + TEXT(".DialNotch")), Cue.DialNotch);
	}

	AddOne(Out, TEXT("SmallBellStrike"), SmallBellStrike);
	AddOne(Out, TEXT("SmallBellFail"), SmallBellFail);
	AddOne(Out, TEXT("SmallBellSolved"), SmallBellSolved);
}

int32 ULBAudioSettings::FindCueRow(const UClass* ActorClass, bool& bOutSilent) const
{
	bOutSilent = false;
	if (!ActorClass)
	{
		return INDEX_NONE;
	}
	auto Depth = [](const UClass* Class)
	{
		int32 Count = 0;
		for (const UClass* Super = Class ? Class->GetSuperClass() : nullptr; Super; Super = Super->GetSuperClass())
		{
			++Count;
		}
		return Count;
	};
	int32 BestRow = INDEX_NONE;
	int32 BestDepth = -1;
	for (int32 Index = 0; Index < InteractionCues.Num(); ++Index)
	{
		const FLBInteractionCue& Cue = InteractionCues[Index];
		const UClass* CueClass = Cue.ActorClass.IsNull() ? nullptr : Cue.ActorClass.LoadSynchronous();
		if (!CueClass)
		{
			continue;
		}
		const bool bMatch = Cue.bIncludeSubclasses ? ActorClass->IsChildOf(CueClass) : ActorClass == CueClass;
		const int32 CueDepth = Depth(CueClass);
		if (bMatch && CueDepth > BestDepth)
		{
			BestDepth = CueDepth;
			BestRow = Index;
		}
	}
	int32 SilentDepth = -1;
	for (const TSoftClassPtr<AActor>& Silent : SilentClasses)
	{
		const UClass* SilentClass = Silent.IsNull() ? nullptr : Silent.LoadSynchronous();
		if (SilentClass && ActorClass->IsChildOf(SilentClass))
		{
			SilentDepth = FMath::Max(SilentDepth, Depth(SilentClass));
		}
	}
	if (BestRow != INDEX_NONE && BestDepth >= SilentDepth)
	{
		return BestRow;
	}
	bOutSilent = SilentDepth >= 0;
	return INDEX_NONE;
}

LBAudioLogic::FThunderParams ULBAudioSettings::MakeThunderParams() const
{
	LBAudioLogic::FThunderParams Out;
	Out.Delay = ThunderDelay;
	Out.Jitter = ThunderJitter;
	Out.NearAt = ThunderNearAt;
	Out.FarBelow = ThunderFarBelow;
	return Out;
}

LBAudioLogic::FMusicParams ULBAudioSettings::MakeMusicParams() const
{
	LBAudioLogic::FMusicParams Out;
	Out.TensionNearDistance = TensionNearDistance;
	Out.MinStage = MusicMinStage;
	Out.Patrol = TensionLevels.Patrol;
	Out.Suspicious = TensionLevels.Suspicious;
	Out.Investigate = TensionLevels.Investigate;
	Out.Search = TensionLevels.Search;
	Out.Chase = TensionLevels.Chase;
	Out.Return = TensionLevels.Return;
	Out.ChaseLevel = ChaseLevel;
	return Out;
}

LBAudioLogic::FStressParams ULBAudioSettings::MakeStressParams() const
{
	LBAudioLogic::FStressParams Out;
	Out.Chase = StressChase;
	Out.NearSearch = StressNearSearch;
	Out.NearDistance = StressNearDistance;
	Out.SprintBonus = StressSprintBonus;
	Out.SprintSeconds = StressSprintSeconds;
	Out.Decay = StressDecay;
	Out.Rise = StressRise;
	Out.DarknessLit = DarknessLit;
	Out.DarknessUnlit = DarknessUnlit;
	Out.CandleOut = CandleOutStress;
	return Out;
}

LBAudioLogic::FBreathThresholds ULBAudioSettings::MakeBreathThresholds() const
{
	LBAudioLogic::FBreathThresholds Out;
	Out.Calm = BreathCalmAt;
	Out.Heavy = BreathHeavyAt;
	Out.Panic = BreathPanicAt;
	return Out;
}

LBAudioLogic::FTollParams ULBAudioSettings::MakeTollParams() const
{
	LBAudioLogic::FTollParams Out;
	Out.bEnabled = bAmbientTolls;
	Out.Interval = AmbientTollInterval;
	Out.Strikes = AmbientTollStrikes;
	Out.GapAfterBeat = AmbientTollGapAfterBeat;
	Out.MaxTension = AmbientTollMaxTension;
	return Out;
}
