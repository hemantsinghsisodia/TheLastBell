#include "AI/LBWardenBrainComponent.h"
#include "AI/LBWarden.h"
#include "AI/LBWardenController.h"
#include "AI/LBWardenMarkers.h"
#include "AI/LBWardenTuningData.h"
#include "Character/LBCandleComponent.h"
#include "Character/LBCharacter.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "Components/CapsuleComponent.h"
#include "DrawDebugHelpers.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "NavigationSystem.h"
#include "Perception/AIPerceptionComponent.h"
#include "Perception/AISense_Hearing.h"
#include "Perception/AISense_Sight.h"
#include "VisualLogger/VisualLogger.h"
#include "LBLog.h"

#if !UE_BUILD_SHIPPING
static TAutoConsoleVariable<int32> CVarWardenDebug(
	TEXT("lb.Warden.Debug"), 0,
	TEXT("1 = draw the Warden's state, last-known location, sight cone, move target and last noise. 0 = off."),
	ECVF_Default);
#endif

ULBWardenBrainComponent::ULBWardenBrainComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PrePhysics;
}

// ---------------------------------------------------------------------------------------------------------------------
// Plumbing
// ---------------------------------------------------------------------------------------------------------------------

AAIController* ULBWardenBrainComponent::GetAIController() const
{
	return Cast<AAIController>(GetOwner());
}

ALBWarden* ULBWardenBrainComponent::GetWarden() const
{
	const AAIController* C = GetAIController();
	return C ? Cast<ALBWarden>(C->GetPawn()) : nullptr;
}

const ULBWardenTuningData& ULBWardenBrainComponent::GetTuning() const
{
	const ALBWarden* Warden = GetWarden();
	return Warden ? Warden->GetTuning() : *GetDefault<ULBWardenTuningData>();
}

FVector ULBWardenBrainComponent::GetFeetLocation() const
{
	const ALBWarden* Warden = GetWarden();
	return Warden ? Warden->GetNavAgentLocation() : FVector::ZeroVector;
}

void ULBWardenBrainComponent::BeginPlay()
{
	Super::BeginPlay();
	if (ULBWorldStateSubsystem* WorldState = ULBWorldStateSubsystem::Get(this))
	{
		WorldState->OnStateChanged.AddDynamic(this, &ULBWardenBrainComponent::HandleWorldStateChanged);
		WorldState->OnStateReplaced.AddDynamic(this, &ULBWardenBrainComponent::HandleWorldStateReplaced);
	}
}

void ULBWardenBrainComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (ULBWorldStateSubsystem* WorldState = ULBWorldStateSubsystem::Get(this))
	{
		WorldState->OnStateChanged.RemoveDynamic(this, &ULBWardenBrainComponent::HandleWorldStateChanged);
		WorldState->OnStateReplaced.RemoveDynamic(this, &ULBWardenBrainComponent::HandleWorldStateReplaced);
	}
	Super::EndPlay(EndPlayReason);
}

void ULBWardenBrainComponent::HandleWorldStateChanged(FGameplayTag Tag, bool bAdded)
{
	if (bInitialized)
	{
		RefreshStage();
	}
}

void ULBWardenBrainComponent::HandleWorldStateReplaced()
{
	if (bInitialized)
	{
		RefreshStage();
	}
}

void ULBWardenBrainComponent::Initialize()
{
	bInitialized = true;
	Stuck.StuckSeconds = GetTuning().StuckSeconds;
	Stuck.MinProgress = GetTuning().StuckMinProgress;
	Stuck.ForgiveDistance = GetTuning().StuckForgiveDistance;
	Stage = -1;
	RefreshStage();
	UE_LOG(LogLBWarden, Log, TEXT("%s: brain ready, stage %d"), *GetNameSafe(GetWarden()), Stage);
}

void ULBWardenBrainComponent::RefreshStage()
{
	const ULBWorldStateSubsystem* WorldState = ULBWorldStateSubsystem::Get(this);
	const int32 NewStage = WorldState ? LBWardenLogic::HighestStage(WorldState->GetStateRef()) : 0;
	if (NewStage == Stage)
	{
		return;
	}
	const int32 OldStage = Stage;
	Stage = NewStage;
	Caps = LBWardenLogic::CapsForStage(Stage);
	UE_LOG(LogLBWarden, Log, TEXT("%s: stage %d -> %d (patrol %d, search %d, chase %d)"), *GetNameSafe(GetWarden()), OldStage, Stage,
		Caps.bPatrol, Caps.bSearch, Caps.bChase);

	if (ALBWardenController* WardenController = Cast<ALBWardenController>(GetOwner()))
	{
		WardenController->UpdatePerceptionForStage(Stage);
	}
	// A new stage may mean a different spawn point or route; it is applied the next time the Warden is idle and unseen.
	bRelocationPending = true;
	if (State == ELBWardenState::Patrol)
	{
		bRestartPatrol = true;
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Perception input
// ---------------------------------------------------------------------------------------------------------------------

void ULBWardenBrainComponent::HandleTargetPerceptionUpdated(AActor* Actor, const FAIStimulus& Stimulus)
{
	if (!bInitialized || !Caps.bActive || State == ELBWardenState::Dormant || !Actor)
	{
		return;
	}
	const FAISenseID SightId = UAISense::GetSenseID<UAISense_Sight>();
	const FAISenseID HearingId = UAISense::GetSenseID<UAISense_Hearing>();

	if (Stimulus.Type == SightId)
	{
		ALBCharacter* Player = Cast<ALBCharacter>(Actor);
		if (Player && Player->IsPlayerControlled())
		{
			KnownPlayer = Player;
			UE_VLOG(GetOwner(), LogLBWarden, Verbose, TEXT("sight event: %s %s"), *GetNameSafe(Actor), Stimulus.WasSuccessfullySensed() ? TEXT("gained") : TEXT("lost"));
		}
	}
	else if (Stimulus.Type == HearingId)
	{
		if (Stimulus.WasSuccessfullySensed() && Stimulus.Strength >= GetTuning().HearingLoudnessThreshold)
		{
			bPendingNoise = true;
			NoiseLocation = Stimulus.StimulusLocation;
			NoiseLoudness = Stimulus.Strength;
			NoiseTag = Stimulus.Tag;
			LastNoiseLocation = NoiseLocation;
			LastNoiseTime = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
			UE_LOG(LogLBWarden, Verbose, TEXT("%s: heard '%s' from %s, loudness %.2f"), *GetNameSafe(GetWarden()), *NoiseTag.ToString(), *GetNameSafe(Actor), NoiseLoudness);
			UE_VLOG_LOCATION(GetOwner(), LogLBWarden, Log, NoiseLocation, 30.f, FColor::Magenta, TEXT("noise %s %.2f"), *NoiseTag.ToString(), NoiseLoudness);
		}
	}
}

void ULBWardenBrainComponent::HandleMoveCompleted(FAIRequestID RequestID, EPathFollowingResult::Type Result)
{
	if (bIssuingMove || !bMoveActive || RequestID != CurrentMoveId)
	{
		return;
	}
	bMoveActive = false;
	if (Result == EPathFollowingResult::Success)
	{
		bArrived = true;
	}
	else
	{
		bMoveFailurePending = true;
	}
}

void ULBWardenBrainComponent::PollSight(float DeltaTime)
{
	bool bVisible = false;
	FVector SeenLocation = FVector::ZeroVector;

	const ALBCharacter* Player = KnownPlayer.Get();
	const AAIController* C = GetAIController();
	const UAIPerceptionComponent* Perception = C ? C->GetAIPerceptionComponent() : nullptr;
	if (Caps.bActive && State != ELBWardenState::Dormant && Player && !Player->IsDead() && Perception)
	{
		if (const FActorPerceptionInfo* Info = Perception->GetActorInfo(*Player))
		{
			const FAISenseID SightId = UAISense::GetSenseID<UAISense_Sight>();
			if (Info->LastSensedStimuli.IsValidIndex(SightId))
			{
				const FAIStimulus& Sight = Info->LastSensedStimuli[SightId];
				if (Sight.WasSuccessfullySensed() && Sight.GetAge() < FAIStimulus::NeverHappenedAge)
				{
					// The candle is a light source the Warden can see: a lit candle makes the player visible from further away.
					const ULBCandleComponent* Candle = Player->GetCandle();
					const bool bLit = Candle && Candle->IsLit();
					const ULBWardenTuningData& T = GetTuning();
					const float Radius = LBWardenLogic::EffectiveSightRadius(Stage, bLit, T);
					const float Distance = FVector::Dist(GetFeetLocation(), Sight.StimulusLocation);
					if (LBWardenLogic::IsWithinSightRadius(Distance, bPlayerVisible, Radius, T.LoseSightExtraRadius))
					{
						bVisible = true;
						SeenLocation = Sight.StimulusLocation;
					}
				}
			}
		}
	}

	if (bVisible && !bPlayerVisible)
	{
		UE_LOG(LogLBWarden, Verbose, TEXT("%s: player in sight"), *GetNameSafe(GetWarden()));
	}
	SightConfirm.Advance(bVisible, DeltaTime);
	bPlayerVisible = bVisible;
	if (bVisible)
	{
		LastKnownLocation = SeenLocation;
		bHasLastKnown = true;
		TimeSinceSight = 0.f;
	}
	else
	{
		TimeSinceSight += DeltaTime;
	}
}

void ULBWardenBrainComponent::ClearPerceptionFacts()
{
	SightConfirm.Reset();
	bPlayerVisible = false;
	TimeSinceSight = 0.f;
	bPendingNoise = false;
	bHasLastKnown = false;
	AttackCooldownLeft = 0.f;
	bPlayerUnreachable = false;
	UnreachableTimeLeft = 0.f;
	KnownPlayer.Reset();
}

// ---------------------------------------------------------------------------------------------------------------------
// Tick: gather facts, decide, act
// ---------------------------------------------------------------------------------------------------------------------

void ULBWardenBrainComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

	if (!GetAIController() || !GetWarden())
	{
		return;
	}
	if (!bInitialized)
	{
		Initialize();
	}

	StateTime += DeltaTime;
	AttackCooldownLeft = FMath::Max(0.f, AttackCooldownLeft - DeltaTime);
	if (UnreachableTimeLeft > 0.f)
	{
		UnreachableTimeLeft -= DeltaTime;
		if (UnreachableTimeLeft <= 0.f)
		{
			bPlayerUnreachable = false;
		}
	}

	PollSight(DeltaTime);
	UpdateMaterializeCheck(DeltaTime);

	const FLBWardenFacts Facts = BuildFacts();
	ApplyDecision(LBWardenLogic::Evaluate(State, Facts, GetTuning()));

	TickState(DeltaTime);
	TickMoveStuck(DeltaTime);

	bPendingNoise = false;
#if !UE_BUILD_SHIPPING
	DrawDebug();
#endif
}

FLBWardenFacts ULBWardenBrainComponent::BuildFacts()
{
	const ULBWardenTuningData& T = GetTuning();
	FLBWardenFacts F;
	F.Caps = Caps;
	F.bSeesPlayer = bPlayerVisible;
	F.bSightConfirmed = SightConfirm.IsConfirmed(T.SightConfirmTime);
	F.bNoiseHeard = bPendingNoise;
	F.bArrived = bArrived;
	F.bPlayerUnreachable = bPlayerUnreachable;
	F.bSearchFinished = bSearchFinished;
	F.bCanMaterialize = bCanMaterialize;
	F.StateTime = StateTime;
	F.TimeSinceSight = TimeSinceSight;

	const ALBWarden* Warden = GetWarden();
	const AAIController* C = GetAIController();
	const ALBCharacter* Player = KnownPlayer.Get();
	if (Caps.bActive && Warden && C && Player && !Player->IsDead())
	{
		// Only a player that perception currently reports can be attacked. Range and the eye-level line of sight use the
		// Warden's own body and eyes; the live position is never used once sight is lost.
		const bool bInRange = FVector::Dist(Warden->GetActorLocation(), Player->GetActorLocation()) <= T.AttackRange;
		if (bPlayerVisible && bInRange && AttackCooldownLeft <= 0.f && C->LineOfSightTo(Player))
		{
			F.bInAttackRange = true;
		}
		if (State == ELBWardenState::Attack)
		{
			F.bAttackStillValid = bInRange && C->LineOfSightTo(Player);
		}
	}
	return F;
}

void ULBWardenBrainComponent::UpdateMaterializeCheck(float DeltaTime)
{
	if (State != ELBWardenState::Dormant || !Caps.bActive)
	{
		bCanMaterialize = false;
		MaterializeTimer = 0.f;
		return;
	}
	MaterializeTimer -= DeltaTime;
	if (MaterializeTimer > 0.f)
	{
		return;
	}
	MaterializeTimer = GetTuning().MaterializeRetrySeconds;

	const ALBWarden* Warden = GetWarden();
	const float HalfHeight = Warden->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	FVector Where = Warden->GetActorLocation();
	if (FindSpawn())
	{
		Where = ActiveSpawn->GetActorLocation() + FVector(0.f, 0.f, HalfHeight);
	}
	else if (!bWarnedNoSpawn)
	{
		bWarnedNoSpawn = true;
		UE_LOG(LogLBWarden, Warning, TEXT("%s: no ALBWardenSpawnPoint with MinStage <= %d; appearing where it is placed"), *GetNameSafe(Warden), Stage);
	}
	bCanMaterialize = !IsVisibleToPlayer(Where);
}

void ULBWardenBrainComponent::ApplyDecision(const FLBWardenDecision& Decision)
{
	if (Decision.bKillPlayer)
	{
		KillPlayer();
	}
	if (Decision.Next != State || Decision.bReenter)
	{
		Transition(Decision.Next, Decision.Reason);
	}
}

void ULBWardenBrainComponent::KillPlayer()
{
	if (ALBCharacter* Player = KnownPlayer.Get())
	{
		UE_LOG(LogLBWarden, Log, TEXT("%s: attack landed on %s"), *GetNameSafe(GetWarden()), *GetNameSafe(Player));
		Player->Kill();
	}
}

void ULBWardenBrainComponent::Transition(ELBWardenState NewState, const TCHAR* Reason)
{
	const ELBWardenState OldState = State;
	ExitState(OldState, NewState);

	State = NewState;
	StateTime = 0.f;
	bArrived = false;
	bSearchFinished = false;
	bMoveFailurePending = false;
	Stuck.Reset();
	RepathTimer = 0.f;

	UE_LOG(LogLBWarden, Log, TEXT("%s: %s -> %s (%s) stage=%d lastKnown=%s"), *GetNameSafe(GetWarden()), LBWardenLogic::StateName(OldState),
		LBWardenLogic::StateName(NewState), Reason, Stage, bHasLastKnown ? *LastKnownLocation.ToCompactString() : TEXT("none"));
	UE_VLOG(GetOwner(), LogLBWarden, Log, TEXT("%s -> %s (%s)"), LBWardenLogic::StateName(OldState), LBWardenLogic::StateName(NewState), Reason);

	EnterState(NewState, OldState);
	if (OldState != NewState)
	{
		OnStateChanged.Broadcast(OldState, NewState);
	}
}

void ULBWardenBrainComponent::ExitState(ELBWardenState OldState, ELBWardenState NewState)
{
	if (OldState == ELBWardenState::Attack)
	{
		// A resolved attack always starts the cooldown, so a cancelled attack becomes a chase and not an instant re-attack.
		AttackCooldownLeft = GetTuning().AttackCooldownSeconds;
	}
}

void ULBWardenBrainComponent::EnterState(ELBWardenState NewState, ELBWardenState OldState)
{
	ALBWarden* Warden = GetWarden();
	if (!Warden)
	{
		return;
	}
	const ULBWardenTuningData& T = GetTuning();
	if (UCharacterMovementComponent* Movement = Warden->GetCharacterMovement())
	{
		const float Speed = T.GetMoveSpeed(NewState);
		if (Speed > 0.f)
		{
			Movement->MaxWalkSpeed = Speed;
		}
	}

	switch (NewState)
	{
	case ELBWardenState::Dormant:
		StopMove();
		ClearPerceptionFacts();
		Warden->SetDormantPresentation(true);
		break;

	case ELBWardenState::Patrol:
		if (OldState == ELBWardenState::Dormant)
		{
			ClearPerceptionFacts();
			PlaceAtSpawn();
			PatrolIndex = 0;
		}
		BeginPatrol();
		break;

	case ELBWardenState::Investigate:
		if (bPendingNoise && !bPlayerVisible)
		{
			LastKnownLocation = NoiseLocation;
			bHasLastKnown = true;
		}
		if (!RequestMove(LastKnownLocation))
		{
			OnMoveGaveUp();
		}
		break;

	case ELBWardenState::Suspicious:
		StopMove();
		LookBaseYaw = Warden->GetActorRotation().Yaw;
		break;

	case ELBWardenState::Search:
		StartSearch();
		break;

	case ELBWardenState::Chase:
		if (!RequestMove(LastKnownLocation))
		{
			OnMoveGaveUp();
		}
		else if (bMovePartial)
		{
			SetPlayerUnreachable();
		}
		break;

	case ELBWardenState::Attack:
		StopMove();
		OnAttackWindup.Broadcast(T.AttackWindupSeconds);
		break;

	case ELBWardenState::Return:
	{
		const FVector Target = ChooseReturnTarget();
		if (!RequestMove(Target))
		{
			OnMoveGaveUp();
		}
		break;
	}
	}
}

void ULBWardenBrainComponent::TickState(float DeltaTime)
{
	const ULBWardenTuningData& T = GetTuning();
	const ALBWarden* Warden = GetWarden();
	if (!Warden)
	{
		return;
	}

	switch (State)
	{
	case ELBWardenState::Patrol:
		TickPatrol(DeltaTime);
		break;

	case ELBWardenState::Investigate:
		// A visible target keeps moving: follow its refreshed location.
		if (bPlayerVisible)
		{
			RepathTimer -= DeltaTime;
			if (RepathTimer <= 0.f && FVector::Dist(MoveTarget, LastKnownLocation) >= T.RepathMinDistance)
			{
				RepathTimer = T.RepathIntervalSeconds;
				if (!RequestMove(LastKnownLocation))
				{
					OnMoveGaveUp();
				}
			}
		}
		break;

	case ELBWardenState::Suspicious:
		LookAround(DeltaTime, StateTime, FMath::Max(T.SuspiciousSeconds, 0.1f));
		break;

	case ELBWardenState::Search:
		TickSearch(DeltaTime);
		break;

	case ELBWardenState::Chase:
		if (bPlayerVisible)
		{
			RepathTimer -= DeltaTime;
			if (!bPlayerUnreachable && RepathTimer <= 0.f
				&& (!bMoveActive || FVector::Dist(MoveTarget, LastKnownLocation) >= T.RepathMinDistance))
			{
				RepathTimer = T.RepathIntervalSeconds;
				if (!RequestMove(LastKnownLocation))
				{
					OnMoveGaveUp();
				}
				else if (bMovePartial)
				{
					SetPlayerUnreachable();
				}
			}
		}
		else
		{
			// Sight lost: follow the memory, and any fresh noise, never the live player.
			if (bPendingNoise)
			{
				LastKnownLocation = NoiseLocation;
				bHasLastKnown = true;
				if (!RequestMove(LastKnownLocation))
				{
					OnMoveGaveUp();
				}
			}
			else if (!bMoveActive)
			{
				LookAround(DeltaTime, StateTime, FMath::Max(T.LastKnownMemorySeconds, 0.1f));
			}
		}
		break;

	case ELBWardenState::Attack:
		// Stand and face the last place the player was seen.
		if (bHasLastKnown)
		{
			FaceLocation(DeltaTime, LastKnownLocation);
		}
		break;

	case ELBWardenState::Return:
	case ELBWardenState::Dormant:
	default:
		break;
	}
}

void ULBWardenBrainComponent::TickMoveStuck(float DeltaTime)
{
	const ALBWarden* Warden = GetWarden();
	if (!Warden)
	{
		return;
	}
	if (!bMoveActive && !bMoveFailurePending)
	{
		Stuck.Pause();
		return;
	}

	ELBStuckResult Result = ELBStuckResult::None;
	if (bMoveFailurePending)
	{
		bMoveFailurePending = false;
		Result = Stuck.RegisterFailure(Warden->GetActorLocation());
	}
	else
	{
		Result = Stuck.Update(DeltaTime, Warden->GetActorLocation());
	}

	if (Result == ELBStuckResult::Repath)
	{
		UE_LOG(LogLBWarden, Log, TEXT("%s: stuck in %s, re-pathing to %s"), *GetNameSafe(Warden), LBWardenLogic::StateName(State), *MoveTarget.ToCompactString());
		UE_VLOG(GetOwner(), LogLBWarden, Log, TEXT("stuck: repath"));
		if (!RequestMove(MoveTarget))
		{
			OnMoveGaveUp();
		}
	}
	else if (Result == ELBStuckResult::GiveUp)
	{
		UE_LOG(LogLBWarden, Log, TEXT("%s: stuck again in %s, giving this target up"), *GetNameSafe(Warden), LBWardenLogic::StateName(State));
		UE_VLOG(GetOwner(), LogLBWarden, Log, TEXT("stuck: give up"));
		Stuck.Reset();
		OnMoveGaveUp();
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Movement
// ---------------------------------------------------------------------------------------------------------------------

bool ULBWardenBrainComponent::RequestMove(const FVector& Destination)
{
	AAIController* C = GetAIController();
	if (!C)
	{
		return false;
	}
	const ULBWardenTuningData& T = GetTuning();

	bArrived = false;
	bMoveActive = false;
	bMovePartial = false;
	bMoveFailurePending = false;
	MoveTarget = Destination;

	TGuardValue<bool> Guard(bIssuingMove, true);

	FAIMoveRequest Request(Destination);
	Request.SetAcceptanceRadius(T.ArrivalRadius);
	Request.SetAllowPartialPath(true);
	Request.SetUsePathfinding(true);
	Request.SetProjectGoalLocation(true);
	Request.SetCanStrafe(false);

	FNavPathSharedPtr Path;
	FPathFollowingRequestResult Result = C->MoveTo(Request, &Path);
	if (Result.Code == EPathFollowingRequestResult::Failed)
	{
		// The goal is off the navmesh (or too far from it): walk to the closest navigable point instead.
		UNavigationSystemV1* NavSys = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
		FNavLocation Projected;
		const float R = T.UnreachableFallbackRadius;
		if (NavSys && NavSys->ProjectPointToNavigation(Destination, Projected, FVector(R, R, R)))
		{
			bMovePartial = true;
			Request.SetGoalLocation(Projected.Location);
			Path.Reset();
			Result = C->MoveTo(Request, &Path);
		}
	}

	if (Result.Code == EPathFollowingRequestResult::AlreadyAtGoal)
	{
		bArrived = true;
		return true;
	}
	if (Result.Code == EPathFollowingRequestResult::RequestSuccessful)
	{
		CurrentMoveId = Result.MoveId;
		bMoveActive = true;
		if (Path.IsValid() && Path->IsPartial())
		{
			bMovePartial = true;
		}
		return true;
	}
	bMovePartial = true;
	UE_LOG(LogLBWarden, Log, TEXT("%s: no path to %s"), *GetNameSafe(GetWarden()), *Destination.ToCompactString());
	return false;
}

void ULBWardenBrainComponent::StopMove()
{
	if (AAIController* C = GetAIController())
	{
		TGuardValue<bool> Guard(bIssuingMove, true);
		C->StopMovement();
	}
	bMoveActive = false;
	bMoveFailurePending = false;
}

void ULBWardenBrainComponent::OnMoveGaveUp()
{
	StopMove();
	switch (State)
	{
	case ELBWardenState::Patrol:
		AdvancePatrol();
		break;
	case ELBWardenState::Search:
		SearchPlan.MarkVisited(CurrentSearchIndex);
		NextSearchPoint();
		break;
	case ELBWardenState::Chase:
		// Cannot get to the player: treat the spot as the closest we can reach, then search from there.
		SetPlayerUnreachable();
		bArrived = true;
		break;
	case ELBWardenState::Investigate:
	case ELBWardenState::Return:
		bArrived = true;
		break;
	default:
		break;
	}
}

void ULBWardenBrainComponent::SetPlayerUnreachable()
{
	if (!bPlayerUnreachable)
	{
		UE_LOG(LogLBWarden, Log, TEXT("%s: player unreachable, going to the closest reachable point"), *GetNameSafe(GetWarden()));
		UE_VLOG(GetOwner(), LogLBWarden, Log, TEXT("player unreachable"));
	}
	bPlayerUnreachable = true;
	UnreachableTimeLeft = GetTuning().UnreachableRecheckSeconds;
}

void ULBWardenBrainComponent::FaceYaw(float DeltaTime, float TargetYaw)
{
	if (ALBWarden* Warden = GetWarden())
	{
		FRotator Rotation = Warden->GetActorRotation();
		Rotation.Yaw = FMath::FixedTurn(Rotation.Yaw, TargetYaw, GetTuning().TurnRate * DeltaTime);
		Warden->SetActorRotation(Rotation);
	}
}

void ULBWardenBrainComponent::FaceLocation(float DeltaTime, const FVector& Target)
{
	if (const ALBWarden* Warden = GetWarden())
	{
		const FVector To = Target - Warden->GetActorLocation();
		if (To.SizeSquared2D() > UE_KINDA_SMALL_NUMBER)
		{
			FaceYaw(DeltaTime, To.Rotation().Yaw);
		}
	}
}

void ULBWardenBrainComponent::LookAround(float DeltaTime, float Elapsed, float Period)
{
	// One full left-right sweep over Period, centred on the heading the Warden stopped with.
	const float Phase = 2.f * PI * Elapsed / Period;
	FaceYaw(DeltaTime, LookBaseYaw + GetTuning().LookAroundHalfAngle * FMath::Sin(Phase));
}

// ---------------------------------------------------------------------------------------------------------------------
// Spawn point, teleport, visibility to the player
// ---------------------------------------------------------------------------------------------------------------------

bool ULBWardenBrainComponent::FindSpawn()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return false;
	}
	TArray<ALBWardenSpawnPoint*> Spawns;
	TArray<int32> MinStages;
	for (TActorIterator<ALBWardenSpawnPoint> It(World); It; ++It)
	{
		Spawns.Add(*It);
		MinStages.Add(It->MinStage);
	}
	const int32 Index = LBWardenLogic::SelectSpawnIndex(MinStages, Stage);
	if (Index == INDEX_NONE)
	{
		ActiveSpawn.Reset();
		return false;
	}
	ActiveSpawn = Spawns[Index];
	return true;
}

bool ULBWardenBrainComponent::IsVisibleToPlayer(const FVector& CenterLocation) const
{
	const UWorld* World = GetWorld();
	const ALBWarden* Warden = GetWarden();
	const APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	if (!World || !Warden || !PC || !PC->GetPawn())
	{
		return false;
	}
	FVector CameraLocation;
	FRotator CameraRotation;
	PC->GetPlayerViewPoint(CameraLocation, CameraRotation);
	const FVector Forward = CameraRotation.Vector();
	const float HalfAngle = GetTuning().PlayerViewHalfAngle;
	const float HalfHeight = Warden->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();

	FCollisionQueryParams Params(SCENE_QUERY_STAT(LBWardenVisible), false);
	Params.AddIgnoredActor(PC->GetPawn());
	Params.AddIgnoredActor(Warden);

	const FVector Samples[] = {
		CenterLocation - FVector(0.f, 0.f, HalfHeight - 10.f),
		CenterLocation,
		CenterLocation + FVector(0.f, 0.f, HalfHeight - 10.f) };
	for (const FVector& Sample : Samples)
	{
		if (LBWardenLogic::IsInsideViewCone(CameraLocation, Forward, Sample, HalfAngle)
			&& !World->LineTraceTestByChannel(CameraLocation, Sample, ECC_Visibility, Params))
		{
			return true;
		}
	}
	return false;
}

void ULBWardenBrainComponent::PlaceAtSpawn()
{
	ALBWarden* Warden = GetWarden();
	if (!Warden)
	{
		return;
	}
	const float HalfHeight = Warden->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	if (FindSpawn())
	{
		const ALBWardenSpawnPoint* Spawn = ActiveSpawn.Get();
		HomeLocation = Spawn->GetActorLocation();
		HomeRotation = FRotator(0.f, Spawn->GetActorRotation().Yaw, 0.f);
		RouteId = Spawn->RouteId;
		Warden->SetActorLocationAndRotation(HomeLocation + FVector(0.f, 0.f, HalfHeight), HomeRotation, false, nullptr, ETeleportType::TeleportPhysics);
	}
	else
	{
		HomeLocation = Warden->GetNavAgentLocation();
		HomeRotation = Warden->GetActorRotation();
		RouteId = NAME_None;
	}
	bHasHome = true;
	bRelocationPending = false;
	Warden->SetDormantPresentation(false);
	RebuildRoute();
	UE_LOG(LogLBWarden, Log, TEXT("%s: appears at %s (route '%s')"), *GetNameSafe(Warden), *HomeLocation.ToCompactString(), *RouteId.ToString());
}

void ULBWardenBrainComponent::TryRelocate()
{
	if (!bRelocationPending)
	{
		return;
	}
	ALBWarden* Warden = GetWarden();
	if (!Warden || !FindSpawn())
	{
		bRelocationPending = false;
		return;
	}
	const ALBWardenSpawnPoint* Spawn = ActiveSpawn.Get();
	const FVector NewHome = Spawn->GetActorLocation();
	const FName NewRoute = Spawn->RouteId;
	if (bHasHome && NewHome.Equals(HomeLocation, 1.f) && NewRoute == RouteId)
	{
		bRelocationPending = false;
		return;
	}

	const float HalfHeight = Warden->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	const FVector Destination = NewHome + FVector(0.f, 0.f, HalfHeight);
	if (IsVisibleToPlayer(Warden->GetActorLocation()) || IsVisibleToPlayer(Destination))
	{
		// Seen, or the destination is seen: no teleport. Walk there instead.
		bRelocationPending = false;
		HomeLocation = NewHome;
		HomeRotation = FRotator(0.f, Spawn->GetActorRotation().Yaw, 0.f);
		RouteId = NewRoute;
		RebuildRoute();
		UE_LOG(LogLBWarden, Log, TEXT("%s: new spawn %s is in view or the Warden is, walking there"), *GetNameSafe(Warden), *NewHome.ToCompactString());
		Transition(ELBWardenState::Return, TEXT("new stage spawn, walking"));
		return;
	}

	StopMove();
	HomeLocation = NewHome;
	HomeRotation = FRotator(0.f, Spawn->GetActorRotation().Yaw, 0.f);
	RouteId = NewRoute;
	bRelocationPending = false;
	Warden->SetActorLocationAndRotation(Destination, HomeRotation, false, nullptr, ETeleportType::TeleportPhysics);
	RebuildRoute();
	PatrolIndex = 0;
	UE_LOG(LogLBWarden, Log, TEXT("%s: relocated unseen to spawn %s (route '%s')"), *GetNameSafe(Warden), *NewHome.ToCompactString(), *RouteId.ToString());
	bRestartPatrol = true;
}

// ---------------------------------------------------------------------------------------------------------------------
// Patrol and return
// ---------------------------------------------------------------------------------------------------------------------

void ULBWardenBrainComponent::RebuildRoute()
{
	RoutePoints.Reset();
	RouteWaits.Reset();
	UWorld* World = GetWorld();
	if (!World || RouteId.IsNone())
	{
		return;
	}
	TArray<const ALBPatrolPoint*> Points;
	for (TActorIterator<ALBPatrolPoint> It(World); It; ++It)
	{
		if (It->RouteId == RouteId)
		{
			Points.Add(*It);
		}
	}
	Points.StableSort([](const ALBPatrolPoint& A, const ALBPatrolPoint& B) { return A.Order < B.Order; });
	for (const ALBPatrolPoint* Point : Points)
	{
		RoutePoints.Add(Point->GetActorLocation());
		RouteWaits.Add(Point->WaitSeconds);
	}
}

void ULBWardenBrainComponent::BeginPatrol()
{
	bRestartPatrol = false;
	if (Caps.bPatrol && RoutePoints.Num() > 0)
	{
		PatrolIndex = FMath::Clamp(PatrolIndex, 0, RoutePoints.Num() - 1);
		StartPatrolMove();
		return;
	}
	// Hold the post: walk back to it if displaced, then stand.
	PatrolPhase = EPatrolPhase::Moving;
	if (!RequestMove(bHasHome ? HomeLocation : GetFeetLocation()))
	{
		PatrolPhase = EPatrolPhase::Holding;
		bArrived = false;
	}
}

void ULBWardenBrainComponent::StartPatrolMove()
{
	PatrolPhase = EPatrolPhase::Moving;
	if (!RequestMove(RoutePoints[PatrolIndex]))
	{
		// Unreachable point: pause briefly at the current spot so a broken route cannot spin every frame.
		PatrolPhase = EPatrolPhase::Waiting;
		PatrolWaitLeft = 1.f;
	}
}

void ULBWardenBrainComponent::AdvancePatrol()
{
	if (Caps.bPatrol && RoutePoints.Num() > 0)
	{
		PatrolIndex = (PatrolIndex + 1) % RoutePoints.Num();
		StartPatrolMove();
	}
	else
	{
		PatrolPhase = EPatrolPhase::Holding;
	}
}

void ULBWardenBrainComponent::TickPatrol(float DeltaTime)
{
	if (bRestartPatrol)
	{
		StopMove();
		BeginPatrol();
	}
	const bool bRoute = Caps.bPatrol && RoutePoints.Num() > 0;

	switch (PatrolPhase)
	{
	case EPatrolPhase::Moving:
		if (bArrived)
		{
			bArrived = false;
			if (bRoute)
			{
				PatrolPhase = EPatrolPhase::Waiting;
				PatrolWaitLeft = RouteWaits.IsValidIndex(PatrolIndex) ? RouteWaits[PatrolIndex] : 0.f;
			}
			else
			{
				PatrolPhase = EPatrolPhase::Holding;
			}
		}
		break;

	case EPatrolPhase::Waiting:
		TryRelocate();
		if (State != ELBWardenState::Patrol)
		{
			return;
		}
		PatrolWaitLeft -= DeltaTime;
		if (PatrolWaitLeft <= 0.f)
		{
			AdvancePatrol();
		}
		break;

	case EPatrolPhase::Holding:
		TryRelocate();
		if (State == ELBWardenState::Patrol && bHasHome)
		{
			// Settle into the heading the spawn point faces.
			FaceYaw(DeltaTime, HomeRotation.Yaw);
		}
		break;
	}
}

FVector ULBWardenBrainComponent::ChooseReturnTarget()
{
	if (Caps.bPatrol && RoutePoints.Num() > 0)
	{
		const FVector From = GetFeetLocation();
		int32 Best = 0;
		double BestDistSq = TNumericLimits<double>::Max();
		for (int32 i = 0; i < RoutePoints.Num(); ++i)
		{
			const double DistSq = FVector::DistSquared(RoutePoints[i], From);
			if (DistSq < BestDistSq)
			{
				BestDistSq = DistSq;
				Best = i;
			}
		}
		PatrolIndex = Best;
		return RoutePoints[Best];
	}
	return bHasHome ? HomeLocation : GetFeetLocation();
}

// ---------------------------------------------------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------------------------------------------------

void ULBWardenBrainComponent::StartSearch()
{
	const ULBWardenTuningData& T = GetTuning();
	StopMove();
	bSearchPausing = false;
	CurrentSearchIndex = INDEX_NONE;

	TArray<FVector> Candidates;
	if (UWorld* World = GetWorld())
	{
		for (TActorIterator<ALBSearchPoint> It(World); It; ++It)
		{
			Candidates.Add(It->GetActorLocation());
		}
	}
	SearchPlan.Build(Candidates, LastKnownLocation, T.SearchPointRadius, T.SearchPointCount);

	if (SearchPlan.Points.Num() == 0)
	{
		// No designer points near the stimulus: use random reachable spots around it (a nav query, not EQS).
		if (UNavigationSystemV1* NavSys = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()))
		{
			TArray<FVector> Fallback;
			for (int32 i = 0; i < T.SearchPointCount; ++i)
			{
				FNavLocation Random;
				if (NavSys->GetRandomReachablePointInRadius(LastKnownLocation, T.SearchFallbackRadius, Random))
				{
					Fallback.Add(Random.Location);
				}
			}
			SearchPlan.Build(Fallback, LastKnownLocation, T.SearchFallbackRadius * 2.f, T.SearchPointCount);
		}
	}
	UE_LOG(LogLBWarden, Log, TEXT("%s: searching around %s with %d point(s)"), *GetNameSafe(GetWarden()), *LastKnownLocation.ToCompactString(), SearchPlan.Points.Num());
	NextSearchPoint();
}

void ULBWardenBrainComponent::NextSearchPoint()
{
	bSearchPausing = false;
	// Bounded: every failed point is marked visited, so this ends when the plan runs out.
	for (int32 Guard = 0; Guard <= SearchPlan.Points.Num(); ++Guard)
	{
		const int32 Next = SearchPlan.PickNext(GetFeetLocation());
		if (Next == INDEX_NONE)
		{
			CurrentSearchIndex = INDEX_NONE;
			bSearchFinished = true;
			return;
		}
		CurrentSearchIndex = Next;
		if (RequestMove(SearchPlan.Points[Next]))
		{
			return;
		}
		SearchPlan.MarkVisited(Next);
	}
	bSearchFinished = true;
}

void ULBWardenBrainComponent::TickSearch(float DeltaTime)
{
	const ULBWardenTuningData& T = GetTuning();
	if (bSearchFinished)
	{
		return;
	}
	if (bSearchPausing)
	{
		SearchPauseElapsed += DeltaTime;
		LookAround(DeltaTime, SearchPauseElapsed, FMath::Max(T.SearchPointPauseSeconds, 0.1f));
		if (SearchPauseElapsed >= T.SearchPointPauseSeconds)
		{
			SearchPlan.MarkVisited(CurrentSearchIndex);
			NextSearchPoint();
		}
		return;
	}
	if (bArrived)
	{
		bArrived = false;
		bSearchPausing = true;
		SearchPauseElapsed = 0.f;
		if (const ALBWarden* Warden = GetWarden())
		{
			LookBaseYaw = Warden->GetActorRotation().Yaw;
		}
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Debug
// ---------------------------------------------------------------------------------------------------------------------

void ULBWardenBrainComponent::DrawDebug() const
{
#if !UE_BUILD_SHIPPING
	if (CVarWardenDebug.GetValueOnGameThread() <= 0)
	{
		return;
	}
	const UWorld* World = GetWorld();
	const ALBWarden* Warden = GetWarden();
	if (!World || !Warden || Warden->IsDormantPresentation())
	{
		return;
	}
	const ULBWardenTuningData& T = GetTuning();

	FColor Color = FColor::White;
	switch (State)
	{
	case ELBWardenState::Investigate: case ELBWardenState::Suspicious: Color = FColor::Yellow; break;
	case ELBWardenState::Search: Color = FColor::Orange; break;
	case ELBWardenState::Chase: case ELBWardenState::Attack: Color = FColor::Red; break;
	case ELBWardenState::Return: Color = FColor::Cyan; break;
	default: break;
	}

	const float HalfHeight = Warden->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	const FVector Head = Warden->GetActorLocation() + FVector(0.f, 0.f, HalfHeight + 30.f);
	FString Text = FString::Printf(TEXT("%s%s  stage %d"), LBWardenLogic::StateName(State), IsHoldingPost() ? TEXT(" (post)") : TEXT(""), Stage);
	if (bPlayerVisible)
	{
		Text += FString::Printf(TEXT("  SEES %.1f/%.1fs"), SightConfirm.Continuous, T.SightConfirmTime);
	}
	else if (State == ELBWardenState::Chase)
	{
		Text += FString::Printf(TEXT("  lost %.1f/%.1fs"), TimeSinceSight, T.LastKnownMemorySeconds);
	}
	if (bPlayerUnreachable)
	{
		Text += TEXT("  UNREACHABLE");
	}
	DrawDebugString(World, Head, Text, nullptr, Color, 0.f, true, 1.2f);

	// Sight cone: the unlit radius solid, the candle-lit radius (a longer cone) in orange.
	FVector EyeLocation;
	FRotator EyeRotation;
	Warden->GetActorEyesViewPoint(EyeLocation, EyeRotation);
	EyeRotation = Warden->GetActorRotation();
	const float BaseRadius = T.GetSightRadiusForStage(Stage);
	const float HalfAngleRad = FMath::DegreesToRadians(T.PeripheralHalfAngle);
	DrawDebugCone(World, EyeLocation, EyeRotation.Vector(), BaseRadius, HalfAngleRad, HalfAngleRad, 12, Color, false, 0.f, 0, 1.f);
	DrawDebugCone(World, EyeLocation, EyeRotation.Vector(), BaseRadius * T.CandleLitSightMultiplier, HalfAngleRad, HalfAngleRad, 4, FColor::Orange, false, 0.f, 0, 0.5f);

	if (bHasLastKnown)
	{
		DrawDebugSphere(World, LastKnownLocation, 25.f, 8, FColor::Yellow, false, 0.f, 0, 2.f);
		DrawDebugLine(World, Warden->GetActorLocation(), LastKnownLocation, FColor::Yellow, false, 0.f, 0, 0.5f);
		DrawDebugString(World, LastKnownLocation + FVector(0.f, 0.f, 40.f), TEXT("last known"), nullptr, FColor::Yellow, 0.f, true, 1.f);
	}
	if (bMoveActive)
	{
		DrawDebugSphere(World, MoveTarget, 20.f, 6, FColor::Cyan, false, 0.f, 0, 2.f);
		DrawDebugLine(World, Warden->GetActorLocation(), MoveTarget, FColor::Cyan, false, 0.f, 0, 1.f);
	}
	if (World->GetTimeSeconds() - LastNoiseTime < 2.0)
	{
		DrawDebugSphere(World, LastNoiseLocation, 30.f, 8, FColor::Magenta, false, 0.f, 0, 1.5f);
	}
#endif
}
