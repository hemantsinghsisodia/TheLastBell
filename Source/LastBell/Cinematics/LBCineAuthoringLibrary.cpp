#include "Cinematics/LBCineAuthoringLibrary.h"
#include "Tracks/MovieSceneCameraCutTrack.h"
#include "LBLog.h"

bool ULBCineAuthoringLibrary::SetCameraCutTrackCanBlend(UMovieSceneCameraCutTrack* Track, bool bInCanBlend)
{
	if (!Track)
	{
		UE_LOG(LogLB, Warning, TEXT("SetCameraCutTrackCanBlend: the track is null"));
		return false;
	}
	Track->Modify();
	Track->bCanBlend = bInCanBlend;
	return true;
}

bool ULBCineAuthoringLibrary::GetCameraCutTrackCanBlend(const UMovieSceneCameraCutTrack* Track)
{
	return Track && Track->bCanBlend;
}
