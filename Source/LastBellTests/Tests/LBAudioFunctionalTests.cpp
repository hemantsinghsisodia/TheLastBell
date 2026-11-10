#include "Tests/LBRouteBot.h"
#include "Tests/LBAudioTestSink.h"
#include "Storm/LBStormSubsystem.h"

void ULBAudioTestSink::Bind(ULBStormSubsystem* Storm, UWorld* InWorld)
{
	World = InWorld;
	if (Storm)
	{
		Storm->OnLightningStrike.AddDynamic(this, &ULBAudioTestSink::HandleStrike);
	}
}

void ULBAudioTestSink::HandleStrike(const FLBLightningStrikeInfo& Info)
{
	FStrikeRecord Record;
	Record.Time = World.IsValid() ? World->GetTimeSeconds() : 0.0;
	Record.Info = Info;
	Strikes.Add(Record);
}

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Editor.h"
#include "EngineUtils.h"
#include "Tests/AutomationEditorCommon.h"
#include "AI/LBWarden.h"
#include "AI/LBWardenApparition.h"
#include "AI/LBWardenBrainComponent.h"
#include "Audio/LBAmbientEmitter.h"
#include "Audio/LBAudioSettings.h"
#include "Audio/LBAudioSubsystem.h"
#include "Audio/LBAudioZone.h"
#include "Audio/LBWardenAudioComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Character/LBCandleComponent.h"
#include "Character/LBCharacter.h"
#include "Character/LBFootstepComponent.h"
#include "Character/LBInspectionComponent.h"
#include "Components/LBInspectableComponent.h"
#include "Components/LBInteractableComponent.h"
#include "Engine/DataTable.h"
#include "Engine/DirectionalLight.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/TargetPoint.h"
#include "Engine/TriggerBox.h"
#include "Components/LightComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/PackageName.h"
#include "Puzzles/LBSequencePuzzleComponent.h"
#include "Sound/AudioVolume.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundClass.h"
#include "Sound/SoundMix.h"
#include "Storm/LBStormSettings.h"
#include "Systems/LBGameSettings.h"
#include "Systems/LBUserSettings.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "UObject/StrongObjectPtr.h"
#include "LBLog.h"

// P16-1 functional tests of the audio director (LastBell.Functional.Audio.*). Like the P14 and P15 tests, the PIE tests load
// /Game/LastBell/Maps/L_Test_Warden (one session each), spawn their own tagged moon and hand over a transient ULBStormSettings and a transient
// ULBAudioSettings through OverrideSettings + RefreshLinkedLights + Rearm. So none of them needs DA_StormSettings or DA_Audio: every sound slot
// is filled with the engine's /Engine/EngineSounds/1kSineTonePing. The suite runs with -nosound, so there is no audio device and nothing is
// heard: the tests check the audio subsystem's request log (what it asked to be played, where, how loud, when), which is recorded whether or
// not a device exists. lb.Warden.Enabled is 0 for the sessions (the Warden stays dormant unless a test shows it) and lb.Audio.Enabled is put
// back afterwards. The last test checks the real L_Monastery setup and is EXPECTED TO FAIL until P16-2 (DA_Audio and the sounds) and P16-3
// (the level work) are done.

#define LB_AUDIOFUNC_FLAGS (EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

namespace LBAudioTest
{
	const TCHAR* GAudioTestMap = TEXT("/Game/LastBell/Maps/L_Test_Warden");
	const TCHAR* GAudioMonasteryMap = TEXT("/Game/LastBell/Maps/L_Monastery");
	const TCHAR* GPingPath = TEXT("/Engine/EngineSounds/1kSineTonePing.1kSineTonePing");
	const TCHAR* GFootstepTablePath = TEXT("/Game/LastBell/Data/DT_Footsteps.DT_Footsteps");

	void AudioNote(const FString& Text) { UE_LOG(LogLB, Display, TEXT("[AudioTest] %s"), *Text); }

	struct FAudioCtx
	{
		UWorld* W = nullptr;
		double Elapsed = 0.0; // game seconds since the step began
		double Now = 0.0;     // world time
		int32 Frames = 0;
	};

	struct FAudioState
	{
		TStrongObjectPtr<ULBStormSettings> StormSettings;
		TStrongObjectPtr<ULBAudioSettings> AudioSettings;
		TStrongObjectPtr<ULBAudioTestSink> Sink;
		TWeakObjectPtr<ADirectionalLight> Moon;
		TArray<TWeakObjectPtr<AActor>> Actors;
		FVector Anchor = FVector::ZeroVector;
		double T0 = 0.0;
		double T1 = 0.0;
		int32 Phase = 0;
		int32 Counter = 0;

		ULBStormSubsystem* Storm(UWorld* W) const { return W ? W->GetSubsystem<ULBStormSubsystem>() : nullptr; }
		ULBAudioSubsystem* Audio(UWorld* W) const { return W ? W->GetSubsystem<ULBAudioSubsystem>() : nullptr; }
	};

	/** Sets lb.Audio.Enabled to 1 for the lifetime of the object and puts the previous value back afterwards. */
	class FAudioEnabledGuard
	{
	public:
		FAudioEnabledGuard()
		{
			if (IConsoleVariable* Var = Get())
			{
				Previous = Var->GetInt();
				Var->Set(1, ECVF_SetByCode);
			}
		}
		~FAudioEnabledGuard()
		{
			if (IConsoleVariable* Var = Get())
			{
				Var->Set(Previous, ECVF_SetByCode);
			}
		}
		FAudioEnabledGuard(const FAudioEnabledGuard&) = delete;
		FAudioEnabledGuard& operator=(const FAudioEnabledGuard&) = delete;

		static IConsoleVariable* Get() { return IConsoleManager::Get().FindConsoleVariable(TEXT("lb.Audio.Enabled")); }
		static void Set(int32 Value)
		{
			if (IConsoleVariable* Var = Get())
			{
				Var->Set(Value, ECVF_SetByCode);
			}
		}

	private:
		int32 Previous = 1;
	};

	/** Puts the user volumes back to what they were (the tests change them without saving). */
	class FUserVolumeGuard
	{
	public:
		FUserVolumeGuard()
		{
			const ULBUserSettings* User = ULBUserSettings::Get();
			for (int32 Index = 0; Index < 6; ++Index)
			{
				Previous[Index] = User->GetVolume(static_cast<ELBAudioVolumeGroup>(Index));
			}
		}
		~FUserVolumeGuard()
		{
			for (int32 Index = 0; Index < 6; ++Index)
			{
				ULBUserSettings::GetUserSettings()->SetVolumeTransient(static_cast<ELBAudioVolumeGroup>(Index), Previous[Index]);
			}
		}
		FUserVolumeGuard(const FUserVolumeGuard&) = delete;
		FUserVolumeGuard& operator=(const FUserVolumeGuard&) = delete;

	private:
		float Previous[6] = { 1.f, 1.f, 1.f, 1.f, 1.f, 1.f };
	};

	class FAudioRunner : public IAutomationLatentCommand
	{
	public:
		using FStepFn = TFunction<bool(FAudioCtx&)>;

		explicit FAudioRunner(FAutomationTestBase* InTest)
			: S(MakeShared<FAudioState>()), Test(InTest), WardenOff(false)
		{
		}

		void Add(const TCHAR* Name, FStepFn Fn, float WallTimeout = 40.f)
		{
			Steps.Add({ Name, WallTimeout, MoveTemp(Fn) });
		}

		virtual bool Update() override
		{
			if (bTearingDown)
			{
				return !LBPie::World() || (FPlatformTime::Seconds() - TeardownStart) > 30.0;
			}
			if (bAbort || StepIndex >= Steps.Num())
			{
				BeginTeardown();
				return false;
			}

			UWorld* W = LBPie::World();
			FStep& Step = Steps[StepIndex];
			if (!bEntered)
			{
				if (StepIndex > 0 && (!W || !LBPie::Pawn()))
				{
					Test->AddError(FString::Printf(TEXT("Step '%s': PIE world or pawn is gone"), *Step.Name));
					bAbort = true;
					return false;
				}
				bEntered = true;
				Frames = 0;
				WallStart = FPlatformTime::Seconds();
				WorldStart = W ? W->GetTimeSeconds() : 0.0;
				ErrorsAtStart = ErrCount();
				AudioNote(FString::Printf(TEXT("STEP %d begin: %s"), StepIndex + 1, *Step.Name));
			}

			FAudioCtx Ctx;
			Ctx.W = W;
			Ctx.Now = W ? W->GetTimeSeconds() : 0.0;
			Ctx.Elapsed = Ctx.Now - WorldStart;
			Ctx.Frames = Frames;
			++Frames;

			const bool bDone = Step.Fn(Ctx);
			const bool bTimedOut = !bDone && (FPlatformTime::Seconds() - WallStart) > Step.Timeout;
			if (bTimedOut)
			{
				Test->AddError(FString::Printf(TEXT("Step '%s' timed out after %.0fs"), *Step.Name, Step.Timeout));
			}
			if (bDone || bTimedOut)
			{
				AudioNote(FString::Printf(TEXT("STEP %d %s: %s"), StepIndex + 1, ErrCount() == ErrorsAtStart ? TEXT("PASS") : TEXT("FAIL"), *Step.Name));
				if (bTimedOut || ErrCount() != ErrorsAtStart)
				{
					// Later steps depend on this one: stop at the first failure.
					bAbort = true;
				}
				++StepIndex;
				bEntered = false;
			}
			return false;
		}

		TSharedRef<FAudioState> S;

	private:
		struct FStep
		{
			FString Name;
			float Timeout;
			FStepFn Fn;
		};

		int32 ErrCount() const
		{
			FAutomationTestExecutionInfo Info;
			Test->GetExecutionInfo(Info);
			return Info.GetErrorTotal();
		}

		void BeginTeardown()
		{
			bTearingDown = true;
			TeardownStart = FPlatformTime::Seconds();
			if (GEditor && LBPie::World())
			{
				GEditor->RequestEndPlayMap();
			}
		}

		FAutomationTestBase* Test;
		LBPie::FWardenSwitch WardenOff;
		// P17 (R-82): the New Game intro would lock input and add State.Event.Arrival in L_Monastery; these runs do not test it.
		LBPie::FCineSwitch CineOff{ false };
		FAudioEnabledGuard AudioEnabled;
		FUserVolumeGuard UserVolumes;
		TArray<FStep> Steps;
		int32 StepIndex = 0;
		int32 Frames = 0;
		bool bEntered = false;
		bool bAbort = false;
		bool bTearingDown = false;
		double WallStart = 0.0;
		double WorldStart = 0.0;
		double TeardownStart = 0.0;
		int32 ErrorsAtStart = 0;
	};

	TSharedRef<FAudioRunner> AudioStartSession(FAutomationTestBase* Test, const TCHAR* Map = nullptr)
	{
		TSharedRef<FAudioRunner> Runner = MakeShared<FAudioRunner>(Test);
		FAutomationEditorCommonUtils::LoadMap(Map ? Map : GAudioTestMap);
		FRequestPlaySessionParams PlayParams;
		PlayParams.WorldType = EPlaySessionWorldType::PlayInEditor;
		GEditor->RequestPlaySession(PlayParams);
		return Runner;
	}

	void AudioEnqueue(const TSharedRef<FAudioRunner>& Runner)
	{
		FAutomationTestFramework::Get().EnqueueLatentCommand(Runner);
	}

	// ---- Scene helpers ---------------------------------------------------------------------------------------------------------

	FGameplayTag AudioTag(const TCHAR* Name) { return LBPie::Tag(Name); }

	TSoftObjectPtr<USoundBase> Ping() { return TSoftObjectPtr<USoundBase>(FSoftObjectPath(GPingPath)); }

	void FillSet(TArray<TSoftObjectPtr<USoundBase>>& Set, int32 Count)
	{
		Set.Reset();
		for (int32 Index = 0; Index < Count; ++Index)
		{
			Set.Add(Ping());
		}
	}

	/** A transient audio-settings object with every sound slot filled with the ping, the plan's beats, and the tolls off. */
	void MakeSettings(FAudioState& S)
	{
		S.StormSettings.Reset(NewObject<ULBStormSettings>(GetTransientPackage()));
		S.StormSettings->FillPlanTagDefaults();
		S.StormSettings->RandomSeed = 1601;
		S.StormSettings->bAmbientFlashes = false;

		S.AudioSettings.Reset(NewObject<ULBAudioSettings>(GetTransientPackage()));
		ULBAudioSettings& A = *S.AudioSettings;
		A.FillPlanDefaults();
		A.RandomSeed = 1601;
		A.bNewGameToll = false;
		A.bAmbientTolls = false;
		A.BellLocation = FVector(5000.0, 0.0, 3000.0);
		// The beats keep their plan stages and strikes but come fast, so a test does not wait 11 s for a toll.
		for (FLBBellBeat& Beat : A.BellBeats)
		{
			Beat.FirstDelay = FMath::Min(Beat.FirstDelay, 0.3f);
			Beat.Spacing = FMath::Min(Beat.Spacing, 0.4f);
		}

		A.Weather.RainOut = Ping();
		A.Weather.RainIn = Ping();
		A.Weather.Wind = Ping();
		A.Weather.WindHowl = Ping();
		FillSet(A.Thunder.Near, 4);
		FillSet(A.Thunder.Mid, 4);
		FillSet(A.Thunder.Far, 4);
		FillSet(A.Thunder.StrikeCrack, 3);
		FillSet(A.Bell.Stage, 5);
		FillSet(A.Music.Drones, 3);
		A.Music.Tension = Ping();
		A.Music.Chase = Ping();
		A.Music.StingSpotted = Ping();
		A.Music.StingCaught = Ping();
		A.Music.StingApparition = Ping();
		FillSet(A.Player.BreathCalm, 4);
		FillSet(A.Player.BreathHeavy, 4);
		FillSet(A.Player.BreathPanic, 4);
		FillSet(A.Player.BreathGasp, 3);
		FillSet(A.Player.CandleLight, 3);
		FillSet(A.Player.CandleOut, 3);
		A.Player.CandleRelight = Ping();
		A.Warden.BreathSlow = Ping();
		A.Warden.BreathFast = Ping();
		A.Warden.BreathHeavy = Ping();
		FillSet(A.Warden.Steps, 5);
		FillSet(A.Warden.Chains, 4);
		A.Warden.RobeLoop = Ping();
		FillSet(A.Warden.Spotted, 3);
		FillSet(A.Warden.Roar, 3);
		FillSet(A.Warden.Windup, 3);
		FillSet(A.Warden.Exhale, 3);
		FillSet(A.Warden.Caught, 2);
		FillSet(A.Warden.ApparitionWhisper, 3);
		A.SmallBellStrike = Ping();
		A.SmallBellFail = Ping();
		A.SmallBellSolved = Ping();

		S.Sink.Reset(NewObject<ULBAudioTestSink>());
	}

	/** Spawns the tagged moon, hands the settings over (Tweak edits the audio settings first), activates the storm and arms the audio. Null (with an error) on failure. */
	ULBAudioSubsystem* ActivateAudio(FAudioCtx& C, FAudioState& S, FAutomationTestBase* Test, TFunction<void(ULBAudioSettings&)> Tweak = nullptr)
	{
		MakeSettings(S);
		if (Tweak)
		{
			Tweak(*S.AudioSettings);
		}

		ADirectionalLight* Moon = C.W->SpawnActor<ADirectionalLight>(FVector(0.0, 0.0, 5000.0), FRotator(-40.f, 35.f, 0.f));
		S.Moon = Moon;
		if (Moon)
		{
			if (ULightComponent* Light = Moon->GetLightComponent())
			{
				Light->SetMobility(EComponentMobility::Movable);
				Light->SetIntensity(0.9f);
			}
			Moon->Tags.Add(FName(TEXT("LB_StormMoon")));
		}
		ULBStormSubsystem* Storm = S.Storm(C.W);
		ULBAudioSubsystem* Audio = S.Audio(C.W);
		if (!Test->TestNotNull(TEXT("Storm subsystem exists in a PIE world"), Storm) || !Test->TestNotNull(TEXT("Audio subsystem exists in a PIE world"), Audio)
			|| !Test->TestNotNull(TEXT("Tagged moon spawned"), Moon))
		{
			return nullptr;
		}
		Storm->OverrideSettings(S.StormSettings.Get());
		Storm->RefreshLinkedLights();
		if (!Test->TestTrue(TEXT("Storm is active after RefreshLinkedLights with a tagged moon"), Storm->IsActive()))
		{
			return nullptr;
		}
		S.Sink->Bind(Storm, C.W);
		Audio->OverrideSettings(S.AudioSettings.Get());
		Audio->Rearm();
		return Audio;
	}

	/** Waits for the audio director to activate (a few frames). Returns true when it has; adds an error after 3 s. */
	bool AudioIsUp(FAudioCtx& C, FAudioState& S, FAutomationTestBase* Test)
	{
		const ULBAudioSubsystem* Audio = S.Audio(C.W);
		if (Audio && Audio->IsActive())
		{
			return true;
		}
		if (C.Elapsed > 3.0)
		{
			Test->AddError(TEXT("The audio director did not become active within 3 s"));
			return true;
		}
		return false;
	}

	/** The requests of one cue so far (copies). */
	TArray<FLBAudioRequest> Requests(const ULBAudioSubsystem* Audio, FName Cue)
	{
		TArray<FLBAudioRequest> Out;
		if (Audio)
		{
			for (const FLBAudioRequest& Request : Audio->GetRequests())
			{
				if (Request.Cue == Cue)
				{
					Out.Add(Request);
				}
			}
		}
		return Out;
	}

	bool FlashEnded(const ULBStormSubsystem* Storm)
	{
		return Storm && !Storm->IsFlashBusy() && Storm->GetLightningFlash() < 0.01f;
	}

	/** A static mesh actor (or another class) with an interactable component at a place; both are in the world and bound by RefreshBindings. */
	template <typename TActor>
	TActor* SpawnInteractable(UWorld* W, const FVector& Location, ULBInteractableComponent*& OutInteractable, bool bEnabled = true)
	{
		TActor* Actor = W->SpawnActor<TActor>(Location, FRotator::ZeroRotator);
		OutInteractable = nullptr;
		if (!Actor)
		{
			return nullptr;
		}
		if (AStaticMeshActor* Mesh = Cast<AStaticMeshActor>(static_cast<AActor*>(Actor)))
		{
			Mesh->SetMobility(EComponentMobility::Movable);
			Mesh->SetActorLocation(Location);
		}
		else if (Actor->GetRootComponent())
		{
			Actor->GetRootComponent()->SetMobility(EComponentMobility::Movable);
		}
		ULBInteractableComponent* Interactable = NewObject<ULBInteractableComponent>(Actor);
		Interactable->bEnabled = bEnabled;
		Actor->AddInstanceComponent(Interactable);
		Interactable->RegisterComponent();
		OutInteractable = Interactable;
		return Actor;
	}
}

using namespace LBAudioTest;

// =====================================================================================================================
// 1. The director runs while the storm does, and not otherwise
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioActivatesTest, "LastBell.Functional.Audio.ActivatesWithStorm", LB_AUDIOFUNC_FLAGS)
bool FLBAudioActivatesTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, no storm: the director is inactive; then the storm is switched on"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		const ULBAudioSubsystem* Audio = S->Audio(C.W);
		if (!Test->TestNotNull(TEXT("Audio subsystem exists in a PIE world"), Audio))
		{
			return true;
		}
		Test->TestFalse(TEXT("No tagged moon: the director is inactive"), Audio->IsActive());
		Test->TestEqual(TEXT("No tagged moon: nothing is bound"), Audio->GetBoundActorCount(), 0);
		ActivateAudio(C, *S, Test);
		return true;
	});

	R->Add(TEXT("With the storm active the director activates and the room has its loops at rest"), [S, Test](FAudioCtx& C)
	{
		if (!AudioIsUp(C, *S, Test))
		{
			return false;
		}
		const ULBAudioSubsystem* Audio = S->Audio(C.W);
		Test->TestTrue(TEXT("The director is active"), Audio && Audio->IsActive());
		if (Audio)
		{
			Test->TestNotNull(TEXT("The settings are the override"), Audio->GetSettings());
			Test->TestNearlyEqual(TEXT("No music at rest: the chase layer is 0"), Audio->GetLayerLevel(ELBAudioLayer::Chase), 0.f, 1.0e-4f);
			Test->TestNearlyEqual(TEXT("No music at rest: the drone is 0"), Audio->GetLayerLevel(ELBAudioLayer::Drone), 0.f, 1.0e-4f);
		}
		// The storm goes away: the moon loses its tag.
		if (ADirectionalLight* Moon = S->Moon.Get())
		{
			Moon->Tags.Empty();
		}
		if (ULBStormSubsystem* Storm = S->Storm(C.W))
		{
			Storm->RefreshLinkedLights();
			Test->TestFalse(TEXT("No tagged moon: the storm is inactive again"), Storm->IsActive());
		}
		return true;
	});

	R->Add(TEXT("With the storm gone the director switches off"), [S, Test](FAudioCtx& C)
	{
		const ULBAudioSubsystem* Audio = S->Audio(C.W);
		if (Audio && Audio->IsActive())
		{
			if (C.Elapsed > 3.0)
			{
				Test->AddError(TEXT("The director stayed active 3 s after the storm went inactive"));
				return true;
			}
			return false;
		}
		Test->TestEqual(TEXT("Nothing is bound any more"), Audio ? Audio->GetBoundActorCount() : -1, 0);
		return true;
	});

	AudioEnqueue(R);
	return true;
}

// =====================================================================================================================
// 2. lb.Audio.Enabled
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioDisabledByCVarTest, "LastBell.Functional.Audio.DisabledByCVar", LB_AUDIOFUNC_FLAGS)
bool FLBAudioDisabledByCVarTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, storm and director active"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ActivateAudio(C, *S, Test);
		return true;
	});

	R->Add(TEXT("lb.Audio.Enabled 0 switches the director off"), [S, Test](FAudioCtx& C)
	{
		if (S->Phase == 0)
		{
			if (!AudioIsUp(C, *S, Test))
			{
				return false;
			}
			Test->TestTrue(TEXT("The director is active with lb.Audio.Enabled 1"), S->Audio(C.W)->IsActive());
			FAudioEnabledGuard::Set(0);
			S->Phase = 1;
			return false;
		}
		const ULBAudioSubsystem* Audio = S->Audio(C.W);
		if (Audio && Audio->IsActive())
		{
			if (C.Elapsed > 3.0)
			{
				Test->AddError(TEXT("The director stayed active 3 s after lb.Audio.Enabled 0"));
				return true;
			}
			return false;
		}
		Test->TestEqual(TEXT("Switched off: nothing is bound"), Audio ? Audio->GetBoundActorCount() : -1, 0);
		Test->TestEqual(TEXT("Switched off: nothing is scheduled"), Audio ? Audio->GetScheduledCount() : -1, 0);
		return true;
	});

	R->Add(TEXT("lb.Audio.Enabled 1 brings it back"), [S, Test](FAudioCtx& C)
	{
		if (S->Phase == 1)
		{
			FAudioEnabledGuard::Set(1);
			S->Phase = 2;
			return false;
		}
		if (!AudioIsUp(C, *S, Test))
		{
			return false;
		}
		Test->TestTrue(TEXT("The director is active again"), S->Audio(C.W)->IsActive());
		return true;
	});

	AudioEnqueue(R);
	return true;
}

// =====================================================================================================================
// 3. Thunder follows a flash after the planned delay
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioThunderAfterFlashTest, "LastBell.Functional.Audio.ThunderAfterFlash", LB_AUDIOFUNC_FLAGS)
bool FLBAudioThunderAfterFlashTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, storm and director active"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ActivateAudio(C, *S, Test);
		return true;
	});

	R->Add(TEXT("A brightness-1 flash gives one near thunder inside the planned window, from the flash side"), [S, Test](FAudioCtx& C)
	{
		ULBStormSubsystem* Storm = S->Storm(C.W);
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		if (!Storm || !Audio)
		{
			Test->AddError(TEXT("Storm or audio subsystem is gone"));
			return true;
		}
		if (C.Elapsed > 12.0)
		{
			Test->AddError(FString::Printf(TEXT("Timed out in phase %d"), S->Phase));
			return true;
		}
		switch (S->Phase)
		{
		case 0:
			if (!Audio->IsActive())
			{
				return false;
			}
			Audio->ClearRequests();
			Storm->RequestFlash(1.f, 0.f, ELBFlashReason::Debug, ELBFlashProfile::Sheet);
			S->Phase = 1;
			return false;
		case 1:
		{
			if (S->Sink->Strikes.IsEmpty())
			{
				return false;
			}
			S->T0 = S->Sink->Strikes[0].Time;
			S->Phase = 2;
			return false;
		}
		case 2:
		{
			const TArray<FLBAudioRequest> Thunder = Requests(Audio, LBAudioCue::Thunder);
			if (Thunder.IsEmpty())
			{
				return false;
			}
			const FLBAudioRequest& Request = Thunder[0];
			const double Delay = Request.Time - S->T0;
			const float B = S->Sink->Strikes[0].Info.Brightness;
			AudioNote(FString::Printf(TEXT("thunder %.3f s after the flash (brightness %.2f), set %d, volume %.2f, at %s"), Delay, B, Request.Aux, Request.Volume, *Request.Location.ToString()));
			// The base delay lerps 4.5 s (brightness 0) to 0.6 s (brightness 1), 0.4 s of jitter either way; a frame or a hitch of slack on top.
			const double Base = FMath::Lerp(4.5, 0.6, static_cast<double>(B));
			Test->TestTrue(FString::Printf(TEXT("The thunder comes within the planned window (%.3f vs %.2f +- 0.4)"), Delay, Base), Delay >= Base - 0.4 - 0.02 && Delay <= Base + 0.4 + 0.35);
			Test->TestTrue(FString::Printf(TEXT("A bright flash (%.2f) gives a short delay (under 1.5 s)"), B), B < 0.9f || Delay < 1.5);
			Test->TestEqual(TEXT("The brightness picks the set"), Request.Aux, static_cast<int32>(LBAudioLogic::ThunderSetFor(B, S->AudioSettings->MakeThunderParams())));
			Test->TestNearlyEqual(TEXT("Volume 0.55 + 0.45 * brightness"), Request.Volume, 0.55f + 0.45f * B, 1.0e-3f);
			Test->TestTrue(TEXT("A variant of the set was picked"), Request.Variant >= 0 && Request.Variant < 4);
			Test->TestTrue(TEXT("The ping loaded"), Request.bSoundResolved);
			Test->TestTrue(TEXT("The thunder is positional"), Request.bPositional);

			// It sits ThunderDistance from the listener along the flash's horizontal direction.
			FVector Listener;
			if (Audio->GetListenerLocation(Listener))
			{
				const double Distance = FVector::Dist2D(Request.Location, Listener);
				Test->TestTrue(FString::Printf(TEXT("The thunder is ThunderDistance (6000 cm) away horizontally (%.1f)"), Distance), FMath::Abs(Distance - 6000.0) <= 100.0);
				const FVector Flat(S->Sink->Strikes[0].Info.Direction.X, S->Sink->Strikes[0].Info.Direction.Y, 0.0);
				const FVector ToThunder = FVector(Request.Location.X - Listener.X, Request.Location.Y - Listener.Y, 0.0).GetSafeNormal();
				Test->TestTrue(FString::Printf(TEXT("It is on the flash side (dot %.3f)"), FVector::DotProduct(ToThunder, Flat.GetSafeNormal())), FVector::DotProduct(ToThunder, Flat.GetSafeNormal()) > 0.98);
			}
			S->T1 = C.Now;
			S->Phase = 3;
			return false;
		}
		default:
			// A second of quiet: still exactly one thunder, and no strike crack (the flash had no target).
			if (C.Now - S->T1 < 1.5)
			{
				return false;
			}
			Test->TestEqual(TEXT("Exactly one thunder for the flash"), Requests(Audio, LBAudioCue::Thunder).Num(), 1);
			Test->TestEqual(TEXT("No strike crack for a flash without a target"), Requests(Audio, LBAudioCue::ThunderStrike).Num(), 0);
			return true;
		}
	}, 60.f);

	AudioEnqueue(R);
	return true;
}

// =====================================================================================================================
// 4. A tower strike cracks at its target, and its thunder is near
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioTargetStrikeCrackTest, "LastBell.Functional.Audio.TargetStrikeCrack", LB_AUDIOFUNC_FLAGS)
bool FLBAudioTargetStrikeCrackTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, storm and director active, a target"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		if (!ActivateAudio(C, *S, Test))
		{
			return true;
		}
		const ALBCharacter* Pawn = LBPie::Pawn();
		S->Anchor = (Pawn ? Pawn->GetActorLocation() : FVector::ZeroVector) + FVector(2500.0, 800.0, 2000.0);
		AStaticMeshActor* Target = C.W->SpawnActor<AStaticMeshActor>(S->Anchor, FRotator::ZeroRotator);
		if (!Test->TestNotNull(TEXT("The strike target spawned"), Target))
		{
			return true;
		}
		Target->SetMobility(EComponentMobility::Movable);
		Target->SetActorLocation(S->Anchor);
		S->Actors.Add(Target);
		return true;
	});

	R->Add(TEXT("A brightness-0.5 strike at the target: the crack at once at the target, the thunder near"), [S, Test](FAudioCtx& C)
	{
		ULBStormSubsystem* Storm = S->Storm(C.W);
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		if (!Storm || !Audio || S->Actors.IsEmpty() || !S->Actors[0].IsValid())
		{
			Test->AddError(TEXT("Storm, audio subsystem or target is gone"));
			return true;
		}
		if (C.Elapsed > 14.0)
		{
			Test->AddError(FString::Printf(TEXT("Timed out in phase %d"), S->Phase));
			return true;
		}
		switch (S->Phase)
		{
		case 0:
			if (!Audio->IsActive())
			{
				return false;
			}
			Audio->ClearRequests();
			Storm->RequestFlashAtTarget(0.5f, 0.f, ELBFlashReason::Scripted, ELBFlashProfile::Double, S->Actors[0].Get());
			S->Phase = 1;
			return false;
		case 1:
			if (S->Sink->Strikes.IsEmpty())
			{
				return false;
			}
			Test->TestTrue(TEXT("The strike carries its target"), S->Sink->Strikes[0].Info.bHasTarget);
			S->T0 = S->Sink->Strikes[0].Time;
			S->Phase = 2;
			return false;
		case 2:
		{
			// Brightness 0.5 without a target would be mid thunder; with a target it is near.
			const TArray<FLBAudioRequest> Thunder = Requests(Audio, LBAudioCue::Thunder);
			if (Thunder.IsEmpty())
			{
				return false;
			}
			const TArray<FLBAudioRequest> Crack = Requests(Audio, LBAudioCue::ThunderStrike);
			if (!Test->TestEqual(TEXT("One strike crack"), Crack.Num(), 1))
			{
				return true;
			}
			const double CrackDelay = Crack[0].Time - S->T0;
			Test->TestTrue(FString::Printf(TEXT("The crack follows the flash by StrikeCrackDelay (0.12 s; %.3f)"), CrackDelay), CrackDelay >= 0.12 - 0.02 && CrackDelay <= 0.12 + 0.35);
			Test->TestTrue(FString::Printf(TEXT("The crack is at the target (%s)"), *Crack[0].Location.ToString()), Crack[0].Location.Equals(S->Anchor, 1.0));
			Test->TestTrue(TEXT("The crack is positional and loaded"), Crack[0].bPositional && Crack[0].bSoundResolved);
			Test->TestTrue(TEXT("A strike-crack variant was picked"), Crack[0].Variant >= 0 && Crack[0].Variant < 3);

			const double ThunderDelay = Thunder[0].Time - S->T0;
			const float B = S->Sink->Strikes[0].Info.Brightness;
			const double Base = FMath::Lerp(4.5, 0.6, static_cast<double>(B));
			Test->TestEqual(TEXT("A strike's thunder is the near set whatever the brightness"), Thunder[0].Aux, static_cast<int32>(LBAudioLogic::EThunderSet::Near));
			Test->TestTrue(FString::Printf(TEXT("Its delay follows the brightness (%.3f vs %.2f +- 0.4; brightness %.2f)"), ThunderDelay, Base, B), ThunderDelay >= Base - 0.4 - 0.02 && ThunderDelay <= Base + 0.4 + 0.35);
			Test->TestTrue(TEXT("The crack came before the thunder"), Crack[0].Time < Thunder[0].Time);
			Test->TestNearlyEqual(TEXT("Thunder volume 0.55 + 0.45 * brightness"), Thunder[0].Volume, 0.55f + 0.45f * B, 1.0e-3f);
			return true;
		}
		default:
			return true;
		}
	}, 60.f);

	AudioEnqueue(R);
	return true;
}

// =====================================================================================================================
// 5. A ritual tag tolls the bell: three stage-2 strikes. A state replace tolls nothing. A new game tolls stage 1.
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioBellOnRitualTagTest, "LastBell.Functional.Audio.BellOnRitualTag", LB_AUDIOFUNC_FLAGS)
bool FLBAudioBellOnRitualTagTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, storm and director active"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ActivateAudio(C, *S, Test);
		return true;
	});

	R->Add(TEXT("State.Ritual.1 added: three stage-2 strikes at the bell, 0.3 s then 0.4 s apart, and drone B"), [S, Test](FAudioCtx& C)
	{
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		if (!Audio)
		{
			Test->AddError(TEXT("Audio subsystem is gone"));
			return true;
		}
		if (C.Elapsed > 10.0)
		{
			Test->AddError(FString::Printf(TEXT("Timed out in phase %d"), S->Phase));
			return true;
		}
		if (S->Phase == 0)
		{
			if (!Audio->IsActive() || C.Frames < 4)
			{
				return false;
			}
			Test->TestEqual(TEXT("No bell reached yet: stage 1"), Audio->GetBellStage(), 1);
			Audio->ClearRequests();
			S->T0 = C.Now;
			ULBWorldStateSubsystem::Get(C.W)->AddState(AudioTag(TEXT("State.Ritual.1")));
			S->Phase = 1;
			return false;
		}
		// Wait until the three strikes are in, plus a moment to see that no fourth comes.
		if (C.Now - S->T0 < 2.2)
		{
			return false;
		}
		const TArray<FLBAudioRequest> Bells = Requests(Audio, LBAudioCue::Bell);
		if (!Test->TestEqual(TEXT("Three strikes"), Bells.Num(), 3))
		{
			return true;
		}
		for (int32 Index = 0; Index < 3; ++Index)
		{
			Test->TestEqual(FString::Printf(TEXT("Strike %d is stage 2"), Index), Bells[Index].Aux, 2);
			Test->TestEqual(FString::Printf(TEXT("Strike %d plays Bell.Stage[1]"), Index), Bells[Index].Variant, 1);
			Test->TestTrue(FString::Printf(TEXT("Strike %d is at the bell location (%s)"), Index, *Bells[Index].Location.ToString()),
				Bells[Index].bPositional && Bells[Index].Location.Equals(FVector(5000.0, 0.0, 3000.0), 0.5));
			Test->TestNearlyEqual(TEXT("A beat strike is at full volume"), Bells[Index].Volume, 1.f, 1.0e-4f);
			const double Expected = 0.3 + 0.4 * Index;
			const double Offset = Bells[Index].Time - S->T0;
			Test->TestTrue(FString::Printf(TEXT("Strike %d comes %.1f s after the tag (%.3f)"), Index, Expected, Offset), Offset >= Expected - 0.02 && Offset <= Expected + 0.35);
		}
		Test->TestEqual(TEXT("The beat raised the bell stage to 2"), Audio->GetBellStage(), 2);
		Test->TestEqual(TEXT("Drone B starts with the beat"), Requests(Audio, LBAudioCue::LoopDrone).Num(), 1);
		Test->TestEqual(TEXT("No ambient toll (switched off)"), Requests(Audio, LBAudioCue::BellAmbient).Num(), 0);
		return true;
	}, 60.f);

	AudioEnqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioNoBellOnStateReplacedTest, "LastBell.Functional.Audio.NoBellOnStateReplaced", LB_AUDIOFUNC_FLAGS)
bool FLBAudioNoBellOnStateReplacedTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, storm and director active"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ActivateAudio(C, *S, Test);
		return true;
	});

	R->Add(TEXT("A checkpoint load (state replaced with two ritual tags) tolls nothing and plays no drone, but counts as progress"), [S, Test](FAudioCtx& C)
	{
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		if (!Audio)
		{
			Test->AddError(TEXT("Audio subsystem is gone"));
			return true;
		}
		if (S->Phase == 0)
		{
			if (!Audio->IsActive() || C.Frames < 4)
			{
				return false;
			}
			Audio->ClearRequests();
			S->T0 = C.Now;
			FGameplayTagContainer Loaded;
			Loaded.AddTag(AudioTag(TEXT("State.Ritual.1")));
			Loaded.AddTag(AudioTag(TEXT("State.Ritual.2")));
			ULBWorldStateSubsystem::Get(C.W)->ReplaceState(Loaded);
			S->Phase = 1;
			return false;
		}
		// The shortened beats would have tolled within 0.3 s and finished within 1.1 s: three seconds is plenty.
		if (C.Now - S->T0 < 3.0)
		{
			return false;
		}
		Test->TestEqual(TEXT("No bell after OnStateReplaced"), Requests(Audio, LBAudioCue::Bell).Num(), 0);
		Test->TestEqual(TEXT("No drone after OnStateReplaced"), Requests(Audio, LBAudioCue::LoopDrone).Num(), 0);
		Test->TestEqual(TEXT("No ambient toll"), Requests(Audio, LBAudioCue::BellAmbient).Num(), 0);
		Test->TestEqual(TEXT("Nothing is scheduled"), Audio->GetScheduledCount(), 0);
		Test->TestEqual(TEXT("The loaded progress counts: bell stage 3"), Audio->GetBellStage(), 3);
		return true;
	}, 60.f);

	AudioEnqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioNewGameTollTest, "LastBell.Functional.Audio.NewGameToll", LB_AUDIOFUNC_FLAGS)
bool FLBAudioNewGameTollTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready; the director activates with the new-game toll on (0.5 s, 0.4 s apart, three strikes)"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ActivateAudio(C, *S, Test, [](ULBAudioSettings& A)
		{
			A.bNewGameToll = true;
			A.NewGameTollDelay = 0.5f;
			A.NewGameTollSpacing = 0.4f;
			A.NewGameTollStrikes = 3;
		});
		S->T0 = C.Now;
		return true;
	});

	R->Add(TEXT("A new game (no beat tag): three stage-1 strikes and drone A"), [S, Test](FAudioCtx& C)
	{
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		if (!Audio)
		{
			Test->AddError(TEXT("Audio subsystem is gone"));
			return true;
		}
		if (!Audio->IsActive())
		{
			if (C.Elapsed > 3.0)
			{
				Test->AddError(TEXT("The director did not become active within 3 s"));
				return true;
			}
			return false;
		}
		if (S->Phase == 0)
		{
			S->Phase = 1;
			S->T0 = C.Now;
			return false;
		}
		if (C.Now - S->T0 < 2.2)
		{
			return false;
		}
		const TArray<FLBAudioRequest> Bells = Requests(Audio, LBAudioCue::Bell);
		if (Test->TestEqual(TEXT("Three strikes"), Bells.Num(), 3))
		{
			for (int32 Index = 0; Index < 3; ++Index)
			{
				Test->TestEqual(FString::Printf(TEXT("Strike %d is stage 1"), Index), Bells[Index].Aux, 1);
			}
			Test->TestTrue(FString::Printf(TEXT("The first strike is NewGameTollDelay after activation (%.3f)"), Bells[0].Time - S->T0), Bells[0].Time - S->T0 > 0.3);
			Test->TestTrue(TEXT("The strikes are about 0.4 s apart"), Bells[1].Time - Bells[0].Time >= 0.38 && Bells[1].Time - Bells[0].Time <= 0.9);
		}
		Test->TestEqual(TEXT("Drone A starts with the first strike"), Requests(Audio, LBAudioCue::LoopDrone).Num(), 1);
		return true;
	}, 60.f);

	R->Add(TEXT("Switched off and on again with a beat tag present: no new-game toll"), [S, Test](FAudioCtx& C)
	{
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		if (!Audio)
		{
			Test->AddError(TEXT("Audio subsystem is gone"));
			return true;
		}
		if (C.Elapsed > 14.0)
		{
			Test->AddError(FString::Printf(TEXT("Timed out in phase %d"), S->Phase));
			return true;
		}
		switch (S->Phase)
		{
		case 1:
			FAudioEnabledGuard::Set(0);
			S->Phase = 2;
			return false;
		case 2:
			if (Audio->IsActive())
			{
				return false;
			}
			// Inactive: the tag is added with nobody listening, so nothing tolls for it.
			ULBWorldStateSubsystem::Get(C.W)->AddState(AudioTag(TEXT("State.Ritual.1")));
			Audio->ClearRequests();
			FAudioEnabledGuard::Set(1);
			S->Phase = 3;
			return false;
		case 3:
			if (!Audio->IsActive())
			{
				return false;
			}
			S->T0 = C.Now;
			S->Phase = 4;
			return false;
		default:
			if (C.Now - S->T0 < 2.5)
			{
				return false;
			}
			Test->TestEqual(TEXT("A checkpoint-style start (a beat tag present): no bell"), Requests(Audio, LBAudioCue::Bell).Num(), 0);
			Test->TestEqual(TEXT("...and no drone"), Requests(Audio, LBAudioCue::LoopDrone).Num(), 0);
			Test->TestEqual(TEXT("The tag already present counts: bell stage 2"), Audio->GetBellStage(), 2);
			return true;
		}
	}, 60.f);

	AudioEnqueue(R);
	return true;
}

// =====================================================================================================================
// 6. Ambient tolls
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioAmbientTollFuncTest, "LastBell.Functional.Audio.AmbientToll", LB_AUDIOFUNC_FLAGS)
bool FLBAudioAmbientTollFuncTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready; Ritual 1 is already in the state; ambient tolls every 1.5 to 2 s"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		// Reached before the director starts, so the start sees a checkpoint-like state: stage 2, no new-game toll.
		ULBWorldStateSubsystem::Get(C.W)->AddState(AudioTag(TEXT("State.Ritual.1")));
		ActivateAudio(C, *S, Test, [](ULBAudioSettings& A)
		{
			A.bAmbientTolls = true;
			A.AmbientTollInterval = FVector2D(1.5, 2.0);
			A.AmbientTollStrikes = FVector2D(1.0, 1.0);
			A.AmbientTollGapAfterBeat = 0.f;
			A.AmbientTollMaxTension = 0.5f;
		});
		return true;
	});

	R->Add(TEXT("A toll at the current stage (2), quietly, from the bell; none while a chase is forced"), [S, Test](FAudioCtx& C)
	{
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		if (!Audio)
		{
			Test->AddError(TEXT("Audio subsystem is gone"));
			return true;
		}
		if (C.Elapsed > 25.0)
		{
			Test->AddError(FString::Printf(TEXT("Timed out in phase %d"), S->Phase));
			return true;
		}
		switch (S->Phase)
		{
		case 0:
			if (!Audio->IsActive())
			{
				return false;
			}
			Test->TestEqual(TEXT("Ritual 1 was present at the start: bell stage 2"), Audio->GetBellStage(), 2);
			Audio->ClearRequests();
			S->T0 = C.Now;
			S->Phase = 1;
			return false;
		case 1:
		{
			const TArray<FLBAudioRequest> Tolls = Requests(Audio, LBAudioCue::BellAmbient);
			if (Tolls.IsEmpty())
			{
				return false;
			}
			const FLBAudioRequest& Toll = Tolls[0];
			AudioNote(FString::Printf(TEXT("ambient toll %.3f s after the start, stage %d, volume %.2f"), Toll.Time - S->T0, Toll.Aux, Toll.Volume));
			Test->TestEqual(TEXT("The toll plays the current stage"), Toll.Aux, 2);
			Test->TestNearlyEqual(TEXT("At AmbientTollVolume"), Toll.Volume, 0.5f, 1.0e-4f);
			Test->TestTrue(TEXT("From the bell"), Toll.bPositional && Toll.Location.Equals(FVector(5000.0, 0.0, 3000.0), 0.5));
			Test->TestTrue(FString::Printf(TEXT("It came within the interval plus a frame (%.3f)"), Toll.Time - S->T0), Toll.Time - S->T0 <= 2.0 + 0.5);
			Test->TestEqual(TEXT("No beat bell"), Requests(Audio, LBAudioCue::Bell).Num(), 0);
			// Now a chase: tolls that fall due are skipped and put off by 30 to 60 s.
			Audio->SetConsoleMusicState(static_cast<int32>(ELBWardenState::Chase));
			S->T1 = C.Now;
			S->Phase = 2;
			return false;
		}
		case 2:
			// Let the pending toll (if one was already scheduled) finish, then clear and watch.
			if (C.Now - S->T1 < 2.5)
			{
				return false;
			}
			Audio->ClearRequests();
			S->T1 = C.Now;
			S->Phase = 3;
			return false;
		default:
			if (C.Now - S->T1 < 7.0)
			{
				return false;
			}
			Test->TestEqual(TEXT("No ambient toll in 7 s of a forced chase"), Requests(Audio, LBAudioCue::BellAmbient).Num(), 0);
			Test->TestTrue(TEXT("The next toll was put off by 30 to 60 s from the skipped one (more than 20 s still to go)"), Audio->GetNextTollTime() - C.Now > 20.0);
			Audio->SetConsoleMusicState(-1);
			return true;
		}
	}, 90.f);

	AudioEnqueue(R);
	return true;
}

// =====================================================================================================================
// 7. The candle going out: a gasp and a jump in stress
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioCandleOutGaspTest, "LastBell.Functional.Audio.CandleOutGasp", LB_AUDIOFUNC_FLAGS)
bool FLBAudioCandleOutGaspTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, storm and director active"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ActivateAudio(C, *S, Test);
		return true;
	});

	R->Add(TEXT("The candle is snuffed: a gasp at once, the candle-out sound, stress jumps by about 0.35; then a relight sound"), [S, Test](FAudioCtx& C)
	{
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		ALBCharacter* Pawn = LBPie::Pawn();
		ULBCandleComponent* Candle = Pawn ? Pawn->GetCandle() : nullptr;
		if (!Audio || !Candle)
		{
			Test->AddError(TEXT("Audio subsystem or the player's candle is missing"));
			return true;
		}
		if (C.Elapsed > 10.0)
		{
			Test->AddError(FString::Printf(TEXT("Timed out in phase %d"), S->Phase));
			return true;
		}
		switch (S->Phase)
		{
		case 0:
			// A few ticks after activation, so the candle is bound.
			if (!Audio->IsActive() || C.Frames < 8)
			{
				return false;
			}
			if (!Test->TestTrue(TEXT("The candle starts lit"), Candle->IsLit()))
			{
				return true;
			}
			Audio->ClearRequests();
			S->T0 = Audio->GetStress();
			Test->TestTrue(TEXT("The stress is calm before (under 0.2)"), S->T0 < 0.2);
			Test->TestTrue(TEXT("ToggleCandle snuffs it"), Candle->ToggleCandle());
			// The gasp is immediate: the delegate fires inside ToggleCandle.
			Test->TestEqual(TEXT("A gasp"), Requests(Audio, LBAudioCue::BreathGasp).Num(), 1);
			Test->TestEqual(TEXT("The candle-out sound"), Requests(Audio, LBAudioCue::CandleOut).Num(), 1);
			Test->TestEqual(TEXT("No candle-light sound"), Requests(Audio, LBAudioCue::CandleLight).Num(), 0);
			S->Phase = 1;
			return false;
		case 1:
		{
			// The next tick applies the impulse: +0.35, minus a frame of decay.
			const float Stress = Audio->GetStress();
			Test->TestTrue(FString::Printf(TEXT("The stress jumped (%.3f from %.3f)"), Stress, static_cast<float>(S->T0)), Stress >= static_cast<float>(S->T0) + 0.25f && Stress <= 0.5f);
			const TArray<FLBAudioRequest> Gasp = Requests(Audio, LBAudioCue::BreathGasp);
			if (!Gasp.IsEmpty())
			{
				Test->TestTrue(TEXT("The gasp is a 2D one-shot with a variant"), !Gasp[0].bPositional && Gasp[0].Variant >= 0 && Gasp[0].Variant < 3);
			}
			// Stress above 0.3 breathes: a calm breath follows.
			Test->TestTrue(TEXT("A breath follows the gasp (stress at least 0.3)"), Requests(Audio, LBAudioCue::Breath).Num() >= 1);
			S->Phase = 2;
			return false;
		}
		default:
			Test->TestTrue(TEXT("ToggleCandle starts the relight"), Candle->ToggleCandle());
			Test->TestEqual(TEXT("A relight sound"), Requests(Audio, LBAudioCue::CandleRelight).Num(), 1);
			return true;
		}
	}, 60.f);

	AudioEnqueue(R);
	return true;
}

// =====================================================================================================================
// 8. The music follows the Warden's state
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioMusicFollowsWardenTest, "LastBell.Functional.Audio.MusicFollowsWarden", LB_AUDIOFUNC_FLAGS)
bool FLBAudioMusicFollowsWardenTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, storm and director active"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ActivateAudio(C, *S, Test);
		return true;
	});

	R->Add(TEXT("A forced chase: tension target 0.4, chase target 1, both layers fade in; cleared, they fade out"), [S, Test](FAudioCtx& C)
	{
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		if (!Audio)
		{
			Test->AddError(TEXT("Audio subsystem is gone"));
			return true;
		}
		if (C.Elapsed > 14.0)
		{
			Test->AddError(FString::Printf(TEXT("Timed out in phase %d"), S->Phase));
			return true;
		}
		switch (S->Phase)
		{
		case 0:
			if (!Audio->IsActive() || C.Frames < 4)
			{
				return false;
			}
			Test->TestNearlyEqual(TEXT("Silent by default: tension target 0"), Audio->GetMusicTargets().Tension, 0.f, 1.0e-4f);
			Test->TestNearlyEqual(TEXT("Silent by default: chase target 0"), Audio->GetMusicTargets().Chase, 0.f, 1.0e-4f);
			Audio->ClearRequests();
			Audio->SetConsoleMusicState(static_cast<int32>(ELBWardenState::Chase));
			S->T0 = C.Now;
			S->Phase = 1;
			return false;
		case 1:
			// Tension fades in over 3 s (to 0.4: 1.2 s), the chase layer over 0.8 s.
			if (C.Now - S->T0 < 1.6)
			{
				return false;
			}
			Test->TestNearlyEqual(TEXT("Chase: the tension target is 0.4"), Audio->GetMusicTargets().Tension, 0.4f, 1.0e-4f);
			Test->TestNearlyEqual(TEXT("Chase: the chase target is 1"), Audio->GetMusicTargets().Chase, 1.f, 1.0e-4f);
			Test->TestNearlyEqual(TEXT("The chase layer reached 1"), Audio->GetLayerLevel(ELBAudioLayer::Chase), 1.f, 0.02f);
			Test->TestNearlyEqual(TEXT("The tension layer reached 0.4"), Audio->GetLayerLevel(ELBAudioLayer::Tension), 0.4f, 0.02f);
			Test->TestEqual(TEXT("The chase loop started once"), Requests(Audio, LBAudioCue::LoopChase).Num(), 1);
			Test->TestEqual(TEXT("The tension loop started once"), Requests(Audio, LBAudioCue::LoopTension).Num(), 1);
			Test->TestEqual(TEXT("No drone"), Requests(Audio, LBAudioCue::LoopDrone).Num(), 0);
			Audio->SetConsoleMusicState(-1);
			S->T1 = C.Now;
			S->Phase = 2;
			return false;
		default:
			if (C.Now - S->T1 < 1.0)
			{
				return false;
			}
			Test->TestNearlyEqual(TEXT("Cleared: the targets are 0 (the Warden is dormant)"), Audio->GetMusicTargets().Chase + Audio->GetMusicTargets().Tension, 0.f, 1.0e-4f);
			Test->TestTrue(FString::Printf(TEXT("The chase layer is fading out (%.2f)"), Audio->GetLayerLevel(ELBAudioLayer::Chase)),
				Audio->GetLayerLevel(ELBAudioLayer::Chase) < 0.95f && Audio->GetLayerLevel(ELBAudioLayer::Chase) > 0.5f);
			return true;
		}
	}, 60.f);

	AudioEnqueue(R);
	return true;
}

// =====================================================================================================================
// 9. Interaction cues
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioInteractionCueTest, "LastBell.Functional.Audio.InteractionCue", LB_AUDIOFUNC_FLAGS)
bool FLBAudioInteractionCueTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready; the cue map has a row for AActor (volume 0.3), a more specific one for AStaticMeshActor (0.8), and ATriggerBox is silent"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ActivateAudio(C, *S, Test, [](ULBAudioSettings& A)
		{
			FLBInteractionCue General;
			General.ActorClass = TSoftClassPtr<AActor>(AActor::StaticClass());
			FillSet(General.Interact, 2);
			General.Volume = 0.3f;
			A.InteractionCues.Add(General);
			FLBInteractionCue Specific;
			Specific.ActorClass = TSoftClassPtr<AActor>(AStaticMeshActor::StaticClass());
			FillSet(Specific.Interact, 3);
			Specific.Volume = 0.8f;
			Specific.Pitch = FVector2D(0.97, 1.03);
			A.InteractionCues.Add(Specific);
			A.SilentClasses.Add(TSoftClassPtr<AActor>(ATriggerBox::StaticClass()));
		});
		return true;
	});

	R->Add(TEXT("Using them: the most specific row sounds at the actor, variants do not repeat, the silent class makes no request"), [S, Test](FAudioCtx& C)
	{
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		ALBCharacter* Pawn = LBPie::Pawn();
		if (!Audio || !Pawn)
		{
			Test->AddError(TEXT("Audio subsystem or the pawn is gone"));
			return true;
		}
		if (!Audio->IsActive())
		{
			if (C.Elapsed > 3.0)
			{
				Test->AddError(TEXT("The director did not become active within 3 s"));
				return true;
			}
			return false;
		}

		const FVector Base = Pawn->GetActorLocation() + FVector(600.0, 0.0, 100.0);
		ULBInteractableComponent* MeshInteractable = nullptr;
		ULBInteractableComponent* PointInteractable = nullptr;
		ULBInteractableComponent* BoxInteractable = nullptr;
		AStaticMeshActor* Mesh = SpawnInteractable<AStaticMeshActor>(C.W, Base, MeshInteractable);
		ATargetPoint* Point = SpawnInteractable<ATargetPoint>(C.W, Base + FVector(300.0, 0.0, 0.0), PointInteractable);
		ATriggerBox* Box = SpawnInteractable<ATriggerBox>(C.W, Base + FVector(600.0, 0.0, 0.0), BoxInteractable);
		if (!Test->TestTrue(TEXT("The test actors spawned"), Mesh && Point && Box && MeshInteractable && PointInteractable && BoxInteractable))
		{
			return true;
		}
		Audio->RefreshBindings();
		Test->TestTrue(TEXT("The three actors are bound"), Audio->GetBoundActorCount() >= 3);
		Audio->ClearRequests();

		// The specific row for the static mesh actor.
		MeshInteractable->Interact(Pawn);
		TArray<FLBAudioRequest> Interacts = Requests(Audio, LBAudioCue::Interact);
		if (Test->TestEqual(TEXT("One interaction request"), Interacts.Num(), 1))
		{
			Test->TestTrue(FString::Printf(TEXT("It is at the actor (%s)"), *Interacts[0].Location.ToString()), Interacts[0].bPositional && Interacts[0].Location.Equals(Base, 1.0));
			Test->TestNearlyEqual(TEXT("It uses the specific row's volume 0.8"), Interacts[0].Volume, 0.8f, 1.0e-4f);
			Test->TestEqual(TEXT("It is cue row 1"), Interacts[0].Aux, 1);
			Test->TestTrue(TEXT("Its pitch is inside the row's range"), Interacts[0].Pitch >= 0.97f - 1.0e-4f && Interacts[0].Pitch <= 1.03f + 1.0e-4f);
			Test->TestTrue(TEXT("A variant was picked and loaded"), Interacts[0].Variant >= 0 && Interacts[0].Variant < 3 && Interacts[0].bSoundResolved);
		}

		// Variants never repeat.
		for (int32 Use = 0; Use < 40; ++Use)
		{
			MeshInteractable->Interact(Pawn);
		}
		Interacts = Requests(Audio, LBAudioCue::Interact);
		int32 Repeats = 0;
		for (int32 Index = 1; Index < Interacts.Num(); ++Index)
		{
			Repeats += Interacts[Index].Variant == Interacts[Index - 1].Variant ? 1 : 0;
		}
		Test->TestEqual(TEXT("41 uses: 41 requests"), Interacts.Num(), 41);
		Test->TestEqual(TEXT("41 uses: the same variant never twice in a row"), Repeats, 0);

		// The general row for another actor class.
		Audio->ClearRequests();
		PointInteractable->Interact(Pawn);
		Interacts = Requests(Audio, LBAudioCue::Interact);
		if (Test->TestEqual(TEXT("The target point sounds through the AActor row"), Interacts.Num(), 1))
		{
			Test->TestNearlyEqual(TEXT("Volume 0.3"), Interacts[0].Volume, 0.3f, 1.0e-4f);
			Test->TestEqual(TEXT("Cue row 0"), Interacts[0].Aux, 0);
		}

		// Silent on purpose: the trigger box is more specific than the AActor row.
		Audio->ClearRequests();
		BoxInteractable->Interact(Pawn);
		Test->TestEqual(TEXT("A silent class makes no request"), Requests(Audio, LBAudioCue::Interact).Num(), 0);
		return true;
	}, 60.f);

	AudioEnqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioDeniedCueTest, "LastBell.Functional.Audio.DeniedCue", LB_AUDIOFUNC_FLAGS)
bool FLBAudioDeniedCueTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready; a row for AStaticMeshActor with Interact, Denied and DialNotch sounds"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ActivateAudio(C, *S, Test, [](ULBAudioSettings& A)
		{
			FLBInteractionCue Cue;
			Cue.ActorClass = TSoftClassPtr<AActor>(AStaticMeshActor::StaticClass());
			FillSet(Cue.Interact, 2);
			FillSet(Cue.Denied, 2);
			FillSet(Cue.DialNotch, 2);
			Cue.Volume = 0.9f;
			A.InteractionCues.Add(Cue);
		});
		return true;
	});

	R->Add(TEXT("A locked interactable plays its denied sound and not its interact sound; unlocked it plays the interact sound"), [S, Test](FAudioCtx& C)
	{
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		ALBCharacter* Pawn = LBPie::Pawn();
		if (!Audio || !Pawn)
		{
			Test->AddError(TEXT("Audio subsystem or the pawn is gone"));
			return true;
		}
		if (!Audio->IsActive())
		{
			if (C.Elapsed > 3.0)
			{
				Test->AddError(TEXT("The director did not become active within 3 s"));
				return true;
			}
			return false;
		}
		const FVector Where = Pawn->GetActorLocation() + FVector(500.0, 200.0, 100.0);
		ULBInteractableComponent* Interactable = nullptr;
		AStaticMeshActor* Door = SpawnInteractable<AStaticMeshActor>(C.W, Where, Interactable, /*bEnabled*/ false);
		if (!Test->TestTrue(TEXT("The locked door spawned"), Door && Interactable))
		{
			return true;
		}
		Audio->RefreshBindings();
		Audio->ClearRequests();

		Interactable->Interact(Pawn);
		const TArray<FLBAudioRequest> Denied = Requests(Audio, LBAudioCue::Denied);
		if (Test->TestEqual(TEXT("One denied request"), Denied.Num(), 1))
		{
			Test->TestTrue(TEXT("It is at the door"), Denied[0].bPositional && Denied[0].Location.Equals(Where, 1.0));
			Test->TestNearlyEqual(TEXT("At the row's volume"), Denied[0].Volume, 0.9f, 1.0e-4f);
			Test->TestTrue(TEXT("A denied variant was picked"), Denied[0].Variant >= 0 && Denied[0].Variant < 2);
		}
		Test->TestEqual(TEXT("No interact sound for a refused use"), Requests(Audio, LBAudioCue::Interact).Num(), 0);

		Audio->ClearRequests();
		Interactable->bEnabled = true;
		Interactable->Interact(Pawn);
		Test->TestEqual(TEXT("Unlocked: the interact sound"), Requests(Audio, LBAudioCue::Interact).Num(), 1);
		Test->TestEqual(TEXT("Unlocked: no denied sound"), Requests(Audio, LBAudioCue::Denied).Num(), 0);
		return true;
	}, 60.f);

	AudioEnqueue(R);
	return true;
}

// =====================================================================================================================
// 9b. P16-6: a note rustles when it is picked up (the inspection begins), not only when it is put down
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioNotePickupCueTest, "LastBell.Functional.Audio.NotePickupCue", LB_AUDIOFUNC_FLAGS)
bool FLBAudioNotePickupCueTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready; AStaticMeshActor is mapped to a 3-variant Interact cue (volume 0.8)"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ActivateAudio(C, *S, Test, [](ULBAudioSettings& A)
		{
			FLBInteractionCue Note;
			Note.ActorClass = TSoftClassPtr<AActor>(AStaticMeshActor::StaticClass());
			FillSet(Note.Interact, 3);
			Note.Volume = 0.8f;
			A.InteractionCues.Add(Note);
		});
		return true;
	});

	R->Add(TEXT("Beginning an inspection plays the mapped Interact cue at the actor once; an unmapped actor stays silent"), [S, Test](FAudioCtx& C)
	{
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		ALBCharacter* Pawn = LBPie::Pawn();
		if (!Audio || !Pawn || !Pawn->GetInspection())
		{
			Test->AddError(TEXT("Audio subsystem, the pawn or its inspection component is gone"));
			return true;
		}
		if (!Audio->IsActive() || C.Frames < 4)
		{
			if (C.Elapsed > 3.0)
			{
				Test->AddError(TEXT("The director did not become active within 3 s"));
				return true;
			}
			return false;
		}

		const FVector Base = Pawn->GetActorLocation() + FVector(300.0, 0.0, 100.0);
		AStaticMeshActor* Note = C.W->SpawnActor<AStaticMeshActor>(Base, FRotator::ZeroRotator);
		if (!Test->TestNotNull(TEXT("The note actor spawned"), Note))
		{
			return true;
		}
		Note->SetMobility(EComponentMobility::Movable);
		Note->SetActorLocation(Base);
		ULBInspectableComponent* Inspectable = NewObject<ULBInspectableComponent>(Note);
		Note->AddInstanceComponent(Inspectable);
		Inspectable->RegisterComponent();

		ULBInspectionComponent* Inspection = Pawn->GetInspection();
		Audio->ClearRequests();
		if (Test->TestTrue(TEXT("BeginInspect succeeded"), Inspection->BeginInspect(Inspectable)))
		{
			const TArray<FLBAudioRequest> Interacts = Requests(Audio, LBAudioCue::Interact);
			if (Test->TestEqual(TEXT("The pick-up made one Interact request, in the same call"), Interacts.Num(), 1))
			{
				Test->TestTrue(FString::Printf(TEXT("It is at the note (%s)"), *Interacts[0].Location.ToString()), Interacts[0].bPositional && Interacts[0].Location.Equals(Base, 1.0));
				Test->TestNearlyEqual(TEXT("It uses the row's volume 0.8"), Interacts[0].Volume, 0.8f, 1.0e-4f);
				Test->TestTrue(TEXT("A variant was picked and loaded"), Interacts[0].Variant >= 0 && Interacts[0].Variant < 3 && Interacts[0].bSoundResolved);
			}
			Inspection->CancelInspect();
			Test->TestEqual(TEXT("Cancelling the inspection plays the put-down cue (a second request; NotePutDownCue checks it in detail)"), Requests(Audio, LBAudioCue::Interact).Num(), 2);
		}

		// An inspectable whose class has no row makes no request (an unmapped class is silent).
		Audio->ClearRequests();
		ATargetPoint* Bare = C.W->SpawnActor<ATargetPoint>(Base + FVector(0.0, 300.0, 0.0), FRotator::ZeroRotator);
		if (Test->TestNotNull(TEXT("The unmapped actor spawned"), Bare) && Bare->GetRootComponent())
		{
			Bare->GetRootComponent()->SetMobility(EComponentMobility::Movable);
			ULBInspectableComponent* BareInspectable = NewObject<ULBInspectableComponent>(Bare);
			Bare->AddInstanceComponent(BareInspectable);
			BareInspectable->RegisterComponent();
			if (Inspection->BeginInspect(BareInspectable))
			{
				Test->TestEqual(TEXT("An unmapped class makes no Interact request"), Requests(Audio, LBAudioCue::Interact).Num(), 0);
				Inspection->CancelInspect();
			}
			Bare->Destroy();
		}
		Note->Destroy();
		return true;
	}, 60.f);

	AudioEnqueue(R);
	return true;
}

// =====================================================================================================================
// 9b2. P16-6: a note also rustles when it is put down (every inspection end, kept or cancelled), and a kept item rustles once, not twice
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioNotePutDownCueTest, "LastBell.Functional.Audio.NotePutDownCue", LB_AUDIOFUNC_FLAGS)
bool FLBAudioNotePutDownCueTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready; AStaticMeshActor is mapped to a 3-variant Interact cue (volume 0.8)"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ActivateAudio(C, *S, Test, [](ULBAudioSettings& A)
		{
			FLBInteractionCue Note;
			Note.ActorClass = TSoftClassPtr<AActor>(AStaticMeshActor::StaticClass());
			FillSet(Note.Interact, 3);
			Note.Volume = 0.8f;
			A.InteractionCues.Add(Note);
		});
		return true;
	});

	R->Add(TEXT("Cancel and a normal close each play one put-down request at the note; a kept item makes one request at put-down, not two"), [S, Test](FAudioCtx& C)
	{
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		ALBCharacter* Pawn = LBPie::Pawn();
		if (!Audio || !Pawn || !Pawn->GetInspection())
		{
			Test->AddError(TEXT("Audio subsystem, the pawn or its inspection component is gone"));
			return true;
		}
		if (!Audio->IsActive() || C.Frames < 4)
		{
			if (C.Elapsed > 3.0)
			{
				Test->AddError(TEXT("The director did not become active within 3 s"));
				return true;
			}
			return false;
		}
		ULBInspectionComponent* Inspection = Pawn->GetInspection();
		const FVector Base = Pawn->GetActorLocation() + FVector(300.0, 0.0, 100.0);

		// ---- A note put back (bKeepOnClose false) ----
		ULBInteractableComponent* NoteInteractable = nullptr;
		AStaticMeshActor* Note = SpawnInteractable<AStaticMeshActor>(C.W, Base, NoteInteractable);
		if (!Test->TestTrue(TEXT("The note spawned"), Note && NoteInteractable))
		{
			return true;
		}
		ULBInspectableComponent* NoteInspectable = NewObject<ULBInspectableComponent>(Note);
		Note->AddInstanceComponent(NoteInspectable);
		NoteInspectable->RegisterComponent();
		Audio->RefreshBindings();

		Audio->ClearRequests();
		if (Test->TestTrue(TEXT("BeginInspect succeeded"), Inspection->BeginInspect(NoteInspectable, NoteInteractable)))
		{
			Test->TestEqual(TEXT("Cancel path: one request at pick-up"), Requests(Audio, LBAudioCue::Interact).Num(), 1);
			Inspection->CancelInspect();
			const TArray<FLBAudioRequest> After = Requests(Audio, LBAudioCue::Interact);
			if (Test->TestEqual(TEXT("Cancel path: one more request at put-down"), After.Num(), 2))
			{
				Test->TestTrue(TEXT("Cancel path: the put-down is at the note"), After[1].bPositional && After[1].Location.Equals(Base, 1.0));
			}

			Audio->ClearRequests();
			Test->TestTrue(TEXT("BeginInspect again succeeded"), Inspection->BeginInspect(NoteInspectable, NoteInteractable));
			Inspection->EndInspect();
			Test->TestEqual(TEXT("Normal close of an item that is put back: pick-up and put-down, two requests"), Requests(Audio, LBAudioCue::Interact).Num(), 2);
			Test->TestFalse(TEXT("The inspection is over"), Inspection->IsInspecting());

			// A second end with nothing inspected plays nothing.
			Audio->ClearRequests();
			Inspection->CancelInspect();
			Test->TestEqual(TEXT("Cancelling while not inspecting plays nothing"), Requests(Audio, LBAudioCue::Interact).Num(), 0);
		}
		Note->Destroy();

		// ---- A kept item: OnInteracted (the grant) and OnInspectEnd both fire; only one put-down rustle ----
		ULBInteractableComponent* KeyInteractable = nullptr;
		AStaticMeshActor* Key = SpawnInteractable<AStaticMeshActor>(C.W, Base + FVector(0.0, 300.0, 0.0), KeyInteractable);
		if (Test->TestTrue(TEXT("The kept item spawned"), Key && KeyInteractable))
		{
			KeyInteractable->bInspectOnInteract = true;
			ULBInspectableComponent* KeyInspectable = NewObject<ULBInspectableComponent>(Key);
			KeyInspectable->bKeepOnClose = true;
			Key->AddInstanceComponent(KeyInspectable);
			KeyInspectable->RegisterComponent();
			Audio->RefreshBindings();

			Audio->ClearRequests();
			KeyInteractable->Interact(Pawn);
			if (Test->TestTrue(TEXT("Interact opened the inspection"), Inspection->IsInspecting()))
			{
				Test->TestEqual(TEXT("Kept item: one request at pick-up"), Requests(Audio, LBAudioCue::Interact).Num(), 1);
				Inspection->EndInspect();
				Test->TestEqual(TEXT("Kept item: exactly one more request at put-down (two in all, not three)"), Requests(Audio, LBAudioCue::Interact).Num(), 2);
			}
			Key->Destroy();
		}

		// ---- A plain interactable (not inspected) is unchanged: one request per Interact ----
		ULBInteractableComponent* DoorInteractable = nullptr;
		AStaticMeshActor* Door = SpawnInteractable<AStaticMeshActor>(C.W, Base + FVector(0.0, -300.0, 0.0), DoorInteractable);
		if (Test->TestTrue(TEXT("The plain interactable spawned"), Door && DoorInteractable))
		{
			Audio->RefreshBindings();
			Audio->ClearRequests();
			DoorInteractable->Interact(Pawn);
			Test->TestEqual(TEXT("A plain interactable still makes one Interact request"), Requests(Audio, LBAudioCue::Interact).Num(), 1);
			Door->Destroy();
		}
		return true;
	}, 60.f);

	AudioEnqueue(R);
	return true;
}

// =====================================================================================================================
// 9c. P16-6: the great bell of the finale: the first strike is requested in the same frame as the tag (the ending pauses the game)
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioFinaleBellImmediateTest, "LastBell.Functional.Audio.FinaleBellImmediate", LB_AUDIOFUNC_FLAGS)
bool FLBAudioFinaleBellImmediateTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, storm and director active"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ActivateAudio(C, *S, Test);
		return true;
	});

	R->Add(TEXT("State.Event.Finale: strike 1 (stage 5) is requested by the AddState call itself, the other four follow 0.4 s apart"), [S, Test](FAudioCtx& C)
	{
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		if (!Audio)
		{
			Test->AddError(TEXT("Audio subsystem is gone"));
			return true;
		}
		if (C.Elapsed > 10.0)
		{
			Test->AddError(FString::Printf(TEXT("Timed out in phase %d"), S->Phase));
			return true;
		}
		if (S->Phase == 0)
		{
			if (!Audio->IsActive() || C.Frames < 4)
			{
				return false;
			}
			Audio->ClearRequests();
			S->T0 = C.Now;
			ULBWorldStateSubsystem::Get(C.W)->AddState(AudioTag(TEXT("State.Event.Finale")));
			const TArray<FLBAudioRequest> Immediate = Requests(Audio, LBAudioCue::Bell);
			if (Test->TestEqual(TEXT("One stage-5 strike was requested before AddState returned"), Immediate.Num(), 1))
			{
				Test->TestEqual(TEXT("It is stage 5"), Immediate[0].Aux, 5);
				Test->TestEqual(TEXT("It plays Bell.Stage[4]"), Immediate[0].Variant, 4);
				Test->TestNearlyEqual(TEXT("It is at the same world time as the tag"), static_cast<float>(Immediate[0].Time - S->T0), 0.f, 1.0e-4f);
			}
			Test->TestEqual(TEXT("The other four strikes are scheduled"), Audio->GetScheduledCount(), 4);
			S->Phase = 1;
			return false;
		}
		if (C.Now - S->T0 < 2.4)
		{
			return false;
		}
		const TArray<FLBAudioRequest> Bells = Requests(Audio, LBAudioCue::Bell);
		if (Test->TestEqual(TEXT("Five strikes in all"), Bells.Num(), 5))
		{
			for (int32 Index = 1; Index < Bells.Num(); ++Index)
			{
				const double Gap = Bells[Index].Time - Bells[Index - 1].Time;
				Test->TestTrue(FString::Printf(TEXT("Strike %d comes %.2f s after the one before (about 0.4)"), Index, Gap), Gap >= 0.38 && Gap <= 0.75);
				Test->TestEqual(TEXT("Every strike is stage 5"), Bells[Index].Aux, 5);
			}
		}
		Test->TestEqual(TEXT("The bell stage is 5"), Audio->GetBellStage(), 5);
		Test->TestEqual(TEXT("Nothing is left scheduled"), Audio->GetScheduledCount(), 0);
		return true;
	}, 60.f);

	AudioEnqueue(R);
	return true;
}

// =====================================================================================================================
// 10. The small bells: pitch per bell, the fail cluster, the solved chord
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioSequenceSmallBellPitchTest, "LastBell.Functional.Audio.SequenceSmallBellPitch", LB_AUDIOFUNC_FLAGS)
bool FLBAudioSequenceSmallBellPitchTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	// D-081: the sizes 1.30, 1.15, 1.00 and 0.85 give the pitches 1 / size.
	static const TCHAR* BellTags[4] = { TEXT("State.Tower.Bell.1"), TEXT("State.Tower.Bell.2"), TEXT("State.Tower.Bell.3"), TEXT("State.Tower.Bell.4") };
	static const float BellSizes[4] = { 1.30f, 1.15f, 1.00f, 0.85f };

	R->Add(TEXT("PIE ready; four bells, each granting its step tag, and a sequence puzzle over the four tags"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ULBAudioSubsystem* Audio = ActivateAudio(C, *S, Test, [](ULBAudioSettings& A)
		{
			for (int32 Index = 0; Index < 4; ++Index)
			{
				A.SmallBellPitch.Add(LBPie::Tag(BellTags[Index]), 1.f / BellSizes[Index]);
			}
		});
		if (!Audio)
		{
			return true;
		}
		const ALBCharacter* Pawn = LBPie::Pawn();
		const FVector Base = (Pawn ? Pawn->GetActorLocation() : FVector::ZeroVector) + FVector(500.0, 0.0, 100.0);
		for (int32 Index = 0; Index < 4; ++Index)
		{
			ULBInteractableComponent* Interactable = nullptr;
			AStaticMeshActor* Bell = SpawnInteractable<AStaticMeshActor>(C.W, Base + FVector(0.0, 250.0 * Index, 0.0), Interactable);
			if (!Test->TestTrue(TEXT("A bell spawned"), Bell && Interactable))
			{
				return true;
			}
			Interactable->GrantedStateTags.AddTag(LBPie::Tag(BellTags[Index]));
			S->Actors.Add(Bell);
		}
		// The puzzle lives on its own actor, away from the bells, as in the level.
		AStaticMeshActor* Controller = C.W->SpawnActor<AStaticMeshActor>(Base + FVector(0.0, -800.0, 0.0), FRotator::ZeroRotator);
		if (!Test->TestNotNull(TEXT("The puzzle actor spawned"), Controller))
		{
			return true;
		}
		ULBSequencePuzzleComponent* Puzzle = NewObject<ULBSequencePuzzleComponent>(Controller);
		for (const TCHAR* Name : BellTags)
		{
			Puzzle->Steps.Add(LBPie::Tag(Name));
		}
		Puzzle->SolvedTags.AddTag(LBPie::Tag(TEXT("State.Tower.BellsSolved")));
		Controller->AddInstanceComponent(Puzzle);
		Puzzle->RegisterComponent();
		S->Actors.Add(Controller);
		S->Anchor = Controller->GetActorLocation();
		return true;
	});

	R->Add(TEXT("Steps in order strike each bell at its pitch; a wrong step fails; the right order solves"), [S, Test](FAudioCtx& C)
	{
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		if (!Audio || S->Actors.Num() != 5)
		{
			Test->AddError(TEXT("Audio subsystem or the test actors are gone"));
			return true;
		}
		ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(C.W);
		if (C.Elapsed > 14.0)
		{
			Test->AddError(FString::Printf(TEXT("Timed out in phase %d"), S->Phase));
			return true;
		}
		switch (S->Phase)
		{
		case 0:
			if (!Audio->IsActive())
			{
				return false;
			}
			Audio->RefreshBindings();
			Test->TestTrue(TEXT("The four bells and the puzzle actor are bound"), Audio->GetBoundActorCount() >= 5);
			Audio->ClearRequests();
			// Bell 1 then bell 2, in order.
			State->AddState(LBPie::Tag(BellTags[0]));
			State->AddState(LBPie::Tag(BellTags[1]));
			S->Phase = 1;
			return false;
		case 1:
		{
			const TArray<FLBAudioRequest> Strikes = Requests(Audio, LBAudioCue::SmallBellStrike);
			if (!Test->TestEqual(TEXT("Two strikes for two accepted steps"), Strikes.Num(), 2))
			{
				return true;
			}
			for (int32 Index = 0; Index < 2; ++Index)
			{
				Test->TestNearlyEqual(FString::Printf(TEXT("Bell %d plays at pitch 1 / %.2f"), Index + 1, BellSizes[Index]), Strikes[Index].Pitch, 1.f / BellSizes[Index], 1.0e-4f);
				Test->TestEqual(FString::Printf(TEXT("Strike %d carries the step index"), Index), Strikes[Index].Aux, Index);
				Test->TestTrue(FString::Printf(TEXT("Bell %d sounds at the bell, not at the puzzle actor"), Index + 1),
					S->Actors[Index].IsValid() && Strikes[Index].Location.Equals(S->Actors[Index]->GetActorLocation(), 1.0));
			}
			// Bell 4 out of turn (bell 3 is next): the puzzle fails on the next tick.
			State->AddState(LBPie::Tag(BellTags[3]));
			S->Phase = 2;
			return false;
		}
		case 2:
		{
			const TArray<FLBAudioRequest> Fail = Requests(Audio, LBAudioCue::SmallBellFail);
			if (Fail.IsEmpty())
			{
				return false;
			}
			Test->TestEqual(TEXT("One fail cluster"), Fail.Num(), 1);
			Test->TestTrue(TEXT("It sounds at the wrong bell"), S->Actors[3].IsValid() && Fail[0].Location.Equals(S->Actors[3]->GetActorLocation(), 1.0));
			Test->TestEqual(TEXT("No strike for the wrong step"), Requests(Audio, LBAudioCue::SmallBellStrike).Num(), 2);
			Audio->ClearRequests();
			S->Phase = 3;
			S->Counter = C.Frames;
			return false;
		}
		case 3:
			// The puzzle removed the step tags; let it settle, then play the right order.
			if (C.Frames - S->Counter < 4)
			{
				return false;
			}
			for (const TCHAR* Name : BellTags)
			{
				State->AddState(LBPie::Tag(Name));
			}
			S->Phase = 4;
			return false;
		default:
		{
			const TArray<FLBAudioRequest> Strikes = Requests(Audio, LBAudioCue::SmallBellStrike);
			const TArray<FLBAudioRequest> Solved = Requests(Audio, LBAudioCue::SmallBellSolved);
			if (Solved.IsEmpty())
			{
				return false;
			}
			Test->TestEqual(TEXT("Four strikes in the right order"), Strikes.Num(), 4);
			for (int32 Index = 0; Index < Strikes.Num() && Index < 4; ++Index)
			{
				Test->TestNearlyEqual(FString::Printf(TEXT("Strike %d pitch"), Index), Strikes[Index].Pitch, 1.f / BellSizes[Index], 1.0e-4f);
			}
			Test->TestEqual(TEXT("One solved chord"), Solved.Num(), 1);
			Test->TestTrue(TEXT("It sounds at the puzzle's actor"), Solved[0].Location.Equals(S->Anchor, 1.0));
			Test->TestEqual(TEXT("No fail this time"), Requests(Audio, LBAudioCue::SmallBellFail).Num(), 0);
			return true;
		}
		}
	}, 60.f);

	AudioEnqueue(R);
	return true;
}

// =====================================================================================================================
// 10b. The chapel candle puzzle is not the bell puzzle: no small-bell sounds, a candle-out on failure
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioCandlePuzzleNotBellsTest, "LastBell.Functional.Audio.CandlePuzzleNotBells", LB_AUDIOFUNC_FLAGS)
bool FLBAudioCandlePuzzleNotBellsTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	static const TCHAR* CandleTags[4] = { TEXT("State.Chapel.Candle.1"), TEXT("State.Chapel.Candle.2"), TEXT("State.Chapel.Candle.3"), TEXT("State.Chapel.Candle.4") };
	static const TCHAR* BellTags[4] = { TEXT("State.Tower.Bell.1"), TEXT("State.Tower.Bell.2"), TEXT("State.Tower.Bell.3"), TEXT("State.Tower.Bell.4") };

	R->Add(TEXT("PIE ready; SmallBellPitch holds the bell tags only; four candles and a sequence puzzle over the candle tags"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ULBAudioSubsystem* Audio = ActivateAudio(C, *S, Test, [](ULBAudioSettings& A)
		{
			for (int32 Index = 0; Index < 4; ++Index)
			{
				A.SmallBellPitch.Add(LBPie::Tag(BellTags[Index]), 1.f);
			}
		});
		if (!Audio)
		{
			return true;
		}
		const ALBCharacter* Pawn = LBPie::Pawn();
		const FVector Base = (Pawn ? Pawn->GetActorLocation() : FVector::ZeroVector) + FVector(500.0, 0.0, 100.0);
		for (int32 Index = 0; Index < 4; ++Index)
		{
			ULBInteractableComponent* Interactable = nullptr;
			AStaticMeshActor* Candle = SpawnInteractable<AStaticMeshActor>(C.W, Base + FVector(0.0, 250.0 * Index, 0.0), Interactable);
			if (!Test->TestTrue(TEXT("A candle spawned"), Candle && Interactable))
			{
				return true;
			}
			Interactable->GrantedStateTags.AddTag(LBPie::Tag(CandleTags[Index]));
			S->Actors.Add(Candle);
		}
		AStaticMeshActor* Controller = C.W->SpawnActor<AStaticMeshActor>(Base + FVector(0.0, -800.0, 0.0), FRotator::ZeroRotator);
		if (!Test->TestNotNull(TEXT("The puzzle actor spawned"), Controller))
		{
			return true;
		}
		ULBSequencePuzzleComponent* Puzzle = NewObject<ULBSequencePuzzleComponent>(Controller);
		for (const TCHAR* Name : CandleTags)
		{
			Puzzle->Steps.Add(LBPie::Tag(Name));
		}
		Puzzle->SolvedTags.AddTag(LBPie::Tag(TEXT("State.Chapel.CandlesSolved")));
		Controller->AddInstanceComponent(Puzzle);
		Puzzle->RegisterComponent();
		S->Actors.Add(Controller);
		S->Anchor = Controller->GetActorLocation();
		return true;
	});

	R->Add(TEXT("Candle steps are silent, a wrong candle plays one candle-out at the puzzle, solving is silent"), [S, Test](FAudioCtx& C)
	{
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		if (!Audio || S->Actors.Num() != 5)
		{
			Test->AddError(TEXT("Audio subsystem or the test actors are gone"));
			return true;
		}
		ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(C.W);
		if (C.Elapsed > 14.0)
		{
			Test->AddError(FString::Printf(TEXT("Timed out in phase %d"), S->Phase));
			return true;
		}
		auto NoBellSounds = [&](const TCHAR* When)
		{
			Test->TestEqual(FString::Printf(TEXT("%s: no small-bell strike"), When), Requests(Audio, LBAudioCue::SmallBellStrike).Num(), 0);
			Test->TestEqual(FString::Printf(TEXT("%s: no small-bell fail"), When), Requests(Audio, LBAudioCue::SmallBellFail).Num(), 0);
			Test->TestEqual(FString::Printf(TEXT("%s: no small-bell solved"), When), Requests(Audio, LBAudioCue::SmallBellSolved).Num(), 0);
		};
		switch (S->Phase)
		{
		case 0:
			if (!Audio->IsActive())
			{
				return false;
			}
			Audio->RefreshBindings();
			Test->TestTrue(TEXT("The four candles and the puzzle actor are bound"), Audio->GetBoundActorCount() >= 5);
			Audio->ClearRequests();
			// Candle 1 then candle 2, in order.
			State->AddState(LBPie::Tag(CandleTags[0]));
			State->AddState(LBPie::Tag(CandleTags[1]));
			S->Phase = 1;
			S->Counter = C.Frames;
			return false;
		case 1:
			if (C.Frames - S->Counter < 3)
			{
				return false;
			}
			NoBellSounds(TEXT("Two accepted candle steps"));
			Test->TestEqual(TEXT("Two accepted candle steps: no candle-out either"), Requests(Audio, LBAudioCue::CandleOut).Num(), 0);
			// Candle 4 out of turn (candle 3 is next): the puzzle fails on the next tick.
			State->AddState(LBPie::Tag(CandleTags[3]));
			S->Phase = 2;
			return false;
		case 2:
		{
			const TArray<FLBAudioRequest> Out = Requests(Audio, LBAudioCue::CandleOut);
			if (Out.IsEmpty())
			{
				return false;
			}
			if (Test->TestEqual(TEXT("A failed candle puzzle plays exactly one candle-out"), Out.Num(), 1))
			{
				Test->TestTrue(TEXT("It is positional, at the puzzle's actor"), Out[0].bPositional && Out[0].Location.Equals(S->Anchor, 1.0));
				Test->TestTrue(TEXT("A candle-out variant of the three was picked"), Out[0].Variant >= 0 && Out[0].Variant < 3);
			}
			NoBellSounds(TEXT("A failed candle puzzle"));
			Audio->ClearRequests();
			S->Phase = 3;
			S->Counter = C.Frames;
			return false;
		}
		case 3:
			// The puzzle removed the step tags; let it settle, then play the right order.
			if (C.Frames - S->Counter < 4)
			{
				return false;
			}
			for (const TCHAR* Name : CandleTags)
			{
				State->AddState(LBPie::Tag(Name));
			}
			S->Phase = 4;
			S->Counter = C.Frames;
			return false;
		default:
		{
			const AActor* Controller = S->Actors[4].Get();
			const ULBSequencePuzzleComponent* Puzzle = Controller ? Controller->FindComponentByClass<ULBSequencePuzzleComponent>() : nullptr;
			if (!Puzzle || !Puzzle->IsSolved() || C.Frames - S->Counter < 3)
			{
				return false;
			}
			NoBellSounds(TEXT("The solved candle puzzle"));
			Test->TestEqual(TEXT("The solved candle puzzle: no candle-out"), Requests(Audio, LBAudioCue::CandleOut).Num(), 0);
			return true;
		}
		}
	}, 60.f);

	AudioEnqueue(R);
	return true;
}

// =====================================================================================================================
// 11. Footsteps: no repeated variant, gait volumes, the surface rows
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioFootstepVariantTest, "LastBell.Functional.Audio.FootstepVariantNoRepeat", LB_AUDIOFUNC_FLAGS)
bool FLBAudioFootstepVariantTest::RunTest(const FString& Parameters)
{
	USoundBase* Ping = LoadObject<USoundBase>(nullptr, GPingPath);
	if (!TestNotNull(TEXT("The engine's ping sound loads"), Ping))
	{
		return true;
	}

	// A table with a Default row (4 variants, one null among them) and a Wood row (1 variant, a fallback sound).
	UDataTable* Table = NewObject<UDataTable>(GetTransientPackage());
	Table->RowStruct = FLBFootstepRow::StaticStruct();
	FLBFootstepRow Stone;
	Stone.SurfaceType = SurfaceType_Default;
	Stone.Variants = { Ping, Ping, nullptr, Ping, Ping };
	Stone.Sound = nullptr;
	Table->AddRow(TEXT("Default"), Stone);
	FLBFootstepRow Wood;
	Wood.SurfaceType = SurfaceType2;
	Wood.Variants = { Ping };
	Table->AddRow(TEXT("Wood"), Wood);
	FLBFootstepRow Earth;
	Earth.SurfaceType = SurfaceType3;
	Earth.Sound = Ping;
	Table->AddRow(TEXT("Earth"), Earth);

	ULBFootstepComponent* Steps = NewObject<ULBFootstepComponent>(GetTransientPackage());
	Steps->FootstepTable = Table;

	const FLBFootstepRow* Default = Steps->FindRow(SurfaceType_Default);
	const FLBFootstepRow* Grass = Steps->FindRow(SurfaceType4);
	TestNotNull(TEXT("The Default row is found"), Default);
	TestTrue(TEXT("A surface with no row falls back to the Default row"), Grass == Default);
	const FLBFootstepRow* WoodRow = Steps->FindRow(SurfaceType2);
	TestTrue(TEXT("Wood finds its own row"), WoodRow && WoodRow != Default && WoodRow->SurfaceType == SurfaceType2);
	if (!Default || !WoodRow)
	{
		return true;
	}

	// Four valid variants: 1000 picks, never the same one twice in a row, every one used, no null returned.
	int32 Last = INDEX_NONE;
	int32 Repeats = 0;
	int32 Nulls = 0;
	TSet<int32> Seen;
	for (int32 Step = 0; Step < 1000; ++Step)
	{
		int32 Variant = INDEX_NONE;
		const USoundBase* Sound = Steps->PickStepSound(*Default, Variant);
		Nulls += Sound == nullptr ? 1 : 0;
		Repeats += Variant == Last ? 1 : 0;
		Last = Variant;
		Seen.Add(Variant);
		if (Variant == 2)
		{
			AddError(TEXT("The null variant (index 2) was picked"));
			break;
		}
	}
	TestEqual(TEXT("1000 steps: no sound is null"), Nulls, 0);
	TestEqual(TEXT("1000 steps: the same variant never twice in a row"), Repeats, 0);
	TestEqual(TEXT("1000 steps: all four valid variants are used"), Seen.Num(), 4);

	// A row with one variant plays it every time (a repeat is allowed when there is no other).
	int32 Variant = INDEX_NONE;
	TestTrue(TEXT("One variant: it is returned"), Steps->PickStepSound(*WoodRow, Variant) == Ping && Variant == 0);
	TestTrue(TEXT("One variant: it is returned again"), Steps->PickStepSound(*WoodRow, Variant) == Ping && Variant == 0);

	// No variants: the fallback sound, variant INDEX_NONE.
	const FLBFootstepRow* EarthRow = Steps->FindRow(SurfaceType3);
	TestTrue(TEXT("No variants: the fallback Sound is used"), EarthRow && Steps->PickStepSound(*EarthRow, Variant) == Ping && Variant == INDEX_NONE);

	// The gait multipliers: crouch 0.5, sprint 1.25, others 1.
	FLBFootstepRow Gaits;
	TestNearlyEqual(TEXT("Crouch volume defaults to 0.5"), ULBFootstepComponent::GaitVolume(Gaits, ELBGait::Crouch), 0.5f, 1.0e-6f);
	TestNearlyEqual(TEXT("Sprint volume defaults to 1.25"), ULBFootstepComponent::GaitVolume(Gaits, ELBGait::Sprint), 1.25f, 1.0e-6f);
	TestNearlyEqual(TEXT("Walking is 1"), ULBFootstepComponent::GaitVolume(Gaits, ELBGait::Walk), 1.f, 1.0e-6f);
	Gaits.CrouchVolume = 0.2f;
	TestNearlyEqual(TEXT("The row's own crouch volume is used"), ULBFootstepComponent::GaitVolume(Gaits, ELBGait::Crouch), 0.2f, 1.0e-6f);
	return true;
}

// =====================================================================================================================
// 12. User volumes
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioUserVolumesTest, "LastBell.Functional.Audio.UserVolumesApplied", LB_AUDIOFUNC_FLAGS)
bool FLBAudioUserVolumesTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready; a SoundMix and the five classes from the engine's content are set as the user mix"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ActivateAudio(C, *S, Test, [](ULBAudioSettings& A)
		{
			A.UserMix = TSoftObjectPtr<USoundMix>(FSoftObjectPath(TEXT("/Engine/EngineSounds/Duck_Normal_Attack_MixMod.Duck_Normal_Attack_MixMod")));
			A.UserClasses.Add(FName(TEXT("Master")), TSoftObjectPtr<USoundClass>(FSoftObjectPath(TEXT("/Engine/EngineSounds/Master.Master"))));
			A.UserClasses.Add(FName(TEXT("SFX")), TSoftObjectPtr<USoundClass>(FSoftObjectPath(TEXT("/Engine/EngineSounds/SFX.SFX"))));
			A.UserClasses.Add(FName(TEXT("Music")), TSoftObjectPtr<USoundClass>(FSoftObjectPath(TEXT("/Engine/EngineSounds/Music.Music"))));
			A.UserClasses.Add(FName(TEXT("Voice")), TSoftObjectPtr<USoundClass>(FSoftObjectPath(TEXT("/Engine/EngineSounds/Voice.Voice"))));
		});
		return true;
	});

	R->Add(TEXT("The volumes are pushed at activation and follow the user settings; out-of-range values are clamped"), [S, Test](FAudioCtx& C)
	{
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		if (!Audio)
		{
			Test->AddError(TEXT("Audio subsystem is gone"));
			return true;
		}
		if (!Audio->IsActive())
		{
			if (C.Elapsed > 3.0)
			{
				Test->AddError(TEXT("The director did not become active within 3 s"));
				return true;
			}
			return false;
		}
		ULBUserSettings* User = ULBUserSettings::GetUserSettings();
		for (int32 Index = 0; Index < 6; ++Index)
		{
			Test->TestNearlyEqual(FString::Printf(TEXT("Group %d starts at the user setting"), Index), Audio->GetAppliedVolume(static_cast<ELBAudioVolumeGroup>(Index)),
				User->GetVolume(static_cast<ELBAudioVolumeGroup>(Index)), 1.0e-5f);
		}
		User->SetVolumeTransient(ELBAudioVolumeGroup::SFX, 0.4f);
		Test->TestNearlyEqual(TEXT("SFX 0.4 is pushed"), Audio->GetAppliedVolume(ELBAudioVolumeGroup::SFX), 0.4f, 1.0e-5f);
		User->SetVolumeTransient(ELBAudioVolumeGroup::Master, 0.7f);
		Test->TestNearlyEqual(TEXT("Master 0.7 is pushed"), Audio->GetAppliedVolume(ELBAudioVolumeGroup::Master), 0.7f, 1.0e-5f);
		Test->TestNearlyEqual(TEXT("SFX is unchanged by the master"), Audio->GetAppliedVolume(ELBAudioVolumeGroup::SFX), 0.4f, 1.0e-5f);
		User->SetVolumeTransient(ELBAudioVolumeGroup::Music, 3.f);
		Test->TestNearlyEqual(TEXT("Above 1 is clamped to 1"), Audio->GetAppliedVolume(ELBAudioVolumeGroup::Music), 1.f, 1.0e-5f);
		User->SetVolumeTransient(ELBAudioVolumeGroup::UI, -2.f);
		Test->TestNearlyEqual(TEXT("Below 0 is clamped to 0"), Audio->GetAppliedVolume(ELBAudioVolumeGroup::UI), 0.f, 1.0e-5f);
		Test->TestNearlyEqual(TEXT("The setting reads back clamped"), User->GetVolume(ELBAudioVolumeGroup::UI), 0.f, 1.0e-5f);
		Test->TestNearlyEqual(TEXT("The new groups default to 1 (Voice here)"), User->GetVolume(ELBAudioVolumeGroup::Voice), 1.f, 1.0e-5f);
		// The explicit call pushes again.
		User->SetVolumeTransient(ELBAudioVolumeGroup::Ambience, 0.25f);
		Audio->ApplyUserVolumes();
		Test->TestNearlyEqual(TEXT("Ambience 0.25 is pushed"), Audio->GetAppliedVolume(ELBAudioVolumeGroup::Ambience), 0.25f, 1.0e-5f);
		return true;
	}, 60.f);

	AudioEnqueue(R);
	return true;
}

// =====================================================================================================================
// 13. The Warden's tells
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioWardenTellsTest, "LastBell.Functional.Audio.WardenTells", LB_AUDIOFUNC_FLAGS)
bool FLBAudioWardenTellsTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, storm and director active"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ActivateAudio(C, *S, Test);
		return true;
	});

	R->Add(TEXT("A Warden on stage: the brain's events give the tells and the stings; off stage they give none"), [S, Test](FAudioCtx& C)
	{
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		if (!Audio)
		{
			Test->AddError(TEXT("Audio subsystem is gone"));
			return true;
		}
		ALBWarden* Warden = nullptr;
		for (TActorIterator<ALBWarden> It(C.W); It; ++It)
		{
			Warden = *It;
			break;
		}
		ULBWardenBrainComponent* Brain = Warden ? Warden->GetBrain() : nullptr;
		ULBWardenAudioComponent* WardenAudio = Warden ? Warden->FindComponentByClass<ULBWardenAudioComponent>() : nullptr;
		if (!Test->TestNotNull(TEXT("L_Test_Warden has an ALBWarden"), Warden) || !Test->TestNotNull(TEXT("The Warden has a brain on its controller"), Brain)
			|| !Test->TestNotNull(TEXT("ALBWarden creates a ULBWardenAudioComponent"), WardenAudio))
		{
			return true;
		}
		if (C.Elapsed > 14.0)
		{
			Test->AddError(FString::Printf(TEXT("Timed out in phase %d"), S->Phase));
			return true;
		}
		switch (S->Phase)
		{
		case 0:
			// The subsystem finds the Warden and binds its brain within a second of activation.
			if (!Audio->IsActive() || C.Elapsed < 1.3)
			{
				return false;
			}
			Test->TestFalse(TEXT("Dormant: the component is silent"), WardenAudio->IsAudioActive());
			Audio->ClearRequests();
			Brain->OnPlayerSpotted.Broadcast();
			Test->TestEqual(TEXT("Off stage: no spotted tell"), Requests(Audio, LBAudioCue::WardenSpotted).Num(), 0);
			Test->TestEqual(TEXT("...but the stinger still plays (the player is spotted)"), Requests(Audio, LBAudioCue::StingSpotted).Num(), 1);
			Warden->SetDormantPresentation(false);
			Audio->ClearRequests();
			S->Phase = 1;
			S->Counter = C.Frames;
			return false;
		case 1:
		{
			if (C.Frames - S->Counter < 5)
			{
				return false;
			}
			Test->TestTrue(TEXT("On stage: the component is active"), WardenAudio->IsAudioActive());
			Test->TestTrue(FString::Printf(TEXT("The slow breath loop eases in (%.2f)"), WardenAudio->GetBreathLevel(0)), WardenAudio->GetBreathLevel(0) > 0.f);
			Test->TestNearlyEqual(TEXT("The fast breath loop is off"), WardenAudio->GetBreathLevel(1), 0.f, 1.0e-4f);
			Test->TestEqual(TEXT("The slow breath loop started"), Requests(Audio, LBAudioCue::LoopWardenBreath).Num(), 1);

			Brain->OnPlayerSpotted.Broadcast();
			const TArray<FLBAudioRequest> Spotted = Requests(Audio, LBAudioCue::WardenSpotted);
			if (Test->TestEqual(TEXT("Spotted: one tell"), Spotted.Num(), 1))
			{
				Test->TestTrue(TEXT("It follows the Warden (attached) and loaded"), Spotted[0].bPositional && Spotted[0].bSoundResolved && Spotted[0].Variant >= 0 && Spotted[0].Variant < 3);
				Test->TestTrue(TEXT("It is at the Warden"), Spotted[0].Location.Equals(Warden->GetRootComponent()->GetComponentLocation(), 1.0));
			}
			Test->TestEqual(TEXT("Spotted: the stinger"), Requests(Audio, LBAudioCue::StingSpotted).Num(), 1);

			Brain->OnStateChanged.Broadcast(ELBWardenState::Suspicious, ELBWardenState::Chase);
			Test->TestEqual(TEXT("Entering Chase: a roar"), Requests(Audio, LBAudioCue::WardenRoar).Num(), 1);
			Brain->OnStateChanged.Broadcast(ELBWardenState::Chase, ELBWardenState::Search);
			Test->TestEqual(TEXT("Leaving Chase: no second roar"), Requests(Audio, LBAudioCue::WardenRoar).Num(), 1);
			Brain->OnAttackWindup.Broadcast(0.6f);
			Test->TestEqual(TEXT("Attack wind-up: a wind-up vocal"), Requests(Audio, LBAudioCue::WardenWindup).Num(), 1);
			Brain->OnPlayerLost.Broadcast();
			Test->TestEqual(TEXT("Sight lost: an exhale"), Requests(Audio, LBAudioCue::WardenExhale).Num(), 1);
			Brain->OnPlayerCaught.Broadcast();
			Test->TestEqual(TEXT("Caught: a vocal"), Requests(Audio, LBAudioCue::WardenCaught).Num(), 1);
			Test->TestEqual(TEXT("Caught: the stinger"), Requests(Audio, LBAudioCue::StingCaught).Num(), 1);

			// No repeats across spotted tells (three variants): 21 so far.
			for (int32 Index = 0; Index < 20; ++Index)
			{
				Brain->OnPlayerSpotted.Broadcast();
			}
			int32 Last = INDEX_NONE;
			int32 Repeats = 0;
			for (const FLBAudioRequest& Request : Requests(Audio, LBAudioCue::WardenSpotted))
			{
				Repeats += Request.Variant == Last ? 1 : 0;
				Last = Request.Variant;
			}
			Test->TestEqual(TEXT("21 spotted tells: none repeats the variant before it"), Repeats, 0);

			// Hidden again: silent.
			Warden->SetDormantPresentation(true);
			Audio->ClearRequests();
			Brain->OnPlayerSpotted.Broadcast();
			Test->TestEqual(TEXT("Dormant again: no spotted tell"), Requests(Audio, LBAudioCue::WardenSpotted).Num(), 0);
			return true;
		}
		default:
			return true;
		}
	}, 60.f);

	AudioEnqueue(R);
	return true;
}

// =====================================================================================================================
// 14. The apparition's sting
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioApparitionStingTest, "LastBell.Functional.Audio.ApparitionSting", LB_AUDIOFUNC_FLAGS)
bool FLBAudioApparitionStingTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, storm and director active, an apparition actor"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		if (!ActivateAudio(C, *S, Test))
		{
			return true;
		}
		const ALBCharacter* Pawn = LBPie::Pawn();
		S->Anchor = (Pawn ? Pawn->GetActorLocation() : FVector::ZeroVector) + FVector(900.0, 300.0, 0.0);
		ALBWardenApparition* Apparition = C.W->SpawnActor<ALBWardenApparition>(S->Anchor, FRotator::ZeroRotator);
		Test->TestNotNull(TEXT("The apparition spawned"), Apparition);
		S->Actors.Add(Apparition);
		return true;
	});

	R->Add(TEXT("OnAppeared gives the sting, the whisper and a chain at the figure"), [S, Test](FAudioCtx& C)
	{
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		ALBWardenApparition* Apparition = S->Actors.IsEmpty() ? nullptr : Cast<ALBWardenApparition>(S->Actors[0].Get());
		if (!Audio || !Apparition)
		{
			Test->AddError(TEXT("Audio subsystem or the apparition is gone"));
			return true;
		}
		if (!Audio->IsActive())
		{
			if (C.Elapsed > 3.0)
			{
				Test->AddError(TEXT("The director did not become active within 3 s"));
				return true;
			}
			return false;
		}
		Audio->RefreshBindings();
		Audio->ClearRequests();
		Apparition->OnAppeared.Broadcast(Apparition, 0);
		Test->TestEqual(TEXT("The apparition sting"), Requests(Audio, LBAudioCue::StingApparition).Num(), 1);
		const TArray<FLBAudioRequest> Whisper = Requests(Audio, LBAudioCue::ApparitionWhisper);
		if (Test->TestEqual(TEXT("One whisper"), Whisper.Num(), 1))
		{
			Test->TestTrue(TEXT("The whisper is at the apparition"), Whisper[0].bPositional && Whisper[0].Location.Equals(S->Anchor, 1.0));
		}
		const TArray<FLBAudioRequest> Chain = Requests(Audio, LBAudioCue::ApparitionChain);
		if (Test->TestEqual(TEXT("One chain"), Chain.Num(), 1))
		{
			Test->TestTrue(TEXT("The chain is at the apparition"), Chain[0].Location.Equals(S->Anchor, 1.0));
		}
		return true;
	}, 60.f);

	AudioEnqueue(R);
	return true;
}

// =====================================================================================================================
// 15. Zones: the highest priority wins; the room tone crossfades in; the roof rain follows the zone
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioZoneSelectionTest, "LastBell.Functional.Audio.ZoneSelection", LB_AUDIOFUNC_FLAGS)
bool FLBAudioZoneSelectionTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, storm and director active, two overlapping zones around the player"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		if (!ActivateAudio(C, *S, Test))
		{
			return true;
		}
		const ALBCharacter* Pawn = LBPie::Pawn();
		const FVector Centre = Pawn ? Pawn->GetActorLocation() : FVector::ZeroVector;
		ALBAudioZone* Low = C.W->SpawnActor<ALBAudioZone>(Centre, FRotator::ZeroRotator);
		ALBAudioZone* High = C.W->SpawnActor<ALBAudioZone>(Centre, FRotator::ZeroRotator);
		if (!Test->TestTrue(TEXT("The zones spawned"), Low && High))
		{
			return true;
		}
		Low->ZoneName = TEXT("Low");
		Low->Priority = 1;
		Low->RoomTone = Ping();
		Low->RoomToneVolume = 0.3f;
		Low->Darkness = 0.2f;
		High->ZoneName = TEXT("High");
		High->Priority = 5;
		High->RoomTone = Ping();
		High->RoomToneVolume = 0.6f;
		High->Darkness = 1.f;
		S->Actors.Add(Low);
		S->Actors.Add(High);
		// Spawned after BeginPlay: they do begin play on spawn in a running world and register themselves.
		return true;
	});

	R->Add(TEXT("The higher priority wins, its room tone fades in over 2 s, and leaving the zones fades it out"), [S, Test](FAudioCtx& C)
	{
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		if (!Audio || S->Actors.Num() != 2)
		{
			Test->AddError(TEXT("Audio subsystem or the zones are gone"));
			return true;
		}
		if (C.Elapsed > 14.0)
		{
			Test->AddError(FString::Printf(TEXT("Timed out in phase %d"), S->Phase));
			return true;
		}
		const float RoomLevel = Audio->GetLayerLevel(ELBAudioLayer::RoomA) + Audio->GetLayerLevel(ELBAudioLayer::RoomB);
		switch (S->Phase)
		{
		case 0:
			if (!Audio->IsActive() || C.Elapsed < 0.8)
			{
				return false;
			}
			if (Test->TestNotNull(TEXT("The player is in a zone"), Audio->GetCurrentZone()))
			{
				Test->TestEqual(TEXT("The priority-5 zone wins"), Audio->GetCurrentZone()->ZoneName, FName(TEXT("High")));
			}
			Test->TestEqual(TEXT("The room tone started"), Requests(Audio, LBAudioCue::LoopRoomTone).Num(), 1);
			S->T0 = C.Now;
			S->Phase = 1;
			return false;
		case 1:
			if (C.Now - S->T0 < 2.4)
			{
				return false;
			}
			Test->TestNearlyEqual(TEXT("After the 2 s fade the room tone is at the zone's volume (0.6)"), RoomLevel, 0.6f, 0.03f);
			// Take the priority zone away: the lower one applies.
			if (S->Actors[1].IsValid())
			{
				S->Actors[1]->Destroy();
			}
			S->T0 = C.Now;
			S->Phase = 2;
			return false;
		case 2:
			if (C.Now - S->T0 < 0.6)
			{
				return false;
			}
			if (Test->TestNotNull(TEXT("The lower zone applies once the higher one is gone"), Audio->GetCurrentZone()))
			{
				Test->TestEqual(TEXT("It is the priority-1 zone"), Audio->GetCurrentZone()->ZoneName, FName(TEXT("Low")));
			}
			// Move the other zone far away: outdoors.
			if (S->Actors[0].IsValid())
			{
				S->Actors[0]->SetActorLocation(S->Actors[0]->GetActorLocation() + FVector(200000.0, 0.0, 0.0));
			}
			S->T0 = C.Now;
			S->Phase = 3;
			return false;
		default:
			if (C.Now - S->T0 < 3.0)
			{
				return false;
			}
			Test->TestNull(TEXT("Outdoors: no zone"), Audio->GetCurrentZone());
			Test->TestNearlyEqual(TEXT("Outdoors: the room tone has faded out"), RoomLevel, 0.f, 0.02f);
			return true;
		}
	}, 60.f);

	AudioEnqueue(R);
	return true;
}

// =====================================================================================================================
// 16. Ambient emitters: active only near the player, no repeated variant
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioAmbientEmitterTest, "LastBell.Functional.Audio.AmbientEmitter", LB_AUDIOFUNC_FLAGS)
bool FLBAudioAmbientEmitterTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, storm and director active, an emitter with three drips every 0.3 to 0.4 s"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		if (!ActivateAudio(C, *S, Test))
		{
			return true;
		}
		const ALBCharacter* Pawn = LBPie::Pawn();
		S->Anchor = (Pawn ? Pawn->GetActorLocation() : FVector::ZeroVector) + FVector(600.0, 0.0, 100.0);
		ALBAmbientEmitter* Emitter = C.W->SpawnActor<ALBAmbientEmitter>(S->Anchor, FRotator::ZeroRotator);
		if (!Test->TestNotNull(TEXT("The emitter spawned"), Emitter))
		{
			return true;
		}
		FillSet(Emitter->Variants, 3);
		Emitter->IntervalMin = 0.3f;
		Emitter->IntervalMax = 0.4f;
		Emitter->ActiveRadius = 3000.f;
		S->Actors.Add(Emitter);
		return true;
	});

	R->Add(TEXT("Near the player it drips without repeating a variant; far away it is silent"), [S, Test](FAudioCtx& C)
	{
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		ALBAmbientEmitter* Emitter = S->Actors.IsEmpty() ? nullptr : Cast<ALBAmbientEmitter>(S->Actors[0].Get());
		if (!Audio || !Emitter)
		{
			Test->AddError(TEXT("Audio subsystem or the emitter is gone"));
			return true;
		}
		if (C.Elapsed > 20.0)
		{
			Test->AddError(FString::Printf(TEXT("Timed out in phase %d"), S->Phase));
			return true;
		}
		switch (S->Phase)
		{
		case 0:
			if (!Audio->IsActive())
			{
				return false;
			}
			Audio->ClearRequests();
			S->T0 = C.Now;
			S->Phase = 1;
			return false;
		case 1:
		{
			if (C.Now - S->T0 < 4.0)
			{
				return false;
			}
			Test->TestTrue(TEXT("The emitter is active near the player"), Emitter->IsEmitterActive());
			const TArray<FLBAudioRequest> Drips = Requests(Audio, LBAudioCue::Emitter);
			Test->TestTrue(FString::Printf(TEXT("About 8 drips in 4 s (got %d)"), Drips.Num()), Drips.Num() >= 4 && Drips.Num() <= 14);
			int32 Repeats = 0;
			for (int32 Index = 1; Index < Drips.Num(); ++Index)
			{
				Repeats += Drips[Index].Variant == Drips[Index - 1].Variant ? 1 : 0;
				Test->TestTrue(TEXT("A drip is at the emitter"), Drips[Index].Location.Equals(S->Anchor, 1.0));
			}
			Test->TestEqual(TEXT("No variant twice in a row"), Repeats, 0);
			// Far away: out of range.
			Emitter->SetActorLocation(S->Anchor + FVector(100000.0, 0.0, 0.0));
			S->T0 = C.Now;
			S->Phase = 2;
			return false;
		}
		case 2:
			// Past one check (0.25 s) the emitter is idle; count from then on.
			if (C.Now - S->T0 < 0.8)
			{
				return false;
			}
			Test->TestFalse(TEXT("Out of range the emitter is inactive"), Emitter->IsEmitterActive());
			Audio->ClearRequests();
			S->T0 = C.Now;
			S->Phase = 3;
			return false;
		default:
			if (C.Now - S->T0 < 2.0)
			{
				return false;
			}
			Test->TestEqual(TEXT("Out of range: no drips"), Requests(Audio, LBAudioCue::Emitter).Num(), 0);
			return true;
		}
	}, 60.f);

	AudioEnqueue(R);
	return true;
}

// =====================================================================================================================
// 17. The real L_Monastery setup. EXPECTED TO FAIL until P16-2 (DA_Audio and the sounds) and P16-3 (the level work) are done.
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioMonasteryTest, "LastBell.Functional.Audio.Monastery.AudioSetup", LB_AUDIOFUNC_FLAGS)
bool FLBAudioMonasteryTest::RunTest(const FString& Parameters)
{
	if (!FPackageName::DoesPackageExist(GAudioMonasteryMap))
	{
		AddWarning(TEXT("L_Monastery does not exist: the audio setup check is skipped"));
		return true;
	}
	TSharedRef<FAudioRunner> R = AudioStartSession(this, GAudioMonasteryMap);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("L_Monastery: DA_Audio, its sounds, the interactable classes, the zones and volumes, the debug field, DT_Footsteps"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 10)
		{
			return false;
		}
		const ULBAudioSubsystem* Audio = S->Audio(C.W);
		if (!Test->TestNotNull(TEXT("The audio subsystem exists"), Audio))
		{
			return true;
		}

		// ---- DA_Audio ----
		const ULBGameSettings* GameSettings = ULBGameSettings::Get();
		Test->TestFalse(TEXT("ULBGameSettings::AudioSettings is linked (Config/DefaultGame.ini)"), GameSettings->AudioSettings.IsNull());
		const ULBAudioSettings* Settings = GameSettings->AudioSettings.IsNull() ? nullptr : GameSettings->AudioSettings.LoadSynchronous();
		// The rest of the DA_Audio checks need the asset; the zones, the volumes and DT_Footsteps below do not, so they still report.
		if (Test->TestNotNull(TEXT("DA_Audio exists and loads (P16-2 creates /Game/LastBell/Data/DA_Audio)"), Settings))
		{
			Test->TestTrue(TEXT("The audio director is active in L_Monastery (storm active and DA_Audio loaded)"), Audio->IsActive());
			Test->TestEqual(TEXT("DA_Audio.DebugForceMusicState is -1 (never saved otherwise)"), Settings->DebugForceMusicState, -1);

			// ---- Every sound loads ----
			TArray<ULBAudioSettings::FSoundEntry> Entries;
			Settings->CollectSounds(Entries);
			int32 Missing = 0;
			for (const ULBAudioSettings::FSoundEntry& Entry : Entries)
			{
				if (Entry.Ref.IsNull())
				{
					Test->AddError(FString::Printf(TEXT("DA_Audio.%s is not set"), *Entry.Name));
					++Missing;
				}
				else if (!Entry.Ref.LoadSynchronous())
				{
					Test->AddError(FString::Printf(TEXT("DA_Audio.%s (%s) does not load"), *Entry.Name, *Entry.Ref.ToString()));
					++Missing;
				}
			}
			Test->TestEqual(TEXT("Every soft sound reference in DA_Audio is set and loads"), Missing, 0);
			Test->TestFalse(TEXT("DA_Audio.UserMix is set"), Settings->UserMix.IsNull());
			for (const TCHAR* Group : { TEXT("Master"), TEXT("SFX"), TEXT("Ambience"), TEXT("Music"), TEXT("Voice"), TEXT("UI") })
			{
				const TSoftObjectPtr<USoundClass>* Class = Settings->UserClasses.Find(FName(Group));
				Test->TestTrue(FString::Printf(TEXT("DA_Audio.UserClasses has %s"), Group), Class && !Class->IsNull() && Class->LoadSynchronous());
			}
			Test->TestTrue(TEXT("DA_Audio.BellBeats has the six story beats"), Settings->BellBeats.Num() >= 6);
			Test->TestTrue(TEXT("DA_Audio.BellLocation is set (not the world origin)"), !Settings->BellLocation.IsNearlyZero(1.0));
		}

		// ---- Every interactable class is mapped or silent on purpose ----
		TSet<const UClass*> Checked;
		int32 Unmapped = 0;
		for (TActorIterator<AActor> It(C.W); It; ++It)
		{
			const AActor* Actor = *It;
			if (!Actor->FindComponentByClass<ULBInteractableComponent>() && !Actor->FindComponentByClass<ULBSequencePuzzleComponent>())
			{
				continue;
			}
			if (Checked.Contains(Actor->GetClass()))
			{
				continue;
			}
			Checked.Add(Actor->GetClass());
			bool bSilent = false;
			const int32 Row = Settings ? Settings->FindCueRow(Actor->GetClass(), bSilent) : INDEX_NONE;
			if (Row == INDEX_NONE && !bSilent)
			{
				Test->AddError(FString::Printf(TEXT("Interactable class %s (e.g. %s) is neither mapped in InteractionCues nor listed in SilentClasses"), *Actor->GetClass()->GetName(), *Actor->GetActorLabel()));
				++Unmapped;
			}
		}
		Test->TestTrue(FString::Printf(TEXT("L_Monastery has interactable classes (%d)"), Checked.Num()), Checked.Num() > 0);
		Test->TestEqual(TEXT("Every interactable class in L_Monastery is mapped or silent"), Unmapped, 0);

		// ---- Zones and audio volumes ----
		int32 Zones = 0;
		for (TActorIterator<ALBAudioZone> It(C.W); It; ++It)
		{
			++Zones;
		}
		int32 Volumes = 0;
		for (TActorIterator<AAudioVolume> It(C.W); It; ++It)
		{
			++Volumes;
		}
		Test->TestTrue(FString::Printf(TEXT("At least 6 ALBAudioZone actors (%d)"), Zones), Zones >= 6);
		Test->TestTrue(FString::Printf(TEXT("At least 6 AAudioVolume actors (%d)"), Volumes), Volumes >= 6);

		// ---- DT_Footsteps: a row per surface, each with at least 4 variants ----
		const UDataTable* Table = LoadObject<UDataTable>(nullptr, GFootstepTablePath);
		if (Test->TestNotNull(TEXT("DT_Footsteps loads"), Table))
		{
			TArray<FLBFootstepRow*> Rows;
			Table->GetAllRows<FLBFootstepRow>(TEXT("AudioSetup"), Rows);
			static const EPhysicalSurface Surfaces[6] = { SurfaceType1, SurfaceType2, SurfaceType3, SurfaceType4, SurfaceType5, SurfaceType6 };
			static const TCHAR* SurfaceNames[6] = { TEXT("Stone"), TEXT("Wood"), TEXT("Earth"), TEXT("Grass"), TEXT("Water"), TEXT("Metal") };
			for (int32 Index = 0; Index < 6; ++Index)
			{
				const FLBFootstepRow* Found = nullptr;
				for (const FLBFootstepRow* Row : Rows)
				{
					if (Row && Row->SurfaceType == Surfaces[Index])
					{
						Found = Row;
						break;
					}
				}
				if (!Test->TestNotNull(*FString::Printf(TEXT("DT_Footsteps has a %s row"), SurfaceNames[Index]), Found))
				{
					continue;
				}
				int32 Valid = 0;
				for (const USoundBase* Variant : Found->Variants)
				{
					Valid += Variant ? 1 : 0;
				}
				Test->TestTrue(FString::Printf(TEXT("The %s row has at least 4 variants (%d)"), SurfaceNames[Index], Valid), Valid >= 4);
			}
		}
		return true;
	}, 90.f);

	AudioEnqueue(R);
	return true;
}

// =====================================================================================================================
// P17: the Arrival beat and the great-bell strike delegate
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioArrivalBeatTest, "LastBell.Functional.Audio.ArrivalBeat", LB_AUDIOFUNC_FLAGS)
bool FLBAudioArrivalBeatTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, storm and director active"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ActivateAudio(C, *S, Test);
		return true;
	});

	R->Add(TEXT("State.Event.Arrival: stage 1 x 3, the first strike at once, the others follow"), [S, Test](FAudioCtx& C)
	{
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		if (!Audio)
		{
			Test->AddError(TEXT("Audio subsystem is gone"));
			return true;
		}
		if (C.Elapsed > 10.0)
		{
			Test->AddError(FString::Printf(TEXT("Timed out in phase %d"), S->Phase));
			return true;
		}
		if (S->Phase == 0)
		{
			if (!Audio->IsActive() || C.Frames < 4)
			{
				return false;
			}
			Audio->ClearRequests();
			S->T0 = C.Now;
			ULBWorldStateSubsystem::Get(C.W)->AddState(AudioTag(TEXT("State.Event.Arrival")));
			const TArray<FLBAudioRequest> Immediate = Requests(Audio, LBAudioCue::Bell);
			if (Test->TestEqual(TEXT("One strike was requested before AddState returned"), Immediate.Num(), 1))
			{
				Test->TestEqual(TEXT("It is stage 1"), Immediate[0].Aux, 1);
				Test->TestEqual(TEXT("It plays Bell.Stage[0]"), Immediate[0].Variant, 0);
			}
			// Two more bell strikes and Drone A (the beat's drone, scheduled at once).
			Test->TestEqual(TEXT("The other two strikes and the drone are scheduled"), Audio->GetScheduledCount(), 3);
			S->Phase = 1;
			return false;
		}
		if (C.Now - S->T0 < 1.5)
		{
			return false;
		}
		const TArray<FLBAudioRequest> Bells = Requests(Audio, LBAudioCue::Bell);
		if (Test->TestEqual(TEXT("Three strikes in all"), Bells.Num(), 3))
		{
			for (const FLBAudioRequest& Bell : Bells)
			{
				Test->TestEqual(TEXT("Every strike is stage 1"), Bell.Aux, 1);
			}
		}
		Test->TestEqual(TEXT("The bell stage stays 1"), Audio->GetBellStage(), 1);
		return true;
	}, 60.f);

	AudioEnqueue(R);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBAudioGreatBellStrikeDelegateTest, "LastBell.Functional.Audio.GreatBellStrikeDelegate", LB_AUDIOFUNC_FLAGS)
bool FLBAudioGreatBellStrikeDelegateTest::RunTest(const FString& Parameters)
{
	TSharedRef<FAudioRunner> R = AudioStartSession(this);
	const TSharedRef<FAudioState> S = R->S;
	FAutomationTestBase* Test = this;
	// The strikes the delegate announced: stage and the world time it came at.
	const TSharedRef<TArray<TPair<int32, double>>> Heard = MakeShared<TArray<TPair<int32, double>>>();

	R->Add(TEXT("PIE ready, storm and director active"), [S, Test](FAudioCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ActivateAudio(C, *S, Test);
		return true;
	});

	R->Add(TEXT("PlayBell(3, 2) announces two stage-3 strikes, exactly when each is requested"), [S, Test, Heard](FAudioCtx& C)
	{
		ULBAudioSubsystem* Audio = S->Audio(C.W);
		if (!Audio)
		{
			Test->AddError(TEXT("Audio subsystem is gone"));
			return true;
		}
		if (C.Elapsed > 10.0)
		{
			Test->AddError(FString::Printf(TEXT("Timed out in phase %d"), S->Phase));
			return true;
		}
		if (S->Phase == 0)
		{
			if (!Audio->IsActive() || C.Frames < 4)
			{
				return false;
			}
			Audio->ClearRequests();
			UWorld* World = C.W;
			Audio->OnGreatBellStrike.AddLambda([Heard, World](int32 Stage, float Volume)
			{
				Heard->Add({ Stage, World->GetTimeSeconds() });
			});
			S->T0 = C.Now;
			Audio->PlayBell(3, 2);
			S->Phase = 1;
			return false;
		}
		// PlayBellSpacing is 4.5 s in the transient settings.
		if (C.Now - S->T0 < 5.0)
		{
			return false;
		}
		const TArray<FLBAudioRequest> Bells = Requests(Audio, LBAudioCue::Bell);
		if (Test->TestEqual(TEXT("Two strikes were played"), Bells.Num(), 2) && Test->TestEqual(TEXT("...and announced"), Heard->Num(), 2))
		{
			for (int32 Index = 0; Index < 2; ++Index)
			{
				Test->TestEqual(TEXT("The announced stage is 3"), (*Heard)[Index].Key, 3);
				Test->TestNearlyEqual(TEXT("It comes at the moment the strike plays"), static_cast<float>((*Heard)[Index].Value - Bells[Index].Time), 0.f, 0.05f);
			}
		}
		return true;
	}, 60.f);

	AudioEnqueue(R);
	return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
