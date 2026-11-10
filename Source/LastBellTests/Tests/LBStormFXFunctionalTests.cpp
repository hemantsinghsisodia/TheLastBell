#include "Tests/LBRouteBot.h"
#include "Tests/LBStormFXTestSink.h"
#include "Storm/LBStormSubsystem.h"

void ULBStormFXTestSink::Bind(ULBStormSubsystem* Storm, UWorld* InWorld)
{
	World = InWorld;
	if (Storm)
	{
		Storm->OnLightningFlash.AddDynamic(this, &ULBStormFXTestSink::HandleFlash);
		Storm->OnLightningStrike.AddDynamic(this, &ULBStormFXTestSink::HandleStrike);
	}
}

void ULBStormFXTestSink::HandleFlash(float Brightness, ELBFlashReason Reason)
{
	FFlashRecord Record;
	Record.Seq = NextSeq++;
	Record.Time = World.IsValid() ? World->GetTimeSeconds() : 0.0;
	Record.Brightness = Brightness;
	Record.Reason = Reason;
	Flashes.Add(Record);
}

void ULBStormFXTestSink::HandleStrike(const FLBLightningStrikeInfo& Info)
{
	FStrikeRecord Record;
	Record.Seq = NextSeq++;
	Record.Time = World.IsValid() ? World->GetTimeSeconds() : 0.0;
	Record.Info = Info;
	Strikes.Add(Record);
}

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Editor.h"
#include "EngineUtils.h"
#include "Tests/AutomationEditorCommon.h"
#include "Camera/PlayerCameraManager.h"
#include "Character/LBCharacter.h"
#include "Components/LightComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/App.h"
#include "Misc/PackageName.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Storm/LBLightningBolt.h"
#include "Storm/LBStormFXSettings.h"
#include "Storm/LBStormFXSubsystem.h"
#include "Storm/LBStormSettings.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "UObject/StrongObjectPtr.h"
#include "LBLog.h"

// P15-1 functional tests of the storm's particle FX (LastBell.Functional.StormFX.*). Like the P14 storm tests, tests 1 to 7 load
// /Game/LastBell/Maps/L_Test_Warden (one PIE session each), spawn their own tagged moon and use a transient ULBStormSettings (the plan's tag
// tables, seed 1401, ambient flashes off) and a transient ULBStormFXSettings, handed over through OverrideSettings + RefreshLinkedLights +
// Rearm. So none of them needs DA_StormSettings, DA_StormFX or the P15 Niagara assets: the rain uses the project's NS_LB_SmokeWisp and the
// bolt card is the engine's plane. lb.Warden.Enabled is 0 for the session, and lb.StormFX.Enabled is put back afterwards. The last test
// checks the real L_Monastery setup and is EXPECTED TO FAIL until P15-6 (the DA_StormFX asset and the level work) is done.

#define LB_FXFUNC_FLAGS (EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

namespace LBStormFXTest
{
	const TCHAR* GFXTestMap = TEXT("/Game/LastBell/Maps/L_Test_Warden");
	const TCHAR* GFXMonasteryMap = TEXT("/Game/LastBell/Maps/L_Monastery");
	const TCHAR* GFXRainTestSystem = TEXT("/Game/LastBell/FX/Niagara/NS_LB_SmokeWisp.NS_LB_SmokeWisp");
	const TCHAR* GFXBoltTestMesh = TEXT("/Engine/BasicShapes/Plane.Plane");
	const FName GFXTestTargetTag(TEXT("LB_TestStrikeTarget"));

	void FXNote(const FString& Text) { UE_LOG(LogLB, Display, TEXT("[StormFXTest] %s"), *Text); }

	struct FFXCtx
	{
		UWorld* W = nullptr;
		double Elapsed = 0.0; // game seconds since the step began
		double Now = 0.0;     // world time
		int32 Frames = 0;
	};

	struct FFXState
	{
		TStrongObjectPtr<ULBStormSettings> StormSettings;
		TStrongObjectPtr<ULBStormFXSettings> FXSettings;
		TStrongObjectPtr<ULBStormFXTestSink> Sink;
		TWeakObjectPtr<ADirectionalLight> Moon;
		TWeakObjectPtr<AStaticMeshActor> Target;
		FVector TargetLocation = FVector::ZeroVector;
		double T0 = 0.0;
		int32 Phase = 0;
		int32 Counter = 0;
		bool bSawPeak = false;

		ULBStormSubsystem* Storm(UWorld* W) const { return W ? W->GetSubsystem<ULBStormSubsystem>() : nullptr; }
		ULBStormFXSubsystem* FX(UWorld* W) const { return W ? W->GetSubsystem<ULBStormFXSubsystem>() : nullptr; }
	};

	/** Sets lb.StormFX.Enabled to 1 for the lifetime of the object and puts the previous value back afterwards. */
	class FFXEnabledGuard
	{
	public:
		FFXEnabledGuard()
		{
			if (IConsoleVariable* Var = Get())
			{
				Previous = Var->GetInt();
				Var->Set(1, ECVF_SetByCode);
			}
		}
		~FFXEnabledGuard()
		{
			if (IConsoleVariable* Var = Get())
			{
				Var->Set(Previous, ECVF_SetByCode);
			}
		}
		FFXEnabledGuard(const FFXEnabledGuard&) = delete;
		FFXEnabledGuard& operator=(const FFXEnabledGuard&) = delete;

		static IConsoleVariable* Get() { return IConsoleManager::Get().FindConsoleVariable(TEXT("lb.StormFX.Enabled")); }
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

	class FFXRunner : public IAutomationLatentCommand
	{
	public:
		using FStepFn = TFunction<bool(FFXCtx&)>;

		explicit FFXRunner(FAutomationTestBase* InTest)
			: S(MakeShared<FFXState>()), Test(InTest), WardenOff(false)
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
				FXNote(FString::Printf(TEXT("STEP %d begin: %s"), StepIndex + 1, *Step.Name));
			}

			FFXCtx Ctx;
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
				FXNote(FString::Printf(TEXT("STEP %d %s: %s"), StepIndex + 1, ErrCount() == ErrorsAtStart ? TEXT("PASS") : TEXT("FAIL"), *Step.Name));
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

		TSharedRef<FFXState> S;

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
		FFXEnabledGuard FXEnabled;
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

	TSharedRef<FFXRunner> FXStartSession(FAutomationTestBase* Test, const TCHAR* Map = nullptr)
	{
		TSharedRef<FFXRunner> Runner = MakeShared<FFXRunner>(Test);
		FAutomationEditorCommonUtils::LoadMap(Map ? Map : GFXTestMap);
		FRequestPlaySessionParams PlayParams;
		PlayParams.WorldType = EPlaySessionWorldType::PlayInEditor;
		GEditor->RequestPlaySession(PlayParams);
		return Runner;
	}

	void FXEnqueue(const TSharedRef<FFXRunner>& Runner)
	{
		FAutomationTestFramework::Get().EnqueueLatentCommand(Runner);
	}

	// ---- Scene helpers ---------------------------------------------------------------------------------------------------------

	FGameplayTag FXTag(const TCHAR* Name) { return LBPie::Tag(Name); }

	/** The player camera's location, or false when there is none. */
	bool FXCameraLocation(UWorld* W, FVector& Out)
	{
		const APlayerController* PC = W ? W->GetFirstPlayerController() : nullptr;
		const APlayerCameraManager* Camera = PC ? PC->PlayerCameraManager.Get() : nullptr;
		if (!Camera)
		{
			return false;
		}
		Out = Camera->GetCameraLocation();
		return true;
	}

	/** A transient storm-settings object (plan tag tables, seed 1401, no ambient flashes) and the FX settings the tests use. */
	void FXMakeSettings(FFXState& S)
	{
		S.StormSettings.Reset(NewObject<ULBStormSettings>(GetTransientPackage()));
		S.StormSettings->FillPlanTagDefaults();
		S.StormSettings->RandomSeed = 1401;
		S.StormSettings->bAmbientFlashes = false;

		S.FXSettings.Reset(NewObject<ULBStormFXSettings>(GetTransientPackage()));
		S.FXSettings->RainSystem = TSoftObjectPtr<UNiagaraSystem>(FSoftObjectPath(GFXRainTestSystem));
		S.FXSettings->BoltMesh = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(GFXBoltTestMesh));
		for (const ELBFlashReason Reason : { ELBFlashReason::Ambient, ELBFlashReason::Scripted, ELBFlashReason::WardenReveal, ELBFlashReason::Apparition, ELBFlashReason::Debug })
		{
			S.FXSettings->SkyBoltChance.Add(Reason, 1.f);
		}

		S.Sink.Reset(NewObject<ULBStormFXTestSink>());
	}

	/** Spawns the tagged moon, hands the settings over, activates the storm and arms the FX. Null (with an error) on failure. */
	ULBStormFXSubsystem* ActivateFX(FFXCtx& C, FFXState& S, FAutomationTestBase* Test)
	{
		FXMakeSettings(S);

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
		ULBStormFXSubsystem* FX = S.FX(C.W);
		if (!Test->TestNotNull(TEXT("Storm subsystem exists in a PIE world"), Storm) || !Test->TestNotNull(TEXT("Storm FX subsystem exists in a PIE world"), FX)
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
		FX->OverrideSettings(S.FXSettings.Get());
		FX->Rearm();
		return FX;
	}

	/** Waits for the FX to activate (a few frames). Returns true when they have; adds an error after 3 s. */
	bool FXIsUp(FFXCtx& C, FFXState& S, FAutomationTestBase* Test)
	{
		const ULBStormFXSubsystem* FX = S.FX(C.W);
		if (FX && FX->IsActive())
		{
			return true;
		}
		if (C.Elapsed > 3.0)
		{
			Test->AddError(TEXT("The storm FX did not become active within 3 s"));
			return true;
		}
		return false;
	}

	bool FXFlashEnded(const ULBStormSubsystem* Storm)
	{
		return Storm && !Storm->IsFlashBusy() && Storm->GetLightningFlash() < 0.01f;
	}
}

using namespace LBStormFXTest;

// =====================================================================================================================
// 1. The FX run while the storm does, and not otherwise
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormFXActivatesTest, "LastBell.Functional.StormFX.ActivatesWithStorm", LB_FXFUNC_FLAGS)
bool FLBStormFXActivatesTest::RunTest(const FString& Parameters)
{
	TSharedRef<FFXRunner> R = FXStartSession(this);
	const TSharedRef<FFXState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, no storm: the FX are inactive; then the storm is switched on"), [S, Test](FFXCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		const ULBStormFXSubsystem* FX = S->FX(C.W);
		if (!Test->TestNotNull(TEXT("Storm FX subsystem exists in a PIE world"), FX))
		{
			return true;
		}
		Test->TestFalse(TEXT("No tagged moon: the FX are inactive"), FX->IsActive());
		Test->TestNull(TEXT("No tagged moon: there is no rain component"), FX->GetRainComponent());
		ActivateFX(C, *S, Test);
		return true;
	});

	R->Add(TEXT("With the storm active the FX activate and the rain exists"), [S, Test](FFXCtx& C)
	{
		if (!FXIsUp(C, *S, Test))
		{
			return false;
		}
		const ULBStormFXSubsystem* FX = S->FX(C.W);
		Test->TestTrue(TEXT("The FX are active"), FX && FX->IsActive());
		if (const UNiagaraComponent* Rain = FX ? FX->GetRainComponent() : nullptr)
		{
			// Niagara never activates a component when the app cannot render (-nullrhi, the automation run): UNiagaraComponent::ActivateInternal returns early.
			if (FApp::CanEverRender())
			{
				Test->TestTrue(TEXT("The rain component is active"), Rain->IsActive());
			}
		}
		else
		{
			Test->AddError(TEXT("The rain component does not exist (does NS_LB_SmokeWisp load?)"));
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

	R->Add(TEXT("With the storm gone the FX switch off and the rain is destroyed"), [S, Test](FFXCtx& C)
	{
		const ULBStormFXSubsystem* FX = S->FX(C.W);
		if (FX && FX->IsActive())
		{
			if (C.Elapsed > 3.0)
			{
				Test->AddError(TEXT("The FX stayed active 3 s after the storm went inactive"));
				return true;
			}
			return false;
		}
		Test->TestNull(TEXT("The rain component is gone"), FX ? FX->GetRainComponent() : nullptr);
		Test->TestEqual(TEXT("No bolt is shown"), FX ? FX->GetShownBoltCount() : -1, 0);
		return true;
	});

	FXEnqueue(R);
	return true;
}

// =====================================================================================================================
// 2. The rain rides on the camera
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormFXRainFollowsCameraTest, "LastBell.Functional.StormFX.RainFollowsCamera", LB_FXFUNC_FLAGS)
bool FLBStormFXRainFollowsCameraTest::RunTest(const FString& Parameters)
{
	TSharedRef<FFXRunner> R = FXStartSession(this);
	const TSharedRef<FFXState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, storm and FX active"), [S, Test](FFXCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ActivateFX(C, *S, Test);
		return true;
	});

	R->Add(TEXT("The rain is on the camera; after the player moves it is on the camera again"), [S, Test](FFXCtx& C)
	{
		if (S->Phase == 0)
		{
			if (!FXIsUp(C, *S, Test))
			{
				return false;
			}
			S->Phase = 1;
			S->Counter = C.Frames;
			// Move the player far from where it stands.
			const ALBCharacter* Pawn = LBPie::Pawn();
			const FVector Moved = (Pawn ? Pawn->GetActorLocation() : FVector::ZeroVector) + FVector(1500.0, 700.0, 0.0);
			LBPie::Teleport(Moved, FRotator::ZeroRotator);
			return false;
		}
		if (C.Frames - S->Counter < 6)
		{
			return false;
		}
		const UNiagaraComponent* Rain = S->FX(C.W) ? S->FX(C.W)->GetRainComponent() : nullptr;
		FVector Camera;
		if (!Test->TestNotNull(TEXT("The rain component exists"), Rain) || !Test->TestTrue(TEXT("The player has a camera"), FXCameraLocation(C.W, Camera)))
		{
			return true;
		}
		const double Distance = FVector::Dist(Rain->GetComponentLocation(), Camera);
		FXNote(FString::Printf(TEXT("rain %s, camera %s, distance %.3f cm"), *Rain->GetComponentLocation().ToString(), *Camera.ToString(), Distance));
		Test->TestTrue(FString::Printf(TEXT("The rain component is within 1 cm of the camera (%.3f)"), Distance), Distance <= 1.0);
		return true;
	});

	FXEnqueue(R);
	return true;
}

// =====================================================================================================================
// 3. A scripted strike with a target draws a bolt to it
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormFXTargetedStrikeTest, "LastBell.Functional.StormFX.TargetedStrikeDrawsBoltToTarget", LB_FXFUNC_FLAGS)
bool FLBStormFXTargetedStrikeTest::RunTest(const FString& Parameters)
{
	TSharedRef<FFXRunner> R = FXStartSession(this);
	const TSharedRef<FFXState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, storm and FX active, a tagged target, then Ritual.1 is added"), [S, Test](FFXCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		if (!ActivateFX(C, *S, Test))
		{
			return true;
		}
		// The Ritual.1 strike (1.2 s, one flash, profile Double) gets a target tag.
		int32 Found = 0;
		for (FLBStormStrike& Strike : S->StormSettings->ScriptedStrikes)
		{
			if (Strike.TriggerTag == FXTag(TEXT("State.Ritual.1")))
			{
				Strike.StrikeTargetTag = GFXTestTargetTag;
				++Found;
			}
		}
		Test->TestEqual(TEXT("The plan tables have one Ritual.1 strike"), Found, 1);

		const ALBCharacter* Pawn = LBPie::Pawn();
		S->TargetLocation = (Pawn ? Pawn->GetActorLocation() : FVector::ZeroVector) + FVector(2500.0, 800.0, 2000.0);
		AStaticMeshActor* Target = C.W->SpawnActor<AStaticMeshActor>(S->TargetLocation, FRotator::ZeroRotator);
		if (!Test->TestNotNull(TEXT("The strike target spawned"), Target))
		{
			return true;
		}
		Target->SetMobility(EComponentMobility::Movable);
		Target->SetActorLocation(S->TargetLocation);
		Target->Tags.Add(GFXTestTargetTag);
		S->Target = Target;
		S->T0 = C.Now;
		ULBWorldStateSubsystem::Get(C.W)->AddState(FXTag(TEXT("State.Ritual.1")));
		return true;
	});

	R->Add(TEXT("The strike carries the target and a bolt hangs from the sky to it"), [S, Test](FFXCtx& C)
	{
		if (S->Sink->Strikes.IsEmpty())
		{
			if (C.Now - S->T0 > 4.0)
			{
				Test->AddError(TEXT("Adding State.Ritual.1 did not strike within 4 s"));
				return true;
			}
			return false;
		}
		Test->TestEqual(TEXT("One strike announced"), S->Sink->Strikes.Num(), 1);
		const FLBLightningStrikeInfo& Info = S->Sink->Strikes[0].Info;
		Test->TestTrue(TEXT("The strike has a target"), Info.bHasTarget);
		Test->TestTrue(FString::Printf(TEXT("The strike's target location is the target actor's (%s)"), *Info.TargetLocation.ToString()), Info.TargetLocation.Equals(S->TargetLocation, 1.0));
		Test->TestEqual(TEXT("Reason Scripted"), static_cast<int32>(Info.Reason), static_cast<int32>(ELBFlashReason::Scripted));
		Test->TestEqual(TEXT("Profile Double (the Ritual.1 strike's)"), static_cast<int32>(Info.Profile), static_cast<int32>(ELBFlashProfile::Double));

		FVector Camera;
		if (FXCameraLocation(C.W, Camera))
		{
			const FVector Expected = (S->TargetLocation - Camera).GetSafeNormal();
			Test->TestTrue(FString::Printf(TEXT("The flash direction points at the target (dot %.4f)"), FVector::DotProduct(Info.Direction, Expected)), FVector::DotProduct(Info.Direction, Expected) > 0.999);
		}

		const ULBStormFXSubsystem* FX = S->FX(C.W);
		const ALBLightningBolt* Bolt = FX ? FX->GetLatestBolt() : nullptr;
		if (Test->TestNotNull(TEXT("A bolt was placed"), Bolt))
		{
			Test->TestTrue(TEXT("The bolt is shown"), Bolt->IsBoltShown());
			const double Miss = FVector::Dist(Bolt->GetBoltBottom(), S->TargetLocation);
			FXNote(FString::Printf(TEXT("bolt bottom %s, target %s, miss %.3f cm"), *Bolt->GetBoltBottom().ToString(), *S->TargetLocation.ToString(), Miss));
			Test->TestTrue(FString::Printf(TEXT("The bottom of the bolt is within 5 cm of the target (%.3f)"), Miss), Miss <= 5.0);
			Test->TestTrue(TEXT("The bolt starts in the sky above the target"), Bolt->GetActorLocation().Z > S->TargetLocation.Z + 1000.0);
		}
		Test->TestEqual(TEXT("Exactly one bolt is shown"), FX ? FX->GetShownBoltCount() : -1, 1);
		return true;
	});

	FXEnqueue(R);
	return true;
}

// =====================================================================================================================
// 4. An ambient flash draws a sky bolt by chance
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormFXSkyBoltTest, "LastBell.Functional.StormFX.SkyBoltOnAmbientFlash", LB_FXFUNC_FLAGS)
bool FLBStormFXSkyBoltTest::RunTest(const FString& Parameters)
{
	TSharedRef<FFXRunner> R = FXStartSession(this);
	const TSharedRef<FFXState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, storm and FX active, chance 1, an Ambient flash"), [S, Test](FFXCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		if (!ActivateFX(C, *S, Test))
		{
			return true;
		}
		S->Phase = 0;
		return true;
	});

	R->Add(TEXT("Chance 1: the flash draws a sky bolt at SkyBoltDistance; then chance 0: it draws none"), [S, Test](FFXCtx& C)
	{
		ULBStormSubsystem* Storm = S->Storm(C.W);
		const ULBStormFXSubsystem* FX = S->FX(C.W);
		if (!Storm || !FX)
		{
			Test->AddError(TEXT("Storm or FX subsystem is gone"));
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
			if (!FX->IsActive())
			{
				return false;
			}
			Storm->RequestFlash(1.f, 0.f, ELBFlashReason::Ambient, ELBFlashProfile::Sheet);
			S->Phase = 1;
			return false;
		case 1:
		{
			if (S->Sink->Strikes.IsEmpty())
			{
				return false;
			}
			const FLBLightningStrikeInfo& Info = S->Sink->Strikes[0].Info;
			Test->TestFalse(TEXT("An ambient flash has no target"), Info.bHasTarget);
			Test->TestEqual(TEXT("Reason Ambient"), static_cast<int32>(Info.Reason), static_cast<int32>(ELBFlashReason::Ambient));
			const ALBLightningBolt* Bolt = FX->GetLatestBolt();
			if (Test->TestNotNull(TEXT("A sky bolt was placed"), Bolt))
			{
				Test->TestTrue(TEXT("The bolt is shown"), Bolt->IsBoltShown());
				FVector Camera;
				if (FXCameraLocation(C.W, Camera))
				{
					const FVector Top = Bolt->GetActorLocation();
					const double Horizontal = FVector::Dist2D(Top, Camera);
					FXNote(FString::Printf(TEXT("sky bolt top %s, camera %s, horizontal %.2f, height %.2f"), *Top.ToString(), *Camera.ToString(), Horizontal, Top.Z - Camera.Z));
					Test->TestTrue(FString::Printf(TEXT("The bolt is SkyBoltDistance away horizontally (%.2f)"), Horizontal), FMath::Abs(Horizontal - S->FXSettings->SkyBoltDistance) <= 5.0);
					Test->TestTrue(FString::Printf(TEXT("The bolt's top is SkyBoltTopHeight above the camera (%.2f)"), Top.Z - Camera.Z), FMath::Abs((Top.Z - Camera.Z) - S->FXSettings->SkyBoltTopHeight) <= 5.0);
				}
				const double Length = Bolt->GetActorScale3D().Z * 100.0;
				Test->TestTrue(FString::Printf(TEXT("The bolt's length is within SkyBoltLength (%.0f)"), Length), Length >= S->FXSettings->SkyBoltLength.X - 1.0 && Length <= S->FXSettings->SkyBoltLength.Y + 1.0);
				Test->TestTrue(TEXT("The atlas cell is in range"), Bolt->GetAtlasIndex() >= 0 && Bolt->GetAtlasIndex() < S->FXSettings->BoltAtlasCount);
			}
			Test->TestEqual(TEXT("Exactly one bolt is shown"), FX->GetShownBoltCount(), 1);
			S->Phase = 2;
			return false;
		}
		case 2:
			// Let the flash end, then ask for another with chance 0.
			if (!FXFlashEnded(Storm) || FX->GetShownBoltCount() != 0)
			{
				return false;
			}
			S->FXSettings->SkyBoltChance.Add(ELBFlashReason::Ambient, 0.f);
			Storm->RequestFlash(1.f, 0.f, ELBFlashReason::Ambient, ELBFlashProfile::Sheet);
			S->Phase = 3;
			return false;
		default:
			if (S->Sink->Strikes.Num() < 2)
			{
				return false;
			}
			Test->TestEqual(TEXT("Chance 0: no bolt for the second flash"), FX->GetShownBoltCount(), 0);
			return true;
		}
	}, 60.f);

	FXEnqueue(R);
	return true;
}

// =====================================================================================================================
// 5. A bolt is hidden when its flash ends, or after BoltMaxSeconds
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormFXBoltHidesTest, "LastBell.Functional.StormFX.BoltHidesAfterFlash", LB_FXFUNC_FLAGS)
bool FLBStormFXBoltHidesTest::RunTest(const FString& Parameters)
{
	TSharedRef<FFXRunner> R = FXStartSession(this);
	const TSharedRef<FFXState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, storm and FX active"), [S, Test](FFXCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ActivateFX(C, *S, Test);
		S->Phase = 0;
		return true;
	});

	R->Add(TEXT("A bolt stays through its flash and is hidden when it ends"), [S, Test](FFXCtx& C)
	{
		ULBStormSubsystem* Storm = S->Storm(C.W);
		const ULBStormFXSubsystem* FX = S->FX(C.W);
		if (!Storm || !FX)
		{
			Test->AddError(TEXT("Storm or FX subsystem is gone"));
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
			if (!FX->IsActive())
			{
				return false;
			}
			Storm->RequestFlash(1.f, 0.f, ELBFlashReason::Debug, ELBFlashProfile::Double);
			S->Phase = 1;
			return false;
		case 1:
			if (Storm->GetLightningFlash() >= 0.5f)
			{
				// At the peak the bolt is up.
				Test->TestEqual(TEXT("At the peak of the flash one bolt is shown"), FX->GetShownBoltCount(), 1);
				S->bSawPeak = true;
			}
			if (S->bSawPeak && FXFlashEnded(Storm))
			{
				S->Counter = C.Frames;
				S->Phase = 2;
			}
			return false;
		default:
			// The bolt goes within a couple of frames of the flash ending.
			if (C.Frames - S->Counter < 3)
			{
				return false;
			}
			Test->TestEqual(TEXT("After the flash ended no bolt is shown"), FX->GetShownBoltCount(), 0);
			if (const ALBLightningBolt* Bolt = FX->GetLatestBolt())
			{
				Test->TestFalse(TEXT("The bolt is hidden"), Bolt->IsBoltShown());
			}
			return true;
		}
	});

	R->Add(TEXT("With the flash held, a bolt is hidden after BoltMaxSeconds"), [S, Test](FFXCtx& C)
	{
		ULBStormSubsystem* Storm = S->Storm(C.W);
		const ULBStormFXSubsystem* FX = S->FX(C.W);
		if (!Storm || !FX)
		{
			Test->AddError(TEXT("Storm or FX subsystem is gone"));
			return true;
		}
		if (C.Elapsed > 20.0)
		{
			Test->AddError(FString::Printf(TEXT("Timed out in phase %d"), S->Phase));
			return true;
		}
		switch (S->Phase)
		{
		case 2:
			// The previous flash is over; hold the flash value so only the timeout can hide the next bolt.
			S->FXSettings->BoltMaxSeconds = 0.6f;
			Storm->SetConsoleFreeze(0.5f);
			Storm->RequestFlash(1.f, 0.f, ELBFlashReason::Debug, ELBFlashProfile::Sheet);
			S->Phase = 3;
			return false;
		case 3:
			if (FX->GetShownBoltCount() < 1)
			{
				return false;
			}
			S->T0 = C.Now;
			S->Phase = 4;
			return false;
		case 4:
			if (C.Now - S->T0 < 0.3)
			{
				return false;
			}
			Test->TestEqual(TEXT("Held at F 0.5: still shown after 0.3 s (BoltMaxSeconds 0.6)"), FX->GetShownBoltCount(), 1);
			S->Phase = 5;
			return false;
		default:
			if (C.Now - S->T0 < 1.0)
			{
				return false;
			}
			Test->TestEqual(TEXT("Held at F 0.5: hidden after BoltMaxSeconds"), FX->GetShownBoltCount(), 0);
			Storm->SetConsoleFreeze(-1.f);
			return true;
		}
	});

	FXEnqueue(R);
	return true;
}

// =====================================================================================================================
// 6. lb.StormFX.Enabled 0 switches the FX off, 1 back on
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormFXDisabledByCVarTest, "LastBell.Functional.StormFX.DisabledByCVar", LB_FXFUNC_FLAGS)
bool FLBStormFXDisabledByCVarTest::RunTest(const FString& Parameters)
{
	TSharedRef<FFXRunner> R = FXStartSession(this);
	const TSharedRef<FFXState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, storm and FX active"), [S, Test](FFXCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ActivateFX(C, *S, Test);
		return true;
	});

	R->Add(TEXT("The FX are up, then lb.StormFX.Enabled 0 removes the rain and draws no bolt"), [S, Test](FFXCtx& C)
	{
		ULBStormSubsystem* Storm = S->Storm(C.W);
		const ULBStormFXSubsystem* FX = S->FX(C.W);
		if (!Storm || !FX)
		{
			Test->AddError(TEXT("Storm or FX subsystem is gone"));
			return true;
		}
		if (C.Elapsed > 12.0)
		{
			Test->AddError(FString::Printf(TEXT("Timed out in phase %d"), S->Phase));
			FFXEnabledGuard::Set(1);
			return true;
		}
		switch (S->Phase)
		{
		case 0:
			if (!FX->IsActive())
			{
				return false;
			}
			Test->TestNotNull(TEXT("The rain exists while enabled"), FX->GetRainComponent());
			FFXEnabledGuard::Set(0);
			S->Counter = C.Frames;
			S->Phase = 1;
			return false;
		case 1:
			if (C.Frames - S->Counter < 3)
			{
				return false;
			}
			Test->TestFalse(TEXT("lb.StormFX.Enabled 0: the FX are inactive"), FX->IsActive());
			Test->TestNull(TEXT("lb.StormFX.Enabled 0: the rain component is gone"), FX->GetRainComponent());
			Test->TestTrue(TEXT("The storm itself still runs"), Storm->IsActive());
			Storm->RequestFlash(1.f, 0.f, ELBFlashReason::Debug, ELBFlashProfile::Sheet);
			S->Phase = 2;
			return false;
		case 2:
			if (S->Sink->Flashes.IsEmpty())
			{
				return false;
			}
			Test->TestEqual(TEXT("lb.StormFX.Enabled 0: the flash draws no bolt"), FX->GetShownBoltCount(), 0);
			Test->TestEqual(TEXT("lb.StormFX.Enabled 0: no strike was seen by the FX (the storm still announced it)"), S->Sink->Strikes.Num(), 1);
			// Back on at once, so a later failure cannot leave it off.
			FFXEnabledGuard::Set(1);
			S->Phase = 3;
			return false;
		default:
			if (!FX->IsActive())
			{
				return false;
			}
			Test->TestNotNull(TEXT("lb.StormFX.Enabled 1: the rain is back"), FX->GetRainComponent());
			return true;
		}
	}, 60.f);

	FXEnqueue(R);
	return true;
}

// =====================================================================================================================
// 7. OnLightningFlash and OnLightningStrike carry the same flash
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormFXStrikeInfoTest, "LastBell.Functional.StormFX.StrikeInfoMatchesFlash", LB_FXFUNC_FLAGS)
bool FLBStormFXStrikeInfoTest::RunTest(const FString& Parameters)
{
	TSharedRef<FFXRunner> R = FXStartSession(this);
	const TSharedRef<FFXState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, storm active, a flash of brightness 0.8 with profile Auto"), [S, Test](FFXCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		if (!ActivateFX(C, *S, Test))
		{
			return true;
		}
		S->StormSettings->bAmbientFlashes = false;
		S->T0 = C.Now;
		S->Storm(C.W)->RequestFlash(0.8f, 0.f, ELBFlashReason::WardenReveal, ELBFlashProfile::Auto);
		return true;
	});

	R->Add(TEXT("Both delegates fire together for the same flash"), [S, Test](FFXCtx& C)
	{
		if (S->Sink->Flashes.IsEmpty() || S->Sink->Strikes.IsEmpty())
		{
			if (C.Now - S->T0 > 3.0)
			{
				Test->AddError(TEXT("The requested flash did not announce both OnLightningFlash and OnLightningStrike within 3 s"));
				return true;
			}
			return false;
		}
		Test->TestEqual(TEXT("One OnLightningFlash"), S->Sink->Flashes.Num(), 1);
		Test->TestEqual(TEXT("One OnLightningStrike"), S->Sink->Strikes.Num(), 1);
		const ULBStormFXTestSink::FFlashRecord& Flash = S->Sink->Flashes[0];
		const ULBStormFXTestSink::FStrikeRecord& Strike = S->Sink->Strikes[0];
		Test->TestEqual(TEXT("Same brightness"), Strike.Info.Brightness, Flash.Brightness);
		Test->TestNearlyEqual(TEXT("The brightness is the requested 0.8"), Strike.Info.Brightness, 0.8f, 1.0e-5f);
		Test->TestEqual(TEXT("Same reason"), static_cast<int32>(Strike.Info.Reason), static_cast<int32>(Flash.Reason));
		Test->TestEqual(TEXT("The reason is WardenReveal"), static_cast<int32>(Strike.Info.Reason), static_cast<int32>(ELBFlashReason::WardenReveal));
		Test->TestEqual(TEXT("OnLightningStrike follows OnLightningFlash at once"), Strike.Seq, Flash.Seq + 1);
		Test->TestEqual(TEXT("Same world time"), Strike.Time, Flash.Time);
		Test->TestTrue(TEXT("The profile is resolved (never Auto)"), static_cast<uint8>(Strike.Info.Profile) < static_cast<uint8>(ELBFlashProfile::Auto));
		Test->TestFalse(TEXT("No target"), Strike.Info.bHasTarget);
		Test->TestNearlyEqual(TEXT("The direction is a unit vector"), static_cast<float>(Strike.Info.Direction.Size()), 1.f, 1.0e-3f);
		return true;
	});

	FXEnqueue(R);
	return true;
}

// =====================================================================================================================
// 8. The real L_Monastery setup. EXPECTED TO FAIL until P15-6 (DA_StormFX and the level work) is done.
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormFXMonasteryTest, "LastBell.Functional.StormFX.Monastery.FXSetup", LB_FXFUNC_FLAGS)
bool FLBStormFXMonasteryTest::RunTest(const FString& Parameters)
{
	if (!FPackageName::DoesPackageExist(GFXMonasteryMap))
	{
		AddWarning(TEXT("L_Monastery does not exist: the storm FX setup check is skipped"));
		return true;
	}
	TSharedRef<FFXRunner> R = FXStartSession(this, GFXMonasteryMap);
	const TSharedRef<FFXState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("L_Monastery: DA_StormFX, the tower strike target, both target strikes, the rain, the debug fields"), [S, Test](FFXCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 10)
		{
			return false;
		}
		const ULBStormSubsystem* Storm = S->Storm(C.W);
		const ULBStormFXSubsystem* FX = S->FX(C.W);
		if (!Test->TestNotNull(TEXT("The storm subsystem exists"), Storm) || !Test->TestNotNull(TEXT("The storm FX subsystem exists"), FX))
		{
			return true;
		}
		const ULBStormSettings* StormSettings = Storm->GetSettings();
		if (!Test->TestTrue(TEXT("The storm is active in L_Monastery (moon tagged and DA_StormSettings set)"), Storm->IsActive()) || !Test->TestNotNull(TEXT("The storm settings are loaded"), StormSettings))
		{
			return true;
		}

		// ---- DA_StormFX ----
		Test->TestFalse(TEXT("DA_StormSettings.FXSettings is linked (P15-6 sets it to DA_StormFX)"), StormSettings->FXSettings.IsNull());
		const ULBStormFXSettings* FXSettings = StormSettings->FXSettings.LoadSynchronous();
		if (Test->TestNotNull(TEXT("DA_StormFX loads"), FXSettings))
		{
			Test->TestEqual(TEXT("DA_StormFX.DebugBolt is -1 (never saved otherwise)"), FXSettings->DebugBolt, -1);
			Test->TestFalse(TEXT("DA_StormFX.RainSystem is set"), FXSettings->RainSystem.IsNull());
			Test->TestFalse(TEXT("DA_StormFX.BoltMesh is set"), FXSettings->BoltMesh.IsNull());
			Test->TestFalse(TEXT("DA_StormFX.BoltMaterial is set"), FXSettings->BoltMaterial.IsNull());
		}
		Test->TestNearlyEqual(TEXT("DA_StormSettings.DebugFreezeFlash is -1"), StormSettings->DebugFreezeFlash, -1.f, 1.0e-6f);
		Test->TestNearlyEqual(TEXT("DA_StormSettings.DebugIntensityOverride is -1"), StormSettings->DebugIntensityOverride, -1.f, 1.0e-6f);

		// ---- The strike target ----
		static const FName TowerTag(TEXT("LB_StrikeTarget_Tower"));
		int32 Labelled = 0;
		int32 Tagged = 0;
		int32 Both = 0;
		TMap<FName, int32> TagCounts;
		for (TActorIterator<AActor> It(C.W); It; ++It)
		{
			const AActor* Actor = *It;
			const bool bLabel = Actor->GetActorLabel() == TEXT("FX_StrikeTarget_Tower");
			const bool bTag = Actor->ActorHasTag(TowerTag);
			Labelled += bLabel ? 1 : 0;
			Tagged += bTag ? 1 : 0;
			Both += (bLabel && bTag) ? 1 : 0;
			for (const FLBStormStrike& Strike : StormSettings->ScriptedStrikes)
			{
				if (!Strike.StrikeTargetTag.IsNone() && Actor->ActorHasTag(Strike.StrikeTargetTag))
				{
					++TagCounts.FindOrAdd(Strike.StrikeTargetTag);
				}
			}
		}
		Test->TestEqual(TEXT("Exactly one actor labelled FX_StrikeTarget_Tower"), Labelled, 1);
		Test->TestEqual(TEXT("Exactly one actor tagged LB_StrikeTarget_Tower"), Tagged, 1);
		Test->TestEqual(TEXT("The labelled actor is the tagged one"), Both, 1);

		// ---- Both target strikes resolve ----
		int32 TargetStrikes = 0;
		for (const FLBStormStrike& Strike : StormSettings->ScriptedStrikes)
		{
			if (Strike.StrikeTargetTag.IsNone())
			{
				continue;
			}
			++TargetStrikes;
			Test->TestTrue(FString::Printf(TEXT("The strike for %s resolves: an actor carries '%s'"), *Strike.TriggerTag.ToString(), *Strike.StrikeTargetTag.ToString()), TagCounts.Contains(Strike.StrikeTargetTag));
		}
		Test->TestEqual(TEXT("Two strikes have a StrikeTargetTag (CourtyardEntered and TowerTop)"), TargetStrikes, 2);
		for (const TCHAR* TriggerName : { TEXT("State.Event.CourtyardEntered"), TEXT("State.Event.TowerTop") })
		{
			bool bFound = false;
			for (const FLBStormStrike& Strike : StormSettings->ScriptedStrikes)
			{
				bFound |= (Strike.TriggerTag == FXTag(TriggerName) && Strike.StrikeTargetTag == TowerTag);
			}
			Test->TestTrue(FString::Printf(TEXT("The %s strike targets LB_StrikeTarget_Tower"), TriggerName), bFound);
		}

		// ---- The rain ----
		Test->TestTrue(TEXT("The storm FX are active after BeginPlay"), FX->IsActive());
		Test->TestNotNull(TEXT("The rain component exists after BeginPlay"), FX->GetRainComponent());
		return true;
	}, 90.f);

	FXEnqueue(R);
	return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
