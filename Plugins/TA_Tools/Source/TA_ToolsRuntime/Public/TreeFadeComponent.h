// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "TreeFadeComponent.generated.h"

UCLASS(ClassGroup = (TA_Tools), meta = (BlueprintSpawnableComponent, DisplayName = "Tree Fade Component"))
class TA_TOOLSRUNTIME_API UTreeFadeComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UTreeFadeComponent();

	virtual void BeginPlay() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	UFUNCTION(BlueprintCallable, Category = "Tree Fade")
	void StartFadeOut();

	UFUNCTION(BlueprintCallable, Category = "Tree Fade")
	void StartFadeIn();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tree Fade", meta = (ClampMin = "0.01"))
	float FadeOutSpeed = 4.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tree Fade", meta = (ClampMin = "0.01"))
	float FadeInSpeed = 2.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tree Fade")
	FName FadeParamName = TEXT("EffectAmount");

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Tree Fade")
	float CurrentEffectAmount = 0.0f;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Tree Fade")
	float TargetEffectAmount = 0.0f;

private:
	UPROPERTY()
	TArray<TObjectPtr<UMaterialInstanceDynamic>> DynamicMaterials;

	static bool MaterialHasScalarParameter(const UMaterialInterface* Material, FName ParamName);
	void ApplyEffectAmountToMaterials();
};
