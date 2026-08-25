# PRD: 多 LOD 样条草叶生成器 + 渲染管线优化

## Problem Statement

当前 `SplineGrassGenerator` 仅生成单 LOD 的草叶 StaticMesh（每根草 18 顶点/16 三角面）。通过 UE Foliage（HISM）大面积布草后，远距离仍然渲染全精度草叶并执行完整 vertex shader WPO 风动计算。缺少 LOD 系统导致：

- GPU 顶点处理压力随草密度线性增长
- 远处草的三角形远小于一像素，浪费 GPU
- WPO 风动在不可见距离上仍然执行
- 无距离剔除与视锥体外剔除的配合

## Solution

扩展 `ASplineGrassGenerator`（TA_Tools 插件），使其支持从单 LOD 升级为 3 级程序化 LOD 导出。配合 UE Foliage HISM 的视锥剔除、距离剔除，以及草材质的 WPO 距离衰减，形成完整的三层渲染管线优化。

## User Stories

1. As a TA, I want to configure up to N levels of LOD (typically 3) on the spline grass generator, each with its own segment counts and screen-size threshold, so that exported grass meshes degrade gracefully with distance.
2. As a TA, I want the preview in the editor viewport to always show LOD0 at full quality, so that I can accurately judge the shape and width curve without LOD switching interfering.
3. As a level artist, I want the exported static mesh to contain all configured LOD levels in a single asset, so that UE's built-in LOD system handles switching automatically when the mesh is placed via Foliage.
4. As a TA, I want the FBX round-trip pipeline to preserve UV and vertex color data at every LOD level, because those channels drive grass width scaling and texture mapping in the material.
5. As a TA, I want the FBX round-trip to restore my custom LOD ScreenSize thresholds after import, so that the automatic ScreenSize calculation from the FBX importer does not override my configured values.
6. As a level artist, I want grass at medium distance (8–25m) to render with half the vertex count and reduced WPO wind animation, so that GPU cycles are saved without perceptible visual difference.
7. As a level artist, I want grass at far distance (25–80m) to render as a minimal proxy mesh with no WPO, so that the scene still looks populated but GPU cost is negligible.
8. As a level designer, I want HISM distance culling to completely skip rendering grass beyond 80m and grass outside the camera frustum, eliminating unnecessary draw calls.
9. As a TA, I want the LOD configuration stored as an editable array in the Details panel, with sensible defaults (8/4/2 segments for the three levels), so that non-programmer artists can adjust the setup per-asset.
10. As a developer, I want `BuildGrassMesh` to accept segment counts as explicit parameters (overload), making it a pure function of its inputs, so that the LOD generation loop is side-effect-free and testable.
11. As a TA, I want all LOD levels to share the same shape parameters (BaseWidth, TipWidth, WidthCurve, UV flip), so that the grass silhouette remains consistent across LOD transitions.

## Implementation Decisions

### Data Structure

- A new `FGrassLODInfo` struct (`USTRUCT`) with fields: `LengthSegments` (int32, clamped 2–64), `WidthSegments` (int32, clamped 1–8), `ScreenSize` (float, clamped 0.001–1.0).
- `ASplineGrassGenerator` gains `TArray<FGrassLODInfo> LODs` with default value: `[{8, 1, 1.0}, {4, 1, 0.08}, {2, 1, 0.03}]`.
- Existing `LengthSegments` and `WidthSegments` members are retained for backward compatibility and continue to drive LOD0 in `GeneratePreview`.

### Mesh Generation

- `BuildGrassMesh` gains an overload accepting `(int32 OverrideLengthSegments, int32 OverrideWidthSegments)`. The original zero-argument version becomes a passthrough that calls the overload with the member-variable values.
- `ExportToStaticMesh` iterates `LODs`: for each entry, calls the overloaded `BuildGrassMesh`, applies coordinate-axis rotation (`FVector(-V.Y, V.X, V.Z)` for both vertices and normals), builds a `FMeshDescription`, and pushes it into a `TArray<const FMeshDescription*>`.
- The array is passed to `StaticMesh->BuildFromMeshDescriptions(...)` which natively produces a multi-LOD `UStaticMesh`.
- After `BuildFromMeshDescriptions`, each `FStaticMeshSourceModel`'s `ScreenSize` is set from the corresponding `FGrassLODInfo`.
- `GeneratePreview` continues rendering only LOD0, using `LODs[0]` if available, falling back to the member variables otherwise.

### FBX Round-Trip

- FBX round-trip remains enabled and exports/imports the multi-LOD mesh as a single FBX file.
- After import, `RoundTripFbx` iterates the imported `UStaticMesh`'s `SourceModels` and overwrites `ScreenSize` values from the original `LODs` array to counteract the FBX importer's automatic ScreenSize calculation.
- UV and vertex color data are authored in `FMeshDescription` at construction time and survive the round-trip; no additional handling is required.

### Coordinate Transform

- All LOD levels undergo the identical coordinate-axis rotation before building their `FMeshDescription`. This ensures LOD transitions do not produce visible rotation or texture-mapping discontinuities.

### Material-Side WPO Distance Attenuation

- (Implemented in the grass material, not C++.) World Position Offset for wind animation scales by a distance factor:
  - Distance < 8m: 100% wind intensity
  - Distance 8–25m: linearly ramp wind from 100% down to 0%
  - Distance > 25m: no WPO evaluation
- This maps to LOD levels: LOD0 gets full wind, LOD1 gets reduced wind, LOD2 (and beyond) gets no wind.

### Foliage / HISM Configuration

- Foliage Type remains HISM (Paint mode, `Static Mesh`).
- HISM inherently provides frustum culling via BVH and cull-distance support through `FoliageType` settings.
- Cull Distance: Min=0, Max=80m (set per Foliage Type in editor).
- Dithered LOD transitions enabled on the grass material for smooth cross-fade between LOD levels.

## Testing Decisions

### What Makes a Good Test

Tests should verify that `BuildGrassMesh` produces correct output arrays (vertex count, triangle count) given specific segment inputs, independently of any engine state. They should test the pure-function overload, not the member-variable version.

### Seam: BuildGrassMesh Overload

`BuildGrassMesh(Vertices, Triangles, Normals, UVs, VertexColors, LengthSegments, WidthSegments)` is the single highest-value test seam. It accepts explicit parameters and returns structured output arrays. All other parameters (BaseWidth, TipWidth, WidthCurve, bDoubleSided, bFlipU, bFlipV) remain read from the owning Actor; they are shape-configuration inputs and shareable across LODs.

### Testing Scenarios

- Given `LengthSegments=8, WidthSegments=1`: assert vertex count = 18, triangle count = 16 × (bDoubleSided ? 2 : 1).
- Given `LengthSegments=4, WidthSegments=1`: assert vertex count = 10.
- Given `LengthSegments=2, WidthSegments=1`: assert vertex count = 6.
- Given any valid input: assert UVs[0].X ∈ [0,1], UVs[0].Y ∈ [0,1].
- Given `bDoubleSided=true`: assert vertex/triangle count doubled and back-face normals are inverse of front-face normals.
- Given `bFlipU=true`: assert UV.x values are inverted relative to default.

### Integration Test: Multi-LOD Export

- Configure 3 LODs, invoke `ExportToStaticMesh`, verify the resulting `.uasset` contains exactly 3 `FStaticMeshSourceModel` entries with the expected ScreenSize values.
- Run FBX round-trip, verify the reimported mesh retains 3 LODs with correct ScreenSize (not auto-calculated).

## Out of Scope

- **Procedural foliage spawning**: This PRD does not add a runtime grass-spawning algorithm. Foliage placement remains manual (Foliage Paint) or via the existing Foliage Type workflow.
- **Runtime LOD switching logic**: LOD selection is delegated entirely to UE's built-in `UStaticMesh` LOD system and HISM. No custom C++ LOD-selection code.
- **Material authoring**: The C++ change only produces the mesh asset. The grass material with WPO distance attenuation must be authored separately in the Material Editor.
- **Nanite support**: Nanite is explicitly disabled in the FBX round-trip path (`NaniteSettings.bEnabled = false`). This PRD does not add Nanite compatibility.
- **Level-of-detail beyond 3 levels**: The system supports arbitrary array length, but only 3 levels are configured by default and validated in testing.
- **Non-HISM placement**: Instanced Static Mesh Component (ISM) and plain `UStaticMeshComponent` are not explicitly tested or optimized for in this PRD, though the generated assets work with any placement method.
- **Dynamic LOD for preview**: The editor preview (`GeneratePreview`) remains LOD0-only. Interactive LOD switching in the viewport is out of scope.

## Further Notes

- This PRD covers `Plugins/TA_Tools/Source/TA_Tools/Public/SplineGrassGenerator.h` and `Plugins/TA_Tools/Source/TA_Tools/Private/SplineGrassGenerator.cpp`. No other files are modified.
- The existing `BuildFromMeshDescriptions` API in UE5.8 supports multi-LOD construction natively via the array parameter; no engine modification is required.
- The `FGrassLODInfo` defaults (8/4/2 segments) were chosen as a balanced starting point following discussion. Individual projects can adjust in-editor.
- Coordinate-axis rotation `FVector(-V.Y, V.X, V.Z)` is preserved from the current implementation and applied uniformly across all LODs.
- All decisions in this document are the result of a 10-question design interview covering data structure, algorithm signature, LOD count, ScreenSize thresholds, WPO synchronization, coordinate transforms, FBX round-trip behavior, and preview strategy.
