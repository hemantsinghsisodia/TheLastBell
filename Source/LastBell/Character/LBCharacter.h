#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "LBCharacter.generated.h"

class UCameraComponent;
class UInputAction;
class ULBInteractorComponent;
struct FInputActionValue;

UCLASS()
class LASTBELL_API ALBCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	ALBCharacter();

	/** Disables input and asks the game mode to handle death. Safe to call repeatedly. */
	UFUNCTION(BlueprintCallable, Category = "LastBell|Player")
	void Kill();

	UFUNCTION(BlueprintPure, Category = "LastBell|Player")
	bool IsDead() const { return bIsDead; }

	UFUNCTION(BlueprintPure, Category = "LastBell|Player")
	ULBInteractorComponent* GetInteractor() const { return Interactor; }

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "LastBell|Input")
	TObjectPtr<UInputAction> MoveAction;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "LastBell|Input")
	TObjectPtr<UInputAction> LookAction;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "LastBell|Input")
	TObjectPtr<UInputAction> InteractAction;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LastBell|Input")
	float LookSensitivity = 1.0f;

protected:
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "LastBell|Player")
	TObjectPtr<UCameraComponent> FirstPersonCamera;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "LastBell|Player")
	TObjectPtr<ULBInteractorComponent> Interactor;

private:
	void Move(const FInputActionValue& Value);
	void Look(const FInputActionValue& Value);
	void Interact();

	bool bIsDead = false;
};
