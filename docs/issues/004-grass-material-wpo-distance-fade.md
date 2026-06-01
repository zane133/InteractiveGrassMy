# 004 — 草材质 WPO 距离衰减

## Type

HITL — 需在 Material Editor 中手动操作，无法自动化

## Blocked by

- [#002](002-multi-lod-staticmesh-export.md)（需要至少一个多 LOD 草网格作为测试资产）

---

## Parent

PRD: Multi-LOD Grass Generator (`docs/PRD-multi-lod-grass-generator.md`)

## What to build

在草材质中增加 WPO（World Position Offset）距离衰减逻辑，使风动强度随摄像机距离渐变衰减，与 LOD 切换节奏同步。

具体行为：
- 在材质图表中添加 `Distance` 计算节点（CameraPosition - WorldPosition → Length）。
- 添加 WPO 乘数：`WindScale = 1.0 - saturate((Distance - 300) / 500)`，效果为：
  - 0–300cm：100% 风动
  - 300–800cm：线性衰减
  - >800cm：0% 风动（不再计算复杂顶点偏移）
- WPO 输出节点前乘以 WindScale。
- 同时启用 Dithered LOD Transition（材质属性中勾选），配合 LOD 切换做平滑淡入淡出。

## Acceptance criteria

- [ ] 在 PIE 中近距离（<3m）草有明显风动
- [ ] 中距离（~5–8m）草摆动幅度明显减小
- [ ] 远距离（>8m）草完全静止
- [ ] 拉远/拉近时过渡无Pop感（平滑淡入淡出）
- [ ] 材质编译无警告

## Blocked by

- #002
