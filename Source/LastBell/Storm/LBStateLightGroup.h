#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameplayTagContainer.h"
#include "Storm/LBStormLogic.h"
#include "Storm/LBStormTypes.h"
#include "LBStateLightGroup.generated.h"

class ALight;
class ULightComponent;
class UMaterialInstanceDynamic;

/**
 * Dims, kills or flickers a set of placed lights from the story tags (P14 section 8). The Rules are in story order and the last
 * one whose tag is present wins; with none present the lights are On at their base intensity.
 *
 *   - The base intensity of every light is recorded at BeginPlay.
 *   - BeginPlay and OnStateReplaced (a checkpoint load) apply the rule instantly, so a load is correct on the first frame.
 *   - A change through OnStateChanged fades over FadeSeconds, with a guttering noise, so the player sees the light die.
 *   - The actor ticks only while it is fading or a Flicker rule is in force.
 *
 * Lights: placed light actors only. Never a Blueprint light, a puzzle candle's flame light, the Warden's tell light or the player's
 * candle (the player candle writes its own intensity every tick). A light listed in two groups is a setup error (a Warning is
 * logged at BeginPlay and the setup test catches it).
 *
 * GlowActors (P14-1b, D-099): actors whose material slots glow with a vector parameter (a lantern's glass). Each is paired with the
 * nearest light in Lights, and its glow slots follow that light's intensity, so the glass dims, flickers and goes dark with the light.
 * A glow actor listed in two groups is a setup error, like a duplicated light.
 */
UCLASS()
class LASTBELL_API ALBStateLightGroup : public AActor
{
	GENERATED_BODY()

public:
	ALBStateLightGroup();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Light Group")
	TArray<TObjectPtr<ALight>> Lights;

	/** Hidden (SetActorHiddenInGame) while the mode is Off, shown in any other mode: flame or glow meshes. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Light Group")
	TArray<TObjectPtr<AActor>> EmissiveActors;

	/**
	 * Actors whose glowing material slots follow the nearest light of this group (a lantern's glass). Every mesh component slot whose
	 * material has the vector parameter GlowParameter is driven: the parameter is the base colour scaled by light / base light.
	 * Independent of EmissiveActors.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Light Group")
	TArray<TObjectPtr<AActor>> GlowActors;

	/** The vector material parameter scaled on the glow slots. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Light Group")
	FName GlowParameter = TEXT("Color");

	/** In story order; the last rule whose RequiredTag is present wins. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Light Group")
	TArray<FLBLightStateRule> Rules;

	/** How long a live change takes. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Light Group", meta = (ClampMin = "0", Units = "s"))
	float FadeSeconds = 1.5f;

	/** The mode in force right now. */
	UFUNCTION(BlueprintPure, Category = "Light Group")
	ELBLightStateMode GetCurrentMode() const { return CurrentRule.Mode; }

	/** True while a fade is running. */
	UFUNCTION(BlueprintPure, Category = "Light Group")
	bool IsFading() const { return bFading; }

	/** The scale (of the base intensity) the first light has now, 1 when the group has no light. For tests and debugging. */
	float GetCurrentScale() const { return Entries.IsEmpty() ? 1.f : Entries[0].AppliedScale; }

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void Tick(float DeltaSeconds) override;

private:
	/** One glow material slot: the dynamic instance made for it and the parameter's value before the group touched it. */
	struct FGlowSlot
	{
		TWeakObjectPtr<UMaterialInstanceDynamic> Material;
		FLinearColor Base = FLinearColor::Black;
	};

	struct FEntry
	{
		TWeakObjectPtr<ULightComponent> Component;
		/** The glow slots of the glow actors paired with this light. */
		TArray<FGlowSlot> Glow;
		float Base = 0.f;
		/** A per-light offset into the flicker noise (from the light's name), so lights do not flicker in step. */
		float Seed = 0.f;
		float AppliedScale = 1.f;
		float FadeFrom = 1.f;
	};

	UFUNCTION()
	void HandleStateChanged(FGameplayTag Tag, bool bAdded);

	UFUNCTION()
	void HandleStateReplaced();

	LBStormLogic::FLightRule SelectRule() const;
	void ApplyInstant();
	void BeginFade(const LBStormLogic::FLightRule& NewRule);
	void WriteScale(FEntry& Entry, float Scale);
	void WriteGlow(const FEntry& Entry, float Scale) const;
	/** EntryLights[i] is the light actor of Entries[i]. */
	void BuildGlow(const TArray<const ALight*>& EntryLights);
	void ShowEmissive(bool bShow);
	void UpdateTickState();
	void WarnAboutDuplicates() const;

	TArray<FEntry> Entries;
	LBStormLogic::FLightRule CurrentRule;
	bool bFading = false;
	float FadeElapsed = 0.f;
};
