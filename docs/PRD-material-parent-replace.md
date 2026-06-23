# PRD: 母材质批量替换工具（Material Parent Replace）

**Status:** ready-for-agent

## Problem Statement

TA 在升级或切换母材质（Master Material）时，项目里往往已有大量 **Material Instance** 直接挂在旧母材质下，并带有美术调好的标量、向量、贴图、静态开关覆盖。手工在 Content Browser 里逐个打开实例、改 Parent、核对参数，既慢又容易漏改或丢参数。

项目已有材质 DSL 导出（`export_materials.py`）和若干 PySide6 TA 工具（`TATools/`），但缺少一个可预演、可撤销、可出报告的 **母材质 → 新母材质** 批量替换流程。`Content/XW_Art/RES/TAExample/MaterailReplace/MatSwitch.umap` 场景即为此类工作流的手动验证用例。

## Solution

在 UE 编辑器内提供 **TATools 菜单入口**，打开 PySide6 工具窗口。用户指定旧母材质、新母材质与扫描范围后，可先做 **预演（Dry Run）** 查看将受影响的实例与参数迁移情况，确认后再 **原地改挂** 直接子实例的 Parent，并尽量按参数名保留覆盖值。整次修改包在单次 Undo 事务中，可选执行后自动保存，并输出 Log + 文本报告。

## User Stories

1. As a TA, I want to open a **TATools** menu item that launches a material parent replace window, so that the tool sits alongside existing TA utilities like unused-material finders.
2. As a TA, I want the window to use **PySide6** with the project's **unreal_stylesheet** skin and embed into the editor via **parent_external_window_to_slate**, so that the UI feels consistent with other in-editor Python tools.
3. As a TA, I want to specify an **old master Material** and a **new master Material** via path fields, so that I can target a specific upgrade path.
4. As a TA, I want path fields to support manual entry and **fill from Content Browser selection**, so that I can pick materials in the browser and click a button instead of typing paths.
5. As a TA, I want the tool to **pre-fill old/new material paths** when I have one or two Materials selected before opening the window (first selected = old, second = new), so that common two-click workflows are faster.
6. As a TA, I want the default scan folder to be the **currently selected Content Browser folder**, with an **editable path field**, so that I can scope work to a directory without scanning the whole project.
7. As a TA, I want an optional **scan entire project** checkbox, so that I can run large migrations when needed while keeping folder-scoped scan as the safer default.
8. As a TA, I want the tool to find only **Material Instance** assets whose **immediate parent is the old master Material** (not instances parented to other instances), so that instance hierarchies are not broken.
9. As a TA, I want parameter overrides to **migrate by matching parameter names** (scalar, vector, texture, static switch), so that art tuning survives the parent swap when the new master exposes the same names.
10. As a TA, I want parameters that exist on the instance but not on the new master to be **dropped and listed in a report**, so that I know what was lost during migration.
11. As a TA, I want new parameters on the new master to **keep their defaults** after reparenting, so that I am not forced to set every new param during bulk replace.
12. As a TA, I want a **dry-run mode** (checkbox, **on by default**) that scans and reports without modifying assets, so that I can review impact before committing.
13. As a TA, I want a separate **execute** action that performs the actual reparent after I disable dry-run or use an explicit execute control, so that preview and apply are clearly separated.
14. As a TA, I want all modifications in one apply operation wrapped in a **single ScopedEditorTransaction**, so that one Ctrl+Z reverts the entire batch.
15. As a TA, I want an optional **auto-save after apply** checkbox (**off by default**), so that I can verify results before writing packages to disk.
16. As a TA, I want results written to **Output Log** and to **`Saved/MaterialParentReplace/<timestamp>.txt`**, with dry-run reports marked **`[DRY RUN]`**, so that I can archive and share migration summaries.
17. As a TA, I want the Content Browser to **select all modified instances** after a successful apply, so that I can inspect or batch-save them quickly.
18. As a TA, I want validation that old and new inputs are **`UMaterial`** assets (not Material Instances), so that I cannot accidentally point the tool at the wrong asset type.
19. As a developer, I want core replace logic separated from the Qt window where practical, so that scanning, parameter migration, and reporting can be reasoned about independently of UI event handlers.
20. As a developer, I want the tool to depend on **`MaterialEditingLibrary.set_material_instance_parent`** for reparenting, so that behavior matches UE's supported material-instance editing API.
21. As a TA, I want **PackageInstall** to ensure **PySide6** is available on first run, consistent with other TATools scripts in this repo.
22. As a level artist, I want the tool to work on **`MaterialInstanceConstant`** assets in the Content Browser, so that standard authored instances are covered.
23. As a TA, I want the results list in the UI to show per-instance outcomes (path, kept params, discarded params), so that I do not have to read only the log file to understand a run.
24. As a TA, I want a confirmation step before apply when instances will be modified, showing the count of affected instances, so that accidental bulk edits are less likely.

## Implementation Decisions

### Architecture

- New editor Python tool under the existing **TATools** pattern: PySide6 window + `unreal` API + `unreal_stylesheet.setup()`.
- **Menu registration** via a new **PythonMenu** helper (aligned with the reference xiawan project), invoked from **`init_unreal.py`** alongside the existing BlueprintLisp menu. Menu label section: **TATools / 材质**.
- Add missing **`PackageInstall`** module if not present, since existing TATools scripts already import it for PySide6 bootstrap.

### Core replace pipeline

1. **Resolve inputs**: Normalize asset paths; load old and new `UMaterial`; reject invalid types or identical old/new.
2. **Collect candidates**: Query Asset Registry for `MaterialInstanceConstant` / `MaterialInstance` within scan scope (`package_paths` + `recursive_paths`, or full `/Game` when enabled).
3. **Filter**: Load each candidate; keep only those whose `parent` is a `UMaterial` with the same path as the old master.
4. **Preview or apply**:
   - Read current instance parameter values (scalar, vector, texture, static switch) using `MaterialEditingLibrary` getters (same families as `export_materials.py`).
   - On apply: within one `ScopedEditorTransaction`, for each instance call `set_material_instance_parent`, then re-apply values whose names exist on the new master; record kept vs discarded names.
5. **Post-apply**: Optional `EditorAssetLibrary.save_loaded_assets`; `sync_browser_to_objects` for modified instance paths; write timestamped report under `Saved/MaterialParentReplace/`.

### Parameter migration contract

| Parameter kind | Match rule | On mismatch |
| --- | --- | --- |
| Scalar | Name exists on new master | Discard; report |
| Vector | Name exists on new master | Discard; report |
| Texture | Name exists on new master | Discard; report |
| Static switch | Name exists on new master | Discard; report |

No custom rename mapping table in v1.

### UI layout (PySide6)

- Old material row: path field, "从选中填入", "定位"
- New material row: same
- Scan path row: editable folder path (default from selected CB folder), checkbox "全项目扫描"
- Checkboxes: "仅预演（不修改）" default **on**; "执行后自动保存" default **off**
- Actions: **预演**, **执行替换** (execute requires confirmation with instance count)
- Results: list or text area showing per-instance summary; status labels for totals

### Window lifecycle

- Global reference to prevent GC closing the window immediately.
- Re-open focuses existing visible window.
- `main()` calls `parent_external_window_to_slate` after `show()`.

### Dependencies

- **In-repo**: `unreal_stylesheet`, `PackageInstall`, patterns from `FindBadMaterialInstances.py` and parameter APIs from `export_materials.py`.
- **UE APIs**: `AssetRegistry`, `MaterialEditingLibrary`, `EditorAssetLibrary`, `EditorUtilityLibrary`, `ScopedEditorTransaction`.
- **Does not depend on** MaterialBP2DSL / MatLang export for the replace workflow itself.

## Testing Decisions

### What makes a good test

Tests should assert **observable outcomes** of the replace pipeline— which instances are selected for migration, which parameter names are kept vs discarded, and what the report contains— without coupling to Qt widget internals or specific button click handlers.

### Proposed seams (highest first)

1. **Pure parameter-matching seam (highest, no UE required if extracted)**  
   A small pure function that takes `(instance_overrides: dict[str, Any], new_master_param_names: set[str])` and returns `(kept, discarded)`. This encodes the v1 migration contract and can be covered by ordinary unit tests if moved to a helper with no `unreal` import.

2. **Asset-path normalization seam**  
   Functions that convert user input (`/Game/Foo/M`, `/Game/Foo/M.M`) into a canonical object path for `load_asset`. Test with string fixtures only.

3. **Editor integration seam (manual / smoke)**  
   In `MatSwitch.umap` or `MaterailReplace` example content: two master materials, several instances on the old master with known overrides → run dry-run → execute → verify parent, kept params, Undo restores previous parent. This is the authoritative acceptance path because Asset Registry and `MaterialEditingLibrary` require the editor.

4. **UI seam (lowest)**  
   Manual smoke: menu opens window, fields pre-fill from selection, window stays open and is parented to Slate. Do not unit-test Qt layout.

**Prior art**: `export_materials.py` (instance parameter enumeration), `TATools/FindBadMaterialInstances.py` (registry scan + PySide6 window + Slate parenting).

### Suggested acceptance scenarios

- Dry-run on a folder with 0 matching instances → report says 0, no dirty assets.
- Instance with matching scalar/texture names → values preserved after apply.
- Instance with a param only on old master → listed under discarded; apply still succeeds for other params.
- Instance whose parent is another MI (not the old master) → not included.
- Apply 3 instances → one Undo reverts all three.
- Execute without auto-save → assets dirty but not written until user saves.

## Out of Scope

- **MaterialInstanceDynamic** (runtime-only instances).
- **Reparenting instances whose direct parent is another Material Instance** (only direct children of the old `UMaterial`).
- **Creating duplicate instances**; all work is in-place on existing assets.
- **Custom parameter rename / mapping tables** (JSON or UI mapping in v1).
- **Editing master Material graphs** or MatLang DSL import/export as part of replace.
- **Headless commandlet** or CI automation in v1 (editor-interactive tool only).
- **Replacing Material Functions** or other non-instance asset types.

## Further Notes

- Reference implementation patterns live in the xiawan project's `Content/Python` (PySide6, `PackageInstall`, `unreal_stylesheet`, `PythonMenu.py`). This repo already contains copied TATools and stylesheet assets; **`PackageInstall.py` may still need to be added** for imports to succeed.
- Use domain terms consistently: **母材质** = master `UMaterial`; **材质实例** = `MaterialInstanceConstant` in Content Browser.
- Report directory `Saved/MaterialParentReplace/` is intentionally under Saved (gitignored) like other tool outputs.
- If `set_material_instance_parent` clears overrides before re-application, the implementation must **read all overrides before** changing parent, then **write back** matching names— order matters.
