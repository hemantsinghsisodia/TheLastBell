#include "AI/LBWardenAnimInstance.h"
#include "AI/LBWardenAnimSet.h"
#include "AI/LBWardenStoopSubsystem.h"
#include "AnimNodes/AnimNode_BlendSpacePlayer.h"
#include "Animation/AnimClassInterface.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Animation/BlendSpace.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
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
	/** Above this StoopAlpha the Warden counts as stooping: foot IK on, at any speed. */
	constexpr float StoopActiveAlpha = 0.01f;

	TAutoConsoleVariable<int32> CVarWardenAnimDebug(
		TEXT("lb.Warden.AnimDebug"), 0,
		TEXT("1: every Warden anim instance logs (LogLBWarden, once a second) its speed, the mesh tick state, foot_l and the blend space players."),
		ECVF_Default);

	const TCHAR* AnimationModeName(EAnimationMode::Type Mode)
	{
		switch (Mode)
		{
		case EAnimationMode::AnimationBlueprint: return TEXT("AnimationBlueprint");
		case EAnimationMode::AnimationSingleNode: return TEXT("AnimationSingleNode");
		case EAnimationMode::AnimationCustomMode: return TEXT("AnimationCustomMode");
		default: return TEXT("?");
		}
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
	CachedStoopPelvisDrop = Set.StoopPelvisDrop;
	CachedMaxPelvisDrop = Set.MaxPelvisDrop;

	// Flat ground, upright: the feet stay where the animation puts them.
	FootIKLeft = TargetFootLeft = FVector::ZeroVector;
	FootIKRight = TargetFootRight = FVector::ZeroVector;
	PelvisOffset = FVector::ZeroVector;
	TargetFootPelvisZ = 0.f;
	EasedFootPelvisZ = 0.f;
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
	LogAnimDebug(DeltaSeconds);
}

void ULBWardenAnimInstance::LogAnimDebug(float DeltaSeconds)
{
	++DebugUpdateCount;
	if (CVarWardenAnimDebug.GetValueOnGameThread() == 0)
	{
		DebugLogTimer = 0.f;
		DebugUpdateCount = 0;
		return;
	}
	DebugLogTimer += DeltaSeconds;
	if (DebugLogTimer < 1.f)
	{
		return;
	}
	DebugLogTimer = 0.f;

	const AActor* Owner = GetOwningActor();
	const ACharacter* Character = Cast<ACharacter>(Owner);
	const UCharacterMovementComponent* Movement = Character ? Character->GetCharacterMovement() : nullptr;
	USkeletalMeshComponent* Mesh = GetSkelMeshComponent();

	FString Line = FString::Printf(TEXT("AnimDebug %s: GroundSpeed %.1f | Velocity2D %.1f MaxSpeed %.1f | StoopAlpha %.2f | IsAnyMontagePlaying %d | updates since last line %d"),
		*GetNameSafe(Owner), GroundSpeed, Movement ? Movement->Velocity.Size2D() : -1.0, Movement ? Movement->GetMaxSpeed() : -1.f,
		StoopAlpha, IsAnyMontagePlaying() ? 1 : 0, DebugUpdateCount);
	DebugUpdateCount = 0;

	if (Mesh)
	{
		const FVector FootRel = Mesh->GetSocketTransform(FootLeftBone, RTS_Component).GetLocation();
		Line += FString::Printf(TEXT(" | Mesh mode %s, anim class %s, is-this-instance %d, ShouldTickPose %d, bRecentlyRendered %d, WasRecentlyRendered %d, predicted LOD %d, tick option %d, URO %d, foot_l (component space) %s"),
			AnimationModeName(Mesh->GetAnimationMode()), *GetNameSafe(Mesh->GetAnimInstance() ? Mesh->GetAnimInstance()->GetClass() : nullptr),
			Mesh->GetAnimInstance() == this ? 1 : 0, Mesh->ShouldTickPose() ? 1 : 0, Mesh->bRecentlyRendered ? 1 : 0, Mesh->WasRecentlyRendered() ? 1 : 0,
			Mesh->GetPredictedLODLevel(), static_cast<int32>(Mesh->VisibilityBasedAnimTickOption), Mesh->bEnableUpdateRateOptimizations ? 1 : 0, *FootRel.ToCompactString());
	}
	else
	{
		Line += TEXT(" | no mesh");
	}
	UE_LOG(LogLBWarden, Log, TEXT("%s"), *Line);

	// The blend space players of the graph: where they sample, what weights that gives, and whether the clip time moves.
	const IAnimClassInterface* AnimClass = IAnimClassInterface::GetFromClass(GetClass());
	if (!AnimClass)
	{
		UE_LOG(LogLBWarden, Log, TEXT("AnimDebug %s: no anim class interface"), *GetNameSafe(Owner));
		return;
	}
	int32 PlayerIndex = 0;
	for (const FStructProperty* Property : AnimClass->GetAnimNodeProperties())
	{
		if (!Property || !Property->Struct || !Property->Struct->IsChildOf(FAnimNode_BlendSpacePlayerBase::StaticStruct()))
		{
			continue;
		}
		const FAnimNode_BlendSpacePlayerBase* Node = Property->ContainerPtrToValuePtr<FAnimNode_BlendSpacePlayerBase>(this);
		const UBlendSpace* BlendSpace = Node->GetBlendSpace();
		const FVector Position = Node->GetPosition();
		FString Weights;
		FString Axis;
		if (BlendSpace)
		{
			const FBlendParameter& Parameter = BlendSpace->GetBlendParameter(0);
			const FBlendSpaceData& RuntimeData = BlendSpace->GetBlendSpaceData();
			Axis = FString::Printf(TEXT("axis '%s' %.0f..%.0f, %d samples, runtime data: %d segments %d triangles%s"), *Parameter.DisplayName, Parameter.Min, Parameter.Max,
				BlendSpace->GetBlendSamples().Num(), RuntimeData.Segments.Num(), RuntimeData.Triangles.Num(), RuntimeData.IsEmpty() ? TEXT(" (EMPTY: the blend space returns no clip)") : TEXT(""));
			for (const FBlendSample& Sample : BlendSpace->GetBlendSamples())
			{
				Axis += FString::Printf(TEXT(" {%s at %.0f rate %.3f}"), *GetNameSafe(Sample.Animation), Sample.SampleValue.X, Sample.RateScale);
			}
			TArray<FBlendSampleData> SampleData;
			int32 CachedIndex = -1;
			BlendSpace->GetSamplesFromBlendInput(FVector(Position.X, Position.Y, Position.Z), SampleData, CachedIndex, true);
			for (const FBlendSampleData& Data : SampleData)
			{
				Weights += FString::Printf(TEXT(" [%s w %.2f rate %.2f]"), *GetNameSafe(Data.Animation), Data.TotalWeight, Data.SamplePlayRate);
			}
		}
		UE_LOG(LogLBWarden, Log, TEXT("AnimDebug %s: blend space player %d %s (%s) input X %.1f (filtered %.1f) asset time %.2f of %.2f, play rate %.2f; unfiltered weights:%s"),
			*GetNameSafe(Owner), PlayerIndex++, *GetNameSafe(BlendSpace), *Axis, Position.X, Node->GetFilteredPosition().X,
			Node->GetCurrentAssetTime(), Node->GetCurrentAssetLength(), Node->GetPlayRate(), *Weights);
	}
	if (PlayerIndex == 0)
	{
		UE_LOG(LogLBWarden, Log, TEXT("AnimDebug %s: this anim class has no blend space player (graph empty or replaced?)"), *GetNameSafe(Owner));
	}
}

void ULBWardenAnimInstance::UpdateFootTargets(const AActor& Owner, const UWorld& World)
{
	const ULBWardenAnimSet& Set = GetAnimSet();
	const USkeletalMeshComponent* Mesh = GetSkelMeshComponent();
	const bool bStooping = StoopAlpha > StoopActiveAlpha;
	// Traces run when walking slowly (stairs at patrol speed) and at any speed while stooping.
	if (!Mesh || (GroundSpeed >= FootTraceMaxSpeed && !bStooping))
	{
		// Not tracing: everything eases back to "the animation as it is".
		TargetFootLeft = FVector::ZeroVector;
		TargetFootRight = FVector::ZeroVector;
		TargetFootPelvisZ = 0.f;
		TargetFootAlpha = 0.f;
		return;
	}

	// The floor the capsule stands on: the capsule bottom (the mesh origin for an actor without one).
	const ACharacter* Character = Cast<ACharacter>(&Owner);
	const UCapsuleComponent* Capsule = Character ? Character->GetCapsuleComponent() : nullptr;
	const double FloorZ = Capsule ? Capsule->GetComponentLocation().Z - Capsule->GetScaledCapsuleHalfHeight() : Mesh->GetComponentLocation().Z;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(LBWardenFootIK), false, &Owner);

	FLBFootHit Hits[2];
	FQuat FootRotation[2];
	const FName Bones[2] = { FootLeftBone, FootRightBone };
	for (int32 Side = 0; Side < 2; ++Side)
	{
		// Last frame's pose: the foot XY (where to look) and its orientation (to express the correction in its own space).
		const FVector FootLocation = Mesh->GetSocketLocation(Bones[Side]);
		FootRotation[Side] = Mesh->GetSocketTransform(Bones[Side], RTS_Component).GetRotation();
		if (Set.FootTraceUp + Set.FootTraceDown > 0.f)
		{
			const FVector Start(FootLocation.X, FootLocation.Y, FloorZ + Set.FootTraceUp);
			const FVector End(FootLocation.X, FootLocation.Y, FloorZ - Set.FootTraceDown);
			FHitResult Hit;
			if (World.LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params))
			{
				Hits[Side].bHit = true;
				Hits[Side].Offset = static_cast<float>(Hit.ImpactPoint.Z - FloorZ);
			}
		}
	}

	const FLBFootPlacement Placement = LBWardenAnim::PelvisAndFeet(Hits[0], Hits[1], Set.MaxPelvisDrop);

	// The pelvis move already applied (the graph scales it by FootIKAlpha) drags the feet along: every foot has to come back up by it.
	const float AppliedPelvisZ = PelvisOffset.Z * FootIKAlpha;
	const float Offsets[2] = { Placement.LeftOffset, Placement.RightOffset };
	FVector* Targets[2] = { &TargetFootLeft, &TargetFootRight };
	for (int32 Side = 0; Side < 2; ++Side)
	{
		const float Correction = LBWardenAnim::FootCorrection(Offsets[Side], AppliedPelvisZ);
		*Targets[Side] = FootRotation[Side].UnrotateVector(FVector(0.0, 0.0, Correction));
	}
	TargetFootPelvisZ = Placement.PelvisZ;
	TargetFootAlpha = (Placement.bActive || bStooping) ? 1.f : 0.f;
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
	FootIKLeft = FMath::VInterpTo(FootIKLeft, TargetFootLeft, DeltaSeconds, CachedFootInterpSpeed);
	FootIKRight = FMath::VInterpTo(FootIKRight, TargetFootRight, DeltaSeconds, CachedFootInterpSpeed);
	EasedFootPelvisZ = FMath::FInterpTo(EasedFootPelvisZ, TargetFootPelvisZ, DeltaSeconds, CachedFootInterpSpeed);
	// The stoop part follows the (already eased) StoopAlpha, so it is not eased a second time.
	PelvisOffset = FVector(0.0, 0.0, LBWardenAnim::CombinedPelvisZ(EasedFootPelvisZ, StoopAlpha, CachedStoopPelvisDrop, CachedMaxPelvisDrop));
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
