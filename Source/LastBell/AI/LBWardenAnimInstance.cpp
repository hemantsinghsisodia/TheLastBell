#include "AI/LBWardenAnimInstance.h"
#include "AI/LBWardenAnimSet.h"
#include "AI/LBWardenStoopSubsystem.h"
#include "Animation/AnimMontage.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "LBLog.h"

namespace
{
	const FName FootLeftBone(TEXT("foot_l"));
	const FName FootRightBone(TEXT("foot_r"));

	/** Foot IK only matters when walking slowly: stairs at patrol speed. */
	constexpr float FootTraceMaxSpeed = 250.f;
	/** A speed above this between two frames is a teleport, not walking. */
	constexpr float MaxPlausibleSpeed = 2000.f;
	/** A yaw change above this in one frame is a snap (a teleport or a scripted turn), not the Warden turning. */
	constexpr float MaxFrameYawDegrees = 45.f;

	float AnkleHeight(const FReferenceSkeleton& RefSkeleton, FName Bone)
	{
		const int32 Index = RefSkeleton.FindBoneIndex(Bone);
		return Index != INDEX_NONE ? static_cast<float>(RefSkeleton.GetBoneAbsoluteTransform(Index).GetLocation().Z) : 0.f;
	}
}

const ULBWardenAnimSet& ULBWardenAnimInstance::GetAnimSet() const
{
	return AnimSet ? *AnimSet : *GetDefault<ULBWardenAnimSet>();
}

void ULBWardenAnimInstance::NativeInitializeAnimation()
{
	Super::NativeInitializeAnimation();

	const ULBWardenAnimSet& Set = GetAnimSet();
	CachedStoopEaseRate = Set.StoopEaseRate;
	CachedFootInterpSpeed = Set.FootIKInterpSpeed;

	RefFootHeightLeft = 0.f;
	RefFootHeightRight = 0.f;
	if (const USkeletalMeshComponent* Mesh = GetSkelMeshComponent())
	{
		if (const USkeletalMesh* SkeletalMesh = Mesh->GetSkeletalMeshAsset())
		{
			RefFootHeightLeft = AnkleHeight(SkeletalMesh->GetRefSkeleton(), FootLeftBone);
			RefFootHeightRight = AnkleHeight(SkeletalMesh->GetRefSkeleton(), FootRightBone);
		}
	}

	// Flat ground: the feet stay where the animation puts them.
	FootIKLeft = TargetFootLeft = FVector(0.0, 0.0, RefFootHeightLeft);
	FootIKRight = TargetFootRight = FVector(0.0, 0.0, RefFootHeightRight);
	PelvisOffset = FVector::ZeroVector;
	TargetPelvisZ = 0.f;
	FootIKAlpha = 0.f;
	TargetFootAlpha = 0.f;
	StoopAlpha = 0.f;
	TargetStoop = 0.f;

	YawHistory.Reset();
	bHasLastLocation = false;
	bHasLastYaw = false;
	bHoldingCatchPose = false;
	bCatchPoseFrozen = false;
	TurnCooldownLeft = 0.f;
}

void ULBWardenAnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
	Super::NativeUpdateAnimation(DeltaSeconds);

	const AActor* Owner = GetOwningActor();
	const UWorld* World = GetWorld();
	if (!Owner || !World || DeltaSeconds <= 0.f)
	{
		return;
	}
	ClockSeconds += DeltaSeconds;
	const FVector Location = Owner->GetActorLocation();

	// Ground speed: the movement component when there is one, otherwise how far the actor moved.
	const ACharacter* Character = Cast<ACharacter>(Owner);
	const UCharacterMovementComponent* Movement = Character ? Character->GetCharacterMovement() : nullptr;
	if (Movement)
	{
		GroundSpeed = static_cast<float>(Movement->Velocity.Size2D());
	}
	else
	{
		const float Moved = bHasLastLocation ? static_cast<float>(FVector::DistXY(Location, LastLocation)) / DeltaSeconds : 0.f;
		GroundSpeed = Moved <= MaxPlausibleSpeed ? Moved : 0.f;
	}
	LastLocation = Location;
	bHasLastLocation = true;

	// Stoop: the zone query is on the game thread; the easing is in the thread-safe update.
	const ULBWardenStoopSubsystem* Zones = World->GetSubsystem<ULBWardenStoopSubsystem>();
	TargetStoop = Zones ? Zones->GetStoopAmount(Location) : 0.f;

	// Physics only near the player.
	const APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(World, 0);
	const float MaxDistance = GetAnimSet().PhysicsMaxDistance;
	PhysicsAlpha = Camera && FVector::DistSquared(Camera->GetCameraLocation(), Location) <= FMath::Square(MaxDistance) ? 1.f : 0.f;

	UpdateFootTargets(*Owner, *World);
	UpdateTurn(*Owner, DeltaSeconds);
	UpdateCatchHold();
}

void ULBWardenAnimInstance::UpdateFootTargets(const AActor& Owner, const UWorld& World)
{
	const ULBWardenAnimSet& Set = GetAnimSet();
	const USkeletalMeshComponent* Mesh = GetSkelMeshComponent();
	if (!Mesh || GroundSpeed >= FootTraceMaxSpeed || Set.FootTraceUp + Set.FootTraceDown <= 0.f)
	{
		// Not tracing: everything eases back to flat ground.
		TargetFootLeft.Z = RefFootHeightLeft;
		TargetFootRight.Z = RefFootHeightRight;
		TargetPelvisZ = 0.f;
		TargetFootAlpha = 0.f;
		return;
	}

	const double FloorZ = Mesh->GetComponentLocation().Z;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(LBWardenFootIK), false, &Owner);

	FLBFootHit Hits[2];
	FVector FootComponent[2];
	const FName Bones[2] = { FootLeftBone, FootRightBone };
	for (int32 Side = 0; Side < 2; ++Side)
	{
		const FVector FootWorld = Mesh->GetSocketLocation(Bones[Side]);
		FootComponent[Side] = Mesh->GetComponentTransform().InverseTransformPosition(FootWorld);
		const FVector Start(FootWorld.X, FootWorld.Y, FloorZ + Set.FootTraceUp);
		const FVector End(FootWorld.X, FootWorld.Y, FloorZ - Set.FootTraceDown);
		FHitResult Hit;
		if (World.LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params))
		{
			Hits[Side].bHit = true;
			Hits[Side].GroundZ = static_cast<float>(Hit.ImpactPoint.Z - FloorZ);
		}
	}

	const FLBFootPlacement Placement = LBWardenAnim::PelvisAndFeet(Hits[0], Hits[1], Set.MaxPelvisDrop);
	TargetFootLeft = FVector(FootComponent[0].X, FootComponent[0].Y, Placement.LeftZ + RefFootHeightLeft);
	TargetFootRight = FVector(FootComponent[1].X, FootComponent[1].Y, Placement.RightZ + RefFootHeightRight);
	TargetPelvisZ = Placement.PelvisZ;
	TargetFootAlpha = Placement.bActive ? 1.f : 0.f;
}

void ULBWardenAnimInstance::UpdateTurn(const AActor& Owner, float DeltaSeconds)
{
	const float Yaw = static_cast<float>(Owner.GetActorRotation().Yaw);
	if (bHasLastYaw)
	{
		const float Delta = FMath::FindDeltaAngleDegrees(LastYaw, Yaw);
		if (FMath::Abs(Delta) > MaxFrameYawDegrees)
		{
			YawHistory.Reset();
		}
		else
		{
			YawHistory.Add(ClockSeconds, Delta);
		}
	}
	LastYaw = Yaw;
	bHasLastYaw = true;
	TurnCooldownLeft = FMath::Max(TurnCooldownLeft - DeltaSeconds, 0.f);

	if (bHoldingCatchPose)
	{
		return;
	}
	const ULBWardenAnimSet& Set = GetAnimSet();
	const ELBWardenTurn Turn = LBWardenAnim::TurnDecision(YawHistory, GroundSpeed, IsAnyMontagePlaying(), TurnCooldownLeft, Set.TurnTriggerDegrees);
	if (Turn == ELBWardenTurn::None)
	{
		return;
	}
	UAnimMontage* Montage = Turn == ELBWardenTurn::Left ? Set.TurnLeft90.Get() : Set.TurnRight90.Get();
	if (Montage && Montage_Play(Montage, Set.TurnPlayRate) > 0.f)
	{
		UE_LOG(LogLBWarden, Verbose, TEXT("%s: turn %s on the spot (%.0f deg in the last %.1f s)"), *GetNameSafe(&Owner),
			Turn == ELBWardenTurn::Left ? TEXT("left") : TEXT("right"), YawHistory.Total(), YawHistory.Window);
		TurnCooldownLeft = Set.TurnCooldownSeconds;
		YawHistory.Reset();
	}
}

void ULBWardenAnimInstance::UpdateCatchHold()
{
	if (!bHoldingCatchPose || bCatchPoseFrozen)
	{
		return;
	}
	const ULBWardenAnimSet& Set = GetAnimSet();
	if (!Set.Attack || !Montage_IsPlaying(Set.Attack))
	{
		// The attack ended before it reached its hit time: nothing left to hold.
		bHoldingCatchPose = false;
		return;
	}
	if (Montage_GetPosition(Set.Attack) >= Set.AttackHitTime)
	{
		Montage_Pause(Set.Attack);
		bCatchPoseFrozen = true;
		UE_LOG(LogLBWarden, Verbose, TEXT("%s: catch pose held at %.2f s"), *GetNameSafe(GetOwningActor()), Montage_GetPosition(Set.Attack));
	}
}

void ULBWardenAnimInstance::NativeThreadSafeUpdateAnimation(float DeltaSeconds)
{
	Super::NativeThreadSafeUpdateAnimation(DeltaSeconds);

	// Only plain members here: no UObject, no world.
	StoopAlpha = LBWardenAnim::EaseTowards(StoopAlpha, TargetStoop, CachedStoopEaseRate, DeltaSeconds);
	FootIKAlpha = FMath::FInterpTo(FootIKAlpha, TargetFootAlpha, DeltaSeconds, CachedFootInterpSpeed);
	FootIKLeft.X = TargetFootLeft.X;
	FootIKLeft.Y = TargetFootLeft.Y;
	FootIKLeft.Z = FMath::FInterpTo(FootIKLeft.Z, TargetFootLeft.Z, DeltaSeconds, CachedFootInterpSpeed);
	FootIKRight.X = TargetFootRight.X;
	FootIKRight.Y = TargetFootRight.Y;
	FootIKRight.Z = FMath::FInterpTo(FootIKRight.Z, TargetFootRight.Z, DeltaSeconds, CachedFootInterpSpeed);
	PelvisOffset.Z = FMath::FInterpTo(PelvisOffset.Z, TargetPelvisZ, DeltaSeconds, CachedFootInterpSpeed);
}

void ULBWardenAnimInstance::PlayAttack()
{
	const ULBWardenAnimSet& Set = GetAnimSet();
	bHoldingCatchPose = false;
	bCatchPoseFrozen = false;
	if (Set.Attack)
	{
		Montage_Play(Set.Attack, Set.AttackPlayRate);
	}
}

void ULBWardenAnimInstance::PlayLookAround()
{
	const ULBWardenAnimSet& Set = GetAnimSet();
	if (Set.LookAround)
	{
		Montage_Play(Set.LookAround, 1.f);
	}
}

void ULBWardenAnimInstance::HoldCatchPose()
{
	const ULBWardenAnimSet& Set = GetAnimSet();
	if (!Set.Attack || !Montage_IsPlaying(Set.Attack))
	{
		return;
	}
	bHoldingCatchPose = true;
	bCatchPoseFrozen = false;
	UpdateCatchHold();
}
