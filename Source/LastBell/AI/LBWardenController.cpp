#include "AI/LBWardenController.h"
#include "AI/LBWarden.h"
#include "AI/LBWardenBrainComponent.h"
#include "AI/LBWardenLogic.h"
#include "AI/LBWardenTuningData.h"
#include "Navigation/PathFollowingComponent.h"
#include "Perception/AIPerceptionComponent.h"
#include "Perception/AISenseConfig_Hearing.h"
#include "Perception/AISenseConfig_Sight.h"
#include "Perception/AISense_Hearing.h"
#include "Perception/AISense_Sight.h"

ALBWardenController::ALBWardenController()
{
	PrimaryActorTick.bCanEverTick = false;
	bWantsPlayerState = false;

	UAIPerceptionComponent* Perception = CreateDefaultSubobject<UAIPerceptionComponent>(TEXT("Perception"));
	SetPerceptionComponent(*Perception);

	// The values below are placeholders; UpdatePerceptionForStage applies the tuning asset on possession.
	SightConfig = CreateDefaultSubobject<UAISenseConfig_Sight>(TEXT("SightConfig"));
	SightConfig->DetectionByAffiliation.bDetectEnemies = true;
	SightConfig->DetectionByAffiliation.bDetectNeutrals = true;
	SightConfig->DetectionByAffiliation.bDetectFriendlies = true;

	HearingConfig = CreateDefaultSubobject<UAISenseConfig_Hearing>(TEXT("HearingConfig"));
	HearingConfig->DetectionByAffiliation.bDetectEnemies = true;
	HearingConfig->DetectionByAffiliation.bDetectNeutrals = true;
	HearingConfig->DetectionByAffiliation.bDetectFriendlies = true;

	Perception->ConfigureSense(*SightConfig);
	Perception->ConfigureSense(*HearingConfig);
	Perception->SetDominantSense(SightConfig->GetSenseImplementation());

	Brain = CreateDefaultSubobject<ULBWardenBrainComponent>(TEXT("Brain"));
}

void ALBWardenController::PostInitializeComponents()
{
	Super::PostInitializeComponents();
	if (UAIPerceptionComponent* Perception = GetAIPerceptionComponent())
	{
		Perception->OnTargetPerceptionUpdated.AddDynamic(this, &ALBWardenController::HandleTargetPerceptionUpdated);
	}
}

void ALBWardenController::OnPossess(APawn* InPawn)
{
	Super::OnPossess(InPawn);
	// Stage 3 values until the brain reads the real stage on its first tick.
	UpdatePerceptionForStage(3);
}

void ALBWardenController::UpdatePerceptionForStage(int32 Stage)
{
	UAIPerceptionComponent* Perception = GetAIPerceptionComponent();
	const ALBWarden* Warden = Cast<ALBWarden>(GetPawn());
	if (!Perception || !Warden || !SightConfig || !HearingConfig)
	{
		return;
	}
	const ULBWardenTuningData& T = Warden->GetTuning();

	// The sense must see as far as the candle-lit radius; the brain narrows it back down per target (LBWardenLogic).
	const float MaxRadius = T.GetSightRadiusForStage(Stage) * T.CandleLitSightMultiplier;
	SightConfig->SightRadius = MaxRadius;
	SightConfig->LoseSightRadius = MaxRadius + T.LoseSightExtraRadius;
	SightConfig->PeripheralVisionAngleDegrees = T.PeripheralHalfAngle;
	SightConfig->PointOfViewBackwardOffset = T.SightCloseRangeBackOffset;
	SightConfig->SetMaxAge(T.LastKnownMemorySeconds);

	HearingConfig->HearingRange = T.HearingRange;
	HearingConfig->SetMaxAge(T.LastKnownMemorySeconds);

	Perception->ConfigureSense(*SightConfig);
	Perception->ConfigureSense(*HearingConfig);
	Perception->RequestStimuliListenerUpdate();
}

void ALBWardenController::HandleTargetPerceptionUpdated(AActor* Actor, FAIStimulus Stimulus)
{
	if (Brain)
	{
		Brain->HandleTargetPerceptionUpdated(Actor, Stimulus);
	}
}

void ALBWardenController::OnMoveCompleted(FAIRequestID RequestID, const FPathFollowingResult& Result)
{
	Super::OnMoveCompleted(RequestID, Result);
	if (Brain)
	{
		Brain->HandleMoveCompleted(RequestID, Result.Code);
	}
}
