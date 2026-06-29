// Copyright Epic Games, Inc. All Rights Reserved.

#include "TreeFadeComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"

UTreeFadeComponent::UTreeFadeComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.bStartWithTickEnabled = false;
}

void UTreeFadeComponent::BeginPlay()
{
	Super::BeginPlay();

	DynamicMaterials.Reset();

	AActor* Owner = GetOwner();
	if (!Owner)
	{
		return;
	}

	TArray<UStaticMeshComponent*> MeshComponents;
	Owner->GetComponents<UStaticMeshComponent>(MeshComponents);

	for (UStaticMeshComponent* MeshComponent : MeshComponents)
	{
		if (!MeshComponent)
		{
			continue;
		}

		const int32 MaterialCount = MeshComponent->GetNumMaterials();
		for (int32 MaterialIndex = 0; MaterialIndex < MaterialCount; ++MaterialIndex)
		{
			UMaterialInstanceDynamic* MID = MeshComponent->CreateDynamicMaterialInstance(MaterialIndex);
			if (MID && MaterialHasScalarParameter(MID, FadeParamName))
			{
				DynamicMaterials.Add(MID);
			}
		}
	}

	ApplyEffectAmountToMaterials();
	SetComponentTickEnabled(false);
}

void UTreeFadeComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

	const float InterpSpeed = (TargetEffectAmount > CurrentEffectAmount) ? FadeOutSpeed : FadeInSpeed;
	CurrentEffectAmount = FMath::FInterpConstantTo(CurrentEffectAmount, TargetEffectAmount, DeltaTime, InterpSpeed);

	ApplyEffectAmountToMaterials();

	if (FMath::IsNearlyEqual(CurrentEffectAmount, TargetEffectAmount))
	{
		CurrentEffectAmount = TargetEffectAmount;
		ApplyEffectAmountToMaterials();
		SetComponentTickEnabled(false);
	}
}

void UTreeFadeComponent::StartFadeOut()
{
	TargetEffectAmount = 1.0f;
	SetComponentTickEnabled(true);
}

void UTreeFadeComponent::StartFadeIn()
{
	TargetEffectAmount = 0.0f;
	SetComponentTickEnabled(true);
}

bool UTreeFadeComponent::MaterialHasScalarParameter(const UMaterialInterface* Material, FName ParamName)
{
	if (!Material)
	{
		return false;
	}

	float DummyValue = 0.0f;
	return Material->GetScalarParameterValue(ParamName, DummyValue);
}

void UTreeFadeComponent::ApplyEffectAmountToMaterials()
{
	for (UMaterialInstanceDynamic* MID : DynamicMaterials)
	{
		if (MID)
		{
			MID->SetScalarParameterValue(FadeParamName, CurrentEffectAmount);
		}
	}
}
