#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LBWardenMarkers.generated.h"

class UArrowComponent;

/**
 * Base for the Warden's level markers: a root with an editor-only arrow. Place them ON THE FLOOR; the Warden walks to their
 * location, and a teleport adds the capsule half height.
 */
UCLASS(Abstract)
class LASTBELL_API ALBWardenMarker : public AActor
{
	GENERATED_BODY()

public:
	ALBWardenMarker();

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "LastBell|Warden")
	TObjectPtr<UArrowComponent> Arrow;
};

/** Where the Warden appears. The one with the highest MinStage not above the current stage is used. */
UCLASS()
class LASTBELL_API ALBWardenSpawnPoint : public ALBWardenMarker
{
	GENERATED_BODY()

public:
	/** Lowest Warden stage (3..6) at which this spawn applies. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "LastBell|Warden", meta = (ClampMin = "1", ClampMax = "6"))
	int32 MinStage = 3;

	/** Patrol route the Warden follows from here (matches ALBPatrolPoint::RouteId). None = hold this post. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "LastBell|Warden")
	FName RouteId;
};

/** One waypoint of a patrol route. Points with the same RouteId are walked in ascending Order, then loop. */
UCLASS()
class LASTBELL_API ALBPatrolPoint : public ALBWardenMarker
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "LastBell|Warden")
	FName RouteId;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "LastBell|Warden")
	int32 Order = 0;

	/** Seconds to stand here before walking on. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "LastBell|Warden", meta = (ClampMin = "0"))
	float WaitSeconds = 2.f;
};

/** A spot worth checking. Searches visit up to SearchPointCount of these within SearchPointRadius of the last-known location. */
UCLASS()
class LASTBELL_API ALBSearchPoint : public ALBWardenMarker
{
	GENERATED_BODY()
};
