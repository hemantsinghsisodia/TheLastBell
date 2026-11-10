#pragma once

#include "CoreMinimal.h"
#include "Containers/BitArray.h"
#include "GameplayTagContainer.h"
#include "Subsystems/WorldSubsystem.h"
#include "Cinematics/LBCinematicLogic.h"
#include "Cinematics/LBCinematicTypes.h"
#include "LBCinematicSubsystem.generated.h"

class AActor;
class ALBCharacter;
class ALevelSequenceActor;
class ULBCinematicSettings;
class ULBCinematicWidget;
class ULevelSequence;
class ULevelSequencePlayer;
class USceneComponent;
class USoundMix;
class ULBWorldStateSubsystem;
class ULBAudioSubsystem;

DECLARE_MULTICAST_DELEGATE_OneParam(FLBCineIdSignature, FName /*Id*/);
DECLARE_MULTICAST_DELEGATE_OneParam(FLBCineMarkerSignature, const FString& /*Label*/);

/**
 * The cinematic director (plan P17 section 2.3). Level Sequences hold the cameras, the figure, the lantern and the fades; every action
 * the game must take at a moment is a labelled Sequencer marker (grammar in LBCinematicLogic::ParseMarker) that this subsystem carries
 * out: story cards, world-state tags, the great bell, lightning, look assists, moving the player to a mark, input locks, skippability,
 * the audio mix, the credits roll and the end of the game. It also starts the intro on New Game, plays the finale when its tag is
 * added, swings the great bell with its headstock and rope on every great-bell strike, and always puts the player back: if anything
 * fails it fires the must markers, restores input and the view, and logs an Error.
 *
 * It exists in Game and PIE worlds. Without DA_Cinematics (ULBGameSettings::CinematicSettings) it does nothing for the world.
 * NEVER Live Code LBCinematicSubsystem.cpp: it defines the lb.Cine.* CVars as file statics.
 */
UCLASS()
class LASTBELL_API ULBCinematicSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	// ---- Subsystem plumbing ---------------------------------------------------------------------------------------------------
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;
	virtual ETickableTickType GetTickableTickType() const override;
	/** Ticks only while a cinematic is about to start or plays, or the bell swings. */
	virtual bool IsTickable() const override;

	// ---- Control --------------------------------------------------------------------------------------------------------------

	/**
	 * Plays the cinematic with this Id from the settings (also lb.Cine.Play). Manual: it ignores the trigger and the blocking tag.
	 * False when one is already playing, lb.Cine.Enabled is 0, the Id is unknown or there are no settings.
	 */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Cinematics")
	bool Play(FName Id);

	/** Plays any Level Sequence through a temporary definition (InitialLock Full, skippable): lb.Cine.PlayAsset, for spikes and reviews. */
	bool PlayAsset(const FSoftObjectPath& SequencePath);

	/** Skips: fires the must markers not yet fired, jumps to the end, fades up from black and restores. Works even when not skippable. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Cinematics")
	void RequestSkip();

	/** Stops at once (restore; no must markers). */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Cinematics")
	void StopCinematic();

	/** The character's locked Interact press and release feed this (the subsystem binds them while it plays). */
	void BeginSkipHold();
	void EndSkipHold();

	/** Uses these settings instead of ULBGameSettings::CinematicSettings (tests, tools). Call Rearm afterwards. */
	void OverrideSettings(ULBCinematicSettings* InSettings);

	/** Reloads the settings and finds the bell pieces again, rebinding the world state and the audio. Tests that add actors or settings after begin play call it. */
	void Rearm();

	// ---- Queries --------------------------------------------------------------------------------------------------------------

	/** A cinematic is playing (from Play until its restore). Checkpoints refuse to save while this is true. */
	UFUNCTION(BlueprintPure, Category = "LastBell|Cinematics")
	bool IsPlaying() const { return bRunActive; }

	/** The Id of the cinematic playing, or None. */
	UFUNCTION(BlueprintPure, Category = "LastBell|Cinematics")
	FName GetActiveId() const { return bRunActive ? RunDef.Id : NAME_None; }

	/** The New Game intro was chosen at world begin play and has not started yet (it starts on the first tick). */
	bool IsStartPending() const { return bStartPending; }

	bool IsSkippable() const { return bRunActive && bSkippable; }
	bool IsCreditsRolling() const { return bRunActive && bCreditsRolling; }
	float GetSkipHoldFraction() const;
	/** Seconds into the sequence (from the start of its playback range). */
	double GetSequenceSeconds() const { return CurSeconds; }
	int32 GetMarkerCount() const { return Markers.Num(); }
	int32 GetFiredMarkerCount() const;
	const ULBCinematicWidget* GetWidget() const { return Widget; }
	const ULBCinematicSettings* GetSettings() const { return Settings; }

	/** The bell's swing angle now, degrees (0 at rest) and whether it is swinging. */
	float GetBellAngleDegrees() const { return Pendulum.AngleDeg(); }
	bool IsBellSwinging() const { return Pendulum.IsSwinging(); }
	/** The three pieces were found at setup (the bell is required for a swing; the headstock and the rope are optional). */
	bool HasBell() const { return BellComponent.IsValid(); }
	bool HasHeadstock() const { return HeadstockActor.IsValid(); }
	bool HasRope() const { return RopeActor.IsValid(); }

	// ---- Events (for tests and Blueprints) -----------------------------------------------------------------------------------

	FLBCineIdSignature OnCinematicStarted;
	FLBCineIdSignature OnCinematicFinished;
	FLBCineMarkerSignature OnMarkerFired;

protected:
	/** Game and PIE worlds only. */
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;

private:
	struct FMarkMove
	{
		bool bActive = false;
		FVector Start = FVector::ZeroVector;
		FVector End = FVector::ZeroVector;
		float StartYaw = 0.f;
		float EndYaw = 0.f;
		float StartPitch = 0.f;
		float Elapsed = 0.f;
		float Duration = 1.f;
	};

	struct FLookAssist
	{
		bool bActive = false;
		TWeakObjectPtr<AActor> Target;
		FRotator Start = FRotator::ZeroRotator;
		float Elapsed = 0.f;
		float Duration = 1.f;
	};

	// ---- Setup ----
	void SetupWorld();
	void BindWorldEvents();
	void UnbindWorldEvents();
	void FindBellPieces();
	bool LoadSettings();
	bool ShouldStartNewGameIntro(const FLBCinematicDef& Def) const;
	bool IsEnabled() const;
	float ReadRate() const;

	UFUNCTION()
	void HandleStateChanged(FGameplayTag Tag, bool bAdded);
	UFUNCTION()
	void HandlePlayerFinished();
	void HandleGreatBellStrike(int32 Stage, float Volume);

	// ---- Run ----
	bool PlayDef(const FLBCinematicDef& Def);
	void FailRun(const FLBCinematicDef& Def, const TCHAR* Why);
	void TickRun(float ScaledDelta);
	void FinishRun(const TCHAR* Reason, bool bKeepFade = false);
	void FireMarkerAt(int32 Index);
	void FireMarker(const FLBCineMarker& Marker);
	void FireIndices(const TArray<int32>& Indices);
	void ParseMarkersOf(ULevelSequence& Sequence, double& OutDurationSeconds);
	void DoEnd();
	void ApplyLock(ELBInputLock Lock);
	void BindPlayerInput();
	void UnbindPlayerInput();

	// ---- Marker actions ----
	void StartCard(FName CardId);
	void StartMark(const FLBCineMarker& Marker);
	void StartLook(const FLBCineMarker& Marker);
	void StartCredits(float Seconds);
	void StopCredits();
	void PushMix();
	void PopMix();
	void EndMark();
	void EndLook(bool bRestoreLock);
	void TickMark(float ScaledDelta);
	void TickLook(float ScaledDelta);
	void TickCard(float ScaledDelta);
	void TickCredits(float ScaledDelta);
	void TickBell(float Delta);
	void ApplyBellAngle(float AngleDeg);
	void DrawDebug();

	// ---- Helpers ----
	ALBCharacter* GetPlayerCharacter() const;
	class APlayerController* GetPlayerController() const;
	AActor* FindActorWithTag(FName Tag) const;
	ULBWorldStateSubsystem* GetWorldState() const;

	// ---- Settings ----
	UPROPERTY(Transient)
	TObjectPtr<ULBCinematicSettings> Settings;

	/** Set by OverrideSettings; used instead of the configured asset. */
	UPROPERTY(Transient)
	TObjectPtr<ULBCinematicSettings> SettingsOverride;

	/** The class defaults object PlayAsset uses when there are no settings at all. */
	UPROPERTY(Transient)
	TObjectPtr<ULBCinematicSettings> FallbackSettings;

	bool bLoggedNoSettings = false;

	// ---- Start ----
	bool bStartPending = false;
	FLBCinematicDef StartDef;
	bool bWorldBegun = false;
	bool bStateBound = false;

	// ---- The run ----
	bool bRunActive = false;
	bool bFailSafe = false;
	FLBCinematicDef RunDef;
	TArray<FLBCineMarker> Markers;
	TBitArray<> Fired;
	double PrevSeconds = -1.0;
	double CurSeconds = 0.0;
	double SequenceSeconds = 0.0;
	float RunRate = 1.f;
	bool bSkippable = false;
	bool bPlayerFinished = false;
	bool bTravelling = false;
	bool bPushedMix = false;
	LBCinematicLogic::FSkipHold SkipHold;

	UPROPERTY(Transient)
	TObjectPtr<ULevelSequence> LoadedSequence;

	UPROPERTY(Transient)
	TObjectPtr<ULevelSequencePlayer> Player;

	UPROPERTY(Transient)
	TObjectPtr<ALevelSequenceActor> SequenceActor;

	UPROPERTY(Transient)
	TObjectPtr<ULBCinematicWidget> Widget;

	UPROPERTY(Transient)
	TObjectPtr<USoundMix> PushedMix;

	TWeakObjectPtr<ALBCharacter> BoundPlayer;
	FDelegateHandle PressedHandle;
	FDelegateHandle ReleasedHandle;

	// Card, credits, mark and look
	bool bCardActive = false;
	FLBCineCard Card;
	float CardElapsed = 0.f;
	bool bCreditsRolling = false;
	bool bEndPending = false;
	float CreditsElapsed = 0.f;
	float CreditsDuration = 40.f;
	FMarkMove Mark;
	FLookAssist Look;
	/** The lock the markers last asked for (the look assist holds Full on top of it). */
	ELBInputLock WantedLock = ELBInputLock::None;

	// ---- The bell ----
	TWeakObjectPtr<AActor> BellActor;
	TWeakObjectPtr<USceneComponent> BellComponent;
	TWeakObjectPtr<AActor> HeadstockActor;
	TWeakObjectPtr<AActor> RopeActor;
	FVector BellRestLocation = FVector::ZeroVector;
	FQuat BellRestRotation = FQuat::Identity;
	FVector HeadstockRestLocation = FVector::ZeroVector;
	FQuat HeadstockRestRotation = FQuat::Identity;
	FVector RopeRestLocation = FVector::ZeroVector;
	FVector SwingPivot = FVector::ZeroVector;
	FVector SwingAxis = FVector::YAxisVector;
	LBCinematicLogic::FBellPendulum Pendulum;
	bool bBellStrikeBound = false;
	FDelegateHandle BellStrikeHandle;
	TWeakObjectPtr<ULBAudioSubsystem> BoundAudio;
	bool bWarnedNoHeadstock = false;
	bool bWarnedNoRope = false;
	bool bWarnedImmovable = false;
};
