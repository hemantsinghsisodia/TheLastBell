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

	UFUNCTION(BlueprintPure, Category = "LastBell|UI")
	UUserWidget* GetHUDWidget() const { return HUDWidget; }

protected:
	virtual void BeginPlay() override;

private:
	UPROPERTY(Transient)
	TObjectPtr<UUserWidget> HUDWidget;
};
