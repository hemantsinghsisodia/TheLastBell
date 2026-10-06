#pragma once

#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"

class AActor;
class ALBCharacter;
class UWorld;
class ULBInteractableComponent;
class ALBCheckpoint;

/** Helpers for tests that drive a PIE session. */
namespace LBPie
{
	UWorld* World();
	ALBCharacter* Pawn();
	/** Begun play, pawn possessed, objective subsystem present. */
	bool WorldReady();
	int32 ObjIndex();
	bool HasState(const FGameplayTag& Tag);
	FGameplayTag Tag(const TCHAR* Name);
	FString MapShortName();
	void Teleport(const FVector& Location, const FRotator& Rotation);
	void ClearSlot();
}

/**
 * Generic objective-driven route bot. Call Tick() once per frame. It reads the active objective, finds an actor that
 * provides each missing completion tag (interactable, tag trigger, or auto-open door), moves the pawn there and uses it.
 * A tag with no provider is reported as a soft lock.
 */
class FLBRouteBot
{
public:
	enum class EStatus { Running, Done, Failed };

	struct FConfig
	{
		/** Stop (Done) once this objective index is active. Unset = run until all objectives are complete. */
		TOptional<int32> StopAtIndex;
		float ActionTimeout = 5.f;
		float ObjectiveTimeout = 60.f;
		float CheckpointRadius = 600.f;
	};

	FLBRouteBot(FAutomationTestBase* InTest, const FConfig& InConfig);

	EStatus Tick();

private:
	enum class EKind { Interactable, Trigger, Door };
	enum class EPhase { Plan, Act, Checkpoints };

	struct FAction
	{
		TWeakObjectPtr<AActor> Actor;
		EKind Kind = EKind::Interactable;
		FGameplayTag WaitTag;
		bool bPending = false; // door already told to open: just wait
	};

	// planning
	bool Resolve(const FGameplayTag& Need, int32 Depth, TArray<FGameplayTag>& Stack, FAction& Out) const;
	bool ResolveInteractable(const FGameplayTag& Need, int32 Depth, TArray<FGameplayTag>& Stack, FAction& Out) const;
	bool ResolveTrigger(const FGameplayTag& Need, FAction& Out) const;
	bool ResolveDoor(const FGameplayTag& Need, int32 Depth, TArray<FGameplayTag>& Stack, FAction& Out) const;
	FGameplayTag FirstMissingTag() const;
	bool IsFailed(const AActor* Actor, const FGameplayTag& Tag) const;

	// execution
	EStatus TickPlan();
	EStatus TickAct();
	EStatus TickCheckpoints();
	void BeginAttempt();
	bool PlaceForInteractable(const AActor* Target, int32 Attempt, FVector& OutPawnLoc) const;
	bool StandPointInBounds(const AActor* Target, FVector& OutPawnLoc) const;
	bool FindFloor(const FVector& From, float Depth, float& OutZ) const;
	FVector ReferencePointFor(const FVector& Location) const;
	void AimAt(const FVector& Point) const;
	void QueueCheckpoints(const FVector& Near);
	void FinishAction(bool bOk);
	EStatus Fail(const FString& Message);
	void ResetForNewWorld();
	FString ObjectiveText() const;
	FString ActionLabel() const;

	FAutomationTestBase* Test;
	FConfig Config;
	TWeakObjectPtr<UWorld> BotWorld;

	EPhase Phase = EPhase::Plan;
	int32 CurObjective = -999;
	double ObjectiveStart = 0.0;
	TSet<FString> FailedProviders;

	FAction Action;
	double ActionStart = 0.0;
	int32 Attempt = -1;
	int32 AttemptFrames = 0;
	double AttemptStart = 0.0;
	int32 FiredCount = 0;
	FVector ActionLocation = FVector::ZeroVector;

	TArray<TWeakObjectPtr<ALBCheckpoint>> PendingCheckpoints;
	double CheckpointStart = 0.0;
	bool bCheckpointEntered = false;
	int32 PlanWaitFrames = 0;
};

#endif
