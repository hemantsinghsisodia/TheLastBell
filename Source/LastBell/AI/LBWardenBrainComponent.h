#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "AIController.h"
#include "Navigation/PathFollowingComponent.h"
#include "Perception/AIPerceptionTypes.h"
#include "AI/LBWardenTypes.h"
#include "AI/LBWardenLogic.h"
#include "LBWardenBrainComponent.generated.h"

class ALBCharacter;
class ALBWarden;
class ALBWardenSpawnPoint;
class ULBWardenTuningData;
class ULBWorldStateSubsystem;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FLBWardenStateChangedSignature, ELBWardenState, OldState, ELBWardenState, NewState);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FLBWardenAttackWindupSignature, float, WindupSeconds);

/**
 * The Warden's brain (D-037): a C++ state machine on the AI controller. Why the controller and not the pawn: the controller
 * already owns perception and path following, survives a re-possession, and the checkpoint rule finds it through the world's
 * controller list without a manager actor.
 *
 * It learns about the player ONLY from perception: sight events (polled for the refreshed location while visible) and noise
 * events. After sight is lost it uses the remembered last-known location, never the live player position. The decisions are
 * made by LBWardenLogic::Evaluate (pure, unit tested); this class gathers the facts and performs the actions.
 */
UCLASS(ClassGroup = "LastBell", meta = (BlueprintSpawnableComponent))
class LASTBELL_API ULBWardenBrainComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	ULBWardenBrainComponent();

	UFUNCTION(BlueprintPure, Category = "LastBell|Warden")
	ELBWardenState GetState() const { return State; }

	UFUNCTION(BlueprintPure, Category = "LastBell|Warden")
	FVector GetLastKnownLocation() const { return LastKnownLocation; }

	UFUNCTION(BlueprintPure, Category = "LastBell|Warden")
	bool HasLastKnownLocation() const { return bHasLastKnown; }

	/** Highest State.Warden.Stage.N currently set (0 = none). */
	UFUNCTION(BlueprintPure, Category = "LastBell|Warden")
	int32 GetStage() const { return Stage; }

	/** True in Chase and Attack: checkpoints refuse to save (D-019). */
	UFUNCTION(BlueprintPure, Category = "LastBell|Warden")
	bool IsChasingOrAttacking() const { return State == ELBWardenState::Chase || State == ELBWardenState::Attack; }

	/** Patrol state without a route (stage 3, or no ALBPatrolPoint on the spawn's RouteId): standing at the post. */
	UFUNCTION(BlueprintPure, Category = "LastBell|Warden")
	bool IsHoldingPost() const { return State == ELBWardenState::Patrol && PatrolPhase == EPatrolPhase::Holding; }

	/** Fired after every state change. OldState differs from NewState. */
	UPROPERTY(BlueprintAssignable, Category = "LastBell|Warden")
	FLBWardenStateChangedSignature OnStateChanged;

	/** Fired when an attack starts: play the tell (growl, chain rattle, wind-up animation). The kill lands after WindupSeconds. */
	UPROPERTY(BlueprintAssignable, Category = "LastBell|Warden")
	FLBWardenAttackWindupSignature OnAttackWindup;

	// ---- Called by ALBWardenController ----
	void HandleTargetPerceptionUpdated(AActor* Actor, const FAIStimulus& Stimulus);
	void HandleMoveCompleted(FAIRequestID RequestID, EPathFollowingResult::Type Result);

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	enum class EPatrolPhase : uint8 { Holding, Moving, Waiting };

	UFUNCTION()
	void HandleWorldStateChanged(FGameplayTag Tag, bool bAdded);
	UFUNCTION()
	void HandleWorldStateReplaced();

	// ---- Plumbing ----
	AAIController* GetAIController() const;
	ALBWarden* GetWarden() const;
	const ULBWardenTuningData& GetTuning() const;
	void Initialize();
	void RefreshStage();

	// ---- Per frame ----
	void PollSight(float DeltaTime);
	FLBWardenFacts BuildFacts();
	void UpdateMaterializeCheck(float DeltaTime);
	void TickState(float DeltaTime);
	void TickMoveStuck(float DeltaTime);

	// ---- Transitions ----
	void ApplyDecision(const FLBWardenDecision& Decision);
	void Transition(ELBWardenState NewState, const TCHAR* Reason);
	void EnterState(ELBWardenState NewState, ELBWardenState OldState);
	void ExitState(ELBWardenState OldState, ELBWardenState NewState);
	void KillPlayer();

	// ---- Movement ----
	bool RequestMove(const FVector& Destination);
	void StopMove();
	void OnMoveGaveUp();
	void SetPlayerUnreachable();
	void FaceYaw(float DeltaTime, float TargetYaw);
	void FaceLocation(float DeltaTime, const FVector& Target);
	void LookAround(float DeltaTime, float Elapsed, float Period);
	FVector GetFeetLocation() const;

	// ---- Spawn / patrol / search ----
	bool FindSpawn();
	bool IsVisibleToPlayer(const FVector& CenterLocation) const;
	void PlaceAtSpawn();
	void TryRelocate();
	void RebuildRoute();
	void BeginPatrol();
	void StartPatrolMove();
	void AdvancePatrol();
	void TickPatrol(float DeltaTime);
	FVector ChooseReturnTarget();
	void StartSearch();
	void NextSearchPoint();
	void TickSearch(float DeltaTime);

	void ClearPerceptionFacts();
	void DrawDebug() const;

	// ---- State ----
	ELBWardenState State = ELBWardenState::Dormant;
	float StateTime = 0.f;
	int32 Stage = 0;
	FLBWardenCaps Caps;
	bool bInitialized = false;

	// ---- What perception told us ----
	TWeakObjectPtr<ALBCharacter> KnownPlayer;
	FLBSightConfirm SightConfirm;
	bool bPlayerVisible = false;
	float TimeSinceSight = 0.f;
	FVector LastKnownLocation = FVector::ZeroVector;
	bool bHasLastKnown = false;
	bool bPendingNoise = false;
	FVector NoiseLocation = FVector::ZeroVector;
	float NoiseLoudness = 0.f;
	FName NoiseTag;
	FVector LastNoiseLocation = FVector::ZeroVector;
	double LastNoiseTime = -1000.0;

	// ---- Attack / unreachable ----
	float AttackCooldownLeft = 0.f;
	bool bPlayerUnreachable = false;
	float UnreachableTimeLeft = 0.f;

	// ---- Movement ----
	FAIRequestID CurrentMoveId;
	bool bMoveActive = false;
	bool bIssuingMove = false;
	bool bArrived = false;
	bool bMovePartial = false;
	bool bMoveFailurePending = false;
	FVector MoveTarget = FVector::ZeroVector;
	float RepathTimer = 0.f;
	FLBStuckDetector Stuck;

	// ---- Spawn / route ----
	TWeakObjectPtr<ALBWardenSpawnPoint> ActiveSpawn;
	FVector HomeLocation = FVector::ZeroVector;
	FRotator HomeRotation = FRotator::ZeroRotator;
	bool bHasHome = false;
	FName RouteId;
	bool bRelocationPending = false;
	bool bRestartPatrol = false;
	bool bCanMaterialize = false;
	float MaterializeTimer = 0.f;
	bool bWarnedNoSpawn = false;

	TArray<FVector> RoutePoints;
	TArray<float> RouteWaits;
	int32 PatrolIndex = 0;
	EPatrolPhase PatrolPhase = EPatrolPhase::Holding;
	float PatrolWaitLeft = 0.f;

	// ---- Search / look-around ----
	FLBSearchPlan SearchPlan;
	int32 CurrentSearchIndex = INDEX_NONE;
	bool bSearchFinished = false;
	bool bSearchPausing = false;
	float SearchPauseElapsed = 0.f;
	float LookBaseYaw = 0.f;
};
