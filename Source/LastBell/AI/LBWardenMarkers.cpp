#include "AI/LBWardenMarkers.h"
#include "Components/ArrowComponent.h"
#include "Components/SceneComponent.h"

ALBWardenMarker::ALBWardenMarker()
{
	PrimaryActorTick.bCanEverTick = false;
	USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);

	Arrow = CreateDefaultSubobject<UArrowComponent>(TEXT("Arrow"));
	Arrow->SetupAttachment(Root);
	Arrow->SetHiddenInGame(true);
	Arrow->ArrowSize = 2.f;
	Arrow->SetRelativeLocation(FVector(0.f, 0.f, 20.f));
	SetActorEnableCollision(false);
}
