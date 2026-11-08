#include "Storm/LBStormFXLogic.h"

namespace LBStormFXLogic
{
	namespace
	{
		/** The card's local 100 cm in world units per 1.0 of scale. */
		constexpr double CardSize = 100.0;
	}

	FTransform SkyBoltTransform(const FVector& Camera, const FVector& Direction, float Distance, float TopHeight, float Length, float Aspect)
	{
		FVector Horizontal(Direction.X, Direction.Y, 0.0);
		if (!Horizontal.Normalize())
		{
			Horizontal = FVector(1.0, 0.0, 0.0);
		}
		const FVector Top = Camera + Horizontal * static_cast<double>(Distance) + FVector(0.0, 0.0, TopHeight);
		const FQuat Rotation = FRotationMatrix::MakeFromYZ(Horizontal, FVector::UpVector).ToQuat();
		const FVector Scale(Length * Aspect / CardSize, 1.0, Length / CardSize);
		return FTransform(Rotation, Top, Scale);
	}

	FTransform StrikeBoltTransform(const FVector& Start, const FVector& End, const FVector& Camera, float Width)
	{
		FVector Up = Start - End;
		const double Length = Up.Size();
		if (!Up.Normalize())
		{
			Up = FVector::UpVector;
		}
		// The card normal: from the camera toward the middle of the bolt, with the part along the bolt taken out.
		const FVector Middle = (Start + End) * 0.5;
		const FVector ToBolt = Middle - Camera;
		FVector Normal = ToBolt - Up * FVector::DotProduct(ToBolt, Up);
		if (!Normal.Normalize())
		{
			// The camera is on the bolt's axis: any direction across it will do.
			Normal = FVector::CrossProduct(Up, FVector::XAxisVector);
			if (!Normal.Normalize())
			{
				Normal = FVector::YAxisVector;
			}
		}
		const FQuat Rotation = FRotationMatrix::MakeFromZY(Up, Normal).ToQuat();
		const FVector Scale(Width / CardSize, 1.0, Length / CardSize);
		return FTransform(Rotation, Start, Scale);
	}

	FVector RainWind(const FVector& WindDirection, float WindStrength, float Lean)
	{
		return WindDirection.GetSafeNormal2D() * (static_cast<double>(WindStrength) * Lean);
	}

	float MistAmount(float Exposure, float MinExposure)
	{
		return FMath::SmoothStep(MinExposure - 0.1f, MinExposure + 0.1f, Exposure);
	}

	bool RollBolt(float Chance, float Roll)
	{
		return Roll < Chance;
	}
}
