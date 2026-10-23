#pragma once

#include "CoreMinimal.h"
#include "LBWardenTypes.generated.h"

/** The Warden brain's states (D-037). Patrol doubles as "hold the post" below stage 4 or when no route exists. */
UENUM(BlueprintType)
enum class ELBWardenState : uint8
{
	Dormant,
	Patrol,
	Investigate,
	Suspicious,
	Search,
	Chase,
	Attack,
	Return
};
