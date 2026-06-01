# 005 — Foliage HISM 剔除配置

## Type

HITL — 需在编辑器中手动配置，验证需进 PIE

## Blocked by

- [#003](003-fbx-roundtrip-screensize-preserve.md)（需要最终版多 LOD 资产就位）

---

## Parent

PRD: Multi-LOD Grass Generator (`docs/PRD-multi-lod-grass-generator.md`)

## What to build

在 UE Foliage 系统中配置距离剔除参数，与 HISM 内建的视锥剔除联动，确保远处和屏幕外的草不产生 draw call。

具体行为：
- 选中目标 Foliage Type（Paint 模式下使用的 Static Mesh Foliage）。
- 设置：
  - `Cull Distance` → Min = 0, Max = 8000（厘米，即 80m）
  - `Collision` → 关闭碰撞（草不需要碰撞，节省物理内存）
  - `Cast Shadow` → 根据项目需要（建议远处草不投影）
- 在 `Project Settings → Rendering` 确认 `Foliage Minimum Screen Size` 保持默认或不低于 0.0001。
- 使用 `stat scenerendering` 或 `stat rhi` 验证：
  - 摄像机转离草地时，HISM draw call 下降
  - 摄像机远离至 80m+ 时，草完全停止渲染
- 测试场景：至少刷 5000+ 实例覆盖大面积，确保指标有可见差异。

## Acceptance criteria

- [ ] 摄像机正对草地：正常渲染，draw call 在预期范围
- [ ] 摄像机转离草地 90°+：draw call 明显下降
- [ ] 摄像机退至 80m 外：草停止渲染
- [ ] 近景 LOD0 视觉效果无变化（Cull Distance 不影响近距离渲染）
- [ ] stat 命令确认 HISM 实例数 + draw call 均下降

## Blocked by

- #003
