# 001 — LOD 数据模型 + BuildGrassMesh 纯函数重构

## Type

AFK — 代码改动，无人工交互需求

## Blocked by

None — 可以立即开始

---

## Parent

PRD: Multi-LOD Grass Generator (`docs/PRD-multi-lod-grass-generator.md`)

## What to build

在 `ASplineGrassGenerator` 中新增 LOD 配置数据结构，并对 `BuildGrassMesh` 做纯函数改造，为后续多 LOD 导出做准备。

具体行为：
- 新增 `FGrassLODInfo` 结构体，包含每个 LOD 级别的 `LengthSegments`、`WidthSegments`、`ScreenSize` 三个字段，均带 Editor 可见的 UPROPERTY。
- `ASplineGrassGenerator` 新增 `TArray<FGrassLODInfo> LODs` 属性，默认值 `[{8,1,1.0}, {4,1,0.08}, {2,1,0.03}]`。
- `BuildGrassMesh` 新增重载 `(TArray<FVector>&, TArray<int32>&, TArray<FVector>&, TArray<FVector2D>&, TArray<FColor>&, int32 LengthSegs, int32 WidthSegs)` — 接受显式段数参数的纯函数。
- 原 `BuildGrassMesh(TArray<FVector>&, TArray<int32>&, TArray<FVector>&, TArray<FVector2D>&, TArray<FColor>&)` 改为调用新重载，传入成员变量 `LengthSegments` 和 `WidthSegments`。
- `GeneratePreview` 改为从 `LODs[0]` 读取段数（如果数组非空），否则回退到旧成员变量。

## Acceptance criteria

- [ ] 编译通过，无警告
- [ ] 在编辑器中打开 `ASplineGrassGenerator`，Details 面板显示 LODs 数组，默认 3 个元素
- [ ] `GeneratePreview` 行为与改动前完全一致（仍显示 8 段草叶）
- [ ] 调用 `BuildGrassMesh(Verts, Tris, Norms, UVs, Colors, 4, 1)` 返回 10 个顶点
- [ ] 调用 `BuildGrassMesh(Verts, Tris, Norms, UVs, Colors, 2, 1)` 返回 6 个顶点

## Blocked by

None
