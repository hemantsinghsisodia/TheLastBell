#include "Audio/LBAmbientEmitter.h"
#include "Engine/World.h"
#include "Sound/SoundBase.h"

ALBAmbientEmitter::ALBAmbientEmitter()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = true;
	// Four distance checks a second (plan P16 section 2.9).
	PrimaryActorTick.TickInterval = 0.25f;

	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);
	SetActorEnableCollision(false);
}

void ALBAmbientEmitter::BeginPlay()
{
	Super::BeginPlay();
	// Spread the first shots of neighbouring emitters, whatever the order they begin play in.
	NextShotTime = 0.0;
}

void ALBAmbientEmitter::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	LoopState.Stop();
	bActive = false;
	Super::EndPlay(EndPlayReason);
}

void ALBAmbientEmitter::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (const UWorld* World = GetWorld())
	{
		Evaluate(World->GetTimeSeconds(), DeltaSeconds);
	}
}

void ALBAmbientEmitter::ScheduleNextShot(double Now, ULBAudioSubsystem& Audio)
{
	NextShotTime = Now + static_cast<double>(Audio.RandomRange(IntervalMin, FMath::Max(IntervalMin, IntervalMax)));
}

void ALBAmbientEmitter::Evaluate(double Now, float DeltaSeconds)
{
	const UWorld* World = GetWorld();
	ULBAudioSubsystem* Audio = World ? World->GetSubsystem<ULBAudioSubsystem>() : nullptr;
	FVector Listener = FVector::ZeroVector;
	const bool bShouldPlay = Audio && Audio->IsActive() && Audio->GetListenerLocation(Listener)
		&& FVector::DistSquared(Listener, GetActorLocation()) <= FMath::Square(static_cast<double>(ActiveRadius));

	const bool bLoopMode = !Loop.IsNull();
	if (!bShouldPlay)
	{
		if (bActive)
		{
			bActive = false;
			if (bLoopMode)
			{
				LoopState.FadeOutAndForget(0.5f);
			}
		}
		return;
	}

	if (!bActive)
	{
		bActive = true;
		if (!bLoopMode)
		{
			// Entering the radius: the first one-shot comes after a random part of an interval, not at once.
			ScheduleNextShot(Now, *Audio);
		}
	}

	if (bLoopMode)
	{
		// The loop eases in over half a second (the tick is 4 Hz, so the level moves in steps).
		LoopState.Update(*Audio, LBAudioCue::Emitter, Loop, GetRootComponent(), LoopVolume, 0.5f, 0.5f, 1.f, DeltaSeconds);
		return;
	}

	if (Now >= NextShotTime)
	{
		const int32 Variant = Audio->PickVariantFor(FName(*FString::Printf(TEXT("Emitter.%s"), *GetName())), Variants.Num());
		if (Variant >= 0)
		{
			Audio->PlayAt(LBAudioCue::Emitter, Variants[Variant], GetActorLocation(), Audio->RandomRange(static_cast<float>(VolumeRange.X), static_cast<float>(VolumeRange.Y)),
				Audio->RandomRange(static_cast<float>(PitchRange.X), static_cast<float>(PitchRange.Y)), Variant);
		}
		ScheduleNextShot(Now, *Audio);
	}
}
