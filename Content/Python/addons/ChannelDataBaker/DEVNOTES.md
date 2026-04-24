# ChannelDataBaker 开发笔记

> 项目：InteractiveGrassMy（Unreal Engine 交互草地）
> 插件：ChannelDataBaker —— 在 Blender 中把物体 pivot 坐标烘培到 UV/顶点色，供 UE shader 做 per-instance 草地动画。

---

## 目录

1. [插件无法在 Blender 显示 — 踩坑全记录](#1-插件无法在-blender-显示--踩坑全记录)
2. [目录结构整合](#2-目录结构整合)
3. [面板位置调整](#3-面板位置调整)
4. [UV 烘培数据与 UE shader 对接](#4-uv-烘培数据与-ue-shader-对接)
5. [最终插件使用说明](#5-最终插件使用说明)

---

## 1. 插件无法在 Blender 显示 — 踩坑全记录

### 坑 1：`bl_info` 版本门槛太高

**现象：** 插件列表里搜不到 Channel Data Baker。  
**原因：** `bl_info` 里写了 `"blender": (4, 2, 0)`，如果 Blender 版本低于 4.2，会被过滤掉不显示。  
**修复：** 降到 `"blender": (3, 6, 0)`。

```python
# 改前
"blender": (4, 2, 0),
# 改后
"blender": (3, 6, 0),
```

---

### 坑 2：外层目录名带点（`.`）

**现象：** 本地安装（Script Directory）方式，插件仍不显示。  
**原因：** 原目录名 `ChannelDataBaker_v1.0.1`，Python 把目录名当模块名导入，`1.0.1` 含点号导致导入失败。  
**修复：** 把外层目录改名，去掉点号（如 `ChannelDataBaker_v1_0_1` 或直接 `ChannelDataBaker`）。

---

### 坑 3：Script Directory 路径指向错误

**现象：** 路径设对了但还是找不到。  
**原因：** Blender 本地脚本扫描规则是：
```
Script Directory/
└── addons/
    └── 插件名/
        └── __init__.py   ← Blender 才认
```
如果把 Script Directory 指向了插件目录本身（而不是父级），Blender 扫不到。  
**修复：** Script Directory 指向 `Content/Python`，插件放在 `Content/Python/addons/ChannelDataBaker/`。

---

### 坑 4：`bl_info` 必须是文件内的字面量字典（AST 限制）

**现象：**
```
AST error parsing bl_info for: '...\addons\ChannelDataBaker\__init__.py'
ValueError: malformed node or string on line 1: <ast.Attribute object at ...>
```
**原因：** 早期方案中，`addons/ChannelDataBaker/__init__.py` 作为包装入口，写了 `bl_info = _impl.bl_info`。  
Blender 在扫描插件列表阶段用 `ast.literal_eval` 静态解析 `bl_info`，不执行代码，所以任何非字面量赋值都会报这个错。  
**修复：** `bl_info` 必须是文件内硬编码的字典字面量：

```python
# 必须这样写（字面量）
bl_info = {
    "name": "Channel Data Baker",
    "version": (1, 0, 1),
    ...
}

# 不能这样写（会报 AST 错）
bl_info = some_module.bl_info
```

---

### 坑 5：`No module named 'ChannelDataBaker.lib'`

**现象：** 插件能显示，启用时报错 `No module named 'ChannelDataBaker.lib'`。  
**原因：**  
- `lib/` 子目录缺少 `__init__.py`，Python 不认为它是包  
- 早期"包装入口 + 真实源码分离"的结构导致模块路径解析失败  
**修复：**  
1. 补上 `lib/__init__.py`  
2. 将插件完全整合为单一自包含目录（见下节）

---

## 2. 目录结构整合

### 演变过程

**最初（混乱）：**
```
Content/Python/
├── ChannelDataBaker_v1.0.1/   ← 文件夹名带点，导入失败
│   └── ChannelDataBaker/
│       ├── __init__.py
│       └── lib/
└── addons/
    └── ChannelDataBaker/
        └── __init__.py        ← 只是个包装，bl_info 动态赋值，AST 报错
```

**整合后（正确）：**
```
Content/Python/
├── addons/
│   └── ChannelDataBaker/      ← Blender Script Directory 指向 Content/Python
│       ├── __init__.py        ← 完整插件入口，bl_info 字面量，register/unregister
│       └── lib/
│           ├── __init__.py    ← 必须有，声明子包
│           ├── panel.py
│           ├── cdb_utils.py
│           ├── data_merge_transform.py
│           ├── data_merge_linear_mask.py
│           ├── batch_active_attribute.py
│           └── batch_smart_pivot.py
└── ChannelDataBaker/          ← 原始开发源码，可保留备份或删除
```

**Blender 设置：**
- `Edit > Preferences > File Paths > Script Directories` 添加 `Content/Python`
- 重启 Blender，Add-ons 搜索 `Channel Data Baker` 启用

---

## 3. 面板位置调整

### 从 Tool 标签移出

`bl_category = 'Tool'` 会把面板放到 3D 视口侧边栏的 "Tool" 标签下，跟 Blender 内置工具混在一起不好找。  
改为独立标签 `ChBaker`：

```python
# lib/panel.py
class VIEW3D_PT_tools_channel_data_baker(bpy.types.Panel):
    bl_category = 'ChBaker'   # 改前是 'Tool'，中途用过 'CDB'（容易被误读为 CBD）
```

同步修改 `bl_info` 里的 `location` 描述：
```python
"location": "3D Viewport > Sidebar > ChBaker",
```

---

## 4. UV 烘培数据与 UE shader 对接

### 烘培原理

插件在 Blender 里把每个草叶物体的 **世界坐标 `object.location`（pivot/原点位置）** 存入 UV 通道。  
导入 UE 后，shader 从 UV 读取坐标，用于 per-instance 草地摆动偏移计算。

---

### 坑 6：UE shader 里用了 TransformPosition（Local→World）

**现象：** UE 里读到的 pivot 位置不对。  
**原因：** UV 里存的已经是 **Blender 世界坐标**，不是本地坐标。  
如果 shader 里还接一个 `TransformPosition (Local Space → Absolute World Space)`，会把已经是世界坐标的数据再做一次本地→世界变换，结果当然错。  
**修复：** 删掉 `TransformPosition` 节点，UV × 100（单位换算）的结果直接就是 UE 世界坐标（厘米）。

---

### Blender → UE 坐标轴对应关系

| Blender | UE | 说明 |
|---|---|---|
| X（右） | Y（右） | |
| Y（前） | X（前）× -1 | 方向相反 |
| Z（上） | Z（上） | 相同 |

标准 FBX 导出设置（Forward = -Y，Up = Z）下：
- **UE 世界 X** = `-Blender location.y`
- **UE 世界 Y** = `+Blender location.x`

所以在 Blender 中烘培时应该：

| 烘培轴 | UV 通道 | Negate | 结果 |
|---|---|---|---|
| Y 轴 | U（R 通道） | ✅ | UE 世界 X |
| X 轴 | V（G 通道） | ❌ | UE 世界 Y |

对应的 UE shader 连法（最简）：
```
TexCoord[0] → ×100 → Append(R, G, 0) → SphereMask A
Absolute World Position → SphereMask B
```

---

### 坑 7：FBX 导出的 V 轴翻转

**背景：**
- Blender UV：V=0 在底部
- FBX / UE（DirectX 约定）：V=0 在顶部

Blender 导出 FBX 时自动翻转 V：`V_导出 = 1 - V_Blender`  
所以烘培到 V 通道的值，UE 读到的会是 `1 - 原始值`。

**补偿方案（最终放弃，在插件里不做补偿）：**  
曾尝试在插件烘培 V 通道时预存 `1 - value`，让 FBX 再翻转回来等于原始值，shader 里不需要额外处理。  
但因为行为不透明、容易混乱，最终**还原为存原始值**，由用户在 shader 里自行处理（如有需要用 `1 - G`）。

---

### 新增功能：Negate（取反）选项

在面板每个轴旁边加了 **Negate** 勾选框，用于直接在烘培时翻转值的正负号（如处理 UE X = -Blender Y 的情况），避免在 shader 里手动乘 -1。

相关代码（`data_merge_transform.py`）：
```python
value = getattr(target_obj.location, axis.lower())
if transform.negateValue:
    value = -value
```

---

## 5. 最终插件使用说明

### 安装

1. Blender `Edit > Preferences > File Paths > Script Directories`
2. 添加路径：`[项目路径]/Content/Python`
3. 重启 Blender
4. `Edit > Preferences > Add-ons` 搜索 `Channel Data Baker` 勾选启用
5. 3D 视口侧边栏（`N` 键）找到 `ChBaker` 标签

### 烘培 UE 草地 Pivot（Individual 模式推荐设置）

| 轴 | Mode | UV Ch | Channel UV | Negate |
|---|---|---|---|---|
| X | UV | 0 | V | ❌ |
| Y | UV | 0 | U | ✅ |
| Z | — | — | — | — |

UE shader：
```
TexCoord[0] → ×100 → Append(R, G, 0) → SphereMask Position A
Absolute World Position → SphereMask Position B
```

### 排错

| 症状 | 原因 | 解决 |
|---|---|---|
| 插件列表找不到 | Blender 版本 < 3.6 | 升级 Blender |
| 插件列表找不到 | Script Directory 路径不对 | 指向 `Content/Python`（不是 `addons/`） |
| 启用时报 AST 错 | `bl_info` 不是字面量 | 检查 `__init__.py` 第一行 |
| 启用时报模块找不到 | `lib/__init__.py` 缺失 | 补上空文件 |
| UE 里 pivot 位置偏 | shader 里有 TransformPosition | 删掉该节点 |
| UE 里 pivot 轴向不对 | Blender/UE 坐标系差异 | X→V，Y→U+Negate |
