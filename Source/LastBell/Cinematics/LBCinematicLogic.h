#pragma once

#include "CoreMinimal.h"
#include "Containers/BitArray.h"
#include "Cinematics/LBCinematicTypes.h"

/**
 * Pure, engine-light cinematic logic (plan P17 sections 2.1, 2.8 and 2.10), so it can be unit tested without a world: the marker
 * grammar, which markers a time step crosses, what a skip fires, the easing helpers, the bell pendulum and the credits speed.
 */
namespace LBCinematicLogic
{
	/**
	 * Parses one marker label: [!]kind[:arg[,arg]], case-sensitive, no spaces.
	 *   card:<CardId>              tag:<Tag>                 bell:<Stage>x<Strikes>
	 *   strike:<ActorTag>[,<B>]    flash:<B>                 look:<ActorTag>[,<Seconds>]
	 *   mark:<ActorTag>[,<Seconds>] lock:<None|Look|Full>    skip:<0|1>
	 *   mix:<on|off>               credits[:<Seconds>]       end
	 * A tag: label needs a gameplay tag the project knows. Returns false with a reason in OutError; OutMarker.Seconds is not touched.
	 */
	LASTBELL_API bool ParseMarker(const FString& Label, FLBCineMarker& OutMarker, FString& OutError);

	/** Stable sort by Seconds (markers on the same frame keep their authored order). */
	LASTBELL_API void SortMarkers(TArray<FLBCineMarker>& Markers);

	/**
	 * The markers a step from PrevSeconds to CurSeconds crosses, in order: those with Prev < Seconds <= Cur that FiredMask does not
	 * have set. Sets the mask for each one returned, so a marker never fires twice. A step that does not move forward (a backward jump,
	 * or no time passed) returns none. The mask is resized to Sorted. Start a run with Prev = -1 so markers at time 0 fire.
	 */
	LASTBELL_API void MarkersToFire(const TArray<FLBCineMarker>& Sorted, double PrevSeconds, double CurSeconds, TBitArray<>& FiredMask, TArray<int32>& OutIndices);

	/** What a skip fires: the must markers (bMust) that FiredMask does not have set, in order. Sets the mask for each one returned. */
	LASTBELL_API void MustMarkersOnSkip(const TArray<FLBCineMarker>& Sorted, TBitArray<>& FiredMask, TArray<int32>& OutIndices);

	/** 3t^2 - 2t^3 on a clamped 0..1. */
	LASTBELL_API float Smoothstep(float Alpha);

	/** Degrees along the shortest way round from FromYaw to ToYaw at Alpha (0..1, not eased). The result is not normalised. */
	LASTBELL_API float ShortestYawLerp(float FromYaw, float ToYaw, float Alpha);

	/** A card's opacity 0..1 at Elapsed seconds: fade in over Fade, hold, fade out over Fade. Zero before 0 and after 2*Fade + Hold. */
	LASTBELL_API float CardOpacity(float Elapsed, float Fade, float Hold);

	/** The whole life of a card in seconds. */
	LASTBELL_API float CardDuration(float Fade, float Hold);

	/** Credits scroll speed in px/s: the box travels its own height plus the viewport height in Seconds. */
	LASTBELL_API float CreditsPixelsPerSecond(float BoxHeight, float ViewportHeight, float Seconds);

	/**
	 * The bell's swing (section 2.8): angle(t) = A * e^(-d*t) * sin(2*pi*t/P). Each kick adds to A (clamped), keeping the phase so a
	 * kick during a swing does not jump the angle. Below StopDegrees the swing stops and the bell is exactly at rest.
	 */
	struct LASTBELL_API FBellPendulum
	{
		/** The current amplitude envelope A * e^(-d*t), degrees. */
		float AmplitudeDeg = 0.f;
		/** Radians. */
		float Phase = 0.f;

		/** Adds KickDeg to the amplitude, never above MaxDeg. A kick from rest starts the swing at phase 0. */
		void Kick(float KickDeg, float MaxDeg);

		/** Advances by Dt seconds. Returns false when the swing has just stopped or was already at rest. */
		bool Advance(float Dt, float PeriodSeconds, float DampingPerSecond, float StopDeg);

		/** The angle now, degrees (0 at rest). */
		float AngleDeg() const;

		bool IsSwinging() const { return AmplitudeDeg > 0.f; }

		void Reset() { AmplitudeDeg = 0.f; Phase = 0.f; }
	};

	/**
	 * The transform of a piece that turns about the axle: Q = FQuat(Axis, AngleDeg), location Pivot + Q * (Rest - Pivot), rotation
	 * Q * RestRotation. Axis is a unit world vector. At 0 degrees it returns the rest transform exactly; a piece at the pivot stays there.
	 */
	LASTBELL_API FTransform SwingAboutAxle(const FVector& RestLocation, const FQuat& RestRotation, const FVector& Pivot, const FVector& Axis, float AngleDeg);

	/** The rope: its rest X and Y, and the Z that SwingAboutAxle gives the rope's top. */
	LASTBELL_API FVector RopeZAboutAxle(const FVector& RopeRestLocation, const FVector& Pivot, const FVector& Axis, float AngleDeg);

	/** The axle's world axis: the headstock's rest rotation applied to local Y (Pitch) or local X (Roll). */
	LASTBELL_API FVector AxleAxis(const FQuat& HeadstockRestRotation, ELBBellSwingAxis SwingAxis);

	/**
	 * The hold-to-skip timer. Tick returns true exactly once per hold, when it has been held for Needed seconds while skippable.
	 * Time held while not skippable does not count: the count starts when the cinematic becomes skippable.
	 */
	struct LASTBELL_API FSkipHold
	{
		bool bHolding = false;
		bool bTriggered = false;
		float Held = 0.f;

		void Begin() { bHolding = true; bTriggered = false; Held = 0.f; }
		void End() { bHolding = false; bTriggered = false; Held = 0.f; }
		bool Tick(float Dt, float Needed, bool bSkippable);
		float Fraction(float Needed) const { return Needed > UE_SMALL_NUMBER ? FMath::Clamp(Held / Needed, 0.f, 1.f) : 0.f; }
	};
}
