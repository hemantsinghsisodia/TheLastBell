#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "LBPlayerController.generated.h"

class UInputMappingContext;
class UUserWidget;

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

	UPROPERTY(EditDefaultsOnly, Category = "LastBell|UI")
	TSubclassOf<UUserWidget> HUDWidgetClass;

	/** Menu maps: visible cursor, UI-only input. */
	UPROPERTY(EditDefaultsOnly, Category = "LastBell|UI")
	bool bMenuMode = false;

	/** Switches cursor and input mode at runtime (e.g. the ending screen). */
	UFUNCTION(BlueprintCallable, Category = "LastBell|UI")
	void SetMenuMode(bool bInMenuMode);

	UFUNCTION(BlueprintPure, Category = "LastBell|UI")
	UUserWidget* GetHUDWidget() const { return HUDWidget; }

protected:
	virtual void BeginPlay() override;

private:
	UPROPERTY(Transient)
	TObjectPtr<UUserWidget> HUDWidget;
};
