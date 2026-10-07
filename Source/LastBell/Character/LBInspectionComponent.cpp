#include "Character/LBInspectionComponent.h"
#include "Character/LBCharacter.h"
#include "Character/LBPlayerTuningData.h"
#include "Character/LBPlayerTypes.h"
#include "Components/LBInspectableComponent.h"
#include "Components/LBInteractableComponent.h"
#include "Systems/LBPlayerController.h"
#include "Components/PrimitiveComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "GameFramework/PlayerController.h"
#include "LBLog.h"

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
	AActor* Item = Inspectable ? Inspectable->GetOwner() : nullptr;
	if (!Item || IsInspecting())
	{
		return false;
	}
	if (const ALBCharacter* Owner = Cast<ALBCharacter>(GetOwner()); Owner && Owner->IsDead())
	{
		return false;
	}

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

	ItemRotationInCameraSpace = Inspectable->InitialInspectRotation.Quaternion();
	BlendAlpha = 0.f;
	BeginFrame = GFrameCounter;

	if (ACharacter* Character = Cast<ACharacter>(GetOwner()))
	{
		if (UCharacterMovementComponent* Movement = Character->GetCharacterMovement())
		{
			Movement->StopMovementImmediately();
		}
		if (ALBPlayerController* PC = Cast<ALBPlayerController>(Character->GetController()))
		{
			PC->SetInspectionContextActive(true);
		}
	}

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

	ULBInspectableComponent* Inspectable = Inspected.Get();
	AActor* Item = Inspectable ? Inspectable->GetOwner() : nullptr;
	if (!Item)
	{
		// The item vanished under us: just leave inspection mode.
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

void ULBInspectionComponent::RestoreItem()
{
	ULBInspectableComponent* Inspectable = Inspected.Get();
	AActor* Item = Inspectable ? Inspectable->GetOwner() : nullptr;
	if (!Item)
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

void ULBInspectionComponent::EndInspect()
{
	ULBInspectableComponent* Inspectable = Inspected.Get();
	if (!IsInspecting())
	{
		return;
	}

	ULBInteractableComponent* SourceInteractable = Source.Get();
	const FLBInspectCloseResult Close = LBPlayerLogic::ResolveInspectClose(Inspectable ? Inspectable->bKeepOnClose : false, SourceInteractable != nullptr);

	// The item always goes back to its original transform first; a kept item is then hidden in place.
	RestoreItem();

	if (Inspectable)
	{
		if (Close.bGrantKeepTags || Close.bHideActor)
		{
			Inspectable->ApplyKeep();
		}
		if (Close.bRunInteractGrant)
		{
			SourceInteractable->CompleteInspection(GetOwner());
		}
	}

	Inspected.Reset();
	Source.Reset();
	EndFrame = GFrameCounter;
	SetComponentTickEnabled(false);

	if (const ACharacter* Character = Cast<ACharacter>(GetOwner()))
	{
		if (ALBPlayerController* PC = Cast<ALBPlayerController>(Character->GetController()))
		{
			PC->SetInspectionContextActive(false);
		}
	}
	OnInspectEnd.Broadcast(Close.bKept);
}

void ULBInspectionComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (IsInspecting())
	{
		// Never leave an item floating in the world when the player goes away.
		RestoreItem();
		Inspected.Reset();
	}
	Super::EndPlay(EndPlayReason);
}
