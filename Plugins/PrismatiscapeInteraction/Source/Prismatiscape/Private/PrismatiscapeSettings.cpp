// Copyright 2024, PrismaticaDev. All rights reserved.


#include "PrismatiscapeSettings.h"
#include "Manager/PrismatiscapeManager.h"
#include "UObject/ConstructorHelpers.h"

TAutoConsoleVariable<bool> CVarLogDebugShapes(
	TEXT("pris.DebugShapes"),
	false,
	TEXT("Draws Debug Shapes for currently registered Prismatiscape Draw Components"),
	ECVF_Default);

TAutoConsoleVariable<bool> CVarPrismatiscapeEnabled(
	TEXT("pris.Enabled"),
	true,
	TEXT("Master switch for Prismatiscape simulation. When false, Manager tick is disabled (no gather / RT update)."),
	ECVF_Default);

UPrismatiscapeSettings::UPrismatiscapeSettings()
{
	ConstructorHelpers::FClassFinder<APrismatiscapeManager> ManagerClassFinder(TEXT("/Script/Engine.Blueprint'/Prismatiscape/Prismatiscape_Manager_BP.Prismatiscape_Manager_BP_C'"));
	if (ManagerClassFinder.Succeeded()) SetPrismatiscapeManagerClass(ManagerClassFinder.Class);
}

bool UPrismatiscapeSettings::GetDrawDebugShapes() const
{
	return CVarLogDebugShapes.GetValueOnGameThread();
}

bool UPrismatiscapeSettings::IsEnabled() const
{
	return CVarPrismatiscapeEnabled.GetValueOnGameThread();
}