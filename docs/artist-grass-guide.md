# 交互草地 — 美术工作流指南

面向关卡/TA 美术，说明如何生成草叶 Mesh、刷草、配置材质风动与交互，以及 LOD / 剔除相关设置。

**引擎版本：** Unreal Engine 5.6  
**示例资源路径：** `Content/XW_Art/RES/TAExample/`

---

## 目录

1. [整体流程](#1-整体流程)
2. [草叶 Mesh 生成（Spline Grass Generator）](#2-草叶-mesh-生成spline-grass-generator)
3. [刷草（Foliage / HISM）](#3-刷草foliage--hism)
4. [材质 M_GrassY 调参](#4-材质-m_grassy-调参)
5. [交互蓝图 BP_GrassInteract2](#5-交互蓝图-bp_grassinteract2)
6. [LOD 与性能说明](#6-lod-与性能说明)
7. [检查清单与常见问题](#7-检查清单与常见问题)

---

## 1. 整体流程

```
样条线编辑草形 → 导出 StaticMesh（含多 LOD）
       ↓
创建 Foliage Type → Foliage 模式刷草
       ↓
草 Mesh 指定 M_GrassY 材质实例
       ↓
关卡放置 BP_GrassInteract2 → 角色踩草/拨草生效
       ↓
（可选）调整 MPC_WindGrass2 全局风参数
```

---

## 2. 草叶 Mesh 生成（Spline Grass Generator）

### 2.1 放置与预览

1. 在 **Place Actors** 中搜索 **Spline Grass Mesh Generator**（`TA_Tools` 插件提供）。
2. 拖入关卡，选中 Actor。
3. 编辑 **Spline Component** 上的控制点，塑造草叶弯曲形状（根 → 尖）。
4. 修改 Details 参数后，预览会自动刷新（始终显示 **LOD0** 最高精度，不受 LOD 切换影响）。

默认导出路径：`/Game/XW_Art/RES/TAExample/GrassAnim/Mesh/`  
默认 Mesh 名称：`SM_Grass`

### 2.2 形状参数（Spline Grass | Shape）

| 参数 | 说明 | 默认值 | 调参建议 |
|------|------|--------|----------|
| **Base Width** | 草根处叶片半宽（cm） | 5.0 | 越宽越「肥」，近景草可略大 |
| **Tip Width** | 草尖处叶片半宽（cm） | 0.5 | 尖部收窄，0 则收成线 |
| **Width Curve** | 沿高度对宽度的额外曲线乘子 | 无 | 需要非线性胖瘦时使用 |
| **Length Segments** | 沿草叶长度分段数（LOD0 兼容项） | 8 | 与 LOD0 同步；越高越弯得 smooth |
| **Width Segments** | 沿宽度分段数 | 1 | 一般保持 1 即可 |
| **Flip U / Flip V** | 翻转 UV | false | 贴图方向不对时再改 |
| **Double Sided** | 双面几何 | true | 草必须双面，勿关 |
| **Smooth Normals** | 平滑法线 | true | 一般保持开启 |

**Mesh 数据约定（给材质用）：**

- **UV0**：U = 宽度方向，V = 高度方向（0 = 根，1 = 尖）。
- **UV1**：与 UV0 相同拷贝，供宽度/厚度计算使用。
- **顶点色 RGB**：沿高度 0→1 的渐变（根暗、尖亮），材质里用于 bend mask、渐变着色等。

### 2.3 多 LOD 导出（Spline Grass | LOD）

`LODs` 数组每一项对应 StaticMesh 的一个 LOD 级别：

| 字段 | 含义 |
|------|------|
| **Length Segments** | 该 LOD 的长度分段（越少面数越低） |
| **Width Segments** | 宽度分段 |
| **Screen Size** | UE 内置 LOD 切换阈值（见 [§6](#6-lod-与性能说明)） |

**推荐默认（已内置）：**

| LOD | Length Segments | Width Segments | Screen Size | 大致用途 |
|-----|-----------------|----------------|-------------|----------|
| LOD0 | 8 | 1 | 1.0 | 近景，18 顶点 |
| LOD1 | 4 | 1 | 0.08 | 中景，10 顶点 |
| LOD2 | 2 | 1 | 0.03 | 远景，6 顶点 |

> 所有 LOD 共用同一套样条线形状（BaseWidth、TipWidth、WidthCurve），仅网格密度不同，切换时轮廓一致。

### 2.4 导出步骤

1. 确认 **Mesh Name**、**Export Path**。
2. 点击 **Export To Static Mesh**。
3. 在 Content Browser 打开导出的 StaticMesh（如 `SM_Grass`）。
4. **手动指定材质槽**：将 Slot `Grass` 的材质改为 `M_GrassY` 或你的材质实例（如 `M_GrassY_Inst`）。导出时暂挂引擎默认材质，需美术自行替换。
5. 在 StaticMesh 编辑器 **LOD Settings** 中确认有 3 级 LOD，Screen Size 与 Generator 里一致。

**顶点/面数参考（Double Sided = true）：**

| Length Segments | 顶点数 | 三角面数（双面） |
|-----------------|--------|------------------|
| 8 | 18 | 32 |
| 4 | 10 | 16 |
| 2 | 6 | 8 |

---

## 3. 刷草（Foliage / HISM）

### 3.1 创建 Foliage Type

1. 打开 **Foliage** 模式（Shift + 3）。
2. **+ Add Foliage Type** → **Static Mesh**。
3. 指定上一步导出的草 StaticMesh（如 `SM_Grass` / `SM_Grass_Lod`）。
4. 确认 Mesh 材质槽已是 `M_GrassY` 系列实例。

### 3.2 绘制

- 用 **Paint** 工具在 Landscape 或 Static Mesh 表面刷草。
- 调整 **Paint Density**、**Radius**、**Scale Min/Max** 控制密度与随机大小。
- 如需多种草，为每种 Mesh 各建一个 Foliage Type。

### 3.3 距离剔除（Cull Distance）— 必配

在 Foliage Type 的 **Culling** 中：

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| **Cull Distance Min** | 0 | 从相机开始就参与渲染 |
| **Cull Distance Max** | **8000**（= 80 m，UE 单位为 cm） | 超过此距离 **整簇 HISM 实例不再渲染** |

HISM 同时自带 **视锥剔除**：相机背对草地时 draw call 会下降。Cull Distance 管的是「太远完全不画」，与 Mesh LOD 是两层优化。

### 3.4 其他 Foliage 建议

| 项 | 建议 |
|----|------|
| **Collision** | 关闭（草不需要物理碰撞） |
| **Cast Shadow** | 近景可开；大场景远景草可关以省性能 |
| **Random Yaw** | 开启，避免整齐划一 |
| **Align to Normal** | 贴地形时开启 |

示例地图：`Content/XW_Art/RES/TAExample/GrassAnim/GrassLod.umap`

---

## 4. 材质 M_GrassY 调参

**资产路径：** `Content/XW_Art/RES/TAExample/GrassAnim/Mat/M_GrassY`  
**着色模型：** Two Sided Foliage，**Two Sided = true**  
**工作方式：** 顶点动画全部走 **World Position Offset (WPO)**，最终输出为：

```
WPO = 草叶宽度偏移 + 风动 + 角色交互压草 + 随机 Z 轴旋转
```

> 美术请优先改 **Material Instance**（如 `M_GrassY_Inst`、`M_GrassY_Wave_Inst`），不要直接改母材质，除非 TA 要改逻辑。

### 4.1 01 — Albedo（颜色）

| 参数 | 作用 | 默认倾向 |
|------|------|----------|
| **ColorGround / ColorMid / ColorTip** | 根 / 中 / 尖三层渐变底色 | 绿黄渐变 |
| **ColorGradient** | 渐变位置（X=尖阈值, Y=中阈值, Z=根阈值） | 控制各色过渡高度 |
| **Tint** | 整体色调 | 偏灰绿 |
| **AlbedoCntrol** | X=饱和度, Y=?, Z=亮度, W=色相偏移 | 微调整体 |
| **ArtWaveColor** | 风动噪声叠加的艺术色 | 一般保持黑 |
| **ArtWaveContrast** | 风动区域对比度 | 2.0 |

### 4.2 01 — Wind（风动）

| 参数 | 作用 | 调参建议 |
|------|------|----------|
| **IsWave**（静态开关） | 是否启用「大面积波浪」风 | 默认开；只要 flutter 可关 |
| **FlutterFreq** | 单株抖动频率 | 增大 → 抖更快 |
| **FlutterPhase** | 单株抖动相位随机范围 | 与 Freq 配合 |
| **FlutterStrength** | 单株抖动幅度 | 过大显得抽搐 |
| **SingleRandom** | 单株随机权重 | 0.5 |
| **RotateRandom** | 实例随机绕 Z 轴旋转幅度 | 0.2，增加朝向变化 |
| **RotateZ** | 额外固定 Z 旋转（度） | 一般 0 |

**全局风（Material Parameter Collection）：**  
路径 `/Game/Materials/MPCollection/MPC_WindGrass2`

| MPC 参数名 | 作用 |
|------------|------|
| Wind Dricetion | 风向（2D，材质内 normalize） |
| Wind Strength | 波浪风强度 |
| Wind Speed | 风流动速度 |
| Wind Phase | 波浪相位 |
| Noise Tilling | 噪声平铺（世界空间） |
| Noise Tilling Wave | 艺术波浪噪声平铺 |

在关卡中放 **Wind Directional Source** 或 TA 蓝图驱动 MPC，即可全场景统一改风。

**风动贴图依赖：**

- `T_Grass_Noise` — 世界空间风噪声
- `T_Static_Mask` — 区域遮罩（flutter 强度）
- `T_Wheat_Mask` — 高度遮罩（根不动、尖动得大）

### 4.3 02 — Grass Shape（几何宽度）

| 参数 | 作用 |
|------|------|
| **ThicknessVariation** | 叶片厚度随机变化，配合 UV1 控制 billboard 宽度 |

宽度由 **视图方向** 挤出（`ViewRight`），所以草在屏幕上始终有一定厚度，不正面看时不会消失成线。

### 4.4 04 — Specular（高光）

| 参数 | 作用 |
|------|------|
| **Roughness** | 粗糙度，默认 0.1 |
| **SpecularIntensity** | 高光强度 |
| **SpecularColor** | 高光颜色 |
| **NormalFlatten** | 法线向竖直方向混合，0=用法线贴图，1=更平 |

法线贴图：`T_Grass_BG3_N`

### 4.5 交互压草（Interactive）

材质从 **Render Target** 读取角色踩踏数据（R=方向角, G=形变幅度），并结合：

| 输入 | 来源 |
|------|------|
| **PlayerPos** | MPC `MPC_Grass_Interaction2`（BP 每帧写入） |
| **BendAnlge** | 同上（注意资产里拼写为 Anlge） |
| **BendMask** | UV 高度：草根几乎不弯，草尖全弯 |
| **CaptureSize** | 材质内常量 **1000 cm**（10 m × 10 m 交互区域） |

**重要：** 材质实例需把 **`RT_0`**（或 BP 输出的当前帧 RT）绑定到材质的 **Vector RT** 纹理参数，否则只有风没有交互。示例 RT 路径：

`Content/XW_Art/RES/TAExample/GrassInteraction/RT/RT_0`

### 4.6 其他

| 参数 | 作用 |
|------|------|
| **SSS** | Two Sided Foliage 的次表面散射强度 |

---

## 5. 交互蓝图 BP_GrassInteract2

**资产路径：** `Content/XW_Art/RES/TAExample/GrassInteraction/Blueprint/BP_GrassInteract2`

### 5.1 原理（简述）

```
每帧 Tick
  ├─ 更新 MPC：PlayerPos、GrassHeight、BendAngle
  ├─ Force1：根据玩家位移/速度，向 RT 写入「力场」
  ├─ Offset2：根据玩家世界位置，向 RT 写入「偏移场」
  └─ RT0 ↔ RT1 双缓冲交换（Ping-Pong）
       ↓
M_GrassY 采样 RT → 顶点向踩踏方向弯折
```

关联材质（仅 BP 内部 Dynamic MID，美术一般不用手改）：

- `M_Force_Grass` — 力场累积
- `M_Offset_Grass` — 位置偏移

Render Target：`RT_0`、`RT_1`、`RT_Temp`

### 5.2 场景放置

1. 将 **BP_GrassInteract2** 拖入关卡（通常 **1 个关卡 1 个** 即可）。
2. 确保关卡有 **Player Character**（蓝图通过 `GetPlayerCharacter` 取位置）。
3. **Trace Mesh** 组件的 **Scale** 决定交互捕获范围：

   ```
   捕获边长 (cm) = TraceMesh Scale × 100
   ```

   材质里 **CaptureSize = 1000**，因此 TraceMesh 的 XY Scale 建议设为 **(10, 10, …)**，使捕获区域与材质一致。改 Scale 后若不一致，需 TA 同步改材质常量或改为 MPC 驱动。

4. BP 会跟随玩家移动（Z 方向有约 80 cm 偏移），使 RT 采样中心始终在角色附近。

### 5.3 Details 可调参数

在 BP 实例 Details 中可调整（名称以编辑器为准）：

| 参数 | 作用 | 调参方向 |
|------|------|----------|
| **GrassHeight** | 写入 MPC，供交互计算参考草高 | 与场景草实际高度匹配 |
| **BendAngle** | 最大弯折角倍率（材质内 ×50° 量级） | 增大 → 踩下去弯得更狠 |
| **Radius** | 交互影响半径基础值 | 增大 → 影响范围更大 |
| **Damping** | 力场衰减 | 增大 → 草更快恢复、痕迹更短 |
| **SprintK** | 弹簧刚度（蓝图内变量名拼写为 SprintK） | 影响回弹速度 |
| **ForceClampMax** | 单帧力向量上限 | 防止极速移动时爆值 |
| **N** | RT 分辨率相关（TexelSize = Scale×100 / N） | 越大 RT 越细、性能开销越高 |
| **CenterUV** | 力场材质 UV 中心 | 一般保持默认 |

**Force1 逻辑摘要：**

- 玩家 **空中下落** 时交互半径为 0（不踩草）。
- 否则半径随 **水平速度** 缩放：`速度 × 0.002 × (Radius × 0.01)`。

### 5.4 运行与清理

- **BeginPlay**：初始化 RT、创建 MID。
- **EndPlay**：清空所有 RT，避免残留。

PIE 测试：运行游戏走过草地，草应沿移动方向倒伏并缓慢恢复。

---

## 6. LOD 与性能说明

本项目草地的性能分 **三层**，互不替代：

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1 — Mesh LOD（StaticMesh Screen Size）           │
│  近：LOD0 8段 → 中：LOD1 4段 → 远：LOD2 2段              │
├─────────────────────────────────────────────────────────┤
│  Layer 2 — 材质 WPO 开销                                 │
│  近景：完整风动 + 交互；远景 LOD 顶点少，WPO 计算量自然降 │
│  （可选优化：WPO 距离衰减，见 docs/issues/004）           │
├─────────────────────────────────────────────────────────┤
│  Layer 3 — Foliage Cull Distance + 视锥剔除              │
│  >80 m 不渲染；不在相机视野内不渲染                       │
└─────────────────────────────────────────────────────────┘
```

### 6.1 Screen Size 是什么？

**Screen Size** 不是距离（米），而是 **LOD 在屏幕上占视口比例** 的阈值（0~1）：

- **1.0** — 仅当 LOD0 占满屏时也用 LOD0（最高级永远负责最近处）。
- **0.08** — 当 LOD0 在屏幕上小于约 8% 宽时，切到 LOD1。
- **0.03** — 更小则切 LOD2。

距离上大致对应：LOD0 近 ~8 m、LOD1 中 ~8–25 m、LOD2 远 ~25 m 以上（随 FOV 和草在屏占比变化）。

**改 Screen Size 的经验法则：**

- 切 LOD **太早**（阈值太大）→ 中距离草变细、跳变明显 → **减小** LOD1/LOD2 的 Screen Size。
- 切 LOD **太晚** → 远景仍用高面数 → **增大** LOD1 的 Screen Size 或降低 Length Segments。

### 6.2 材质侧配合

- 材质属性中建议开启 **Dithered LOD Transition**，LOD 切换时 dither 淡入淡出，减少 Pop。
- 远景可配合 WPO 距离衰减（规划见 `docs/issues/004-grass-material-wpo-distance-fade.md`）：8 m 内全风动，25 m 外可停 WPO。

### 6.3 性能验证命令（PIE 控制台）

```
stat scenerendering
stat rhi
```

观察：相机背对草、拉远到 80 m 外，draw call 与 instance 数应明显下降。

---

## 7. 检查清单与常见问题

### 7.1 上线前检查

- [ ] StaticMesh 已指定 `M_GrassY` 材质实例，且 **Vector RT** 指向 `RT_0`
- [ ] StaticMesh 含 ≥2 级 LOD，Screen Size 合理
- [ ] Foliage Type **Cull Distance Max = 8000**
- [ ] 关卡已放置 **BP_GrassInteract2**，TraceMesh Scale ≈ 10
- [ ] **MPC_WindGrass2** 风向/强度可在运行中生效
- [ ] PIE 走过草地有压草 + 回弹

### 7.2 常见问题

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| 草完全不动 | 未绑 Wind MPC 或 IsWave/Flutter 全关 | 检查 MPC_WindGrass2、材质实例开关 |
| 有风但不踩弯 | RT 未绑到材质 / 未放 BP | 绑 RT_0；放置 BP_GrassInteract2 |
| 交互范围不对 | TraceMesh Scale 与 CaptureSize 不一致 | Scale×100 ≈ 1000 cm |
| 踩草范围太小 | Radius 太小或移动太慢 | 增大 Radius；Force 与速度相关 |
| 中距离草突然变细 | LOD 切太早 | 降低 LOD1 Screen Size 或提高 LOD1 分段 |
| 远景还卡 | 未设 Cull Distance | Foliage Max = 8000 |
| 导出 Mesh 无材质 | 导出管线挂默认材质 | 手动换 M_GrassY |
| 预览与导出形状不一致 | 样条线改过未 Export | 再点 Export To Static Mesh |

### 7.3 相关资产速查

| 类型 | 路径 |
|------|------|
| 草材质母版 | `/Game/XW_Art/RES/TAExample/GrassAnim/Mat/M_GrassY` |
| 材质实例 | `M_GrassY_Inst`、`M_GrassY_Wave_Inst` 等 |
| 交互 BP | `/Game/XW_Art/RES/TAExample/GrassInteraction/Blueprint/BP_GrassInteract2` |
| 交互 MPC | `/Game/XW_Art/RES/TAExample/GrassInteraction/Blueprint/MPC_Grass_Interaction2` |
| 交互 RT | `.../GrassInteraction/RT/RT_0`、`RT_1` |
| 全局风 MPC | `/Game/Materials/MPCollection/MPC_WindGrass2` |
| 示例 Mesh | `.../GrassAnim/Mesh/SM_Grass`、`SM_Grass_Lod` |
| 示例地图 | `GrassAnim.umap`、`GrassLod.umap` |

### 7.4 技术文档（程序向）

- 多 LOD 生成 PRD：`docs/PRD-multi-lod-grass-generator.md`
- DSL 导出（便于读蓝图/材质逻辑）：`Saved/BP2DSL/`（运行 `Content/Python/export_blueprints.py` / `export_materials.py` 生成）

---

*文档基于 `M_GrassY.matdsl`、`BP_GrassInteract2` 蓝图 DSL 与 `SplineGrassGenerator` 源码整理。参数默认值以编辑器内资产为准。*
