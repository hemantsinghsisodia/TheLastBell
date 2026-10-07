#include "Character/LBFootstepComponent.h"
#include "Character/LBCharacter.h"
#include "Character/LBPlayerTuningData.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
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
		EmitStep(T->GetLoudness(Gait));
	}
}

void ULBFootstepComponent::HandleLanded(const FHitResult& Hit)
{
	const ALBCharacter* Owner = Character.Get();
	const ULBPlayerTuningData* T = Tuning.Get();
	if (Owner && T)
	{
		// Landing is at least as loud as a walking step.
		EmitStep(FMath::Max(T->GetLoudness(Owner->GetGait()), T->WalkLoudness));
	}
	Stride.Reset();
}

void ULBFootstepComponent::EmitStep(float Loudness)
{
	const ALBCharacter* Owner = Character.Get();
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

	if (FootstepTable)
	{
		TArray<FLBFootstepRow*> Rows;
		FootstepTable->GetAllRows<FLBFootstepRow>(TEXT("LBFootstep"), Rows);
		const FLBFootstepRow* Match = nullptr;
		const FLBFootstepRow* Fallback = nullptr;
		for (const FLBFootstepRow* Row : Rows)
		{
			if (!Row)
			{
				continue;
			}
			if (Row->SurfaceType == Surface)
			{
				Match = Row;
				break;
			}
			if (Row->SurfaceType == SurfaceType_Default)
			{
				Fallback = Row;
			}
		}
		const FLBFootstepRow* Chosen = Match ? Match : Fallback;
		if (Chosen && Chosen->Sound)
		{
			const float Volume = FMath::FRandRange(Chosen->VolumeMin, FMath::Max(Chosen->VolumeMin, Chosen->VolumeMax));
			const float Pitch = FMath::FRandRange(Chosen->PitchMin, FMath::Max(Chosen->PitchMin, Chosen->PitchMax));
			UGameplayStatics::PlaySoundAtLocation(World, Chosen->Sound, FootLocation, Volume, Pitch);
		}
	}

	OnFootstep.Broadcast(Loudness, FootLocation, Surface);
}
