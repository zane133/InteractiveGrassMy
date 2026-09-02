"""
init_unreal.py
--------------
UE5 编辑器启动时自动执行。
在顶部菜单栏注册：
  BlueprintLisp — Blueprint / Material DSL 导出
  TATools — TA 工具（材质批量替换等）
"""

import unreal
import sys

_content_python = unreal.Paths.project_content_dir() + "Python"
if _content_python not in sys.path:
    sys.path.insert(0, _content_python)

# ── 命令字符串 ────────────────────────────────────────────────────────────────

def _cmd(module: str, fn: str) -> str:
    return (
        "import importlib, sys, unreal; "
        f"p = unreal.Paths.project_content_dir() + 'Python'; "
        "p not in sys.path and sys.path.insert(0, p); "
        f"import {module} as _m; importlib.reload(_m); _m.{fn}()"
    )

_BP_SELECTED  = _cmd("export_blueprints", "export_selected")
_BP_ALL       = _cmd("export_blueprints", "export_all")
_MAT_SELECTED = _cmd("export_materials",  "export_selected")
_MAT_ALL      = _cmd("export_materials",  "export_all")


# ── 菜单注册 ──────────────────────────────────────────────────────────────────

def _register_blueprint_lisp_menus():
    menus = unreal.ToolMenus.get()
    if not menus:
        unreal.log_warning("[BlueprintLisp] ToolMenus.get() 返回 None")
        return

    main_menu = menus.find_menu("LevelEditor.MainMenu")
    if not main_menu:
        unreal.log_error("[BlueprintLisp] 未找到 LevelEditor.MainMenu")
        return

    sub_menu = menus.find_menu("LevelEditor.MainMenu.BlueprintLisp")
    if not sub_menu:
        sub_menu = main_menu.add_sub_menu(
            main_menu.get_name(),
            unreal.Name("BlueprintLisp"),
            unreal.Name("BlueprintLisp"),
            unreal.Text("BlueprintLisp"),
        )

    if not sub_menu:
        unreal.log_error("[BlueprintLisp] 创建子菜单失败")
        return

    def _entry(label: str, tooltip: str, cmd: str) -> unreal.ToolMenuEntry:
        e = unreal.ToolMenuEntry(type=unreal.MultiBlockType.MENU_ENTRY)
        e.set_label(unreal.Text(label))
        e.set_tool_tip(unreal.Text(tooltip))
        e.set_string_command(unreal.ToolMenuStringCommandType.PYTHON, unreal.Name(""), string=cmd)
        return e

    sec_bp = unreal.Name("BPDSLSection")
    sub_menu.add_section(sec_bp, unreal.Text("Blueprint DSL"))

    sub_menu.add_menu_entry(sec_bp, _entry(
        "Export Selected DSL（导出选中蓝图）",
        "导出 Content Browser 中选中的 Blueprint 为 BlueprintLisp DSL\n"
        "输出到 Saved/BP2DSL/BlueprintLisp/",
        _BP_SELECTED,
    ))
    sub_menu.add_menu_entry(sec_bp, _entry(
        "Export All DSL（导出全部蓝图）",
        "导出 /Game 下所有 Blueprint 为 BlueprintLisp DSL\n"
        "输出到 Saved/BP2DSL/BlueprintLisp/",
        _BP_ALL,
    ))

    sec_mat = unreal.Name("MatDSLSection")
    sub_menu.add_section(sec_mat, unreal.Text("Material DSL"))

    sub_menu.add_menu_entry(sec_mat, _entry(
        "Export Selected Material（导出选中材质）",
        "导出选中的 Material / MaterialInstance / MaterialFunction\n"
        "输出到 Saved/BP2DSL/Materials/",
        _MAT_SELECTED,
    ))
    sub_menu.add_menu_entry(sec_mat, _entry(
        "Export All Materials（导出全部材质）",
        "导出 /Game 下所有材质资产\n"
        "输出到 Saved/BP2DSL/Materials/",
        _MAT_ALL,
    ))


def _register_tatools_menus():
    import PythonMenu as python_menu
    python_menu.register_menus()


def _do_register():
    _register_blueprint_lisp_menus()
    _register_tatools_menus()
    unreal.ToolMenus.get().refresh_all_widgets()
    unreal.log("[init_unreal] BlueprintLisp + TATools 菜单注册成功")
    try:
        from TATools.material_parent_replace_external import (
            show_pending_result_notification,
        )
        show_pending_result_notification()
    except Exception as exc:
        unreal.log_warning(f"[MaterialParentReplace] 后台结果通知失败: {exc}")


# ── 延迟到 Slate 完全初始化后执行，只跑一次 ──────────────────────────────────
_tick_handle = None

def _deferred_register(delta_time: float):
    global _tick_handle
    if _tick_handle is not None:
        unreal.unregister_slate_pre_tick_callback(_tick_handle)
        _tick_handle = None
    try:
        _do_register()
    except Exception as e:
        unreal.log_error(f"[BlueprintLisp] 注册异常: {e}")

_tick_handle = unreal.register_slate_pre_tick_callback(_deferred_register)
unreal.log("[BlueprintLisp] init_unreal.py 已加载，等待 Slate 初始化...")
