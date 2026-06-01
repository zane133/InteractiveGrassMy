# 002 — 多 LOD StaticMesh 导出

## Type

AFK — 代码改动，无人工交互需求

## Blocked by

- [#001](001-lod-data-model-and-buildgrassmesh-refactor.md)

---

## Parent

PRD: Multi-LOD Grass Generator (`docs/PRD-multi-lod-grass-generator.md`)

## What to build

改造 `ASplineGrassGenerator::ExportToStaticMesh()`，使其生成包含所有配置 LOD 级别的单个 StaticMesh 资源。

具体行为：
- 遍历 `LODs` 数组，对每个元素调用 `BuildGrassMesh` 重载（传入该 LOD 的段数），得到独立的顶点/三角/法线/UV/顶点色数据。
- 每个 LOD 的顶点和法线必须经过坐标轴转换 `FVector(-V.Y, V.X, V.Z)`，与现有逻辑一致。
- 为每个 LOD 构建一个 `FMeshDescription`（含 2 层 UV、顶点色、双面支持），推入 `TArray<const FMeshDescription*>`。
- 将整个数组传给 `StaticMesh->BuildFromMeshDescriptions(...)`，原生生成多 LOD 网格。
- 构建完成后遍历 SourceModels，将每个 LOD 的 `ScreenSize` 设置为 `LODs[i].ScreenSize`。
- 生成 preview 仍然只用 LOD0。

## Acceptance criteria

- [ ] 导出带 3 个 LOD 的 StaticMesh 到指定路径
- [ ] 在 StaticMesh Editor 中打开资产，LOD Picker 显示 3 个级别
- [ ] LOD0 ScreenSize = 1.0, LOD1 = 0.08, LOD2 = 0.03
- [ ] LOD1 顶点数 = 10 × (bDoubleSided ? 2 : 1)
- [ ] LOD2 顶点数 = 6 × (bDoubleSided ? 2 : 1)
- [ ] 所有 LOD 的 UV 与顶点色数据与 LOD0 一致（渐变 UV、灰度顶点色）
- [ ] 仅修改 [LODs] 数组（如减少到 2 个元素），导出资产也只有 2 个 LOD

## Blocked by

- #001
