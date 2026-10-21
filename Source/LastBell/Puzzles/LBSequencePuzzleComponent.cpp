#include "Puzzles/LBSequencePuzzleComponent.h"
#include "Puzzles/LBPuzzleLogic.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "Engine/World.h"
#include "TimerManager.h"
#include "LBLog.h"

void ULBSequencePuzzleComponent::BeginPlay()
{
	Super::BeginPlay();

	ULBWorldStateSubsystem* State = ULBWorldStateSubsystem::Get(this);
	if (!State)
	{
		UE_LOG(LogLB, Warning, TEXT("Sequence puzzle on '%s': no world state subsystem; inert"), *GetNameSafe(GetOwner()));
		return;
	}
	if (!FLBSequenceLogic::IsConfigValid(Steps))
	{
		UE_LOG(LogLB, Warning, TEXT("Sequence puzzle on '%s': Steps must be non-empty, valid and unique; inert"), *GetNameSafe(GetOwner()));
		return;
	}
	WorldState = State;

	// Already solved (saved after solving, or solved by a cheat): nothing to do, nothing to listen to.
	if (!SolvedTags.IsEmpty() && State->GetStateRef().HasAllExact(SolvedTags))
	{
		bSolved = true;
		Accepted = Steps.Num();
		return;
	}

	State->OnStateChanged.AddUniqueDynamic(this, &ULBSequencePuzzleComponent::HandleStateChanged);
	State->OnStateReplaced.AddUniqueDynamic(this, &ULBSequencePuzzleComponent::HandleStateReplaced);
	bListening = true;
	Evaluate(FGameplayTag(), EMode::Quiet);
}

void ULBSequencePuzzleComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	StopListening();
	Super::EndPlay(EndPlayReason);
}

void ULBSequencePuzzleComponent::StopListening()
{
	if (ULBWorldStateSubsystem* State = WorldState.Get())
	{
		State->OnStateChanged.RemoveDynamic(this, &ULBSequencePuzzleComponent::HandleStateChanged);
		State->OnStateReplaced.RemoveDynamic(this, &ULBSequencePuzzleComponent::HandleStateReplaced);
	}
	bListening = false;
}

void ULBSequencePuzzleComponent::HandleStateChanged(FGameplayTag Tag, bool bAdded)
{
	if (bInternalChange || !bListening || !Steps.Contains(Tag))
	{
		return;
	}
	Evaluate(Tag, bAdded ? EMode::Live : EMode::Quiet);
}

void ULBSequencePuzzleComponent::HandleStateReplaced()
{
	if (bInternalChange || !bListening)
	{
		return;
	}
	bFailPending = false;
	Evaluate(FGameplayTag(), EMode::Quiet);
}

void ULBSequencePuzzleComponent::Evaluate(FGameplayTag Trigger, EMode Mode)
{
	const ULBWorldStateSubsystem* State = WorldState.Get();
	if (!State || bSolved)
	{
		return;
	}

	const FLBSequenceLogic::FEval Eval = FLBSequenceLogic::Evaluate(Steps, State->GetStateRef());
	if (!Eval.bValidPrefix)
	{
		if (Mode == EMode::Quiet)
		{
			UE_LOG(LogLB, Log, TEXT("Sequence puzzle on '%s': step tags are not a valid prefix; resetting"), *GetNameSafe(GetOwner()));
			ResetSteps();
			return;
		}
		// Do not mutate world state from inside its own OnStateChanged broadcast: reset on the next tick.
		if (!bFailPending)
		{
			bFailPending = true;
			PendingWrongStep = Trigger;
			if (UWorld* World = GetWorld())
			{
				World->GetTimerManager().SetTimerForNextTick(this, &ULBSequencePuzzleComponent::ExecutePendingFail);
			}
		}
		return;
	}
	if (bFailPending)
	{
		return; // a failure is already queued; it re-checks the state when it runs
	}

	const int32 Previous = Accepted;
	Accepted = Eval.Progress;
	if (Mode == EMode::Live)
	{
		for (int32 Index = Previous; Index < Accepted; ++Index)
		{
			OnStepAccepted.Broadcast(Index, Steps[Index]);
		}
	}
	if (Accepted == Steps.Num())
	{
		Solve();
	}
}

void ULBSequencePuzzleComponent::ExecutePendingFail()
{
	if (!bFailPending)
	{
		return; // cancelled by a state replace
	}
	bFailPending = false;

	const ULBWorldStateSubsystem* State = WorldState.Get();
	if (!State || bSolved || !bListening)
	{
		return;
	}
	// A wrong step was seen: fail even if more steps arrived in the same frame (their order is ambiguous). A state replace
	// (load) cancels the pending failure instead, see HandleStateReplaced.
	const FGameplayTag Wrong = PendingWrongStep;
	PendingWrongStep = FGameplayTag();
	UE_LOG(LogLB, Log, TEXT("Sequence puzzle on '%s' failed on %s; resetting steps"), *GetNameSafe(GetOwner()), *Wrong.ToString());
	ResetSteps();
	OnPuzzleFailed.Broadcast(Wrong);
}

void ULBSequencePuzzleComponent::ResetSteps()
{
	ULBWorldStateSubsystem* State = WorldState.Get();
	if (!State)
	{
		return;
	}
	bInternalChange = true;
	State->RemoveStates(FLBSequenceLogic::ToContainer(Steps));
	bInternalChange = false;
	Accepted = 0;
}

void ULBSequencePuzzleComponent::Solve()
{
	bSolved = true;
	StopListening();
	if (ULBWorldStateSubsystem* State = WorldState.Get())
	{
		State->AddStates(SolvedTags);
	}
	UE_LOG(LogLB, Log, TEXT("Sequence puzzle on '%s' solved"), *GetNameSafe(GetOwner()));
	OnPuzzleSolved.Broadcast();
}
