#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "LBCineAuthoringLibrary.generated.h"

class UMovieSceneCameraCutTrack;

/**
 * Authoring helpers for the cinematic tools (Tools/cine, headless Python). Not used at runtime.
 * UMovieSceneCameraCutTrack::bCanBlend is a public member with a bare UPROPERTY(), so Python's set_editor_property refuses it; without
 * it SupportsEasing is false and RearrangeAllSections strips the eases, so the cut back to the player's camera would be hard.
 */
UCLASS()
class LASTBELL_API ULBCineAuthoringLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** Sets bCanBlend on a camera cut track. False (with a Warning) for a null track. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Cinematics|Authoring")
	static bool SetCameraCutTrackCanBlend(UMovieSceneCameraCutTrack* Track, bool bInCanBlend);

	/** The track's bCanBlend; false for a null track. */
	UFUNCTION(BlueprintPure, Category = "LastBell|Cinematics|Authoring")
	static bool GetCameraCutTrackCanBlend(const UMovieSceneCameraCutTrack* Track);
};
