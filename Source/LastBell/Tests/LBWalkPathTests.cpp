#include "Tests/LBRouteBot.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Editor.h"
#include "EngineUtils.h"
#include "Tests/AutomationEditorCommon.h"
#include "Engine/World.h"
#include "Engine/TargetPoint.h"
#include "Misc/PackageName.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Character/LBCharacter.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "LBLog.h"

// R-21: the route bot teleports, so it cannot prove the level is walkable. FLBWalkPathRunner physically walks a path
// of ATargetPoints tagged "WalkPath.<Name>.<NN>" with AddMovementInput only (no teleporting after the start) and fails
// on stuck / fell / timeout / slid.

namespace
{
	const TCHAR* GWalkMicroSliceMap = TEXT("/Game/LastBell/Maps/L_Test_MicroSlice");
	const TCHAR* GWalkMonasteryMap = TEXT("/Game/LastBell/Maps/L_Monastery");

	constexpr float ReachHorizontal = 60.f;
	constexpr float ReachVertical = 80.f;
	constexpr double StuckWindow = 3.0;
	constexpr float StuckMinProgress = 10.f;
	constexpr float FellBelow = 150.f;
	constexpr double FallingMax = 1.0;
	constexpr double PathTimeout = 120.0;
	constexpr double SettleTime = 1.0;
	constexpr float MaxDrift = 30.f;
	constexpr double DoorWait = 2.5;

	struct FWalkPoint
	{
		int32 Index = 0;
		FVector Loc = FVector::ZeroVector;
		TArray<FString> Tags;
	};

	struct FWalkPathDef
	{
		FString Name;
		TArray<FWalkPoint> Points;
	};

	FString ModeName(const ACharacter* C)
	{
		const UCharacterMovementComponent* M = C ? C->GetCharacterMovement() : nullptr;
		if (!M)
		{
			return TEXT("?");
		}
		const UEnum* E = StaticEnum<EMovementMode>();
		return E ? E->GetNameStringByValue(static_cast<int64>(M->MovementMode.GetValue())) : TEXT("?");
	}

	float FootZ(const ACharacter* C)
	{
		return static_cast<float>(C->GetActorLocation().Z) - C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	}

	bool TraceFloor(UWorld* W, const AActor* Ignore, const FVector& From, float Depth, float& OutZ)
	{
		FCollisionQueryParams Params(SCENE_QUERY_STAT(LBWalkFloor), false, Ignore);
		FHitResult Hit;
		if (W->LineTraceSingleByChannel(Hit, From, From - FVector(0, 0, Depth), ECC_Visibility, Params)
			&& !Hit.bStartPenetrating && Hit.ImpactNormal.Z > 0.6f)
		{
			OutZ = static_cast<float>(Hit.ImpactPoint.Z);
			return true;
		}
		return false;
	}

	/** Finds every WalkPath.<P>.<NN> target point in the world, grouped per path name and sorted by suffix. */
	TArray<FWalkPathDef> DiscoverPaths(UWorld* W)
	{
		TMap<FString, FWalkPathDef> Map;
		const FString Prefix = TEXT("WalkPath.");
		for (TActorIterator<ATargetPoint> It(W); It; ++It)
		{
			for (const FName& T : It->Tags)
			{
				const FString S = T.ToString();
				if (!S.StartsWith(Prefix))
				{
					continue;
				}
				int32 LastDot = INDEX_NONE;
				if (!S.FindLastChar(TEXT('.'), LastDot) || LastDot <= Prefix.Len())
				{
					continue;
				}
				const FString Suffix = S.Mid(LastDot + 1);
				if (Suffix.IsEmpty() || !Suffix.IsNumeric())
				{
					continue;
				}
				const FString PathName = S.Mid(Prefix.Len(), LastDot - Prefix.Len());
				FWalkPathDef& Def = Map.FindOrAdd(PathName);
				Def.Name = PathName;
				FWalkPoint P;
				P.Index = FCString::Atoi(*Suffix);
				P.Loc = It->GetActorLocation();
				for (const FName& Other : It->Tags)
				{
					P.Tags.Add(Other.ToString());
				}
				Def.Points.Add(P);
			}
		}
		TArray<FWalkPathDef> Out;
		for (auto& Pair : Map)
		{
			Pair.Value.Points.Sort([](const FWalkPoint& A, const FWalkPoint& B) { return A.Index < B.Index; });
			Out.Add(MoveTemp(Pair.Value));
		}
		Out.Sort([](const FWalkPathDef& A, const FWalkPathDef& B) { return A.Name < B.Name; });
		return Out;
	}

	/** Walks one path by input only. Call Tick() every frame after Begin(). */
	class FLBWalkPathRunner
	{
	public:
		enum class EStatus { Running, Passed, Failed };

		FLBWalkPathRunner(FAutomationTestBase* InTest, const FWalkPathDef& InDef, bool bInResetState)
			: Test(InTest), Def(InDef), bResetState(bInResetState)
		{
		}

		const FString& Name() const { return Def.Name; }

		EStatus Tick()
		{
			UWorld* W = LBPie::World();
			ALBCharacter* P = LBPie::Pawn();
			if (!W || !P)
			{
				return Fail(TEXT("no world or pawn"), FVector::ZeroVector, nullptr);
			}
			const double Now = W->GetTimeSeconds();

			switch (Phase)
			{
			case EPhase::Begin:
				if (Def.Points.Num() < 2)
				{
					return Fail(FString::Printf(TEXT("no walk path %s"), *Def.Name), FVector::ZeroVector, P);
				}
				if (ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(W))
				{
					if (bResetState)
					{
						State->ResetState();
					}
					const FString ReqPrefix = TEXT("Requires.");
					for (const FString& T : Def.Points[0].Tags)
					{
						if (T.StartsWith(ReqPrefix))
						{
							const FGameplayTag Tag = LBPie::Tag(*T.Mid(ReqPrefix.Len()));
							if (Tag.IsValid())
							{
								State->AddState(Tag);
								UE_LOG(LogLB, Display, TEXT("[WalkPath] %s requires %s"), *Def.Name, *Tag.ToString());
							}
							else
							{
								Test->AddError(FString::Printf(TEXT("WalkPath %s: unknown required tag '%s'"), *Def.Name, *T.Mid(ReqPrefix.Len())));
							}
						}
					}
				}
				PlaceAtStart(W, P);
				PhaseStart = Now;
				Phase = EPhase::Wait;
				return EStatus::Running;

			case EPhase::Wait:
				if (Now - PhaseStart < DoorWait)
				{
					return EStatus::Running;
				}
				PathStart = Now;
				WpIdx = 1;
				ResetStuck(P, Now);
				Phase = EPhase::Walk;
				return EStatus::Running;

			case EPhase::Walk:
				return TickWalk(W, P, Now);
			}
			return EStatus::Running;
		}

	private:
		enum class EPhase { Begin, Wait, Walk };

		FAutomationTestBase* Test;
		FWalkPathDef Def;
		bool bResetState;
		EPhase Phase = EPhase::Begin;
		double PhaseStart = 0.0;
		double PathStart = 0.0;
		int32 WpIdx = 1;
		bool bSettling = false;
		double SettleStart = 0.0;
		FVector ReachLoc = FVector::ZeroVector;
		double ReachTime = 0.0;
		double StuckStart = 0.0;
		float StuckRefDist = 0.f;
		double FallingSince = -1.0;

		static float Dist2D(const FVector& A, const FVector& B)
		{
			return static_cast<float>(FVector::DistXY(A, B));
		}

		void ResetStuck(const ALBCharacter* P, double Now)
		{
			StuckStart = Now;
			StuckRefDist = Dist2D(P->GetActorLocation(), Def.Points[WpIdx].Loc);
		}

		void PlaceAtStart(UWorld* W, ALBCharacter* P)
		{
			const FVector P0 = Def.Points[0].Loc;
			const FVector P1 = Def.Points[1].Loc;
			float FloorZ = static_cast<float>(P0.Z);
			if (!TraceFloor(W, P, P0 + FVector(0, 0, 100), 600.f, FloorZ))
			{
				FloorZ = static_cast<float>(P0.Z);
			}
			const float HalfHeight = P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
			const FVector Dir = FVector(P1.X - P0.X, P1.Y - P0.Y, 0.0);
			P->SetActorLocation(FVector(P0.X, P0.Y, FloorZ + HalfHeight + 2.f), false, nullptr, ETeleportType::TeleportPhysics);
			if (UCharacterMovementComponent* M = P->GetCharacterMovement())
			{
				M->StopMovementImmediately();
			}
			if (AController* C = P->GetController())
			{
				C->SetControlRotation(FRotator(0.f, Dir.Rotation().Yaw, 0.f));
			}
		}

		EStatus Fail(const FString& Reason, const FVector& Loc, const ACharacter* P)
		{
			const FString Msg = FString::Printf(TEXT("[WalkPath] %s FAIL: %s near wp %d at %s, mode=%s"), *Def.Name, *Reason, WpIdx,
				*Loc.ToString(), *ModeName(P));
			UE_LOG(LogLB, Error, TEXT("%s"), *Msg);
			Test->AddError(Msg);
			return EStatus::Failed;
		}

		EStatus TickWalk(UWorld* W, ALBCharacter* P, double Now)
		{
			const FVector Loc = P->GetActorLocation();
			const FVector Tgt = Def.Points[WpIdx].Loc;
			const float D2 = Dist2D(Loc, Tgt);
			const float Foot = FootZ(P);

			if (Now - PathStart > PathTimeout)
			{
				return Fail(FString::Printf(TEXT("timeout %.0fs"), PathTimeout), Loc, P);
			}

			if (bSettling)
			{
				if (Now - SettleStart < SettleTime)
				{
					return EStatus::Running;
				}
				const float Drift = Dist2D(Loc, ReachLoc);
				UE_LOG(LogLB, Display, TEXT("[WalkPath] %s wp %d/%d reached at %s (t=%.1fs, drift=%.1fcm)"), *Def.Name, WpIdx + 1,
					Def.Points.Num(), *ReachLoc.ToString(), ReachTime - PathStart, Drift);
				if (Drift > MaxDrift)
				{
					return Fail(FString::Printf(TEXT("slid %.1fcm (limit %.0f) after stopping"), Drift, MaxDrift), Loc, P);
				}
				bSettling = false;
				++WpIdx;
				if (WpIdx >= Def.Points.Num())
				{
					UE_LOG(LogLB, Display, TEXT("[WalkPath] %s PASS (%d waypoints, %.1fs)"), *Def.Name, Def.Points.Num(), Now - PathStart);
					return EStatus::Passed;
				}
				ResetStuck(P, Now);
				return EStatus::Running;
			}

			if (D2 < ReachHorizontal && FMath::Abs(Foot - static_cast<float>(Tgt.Z)) < ReachVertical)
			{
				bSettling = true;
				SettleStart = Now;
				ReachLoc = Loc;
				ReachTime = Now;
				return EStatus::Running;
			}

			// Fell: far below the route, or falling for too long.
			const float LowerZ = static_cast<float>(FMath::Min(Def.Points[WpIdx - 1].Loc.Z, Tgt.Z));
			if (Foot < LowerZ - FellBelow)
			{
				return Fail(FString::Printf(TEXT("fell (foot Z %.0f, route Z %.0f)"), Foot, LowerZ), Loc, P);
			}
			if (P->GetCharacterMovement()->IsFalling())
			{
				if (FallingSince < 0.0)
				{
					FallingSince = Now;
				}
				else if (Now - FallingSince > FallingMax)
				{
					return Fail(FString::Printf(TEXT("falling for %.1fs"), Now - FallingSince), Loc, P);
				}
			}
			else
			{
				FallingSince = -1.0;
			}

			// Stuck: no horizontal progress.
			if (Now - StuckStart >= StuckWindow)
			{
				if (StuckRefDist - D2 < StuckMinProgress)
				{
					return Fail(FString::Printf(TEXT("stuck (progress %.1fcm in %.0fs, dist %.0fcm, dz %.0f)"), StuckRefDist - D2, StuckWindow, D2,
						static_cast<float>(Tgt.Z) - Foot), Loc, P);
				}
				StuckStart = Now;
				StuckRefDist = D2;
			}

			// Drive: horizontal input toward the waypoint, camera faces forward.
			FVector Dir = Tgt - Loc;
			Dir.Z = 0.0;
			if (!Dir.IsNearlyZero())
			{
				Dir.Normalize();
				P->AddMovementInput(Dir, 1.f);
				if (AController* C = P->GetController())
				{
					C->SetControlRotation(FRotator(0.f, Dir.Rotation().Yaw, 0.f));
				}
			}
			return EStatus::Running;
		}
	};

	/** Latent command: PIE start, optional runtime point spawn, then walks each discovered path in turn. */
	class FLBWalkTestCommand : public IAutomationLatentCommand
	{
	public:
		FLBWalkTestCommand(FAutomationTestBase* InTest, bool bInSynthetic)
			: Test(InTest), bSynthetic(bInSynthetic), WallStart(FPlatformTime::Seconds())
		{
		}

		virtual bool Update() override
		{
			if (Stage == EStage::Done)
			{
				return true;
			}
			if (Stage != EStage::EndPie && FPlatformTime::Seconds() - WallStart > WallTimeout)
			{
				Test->AddError(FString::Printf(TEXT("WalkPath wall-clock timeout of %.0fs"), WallTimeout));
				Stage = EStage::EndPie;
				EndRequested = false;
			}

			switch (Stage)
			{
			case EStage::WaitPie:
				++Frames;
				if (LBPie::WorldReady() && Frames >= 5)
				{
					Stage = EStage::Setup;
				}
				return false;

			case EStage::Setup:
				if (bSynthetic)
				{
					SpawnSyntheticPoints();
				}
				Paths = DiscoverPaths(LBPie::World());
				if (Paths.Num() == 0)
				{
					Test->AddWarning(TEXT("No WalkPath.* target points in the map yet: nothing to walk"));
					Stage = EStage::EndPie;
					return false;
				}
				UE_LOG(LogLB, Display, TEXT("[WalkPath] discovered %d path(s)"), Paths.Num());
				PathIdx = 0;
				Stage = EStage::Run;
				Runner = MakeUnique<FLBWalkPathRunner>(Test, Paths[0], !bSynthetic);
				return false;

			case EStage::Run:
			{
				if (!Runner)
				{
					Stage = EStage::EndPie;
					return false;
				}
				const FLBWalkPathRunner::EStatus S = Runner->Tick();
				if (S == FLBWalkPathRunner::EStatus::Running)
				{
					return false;
				}
				++PathIdx;
				Runner.Reset();
				if (PathIdx < Paths.Num())
				{
					Runner = MakeUnique<FLBWalkPathRunner>(Test, Paths[PathIdx], !bSynthetic);
				}
				else
				{
					Stage = EStage::EndPie;
				}
				return false;
			}

			case EStage::EndPie:
				if (!EndRequested)
				{
					EndRequested = true;
					if (GEditor && GEditor->PlayWorld)
					{
						GEditor->RequestEndPlayMap();
					}
					return false;
				}
				if (LBPie::World() == nullptr)
				{
					LBPie::ClearSlot();
					Stage = EStage::Done;
					return true;
				}
				return false;

			default:
				return true;
			}
		}

	private:
		enum class EStage { WaitPie, Setup, Run, EndPie, Done };

		static constexpr double WallTimeout = 900.0;

		FAutomationTestBase* Test;
		bool bSynthetic;
		double WallStart;
		EStage Stage = EStage::WaitPie;
		int32 Frames = 0;
		bool EndRequested = false;
		TArray<FWalkPathDef> Paths;
		int32 PathIdx = 0;
		TUniquePtr<FLBWalkPathRunner> Runner;

		/** Three waypoints straight across the micro-slice entry room floor. */
		void SpawnSyntheticPoints()
		{
			UWorld* W = LBPie::World();
			const float Xs[3] = { 100.f, 250.f, 400.f };
			for (int32 i = 0; i < 3; ++i)
			{
				float FloorZ = 0.f;
				if (!TraceFloor(W, LBPie::Pawn(), FVector(Xs[i], 0.f, 300.f), 1000.f, FloorZ))
				{
					Test->AddError(FString::Printf(TEXT("Synthetic walk path: no floor under (%.0f, 0)"), Xs[i]));
					FloorZ = 0.f;
				}
				FActorSpawnParameters Params;
				Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
				if (ATargetPoint* TP = W->SpawnActor<ATargetPoint>(FVector(Xs[i], 0.f, FloorZ), FRotator::ZeroRotator, Params))
				{
					TP->Tags.Add(*FString::Printf(TEXT("WalkPath.Synthetic.%02d"), i));
				}
			}
		}
	};

	void StartWalkPie(const TCHAR* MapPath)
	{
		FAutomationEditorCommonUtils::LoadMap(MapPath);
		FRequestPlaySessionParams PlayParams;
		PlayParams.WorldType = EPlaySessionWorldType::PlayInEditor;
		GEditor->RequestPlaySession(PlayParams);
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWalkPathMonasteryTest, "LastBell.Functional.WalkPath.Monastery",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWalkPathMonasteryTest::RunTest(const FString& Parameters)
{
	if (!FPackageName::DoesPackageExist(GWalkMonasteryMap))
	{
		AddWarning(TEXT("L_Monastery does not exist yet: WalkPath.Monastery skipped"));
		return true;
	}
	LBPie::ClearSlot();
	StartWalkPie(GWalkMonasteryMap);
	ADD_LATENT_AUTOMATION_COMMAND(FLBWalkTestCommand(this, false));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBWalkPathSyntheticTest, "LastBell.Functional.WalkPath.Synthetic",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FLBWalkPathSyntheticTest::RunTest(const FString& Parameters)
{
	LBPie::ClearSlot();
	StartWalkPie(GWalkMicroSliceMap);
	ADD_LATENT_AUTOMATION_COMMAND(FLBWalkTestCommand(this, true));
	return true;
}

#endif
