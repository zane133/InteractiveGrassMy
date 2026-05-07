// f:\xiawan\ahui_xiawan_p4\xiawan\Plugins\TA_Tools\Source\TA_Tools\Public\SplineGrassGenerator.h

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Components/SplineComponent.h"
#include "Components/StaticMeshComponent.h"
#include "SplineGrassGenerator.generated.h"

UCLASS(Blueprintable, meta = (DisplayName = "Spline Grass Mesh Generator"))
class TA_TOOLS_API ASplineGrassGenerator : public AActor
{
    GENERATED_BODY()
    
public:	
    ASplineGrassGenerator();

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
    USplineComponent* SplineComponent;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
    UStaticMeshComponent* PreviewMesh;

    UFUNCTION(BlueprintCallable, CallInEditor, Category = "Spline Grass")
    void GeneratePreview();

    UFUNCTION(BlueprintCallable, CallInEditor, Category = "Spline Grass")
    void ExportToStaticMesh();

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spline Grass|Export")
    FString MeshName = TEXT("SM_Grass");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spline Grass|Export")
    FString ExportPath = TEXT("/Game/XW_Art/RES/TAExample/GrassAnim/Mesh/");

    // ---- FBX Round-trip (Export FBX -> Import back) ----
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spline Grass|Export|FBX Round Trip")
    bool bFbxRoundTripAfterExport = true;

    // 留空则使用 Project/Saved/TA_Tools/FbxRoundTrip/
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spline Grass|Export|FBX Round Trip")
    FString FbxExportDirOnDisk;

    // 导回 Content 的目标路径(例如 /Game/MyFolder/)
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spline Grass|Export|FBX Round Trip")
    FString FbxReimportDestinationPath = TEXT("/Game/XW_Art/RES/TAExample/GrassAnim/Mesh/");

    // 生成的新资产名后缀(避免覆盖原资产)
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spline Grass|Export|FBX Round Trip")
    FString FbxReimportNameSuffix = TEXT("_RT");

    // 默认允许覆盖同名 RT 资产,避免弹出覆盖对话框
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spline Grass|Export|FBX Round Trip")
    bool bFbxReimportReplaceExisting = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spline Grass|Shape|Width", meta = (ClampMin = "0.1"))
    float BaseWidth = 5.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spline Grass|Shape|Width", meta = (ClampMin = "0.0"))
    float TipWidth = 0.5f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spline Grass|Shape|Width")
    UCurveFloat* WidthCurve;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spline Grass|Shape|Segments", meta = (ClampMin = "2", ClampMax = "64"))
    int32 LengthSegments = 8;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spline Grass|Shape|Segments", meta = (ClampMin = "1", ClampMax = "8"))
    int32 WidthSegments = 1;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spline Grass|Shape|UV")
    bool bFlipU = false;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spline Grass|Shape|UV")
    bool bFlipV = false;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spline Grass|Shape|Options")
    bool bDoubleSided = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spline Grass|Shape|Options")
    bool bSmoothNormals = true;

protected:
    virtual void OnConstruction(const FTransform& Transform) override;

#if WITH_EDITOR
    virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;
#endif

private:
    void BuildGrassMesh(TArray<FVector>& Vertices, TArray<int32>& Triangles, TArray<FVector>& Normals, TArray<FVector2D>& UVs, TArray<FColor>& VertexColors);
    float GetWidthAtDistance(float NormalizedDistance);

#if WITH_EDITOR
    bool RoundTripFbx(UStaticMesh* SourceMesh, UStaticMesh*& OutImportedMesh) const;
#endif
};
