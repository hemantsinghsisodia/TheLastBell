#pragma once

#include "CoreMinimal.h"

/** Tag names passed to UAISense_Hearing::ReportNoiseEvent so the Warden's logs and debug show what it heard. */
namespace LBNoiseTags
{
	const FName Footstep(TEXT("Footstep"));
	const FName Landing(TEXT("Landing"));
	const FName Interact(TEXT("Interact"));
}
