#include "Audio/LBWardenAudioComponent.h"
#include "Audio/LBAudioSettings.h"
#include "AI/LBWarden.h"
#include "AI/LBWardenBrainComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "Sound/SoundBase.h"

ULBWardenAudioComponent::ULBWardenAudioComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.bStartWithTickEnabled = true;
}

void ULBWardenAudioComponent::BeginPlay()
{
	Super::BeginPlay();
	Warden = Cast<ALBWarden>(GetOwner());
	if (!Warden.IsValid())
	{
		SetComponentTickEnabled(false);
	}
}

void ULBWardenAudioComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	Unbind();
	for (FLBAudioLoop& Loop : Breath)
	{
		Loop.Stop();
	}
	Robe.Stop();
	bAudioActive = false;
	Super::EndPlay(EndPlayReason);
}

ULBAudioSubsystem* ULBWardenAudioComponent::GetAudio() const
{
	const UWorld* World = GetWorld();
	return World ? World->GetSubsystem<ULBAudioSubsystem>() : nullptr;
}

float ULBWardenAudioComponent::GetBreathLevel(int32 Tier) const
{
	return Tier >= 0 && Tier < 3 ? Breath[Tier].Level : 0.f;
}

bool ULBWardenAudioComponent::IsOnStage(const ULBWardenBrainComponent* Brain) const
{
	// The brain shows the Warden (SetDormantPresentation(false)) only when its stage allows it, so "not dormant" is the stage test.
	const ALBWarden* Owner = Warden.Get();
	return Owner && !Owner->IsDormantPresentation();
}

void ULBWardenAudioComponent::EnsureBound()
{
	ALBWarden* Owner = Warden.Get();
	ULBWardenBrainComponent* Brain = Owner ? Owner->GetBrain() : nullptr;
	if (Brain == BoundBrain.Get())
	{
		return;
	}
	Unbind();
	if (Brain)
	{
		Brain->OnPlayerSpotted.AddUniqueDynamic(this, &ULBWardenAudioComponent::HandlePlayerSpotted);
		Brain->OnPlayerLost.AddUniqueDynamic(this, &ULBWardenAudioComponent::HandlePlayerLost);
		Brain->OnAttackWindup.AddUniqueDynamic(this, &ULBWardenAudioComponent::HandleAttackWindup);
		Brain->OnPlayerCaught.AddUniqueDynamic(this, &ULBWardenAudioComponent::HandlePlayerCaught);
		Brain->OnStateChanged.AddUniqueDynamic(this, &ULBWardenAudioComponent::HandleStateChanged);
	}
	BoundBrain = Brain;
}

void ULBWardenAudioComponent::Unbind()
{
	if (ULBWardenBrainComponent* Brain = BoundBrain.Get())
	{
		Brain->OnPlayerSpotted.RemoveDynamic(this, &ULBWardenAudioComponent::HandlePlayerSpotted);
		Brain->OnPlayerLost.RemoveDynamic(this, &ULBWardenAudioComponent::HandlePlayerLost);
		Brain->OnAttackWindup.RemoveDynamic(this, &ULBWardenAudioComponent::HandleAttackWindup);
		Brain->OnPlayerCaught.RemoveDynamic(this, &ULBWardenAudioComponent::HandlePlayerCaught);
		Brain->OnStateChanged.RemoveDynamic(this, &ULBWardenAudioComponent::HandleStateChanged);
	}
	BoundBrain.Reset();
}

void ULBWardenAudioComponent::Silence()
{
	for (FLBAudioLoop& Loop : Breath)
	{
		Loop.FadeOutAndForget(0.3f);
	}
	Robe.FadeOutAndForget(0.3f);
	StrideLeft = 0.f;
	bHasLastLocation = false;
}

void ULBWardenAudioComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

	ALBWarden* Owner = Warden.Get();
	ULBAudioSubsystem* Audio = GetAudio();
	const ULBAudioSettings* Settings = (Audio && Audio->IsActive()) ? Audio->GetSettings() : nullptr;
	if (!Owner || !Settings)
	{
		if (bAudioActive)
		{
			Silence();
			bAudioActive = false;
		}
		return;
	}

	EnsureBound();
	const ULBWardenBrainComponent* Brain = BoundBrain.Get();
	if (!IsOnStage(Brain))
	{
		if (bAudioActive)
		{
			Silence();
			bAudioActive = false;
		}
		return;
	}
	bAudioActive = true;

	const FLBAudioWarden& Sounds = Settings->Warden;
	const FVector Location = Owner->GetActorLocation();
	const float Speed = static_cast<float>(Owner->GetVelocity().Size2D());

	// ---- Breath: three loops that crossfade by state ----
	int32 Tier = 0;
	switch (Brain ? Brain->GetState() : ELBWardenState::Patrol)
	{
	case ELBWardenState::Investigate:
	case ELBWardenState::Suspicious:
	case ELBWardenState::Search:
		Tier = 1;
		break;
	case ELBWardenState::Chase:
	case ELBWardenState::Attack:
		Tier = 2;
		break;
	default:
		Tier = 0;
		break;
	}
	const TSoftObjectPtr<USoundBase>* BreathRefs[3] = { &Sounds.BreathSlow, &Sounds.BreathFast, &Sounds.BreathHeavy };
	for (int32 Index = 0; Index < 3; ++Index)
	{
		Breath[Index].Update(*Audio, LBAudioCue::LoopWardenBreath, *BreathRefs[Index], Owner->GetRootComponent(), Index == Tier ? 1.f : 0.f, Sounds.BreathFade, Sounds.BreathFade,
			1.f, DeltaTime);
	}

	// ---- Robe: the gain follows the speed ----
	Robe.Update(*Audio, LBAudioCue::LoopWardenRobe, Sounds.RobeLoop, Owner->GetRootComponent(), FMath::Clamp(Speed / FMath::Max(Sounds.RobeFullSpeed, 1.f), 0.f, 1.f), 0.4f, 0.6f,
		1.f, DeltaTime);

	// ---- Steps by distance, and a chain clink at speed ----
	const float Moved = bHasLastLocation ? static_cast<float>(FVector::Dist2D(Location, LastLocation)) : 0.f;
	LastLocation = Location;
	bHasLastLocation = true;
	if (Moved < 300.f)
	{
		StrideLeft -= Moved;
	}
	if (StrideLeft <= 0.f)
	{
		StrideLeft = Sounds.StepStride;
		if (Moved > 0.f)
		{
			// Only while it actually moves; the stride counter was just reset, so a standing Warden stays silent.
			const float HalfHeight = Owner->GetCapsuleComponent() ? Owner->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() : 0.f;
			const FVector Foot = Location - FVector(0.0, 0.0, HalfHeight);
			const int32 Step = Audio->PickVariantFor(FName(TEXT("Warden.Step")), Sounds.Steps.Num());
			Audio->PlayAt(LBAudioCue::WardenStep, Step >= 0 ? Sounds.Steps[Step] : TSoftObjectPtr<USoundBase>(), Foot, Sounds.StepVolume,
				Audio->RandomRange(0.95f, 1.05f), Step);
			if (Speed > Sounds.ChainSpeed)
			{
				const int32 Chain = Audio->PickVariantFor(FName(TEXT("Warden.Chain")), Sounds.Chains.Num());
				Audio->PlayAt(LBAudioCue::WardenChain, Chain >= 0 ? Sounds.Chains[Chain] : TSoftObjectPtr<USoundBase>(), Location, Sounds.StepVolume,
					Audio->RandomRange(0.95f, 1.05f), Chain);
			}
		}
	}
}

void ULBWardenAudioComponent::PlayTell(FName Cue, const TArray<TSoftObjectPtr<USoundBase>>& Set, FName Key)
{
	ULBAudioSubsystem* Audio = GetAudio();
	ALBWarden* Owner = Warden.Get();
	if (!Audio || !Audio->IsActive() || !Owner || !IsOnStage(BoundBrain.Get()))
	{
		return;
	}
	const int32 Variant = Audio->PickVariantFor(Key, Set.Num());
	Audio->PlayAttached(Cue, Variant >= 0 ? Set[Variant] : TSoftObjectPtr<USoundBase>(), Owner->GetRootComponent(), 1.f, Audio->RandomRange(0.97f, 1.03f), Variant);
}

void ULBWardenAudioComponent::HandlePlayerSpotted()
{
	if (const ULBAudioSubsystem* Audio = GetAudio())
	{
		if (const ULBAudioSettings* Settings = Audio->GetSettings())
		{
			PlayTell(LBAudioCue::WardenSpotted, Settings->Warden.Spotted, FName(TEXT("Warden.Spotted")));
		}
	}
}

void ULBWardenAudioComponent::HandlePlayerLost()
{
	if (const ULBAudioSubsystem* Audio = GetAudio())
	{
		if (const ULBAudioSettings* Settings = Audio->GetSettings())
		{
			PlayTell(LBAudioCue::WardenExhale, Settings->Warden.Exhale, FName(TEXT("Warden.Exhale")));
		}
	}
}

void ULBWardenAudioComponent::HandleAttackWindup(float WindupSeconds)
{
	if (const ULBAudioSubsystem* Audio = GetAudio())
	{
		if (const ULBAudioSettings* Settings = Audio->GetSettings())
		{
			PlayTell(LBAudioCue::WardenWindup, Settings->Warden.Windup, FName(TEXT("Warden.Windup")));
		}
	}
}

void ULBWardenAudioComponent::HandlePlayerCaught()
{
	if (const ULBAudioSubsystem* Audio = GetAudio())
	{
		if (const ULBAudioSettings* Settings = Audio->GetSettings())
		{
			PlayTell(LBAudioCue::WardenCaught, Settings->Warden.Caught, FName(TEXT("Warden.Caught")));
		}
	}
}

void ULBWardenAudioComponent::HandleStateChanged(ELBWardenState OldState, ELBWardenState NewState)
{
	if (NewState != ELBWardenState::Chase)
	{
		return;
	}
	if (const ULBAudioSubsystem* Audio = GetAudio())
	{
		if (const ULBAudioSettings* Settings = Audio->GetSettings())
		{
			PlayTell(LBAudioCue::WardenRoar, Settings->Warden.Roar, FName(TEXT("Warden.Roar")));
		}
	}
}
