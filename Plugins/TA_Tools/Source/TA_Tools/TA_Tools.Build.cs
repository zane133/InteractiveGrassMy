// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class TA_Tools : ModuleRules
{
    public TA_Tools(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;
        
        PublicIncludePaths.AddRange(
            new string[] {
            }
            );
                
        
        PrivateIncludePaths.AddRange(
            new string[] {
            }
            );
            
        
        PublicDependencyModuleNames.AddRange(
            new string[]
            {
                "Core",
            }
            );
            
        
        PrivateDependencyModuleNames.AddRange(
            new string[]
            {
                "CoreUObject",
                "Engine",
                "Slate",
                "SlateCore",
                "ProceduralMeshComponent",
                "MeshDescription",
                "StaticMeshDescription",
                "MeshConversion",
                "MeshUtilities",
            }
            );
        
        if (Target.bBuildEditor)
        {
            PrivateDependencyModuleNames.AddRange(
                new string[]
                {
                    "UnrealEd",
                    "AssetTools",
                    "StaticMeshEditor",
                }
            );
        }
        
        DynamicallyLoadedModuleNames.AddRange(
            new string[]
            {
            }
            );
    }
}