// f:\xiawan\ahui_xiawan_p4\xiawan\Plugins\TA_Tools\Source\TA_Tools\Public\SplineGrassGenerator.h

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Components/SplineComponent.h"
#include "Components/StaticMeshComponent.h"
#include "SplineGrassGenerator.generated.h"

USTRUCT(BlueprintType)
struct FGrassLODInfo
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LOD", meta = (ClampMin = "2", ClampMax = "64"))
    int32 LengthSegments = 8;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LOD", meta = (ClampMin = "1", ClampMax = "8"))
    int32 WidthSegments = 1;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LOD", meta = (ClampMin = "0.001", ClampMax = "1.0"))
    float ScreenSize = 1.0f;
};

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

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spline Grass|LOD")
    TArray<FGrassLODInfo> LODs = {
        {8, 1, 1.0f},
        {4, 1, 0.08f},
        {2, 1, 0.03f}
    };

protected:
    virtual void OnConstruction(const FTransform& Transform) override;

#if WITH_EDITOR
    virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;
#endif

private:
    void BuildGrassMesh(TArray<FVector>& Vertices, TArray<int32>& Triangles, TArray<FVector>& Normals, TArray<FVector2D>& UVs, TArray<FColor>& VertexColors);
    void BuildGrassMesh(TArray<FVector>& Vertices, TArray<int32>& Triangles, TArray<FVector>& Normals, TArray<FVector2D>& UVs, TArray<FColor>& VertexColors, int32 InLengthSegments, int32 InWidthSegments);
    float GetWidthAtDistance(float NormalizedDistance);

};
