#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameplayTagContainer.h"
#include "AI/LBApparitionLogic.h"
#include "LBWardenApparition.generated.h"

class UMaterialInstanceDynamic;
class UMeshComponent;
class USceneComponent;
class USkeletalMeshComponent;
class UStaticMeshComponent;

/**
 * A scripted, one-shot appearance of the Warden (P12 fix set 1; replaces the old BP_WardenSilhouette). Not the AI: it never
 * moves on its own and has no collision.
 *
 * A world-state tag starts it. After ArmDelaySeconds it goes through the stations in order. At each station it stays hidden
 * until the player looks at it (the look point is inside the view cone with a clear line of sight), then turns to face the
 * player, fades in, holds and fades out. After the last station it never runs again, and if the tag is already present at
 * BeginPlay (a checkpoint reload) it starts finished. The sequence itself is in LBApparitionLogic (unit tested).
 *
 * A station with a WalkPath (P13) adds a Walk phase between Hold and FadeOut: the figure walks the path at WalkSpeed, turning at
 * up to 180 degrees per second, and fades out when the path ends, or at once if the player comes within MinPlayerDistance of it.
 *
 * Meshes and materials are set in the Blueprint. Every material slot of Body and Glow gets a dynamic instance, and the scalar
 * parameter "Fade" is set on all of them to the current alpha. With bUseSkeletalFigure the animated Figure (the Warden's skeletal
 * mesh with its Animation Blueprint) is shown instead of Body, and its slots get the fade instances.
 */
UCLASS(Blueprintable)
class LASTBELL_API ALBWardenApparition : public AActor
{
	GENERATED_BODY()

public:
	ALBWardenApparition();

	/** World-state tag that starts the appearance. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Apparition", meta = (ExposeOnSpawn = "true"))
	FGameplayTag TriggerTag;

	/** Seconds between the tag being added and the first station starting to wait for the player's eyes. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Apparition", meta = (ClampMin = "0", Units = "s", ExposeOnSpawn = "true"))
	float ArmDelaySeconds = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Apparition", meta = (ExposeOnSpawn = "true"))
	TArray<FLBApparitionStation> Stations;

	/** Height above a station's location of the point the player has to look at. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Apparition", meta = (ClampMin = "0", Units = "cm"))
	float LookPointHeight = 200.f;

	/** Size of the Glow card in cm (the card's relative scale is set to this / 100 at BeginPlay). 0 hides the glow. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Apparition", meta = (ClampMin = "0", Units = "cm"))
	float GlowSizeCm = 0.f;

	/**
	 * Show the skeletal Figure (animated, walks) instead of the static Body. Set in the Blueprint together with the Figure's mesh and
	 * Animation Blueprint. When false the Figure stays hidden and has no fade materials.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Apparition", meta = (ExposeOnSpawn = "true"))
	bool bUseSkeletalFigure = false;

	/** The figure's fade, 0 (hidden) to 1 (fully there). */
	UFUNCTION(BlueprintPure, Category = "Apparition")
	float GetAlpha() const { return Run.Alpha; }

	UFUNCTION(BlueprintPure, Category = "Apparition")
	ELBApparitionPhase GetPhase() const { return Run.Phase; }

	/** Index of the station the run is on. */
	UFUNCTION(BlueprintPure, Category = "Apparition")
	int32 GetStationIndex() const { return Run.Station; }

	UStaticMeshComponent* GetBody() const { return Body; }
	USkeletalMeshComponent* GetFigure() const { return Figure; }
	UStaticMeshComponent* GetGlow() const { return Glow; }

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void Tick(float DeltaSeconds) override;

private:
	UFUNCTION()
	void HandleWorldStateChanged(FGameplayTag Tag, bool bAdded);

	UFUNCTION()
	void HandleWorldStateReplaced();

	/** Hide and stop ticking; the run itself is left as it is. */
	void StopShowing();
	void BeginRun();
	void MakeFadeMaterials(UMeshComponent* Mesh);
	void ApplyAlpha();
	/** Moves and turns along the station's WalkPath for this tick. Returns true once the last point is reached. */
	bool AdvanceWalk(const FLBApparitionStation& Station, float DeltaSeconds);
	bool IsTagPresent() const;
	bool IsLookedAt(const FLBApparitionStation& Station, const FVector& CameraLocation, const FRotator& CameraRotation) const;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<USceneComponent> Root;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UStaticMeshComponent> Body;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UStaticMeshComponent> Glow;

	/** Optional animated figure (P13). Hidden unless bUseSkeletalFigure. No collision, no shadows. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<USkeletalMeshComponent> Figure;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> FadeMaterials;

	FLBApparitionRun Run;

	/** Next point of the current station's WalkPath. */
	int32 WalkIndex = 0;
	bool bWalkFinished = false;
};
