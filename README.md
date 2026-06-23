# InteractiveGrassMy

一个基于 Unreal Engine 5.6 的交互草地实验项目，包含草地受角色/遮罩影响的交互效果，以及一个配套的 Blender 数据烘培插件 `ChannelDataBaker`。

## 项目内容

- UE5 交互草地示例场景
- 草地材质、Render Target、交互蓝图
- Blender 插件 `ChannelDataBaker`，用于把物体 pivot / 位置数据烘培到 UV，供 UE shader 使用

## 运行环境

- Unreal Engine `5.6`
- Windows 桌面平台
- 如需使用 Blender 插件，建议 Blender `3.6+`

## 快速开始

1. 用 Unreal Engine 5.6 打开 `InteractiveGrassMy.uproject`
2. 默认启动地图为 `Content/InteractiveGrass/Maps/TutorialMap`
3. 如果工程提示重新生成 C++ 项目，可重新生成项目文件或使用 `rebuild_cpp_env.bat`

## Blender 插件

插件目录位于：

`Content/Python/addons/ChannelDataBaker`

在 Blender 中可将 `Content/Python` 加到 `Script Directories`，然后启用 `Channel Data Baker`。

相关说明文档见：

`Content/Python/addons/ChannelDataBaker/DEVNOTES.md`

## DSL / 自动导出

- **Blueprint → BlueprintLisp**
  - 脚本：`Content/Python/export_blueprints.py`
  - 用法（UE Python 控制台 / Output Log）：
    - 将 `Content/Python` 加入 `sys.path`
    - 调用 `export_blueprints.export_all()` 或 `export_blueprints.export_path("/Game/InteractiveGrass")`
  - 输出位置：`Saved/BP2DSL/BlueprintLisp/.../*.bplisp`

- **Material → MatLang**
  - 脚本：`Content/Python/export_materials.py`
  - 依赖插件：`Plugins/MaterialBP2DSL`（提供 `MatBP2FPPythonBridge`）
  - 支持将 `Material / MaterialInstance / MaterialFunction` 导出为可读 DSL：
    - 基础 `Material`：通过 MatLang 导出完整节点图（含 `(expressions ...)` / `(outputs ...)`）
    - `MaterialInstance`：导出标量/向量/贴图/静态开关参数
    - `MaterialFunction`：通过 MatLang 导出完整节点图（含 `(function-inputs ...)` / `(function-outputs ...)` / `(expressions ...)`）
  - 常用用法：
    - Content Browser 选中若干材质资产 → `export_materials.export_selected()`
    - 或指定路径批量导出：`export_materials.export_path("/Game/InteractiveGrass")`
  - 输出位置：`Saved/BP2DSL/Materials/.../*.matdsl`

## 目录概览

- `Content/InteractiveGrass/`: 交互草地主要资源与地图
- `Content/Python/addons/ChannelDataBaker/`: Blender 插件源码
- `Source/InteractiveGrassMy/`: C++ 模块
- `Config/`: 工程配置

## 注意事项

- 仓库已通过 `.gitignore` 忽略 Unreal 生成文件，如 `Binaries/`、`Intermediate/`、`Saved/`
- `Plugins/Blueprint2DSL-main` 当前是独立 Git 仓库引用，不是普通目录拷贝；如果你克隆后缺少该插件内容，需要单独获取或移除该插件目录
- `Plugins/MaterialBP2DSL` 为材质 DSL（MatLang）支持插件，Material 导出脚本依赖其中的 `MatBP2FPPythonBridge`，在其它工程中复用脚本时需要一并启用该插件

