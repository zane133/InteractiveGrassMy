# 003 — FBX Round-Trip ScreenSize 保留

## Type

AFK — 代码改动，无人工交互需求

## Blocked by

- [#002](002-multi-lod-staticmesh-export.md)

---

## Parent

PRD: Multi-LOD Grass Generator (`docs/PRD-multi-lod-grass-generator.md`)

## What to build

修复 `ASplineGrassGenerator::RoundTripFbx()`，确保多 LOD 网格经过 FBX 导出→导入管线后，保留原始 LOD 的 ScreenSize 配置，而不是被 FBX 导入器自动计算的值覆盖。

具体行为：
- 在 `RoundTripFbx` 返回前，在新导入的 `UStaticMesh` 上遍历所有 `FStaticMeshSourceModel`。
- 对每个 SourceModel，将 `ScreenSize` 覆写为 `LODs[i].ScreenSize`（使用原始 `ASplineGrassGenerator` 实例的 LODs 数组）。
- 当前 `RoundTripFbx` 是 `const` 成员函数，需改为非 const 或通过参数传入 LOD 配置。
- 设置完毕后再 SavePackage。

## Acceptance criteria

- [ ] 导出带 3 LOD 的网格，FBX Round-Trip 完成
- [ ] 导入后资产在 StaticMesh Editor 中 LOD0/1/2 的 ScreenSize 分别为 1.0 / 0.08 / 0.03，而非自动计算值
- [ ] UV 和顶点色数据在 Round-Trip 后保持不变
- [ ] Round-Trip 失败时（如路径无效），不影响已导出的主资产

## Blocked by

- #002
