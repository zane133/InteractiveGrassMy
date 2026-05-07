// f:\xiawan\ahui_xiawan_p4\xiawan\Plugins\TA_Tools\Source\TA_Tools\Private\SplineGrassGenerator.cpp
#include "SplineGrassGenerator.h"
#include "Modules/ModuleManager.h"
#include "Components/StaticMeshComponent.h"
#include "PhysicsEngine/BodySetup.h"

#if WITH_EDITOR
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetExportTask.h"
#include "AssetImportTask.h"
#include "StaticMeshAttributes.h"
#include "MeshDescription.h"
#include "MeshDescriptionBuilder.h"
#include "AssetToolsModule.h"
#include "UObject/SavePackage.h"
#include "Engine/StaticMesh.h"
#include "BodySetupEnums.h"
#include "Engine/CollisionProfile.h"
#include "Exporters/Exporter.h"
#include "Materials/Material.h"
#include "MaterialDomain.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#endif

ASplineGrassGenerator::ASplineGrassGenerator()
{
    PrimaryActorTick.bCanEverTick = false;

    SplineComponent = CreateDefaultSubobject<USplineComponent>(TEXT("SplineComponent"));
    RootComponent = SplineComponent;
    
    SplineComponent->ClearSplinePoints();
    SplineComponent->AddSplinePoint(FVector(0, 0, 0), ESplineCoordinateSpace::Local);
    SplineComponent->AddSplinePoint(FVector(0, 10, 50), ESplineCoordinateSpace::Local);
    SplineComponent->AddSplinePoint(FVector(0, 20, 100), ESplineCoordinateSpace::Local);
    SplineComponent->SetClosedLoop(false);

    PreviewMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("PreviewMesh"));
    PreviewMesh->SetupAttachment(RootComponent);
    PreviewMesh->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    // 确保预览网格按普通世界物体渲染（参与深度）
    PreviewMesh->SetDepthPriorityGroup(SDPG_World);
    PreviewMesh->SetRenderInMainPass(true);
    PreviewMesh->SetRenderInDepthPass(true);
    PreviewMesh->SetRenderCustomDepth(false);
}

void ASplineGrassGenerator::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    GeneratePreview();
}

#if WITH_EDITOR
void ASplineGrassGenerator::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
    Super::PostEditChangeProperty(PropertyChangedEvent);
    GeneratePreview();
}
#endif

float ASplineGrassGenerator::GetWidthAtDistance(float NormalizedDistance)
{
    float BaseToTip = FMath::Lerp(BaseWidth, TipWidth, NormalizedDistance);
    
    if (WidthCurve)
    {
        float CurveValue = WidthCurve->GetFloatValue(NormalizedDistance);
        return BaseToTip * CurveValue;
    }
    return BaseToTip;
}

void ASplineGrassGenerator::BuildGrassMesh(TArray<FVector>& Vertices, TArray<int32>& Triangles, TArray<FVector>& Normals, TArray<FVector2D>& UVs, TArray<FColor>& VertexColors)
{
    Vertices.Empty();
    Triangles.Empty();
    Normals.Empty();
    UVs.Empty();
    VertexColors.Empty();

    if (!SplineComponent || SplineComponent->GetNumberOfSplinePoints() < 2)
    {
        return;
    }

    float SplineLength = SplineComponent->GetSplineLength();
    int32 NumLengthVerts = LengthSegments + 1;
    int32 NumWidthVerts = WidthSegments + 1;

    FVector PrevRight = SplineComponent->GetRightVectorAtDistanceAlongSpline(0, ESplineCoordinateSpace::Local);

    for (int32 LengthIdx = 0; LengthIdx < NumLengthVerts; LengthIdx++)
    {
        float LengthAlpha = (float)LengthIdx / (float)LengthSegments;
        float Distance = LengthAlpha * SplineLength;

        FVector SplinePos = SplineComponent->GetLocationAtDistanceAlongSpline(Distance, ESplineCoordinateSpace::Local);
        FVector Tangent = SplineComponent->GetTangentAtDistanceAlongSpline(Distance, ESplineCoordinateSpace::Local).GetSafeNormal();
        
        FVector SplineRight = SplineComponent->GetRightVectorAtDistanceAlongSpline(Distance, ESplineCoordinateSpace::Local);
        
        if (FVector::DotProduct(SplineRight, PrevRight) < 0)
        {
            SplineRight = -SplineRight;
        }
        PrevRight = SplineRight;

        FVector Normal = FVector::CrossProduct(SplineRight, Tangent).GetSafeNormal();
        
        float CurrentWidth = GetWidthAtDistance(LengthAlpha);

        for (int32 WidthIdx = 0; WidthIdx < NumWidthVerts; WidthIdx++)
        {
            float WidthAlpha = (float)WidthIdx / (float)WidthSegments;
            float WidthOffset = (WidthAlpha - 0.5f) * 2.0f * CurrentWidth;

            FVector VertexPos = SplinePos + SplineRight * WidthOffset;
            Vertices.Add(VertexPos);

            float U = bFlipU ? (1.0f - WidthAlpha) : WidthAlpha;
            float V = bFlipV ? (1.0f - LengthAlpha) : LengthAlpha;
            UVs.Add(FVector2D(U, V));

            Normals.Add(Normal);

            uint8 GradientValue = FMath::Clamp((int32)(LengthAlpha * 255.0f), 0, 255);
            VertexColors.Add(FColor(GradientValue, GradientValue, GradientValue, 255));
        }
    }

    for (int32 LengthIdx = 0; LengthIdx < LengthSegments; LengthIdx++)
    {
        for (int32 WidthIdx = 0; WidthIdx < WidthSegments; WidthIdx++)
        {
            int32 BL = LengthIdx * NumWidthVerts + WidthIdx;
            int32 BR = BL + 1;
            int32 TL = BL + NumWidthVerts;
            int32 TR = TL + 1;

            Triangles.Add(BL);
            Triangles.Add(BR);
            Triangles.Add(TL);

            Triangles.Add(BR);
            Triangles.Add(TR);
            Triangles.Add(TL);
        }
    }

    if (bDoubleSided)
    {
        int32 OriginalVertCount = Vertices.Num();
        int32 OriginalTriCount = Triangles.Num();

        Vertices.Reserve(OriginalVertCount * 2);
        Normals.Reserve(OriginalVertCount * 2);
        UVs.Reserve(OriginalVertCount * 2);
        VertexColors.Reserve(OriginalVertCount * 2);
        Triangles.Reserve(OriginalTriCount * 2);

        TArray<FVector> OriginalVertices = Vertices;
        TArray<FVector> OriginalNormals = Normals;
        TArray<FVector2D> OriginalUVs = UVs;
        TArray<FColor> OriginalColors = VertexColors;
        TArray<int32> OriginalTriangles = Triangles;

        for (int32 i = 0; i < OriginalVertCount; i++)
        {
            Vertices.Add(OriginalVertices[i]);
            Normals.Add(-OriginalNormals[i]);
            UVs.Add(OriginalUVs[i]);
            VertexColors.Add(OriginalColors[i]);
        }

        for (int32 i = 0; i < OriginalTriCount; i += 3)
        {
            Triangles.Add(OriginalTriangles[i] + OriginalVertCount);
            Triangles.Add(OriginalTriangles[i + 2] + OriginalVertCount);
            Triangles.Add(OriginalTriangles[i + 1] + OriginalVertCount);
        }
    }
}

void ASplineGrassGenerator::GeneratePreview()
{
#if WITH_EDITOR
    TArray<FVector> Vertices;
    TArray<int32> Triangles;
    TArray<FVector> Normals;
    TArray<FVector2D> UVs;
    TArray<FColor> VertexColors;

    BuildGrassMesh(Vertices, Triangles, Normals, UVs, VertexColors);

    if (Vertices.Num() == 0)
    {
        PreviewMesh->SetStaticMesh(nullptr);
        return;
    }

    // 模仿 UE 导入流程：在内存中构建 StaticMesh（与导出/导入相同的管线），预览走同一套渲染与深度
    const FName PreviewMeshName = MakeUniqueObjectName(GetTransientPackage(), UStaticMesh::StaticClass(), TEXT("SplineGrassPreview"));
    UStaticMesh* TransientMesh = NewObject<UStaticMesh>(GetTransientPackage(), PreviewMeshName, RF_Transient);

    FMeshDescription MeshDesc;
    FStaticMeshAttributes Attributes(MeshDesc);
    Attributes.Register();
    FMeshDescriptionBuilder MeshBuilder;
    MeshBuilder.SetMeshDescription(&MeshDesc);
    MeshBuilder.EnablePolyGroups();
    MeshBuilder.SetNumUVLayers(2);

    TArray<FVertexInstanceID> VertexInstances;
    for (int32 i = 0; i < Vertices.Num(); i++)
    {
        FVertexID VertexID = MeshBuilder.AppendVertex(Vertices[i]);
        FVertexInstanceID InstanceID = MeshBuilder.AppendInstance(VertexID);
        MeshBuilder.SetInstanceNormal(InstanceID, Normals[i]);
        MeshBuilder.SetInstanceUV(InstanceID, UVs[i], 0);
        MeshBuilder.SetInstanceUV(InstanceID, UVs[i], 1);
        MeshBuilder.SetInstanceColor(InstanceID, FVector4f(VertexColors[i].R / 255.0f, VertexColors[i].G / 255.0f, VertexColors[i].B / 255.0f, VertexColors[i].A / 255.0f));
        VertexInstances.Add(InstanceID);
    }

    FPolygonGroupID PolyGroup = MeshBuilder.AppendPolygonGroup();
    for (int32 i = 0; i < Triangles.Num(); i += 3)
    {
        TArray<FVertexInstanceID> TriVerts;
        TriVerts.Add(VertexInstances[Triangles[i]]);
        TriVerts.Add(VertexInstances[Triangles[i + 1]]);
        TriVerts.Add(VertexInstances[Triangles[i + 2]]);
        MeshBuilder.AppendTriangle(TriVerts[0], TriVerts[1], TriVerts[2], PolyGroup);
    }

    TArray<const FMeshDescription*> MeshDescriptions;
    MeshDescriptions.Add(&MeshDesc);
    TransientMesh->InitResources();
    TransientMesh->SetLightingGuid();
    UStaticMesh::FBuildMeshDescriptionsParams BuildParams;
    BuildParams.bBuildSimpleCollision = true;  // 生成简单碰撞，编辑器内显示紫色碰撞体
    BuildParams.bFastBuild = false;
    TransientMesh->BuildFromMeshDescriptions(MeshDescriptions, BuildParams);

    FStaticMeshSourceModel& SourceModel = TransientMesh->GetSourceModel(0);
    SourceModel.BuildSettings.bGenerateLightmapUVs = false;
    SourceModel.BuildSettings.bRecomputeNormals = false;
    SourceModel.BuildSettings.bRecomputeTangents = true;
    TransientMesh->Build(false);
    TransientMesh->PostEditChange();

    // 预览网格：强制创建/刷新碰撞数据（仅 Editor 下）
    if (UBodySetup* BodySetup = TransientMesh->GetBodySetup())
    {
        BodySetup->CollisionTraceFlag = ECollisionTraceFlag::CTF_UseDefault;
        BodySetup->bDoubleSidedGeometry = bDoubleSided;
        BodySetup->CreatePhysicsMeshes();
    }

    PreviewMesh->SetStaticMesh(TransientMesh);
    // 使用引擎默认表面材质，确保参与深度测试并写入深度缓冲
    if (UMaterialInterface* DefaultSurfaceMat = UMaterial::GetDefaultMaterial(EMaterialDomain::MD_Surface))
    {
        PreviewMesh->SetMaterial(0, DefaultSurfaceMat);
    }
    PreviewMesh->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
    PreviewMesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    PreviewMesh->RecreatePhysicsState();
    // 强制参与深度通道，并刷新渲染状态（避免被当作前景/不进 DepthPass）
    PreviewMesh->SetDepthPriorityGroup(SDPG_World);
    PreviewMesh->SetRenderInMainPass(true);
    PreviewMesh->SetRenderInDepthPass(true);
    PreviewMesh->SetRenderCustomDepth(false);
    PreviewMesh->MarkRenderStateDirty();
    PreviewMesh->SetCastShadow(true);
    PreviewMesh->SetCanEverAffectNavigation(false);
#else
    PreviewMesh->SetStaticMesh(nullptr);
#endif
}

void ASplineGrassGenerator::ExportToStaticMesh()
{
#if WITH_EDITOR
    TArray<FVector> Vertices;
    TArray<int32> Triangles;
    TArray<FVector> Normals;
    TArray<FVector2D> UVs;
    TArray<FColor> VertexColors;

    BuildGrassMesh(Vertices, Triangles, Normals, UVs, VertexColors);

    if (Vertices.Num() == 0)
    {
        UE_LOG(LogTemp, Warning, TEXT("SplineGrassGenerator: No mesh data to export"));
        return;
    }

    // 坐标轴转换（导出用）
    for (int32 i = 0; i < Vertices.Num(); i++)
    {
        FVector V = Vertices[i];
        Vertices[i] = FVector(-V.Y, V.X, V.Z);
        
        FVector N = Normals[i];
        Normals[i] = FVector(-N.Y, N.X, N.Z);
    }

    FString PackagePath = ExportPath + MeshName;
    UPackage* Package = CreatePackage(*PackagePath);
    Package->FullyLoad();

    UStaticMesh* StaticMesh = NewObject<UStaticMesh>(Package, *MeshName, RF_Public | RF_Standalone);

    FMeshDescription MeshDesc;
    FStaticMeshAttributes Attributes(MeshDesc);
    Attributes.Register();

    FMeshDescriptionBuilder MeshBuilder;
    MeshBuilder.SetMeshDescription(&MeshDesc);
    MeshBuilder.EnablePolyGroups();
    MeshBuilder.SetNumUVLayers(2);

    TArray<FVertexInstanceID> VertexInstances;
    for (int32 i = 0; i < Vertices.Num(); i++)
    {
        FVertexID VertexID = MeshBuilder.AppendVertex(Vertices[i]);
        FVertexInstanceID InstanceID = MeshBuilder.AppendInstance(VertexID);
        MeshBuilder.SetInstanceNormal(InstanceID, Normals[i]);
        MeshBuilder.SetInstanceUV(InstanceID, UVs[i], 0);
        MeshBuilder.SetInstanceUV(InstanceID, UVs[i], 1);
        MeshBuilder.SetInstanceColor(InstanceID, FVector4f(VertexColors[i].R / 255.0f, VertexColors[i].G / 255.0f, VertexColors[i].B / 255.0f, VertexColors[i].A / 255.0f));
        VertexInstances.Add(InstanceID);
    }

    FPolygonGroupID PolyGroup = MeshBuilder.AppendPolygonGroup();
    for (int32 i = 0; i < Triangles.Num(); i += 3)
    {
        TArray<FVertexInstanceID> TriVerts;
        TriVerts.Add(VertexInstances[Triangles[i]]);
        TriVerts.Add(VertexInstances[Triangles[i + 1]]);
        TriVerts.Add(VertexInstances[Triangles[i + 2]]);
        MeshBuilder.AppendTriangle(TriVerts[0], TriVerts[1], TriVerts[2], PolyGroup);
    }

    TArray<const FMeshDescription*> MeshDescriptions;
    MeshDescriptions.Add(&MeshDesc);
    
    // 初始化 Static Mesh
    StaticMesh->InitResources();
    StaticMesh->SetLightingGuid();

    // 构建参数
    UStaticMesh::FBuildMeshDescriptionsParams BuildParams;
    BuildParams.bBuildSimpleCollision = true;
    BuildParams.bFastBuild = false;
    StaticMesh->BuildFromMeshDescriptions(MeshDescriptions, BuildParams);

    // ====================================

    // ==========================================

    FStaticMeshSourceModel& SourceModel = StaticMesh->GetSourceModel(0);
    SourceModel.BuildSettings.bGenerateLightmapUVs = false;
    SourceModel.BuildSettings.bRecomputeNormals = false;
    SourceModel.BuildSettings.bRecomputeTangents = true;
    
    StaticMesh->Build(false);
    StaticMesh->PostEditChange();

    FAssetRegistryModule::AssetCreated(StaticMesh);
    Package->MarkPackageDirty();

    FString PackageFileName = FPackageName::LongPackageNameToFilename(PackagePath, FPackageName::GetAssetPackageExtension());
    FSavePackageArgs SaveArgs;
    SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
    UPackage::SavePackage(Package, StaticMesh, *PackageFileName, SaveArgs);

    UE_LOG(LogTemp, Log, TEXT("SplineGrassGenerator: Exported mesh to %s"), *PackagePath);

    // 一键 FBX Round-trip：导出 FBX 再导回（走 UE 标准导入管线）
    if (bFbxRoundTripAfterExport)
    {
        UStaticMesh* ImportedMesh = nullptr;
        if (RoundTripFbx(StaticMesh, ImportedMesh) && ImportedMesh)
        {
            UE_LOG(LogTemp, Log, TEXT("SplineGrassGenerator: FBX round-trip imported %s"), *ImportedMesh->GetPathName());
        }
        else
        {
            UE_LOG(LogTemp, Warning, TEXT("SplineGrassGenerator: FBX round-trip failed."));
        }
    }
#endif
}

#if WITH_EDITOR
bool ASplineGrassGenerator::RoundTripFbx(UStaticMesh* SourceMesh, UStaticMesh*& OutImportedMesh) const
{
    OutImportedMesh = nullptr;
    if (!SourceMesh)
    {
        return false;
    }

    // 1) Export FBX to disk
    FString ExportDir = FbxExportDirOnDisk;
    if (ExportDir.IsEmpty())
    {
        ExportDir = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("TA_Tools"), TEXT("FbxRoundTrip"));
    }
    IFileManager::Get().MakeDirectory(*ExportDir, true);

    const FString BaseName = SourceMesh->GetName();
    const FString ExportFilename = FPaths::Combine(ExportDir, BaseName + TEXT(".fbx"));

    UAssetExportTask* ExportTask = NewObject<UAssetExportTask>();
    ExportTask->Object = SourceMesh;
    ExportTask->Filename = ExportFilename;
    ExportTask->bAutomated = true;
    ExportTask->bPrompt = false;
    ExportTask->bReplaceIdentical = true;
    ExportTask->bUseFileArchive = false;
    ExportTask->bWriteEmptyFiles = false;

    const bool bExportOk = UExporter::RunAssetExportTask(ExportTask);
    if (!bExportOk || !IFileManager::Get().FileExists(*ExportFilename))
    {
        UE_LOG(LogTemp, Warning, TEXT("SplineGrassGenerator: FBX export failed: %s"), *ExportFilename);
        return false;
    }

    // 2) Import FBX back to Content
    FString DestPath = FbxReimportDestinationPath;
    if (DestPath.IsEmpty())
    {
        DestPath = ExportPath;
    }
    if (!DestPath.StartsWith(TEXT("/")))
    {
        UE_LOG(LogTemp, Warning, TEXT("SplineGrassGenerator: Invalid destination path: %s"), *DestPath);
        return false;
    }
    // Ensure it ends with '/'
    if (!DestPath.EndsWith(TEXT("/")))
    {
        DestPath += TEXT("/");
    }

    const FString DestName = BaseName + FbxReimportNameSuffix;

    UAssetImportTask* ImportTask = NewObject<UAssetImportTask>();
    ImportTask->Filename = ExportFilename;
    ImportTask->DestinationPath = DestPath;
    ImportTask->DestinationName = DestName;
    ImportTask->bAutomated = true;
    ImportTask->bSave = true;
    ImportTask->bReplaceExisting = bFbxReimportReplaceExisting;

    FAssetToolsModule& AssetToolsModule = FModuleManager::LoadModuleChecked<FAssetToolsModule>("AssetTools");
    TArray<UAssetImportTask*> Tasks;
    Tasks.Add(ImportTask);
    AssetToolsModule.Get().ImportAssetTasks(Tasks);

    if (ImportTask->ImportedObjectPaths.Num() <= 0)
    {
        UE_LOG(LogTemp, Warning, TEXT("SplineGrassGenerator: FBX import produced no assets."));
        return false;
    }

    // Prefer the first imported UStaticMesh
    for (const FString& ObjPath : ImportTask->ImportedObjectPaths)
    {
        UObject* ImportedObj = StaticLoadObject(UObject::StaticClass(), nullptr, *ObjPath);
        if (UStaticMesh* ImportedSM = Cast<UStaticMesh>(ImportedObj))
        {
            OutImportedMesh = ImportedSM;

            // 导入后关闭 Nanite（避免走 Nanite 渲染路径）
#if WITH_EDITORONLY_DATA
            ImportedSM->NaniteSettings.bEnabled = false;
#endif
            ImportedSM->MarkPackageDirty();
            ImportedSM->PostEditChange();

            // 导入并修改后，立刻保存资源到磁盘
            if (UPackage* ImportPackage = ImportedSM->GetOutermost())
            {
                const FString ImportPackageName = ImportPackage->GetName();
                const FString ImportPackageFilename = FPackageName::LongPackageNameToFilename(
                    ImportPackageName,
                    FPackageName::GetAssetPackageExtension());

                FSavePackageArgs SaveArgs;
                SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
                UPackage::SavePackage(ImportPackage, ImportedSM, *ImportPackageFilename, SaveArgs);
            }

            return true;
        }
    }

    UE_LOG(LogTemp, Warning, TEXT("SplineGrassGenerator: FBX import finished but no StaticMesh found."));
    return false;
}
#endif