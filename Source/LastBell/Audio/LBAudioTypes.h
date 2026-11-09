#pragma once

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"
#include "LBAudioTypes.generated.h"

/** The user volume groups (plan P16 section 2.3, "User volumes"). Master is the parent SoundClass of the other five. */
UENUM(BlueprintType)
enum class ELBAudioVolumeGroup : uint8
{
	Master,
	SFX,
	Ambience,
	Music,
	Voice,
	UI
};

/**
 * One story beat of the great bell (plan P16 section 5.3). It fires only when TriggerTag is ADDED to the world state while playing
 * (never at BeginPlay and never on a state replace, so a checkpoint load plays nothing).
 */
USTRUCT(BlueprintType)
struct LASTBELL_API FLBBellBeat
{
	GENERATED_BODY()

	/** World-state tag whose addition triggers the beat. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell")
	FGameplayTag Trigger;

	/**
	 * Which bell recording (FLBAudioBell::Stage[Stage - 1]): 1 is the farthest, 5 the finale. It also sets the "current stage" that
	 * ambient tolls play (the highest Stage among the beats reached).
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell", meta = (ClampMin = "1", ClampMax = "5"))
	int32 Stage = 1;

	/** Strikes tolled. 0 makes the beat a drone-only beat (State.Event.CryptEntered). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell", meta = (ClampMin = "0", ClampMax = "12"))
	int32 Strikes = 3;

	/** Seconds from the tag being added to the first strike. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell", meta = (ClampMin = "0", ClampMax = "60", Units = "s"))
	float FirstDelay = 2.f;

	/** Seconds from one strike to the next. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell", meta = (ClampMin = "0", ClampMax = "30", Units = "s"))
	float Spacing = 4.5f;

	/** Which drone starts with this beat: an index into FLBAudioMusic::Drones (0 A, 1 B, 2 C), or -1 for none. An addition to the plan table. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bell", meta = (ClampMin = "-1", ClampMax = "7"))
	int32 Drone = -1;
};

/** Names of the play requests the audio subsystem records in its test sink (and writes to the debug readout). */
namespace LBAudioCue
{
	// Loops start (one request per start).
	inline const FName LoopRainOut(TEXT("Loop.RainOut"));
	inline const FName LoopRainIn(TEXT("Loop.RainIn"));
	inline const FName LoopWind(TEXT("Loop.Wind"));
	inline const FName LoopWindHowl(TEXT("Loop.WindHowl"));
	inline const FName LoopRoomTone(TEXT("Loop.RoomTone"));
	inline const FName LoopDrone(TEXT("Loop.Drone"));
	inline const FName LoopTension(TEXT("Loop.Tension"));
	inline const FName LoopChase(TEXT("Loop.Chase"));
	// One-shots.
	inline const FName Thunder(TEXT("Thunder"));
	inline const FName ThunderStrike(TEXT("ThunderStrike"));
	inline const FName Bell(TEXT("Bell"));
	inline const FName BellAmbient(TEXT("BellAmbient"));
	inline const FName StingSpotted(TEXT("Sting.Spotted"));
	inline const FName StingCaught(TEXT("Sting.Caught"));
	inline const FName StingApparition(TEXT("Sting.Apparition"));
	inline const FName ApparitionWhisper(TEXT("Apparition.Whisper"));
	inline const FName ApparitionChain(TEXT("Apparition.Chain"));
	inline const FName Breath(TEXT("Breath"));
	inline const FName BreathGasp(TEXT("Breath.Gasp"));
	inline const FName CandleLight(TEXT("Candle.Light"));
	inline const FName CandleOut(TEXT("Candle.Out"));
	inline const FName CandleRelight(TEXT("Candle.Relight"));
	inline const FName Interact(TEXT("Interact"));
	inline const FName Denied(TEXT("Denied"));
	inline const FName DialNotch(TEXT("DialNotch"));
	inline const FName SmallBellStrike(TEXT("SmallBell.Strike"));
	inline const FName SmallBellFail(TEXT("SmallBell.Fail"));
	inline const FName SmallBellSolved(TEXT("SmallBell.Solved"));
	inline const FName Footstep(TEXT("Footstep"));
	inline const FName Emitter(TEXT("Emitter"));
	inline const FName WardenStep(TEXT("Warden.Step"));
	inline const FName WardenChain(TEXT("Warden.Chain"));
	inline const FName WardenSpotted(TEXT("Warden.Spotted"));
	inline const FName WardenRoar(TEXT("Warden.Roar"));
	inline const FName WardenWindup(TEXT("Warden.Windup"));
	inline const FName WardenExhale(TEXT("Warden.Exhale"));
	inline const FName WardenCaught(TEXT("Warden.Caught"));
	inline const FName LoopWardenBreath(TEXT("Loop.Warden.Breath"));
	inline const FName LoopWardenRobe(TEXT("Loop.Warden.Robe"));
}
