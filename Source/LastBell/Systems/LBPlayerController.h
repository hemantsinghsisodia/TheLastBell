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
