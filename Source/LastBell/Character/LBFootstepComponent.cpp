#include "Character/LBFootstepComponent.h"
#include "Character/LBCharacter.h"
#include "Character/LBPlayerTuningData.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Perception/AISense_Hearing.h"
#include "AI/LBNoiseTags.h"
#include "Audio/LBAudioLogic.h"
#include "Audio/LBAudioSubsystem.h"
#include "Sound/SoundBase.h"

ULBFootstepComponent::ULBFootstepComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PostPhysics;
}

void ULBFootstepComponent::BeginPlay()
{
	Super::BeginPlay();

	ALBCharacter* Owner = Cast<ALBCharacter>(GetOwner());
	Character = Owner;
	if (!Owner)
	{
		SetComponentTickEnabled(false);
		return;
	}
	Tuning = &Owner->GetTuning();
	Owner->LandedDelegate.AddDynamic(this, &ULBFootstepComponent::HandleLanded);
}

void ULBFootstepComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (ALBCharacter* Owner = Character.Get())
	{
		Owner->LandedDelegate.RemoveDynamic(this, &ULBFootstepComponent::HandleLanded);
	}
	Super::EndPlay(EndPlayReason);
}

void ULBFootstepComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

	const ALBCharacter* Owner = Character.Get();
	const ULBPlayerTuningData* T = Tuning.Get();
	if (!Owner || !T)
	{
		return;
	}

	const UCharacterMovementComponent* Movement = Owner->GetCharacterMovement();
	if (!Movement || !Movement->IsMovingOnGround())
	{
		return;
	}

	const ELBGait Gait = Owner->GetGait();
	if (Gait == ELBGait::Idle)
	{
		return;
	}

	const float Distance = Owner->GetVelocity().Size2D() * DeltaTime;
	const int32 Steps = Stride.Advance(Distance, T->GetStride(Gait));
	if (Steps > 0)
	{
		// One step per frame at most: a hitch must not machine-gun sounds.
		EmitStep(T->GetLoudness(Gait), LBNoiseTags::Footstep);
	}
}

void ULBFootstepComponent::HandleLanded(const FHitResult& Hit)
{
	const ALBCharacter* Owner = Character.Get();
	const ULBPlayerTuningData* T = Tuning.Get();
	if (Owner && T)
	{
		// Landing is at least as loud as a walking step.
		EmitStep(FMath::Max(T->GetLoudness(Owner->GetGait()), T->WalkLoudness), LBNoiseTags::Landing);
	}
	Stride.Reset();
}

void ULBFootstepComponent::EmitStep(float Loudness, FName NoiseTag)
{
	ALBCharacter* Owner = Character.Get();
	const ULBPlayerTuningData* T = Tuning.Get();
	UWorld* World = GetWorld();
	if (!Owner || !T || !World)
	{
		return;
	}

	const float HalfHeight = Owner->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	const FVector Start = Owner->GetActorLocation();
	const FVector End = Start - FVector(0.f, 0.f, HalfHeight + T->FootstepTraceExtraDepth);

	FCollisionQueryParams Params(SCENE_QUERY_STAT(LBFootstep), T->bFootstepTraceComplex, Owner);
	Params.bReturnPhysicalMaterial = true;

	FHitResult Hit;
	EPhysicalSurface Surface = SurfaceType_Default;
	FVector FootLocation = Start - FVector(0.f, 0.f, HalfHeight);
	if (World->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params))
	{
		FootLocation = Hit.ImpactPoint;
		Surface = UPhysicalMaterial::DetermineSurfaceType(Hit.PhysMaterial.Get());
	}

	if (const FLBFootstepRow* Chosen = FindRow(Surface))
	{
		int32 Variant = INDEX_NONE;
		USoundBase* Sound = PickStepSound(*Chosen, Variant);
		if (Sound)
		{
			// The gait scales the loudness of the sound (not of the noise the Warden hears: that is Loudness below).
			const float GaitScale = NoiseTag == LBNoiseTags::Footstep ? GaitVolume(*Chosen, Owner->GetGait()) : 1.f;
			const float Volume = FMath::FRandRange(Chosen->VolumeMin, FMath::Max(Chosen->VolumeMin, Chosen->VolumeMax)) * GaitScale;
			const float Pitch = FMath::FRandRange(Chosen->PitchMin, FMath::Max(Chosen->PitchMin, Chosen->PitchMax));
			UGameplayStatics::PlaySoundAtLocation(World, Sound, FootLocation, Volume, Pitch);
#if !UE_BUILD_SHIPPING
			if (ULBAudioSubsystem* Audio = World->GetSubsystem<ULBAudioSubsystem>())
			{
				FLBAudioRequest Request;
				Request.Cue = LBAudioCue::Footstep;
				Request.bPositional = true;
				Request.Location = FootLocation;
				Request.Volume = Volume;
				Request.Pitch = Pitch;
				Request.Variant = Variant;
				Request.Aux = static_cast<int32>(Surface);
				Request.bSoundResolved = true;
				Audio->RecordRequest(Request);
			}
#endif
		}
	}

	// The Warden hears what the player does: loudness by gait, range capped by the player tuning. Dead players make no noise.
	if (!Owner->IsDead())
	{
		UAISense_Hearing::ReportNoiseEvent(World, FootLocation, Loudness, Owner, T->NoiseMaxRange, NoiseTag);
	}

	OnFootstep.Broadcast(Loudness, FootLocation, Surface);
}

const FLBFootstepRow* ULBFootstepComponent::FindRow(EPhysicalSurface Surface) const
{
	if (!FootstepTable)
	{
		return nullptr;
	}
	TArray<FLBFootstepRow*> Rows;
	FootstepTable->GetAllRows<FLBFootstepRow>(TEXT("LBFootstep"), Rows);
	const FLBFootstepRow* Fallback = nullptr;
	for (const FLBFootstepRow* Row : Rows)
	{
		if (!Row)
		{
			continue;
		}
		if (Row->SurfaceType == Surface)
		{
			return Row;
		}
		if (Row->SurfaceType == SurfaceType_Default)
		{
			Fallback = Row;
		}
	}
	return Fallback;
}

USoundBase* ULBFootstepComponent::PickStepSound(const FLBFootstepRow& Row, int32& OutVariant)
{
	OutVariant = INDEX_NONE;
	TArray<int32, TInlineAllocator<8>> Valid;
	for (int32 Index = 0; Index < Row.Variants.Num(); ++Index)
	{
		if (Row.Variants[Index])
		{
			Valid.Add(Index);
		}
	}
	if (Valid.IsEmpty())
	{
		return Row.Sound;
	}
	int32& Last = LastVariant.FindOrAdd(Row.SurfaceType, INDEX_NONE);
	const int32 Pick = LBAudioLogic::PickVariant(Valid.Num(), Last, FMath::FRand());
	Last = Pick;
	OutVariant = Valid[Pick];
	return Row.Variants[OutVariant];
}

float ULBFootstepComponent::GaitVolume(const FLBFootstepRow& Row, ELBGait Gait)
{
	switch (Gait)
	{
	case ELBGait::Crouch: return Row.CrouchVolume;
	case ELBGait::Sprint: return Row.SprintVolume;
	default: return 1.f;
	}
}
