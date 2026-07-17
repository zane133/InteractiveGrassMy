// Copyright 2024, PrismaticaDev. All rights reserved.


#include "PrismatiscapeWorldSubsystem.h"
#include "PrismatiscapeSettings.h"
#include "Manager/PrismatiscapeManager.h"
#include "Engine/World.h"

UPrismatiscapeWorldSubsystem* UPrismatiscapeWorldSubsystem::Get(const UObject* WorldContextObject)
{
	if (!WorldContextObject) return nullptr;
	return WorldContextObject->GetWorld()->GetSubsystem<UPrismatiscapeWorldSubsystem>();
}

APrismatiscapeManager* UPrismatiscapeWorldSubsystem::GetPrismatiscapeManager(const UObject* WorldContextObject)
{
	if (!WorldContextObject) return UPrismatiscapeSettings::Get()->PrismatiscapeManager.Get();

	const UPrismatiscapeWorldSubsystem* ThisSubsystem = Get(WorldContextObject);
	return IsValid(ThisSubsystem) ? ThisSubsystem->Manager : nullptr;
}

void UPrismatiscapeWorldSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);

	SpawnManager();

	// Bind to world end play
	if (!OnWorldCleanupHandle.IsValid()) OnWorldCleanupHandle = FWorldDelegates::OnWorldCleanup.AddUObject(this, &UPrismatiscapeWorldSubsystem::OnWorldEndPlay);
}

void UPrismatiscapeWorldSubsystem::OnWorldEndPlay(UWorld* World, bool bSessionEnded, bool bCleanupResources)
{
	FWorldDelegates::OnWorldCleanup.Remove(OnWorldCleanupHandle);

	if (!Manager) return;
	if (!Get(World)) return;

	if (Get(World)->Manager)
	{
		UPrismatiscapeSettings::Get()->PrismatiscapeManager.Reset();
	}
}

void UPrismatiscapeWorldSubsystem::SpawnManager()
{
	FActorSpawnParameters SpawnParams;
	SpawnParams.bNoFail = true;

//#if WITH_EDITOR
//	SpawnParams.bHideFromSceneOutliner = true;
//#endif

	Manager = GetWorld()->SpawnActor<APrismatiscapeManager>(UPrismatiscapeSettings::Get()->PrismatiscapeManagerClass, FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);

	UPrismatiscapeSettings::Get()->PrismatiscapeManager = Manager;
}

bool UPrismatiscapeWorldSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}