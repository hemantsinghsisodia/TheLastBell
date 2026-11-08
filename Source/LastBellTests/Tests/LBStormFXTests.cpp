#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

#include "Storm/LBStormFXLogic.h"

// P15-1: pure-logic unit tests of the storm's particle FX (LastBell.StormFX.Logic.*). The subsystem, the bolt actors and the rain component
// only gather facts and apply these results; their PIE tests are in LBStormFXFunctionalTests.cpp.

#define LB_FX_TEST_FLAGS (EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

namespace LBStormFXUnitTest
{
	/** The card mesh's bottom (local 0, 0, -100), where a bolt ends. */
	FVector Bottom(const FTransform& T)
	{
		return T.TransformPosition(FVector(0.0, 0.0, -100.0));
	}

	/** The horizontal unit vector from A to B, or zero. */
	FVector Horizontal(const FVector& From, const FVector& To)
	{
		return (To - From).GetSafeNormal2D();
	}
}

// =====================================================================================================================
// SkyBoltTransform
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormFXSkyBoltTransformTest, "LastBell.StormFX.Logic.SkyBoltTransform", LB_FX_TEST_FLAGS)
bool FLBStormFXSkyBoltTransformTest::RunTest(const FString& Parameters)
{
	using namespace LBStormFXUnitTest;

	// Toward +Y: the direction's height is ignored.
	{
		const FVector Camera(1000.0, -2000.0, 300.0);
		const FTransform T = LBStormFXLogic::SkyBoltTransform(Camera, FVector(0.0, 3.0, 5.0), 60000.f, 22000.f, 20000.f, 0.35f);
		TestTrue(TEXT("The top is Distance along the horizontal direction and TopHeight above the camera"), T.GetLocation().Equals(FVector(1000.0, 58000.0, 22300.0), 0.5));
		TestTrue(TEXT("The scale is (Length * Aspect / 100, 1, Length / 100)"), T.GetScale3D().Equals(FVector(70.0, 1.0, 200.0), 1.0e-3));
		TestTrue(TEXT("The card's local +Y is the horizontal camera-to-bolt direction"), T.GetUnitAxis(EAxis::Y).Equals(FVector(0.0, 1.0, 0.0), 1.0e-4));
		TestTrue(TEXT("The card stands upright (local +Z is up)"), T.GetUnitAxis(EAxis::Z).Equals(FVector::UpVector, 1.0e-4));
		TestTrue(TEXT("The bottom of the card is Length below the top"), Bottom(T).Equals(FVector(1000.0, 58000.0, 2300.0), 0.5));
	}

	// Diagonal: the card faces the camera (its normal is the horizontal camera-to-bolt direction).
	{
		const FVector Camera(-500.0, 400.0, 170.0);
		const FTransform T = LBStormFXLogic::SkyBoltTransform(Camera, FVector(1.0, 1.0, 0.0), 40000.f, 15000.f, 16000.f, 0.5f);
		const FVector Expected = FVector(1.0, 1.0, 0.0).GetSafeNormal();
		TestTrue(TEXT("Diagonal: the top is 40000 cm away along the diagonal"), T.GetLocation().Equals(Camera + Expected * 40000.0 + FVector(0.0, 0.0, 15000.0), 0.5));
		TestTrue(TEXT("Diagonal: the normal is horizontal"), FMath::IsNearlyZero(T.GetUnitAxis(EAxis::Y).Z, 1.0e-4));
		TestTrue(TEXT("Diagonal: the normal is the camera-to-bolt direction"), T.GetUnitAxis(EAxis::Y).Equals(Horizontal(Camera, T.GetLocation()), 1.0e-4));
		TestTrue(TEXT("Diagonal: the scale is (80, 1, 160)"), T.GetScale3D().Equals(FVector(80.0, 1.0, 160.0), 1.0e-3));
	}

	// A direction with no horizontal part falls back to +X.
	{
		const FTransform T = LBStormFXLogic::SkyBoltTransform(FVector::ZeroVector, FVector::UpVector, 1000.f, 500.f, 200.f, 1.f);
		TestTrue(TEXT("Straight up: the bolt hangs along +X"), T.GetLocation().Equals(FVector(1000.0, 0.0, 500.0), 0.5));
		TestTrue(TEXT("Straight up: the normal is +X"), T.GetUnitAxis(EAxis::Y).Equals(FVector::XAxisVector, 1.0e-4));
	}
	return true;
}

// =====================================================================================================================
// StrikeBoltTransform
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormFXStrikeBoltTransformTest, "LastBell.StormFX.Logic.StrikeBoltTransform", LB_FX_TEST_FLAGS)
bool FLBStormFXStrikeBoltTransformTest::RunTest(const FString& Parameters)
{
	using namespace LBStormFXUnitTest;

	const FVector Start(500.0, 200.0, 12000.0);
	const FVector End(800.0, -100.0, 1500.0);
	const FVector Camera(-300.0, 0.0, 170.0);
	const FTransform T = LBStormFXLogic::StrikeBoltTransform(Start, End, Camera, 1400.f);

	TestTrue(TEXT("The pivot (the top of the card) is at Start"), T.GetLocation().Equals(Start, 1.0));
	TestTrue(FString::Printf(TEXT("The bottom of the card is within 1 cm of End (%s)"), *Bottom(T).ToString()), Bottom(T).Equals(End, 1.0));

	const FVector Axis = (Start - End).GetSafeNormal();
	TestTrue(TEXT("The card's up axis is Start - End"), T.GetUnitAxis(EAxis::Z).Equals(Axis, 1.0e-4));
	TestTrue(TEXT("The scale is (Width / 100, 1, |Start - End| / 100)"), T.GetScale3D().Equals(FVector(14.0, 1.0, (Start - End).Size() / 100.0), 1.0e-3));

	// Facing the camera: the normal is the part of the camera-to-bolt direction that is across the axis.
	const FVector Normal = T.GetUnitAxis(EAxis::Y);
	const FVector ToBolt = (Start + End) * 0.5 - Camera;
	const FVector Across = (ToBolt - Axis * FVector::DotProduct(ToBolt, Axis)).GetSafeNormal();
	TestTrue(TEXT("The card normal is perpendicular to the bolt axis"), FMath::IsNearlyZero(FVector::DotProduct(Normal, Axis), 1.0e-4));
	TestTrue(TEXT("The card faces the camera (normal along the camera-to-bolt direction across the axis)"), FMath::IsNearlyEqual(FVector::DotProduct(Normal, Across), 1.0, 1.0e-4));
	TestTrue(TEXT("The rotation is a proper rotation (X x Y = Z)"), FVector::CrossProduct(T.GetUnitAxis(EAxis::X), Normal).Equals(T.GetUnitAxis(EAxis::Z), 1.0e-4));

	// A vertical strike with the camera straight below its axis: no division by zero, still spans Start to End.
	{
		const FVector High(0.0, 0.0, 9000.0);
		const FVector Low(0.0, 0.0, 1000.0);
		const FTransform Degenerate = LBStormFXLogic::StrikeBoltTransform(High, Low, FVector(0.0, 0.0, 170.0), 800.f);
		TestTrue(TEXT("Camera on the axis: the card still spans Start to End"), Bottom(Degenerate).Equals(Low, 1.0));
		TestTrue(TEXT("Camera on the axis: the normal is horizontal"), FMath::IsNearlyZero(Degenerate.GetUnitAxis(EAxis::Y).Z, 1.0e-4));
		TestTrue(TEXT("Camera on the axis: the rotation is finite"), !Degenerate.GetRotation().ContainsNaN());
	}
	return true;
}

// =====================================================================================================================
// RainWind, MistAmount, RollBolt
// =====================================================================================================================

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormFXRainWindTest, "LastBell.StormFX.Logic.RainWind", LB_FX_TEST_FLAGS)
bool FLBStormFXRainWindTest::RunTest(const FString& Parameters)
{
	// The horizontal part of the direction, normalised, times strength times lean.
	const FVector Wind = LBStormFXLogic::RainWind(FVector(0.87, 0.5, 0.3), 0.6f, 500.f);
	const FVector Expected = FVector(0.87, 0.5, 0.0).GetSafeNormal() * 300.0;
	TestTrue(FString::Printf(TEXT("A slanted direction: horizontal, normalised, 0.6 * 500 cm/s long (%s)"), *Wind.ToString()), Wind.Equals(Expected, 0.01));
	TestTrue(TEXT("The result has no vertical part"), FMath::IsNearlyZero(Wind.Z, 1.0e-6));

	TestTrue(TEXT("Strength 0: no wind"), LBStormFXLogic::RainWind(FVector(1.0, 0.0, 0.0), 0.f, 500.f).IsNearlyZero(1.0e-6));
	TestTrue(TEXT("Lean 0: no wind"), LBStormFXLogic::RainWind(FVector(1.0, 0.0, 0.0), 1.f, 0.f).IsNearlyZero(1.0e-6));
	TestTrue(TEXT("A zero or vertical direction: no wind, no NaN"), LBStormFXLogic::RainWind(FVector::UpVector, 1.f, 500.f).IsNearlyZero(1.0e-6));
	TestTrue(TEXT("Full strength along +Y: (0, 500, 0)"), LBStormFXLogic::RainWind(FVector(0.0, 7.0, 0.0), 1.f, 500.f).Equals(FVector(0.0, 500.0, 0.0), 0.01));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormFXMistAmountTest, "LastBell.StormFX.Logic.MistAmount", LB_FX_TEST_FLAGS)
bool FLBStormFXMistAmountTest::RunTest(const FString& Parameters)
{
	// smoothstep(Min - 0.1, Min + 0.1, Exposure), Min 0.6.
	TestNearlyEqual(TEXT("Well under the band: 0"), LBStormFXLogic::MistAmount(0.f, 0.6f), 0.f, 1.0e-6f);
	TestNearlyEqual(TEXT("At the foot of the band (0.5): 0"), LBStormFXLogic::MistAmount(0.5f, 0.6f), 0.f, 1.0e-6f);
	TestNearlyEqual(TEXT("A quarter of the way (0.55): 0.15625"), LBStormFXLogic::MistAmount(0.55f, 0.6f), 0.15625f, 1.0e-4f);
	TestNearlyEqual(TEXT("The middle (0.6): 0.5"), LBStormFXLogic::MistAmount(0.6f, 0.6f), 0.5f, 1.0e-4f);
	TestNearlyEqual(TEXT("The top of the band (0.7): 1"), LBStormFXLogic::MistAmount(0.7f, 0.6f), 1.f, 1.0e-6f);
	TestNearlyEqual(TEXT("Open sky (1): 1"), LBStormFXLogic::MistAmount(1.f, 0.6f), 1.f, 1.0e-6f);
	TestNearlyEqual(TEXT("A different threshold (0.3) moves the band: exposure 0.3 gives 0.5"), LBStormFXLogic::MistAmount(0.3f, 0.3f), 0.5f, 1.0e-4f);
	TestTrue(TEXT("Rises with exposure"), LBStormFXLogic::MistAmount(0.58f, 0.6f) < LBStormFXLogic::MistAmount(0.62f, 0.6f));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStormFXRollBoltTest, "LastBell.StormFX.Logic.RollBolt", LB_FX_TEST_FLAGS)
bool FLBStormFXRollBoltTest::RunTest(const FString& Parameters)
{
	TestTrue(TEXT("A roll under the chance draws a bolt"), LBStormFXLogic::RollBolt(0.6f, 0.59f));
	TestFalse(TEXT("A roll at the chance does not"), LBStormFXLogic::RollBolt(0.6f, 0.6f));
	TestFalse(TEXT("A roll over the chance does not"), LBStormFXLogic::RollBolt(0.6f, 0.9f));
	TestTrue(TEXT("Chance 1 always draws (roll 0.9999)"), LBStormFXLogic::RollBolt(1.f, 0.9999f));
	TestTrue(TEXT("Chance 1 always draws (roll 0)"), LBStormFXLogic::RollBolt(1.f, 0.f));
	TestFalse(TEXT("Chance 0 never draws (roll 0)"), LBStormFXLogic::RollBolt(0.f, 0.f));
	TestFalse(TEXT("A negative chance never draws"), LBStormFXLogic::RollBolt(-0.5f, 0.f));
	return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS
