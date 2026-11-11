#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "LBPlayerController.generated.h"

class UInputAction;
class UInputMappingContext;
class UUserWidget;
struct FInputActionValue;

UCLASS()
class LASTBELL_API ALBPlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	/** Added in array order at priority 0 for local controllers. */
	UPROPERTY(EditDefaultsOnly, Category = "LastBell|Input")
	TArray<TObjectPtr<UInputMappingContext>> MappingContexts;

	/** Added above the gameplay contexts while the player inspects an item (IMC_LB_Inspect). */
	UPROPERTY(EditDefaultsOnly, Category = "LastBell|Input")
	TObjectPtr<UInputMappingContext> InspectMappingContext;

	UPROPERTY(EditDefaultsOnly, Category = "LastBell|Input")
	int32 InspectMappingPriority = 1;

	/** Adds or removes InspectMappingContext. Safe to call repeatedly. */
	void SetInspectionContextActive(bool bActive);

	/**
	 * The Pause action (IA_Pause, Escape; created in P18-2). Pressed, it calls ULBUISubsystem::HandleBack: the top screen goes back, otherwise
	 * the pause menu opens. Unset: no pause key is bound and a log line says so.
	 */
	UPROPERTY(EditDefaultsOnly, Category = "LastBell|Input")
	TObjectPtr<UInputAction> PauseAction;

	/**
	 * The gameplay HUD. On a menu map this may instead be a ULBMenuWidgetBase subclass (ULBMainMenuWidget): it is then pushed on the UI subsystem's
	 * screen stack as the main menu rather than added to the viewport directly.
	 */
	UPROPERTY(EditDefaultsOnly, Category = "LastBell|UI")
	TSubclassOf<UUserWidget> HUDWidgetClass;

	/** Menu maps: visible cursor, UI-only input. */
	UPROPERTY(EditDefaultsOnly, Category = "LastBell|UI")
	bool bMenuMode = false;

	/** Switches cursor and input mode at runtime (e.g. the ending screen). Forwards to ULBUISubsystem::SetMenuMode, which keeps a screen on the stack in charge. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|UI")
	void SetMenuMode(bool bInMenuMode);

	UFUNCTION(BlueprintPure, Category = "LastBell|UI")
	UUserWidget* GetHUDWidget() const { return HUDWidget; }

	/**
	 * Collapses or restores the gameplay HUD (cinematics hide it). Never touches the input mode or the cursor, so mouse look keeps working.
	 * A HUD created while it is hidden stays hidden.
	 */
	UFUNCTION(BlueprintCallable, Category = "LastBell|UI")
	void SetHUDHidden(bool bInHidden);

	UFUNCTION(BlueprintPure, Category = "LastBell|UI")
	bool IsHUDHidden() const { return bHUDHidden; }

protected:
	virtual void BeginPlay() override;
	virtual void SetupInputComponent() override;

private:
	void HandlePausePressed(const FInputActionValue& Value);

	UPROPERTY(Transient)
	TObjectPtr<UUserWidget> HUDWidget;

	bool bHUDHidden = false;
};
