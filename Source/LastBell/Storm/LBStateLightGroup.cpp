#include "Storm/LBStateLightGroup.h"
#include "Systems/LBWorldStateSubsystem.h"
#include "Components/LightComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/Light.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "LBLog.h"

ALBStateLightGroup::ALBStateLightGroup()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;

	USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);
}

void ALBStateLightGroup::BeginPlay()
{
	Super::BeginPlay();

	Entries.Reset();
	for (ALight* Light : Lights)
	{
		ULightComponent* Component = Light ? Light->GetLightComponent() : nullptr;
		if (!Component)
		{
			continue;
		}
		FEntry& Entry = Entries.AddDefaulted_GetRef();
		Entry.Component = Component;
		Entry.Base = Component->Intensity;
		Entry.Seed = static_cast<float>(GetTypeHash(Light->GetFName()) % 1000u) * 0.137f;
	}

	WarnAboutDuplicates();

	if (ULBWorldStateSubsystem* WorldState = ULBWorldStateSubsystem::Get(this))
	{
		WorldState->OnStateChanged.AddDynamic(this, &ALBStateLightGroup::HandleStateChanged);
		WorldState->OnStateReplaced.AddDynamic(this, &ALBStateLightGroup::HandleStateReplaced);
	}

	// The rule for the tags present right now, applied before the first frame is drawn.
	ApplyInstant();
}

void ALBStateLightGroup::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (ULBWorldStateSubsystem* WorldState = ULBWorldStateSubsystem::Get(this))
	{
		WorldState->OnStateChanged.RemoveDynamic(this, &ALBStateLightGroup::HandleStateChanged);
		WorldState->OnStateReplaced.RemoveDynamic(this, &ALBStateLightGroup::HandleStateReplaced);
	}
	Super::EndPlay(EndPlayReason);
}

void ALBStateLightGroup::WarnAboutDuplicates() const
{
	const UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	for (TActorIterator<ALBStateLightGroup> It(World); It; ++It)
	{
		const ALBStateLightGroup* Other = *It;
		// Each pair is reported once, by the group at the lower address.
		if (Other == this || Other >= this)
		{
			continue;
		}
		for (ALight* Light : Lights)
		{
			if (Light && Other->Lights.Contains(Light))
			{
				UE_LOG(LogLB, Warning, TEXT("State light groups %s and %s both list the light %s; its base intensity and scale would fight"),
					*GetName(), *Other->GetName(), *Light->GetName());
			}
		}
	}
}

LBStormLogic::FLightRule ALBStateLightGroup::SelectRule() const
{
	const ULBWorldStateSubsystem* WorldState = ULBWorldStateSubsystem::Get(this);
	if (!WorldState)
	{
		return LBStormLogic::FLightRule();
	}
	return LBStormLogic::SelectLightRule(Rules, WorldState->GetStateRef());
}

void ALBStateLightGroup::WriteScale(FEntry& Entry, float Scale)
{
	Scale = FMath::Max(Scale, 0.f);
	if (FMath::IsNearlyEqual(Scale, Entry.AppliedScale, 1.0e-4f))
	{
		return;
	}
	if (ULightComponent* Component = Entry.Component.Get())
	{
		Component->SetIntensity(Entry.Base * Scale);
	}
	Entry.AppliedScale = Scale;
}

void ALBStateLightGroup::ShowEmissive(bool bShow)
{
	for (AActor* Actor : EmissiveActors)
	{
		if (Actor)
		{
			Actor->SetActorHiddenInGame(!bShow);
		}
	}
}

void ALBStateLightGroup::UpdateTickState()
{
	SetActorTickEnabled(bFading || CurrentRule.Mode == ELBLightStateMode::Flicker);
}

void ALBStateLightGroup::ApplyInstant()
{
	CurrentRule = SelectRule();
	bFading = false;
	FadeElapsed = 0.f;
	const UWorld* World = GetWorld();
	const float Time = World ? static_cast<float>(World->GetTimeSeconds()) : 0.f;
	for (FEntry& Entry : Entries)
	{
		Entry.FadeFrom = Entry.AppliedScale;
		WriteScale(Entry, LBStormLogic::LightScaleAt(CurrentRule, Time, Entry.Seed));
	}
	ShowEmissive(CurrentRule.Mode != ELBLightStateMode::Off);
	UpdateTickState();
}

void ALBStateLightGroup::BeginFade(const LBStormLogic::FLightRule& NewRule)
{
	CurrentRule = NewRule;
	if (FadeSeconds <= UE_KINDA_SMALL_NUMBER)
	{
		ApplyInstant();
		return;
	}
	bFading = true;
	FadeElapsed = 0.f;
	for (FEntry& Entry : Entries)
	{
		Entry.FadeFrom = Entry.AppliedScale;
	}
	// A glow or flame mesh comes back at once; it goes away when the fade is over.
	if (CurrentRule.Mode != ELBLightStateMode::Off)
	{
		ShowEmissive(true);
	}
	UpdateTickState();
}

void ALBStateLightGroup::HandleStateChanged(FGameplayTag Tag, bool bAdded)
{
	const LBStormLogic::FLightRule NewRule = SelectRule();
	if (NewRule == CurrentRule)
	{
		return;
	}
	BeginFade(NewRule);
}

void ALBStateLightGroup::HandleStateReplaced()
{
	// A checkpoint load or a new game: no fade, the right state at once.
	ApplyInstant();
}

void ALBStateLightGroup::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	const UWorld* World = GetWorld();
	const float Time = World ? static_cast<float>(World->GetTimeSeconds()) : 0.f;

	float Alpha = 1.f;
	bool bJustFinished = false;
	if (bFading)
	{
		FadeElapsed += DeltaSeconds;
		Alpha = FadeSeconds > UE_KINDA_SMALL_NUMBER ? FadeElapsed / FadeSeconds : 1.f;
		if (Alpha >= 1.f)
		{
			Alpha = 1.f;
			bFading = false;
			bJustFinished = true;
		}
	}

	for (FEntry& Entry : Entries)
	{
		const float Target = LBStormLogic::LightScaleAt(CurrentRule, Time, Entry.Seed);
		const float Scale = (bFading || bJustFinished) ? LBStormLogic::FadeScale(Entry.FadeFrom, Target, Alpha, Time + Entry.Seed) : Target;
		WriteScale(Entry, Scale);
	}

	if (bJustFinished && CurrentRule.Mode == ELBLightStateMode::Off)
	{
		ShowEmissive(false);
	}
	UpdateTickState();
}
