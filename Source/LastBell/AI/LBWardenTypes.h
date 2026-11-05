#pragma once

#include "CoreMinimal.h"
#include "LBWardenTypes.generated.h"

/** The Warden brain's states (D-037). Patrol doubles as "hold the post" below stage 4 or when no route exists. */
// Do not reorder: BP_Warden (PlayStateFeedback, EndWindupTell) compares the state byte to the literals Chase = 5 and Attack = 6; if this order changes, those Blueprint graphs must change too (test LastBell.Warden.StateOrderMatchesBlueprintLiterals).
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
