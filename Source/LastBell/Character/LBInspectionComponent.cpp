#include "Character/LBInspectionComponent.h"
#include "Character/LBCharacter.h"
#include "Character/LBPlayerTuningData.h"
#include "Character/LBPlayerTypes.h"
#include "Components/LBInspectableComponent.h"
#include "Components/LBInteractableComponent.h"
#include "Systems/LBPlayerController.h"
#include "Components/MeshComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SceneComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "GameFramework/PlayerController.h"
#include "LBLog.h"

namespace
{
	/** Half extents of the item's visible meshes along the item's own axes (actor rotation, world-scale size). */
	bool ComputeLocalVisualExtent(const AActor* Item, FVector& OutHalfExtent)
	{
		const FTransform ActorNoScale(Item->GetActorRotation(), Item->GetActorLocation());
		FBox Box(ForceInit);
		TInlineComponentArray<UMeshComponent*> Meshes(Item);
		for (const UMeshComponent* Mesh : Meshes)
		{
			if (!Mesh->IsVisible() || Mesh->bHiddenInGame)
			{
				continue;
			}
			const FTransform Relative = Mesh->GetComponentTransform().GetRelativeTransform(ActorNoScale);
			Box += Mesh->CalcBounds(Relative).GetBox();
		}
		if (!Box.IsValid)
		{
			return false;
		}
		OutHalfExtent = Box.GetExtent();
		return true;
	}
}

ULBInspectionComponent::ULBInspectionComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.bStartWithTickEnabled = false;
	PrimaryComponentTick.TickGroup = TG_PostPhysics;
}

const ULBPlayerTuningData& ULBInspectionComponent::GetTuning() const
{
	if (const ALBCharacter* Owner = Cast<ALBCharacter>(GetOwner()))
	{
		return Owner->GetTuning();
	}
	return *GetDefault<ULBPlayerTuningData>();
}

bool ULBInspectionComponent::GetViewPoint(FVector& OutLocation, FRotator& OutRotation) const
{
	const APawn* Pawn = Cast<APawn>(GetOwner());
	if (const AController* Controller = Pawn ? Pawn->GetController() : nullptr)
	{
		Controller->GetPlayerViewPoint(OutLocation, OutRotation);
		return true;
	}
	return false;
}

bool ULBInspectionComponent::BeginInspect(ULBInspectableComponent* Inspectable, ULBInteractableComponent* InSource)
{
	AActor* Item = IsValid(Inspectable) ? Inspectable->GetOwner() : nullptr;
	if (!Item || IsInspecting())
	{
		return false;
	}
	// The item is moved every frame, which only works on a movable root (static meshes would not even update their render transform).
	const USceneComponent* Root = Item->GetRootComponent();
	if (!Root || Root->Mobility != EComponentMobility::Movable)
	{
		UE_LOG(LogLB, Warning, TEXT("Cannot inspect '%s': its root component is not Movable"), *GetNameSafe(Item));
		return false;
	}
	if (const ALBCharacter* Owner = Cast<ALBCharacter>(GetOwner()); Owner && Owner->IsDead())
	{
		return false;
	}

	bInspecting = true;
	Inspected = Inspectable;
	Source = InSource;
	OriginalTransform = Item->GetActorTransform();
	bOriginalCollision = Item->GetActorEnableCollision();

	FVector BoundsOrigin, BoundsExtent;
	Item->GetActorBounds(false, BoundsOrigin, BoundsExtent);
	LocalCenterOffset = OriginalTransform.InverseTransformPosition(BoundsOrigin);

	UPrimitiveComponent* RootPrimitive = Cast<UPrimitiveComponent>(Item->GetRootComponent());
	bWasSimulatingPhysics = RootPrimitive && RootPrimitive->IsSimulatingPhysics();
	if (bWasSimulatingPhysics)
	{
		RootPrimitive->SetSimulatePhysics(false);
	}
	Item->SetActorEnableCollision(false);

	// Flat items are turned face-on first; InitialInspectRotation (camera space) is applied on top of that.
	FQuat FaceCamera = FQuat::Identity;
	if (Inspectable->bAutoFaceCamera)
	{
		FVector HalfExtent;
		if (ComputeLocalVisualExtent(Item, HalfExtent))
		{
			LBPlayerLogic::ComputeFaceCameraRotation(HalfExtent, FaceCamera);
		}
	}
	ItemRotationInCameraSpace = Inspectable->InitialInspectRotation.Quaternion() * FaceCamera;
	BlendAlpha = 0.f;
	BeginFrame = GFrameCounter;

	if (const ACharacter* Character = Cast<ACharacter>(GetOwner()))
	{
		if (UCharacterMovementComponent* Movement = Character->GetCharacterMovement())
		{
			Movement->StopMovementImmediately();
		}
	}
	SetInputContextActive(true);

	SetComponentTickEnabled(true);
	OnInspectBegin.Broadcast(Inspectable);
	return true;
}

bool ULBInspectionComponent::RequestClose()
{
	constexpr uint64 MinOpenFrames = 2;
	if (!IsInspecting() || GFrameCounter < BeginFrame + MinOpenFrames)
	{
		return false;
	}
	EndInspect();
	return true;
}

bool ULBInspectionComponent::WasClosedThisFrame() const
{
	return !IsInspecting() && EndFrame == GFrameCounter;
}

void ULBInspectionComponent::AddRotateInput(FVector2D Axis)
{
	if (!IsInspecting())
	{
		return;
	}
	const float Rate = FMath::DegreesToRadians(GetTuning().InspectRotateRate);
	// Rotation happens in camera space: horizontal drag spins about the camera's up axis, vertical about its right axis.
	const FQuat Yaw(FVector::ZAxisVector, Axis.X * Rate);
	const FQuat Pitch(FVector::YAxisVector, Axis.Y * Rate);
	ItemRotationInCameraSpace = (Yaw * Pitch * ItemRotationInCameraSpace).GetNormalized();
}

void ULBInspectionComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

	if (!bInspecting)
	{
		SetComponentTickEnabled(false);
		return;
	}
	ULBInspectableComponent* Inspectable = Inspected.Get();
	AActor* Item = Inspectable ? Inspectable->GetOwner() : nullptr;
	if (!IsValid(Item))
	{
		// The item vanished under us: just leave inspection mode (no restore, no keep, no grant).
		EndInspect();
		return;
	}

	FVector ViewLocation;
	FRotator ViewRotation;
	if (!GetViewPoint(ViewLocation, ViewRotation))
	{
		return;
	}

	const ULBPlayerTuningData& T = GetTuning();
	BlendAlpha = T.InspectBlendTime > KINDA_SMALL_NUMBER ? FMath::Min(BlendAlpha + DeltaTime / T.InspectBlendTime, 1.f) : 1.f;
	const float S = FMath::SmoothStep(0.f, 1.f, BlendAlpha);

	const FQuat TargetRotation = ViewRotation.Quaternion() * ItemRotationInCameraSpace;
	const FVector HoldCenter = ViewLocation + ViewRotation.Vector() * T.InspectHoldDistance;
	// Place the item so its bounds centre sits on the hold point, then rotate about that centre.
	const FVector TargetLocation = HoldCenter - TargetRotation.RotateVector(LocalCenterOffset * OriginalTransform.GetScale3D());

	const FVector NewLocation = FMath::Lerp(OriginalTransform.GetLocation(), TargetLocation, S);
	const FQuat NewRotation = FQuat::Slerp(OriginalTransform.GetRotation(), TargetRotation, S);
	Item->SetActorLocationAndRotation(NewLocation, NewRotation, false, nullptr, ETeleportType::TeleportPhysics);
}

void ULBInspectionComponent::RestoreItem(ULBInspectableComponent* Inspectable)
{
	AActor* Item = IsValid(Inspectable) ? Inspectable->GetOwner() : nullptr;
	if (!IsValid(Item))
	{
		return;
	}
	Item->SetActorTransform(OriginalTransform, false, nullptr, ETeleportType::TeleportPhysics);
	Item->SetActorEnableCollision(bOriginalCollision);
	if (bWasSimulatingPhysics)
	{
		if (UPrimitiveComponent* RootPrimitive = Cast<UPrimitiveComponent>(Item->GetRootComponent()))
		{
			RootPrimitive->SetSimulatePhysics(true);
		}
	}
}

void ULBInspectionComponent::SetInputContextActive(bool bActive) const
{
	if (const APawn* Pawn = Cast<APawn>(GetOwner()))
	{
		if (ALBPlayerController* PC = Cast<ALBPlayerController>(Pawn->GetController()))
		{
			PC->SetInspectionContextActive(bActive);
		}
	}
}

void ULBInspectionComponent::EndInspect()
{
	FinishInspect(false);
}

void ULBInspectionComponent::CancelInspect()
{
	FinishInspect(true);
}

void ULBInspectionComponent::FinishInspect(bool bCancel)
{
	if (!bInspecting)
	{
		return;
	}

	ULBInspectableComponent* Inspectable = Inspected.Get();
	ULBInteractableComponent* SourceInteractable = Source.Get();
	const bool bItemValid = IsValid(Inspectable) && IsValid(Inspectable->GetOwner());
	const bool bKept = !bCancel && bItemValid && Inspectable->bKeepOnClose;

	// Leave the inspection state first so anything reacting below (grants, delegates) sees a consistent "not inspecting".
	bInspecting = false;
	Inspected.Reset();
	Source.Reset();
	EndFrame = GFrameCounter;
	SetComponentTickEnabled(false);
	SetInputContextActive(false);

	if (bItemValid)
	{
		// The item always goes back to its original transform first; a kept item is then hidden in place.
		RestoreItem(Inspectable);
		if (bKept)
		{
			Inspectable->ApplyKeep();
			if (SourceInteractable)
			{
				SourceInteractable->CompleteInspection(GetOwner());
			}
		}
	}
	OnInspectEnd.Broadcast(bKept);
}

void ULBInspectionComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	// Never leave an item floating in the world or the inspect input context active when the player goes away.
	CancelInspect();
	SetInputContextActive(false);
	Super::EndPlay(EndPlayReason);
}
