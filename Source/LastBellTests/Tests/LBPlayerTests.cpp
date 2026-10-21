#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

#include "Character/LBCharacter.h"
#include "Character/LBPlayerTuningData.h"
#include "Character/LBPlayerTypes.h"
#include "Components/LBInspectableComponent.h"
#include "Components/LBInteractableComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Systems/LBUserSettings.h"

#define LB_TEST_FLAGS (EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBTuningDefaultsTest, "LastBell.Player.TuningDefaults", LB_TEST_FLAGS)
bool FLBTuningDefaultsTest::RunTest(const FString& Parameters)
{
	const ULBPlayerTuningData* T = GetDefault<ULBPlayerTuningData>();
	TestEqual(TEXT("Walk"), T->WalkSpeed, 260.f);
	TestEqual(TEXT("Sprint"), T->SprintSpeed, 480.f);
	TestEqual(TEXT("Crouch"), T->CrouchSpeed, 140.f);
	TestEqual(TEXT("Accel"), T->MaxAcceleration, 1400.f);
	TestEqual(TEXT("Braking"), T->BrakingDeceleration, 1600.f);
	TestEqual(TEXT("Crouched half height"), T->CrouchedHalfHeight, 58.f);
	TestEqual(TEXT("Crouch blend"), T->CrouchCameraBlendTime, 0.2f);
	TestEqual(TEXT("Walk bob"), T->WalkBobAmplitude, 0.6f);
	TestEqual(TEXT("Sprint bob"), T->SprintBobAmplitude, 1.4f);
	TestEqual(TEXT("Sprint FOV"), T->SprintFOVDelta, 4.f);
	TestEqual(TEXT("Loudness crouch"), T->GetLoudness(ELBGait::Crouch), 0.1f);
	TestEqual(TEXT("Loudness walk"), T->GetLoudness(ELBGait::Walk), 0.3f);
	TestEqual(TEXT("Loudness sprint"), T->GetLoudness(ELBGait::Sprint), 0.8f);
	TestEqual(TEXT("Loudness idle"), T->GetLoudness(ELBGait::Idle), 0.f);
	TestEqual(TEXT("Stride walk"), T->GetStride(ELBGait::Walk), 160.f);
	TestEqual(TEXT("Stride sprint"), T->GetStride(ELBGait::Sprint), 210.f);
	TestEqual(TEXT("Stride crouch"), T->GetStride(ELBGait::Crouch), 120.f);
	TestEqual(TEXT("Stride idle"), T->GetStride(ELBGait::Idle), 0.f);
	TestEqual(TEXT("Candle temperature"), T->CandleTemperature, 1900.f);
	TestEqual(TEXT("Candle radius"), T->CandleAttenuationRadius, 600.f);
	TestEqual(TEXT("Candle relight delay"), T->CandleRelightDelay, 1.2f);
	TestEqual(TEXT("Candle gutter scale"), T->CandleGutterIntensityScale, 0.55f);
	TestFalse(TEXT("Candle shadows off"), T->bCandleCastShadows);
	TestTrue(TEXT("Candle offset"), T->CandleHeldOffset.Equals(FVector(30.f, 18.f, -22.f)));
	TestEqual(TEXT("Inspect hold distance"), T->InspectHoldDistance, 45.f);

	// Applied to a movement component.
	UCharacterMovementComponent* Movement = NewObject<UCharacterMovementComponent>(GetTransientPackage());
	T->ApplyToMovement(Movement);
	TestEqual(TEXT("Applied walk speed"), Movement->MaxWalkSpeed, 260.f);
	TestEqual(TEXT("Applied crouch speed"), Movement->MaxWalkSpeedCrouched, 140.f);
	TestEqual(TEXT("Applied accel"), Movement->MaxAcceleration, 1400.f);
	TestEqual(TEXT("Applied braking"), Movement->BrakingDecelerationWalking, 1600.f);
	TestEqual(TEXT("Applied crouched half height"), Movement->GetCrouchedHalfHeight(), 58.f);

	// A character without a Tuning asset falls back to the class defaults.
	const ALBCharacter* CDO = GetDefault<ALBCharacter>();
	TestNull(TEXT("CDO has no tuning asset"), CDO->Tuning.Get());
	TestEqual(TEXT("Fallback walk speed"), CDO->GetTuning().WalkSpeed, 260.f);

	// User settings defaults.
	const ULBUserSettings* Settings = GetDefault<ULBUserSettings>();
	TestTrue(TEXT("Sensitivity default is positive"), Settings->MouseSensitivity > 0.f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBGaitTest, "LastBell.Player.GaitSelection", LB_TEST_FLAGS)
bool FLBGaitTest::RunTest(const FString& Parameters)
{
	using namespace LBPlayerLogic;
	constexpr float MinDot = 0.5f;

	TestTrue(TEXT("Forward sprint allowed"), CanSprint(true, false, true, 1.f, MinDot));
	TestTrue(TEXT("Forward-diagonal sprint allowed"), CanSprint(true, false, true, 0.7f, MinDot));
	TestFalse(TEXT("Sideways blocks sprint"), CanSprint(true, false, true, 0.f, MinDot));
	TestFalse(TEXT("Exactly at the threshold blocks sprint"), CanSprint(true, false, true, 0.5f, MinDot));
	TestFalse(TEXT("Backwards blocks sprint"), CanSprint(true, false, true, -1.f, MinDot));
	TestFalse(TEXT("Crouched blocks sprint"), CanSprint(true, true, true, 1.f, MinDot));
	TestFalse(TEXT("No input blocks sprint"), CanSprint(true, false, false, 1.f, MinDot));
	TestFalse(TEXT("Button not held blocks sprint"), CanSprint(false, false, true, 1.f, MinDot));

	TestEqual(TEXT("Forward axis dot"), InputForwardDot(FVector2D(0.0, 1.0)), 1.f);
	TestEqual(TEXT("Backward axis dot"), InputForwardDot(FVector2D(0.0, -1.0)), -1.f);
	TestEqual(TEXT("Strafe axis dot"), InputForwardDot(FVector2D(1.0, 0.0)), 0.f);
	TestEqual(TEXT("No input dot"), InputForwardDot(FVector2D::ZeroVector), 0.f);
	TestTrue(TEXT("Diagonal dot is about 0.707"), FMath::IsNearlyEqual(InputForwardDot(FVector2D(1.0, 1.0)), 0.7071f, 0.001f));

	constexpr float Idle = 10.f;
	TestTrue(TEXT("Standing still is Idle"), SelectGait(false, false, 0.f, Idle) == ELBGait::Idle);
	TestTrue(TEXT("Moving is Walk"), SelectGait(false, false, 200.f, Idle) == ELBGait::Walk);
	TestTrue(TEXT("Moving and sprinting is Sprint"), SelectGait(false, true, 400.f, Idle) == ELBGait::Sprint);
	TestTrue(TEXT("Sprint flag without speed is Idle"), SelectGait(false, true, 0.f, Idle) == ELBGait::Idle);
	TestTrue(TEXT("Crouched is Crouch, even if sprint is set"), SelectGait(true, true, 100.f, Idle) == ELBGait::Crouch);
	TestTrue(TEXT("Crouched and still is Crouch"), SelectGait(true, false, 0.f, Idle) == ELBGait::Crouch);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBStrideTest, "LastBell.Player.FootstepStride", LB_TEST_FLAGS)
bool FLBStrideTest::RunTest(const FString& Parameters)
{
	{
		FLBStrideAccumulator Acc;
		int32 Steps = 0;
		// 1000 cm in 10 cm increments at a 160 cm stride: floor(1000 / 160) = 6 steps.
		for (int32 i = 0; i < 100; ++i)
		{
			Steps += Acc.Advance(10.f, 160.f);
		}
		TestEqual(TEXT("Walk steps over 1000 cm"), Steps, 6);
		TestTrue(TEXT("Carry-over is the remainder"), FMath::IsNearlyEqual(Acc.Accumulated, 40.f, 0.01f));
	}
	{
		FLBStrideAccumulator Acc;
		int32 Steps = 0;
		for (int32 i = 0; i < 100; ++i)
		{
			Steps += Acc.Advance(10.f, 210.f);
		}
		TestEqual(TEXT("Sprint steps over 1000 cm"), Steps, 4);
	}
	{
		FLBStrideAccumulator Acc;
		TestEqual(TEXT("A single large move yields several steps"), Acc.Advance(500.f, 120.f), 4);
		TestEqual(TEXT("Zero stride never steps"), Acc.Advance(500.f, 0.f), 0);
		TestEqual(TEXT("Negative distance never steps"), Acc.Advance(-5.f, 120.f), 0);
		Acc.Reset();
		TestEqual(TEXT("Reset clears the carry"), Acc.Accumulated, 0.f);
	}
	{
		// Changing gait mid-way keeps the carried distance.
		FLBStrideAccumulator Acc;
		TestEqual(TEXT("100 cm at 160 stride"), Acc.Advance(100.f, 160.f), 0);
		TestEqual(TEXT("then 30 cm at 120 stride completes a step"), Acc.Advance(30.f, 120.f), 1);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBCandleStateTest, "LastBell.Player.CandleStateMachine", LB_TEST_FLAGS)
bool FLBCandleStateTest::RunTest(const FString& Parameters)
{
	constexpr float Delay = 1.2f;
	FLBCandleStateMachine Candle;
	TestTrue(TEXT("Starts lit"), Candle.IsLit());

	TestTrue(TEXT("Toggle snuffs instantly"), Candle.Toggle(Delay) == ELBCandleEvent::Snuffed);
	TestFalse(TEXT("Not lit after snuff"), Candle.IsLit());

	TestTrue(TEXT("Toggle starts the relight"), Candle.Toggle(Delay) == ELBCandleEvent::RelightStarted);
	TestFalse(TEXT("Not lit while relighting"), Candle.IsLit());
	TestTrue(TEXT("State is Relighting"), Candle.State == ELBCandleState::Relighting);

	TestTrue(TEXT("Cannot toggle while relighting"), Candle.Toggle(Delay) == ELBCandleEvent::None);
	TestTrue(TEXT("Still relighting after rejected toggle"), Candle.State == ELBCandleState::Relighting);

	TestTrue(TEXT("0.5 s: not yet"), Candle.Tick(0.5f) == ELBCandleEvent::None);
	TestFalse(TEXT("Still unlit at 0.5 s"), Candle.IsLit());
	TestTrue(TEXT("1.0 s: not yet"), Candle.Tick(0.5f) == ELBCandleEvent::None);
	TestTrue(TEXT("1.3 s: relit"), Candle.Tick(0.3f) == ELBCandleEvent::Relit);
	TestTrue(TEXT("Lit again"), Candle.IsLit());
	TestTrue(TEXT("Ticking while lit does nothing"), Candle.Tick(5.f) == ELBCandleEvent::None);

	// Ticking while snuffed does not relight.
	Candle.Toggle(Delay);
	TestTrue(TEXT("No relight without a toggle"), Candle.Tick(10.f) == ELBCandleEvent::None);
	TestFalse(TEXT("Stays snuffed"), Candle.IsLit());

	// Zero delay relights on the next tick.
	Candle.Toggle(0.f);
	TestTrue(TEXT("Zero delay relights on next tick"), Candle.Tick(0.f) == ELBCandleEvent::Relit);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLBInspectCloseTest, "LastBell.Player.InspectKeepVsPutBack", LB_TEST_FLAGS)
bool FLBInspectCloseTest::RunTest(const FString& Parameters)
{
	// Inspect-on-interact is opt-in; items are put back unless marked as keepable (the grant itself is the interactable's GrantedStateTags).
	TestFalse(TEXT("bInspectOnInteract defaults off"), GetDefault<ULBInteractableComponent>()->bInspectOnInteract);
	TestFalse(TEXT("bKeepOnClose defaults off"), GetDefault<ULBInspectableComponent>()->bKeepOnClose);
	return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS
