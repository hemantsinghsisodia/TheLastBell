#include "Tests/LBRouteBot.h"
#include "Tests/LBStormTestSink.h"
#include "Storm/LBStormSubsystem.h"

void ULBStormTestSink::Bind(ULBStormSubsystem* Storm, UWorld* InWorld)
{
	World = InWorld;
	if (Storm)
	{
		Storm->OnLightningFlash.AddDynamic(this, &ULBStormTestSink::HandleFlash);
	}
}

void ULBStormTestSink::HandleFlash(float Brightness, ELBFlashReason Reason)
{
	FRecord Record;
	Record.Time = World.IsValid() ? World->GetTimeSeconds() : 0.0;
	Record.Brightness = Brightness;
	Record.Reason = Reason;
	Flashes.Add(Record);
}

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Editor.h"
#include "EngineUtils.h"
#include "Tests/AutomationEditorCommon.h"
#include "AI/LBApparitionLogic.h"
#include "AI/LBWarden.h"
#include "AI/LBWardenApparition.h"
#include "Camera/PlayerCameraManager.h"
#include "Character/LBCharacter.h"
#include "Components/CapsuleComponent.h"
#include "Components/LightComponent.h"
#include "Components/MeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/PointLight.h"
#include "Engine/SpotLight.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialParameterCollection.h"
#include "Misc/PackageName.h"
#include "Storm/LBStateLightGroup.h"
#include "Storm/LBStormLogic.h"
#include "Storm/LBStormSettings.h"
#include "Storm/LBStormZone.h"
#include "Systems/LBGameSettings.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "UObject/StrongObjectPtr.h"
#include "LBLog.h"

// P14-1 functional tests of the storm (LastBell.Functional.Storm.*). Tests 1 to 7 load /Game/LastBell/Maps/L_Test_Warden (one PIE session
// each), spawn their own tagged lights and use a transient ULBStormSettings (the plan's tag tables, seed 1401, ambient flashes off unless
// a test needs them) handed over through OverrideSettings + RefreshLinkedLights, so none of them needs the DA_StormSettings or MPC_LB_Storm
// assets. lb.Warden.Enabled is 0 for the session (the map's Warden stays dormant and cannot touch the player). Test 8 checks the real
// L_Monastery setup and is EXPECTED TO FAIL until P14-2 (assets) and P14-3 (level work) are done.

#define FUNC_FLAGS (EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

namespace
{
	const TCHAR* GStormMap = TEXT("/Game/LastBell/Maps/L_Test_Warden");
	const TCHAR* GMonasteryMap = TEXT("/Game/LastBell/Maps/L_Monastery");
	const TCHAR* GTriggerTagName = TEXT("State.Test.Apparition");

	/** A floor far below anything in the map, as the apparition tests use. */
	constexpr float GFloorTopZ = -20000.f;

	void Note(const FString& Text) { UE_LOG(LogLB, Display, TEXT("[StormTest] %s"), *Text); }

	struct FStormCtx
	{
		UWorld* W = nullptr;
		ALBCharacter* Pawn = nullptr;
		double Elapsed = 0.0; // game seconds since the step began
		double Now = 0.0;     // world time
		int32 Frames = 0;
		bool bFirst = false;
	};

	struct FStormState
	{
		TStrongObjectPtr<ULBStormSettings> Settings;
		TStrongObjectPtr<ULBStormTestSink> Sink;
		TWeakObjectPtr<ADirectionalLight> Moon;
		TWeakObjectPtr<ASpotLight> Spot;
		TWeakObjectPtr<ALBWarden> Warden;
		TWeakObjectPtr<AActor> Wall;
		TWeakObjectPtr<ALBWardenApparition> Apparition;
		TWeakObjectPtr<APointLight> LightA;
		TWeakObjectPtr<APointLight> LightB;
		TWeakObjectPtr<AStaticMeshActor> Emissive;
		TWeakObjectPtr<ALBStateLightGroup> GroupA;
		TWeakObjectPtr<AStaticMeshActor> Lantern;
		/** The lantern's glass colour before the group ran (test 8), and its sample range while flickering. */
		FLinearColor GlassBase = FLinearColor::Black;
		float SampleMin = 0.f;
		float SampleMax = 0.f;
		int32 SampleCount = 0;
		double T0 = 0.0;
		float F0 = 0.f;
		int32 I0 = 0;

		ULBStormSubsystem* Storm(UWorld* W) const { return W ? W->GetSubsystem<ULBStormSubsystem>() : nullptr; }
	};

	class FStormRunner : public IAutomationLatentCommand
	{
	public:
		using FStepFn = TFunction<bool(FStormCtx&)>;

		explicit FStormRunner(FAutomationTestBase* InTest)
			: S(MakeShared<FStormState>()), Test(InTest), WardenOff(false)
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
			ALBCharacter* P = LBPie::Pawn();
			FStep& Step = Steps[StepIndex];
			if (!bEntered)
			{
				if (StepIndex > 0 && (!W || !P))
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
				Note(FString::Printf(TEXT("STEP %d begin: %s"), StepIndex + 1, *Step.Name));
			}

			FStormCtx Ctx;
			Ctx.W = W;
			Ctx.Pawn = P;
			Ctx.Now = W ? W->GetTimeSeconds() : 0.0;
			Ctx.Elapsed = Ctx.Now - WorldStart;
			Ctx.Frames = Frames;
			Ctx.bFirst = (Frames == 0);
			++Frames;

			const bool bDone = Step.Fn(Ctx);
			const bool bTimedOut = !bDone && (FPlatformTime::Seconds() - WallStart) > Step.Timeout;
			if (bTimedOut)
			{
				Test->AddError(FString::Printf(TEXT("Step '%s' timed out after %.0fs"), *Step.Name, Step.Timeout));
			}
			if (bDone || bTimedOut)
			{
				Note(FString::Printf(TEXT("STEP %d %s: %s"), StepIndex + 1, ErrCount() == ErrorsAtStart ? TEXT("PASS") : TEXT("FAIL"), *Step.Name));
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

		TSharedRef<FStormState> S;

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

	TSharedRef<FStormRunner> StartSession(FAutomationTestBase* Test, const TCHAR* Map = nullptr)
	{
		TSharedRef<FStormRunner> Runner = MakeShared<FStormRunner>(Test);
		FAutomationEditorCommonUtils::LoadMap(Map ? Map : GStormMap);
		FRequestPlaySessionParams PlayParams;
		PlayParams.WorldType = EPlaySessionWorldType::PlayInEditor;
		GEditor->RequestPlaySession(PlayParams);
		return Runner;
	}

	void Enqueue(const TSharedRef<FStormRunner>& Runner)
	{
		FAutomationTestFramework::Get().EnqueueLatentCommand(Runner);
	}

	// ---- Scene helpers ---------------------------------------------------------------------------------------------------------

	FGameplayTag Tag(const TCHAR* Name) { return LBPie::Tag(Name); }

	/** Spawns a light, Movable (so the storm may change its intensity), with the intensity and actor tag given. */
	template <class TLightActor>
	TLightActor* SpawnLight(UWorld* W, const FVector& Location, float Intensity, const TCHAR* ActorTag)
	{
		TLightActor* Light = W->SpawnActor<TLightActor>(Location, FRotator(-40.f, 35.f, 0.f));
		if (Light)
		{
			if (ULightComponent* Component = Light->GetLightComponent())
			{
				Component->SetMobility(EComponentMobility::Movable);
				Component->SetIntensity(Intensity);
			}
			if (ActorTag && *ActorTag)
			{
				Light->Tags.Add(FName(ActorTag));
			}
		}
		return Light;
	}

	float IntensityOf(const ALight* Light)
	{
		const ULightComponent* Component = Light ? Light->GetLightComponent() : nullptr;
		return Component ? Component->Intensity : -1.f;
	}

	bool WithinPercent(float Actual, float Expected, float Percent)
	{
		return FMath::Abs(Actual - Expected) <= FMath::Abs(Expected) * Percent / 100.f + 1.0e-5f;
	}

	/** Every RGB channel of Actual is within Percent of the same channel of Expected. */
	bool ColorWithinPercent(const FLinearColor& Actual, const FLinearColor& Expected, float Percent)
	{
		return WithinPercent(Actual.R, Expected.R, Percent) && WithinPercent(Actual.G, Expected.G, Percent) && WithinPercent(Actual.B, Expected.B, Percent);
	}

	const TCHAR* GGlowParameter = TEXT("Color");

	/** The first mesh slot of the actor whose material has the vector parameter; INDEX_NONE when there is none. */
	int32 FindGlowSlot(const AStaticMeshActor* Actor, FName Parameter)
	{
		const UMeshComponent* Mesh = Actor ? Actor->GetStaticMeshComponent() : nullptr;
		for (int32 Index = 0; Mesh && Index < Mesh->GetNumMaterials(); ++Index)
		{
			FLinearColor Value;
			const UMaterialInterface* Material = Mesh->GetMaterial(Index);
			if (Material && Material->GetVectorParameterValue(FHashedMaterialParameterInfo(Parameter), Value))
			{
				return Index;
			}
		}
		return INDEX_NONE;
	}

	/** The glass colour now: the dynamic instance on the lantern's glass slot. False (with an error) when there is none. */
	bool ReadGlass(FAutomationTestBase* Test, const FStormState& S, FLinearColor& OutColor)
	{
		const AStaticMeshActor* Lantern = S.Lantern.Get();
		const UMeshComponent* Mesh = Lantern ? Lantern->GetStaticMeshComponent() : nullptr;
		const UMaterialInstanceDynamic* Dynamic = Mesh ? Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(S.I0)) : nullptr;
		if (!Test->TestNotNull(TEXT("The glass slot holds a dynamic material instance made by the group"), Dynamic))
		{
			return false;
		}
		return Test->TestTrue(TEXT("The glass instance has the Color parameter"), Dynamic->GetVectorParameterValue(FHashedMaterialParameterInfo(GGlowParameter), OutColor));
	}

	/** A transient settings object with the plan's tag tables, seed 1401. Ambient flashes only when asked for. */
	void MakeSettings(FStormState& S, bool bAmbient)
	{
		S.Settings.Reset(NewObject<ULBStormSettings>(GetTransientPackage()));
		S.Settings->FillPlanTagDefaults();
		S.Settings->RandomSeed = 1401;
		S.Settings->bAmbientFlashes = bAmbient;
		S.Sink.Reset(NewObject<ULBStormTestSink>());
	}

	/** Spawns the tagged moon, hands the settings over and activates the subsystem. Returns null (with an error) on failure. */
	ULBStormSubsystem* ActivateStorm(FStormCtx& C, FStormState& S, FAutomationTestBase* Test, bool bAmbient, float MoonBase = 0.9f)
	{
		MakeSettings(S, bAmbient);
		S.Moon = SpawnLight<ADirectionalLight>(C.W, FVector(0.0, 0.0, GFloorTopZ + 5000.0), MoonBase, TEXT("LB_StormMoon"));
		ULBStormSubsystem* Storm = S.Storm(C.W);
		if (!Test->TestNotNull(TEXT("Storm subsystem exists in a PIE world"), Storm) || !Test->TestTrue(TEXT("Tagged moon spawned"), S.Moon.IsValid()))
		{
			return nullptr;
		}
		Storm->OverrideSettings(S.Settings.Get());
		Storm->RefreshLinkedLights();
		if (!Test->TestTrue(TEXT("Storm is active after RefreshLinkedLights with a tagged moon"), Storm->IsActive()))
		{
			return nullptr;
		}
		S.Sink->Bind(Storm, C.W);
		return Storm;
	}

	bool SpawnFloor(UWorld* W)
	{
		UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
		AStaticMeshActor* Floor = Cube ? W->SpawnActor<AStaticMeshActor>(FVector(0.f, 0.f, GFloorTopZ - 100.f), FRotator::ZeroRotator) : nullptr;
		if (!Floor)
		{
			return false;
		}
		Floor->SetMobility(EComponentMobility::Movable);
		Floor->GetStaticMeshComponent()->SetStaticMesh(Cube);
		Floor->SetActorScale3D(FVector(200.f, 60.f, 2.f));
		return true;
	}

	AStaticMeshActor* SpawnBox(UWorld* W, const FVector& Center, const FVector& SizeCm)
	{
		UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
		AStaticMeshActor* Box = Cube ? W->SpawnActor<AStaticMeshActor>(Center, FRotator::ZeroRotator) : nullptr;
		if (!Box)
		{
			return nullptr;
		}
		Box->SetMobility(EComponentMobility::Movable);
		Box->GetStaticMeshComponent()->SetStaticMesh(Cube);
		Box->SetActorScale3D(SizeCm / 100.f);
		return Box;
	}

	/** The player stands on the floor at the origin looking along +X. */
	void PlacePlayer(ALBCharacter* P)
	{
		const float Half = P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
		P->SetActorLocationAndRotation(FVector(0.0, 0.0, GFloorTopZ + Half + 0.1f), FRotator::ZeroRotator, false, nullptr, ETeleportType::TeleportPhysics);
		if (UCharacterMovementComponent* M = P->GetCharacterMovement())
		{
			M->StopMovementImmediately();
		}
		if (AController* Controller = P->GetController())
		{
			Controller->SetControlRotation(FRotator::ZeroRotator);
		}
	}

	void AimAt(ALBCharacter* P, const FVector& Point)
	{
		const APlayerController* PC = Cast<APlayerController>(P->GetController());
		const FVector Eye = PC && PC->PlayerCameraManager ? PC->PlayerCameraManager->GetCameraLocation() : P->GetActorLocation() + FVector(0.0, 0.0, 64.0);
		if (AController* Controller = P->GetController())
		{
			Controller->SetControlRotation((Point - Eye).Rotation());
		}
	}
}

// =====================================================================================================================
// 1. A flash drives the lights (and the flash value the MPC carries)
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormFlashDrivesLightsTest, "LastBell.Functional.Storm.FlashDrivesLightsAndMPC", FUNC_FLAGS)
bool FLBStormFlashDrivesLightsTest::RunTest(const FString& Parameters)
{
	TSharedRef<FStormRunner> R = StartSession(this);
	const TSharedRef<FStormState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, tagged moon and spot, storm active"), [S, Test](FStormCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ULBStormSubsystem* Storm = S->Storm(C.W);
		Test->TestNotNull(TEXT("Storm subsystem exists in a PIE world"), Storm);
		if (Storm)
		{
			Test->TestFalse(TEXT("A level with no tagged moon leaves the storm inactive"), Storm->IsActive());
		}
		Storm = ActivateStorm(C, *S, Test, false, 0.9f);
		if (!Storm)
		{
			return true;
		}
		S->Spot = SpawnLight<ASpotLight>(C.W, FVector(500.0, 0.0, GFloorTopZ + 3000.0), 1000.f, TEXT("LB_StormMoonSpot"));
		Test->TestTrue(TEXT("Tagged spot spawned"), S->Spot.IsValid());
		Storm->RefreshLinkedLights();
		Test->TestEqual(TEXT("Moon and spot are linked"), Storm->GetLinkedLightCount(), 2);
		Test->TestNearlyEqual(TEXT("Moon starts at its base"), IntensityOf(S->Moon.Get()), 0.9f, 1.0e-4f);
		Test->TestNearlyEqual(TEXT("Spot starts at its base"), IntensityOf(S->Spot.Get()), 1000.f, 1.0e-2f);
		Test->TestNearlyEqual(TEXT("Flash value starts at 0"), Storm->GetLightningFlash(), 0.f, 1.0e-6f);
		Storm->RequestFlash(1.f, 0.f, ELBFlashReason::Debug, ELBFlashProfile::Sheet);
		return true;
	});

	R->Add(TEXT("At the peak the lights and the flash value are up"), [S, Test](FStormCtx& C)
	{
		ULBStormSubsystem* Storm = S->Storm(C.W);
		if (!Storm)
		{
			Test->AddError(TEXT("Storm subsystem is gone"));
			return true;
		}
		if (Storm->GetLightningFlash() >= 0.95f)
		{
			const ULBStormSettings* Settings = S->Settings.Get();
			const float MoonBase = 0.9f;
			const float SpotBase = 1000.f;
			const float Moon = IntensityOf(S->Moon.Get());
			const float Spot = IntensityOf(S->Spot.Get());
			Note(FString::Printf(TEXT("peak: F %.3f, moon %.3f (base %.2f), spot %.1f (base %.0f)"), Storm->GetLightningFlash(), Moon, MoonBase, Spot, SpotBase));
			Test->TestTrue(TEXT("Moon >= base + 0.9 * FlashLux"), Moon >= MoonBase + 0.9f * Settings->FlashLux);
			Test->TestTrue(TEXT("Spot >= base * (1 + 0.9 * SpotFlashGain)"), Spot >= SpotBase * (1.f + 0.9f * Settings->SpotFlashGain));
			Test->TestTrue(TEXT("LightningFlash >= 0.9"), Storm->GetLightningFlash() >= 0.9f);
			Test->TestEqual(TEXT("One flash announced"), S->Sink->Flashes.Num(), 1);
			Test->TestEqual(TEXT("Announced with reason Debug"), S->Sink->Count(ELBFlashReason::Debug), 1);
			return true;
		}
		if (C.Elapsed > 3.0)
		{
			Test->AddError(TEXT("The requested Sheet flash never reached 0.95"));
			return true;
		}
		return false;
	});

	R->Add(TEXT("2 s later everything is back within 1 %"), [S, Test](FStormCtx& C)
	{
		if (C.Elapsed < 2.0)
		{
			return false;
		}
		const ULBStormSubsystem* Storm = S->Storm(C.W);
		Test->TestTrue(TEXT("Moon back at its base"), WithinPercent(IntensityOf(S->Moon.Get()), 0.9f, 1.f));
		Test->TestTrue(TEXT("Spot back at its base"), WithinPercent(IntensityOf(S->Spot.Get()), 1000.f, 1.f));
		Test->TestNearlyEqual(TEXT("Flash value back at 0"), Storm ? Storm->GetLightningFlash() : -1.f, 0.f, 1.0e-4f);
		Test->TestEqual(TEXT("Still exactly one flash"), S->Sink->Flashes.Num(), 1);
		return true;
	});

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// 2. The intensity follows the story
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormIntensityFollowsStoryTest, "LastBell.Functional.Storm.IntensityFollowsStory", FUNC_FLAGS)
bool FLBStormIntensityFollowsStoryTest::RunTest(const FString& Parameters)
{
	TSharedRef<FStormRunner> R = StartSession(this);
	const TSharedRef<FStormState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, storm active at the default intensity"), [S, Test](FStormCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ULBStormSubsystem* Storm = ActivateStorm(C, *S, Test, false);
		if (!Storm)
		{
			return true;
		}
		Test->TestNearlyEqual(TEXT("No story tag: intensity 0.55"), Storm->GetStormIntensity(), 0.55f, 1.0e-4f);
		Test->TestNearlyEqual(TEXT("No story tag: target 0.55"), Storm->GetTargetIntensity(), 0.55f, 1.0e-4f);
		ULBWorldStateSubsystem::Get(C.W)->AddState(Tag(TEXT("State.Ritual.2")));
		S->T0 = C.Now;
		return true;
	});

	R->Add(TEXT("Ritual.2: the target is 0.65 and the intensity rises at 0.02 per second"), [S, Test](FStormCtx& C)
	{
		const ULBStormSubsystem* Storm = S->Storm(C.W);
		if (!Storm)
		{
			Test->AddError(TEXT("Storm subsystem is gone"));
			return true;
		}
		if (C.Frames > 2)
		{
			Test->TestNearlyEqual(TEXT("Target is 0.65"), Storm->GetTargetIntensity(), 0.65f, 1.0e-4f);
		}
		if (C.Elapsed < 3.0)
		{
			return false;
		}
		const float Expected = FMath::Min(0.65f, 0.55f + 0.02f * static_cast<float>(C.Now - S->T0));
		Note(FString::Printf(TEXT("after %.2f s: intensity %.4f, expected %.4f"), C.Now - S->T0, Storm->GetStormIntensity(), Expected));
		Test->TestNearlyEqual(TEXT("Intensity rose at 0.02 per second (it does not jump)"), Storm->GetStormIntensity(), Expected, 0.006f);
		Test->TestTrue(TEXT("Intensity is above where it started"), Storm->GetStormIntensity() > 0.58f);
		Test->TestTrue(TEXT("Intensity has not reached the target yet"), Storm->GetStormIntensity() < 0.65f);
		return true;
	});

	R->Add(TEXT("ReplaceState with CloisterEntered snaps to 0.8"), [S, Test](FStormCtx& C)
	{
		ULBStormSubsystem* Storm = S->Storm(C.W);
		if (!Storm)
		{
			Test->AddError(TEXT("Storm subsystem is gone"));
			return true;
		}
		FGameplayTagContainer NewState;
		NewState.AddTag(Tag(TEXT("State.Event.CloisterEntered")));
		ULBWorldStateSubsystem::Get(C.W)->ReplaceState(NewState);
		Test->TestNearlyEqual(TEXT("Snapped to 0.8 at once"), Storm->GetStormIntensity(), 0.8f, 1.0e-4f);
		Test->TestNearlyEqual(TEXT("Target is 0.8"), Storm->GetTargetIntensity(), 0.8f, 1.0e-4f);
		return true;
	});

	R->Add(TEXT("The override replaces the target and snaps; clearing it goes back to the story"), [S, Test](FStormCtx& C)
	{
		ULBStormSubsystem* Storm = S->Storm(C.W);
		if (!Storm)
		{
			Test->AddError(TEXT("Storm subsystem is gone"));
			return true;
		}
		if (C.bFirst)
		{
			S->Settings->DebugIntensityOverride = 0.3f;
			return false;
		}
		if (C.Frames == 2)
		{
			Test->TestNearlyEqual(TEXT("DebugIntensityOverride snaps to 0.3"), Storm->GetStormIntensity(), 0.3f, 1.0e-4f);
			S->Settings->DebugIntensityOverride = -1.f;
			Storm->SetConsoleIntensityOverride(1.f);
			return false;
		}
		if (C.Frames == 4)
		{
			Test->TestNearlyEqual(TEXT("The console override snaps to 1.0"), Storm->GetStormIntensity(), 1.f, 1.0e-4f);
			Storm->SetConsoleIntensityOverride(-1.f);
			return true;
		}
		return false;
	});

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// 3. Scripted strikes fire on the tag being added only
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormScriptedStrikeTest, "LastBell.Functional.Storm.ScriptedStrikeOnTagOnly", FUNC_FLAGS)
bool FLBStormScriptedStrikeTest::RunTest(const FString& Parameters)
{
	TSharedRef<FStormRunner> R = StartSession(this);
	const TSharedRef<FStormState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, storm active, then Ritual.1 is added"), [S, Test](FStormCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ULBStormSubsystem* Storm = ActivateStorm(C, *S, Test, false);
		if (!Storm)
		{
			return true;
		}
		Test->TestEqual(TEXT("No flash yet"), S->Sink->Flashes.Num(), 0);
		S->T0 = C.Now;
		ULBWorldStateSubsystem::Get(C.W)->AddState(Tag(TEXT("State.Ritual.1")));
		return true;
	});

	R->Add(TEXT("Adding Ritual.1 flashes after 1.2 s (within 1.2 + 0.3)"), [S, Test](FStormCtx& C)
	{
		if (S->Sink->Flashes.Num() > 0)
		{
			const double Delay = S->Sink->Flashes[0].Time - S->T0;
			Note(FString::Printf(TEXT("scripted strike %.3f s after the tag"), Delay));
			Test->TestEqual(TEXT("Exactly one flash"), S->Sink->Flashes.Num(), 1);
			Test->TestEqual(TEXT("Reason Scripted"), S->Sink->Count(ELBFlashReason::Scripted), 1);
			Test->TestTrue(FString::Printf(TEXT("Not before 1.2 s (%.3f)"), Delay), Delay >= 1.2 - 0.05);
			Test->TestTrue(FString::Printf(TEXT("Within 1.2 + 0.3 s (%.3f)"), Delay), Delay <= 1.2 + 0.3);
			return true;
		}
		if (C.Now - S->T0 > 2.5)
		{
			Test->AddError(TEXT("Adding State.Ritual.1 did not flash within 2.5 s"));
			return true;
		}
		return false;
	});

	R->Add(TEXT("Wait for the flash to end, then ReplaceState containing the tag: no flash in 3 s"), [S, Test](FStormCtx& C)
	{
		ULBStormSubsystem* Storm = S->Storm(C.W);
		if (!Storm)
		{
			Test->AddError(TEXT("Storm subsystem is gone"));
			return true;
		}
		if (S->I0 == 0)
		{
			// First let the strike finish.
			if (Storm->IsFlashBusy() || C.Elapsed < 0.5)
			{
				return false;
			}
			S->I0 = 1;
			ULBWorldStateSubsystem* WorldState = ULBWorldStateSubsystem::Get(C.W);
			WorldState->ResetState();
			FGameplayTagContainer NewState;
			NewState.AddTag(Tag(TEXT("State.Ritual.1")));
			S->F0 = static_cast<float>(S->Sink->Flashes.Num());
			S->T0 = C.Now;
			WorldState->ReplaceState(NewState);
			return false;
		}
		if (C.Now - S->T0 < 3.0)
		{
			return false;
		}
		Test->TestEqual(TEXT("ReplaceState replays no strike"), static_cast<float>(S->Sink->Flashes.Num()), S->F0);
		return true;
	});

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// 4. The Warden reveal
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormWardenRevealTest, "LastBell.Functional.Storm.WardenRevealFlash", FUNC_FLAGS)
bool FLBStormWardenRevealTest::RunTest(const FString& Parameters)
{
	TSharedRef<FStormRunner> R = StartSession(this);
	const TSharedRef<FStormState> S = R->S;
	FAutomationTestBase* Test = this;

	// The Warden is moved to a floor of the test's own, 2000 cm ahead of the camera, and made a visible (non-dormant) Warden. The brain
	// stays Dormant with lb.Warden.Enabled 0, so nothing moves it back. The map has no storm zone: the exposure is the default, 1.
	const FVector WardenXY(2000.0, 0.0, 0.0);

	R->Add(TEXT("PIE ready, storm active, Warden 2000 cm ahead, a wall between"), [S, Test, WardenXY](FStormCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		if (!Test->TestTrue(TEXT("Floor spawned"), SpawnFloor(C.W)))
		{
			return true;
		}
		ULBStormSubsystem* Storm = ActivateStorm(C, *S, Test, false);
		if (!Storm)
		{
			return true;
		}
		PlacePlayer(C.Pawn);
		for (TActorIterator<ALBWarden> It(C.W); It; ++It)
		{
			S->Warden = *It;
		}
		ALBWarden* Warden = S->Warden.Get();
		if (!Test->TestNotNull(TEXT("L_Test_Warden has an ALBWarden"), Warden))
		{
			return true;
		}
		const float Half = Warden->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
		Warden->SetActorLocationAndRotation(FVector(WardenXY.X, WardenXY.Y, GFloorTopZ + Half + 2.f), FRotator(0.f, 180.f, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
		Warden->SetDormantPresentation(false);
		Test->TestFalse(TEXT("The Warden is no longer dormant"), Warden->IsDormantPresentation());
		Test->TestNearlyEqual(TEXT("No zones: exposure at the Warden is 1"), Storm->GetExposureAt(Warden->GetActorLocation()), 1.f, 1.0e-4f);

		// 500 x 50 x 500 cm, blocking ECC_Visibility, between the camera and the Warden's head.
		S->Wall = SpawnBox(C.W, FVector(1000.0, 0.0, GFloorTopZ + 250.0), FVector(50.0, 500.0, 500.0));
		Test->TestTrue(TEXT("Wall spawned"), S->Wall.IsValid());
		return true;
	});

	R->Add(TEXT("Settle"), [S](FStormCtx& C)
	{
		const UCharacterMovementComponent* M = C.Pawn->GetCharacterMovement();
		if (const ALBWarden* Warden = S->Warden.Get())
		{
			if (Warden->IsDormantPresentation())
			{
				return false;
			}
		}
		return C.Elapsed > 0.7 && M && M->IsMovingOnGround();
	});

	R->Add(TEXT("Behind the wall: no reveal in 3 s, and the rule says Blocked"), [S, Test](FStormCtx& C)
	{
		ULBStormSubsystem* Storm = S->Storm(C.W);
		ALBWarden* Warden = S->Warden.Get();
		if (!Storm || !Warden)
		{
			Test->AddError(TEXT("Storm or Warden is gone"));
			return true;
		}
		AimAt(C.Pawn, Warden->GetActorLocation() + FVector(0.0, 0.0, 140.0));
		if (S->Sink->Count(ELBFlashReason::WardenReveal) > 0)
		{
			Test->AddError(TEXT("A reveal flash fired although a wall blocks the line of sight"));
			return true;
		}
		if (C.Elapsed < 3.0)
		{
			return false;
		}
		Test->TestEqual(TEXT("Last decision: Blocked"), static_cast<int32>(Storm->GetLastRevealCheck()), static_cast<int32>(LBStormLogic::ERevealCheck::Blocked));
		return true;
	});

	R->Add(TEXT("Wall removed: a reveal flash within 1.5 s"), [S, Test](FStormCtx& C)
	{
		ALBWarden* Warden = S->Warden.Get();
		if (!Warden)
		{
			Test->AddError(TEXT("Warden is gone"));
			return true;
		}
		if (C.bFirst)
		{
			if (AActor* Wall = S->Wall.Get())
			{
				Wall->Destroy();
			}
			S->T0 = C.Now;
		}
		AimAt(C.Pawn, Warden->GetActorLocation() + FVector(0.0, 0.0, 140.0));
		if (S->Sink->Count(ELBFlashReason::WardenReveal) > 0)
		{
			const double Delay = S->Sink->LastTime(ELBFlashReason::WardenReveal) - S->T0;
			Note(FString::Printf(TEXT("reveal flash %.3f s after the wall went"), Delay));
			Test->TestTrue(FString::Printf(TEXT("Within 1.5 s (%.3f)"), Delay), Delay <= 1.5);
			Test->TestEqual(TEXT("Exactly one reveal"), S->Sink->Count(ELBFlashReason::WardenReveal), 1);
			return true;
		}
		if (C.Now - S->T0 > 1.5)
		{
			Test->AddError(TEXT("No reveal flash within 1.5 s of a clear view of the exposed Warden"));
			return true;
		}
		return false;
	});

	R->Add(TEXT("A second reveal is blocked by the cooldown"), [S, Test](FStormCtx& C)
	{
		ULBStormSubsystem* Storm = S->Storm(C.W);
		ALBWarden* Warden = S->Warden.Get();
		if (!Storm || !Warden)
		{
			Test->AddError(TEXT("Storm or Warden is gone"));
			return true;
		}
		AimAt(C.Pawn, Warden->GetActorLocation() + FVector(0.0, 0.0, 140.0));
		if (C.Elapsed < 5.0)
		{
			return false;
		}
		Test->TestEqual(TEXT("Still exactly one reveal after 5 s"), S->Sink->Count(ELBFlashReason::WardenReveal), 1);
		Test->TestEqual(TEXT("Last decision: Cooldown"), static_cast<int32>(Storm->GetLastRevealCheck()), static_cast<int32>(LBStormLogic::ERevealCheck::Cooldown));
		return true;
	});

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// 5. A state light group follows the tags
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormStateLightGroupTest, "LastBell.Functional.Storm.StateLightGroupFollowsTags", FUNC_FLAGS)
bool FLBStormStateLightGroupTest::RunTest(const FString& Parameters)
{
	TSharedRef<FStormRunner> R = StartSession(this);
	const TSharedRef<FStormState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("PIE ready, a light and a glow mesh in a group that goes Off on Ritual.1"), [S, Test](FStormCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ULBWorldStateSubsystem::Get(C.W)->ResetState();
		S->LightA = SpawnLight<APointLight>(C.W, FVector(0.0, 0.0, GFloorTopZ + 400.0), 1000.f, nullptr);
		S->Emissive = SpawnBox(C.W, FVector(100.0, 0.0, GFloorTopZ + 400.0), FVector(10.0, 10.0, 10.0));
		if (!Test->TestTrue(TEXT("Light and glow mesh spawned"), S->LightA.IsValid() && S->Emissive.IsValid()))
		{
			return true;
		}
		ALBStateLightGroup* Group = C.W->SpawnActorDeferred<ALBStateLightGroup>(ALBStateLightGroup::StaticClass(), FTransform::Identity, nullptr, nullptr, ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
		if (!Test->TestNotNull(TEXT("Light group spawned"), Group))
		{
			return true;
		}
		Group->Lights.Add(S->LightA.Get());
		Group->EmissiveActors.Add(S->Emissive.Get());
		FLBLightStateRule& Rule = Group->Rules.AddDefaulted_GetRef();
		Rule.RequiredTag = Tag(TEXT("State.Ritual.1"));
		Rule.Mode = ELBLightStateMode::Off;
		Group->FadeSeconds = 0.5f;
		Group->FinishSpawning(FTransform::Identity);
		S->GroupA = Group;

		Test->TestTrue(TEXT("No rule present: the light is at its base"), WithinPercent(IntensityOf(S->LightA.Get()), 1000.f, 1.f));
		Test->TestFalse(TEXT("No rule present: the glow mesh is shown"), S->Emissive->IsHidden());
		Test->TestFalse(TEXT("Not fading, not ticking"), Group->IsActorTickEnabled());
		return true;
	});

	R->Add(TEXT("Ritual.1 added: it fades and the light is 0 after the fade"), [S, Test](FStormCtx& C)
	{
		ALBStateLightGroup* Group = S->GroupA.Get();
		if (!Group || !S->LightA.IsValid() || !S->Emissive.IsValid())
		{
			Test->AddError(TEXT("Group, light or glow mesh is gone"));
			return true;
		}
		if (C.bFirst)
		{
			ULBWorldStateSubsystem::Get(C.W)->AddState(Tag(TEXT("State.Ritual.1")));
			Test->TestTrue(TEXT("The group is fading"), Group->IsFading());
			Test->TestTrue(TEXT("The group ticks while it fades"), Group->IsActorTickEnabled());
			Test->TestFalse(TEXT("The glow mesh is still shown at the start of the fade"), S->Emissive->IsHidden());
			return false;
		}
		if (C.Elapsed < 0.9)
		{
			Test->TestTrue(TEXT("Never above the base during the fade"), IntensityOf(S->LightA.Get()) <= 1000.f + 1.0e-3f);
			return false;
		}
		Test->TestTrue(FString::Printf(TEXT("Off after the fade (%.4f)"), IntensityOf(S->LightA.Get())), IntensityOf(S->LightA.Get()) <= 0.5f);
		Test->TestFalse(TEXT("Fade is over"), Group->IsFading());
		Test->TestTrue(TEXT("The glow mesh is hidden"), S->Emissive->IsHidden());
		Test->TestFalse(TEXT("Ticking stopped"), Group->IsActorTickEnabled());
		return true;
	});

	R->Add(TEXT("ReplaceState without the tag restores the base instantly"), [S, Test](FStormCtx& C)
	{
		ALBStateLightGroup* Group = S->GroupA.Get();
		if (!Group || !S->LightA.IsValid() || !S->Emissive.IsValid())
		{
			Test->AddError(TEXT("Group, light or glow mesh is gone"));
			return true;
		}
		ULBWorldStateSubsystem::Get(C.W)->ReplaceState(FGameplayTagContainer());
		Test->TestTrue(FString::Printf(TEXT("Base intensity back at once (%.2f)"), IntensityOf(S->LightA.Get())), WithinPercent(IntensityOf(S->LightA.Get()), 1000.f, 1.f));
		Test->TestFalse(TEXT("No fade after a state replace"), Group->IsFading());
		Test->TestFalse(TEXT("The glow mesh is shown again"), S->Emissive->IsHidden());
		return true;
	});

	R->Add(TEXT("With the tag present at BeginPlay the light is off on the first frame"), [S, Test](FStormCtx& C)
	{
		ULBWorldStateSubsystem::Get(C.W)->AddState(Tag(TEXT("State.Ritual.1")));
		S->LightB = SpawnLight<APointLight>(C.W, FVector(0.0, 300.0, GFloorTopZ + 400.0), 500.f, nullptr);
		if (!Test->TestTrue(TEXT("Second light spawned"), S->LightB.IsValid()))
		{
			return true;
		}
		Test->TestTrue(TEXT("The second light starts at its own base"), WithinPercent(IntensityOf(S->LightB.Get()), 500.f, 1.f));
		ALBStateLightGroup* Group = C.W->SpawnActorDeferred<ALBStateLightGroup>(ALBStateLightGroup::StaticClass(), FTransform::Identity, nullptr, nullptr, ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
		if (!Test->TestNotNull(TEXT("Second group spawned"), Group))
		{
			return true;
		}
		Group->Lights.Add(S->LightB.Get());
		FLBLightStateRule& Rule = Group->Rules.AddDefaulted_GetRef();
		Rule.RequiredTag = Tag(TEXT("State.Ritual.1"));
		Rule.Mode = ELBLightStateMode::Off;
		Group->FinishSpawning(FTransform::Identity);
		// The same call stack as the spawn: this is "the first frame".
		Test->TestTrue(FString::Printf(TEXT("Off the moment the group begins play (%.4f)"), IntensityOf(S->LightB.Get())), IntensityOf(S->LightB.Get()) <= 0.5f);
		Test->TestFalse(TEXT("Applied instantly: no fade"), Group->IsFading());
		return true;
	});

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// 6. An apparition with bLightningOnHold flashes when it holds
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormApparitionFlashTest, "LastBell.Functional.Storm.ApparitionHoldRequestsFlash", FUNC_FLAGS)
bool FLBStormApparitionFlashTest::RunTest(const FString& Parameters)
{
	TSharedRef<FStormRunner> R = StartSession(this);
	const TSharedRef<FStormState> S = R->S;
	FAutomationTestBase* Test = this;
	const FVector StationLocation(500.0, 0.0, GFloorTopZ);

	R->Add(TEXT("PIE ready, storm active, apparition with bLightningOnHold spawned"), [S, Test, StationLocation](FStormCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		const FGameplayTag Trigger = Tag(GTriggerTagName);
		if (!Test->TestTrue(TEXT("State.Test.Apparition exists in the tag ini"), Trigger.IsValid()) || !Test->TestTrue(TEXT("Floor spawned"), SpawnFloor(C.W)))
		{
			return true;
		}
		ULBStormSubsystem* Storm = ActivateStorm(C, *S, Test, false);
		if (!Storm)
		{
			return true;
		}
		PlacePlayer(C.Pawn);
		ULBWorldStateSubsystem::Get(C.W)->RemoveState(Trigger);

		FLBApparitionStation Station;
		Station.Location = StationLocation;
		Station.LookConeDegrees = 30.f;
		Station.MinPlayerDistance = 150.f;
		Station.FadeInSeconds = 0.2f;
		Station.HoldSeconds = 0.3f;
		Station.FadeOutSeconds = 0.2f;
		Station.GapAfterSeconds = 0.1f;
		Station.bLightningOnHold = true;

		ALBWardenApparition* Apparition = C.W->SpawnActorDeferred<ALBWardenApparition>(ALBWardenApparition::StaticClass(), FTransform::Identity, nullptr, nullptr, ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
		if (!Test->TestNotNull(TEXT("Apparition spawned"), Apparition))
		{
			return true;
		}
		Apparition->TriggerTag = Trigger;
		Apparition->ArmDelaySeconds = 0.1f;
		Apparition->Stations = { Station };
		Apparition->FinishSpawning(FTransform::Identity);
		S->Apparition = Apparition;
		Test->TestEqual(TEXT("No flash before the trigger"), S->Sink->Flashes.Num(), 0);
		return true;
	});

	R->Add(TEXT("Settle on the floor"), [](FStormCtx& C)
	{
		const UCharacterMovementComponent* M = C.Pawn->GetCharacterMovement();
		return C.Elapsed > 0.5 && M && M->IsMovingOnGround();
	});

	R->Add(TEXT("Trigger, look at the station: one Apparition flash when the figure holds, and none before"), [S, Test, StationLocation](FStormCtx& C)
	{
		ALBWardenApparition* Apparition = S->Apparition.Get();
		if (!Apparition)
		{
			Test->AddError(TEXT("Apparition is gone"));
			return true;
		}
		if (C.bFirst)
		{
			ULBWorldStateSubsystem::Get(C.W)->AddState(Tag(GTriggerTagName));
		}
		AimAt(C.Pawn, StationLocation + FVector(0.0, 0.0, Apparition->LookPointHeight));

		const ELBApparitionPhase Phase = Apparition->GetPhase();
		const bool bBeforeHold = Phase == ELBApparitionPhase::ArmDelay || Phase == ELBApparitionPhase::WaitForLook || Phase == ELBApparitionPhase::FadeIn;
		if (bBeforeHold && S->Sink->Count(ELBFlashReason::Apparition) > 0)
		{
			Test->AddError(TEXT("The apparition flashed before it reached Hold"));
			return true;
		}
		if (Phase == ELBApparitionPhase::Done)
		{
			Test->TestEqual(TEXT("Exactly one Apparition flash for the one station"), S->Sink->Count(ELBFlashReason::Apparition), 1);
			Test->TestEqual(TEXT("It is the only flash"), S->Sink->Flashes.Num(), 1);
			return true;
		}
		if (C.Elapsed > 8.0)
		{
			Test->AddError(FString::Printf(TEXT("The apparition did not finish its run (phase %s, %d Apparition flashes)"), LBApparition::PhaseName(Phase), S->Sink->Count(ELBFlashReason::Apparition)));
			return true;
		}
		return false;
	}, 20.f);

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// 7. A lantern's glass follows the light of its state light group (P14-1b, D-099)
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormGlowTest, "LastBell.Functional.Storm.StateLightGroupDrivesGlow", FUNC_FLAGS)
bool FLBStormGlowTest::RunTest(const FString& Parameters)
{
	TSharedRef<FStormRunner> R = StartSession(this);
	const TSharedRef<FStormState> S = R->S;
	FAutomationTestBase* Test = this;

	// The lantern mesh is loaded by path here only; game code never names an asset.
	const TCHAR* LanternMeshPath = TEXT("/Game/LastBell/ArtTest/Props/Wooden_Lantern_01/SM_Wooden_Lantern_01.SM_Wooden_Lantern_01");
	const FVector LightLocation(0.0, 0.0, GFloorTopZ + 400.0);

	R->Add(TEXT("PIE ready, a light, a lantern and a group that turns the light Off on Ritual.2"), [S, Test, LanternMeshPath, LightLocation](FStormCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 5)
		{
			return false;
		}
		ULBWorldStateSubsystem* WorldState = ULBWorldStateSubsystem::Get(C.W);
		WorldState->ResetState();
		Test->TestFalse(TEXT("The world state does not contain State.Ritual.2 at the start"), WorldState->HasState(Tag(TEXT("State.Ritual.2"))));

		UStaticMesh* LanternMesh = LoadObject<UStaticMesh>(nullptr, LanternMeshPath);
		if (!Test->TestNotNull(*FString::Printf(TEXT("The lantern mesh loads (%s)"), LanternMeshPath), LanternMesh))
		{
			return true;
		}

		// 300 lm, Movable point light.
		S->LightA = SpawnLight<APointLight>(C.W, LightLocation, 300.f, nullptr);
		if (!Test->TestTrue(TEXT("Point light spawned"), S->LightA.IsValid()))
		{
			return true;
		}
		if (UPointLightComponent* PointLight = Cast<UPointLightComponent>(S->LightA->GetLightComponent()))
		{
			PointLight->SetIntensityUnits(ELightUnits::Lumens);
			PointLight->SetIntensity(300.f);
		}

		// The lantern keeps a Static component, like the placed ones: the mesh is set while the component is unregistered (deferred
		// spawn), because a registered Static component refuses SetStaticMesh in a game world.
		AStaticMeshActor* Lantern = C.W->SpawnActorDeferred<AStaticMeshActor>(AStaticMeshActor::StaticClass(), FTransform(FRotator::ZeroRotator, LightLocation + FVector(0.0, 40.0, 0.0)), nullptr, nullptr, ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
		if (!Test->TestNotNull(TEXT("Lantern actor spawned"), Lantern))
		{
			return true;
		}
		// SpawnActorDeferred has already registered the component, so it is unregistered for the SetStaticMesh and registered again.
		UStaticMeshComponent* LanternMeshComponent = Lantern->GetStaticMeshComponent();
		if (LanternMeshComponent->IsRegistered())
		{
			LanternMeshComponent->UnregisterComponent();
		}
		LanternMeshComponent->SetStaticMesh(LanternMesh);
		if (!LanternMeshComponent->IsRegistered())
		{
			LanternMeshComponent->RegisterComponent();
		}
		Lantern->FinishSpawning(FTransform(FRotator::ZeroRotator, LightLocation + FVector(0.0, 40.0, 0.0)));
		S->Lantern = Lantern;
		Test->TestTrue(TEXT("The lantern component stays Static"), Lantern->GetStaticMeshComponent()->Mobility == EComponentMobility::Static);
		Test->TestTrue(TEXT("The lantern mesh is set"), Lantern->GetStaticMeshComponent()->GetStaticMesh() == LanternMesh);

		// Its glass: the slot whose mesh-default material has the Color parameter (MI_LB_LanternGlass_Lit).
		S->I0 = FindGlowSlot(Lantern, GGlowParameter);
		if (!Test->TestTrue(TEXT("The lantern has a material slot with the vector parameter Color"), S->I0 != INDEX_NONE))
		{
			return true;
		}
		const UMaterialInterface* Glass = Lantern->GetStaticMeshComponent()->GetMaterial(S->I0);
		Glass->GetVectorParameterValue(FHashedMaterialParameterInfo(GGlowParameter), S->GlassBase);
		Note(FString::Printf(TEXT("glass slot %d, material %s, base Color (%.3f, %.3f, %.3f, %.3f)"), S->I0, *GetNameSafe(Glass), S->GlassBase.R, S->GlassBase.G, S->GlassBase.B, S->GlassBase.A));
		Test->TestTrue(TEXT("The glass base colour is not black (otherwise this test proves nothing)"), FMath::Max3(S->GlassBase.R, S->GlassBase.G, S->GlassBase.B) > 0.01f);

		ALBStateLightGroup* Group = C.W->SpawnActorDeferred<ALBStateLightGroup>(ALBStateLightGroup::StaticClass(), FTransform::Identity, nullptr, nullptr, ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
		if (!Test->TestNotNull(TEXT("Light group spawned"), Group))
		{
			return true;
		}
		Group->Lights.Add(S->LightA.Get());
		Group->GlowActors.Add(Lantern);
		FLBLightStateRule& Rule = Group->Rules.AddDefaulted_GetRef();
		Rule.RequiredTag = Tag(TEXT("State.Ritual.2"));
		Rule.Mode = ELBLightStateMode::Off;
		Group->FinishSpawning(FTransform::Identity);
		S->GroupA = Group;

		// 1. No tag: the glass is at its base.
		FLinearColor Now;
		if (ReadGlass(Test, *S, Now))
		{
			Test->TestTrue(FString::Printf(TEXT("No tag: the glass Color equals its base within 1 %% (%.3f, %.3f, %.3f)"), Now.R, Now.G, Now.B), ColorWithinPercent(Now, S->GlassBase, 1.f));
		}
		return true;
	});

	R->Add(TEXT("Ritual.2 added: after the fade (1.5 + 0.5 s) the glass is black"), [S, Test](FStormCtx& C)
	{
		if (!S->GroupA.IsValid() || !S->Lantern.IsValid())
		{
			Test->AddError(TEXT("Group or lantern is gone"));
			return true;
		}
		if (C.bFirst)
		{
			ULBWorldStateSubsystem::Get(C.W)->AddState(Tag(TEXT("State.Ritual.2")));
			Test->TestTrue(TEXT("The group is fading"), S->GroupA->IsFading());
			return false;
		}
		if (C.Elapsed < 2.0)
		{
			return false;
		}
		FLinearColor Now;
		if (ReadGlass(Test, *S, Now))
		{
			const FLinearColor& B = S->GlassBase;
			Test->TestTrue(FString::Printf(TEXT("Ritual.2: every glass RGB channel is <= 1 %% of the base (%.4f, %.4f, %.4f)"), Now.R, Now.G, Now.B),
				Now.R <= B.R * 0.01f + 1.0e-5f && Now.G <= B.G * 0.01f + 1.0e-5f && Now.B <= B.B * 0.01f + 1.0e-5f);
		}
		Test->TestTrue(TEXT("The light itself is off too"), IntensityOf(S->LightA.Get()) <= 0.5f);
		return true;
	});

	R->Add(TEXT("ReplaceState without the tag: the glass is back at its base on the next frame"), [S, Test](FStormCtx& C)
	{
		if (!S->GroupA.IsValid() || !S->Lantern.IsValid())
		{
			Test->AddError(TEXT("Group or lantern is gone"));
			return true;
		}
		if (C.bFirst)
		{
			ULBWorldStateSubsystem::Get(C.W)->ReplaceState(FGameplayTagContainer());
			return false;
		}
		FLinearColor Now;
		if (ReadGlass(Test, *S, Now))
		{
			Test->TestTrue(FString::Printf(TEXT("After ReplaceState without the tag the glass Color is back at its base within 1 %% (%.3f, %.3f, %.3f)"), Now.R, Now.G, Now.B),
				ColorWithinPercent(Now, S->GlassBase, 1.f));
		}
		return true;
	});

	R->Add(TEXT("Flicker (0.8, 0.5, 8) applied instantly: every sample over 2 s is within [0.4, 0.8] of the base, and it moves"), [S, Test](FStormCtx& C)
	{
		ALBStateLightGroup* Group = S->GroupA.Get();
		if (!Group || !S->Lantern.IsValid())
		{
			Test->AddError(TEXT("Group or lantern is gone"));
			return true;
		}
		if (C.bFirst)
		{
			FLBLightStateRule& Rule = Group->Rules[0];
			Rule.Mode = ELBLightStateMode::Flicker;
			Rule.IntensityScale = 0.8f;
			Rule.FlickerAmount = 0.5f;
			Rule.FlickerSpeed = 8.f;
			S->SampleCount = 0;
			// The tag is present again, so the replace applies the Flicker rule at once: no fade.
			FGameplayTagContainer WithTag;
			WithTag.AddTag(Tag(TEXT("State.Ritual.2")));
			ULBWorldStateSubsystem::Get(C.W)->ReplaceState(WithTag);
			Test->TestEqual(TEXT("The group is in Flicker"), static_cast<int32>(Group->GetCurrentMode()), static_cast<int32>(ELBLightStateMode::Flicker));
			Test->TestFalse(TEXT("Applied instantly: no fade"), Group->IsFading());
		}

		FLinearColor Now;
		if (!ReadGlass(Test, *S, Now))
		{
			return true;
		}
		const FLinearColor& B = S->GlassBase;
		const auto Inside = [](float Value, float Base) { return Value >= Base * 0.4f - Base * 0.01f - 1.0e-5f && Value <= Base * 0.8f + Base * 0.01f + 1.0e-5f; };
		if (!Inside(Now.R, B.R) || !Inside(Now.G, B.G) || !Inside(Now.B, B.B))
		{
			Test->AddError(FString::Printf(TEXT("Flicker sample %d (%.4f, %.4f, %.4f) is outside [0.4, 0.8] of the base (%.4f, %.4f, %.4f)"), S->SampleCount, Now.R, Now.G, Now.B, B.R, B.G, B.B));
			return true;
		}
		// The channel with the most light follows the flicker best.
		const float Brightest = FMath::Max3(Now.R, Now.G, Now.B);
		if (S->SampleCount == 0)
		{
			S->SampleMin = Brightest;
			S->SampleMax = Brightest;
		}
		S->SampleMin = FMath::Min(S->SampleMin, Brightest);
		S->SampleMax = FMath::Max(S->SampleMax, Brightest);
		++S->SampleCount;

		if (C.Elapsed < 2.0)
		{
			return false;
		}
		Note(FString::Printf(TEXT("flicker: %d samples, brightest channel %.4f .. %.4f (base %.4f)"), S->SampleCount, S->SampleMin, S->SampleMax, FMath::Max3(B.R, B.G, B.B)));
		Test->TestTrue(TEXT("At least 30 samples were taken"), S->SampleCount >= 30);
		Test->TestTrue(FString::Printf(TEXT("The samples are not all equal (%.4f .. %.4f)"), S->SampleMin, S->SampleMax), S->SampleMax - S->SampleMin > 1.0e-3f * FMath::Max3(B.R, B.G, B.B));
		return true;
	});

	R->Add(TEXT("Clean up"), [S](FStormCtx& C)
	{
		if (ALBStateLightGroup* Group = S->GroupA.Get())
		{
			Group->Destroy();
		}
		if (AStaticMeshActor* Lantern = S->Lantern.Get())
		{
			Lantern->Destroy();
		}
		if (APointLight* Light = S->LightA.Get())
		{
			Light->Destroy();
		}
		ULBWorldStateSubsystem::Get(C.W)->ResetState();
		return true;
	});

	Enqueue(R);
	return true;
}

// =====================================================================================================================
// 8. The real L_Monastery setup. EXPECTED TO FAIL until P14-2 (assets) and P14-3 (level work) are done.
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormMonasteryTest, "LastBell.Functional.Storm.Monastery.StormSetup", FUNC_FLAGS)
bool FLBStormMonasteryTest::RunTest(const FString& Parameters)
{
	if (!FPackageName::DoesPackageExist(GMonasteryMap))
	{
		AddWarning(TEXT("L_Monastery does not exist: the storm setup check is skipped"));
		return true;
	}
	TSharedRef<FStormRunner> R = StartSession(this, GMonasteryMap);
	const TSharedRef<FStormState> S = R->S;
	FAutomationTestBase* Test = this;

	R->Add(TEXT("L_Monastery: tags, zones, light groups, settings asset, MPC, apparitions"), [S, Test](FStormCtx& C)
	{
		if (!LBPie::WorldReady() || C.Frames < 10)
		{
			return false;
		}

		// ---- Tagged lights ----
		int32 Moons = 0, Spots = 0, Fills = 0, Skies = 0;
		for (TActorIterator<AActor> It(C.W); It; ++It)
		{
			const AActor* Actor = *It;
			Moons += (Actor->ActorHasTag(TEXT("LB_StormMoon")) && Actor->IsA<ADirectionalLight>()) ? 1 : 0;
			Spots += Actor->ActorHasTag(TEXT("LB_StormMoonSpot")) ? 1 : 0;
			Fills += Actor->ActorHasTag(TEXT("LB_StormFill")) ? 1 : 0;
			Skies += Actor->ActorHasTag(TEXT("LB_StormSky")) ? 1 : 0;
		}
		Test->TestEqual(TEXT("Exactly one ADirectionalLight tagged LB_StormMoon in L_Monastery (P14-3 tags the moon)"), Moons, 1);
		Test->TestEqual(TEXT("10 actors tagged LB_StormMoonSpot (chapel S1/S2/S3/Roof, crypt G1/G2/G3, tower F03/F07/F08; P14-3)"), Spots, 10);
		Test->TestEqual(TEXT("1 actor tagged LB_StormFill (L_Tw_BellFill; P14-3)"), Fills, 1);
		Test->TestEqual(TEXT("1 actor tagged LB_StormSky (the SkyLight; P14-3)"), Skies, 1);

		// ---- Zones ----
		int32 Zones = 0;
		for (TActorIterator<ALBStormZone> It(C.W); It; ++It)
		{
			++Zones;
		}
		Test->TestEqual(TEXT("7 ALBStormZone actors in L_Monastery (P14-3 places SZN_Chapel/Crypt/Passage/Cloister/Garth/TowerShaft/Belfry)"), Zones, 7);

		// ---- Light groups: each light valid and in one group only ----
		int32 Groups = 0;
		bool bLightsValid = true;
		TMap<const ALight*, int32> GroupsPerLight;
		TMap<const AActor*, int32> GroupsPerGlowActor;
		for (TActorIterator<ALBStateLightGroup> It(C.W); It; ++It)
		{
			++Groups;
			const ALBStateLightGroup* Group = *It;
			Test->TestTrue(FString::Printf(TEXT("Light group %s lists at least one light"), *Group->GetName()), Group->Lights.Num() > 0);

			// Glow actors (P14-1b): each must have a mesh slot with the group's glow parameter, and be in one group only.
			for (const AActor* GlowActor : Group->GlowActors)
			{
				if (!IsValid(GlowActor))
				{
					Test->AddError(FString::Printf(TEXT("Light group %s has an empty or invalid glow actor entry"), *Group->GetName()));
					continue;
				}
				GroupsPerGlowActor.FindOrAdd(GlowActor) += 1;
				int32 GlowSlots = 0;
				TInlineComponentArray<UMeshComponent*> Meshes;
				GlowActor->GetComponents(Meshes);
				for (const UMeshComponent* Mesh : Meshes)
				{
					for (int32 Index = 0; Index < Mesh->GetNumMaterials(); ++Index)
					{
						FLinearColor Value;
						const UMaterialInterface* Material = Mesh->GetMaterial(Index);
						GlowSlots += (Material && Material->GetVectorParameterValue(FHashedMaterialParameterInfo(Group->GlowParameter), Value)) ? 1 : 0;
					}
				}
				Test->TestTrue(FString::Printf(TEXT("Glow actor %s of group %s has a material slot with the vector parameter %s"), *GlowActor->GetName(), *Group->GetName(), *Group->GlowParameter.ToString()), GlowSlots > 0);
			}
			for (const ALight* Light : Group->Lights)
			{
				if (!IsValid(Light))
				{
					bLightsValid = false;
					Test->AddError(FString::Printf(TEXT("Light group %s has an empty or invalid light entry"), *Group->GetName()));
					continue;
				}
				GroupsPerLight.FindOrAdd(Light) += 1;
			}
		}
		Test->TestEqual(TEXT("9 ALBStateLightGroup actors in L_Monastery (P14-3 places the SLG_* groups of plan section 8)"), Groups, 9);
		Test->TestTrue(TEXT("Every light in every group is valid"), bLightsValid);
		for (const TPair<const ALight*, int32>& Pair : GroupsPerLight)
		{
			if (Pair.Value > 1)
			{
				Test->AddError(FString::Printf(TEXT("The light %s is listed in %d light groups; a light may be in one group only"), *Pair.Key->GetName(), Pair.Value));
			}
		}
		for (const TPair<const AActor*, int32>& Pair : GroupsPerGlowActor)
		{
			if (Pair.Value > 1)
			{
				Test->AddError(FString::Printf(TEXT("The glow actor %s is listed in %d light groups; a glow actor may be in one group only"), *Pair.Key->GetName(), Pair.Value));
			}
		}

		// ---- Settings asset and MPC ----
		const ULBGameSettings* GameSettings = GetDefault<ULBGameSettings>();
		ULBStormSettings* Settings = GameSettings ? GameSettings->StormSettings.LoadSynchronous() : nullptr;
		if (Test->TestNotNull(TEXT("DA_StormSettings loads through ULBGameSettings::StormSettings (P14-2 creates it and sets the ini entry)"), Settings))
		{
			Test->TestEqual(TEXT("DA_StormSettings.DebugFreezeFlash is saved as -1"), Settings->DebugFreezeFlash, -1.f);
			Test->TestEqual(TEXT("DA_StormSettings.DebugIntensityOverride is saved as -1"), Settings->DebugIntensityOverride, -1.f);
			Test->TestEqual(TEXT("DA_StormSettings has the 8 story steps"), Settings->StoryIntensity.Num(), 8);
			Test->TestEqual(TEXT("DA_StormSettings has the 6 scripted strikes"), Settings->ScriptedStrikes.Num(), 6);

			const UMaterialParameterCollection* Collection = Settings->Collection.LoadSynchronous();
			if (Test->TestNotNull(TEXT("DA_StormSettings.Collection loads (MPC_LB_Storm; P14-2)"), Collection))
			{
				for (const TCHAR* Name : { TEXT("StormIntensity"), TEXT("LightningFlash"), TEXT("WindStrength"), TEXT("WindPhase"), TEXT("PlayerExposure"), TEXT("DomeFlashGain"),
						 TEXT("DomeFlashAdd"), TEXT("GlassFlashGain"), TEXT("ShaftFlashGain"), TEXT("PoolFlashGain"), TEXT("RevealGain"), TEXT("RevealEmissive") })
				{
					Test->TestNotNull(*FString::Printf(TEXT("MPC_LB_Storm has the scalar parameter %s"), Name), Collection->GetScalarParameterByName(FName(Name)));
				}
				for (const TCHAR* Name : { TEXT("WindDirection"), TEXT("FlashDirection"), TEXT("FlashTint") })
				{
					Test->TestNotNull(*FString::Printf(TEXT("MPC_LB_Storm has the vector parameter %s"), Name), Collection->GetVectorParameterByName(FName(Name)));
				}
			}
		}

		// ---- Apparitions ----
		int32 Apparitions = 0;
		for (TActorIterator<ALBWardenApparition> It(C.W); It; ++It)
		{
			++Apparitions;
			const ALBWardenApparition* Apparition = *It;
			bool bAnyStationFlashes = false;
			for (const FLBApparitionStation& Station : Apparition->Stations)
			{
				bAnyStationFlashes |= Station.bLightningOnHold;
			}
			Test->TestTrue(FString::Printf(TEXT("Apparition %s has bLightningOnHold on a station (P14-3 sets it on Apparition_Courtyard and Apparition_Chapel)"), *Apparition->GetActorLabel()), bAnyStationFlashes);
		}
		Test->TestEqual(TEXT("2 apparitions in L_Monastery (courtyard roofline and chapel rail)"), Apparitions, 2);

		// ---- The storm itself, if the setup is there ----
		if (const ULBStormSubsystem* Storm = S->Storm(C.W))
		{
			Test->TestTrue(TEXT("The storm subsystem is active in L_Monastery (moon tagged and DA_StormSettings set)"), Storm->IsActive());
			Test->TestEqual(TEXT("The storm knows the 7 zones"), Storm->GetZoneCount(), 7);
		}
		return true;
	}, 90.f);

	Enqueue(R);
	return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
