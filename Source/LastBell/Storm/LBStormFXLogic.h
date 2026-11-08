#pragma once

#include "CoreMinimal.h"

/**
 * Pure maths of the storm's particle FX (P15-1, Docs/plans/P15_PARTICLES.md section 2.4). No UObject, no world: ULBStormFXSubsystem
 * gathers the facts and applies the results. Unit tested (LastBell.StormFX.Logic.*).
 *
 * The bolt card mesh (SM_LB_FX_BoltCard) is a 100 x 100 cm plane in XZ, pivot at the top centre, extending down local -Z, normal
 * local +Y. A bolt transform therefore puts the pivot at the top of the bolt, scales X by the width, Z by the length, and turns the
 * card so +Y is the horizontal direction from the camera to the bolt (the material is two-sided).
 */
namespace LBStormFXLogic
{
	/**
	 * A sky bolt card. The bolt hangs Distance cm from Camera along the horizontal part of Direction ((1, 0) when that is zero), its top
	 * TopHeight cm above the camera, Length cm long and Length * Aspect wide. Returns the transform for a 100 cm card mesh: location =
	 * the top, scale (Length * Aspect / 100, 1, Length / 100), local +Y = horizontal camera-to-bolt direction.
	 */
	LASTBELL_API FTransform SkyBoltTransform(const FVector& Camera, const FVector& Direction, float Distance, float TopHeight, float Length, float Aspect);

	/**
	 * A strike bolt card from Start (the top, in the clouds) to End (the target). The card's local +Z points from End to Start and its
	 * scaled length is |Start - End|, so the bottom of the card (local -100 Z) lands on End. It turns around that axis to face the camera.
	 * Width is the card width in cm.
	 */
	LASTBELL_API FTransform StrikeBoltTransform(const FVector& Start, const FVector& End, const FVector& Camera, float Width);

	/** The rain's wind drift in cm/s: the horizontal part of WindDirection, normalised, times WindStrength times Lean (cm/s). */
	LASTBELL_API FVector RainWind(const FVector& WindDirection, float WindStrength, float Lean);

	/** Low mist outdoors: smoothstep(MinExposure - 0.1, MinExposure + 0.1, Exposure). */
	LASTBELL_API float MistAmount(float Exposure, float MinExposure);

	/** True when the roll (0..1) is under the chance, so a chance of 1 always draws and a chance of 0 never does. */
	LASTBELL_API bool RollBolt(float Chance, float Roll);
}
