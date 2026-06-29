# 008 — XrayHide Demo 蓝图与关卡接线（HITL）

**Status:** ready-for-human

## Type

HITL — 需在 Unreal Editor 中手动操作 Blueprint 与关卡

## Blocked by

- [#007](007-tree-fade-runtime-cpp.md)（C++ 类必须先存在）

---

## Parent

PRD: Tree Fade System (`docs/PRD-tree-fade-system.md`)

## What to build

在 `Content/XW_Art/RES/TAExample/XrayHide/` 示例内容中，将 Demo 从蓝图原型切换到 C++ 运行时栈。

具体步骤：
- 打开树相关 Blueprint（如 `BP_TreeLeafDither`）：**移除** `BPC_TreeFadeComponent`（若已挂）；**添加** `UTreeFadeComponent`。
- 确认树叶材质实例/母材质暴露 **`EffectAmount`** 标量并与 dither 逻辑相连（沿用现有 `MI_TreeLeaf_fade` 等资产）。
- 在 `XrayHide.umap` 放置 **`AOcclusionTraceActor`**（或基于它的 Blueprint 子类）。
- 将 **玩家 Pawn** 赋给 `TargetActor`。
- 按需调节 `TraceInterval`、`SweepRadius`、`TargetZOffset`、`FadeInSpeed` / `FadeOutSpeed`。
- 验收时可选开启 `bDrawDebugTrace` 调试，提交前默认关闭。

## Acceptance criteria

- [ ] PIE 进入 `XrayHide` 关卡，角色与相机之间有树时树叶渐隐
- [ ] 离开遮挡或转向后树木恢复实体感
- [ ] 树干（无 `EffectAmount`）保持不透明，仅树叶参与渐变
- [ ] 关卡内未同时使用 `BPC_TreeFadeComponent` 与 `UTreeFadeComponent` 于同一棵树
- [ ] 无 BeginPlay / Tick 相关蓝图错误日志

## Comments

_(none)_
