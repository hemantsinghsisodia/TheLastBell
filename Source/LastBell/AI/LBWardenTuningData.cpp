#include "AI/LBWardenTuningData.h"

float ULBWardenTuningData::GetSightRadiusForStage(int32 Stage) const
{
	if (Stage >= 5)
	{
		return SightRadiusStage5;
	}
	return Stage == 4 ? SightRadiusStage4 : SightRadiusStage3;
}

float ULBWardenTuningData::GetMoveSpeed(ELBWardenState State) const
{
	switch (State)
	{
	case ELBWardenState::Patrol:
		return PatrolSpeed;
	case ELBWardenState::Investigate:
		return InvestigateSpeed;
	case ELBWardenState::Search:
		return SearchSpeed;
	case ELBWardenState::Return:
		return ReturnSpeed;
	case ELBWardenState::Chase:
		return ChaseSpeed;
	default:
		return 0.f;
	}
}
