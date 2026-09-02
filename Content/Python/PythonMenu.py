# -*- coding: utf-8 -*-
"""
Register TATools editor menu entries (PySide6 utilities under Content/Python/TATools).
"""

from __future__ import annotations

import unreal


def _cmd(module: str, fn: str, *, reload_deps: list[str] | None = None) -> str:
    dep_reload = ""
    for dep in reload_deps or []:
        dep_reload += f"import {dep} as _dep; importlib.reload(_dep); "
    return (
        "import importlib, sys, unreal; "
        f"p = unreal.Paths.project_content_dir() + 'Python'; "
        "p not in sys.path and sys.path.insert(0, p); "
        f"{dep_reload}"
        f"import {module} as _m; importlib.reload(_m); _m.{fn}()"
    )


_TATOOLS_MENU = "LevelEditor.MainMenu.TATools"
_MATERIAL_SECTION = unreal.Name("TAToolsMaterialSection")

_MATERIAL_PARENT_REPLACE = _cmd(
    "TATools.MaterialParentReplace",
    "main",
    reload_deps=["TATools.material_parent_replace_core"],
)

_CUSTOM_NODE_FROM_SHADER = _cmd(
    "TATools.CustomNodeFromShader",
    "main",
    reload_deps=["TATools.custom_node_shader_core"],
)


def _entry(label: str, tooltip: str, cmd: str) -> unreal.ToolMenuEntry:
    entry = unreal.ToolMenuEntry(type=unreal.MultiBlockType.MENU_ENTRY)
    entry.set_label(unreal.Text(label))
    entry.set_tool_tip(unreal.Text(tooltip))
    entry.set_string_command(
        unreal.ToolMenuStringCommandType.PYTHON,
        unreal.Name(""),
        string=cmd,
    )
    return entry


def register_menus() -> None:
    menus = unreal.ToolMenus.get()
    if not menus:
        unreal.log_warning("[TATools] ToolMenus.get() 返回 None")
        return

    main_menu = menus.find_menu("LevelEditor.MainMenu")
    if not main_menu:
        unreal.log_error("[TATools] 未找到 LevelEditor.MainMenu")
        return

    sub_menu = menus.find_menu(_TATOOLS_MENU)
    if not sub_menu:
        sub_menu = main_menu.add_sub_menu(
            main_menu.get_name(),
            unreal.Name("TATools"),
            unreal.Name("TATools"),
            unreal.Text("TATools"),
        )

    if not sub_menu:
        unreal.log_error("[TATools] 创建子菜单失败")
        return

    sub_menu.add_section(_MATERIAL_SECTION, unreal.Text("材质"))

    sub_menu.add_menu_entry(
        _MATERIAL_SECTION,
        _entry(
            "母材质批量替换",
            "将直接挂在旧母材质下的 Material Instance 批量改挂到新母材质，"
            "支持预演、参数迁移与报告。\n"
            "打开前在 Content Browser 选中 1～2 个 Material 可预填旧/新路径。",
            _MATERIAL_PARENT_REPLACE,
        ),
    )

    sub_menu.add_menu_entry(
        _MATERIAL_SECTION,
        _entry(
            "Shader 创建 Custom Node",
            "粘贴 Custom Node HLSL，自动解析 Output Type 和 Inputs，"
            "然后在选中的 Material 中创建 Custom Node。",
            _CUSTOM_NODE_FROM_SHADER,
        ),
    )

    menus.refresh_all_widgets()
    unreal.log("[TATools] 菜单注册成功")
