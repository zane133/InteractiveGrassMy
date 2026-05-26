#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"

class FInverseColorViewExtension;

class FInteractiveGrassMyModule : public IModuleInterface
{
public:
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

private:
	void RegisterInverseColorViewExtension();

	FDelegateHandle PostEngineInitHandle;
	TSharedPtr<FInverseColorViewExtension, ESPMode::ThreadSafe> InverseColorViewExtension;
};
