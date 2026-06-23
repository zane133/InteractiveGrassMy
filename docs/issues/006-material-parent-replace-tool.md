# 006 — 母材质批量替换工具（PySide6）

**Status:** ready-for-agent

## Type

AFK — 编辑器 Python 脚本，可在无人工材质编辑的前提下实现

## Blocked by

None

## Parent

PRD: Material Parent Replace (`docs/PRD-material-parent-replace.md`)

## What to build

实现 PRD 中定义的 **母材质批量替换** 工具：在 TATools 菜单打开 PySide6 窗口，将直接挂在旧母材质下的 Material Instance 原地改挂到新母材质，按参数名迁移覆盖，支持预演、整批 Undo、报告与可选自动保存。

### 交付物

1. **`PackageInstall` 模块**（若项目中缺失）：为 TATools 提供 PySide6 自动安装，与参考工程一致。
2. **`TATools` 替换工具脚本**：核心逻辑（扫描、过滤、参数迁移、事务、报告）+ PySide6 窗口（`unreal_stylesheet`、`parent_external_window_to_slate`、全局窗口引用防 GC）。
3. **`PythonMenu` + `init_unreal` 集成**：在 **TATools / 材质** 分区注册菜单项，例如「母材质批量替换」。

### 核心行为

- 输入：旧 `UMaterial`、新 `UMaterial`、扫描路径（默认 Content Browser 选中文件夹，可编辑）、可选全项目扫描。
- 只处理 **直接 parent == 旧母材质** 的 `MaterialInstanceConstant` / `MaterialInstance`。
- 预演（默认）：只扫描 + 报告，不写资产；报告含 `[DRY RUN]`。
- 执行：单次 `ScopedEditorTransaction` 内 `set_material_instance_parent` + 按名写回参数；丢弃项写入报告。
- 执行后：Log + `Saved/MaterialParentReplace/<timestamp>.txt`；Content Browser 选中已修改实例；可选自动保存（默认关）。

### 测试接缝（实现时优先抽取）

1. 纯函数：参数名匹配 → kept / discarded（可无 UE 单测）。
2. 纯函数：资产路径规范化。
3. 编辑器冒烟：`MaterailReplace` / `MatSwitch` 示例内容上做预演 + 执行 + Undo。

## Acceptance criteria

- [ ] TATools 菜单可打开工具窗口，窗口嵌入 Slate 且不一闪而过
- [ ] 旧/新母材质路径可从 Content Browser 选中填入；打开前选中 1～2 个 Material 可预填
- [ ] 默认扫描路径为当前选中文件夹；可手改；勾选后扫描全 `/Game`
- [ ] 预演默认开启，不修改资产，生成带 `[DRY RUN]` 的报告文件
- [ ] 执行替换后，直接子实例 parent 指向新母材质；同名参数保留；多余参数在报告中列出
- [ ] 父级为其他 Material Instance 的实例不被修改
- [ ] 一次 Ctrl+Z 可撤销整批修改
- [ ] 执行后 Content Browser 选中所有被修改实例
- [ ] 勾选自动保存后，相关包写入磁盘
- [ ] 旧/新输入非 `UMaterial` 或两者相同时，工具给出明确错误且不修改资产

## Comments

_(conversation history appended here)_
