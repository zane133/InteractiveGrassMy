# 007 — Tree Fade Runtime C++（TA_ToolsRuntime 模块）

**Status:** ready-for-agent

## Type

AFK — 纯 C++ 与插件配置，无 Material Editor 手工步骤

## Blocked by

None

---

## Parent

PRD: Tree Fade System (`docs/PRD-tree-fade-system.md`)

## What to build

在 `TA_Tools` 插件中新增 **Runtime** 子模块 `TA_ToolsRuntime`，实现树木遮挡渐变隐藏的运行时逻辑。

### 模块

- 注册 `TA_ToolsRuntime`（`Type: Runtime`）于插件描述文件；保留现有 `TA_Tools` Editor 模块不变。
- 新建 Build.cs：依赖 `Core`, `CoreUObject`, `Engine`。

### UTreeFadeComponent

- `UActorComponent`，`BlueprintSpawnableComponent`。
- `BeginPlay`：遍历 Owner 全部 `UStaticMeshComponent`；对每个材质槽 `CreateDynamicMaterialInstance`；仅当 MID 存在配置的标量参数（默认 `EffectAmount`）时加入 `DynamicMaterials`；默认关闭 Tick。
- 属性：`FadeOutSpeed`（默认 4）、`FadeInSpeed`（默认 2）、`FadeParamName`（默认 `EffectAmount`）、运行时 `CurrentEffectAmount` / `TargetEffectAmount`。
- `StartFadeOut` / `StartFadeIn`：`BlueprintCallable`；设置目标并启用 Tick。
- `TickComponent`：`FInterpConstantTo` 按方向选速度；对所有 MID `SetScalarParameterValue`；到达目标后关闭 Tick。

### AOcclusionTraceActor

- 可放置 `AActor`。
- 属性：`TargetActor`、`TraceInterval`（0.05）、`SweepRadius`（25）、`TargetZOffset`（80）、`bDrawDebugTrace`（false）；`UPROPERTY() UTreeFadeComponent* LastHitFadeComponent`。
- `BeginPlay`：`TargetActor` 有效则 `StartTrace()`，否则 Development Warning。
- `StartTrace` / `StopTrace`：Timer 驱动检测。
- 每次检测：起点 `TargetActor` 位置 + ZOffset → Player 0 `PlayerCameraManager` 相机位置；`SweepSingleByChannel`，`ECC_Visibility`，球半径 `SweepRadius`。
- 单目标状态机（见 PRD Implementation Decisions）；命中同一组件不重复触发。
- 可选 Debug 绘制 sweep 线段与命中状态。

### 建议（非强制）

- 将单目标状态机提取为可单测的纯函数/helper，便于 Automation 或代码审查对照 PRD 状态表。

## Acceptance criteria

- [ ] 项目编译通过（Editor + Development），`TA_ToolsRuntime` 模块被正确加载
- [ ] 树 Blueprint 可 Add Component `UTreeFadeComponent`
- [ ] 关卡可放置 `AOcclusionTraceActor`，Details 可设置 `TargetActor`
- [ ] PIE 中：仅含 `EffectAmount` 的材质槽随 `StartFadeOut`/`StartFadeIn` 变化；无该参数的材质槽不受影响
- [ ] 射线命中带组件的树时渐隐；移开视线后渐显；两棵树切换时旧树恢复、新树渐隐
- [ ] 同一棵树持续命中时不重复打断插值
- [ ] 插值结束后组件 Tick 关闭
- [ ] `TargetActor` 为空时不启动 Timer 且有 Warning
- [ ] `bDrawDebugTrace` 开启时可见调试线/球；关闭时无额外绘制
- [ ] 不修改、不删除 `BPC_TreeFadeComponent` 资产

## Comments

_(none)_
