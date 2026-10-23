#include "AI/LBWardenLogic.h"
#include "AI/LBWardenTuningData.h"
#include "LBGameplayTags.h"

void FLBSearchPlan::Build(const TArray<FVector>& Candidates, const FVector& Center, float Radius, int32 MaxVisitCount)
{
	Points.Reset();
	Visited.Reset();
	VisitedCount = 0;
	MaxVisits = FMath::Max(MaxVisitCount, 0);
	for (const FVector& Candidate : Candidates)
	{
		if (FVector::Dist(Candidate, Center) <= Radius)
		{
			Points.Add(Candidate);
			Visited.Add(false);
		}
	}
}

int32 FLBSearchPlan::PickNext(const FVector& From) const
{
	if (IsComplete())
	{
		return INDEX_NONE;
	}
	int32 Best = INDEX_NONE;
	double BestDistSq = TNumericLimits<double>::Max();
	for (int32 i = 0; i < Points.Num(); ++i)
	{
		if (Visited[i])
		{
			continue;
		}
		const double DistSq = FVector::DistSquared(Points[i], From);
		if (DistSq < BestDistSq)
		{
			BestDistSq = DistSq;
			Best = i;
		}
	}
	return Best;
}

void FLBSearchPlan::MarkVisited(int32 Index)
{
	if (Visited.IsValidIndex(Index) && !Visited[Index])
	{
		Visited[Index] = true;
		++VisitedCount;
	}
}

namespace LBWardenLogic
{
	int32 HighestStage(const FGameplayTagContainer& WorldState)
	{
		const FGameplayTag Stages[] = {
			LBTags::State_Warden_Stage_1.GetTag(), LBTags::State_Warden_Stage_2.GetTag(), LBTags::State_Warden_Stage_3.GetTag(),
			LBTags::State_Warden_Stage_4.GetTag(), LBTags::State_Warden_Stage_5.GetTag(), LBTags::State_Warden_Stage_6.GetTag() };
		for (int32 i = UE_ARRAY_COUNT(Stages) - 1; i >= 0; --i)
		{
			if (WorldState.HasTagExact(Stages[i]))
			{
				return i + 1;
			}
		}
		return 0;
	}

	FLBWardenCaps CapsForStage(int32 Stage)
	{
		FLBWardenCaps Caps;
		Caps.bActive = Stage >= 3;
		Caps.bPatrol = Stage >= 4;
		Caps.bSearch = Stage >= 4;
		Caps.bChase = Stage >= 5;
		return Caps;
	}

	bool IsStateAllowed(ELBWardenState State, const FLBWardenCaps& Caps)
	{
		switch (State)
		{
		case ELBWardenState::Dormant:
			return !Caps.bActive;
		case ELBWardenState::Search:
			return Caps.bActive && Caps.bSearch;
		case ELBWardenState::Chase:
			return Caps.bActive && Caps.bChase;
		default:
			return Caps.bActive;
		}
	}

	float EffectiveSightRadius(int32 Stage, bool bCandleLit, const ULBWardenTuningData& Tuning)
	{
		return Tuning.GetSightRadiusForStage(Stage) * (bCandleLit ? Tuning.CandleLitSightMultiplier : 1.f);
	}

	bool IsWithinSightRadius(float Distance, bool bWasVisible, float Radius, float LoseExtra)
	{
		return Distance <= (bWasVisible ? Radius + LoseExtra : Radius);
	}

	int32 SelectSpawnIndex(const TArray<int32>& MinStages, int32 Stage)
	{
		int32 Best = INDEX_NONE;
		for (int32 i = 0; i < MinStages.Num(); ++i)
		{
			if (MinStages[i] <= Stage && (Best == INDEX_NONE || MinStages[i] > MinStages[Best]))
			{
				Best = i;
			}
		}
		return Best;
	}

	bool IsInsideViewCone(const FVector& Origin, const FVector& ViewDirection, const FVector& Target, float HalfAngleDegrees)
	{
		const FVector ToTarget = (Target - Origin).GetSafeNormal();
		if (ToTarget.IsNearlyZero())
		{
			return true;
		}
		return FVector::DotProduct(ViewDirection.GetSafeNormal(), ToTarget) >= FMath::Cos(FMath::DegreesToRadians(HalfAngleDegrees));
	}

	const TCHAR* StateName(ELBWardenState State)
	{
		switch (State)
		{
		case ELBWardenState::Dormant: return TEXT("Dormant");
		case ELBWardenState::Patrol: return TEXT("Patrol");
		case ELBWardenState::Investigate: return TEXT("Investigate");
		case ELBWardenState::Suspicious: return TEXT("Suspicious");
		case ELBWardenState::Search: return TEXT("Search");
		case ELBWardenState::Chase: return TEXT("Chase");
		case ELBWardenState::Attack: return TEXT("Attack");
		case ELBWardenState::Return: return TEXT("Return");
		default: return TEXT("?");
		}
	}

	namespace
	{
		FLBWardenDecision Go(ELBWardenState Next, const TCHAR* Reason, bool bReenter = false, bool bKill = false)
		{
			FLBWardenDecision D;
			D.Next = Next;
			D.Reason = Reason;
			D.bReenter = bReenter;
			D.bKillPlayer = bKill;
			return D;
		}
	}

	FLBWardenDecision Evaluate(ELBWardenState State, const FLBWardenFacts& F, const ULBWardenTuningData& T)
	{
		const FLBWardenCaps& Caps = F.Caps;
		const FLBWardenDecision Stay = Go(State, TEXT("stay"));

		// 1. Stage gate. Below stage 3 the pawn does nothing; at stage 3+ a dormant pawn wakes once it can appear unseen.
		if (!Caps.bActive)
		{
			return State == ELBWardenState::Dormant ? Stay : Go(ELBWardenState::Dormant, TEXT("stage too low"));
		}
		if (State == ELBWardenState::Dormant)
		{
			return F.bCanMaterialize ? Go(ELBWardenState::Patrol, TEXT("stage active")) : Stay;
		}

		// 2. An attack in progress runs to the end of its windup, then lands or is cancelled.
		if (State == ELBWardenState::Attack)
		{
			if (F.StateTime < T.AttackWindupSeconds)
			{
				return Stay;
			}
			if (F.bAttackStillValid)
			{
				return Go(ELBWardenState::Return, TEXT("attack landed"), false, true);
			}
			return Go(Caps.bChase ? ELBWardenState::Chase : ELBWardenState::Investigate, TEXT("attack cancelled: out of range or sight"));
		}

		// 3. Stage dropped (a reload): leave states the stage no longer allows.
		if (!IsStateAllowed(State, Caps))
		{
			return Go(ELBWardenState::Return, TEXT("state not allowed at this stage"));
		}

		// 4. Close enough to catch, with line of sight: attack at any active stage.
		if (F.bInAttackRange)
		{
			return Go(ELBWardenState::Attack, TEXT("player in attack range"));
		}

		// 5. Confirmed sight.
		if (F.bSightConfirmed && State != ELBWardenState::Chase)
		{
			if (Caps.bChase)
			{
				if (!F.bPlayerUnreachable)
				{
					return Go(ELBWardenState::Chase, TEXT("sight confirmed"));
				}
				if (State != ELBWardenState::Search)
				{
					return Go(ELBWardenState::Search, TEXT("player seen but unreachable"));
				}
			}
			else if (State != ELBWardenState::Investigate)
			{
				return Go(ELBWardenState::Investigate, TEXT("sight confirmed, chase not allowed"));
			}
		}

		// 6. Noise: investigate it, unless already in pursuit.
		if (F.bNoiseHeard && State != ELBWardenState::Chase)
		{
			return Go(ELBWardenState::Investigate, TEXT("noise heard"), State == ELBWardenState::Investigate);
		}

		// 7. Per-state rules.
		switch (State)
		{
		case ELBWardenState::Investigate:
			if (F.bArrived)
			{
				return Go(ELBWardenState::Suspicious, TEXT("reached the stimulus"));
			}
			break;
		case ELBWardenState::Suspicious:
			if (F.StateTime >= T.SuspiciousSeconds)
			{
				return Caps.bSearch ? Go(ELBWardenState::Search, TEXT("nothing seen, search"))
					: Go(ELBWardenState::Return, TEXT("nothing seen, return"));
			}
			break;
		case ELBWardenState::Search:
			if (F.bSearchFinished || F.StateTime >= T.SearchDurationSeconds)
			{
				return Go(ELBWardenState::Return, F.bSearchFinished ? TEXT("search points visited") : TEXT("search time over"));
			}
			break;
		case ELBWardenState::Chase:
			if (F.bPlayerUnreachable && F.bArrived)
			{
				return Go(ELBWardenState::Search, TEXT("closest reachable point reached, player unreachable"));
			}
			if (!F.bSeesPlayer && F.TimeSinceSight >= T.LastKnownMemorySeconds)
			{
				return Go(ELBWardenState::Search, TEXT("lost the player"));
			}
			break;
		case ELBWardenState::Return:
			if (F.bArrived)
			{
				return Go(ELBWardenState::Patrol, TEXT("back on post"));
			}
			break;
		default:
			break;
		}
		return Stay;
	}
}
