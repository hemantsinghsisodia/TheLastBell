#include "Components/LBInteractorComponent.h"
#include "Components/LBInteractableComponent.h"
#include "LBTraceChannels.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "GameFramework/Pawn.h"
#include "TimerManager.h"

void ULBInteractorComponent::BeginPlay()
{
	Super::BeginPlay();
	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().SetTimer(TraceTimer, this, &ULBInteractorComponent::UpdateFocus, FMath::Max(TraceInterval, 0.02f), true);
	}
}

void ULBInteractorComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().ClearTimer(TraceTimer);
	}
	Super::EndPlay(EndPlayReason);
}

ULBInteractableComponent* ULBInteractorComponent::TraceForInteractable() const
{
	const APawn* Pawn = Cast<APawn>(GetOwner());
	AController* Controller = Pawn ? Pawn->GetController() : nullptr;
	UWorld* World = GetWorld();
	if (!Controller || !World)
	{
		return nullptr;
	}

	FVector ViewLocation;
	FRotator ViewRotation;
	Controller->GetPlayerViewPoint(ViewLocation, ViewRotation);
	const FVector End = ViewLocation + ViewRotation.Vector() * TraceDistance;

	FCollisionQueryParams Params(SCENE_QUERY_STAT(LBInteract), false, GetOwner());
	FHitResult Hit;
	if (World->SweepSingleByChannel(Hit, ViewLocation, End, FQuat::Identity, LB_TRACE_INTERACTION,
		FCollisionShape::MakeSphere(TraceRadius), Params))
	{
		if (const AActor* HitActor = Hit.GetActor())
		{
			return HitActor->FindComponentByClass<ULBInteractableComponent>();
		}
	}
	return nullptr;
}

void ULBInteractorComponent::UpdateFocus()
{
	ULBInteractableComponent* NewFocus = TraceForInteractable();
	ULBInteractableComponent* OldFocus = FocusedComponent.Get();

	const bool bFocusChanged = NewFocus != OldFocus;
	if (bFocusChanged)
	{
		if (OldFocus)
		{
			OldFocus->NotifyFocusEnd();
		}
		FocusedComponent = NewFocus;
		if (NewFocus)
		{
			NewFocus->NotifyFocusBegin();
		}
	}

	FText Prompt;
	if (NewFocus && NewFocus->CanInteract(GetOwner()))
	{
		Prompt = NewFocus->PromptText;
	}

	if (bFocusChanged || !Prompt.EqualTo(LastPrompt))
	{
		LastPrompt = Prompt;
		OnFocusChanged.Broadcast(NewFocus, Prompt);
	}
}

void ULBInteractorComponent::TryInteract()
{
	UpdateFocus();
	if (ULBInteractableComponent* Focus = FocusedComponent.Get())
	{
		Focus->Interact(GetOwner());
	}
}
