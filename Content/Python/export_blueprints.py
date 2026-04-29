"""
export_blueprints.py
--------------------
将 /Game 下所有 Blueprint 导出为 BlueprintLisp DSL (.bplisp)。

导出路径：
    <ProjectDir>/Saved/BP2DSL/BlueprintLisp/<相对路径>/<GraphName>.bplisp

用法（UE5 Python 控制台 / Output Log）：
    import importlib, sys
    sys.path.insert(0, unreal.Paths.project_content_dir() + "Python")
    import export_blueprints
    importlib.reload(export_blueprints)
    export_blueprints.export_all()

或者只导出特定路径：
    export_blueprints.export_path("/Game/InteractiveGrass")
"""

import unreal


def _export_one(package_path: str) -> bool:
    """
    导出单个 Blueprint 的所有 Graph，返回是否全部成功。
    """
    result = unreal.BlueprintLispPythonBridge.export_all_graphs_to_default_path(package_path)
    ok      = result.success
    msg     = result.message
    warns   = result.warnings

    status = "OK  " if ok else "FAIL"
    print(f"  [{status}] {package_path}")
    print(f"         {msg}")
    for w in warns:
        print(f"         WARN: {w}")
    return ok


def export_path(package_path: str = "/Game") -> None:
    """
    导出指定路径（含子目录）下所有 Blueprint。
    """
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    f  = unreal.ARFilter(
        class_names    = ["Blueprint"],
        recursive_paths = True,
        package_paths  = [package_path],
    )
    assets = ar.get_assets(f)

    total, ok_count = len(assets), 0
    print(f"\n=== BlueprintLisp Export  ({total} blueprints under '{package_path}') ===")

    for asset in assets:
        if _export_one(str(asset.package_name)):
            ok_count += 1

    print(f"\n=== 完成：{ok_count}/{total} 成功 ===")
    print(f"    输出目录：{{ProjectDir}}/Saved/BP2DSL/BlueprintLisp/\n")


def export_all() -> None:
    """导出 /Game 下全部 Blueprint。"""
    export_path("/Game")


def export_selected() -> None:
    """
    导出 Content Browser 中当前选中的 Blueprint 资产。
    在编辑器菜单 BlueprintLisp → Export Selected DSL 触发。
    """
    selected = unreal.EditorUtilityLibrary.get_selected_assets()
    if not selected:
        print("  [BlueprintLisp] 没有选中任何资产，请先在 Content Browser 中选中 Blueprint")
        return

    blueprints = [a for a in selected if a.get_class().get_name() == "Blueprint"]
    if not blueprints:
        print("  [BlueprintLisp] 选中的资产中没有 Blueprint 类型")
        return

    print(f"\n=== BlueprintLisp Export Selected ({len(blueprints)} 个) ===")
    ok_count = 0
    for bp in blueprints:
        package_path = bp.get_path_name().split(".")[0]  # 去掉 .ClassName 后缀
        if _export_one(package_path):
            ok_count += 1

    print(f"\n=== 完成：{ok_count}/{len(blueprints)} 成功 ===")
    print(f"    输出目录：{{ProjectDir}}/Saved/BP2DSL/BlueprintLisp/\n")
