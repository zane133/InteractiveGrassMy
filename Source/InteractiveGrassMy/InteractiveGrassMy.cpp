#include "InteractiveGrassMy.h"
#include "InverseColorViewExtension.h"
#include "Engine/Engine.h"
#include "Misc/Paths.h"
#include "ShaderCore.h"

#define LOCTEXT_NAMESPACE "FInteractiveGrassMyModule"

void FInteractiveGrassMyModule::StartupModule()
{
	const FString ShaderDirectory = FPaths::Combine(FPaths::ProjectDir(), TEXT("Source/InteractiveGrassMy/Shaders"));
	AddShaderSourceDirectoryMapping(TEXT("/Project/InteractiveGrassMy"), ShaderDirectory);

	if (GEngine)
	{
		RegisterInverseColorViewExtension();
	}
	else
	{
		PostEngineInitHandle = FCoreDelegates::OnPostEngineInit.AddRaw(
			this,
			&FInteractiveGrassMyModule::RegisterInverseColorViewExtension);
	}
}

void FInteractiveGrassMyModule::ShutdownModule()
{
	if (PostEngineInitHandle.IsValid())
	{
		FCoreDelegates::OnPostEngineInit.Remove(PostEngineInitHandle);
		PostEngineInitHandle.Reset();
	}

	InverseColorViewExtension.Reset();
}

void FInteractiveGrassMyModule::RegisterInverseColorViewExtension()
{
	if (!InverseColorViewExtension.IsValid())
	{
		InverseColorViewExtension = FSceneViewExtensions::NewExtension<FInverseColorViewExtension>();
	}
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_PRIMARY_GAME_MODULE(FInteractiveGrassMyModule, InteractiveGrassMy, "InteractiveGrassMy");
