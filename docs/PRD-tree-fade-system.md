# PRD: 树木遮挡渐变隐藏系统 (Tree Fade System)

**Status:** ready-for-agent

## Problem Statement

在第三人称或越肩视角下，角色与相机之间的树木会遮挡视线，影响战斗、探索与镜头可读性。TA 已在 `XrayHide` 示例场景中用蓝图原型验证了 dither 渐变隐藏效果（`BPC_TreeFadeComponent`、`BP_TreeLeafDither` 等），但蓝图实现存在维护成本高、易踩坑（GC 悬空指针、多目标冲突、Tick 常开浪费性能）等问题，且不适合作为可复用的运行时模块交给程序长期维护。

程序侧需要一套符合 UE C++ 规范的组件化实现：树木各自管理材质渐变与生命周期，场景中的检测 Actor 独立负责射线与单目标切换，TA 在 Demo 中通过拖拽组件/摆放 Actor 即可组装，无需改角色 C++ 继承链。

## Solution

在 **TA_Tools 插件**中新增 **Runtime 子模块**（`TA_ToolsRuntime`），提供两个可蓝图使用的运行时类型：

1. **`UTreeFadeComponent`** — 挂到树 Actor 上，在 `BeginPlay` 时为所有带 `EffectAmount` 参数的材质槽创建动态材质实例（MID），按需 Tick 插值，将 `EffectAmount` 从 0（实体）过渡到 1（透明），完成后自动休眠 Tick。
2. **`AOcclusionTraceActor`** — 拖入关卡即可用，不挂角色；按固定频率从 `TargetActor`（带高度偏移）向 Player 0 相机做球体扫描，维护**单目标** `LastHitFadeComponent`，在目标切换、未命中时发出 `StartFadeOut` / `StartFadeIn` 指令。

Demo 继续使用 `XrayHide` 现有材质与关卡资产；树 Blueprint 改用 C++ 组件，旧蓝图组件 `BPC_TreeFadeComponent` 保留但不再用于 Demo。第一版使用 `Visibility` 碰撞通道与 `EffectAmount` 材质参数，以最快路径跑通验收。

## User Stories

1. As a TA, I want a **runtime C++ component** I can add to any tree Blueprint, so that fade logic is reusable without copying blueprint graphs.
2. As a TA, I want the tree component to **fade all StaticMeshComponents** on the same Actor (trunk + leaf), so that the whole tree disappears consistently when occluding the view.
3. As a TA, I want only material slots that expose an **`EffectAmount` scalar** to participate in fading, so that trunk or decorative materials without the parameter are left unchanged.
4. As a TA, I want the fade parameter name to be **configurable on the component** (default `EffectAmount`), so that future materials with different naming can still work without code changes.
5. As a level artist, I want trees to **fade out smoothly** when they block the line from my character to the camera, so that I can always see the playable character.
6. As a level artist, I want trees to **fade back in smoothly** when they no longer block that line, so that the world does not look permanently ghosted.
7. As a level artist, I want **fade-out to feel snappier than fade-in** (separate speeds), so that obstruction is cleared quickly but restoration does not pop visually.
8. As a programmer, I want the tree component to **sleep its Tick** when interpolation completes, so that hundreds of trees in a level do not incur per-frame cost when idle.
9. As a programmer, I want **dynamic material instances created once in BeginPlay** and reused for interpolation, so that runtime allocation and material swaps are predictable.
10. As a TA, I want an **Occlusion Trace Actor** I can place in the level without modifying the player Character class, so that the demo stays drag-and-drop friendly.
11. As a TA, I want to **assign the player Pawn as TargetActor** on the trace Actor in the Details panel, so that setup requires no C++ subclassing.
12. As a programmer, I want the trace Actor to **start automatically on BeginPlay** when `TargetActor` is valid, so that dropping it into a map is sufficient for a default demo.
13. As a programmer, I want **StartTrace / StopTrace** BlueprintCallable entry points, so that designers can pause or manually control detection when needed.
14. As a programmer, I want the trace to run on a **Timer at 20 Hz** (0.05 s interval) rather than every frame, so that cost is bounded while responsiveness remains acceptable for a demo.
15. As a programmer, I want the trace interval to be **editable in Blueprint**, so that a project can trade smoothness for performance.
16. As a level artist, I want occlusion detection to use a **sphere sweep** (default radius 25 cm), so that thin leaf geometry does not flicker in and out on minor camera jitter.
17. As a programmer, I want the sweep radius to be **Blueprint-tunable**, so that different tree scales can be supported without recompiling.
18. As a programmer, I want the ray to run **from TargetActor (with Z offset) toward Player 0's camera**, so that the test matches "character looking toward the lens" debugging intuition.
19. As a programmer, I want a **default Z offset of 80 cm** on the trace start (chest height), so that the line does not originate from the actor's feet or capsule center.
20. As a programmer, I want the trace to use the **`Visibility` collision channel** in v1, so that the demo works without configuring a custom project channel.
21. As a programmer, I want **only one active fade target** at a time (`LastHitFadeComponent`), so that state transitions stay simple and free of multi-tree conflicts.
22. As a programmer, I want `LastHitFadeComponent` stored as a **`UPROPERTY` pointer**, so that the garbage collector does not collect the component while the trace Actor holds a reference.
23. As a programmer, I want **IsValid checks** before calling fade methods on the previous target, so that destroyed trees do not cause crashes.
24. As a programmer, I want hitting the **same tree repeatedly** to be a no-op, so that fade animation is not restarted every trace tick.
25. As a programmer, I want a **miss or non-tree hit** to fade in the previous target and clear the pointer, so that the world restores when the camera line is clear.
26. As a TA, I want an optional **`bDrawDebugTrace`** flag on the trace Actor, so that I can visualize sweep start, end, radius, and hit in the viewport during tuning.
27. As a TA, I want debug drawing **off by default**, so that shipping and normal PIE are not cluttered.
28. As a developer, I want fade interpolation via **`FInterpConstantTo`** (constant speed), so that the component avoids Timeline assets and stays easy to reason about.
29. As a developer, I want **`StartFadeOut` and `StartFadeIn` exposed as BlueprintCallable**, so that manual testing and future gameplay hooks are possible without new C++.
30. As a build engineer, I want runtime code in a **`TA_ToolsRuntime` module** separate from the existing Editor-only `TA_Tools` module, so that packaged games load the fade system without pulling editor dependencies.
31. As a TA, I want the existing **`BPC_TreeFadeComponent` blueprint kept** in the repo but unused in the Demo, so that legacy references are not broken during migration.
32. As a level designer, I want the **XrayHide demo level** to work with the new C++ stack after wiring (separate HITL issue), so that stakeholders can validate the feature in-context with existing tree materials.
33. As a programmer, I want a **Warning log** when `TargetActor` is null at BeginPlay, so that misconfigured trace Actors are obvious in Development builds.
34. As a TA, I want default fade speeds of **FadeOutSpeed = 4.0** and **FadeInSpeed = 2.0**, so that out takes roughly 0.25 s and in roughly 0.5 s for a full 0↔1 transition at default values.
35. As a developer, I want both runtime classes marked **`BlueprintSpawnableComponent` / placeable Actor** as appropriate, so that the assembly matches the "drag a blueprint demo" workflow agreed in design review.

## Implementation Decisions

### Plugin module split

- Add a new **Runtime** module `TA_ToolsRuntime` under the existing `TA_Tools` plugin.
- Keep the current `TA_Tools` module as **Editor** type unchanged (`SplineGrassGenerator` and other editor tools stay there).
- Register both modules in the plugin descriptor.
- `TA_ToolsRuntime` public dependencies: `Core`, `CoreUObject`, `Engine`. No `UnrealEd` or editor-only modules.

### UTreeFadeComponent (Actor Component)

- Inherits `UActorComponent`; `BlueprintSpawnableComponent`.
- **BeginPlay**:
  - `GetOwner()->GetComponents<UStaticMeshComponent>(MeshComponents)`.
  - For each mesh, for each material index: `CreateDynamicMaterialInstance`; if the instance exposes the configured scalar parameter (`EffectAmount` by default), append to `DynamicMaterials`.
  - `SetComponentTickEnabled(false)` after setup.
- **Properties** (BlueprintReadWrite unless noted):
  - `TargetEffectAmount`, `CurrentEffectAmount` (runtime state)
  - `FadeOutSpeed` default `4.0f`, `FadeInSpeed` default `2.0f`
  - `FadeParamName` default `"EffectAmount"`
- **Public API**:
  - `StartFadeOut()` → `TargetEffectAmount = 1`, enable Tick
  - `StartFadeIn()` → `TargetEffectAmount = 0`, enable Tick
- **TickComponent**:
  - Interpolate `CurrentEffectAmount` toward `TargetEffectAmount` using `FInterpConstantTo` with the speed matching the current direction (fade-out uses `FadeOutSpeed`, fade-in uses `FadeInSpeed`).
  - For each MID in `DynamicMaterials`: `SetScalarParameterValue(FadeParamName, CurrentEffectAmount)`.
  - When `FMath::IsNearlyEqual(CurrentEffectAmount, TargetEffectAmount)`, disable Tick.

### AOcclusionTraceActor (placeable Actor)

- Inherits `AActor`; placeable in editor; **not** a component on the character.
- **Properties**:
  - `TargetActor` (`AActor*`, EditInstanceOnly / BlueprintReadWrite)
  - `TraceInterval` default `0.05f`
  - `SweepRadius` default `25.f`
  - `TargetZOffset` default `80.f`
  - `bDrawDebugTrace` default `false`
  - `LastHitFadeComponent` (`UTreeFadeComponent*`, `UPROPERTY()`, private or protected)
- **BeginPlay**: if `TargetActor` valid → `StartTrace()`; else `UE_LOG` Warning (Development).
- **StartTrace / StopTrace**: manage `FTimerHandle` for periodic trace; clearing timer on stop.
- **Trace logic** (each timer fire):
  - Resolve camera location from **Player 0** `PlayerCameraManager`.
  - `TraceStart = TargetActor->GetActorLocation() + FVector(0,0,TargetZOffset)`.
  - `TraceEnd = CameraLocation`.
  - `SweepSingleByChannel` with `ECC_Visibility`, sphere radius `SweepRadius`.
  - On hit: `HitActor->FindComponentByClass<UTreeFadeComponent>()`.
  - Apply single-target state machine (below).

### Single-target trace state machine

From design interview (prototype decision — encodes exact transition table):

```
On trace tick:
  Resolve HitComponent from sweep (or nullptr)

  if HitComponent valid:
    if HitComponent != LastHitFadeComponent:
      if IsValid(LastHitFadeComponent): LastHitFadeComponent->StartFadeIn()
      LastHitFadeComponent = HitComponent
      LastHitFadeComponent->StartFadeOut()
    else:
      // same tree — no-op
  else:
    if IsValid(LastHitFadeComponent): LastHitFadeComponent->StartFadeIn()
    LastHitFadeComponent = nullptr
```

### Material contract

- Participating materials must define a **scalar** parameter named `EffectAmount` (or the overridden `FadeParamName`).
- `0` = fully opaque / solid; `1` = fully faded (matches existing XrayHide dither material intent).
- Slots without the parameter are skipped silently.

### Migration / coexistence

- New Demo path: C++ `UTreeFadeComponent` on tree Blueprints; `AOcclusionTraceActor` in level.
- Existing `BPC_TreeFadeComponent` blueprint asset **not deleted**; Demo explicitly does not use it.
- HITL follow-up: rewire `XrayHide` demo Blueprints and level (see issue `008`).

### Debug visualization

- When `bDrawDebugTrace` true: draw line from start to end, sweep sphere at intervals, color hit vs miss (e.g. green/red) using `DrawDebugLine` / `DrawDebugSphere`.
- Guard or no-op in Shipping if needed; acceptable to use `ENABLE_DRAW_DEBUG` or `GetWorld()->WorldType` check.

## Testing Decisions

### What makes a good test

Tests should assert **observable behavior** — which fade commands fire for which trace outcomes, and whether `EffectAmount` reaches expected values over time — without coupling to internal Timer handles or exact `DrawDebug` call counts. Prefer seams that do not require a full rendered PIE session when a pure function suffices.

### Proposed seams (highest first)

1. **Trace state-machine seam (highest pure seam, recommended extraction)**  
   A small free function or static helper, e.g. `ApplyOcclusionTraceResult(UTreeFadeComponent* Previous, UTreeFadeComponent* Hit, FSingleTargetFadeCallbacks& Out)`, that implements the transition table above and returns which side effects (`FadeInPrevious`, `FadeOutNew`, `ClearTarget`) should occur. Cover with **Automation tests** or a lightweight test module if the repo adds one; otherwise manual table review during code review. This is the highest seam because it encodes the bug-prone GC / multi-target logic without `UWorld` or physics.

2. **Interpolation seam (medium)**  
   If fade speed selection (in vs out) is extracted, unit-test that given `Current`, `Target`, `DeltaTime`, and speed, the next value moves correctly and snaps to target within epsilon. Maps directly to `FInterpConstantTo` usage.

3. **Material filter seam (medium, optional)**  
   Helper that given a `UMaterialInterface*` and `FName` returns whether the scalar exists — testable with authored test materials in editor content, or mocked in editor-only test if available.

4. **Integration / acceptance seam (authoritative for Demo)**  
   Manual PIE in **`XrayHide`** after HITL wiring: place `AOcclusionTraceActor`, assign player Pawn, tree with `UTreeFadeComponent` and leaf materials using `EffectAmount`. Verify: tree fades when between camera and character; restores when moving aside; switching between two trees fades only one at a time; no crash when tree is destroyed while faded.

5. **Packaging smoke (low frequency)**  
   Confirm `TA_ToolsRuntime` loads in a packaged Development build and components tick — validates module type split.

**Prior art**: No existing Automation tests in repo for TA_Tools; grass PRD uses pure `BuildGrassMesh` overload as seam. This PRD mirrors that pattern by recommending extraction of the trace state machine for testability.

### Suggested acceptance scenarios

- Tree with trunk (no `EffectAmount`) + leaf (has `EffectAmount`): only leaf fades.
- First trace hit on tree A → A fades out; continue hitting A → no restart flicker.
- Hit tree B while A faded → A fades in, B fades out.
- Clear line of sight → current tree fades in, pointer cleared.
- `StopTrace` → no further state changes until `StartTrace`.
- `TargetActor` null at BeginPlay → Warning, no timer.
- `bDrawDebugTrace` true → visible sweep in viewport; false → no debug primitives.

## Out of Scope

- **Multi-target occlusion** (fade several trees simultaneously); v1 is strictly single `LastHitFadeComponent`.
- **Custom collision channel `TreeOccluder`**; v1 uses `Visibility` only.
- **Per-character camera from TargetActor's Controller**; v1 uses Player 0 `PlayerCameraManager` only.
- **Automatic capsule-height trace origin**; v1 uses fixed `TargetZOffset` only.
- **Foliage / HISM instances** without an owning Actor that can host `UTreeFadeComponent`.
- **Deleting or refactoring `BPC_TreeFadeComponent`** blueprint graphs in this PRD.
- **Material authoring** for `EffectAmount` / dither logic (assumes existing XrayHide materials).
- **Post-process X-ray materials** (`M_Post_Xray` etc.); this PRD covers mesh fade only.
- **Network replication / multiplayer** fade state.
- **Timeline-based easing curves**; v1 is `FInterpConstantTo` only.

## Further Notes

- All decisions in this document come from a structured design interview (18 questions) covering module placement, single vs multi target, Actor vs Character-attached trace, trace direction, sweep vs line, collision channel, parameter naming, interpolation method, mesh coverage, fade speeds, trace frequency, camera resolution, Z offset, material filtering, blueprint migration, debug draw, and auto-start behavior.
- The existing `TA_Tools` plugin module is **Editor-only** today; adding `TA_ToolsRuntime` is mandatory for packaged runtime use.
- Demo assembly is intentionally **Blueprint-friendly**: add component to tree, place trace Actor, set `TargetActor` — no Character C++ changes.
- Implementation issue: `docs/issues/007-tree-fade-runtime-cpp.md`. Editor wiring: `docs/issues/008-xrayhide-demo-hitl-wiring.md`.
