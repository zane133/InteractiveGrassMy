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

## 目录概览

- `Content/InteractiveGrass/`: 交互草地主要资源与地图
- `Content/Python/addons/ChannelDataBaker/`: Blender 插件源码
- `Source/InteractiveGrassMy/`: C++ 模块
- `Config/`: 工程配置

## 注意事项

- 仓库已通过 `.gitignore` 忽略 Unreal 生成文件，如 `Binaries/`、`Intermediate/`、`Saved/`
- `Plugins/Blueprint2DSL-main` 当前是独立 Git 仓库引用，不是普通目录拷贝；如果你克隆后缺少该插件内容，需要单独获取或移除该插件目录

