"""
export_materials.py
-------------------
将 Material / MaterialInstance / MaterialFunction 资产导出为可读 DSL 文本。

导出路径（与 Blueprint2DSL 相同根目录）：
    <ProjectDir>/Saved/BP2DSL/Materials/<相对路径>/<AssetName>.matdsl
"""

import os
import unreal

_MEL = unreal.MaterialEditingLibrary


# ── 路径工具 ──────────────────────────────────────────────────────────────────

def _dsl_path(package_path: str) -> str:
    """把 /Game/Foo/Bar 转换成 Saved/BP2DSL/Materials/Foo/Bar.matdsl"""
    # 去掉首个挂载点 /Game/ /MyPlugin/ 等
    parts = package_path.lstrip("/").split("/", 1)
    rel = parts[1] if len(parts) > 1 else parts[0]
    out = os.path.join(
        unreal.Paths.project_saved_dir(),
        "BP2DSL", "Materials",
        rel.replace("/", os.sep),
    ) + ".matdsl"
    return out


def _write(path: str, text: str) -> bool:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return True
    except Exception as e:
        print(f"         WARN: 写文件失败 {path}: {e}")
        return False


# ── DSL 生成 ──────────────────────────────────────────────────────────────────

def _export_material_to_matlang_text(mat: unreal.Material) -> str:
    """
    使用 MaterialBP2DSL 插件，把 UMaterial 直接导出为 MatLang 文本。
    这样就能得到完整的 (expressions ...) + (outputs ...) 结构，
    而不是之前那种只导出 blend_mode / shading_model 的简易摘要。
    """
    try:
        bridge = unreal.MatBP2FPPythonBridge
    except Exception as e:
        print(f"  [MaterialDSL] MatBP2FPPythonBridge not available: {e}")
        return ""

    path = mat.get_path_name()
    try:
        # UFUNCTION ExportMaterialToText → Python 名称 export_material_to_text
        result = bridge.export_material_to_text(path)
    except Exception as e:
        print(f"  [MaterialDSL] ExportMaterialToText failed for {path}: {e}")
        return ""

    # FMatBP2FPPythonResult.bSuccess 在 Python 里暴露为 `success`
    if not getattr(result, "success", False):
        msg = getattr(result, "message", "")
        print(f"  [MaterialDSL] ExportMaterialToText returned failure for {path}: {msg}")
        return ""

    text = getattr(result, "dsl_text", "")
    if not text:
        print(f"  [MaterialDSL] ExportMaterialToText returned empty DSL for {path}")
    return text


def _export_material_function_to_matlang_text(mf) -> str:
    """
    使用 MaterialBP2DSL 插件，把 UMaterialFunction 导出为 MatLang 文本。
    如果插件未实现对应接口，则返回空串并回退到简易描述格式。
    """
    try:
        bridge = unreal.MatBP2FPPythonBridge
    except Exception as e:
        print(f"  [MaterialDSL] MatBP2FPPythonBridge not available for MaterialFunction: {e}")
        return ""

    path = mf.get_path_name()

    # 优先尝试插件里可能提供的专用函数导出接口，
    # 如未找到则退回到与 Material 相同的 export_material_to_text，
    # 再不行就整体失败并回退到旧格式。
    export_fn = getattr(bridge, "export_material_function_to_text", None)
    if export_fn is None:
        export_fn = getattr(bridge, "export_material_to_text", None)

    if export_fn is None:
        print("  [MaterialDSL] No MaterialFunction export API found on MatBP2FPPythonBridge")
        return ""

    try:
        result = export_fn(path)
    except Exception as e:
        print(f"  [MaterialDSL] ExportMaterialFunctionToText failed for {path}: {e}")
        return ""

    if not getattr(result, "success", False):
        msg = getattr(result, "message", "")
        print(f"  [MaterialDSL] ExportMaterialFunctionToText returned failure for {path}: {msg}")
        return ""

    text = getattr(result, "dsl_text", "")
    if not text:
        print(f"  [MaterialDSL] ExportMaterialFunctionToText returned empty DSL for {path}")
    return text


def _lines_material(mat: unreal.Material) -> list:
    """
    对于基础 Material，优先通过 MatBP2FPPythonBridge 导出完整 MatLang。
    如果桥接不可用，就退回到旧的“只导出基本属性+参数”的简易格式。
    """
    dsl = _export_material_to_matlang_text(mat)
    if dsl:
        # 直接返回 MatLang 文本行（保持与示例 .matlang 一致）
        return dsl.splitlines()

    # --- 回退路径：旧实现，仅导出少量属性和参数 ---
    lines = [f'(material "{mat.get_path_name()}"']
    try:
        lines.append(f'  :blend-mode      {mat.get_editor_property("blend_mode")}')
        lines.append(f'  :shading-model   {mat.get_editor_property("shading_model")}')
        lines.append(f'  :two-sided       {mat.get_editor_property("two_sided")}')
    except Exception:
        pass

    # 标量参数
    try:
        for name in _MEL.get_material_instance_scalar_parameter_names(mat) or []:
            ok, val = _MEL.get_material_instance_scalar_parameter_value(mat, name)
            if ok:
                lines.append(f'  (scalar-param "{name}" {val:.6g})')
    except Exception:
        pass

    # 向量参数
    try:
        for name in _MEL.get_material_instance_vector_parameter_names(mat) or []:
            ok, val = _MEL.get_material_instance_vector_parameter_value(mat, name)
            if ok:
                lines.append(f'  (vector-param "{name}" {val.r:.4g} {val.g:.4g} {val.b:.4g} {val.a:.4g})')
    except Exception:
        pass

    # 贴图参数
    try:
        for name in _MEL.get_material_instance_texture_parameter_names(mat) or []:
            ok, val = _MEL.get_material_instance_texture_parameter_value(mat, name)
            if ok and val:
                lines.append(f'  (texture-param "{name}" "{val.get_path_name()}")')
    except Exception:
        pass

    # 静态开关参数
    try:
        for name in _MEL.get_material_instance_static_switch_parameter_names(mat) or []:
            ok, val, _ = _MEL.get_material_instance_static_switch_parameter_value(mat, name)
            if ok:
                lines.append(f'  (static-switch-param "{name}" {str(val).lower()})')
    except Exception:
        pass

    lines.append(")")
    return lines


def _lines_material_instance(mi) -> list:
    lines = [f'(material-instance "{mi.get_path_name()}"']
    parent = mi.get_editor_property("parent")
    if parent:
        lines.append(f'  :parent "{parent.get_path_name()}"')

    # 标量
    try:
        vals = _MEL.get_scalar_parameter_values(mi)
        for pv in (vals or []):
            lines.append(f'  (scalar-param "{pv.parameter_info.name}" {pv.parameter_value:.6g})')
    except Exception:
        pass

    # 向量
    try:
        vals = _MEL.get_vector_parameter_values(mi)
        for pv in (vals or []):
            v = pv.parameter_value
            lines.append(f'  (vector-param "{pv.parameter_info.name}" {v.r:.4g} {v.g:.4g} {v.b:.4g} {v.a:.4g})')
    except Exception:
        pass

    # 贴图
    try:
        vals = _MEL.get_texture_parameter_values(mi)
        for pv in (vals or []):
            tex = pv.parameter_value
            if tex:
                lines.append(f'  (texture-param "{pv.parameter_info.name}" "{tex.get_path_name()}")')
    except Exception:
        pass

    # 静态开关
    try:
        vals = _MEL.get_static_switch_parameter_values(mi)
        for pv in (vals or []):
            lines.append(f'  (static-switch-param "{pv.parameter_info.name}" {str(pv.parameter_value).lower()})')
    except Exception:
        pass

    lines.append(")")
    return lines


def _lines_material_function(mf) -> list:
    """
    对于 MaterialFunction，尝试通过 MatBP2FPPythonBridge 导出完整 MatLang。
    如果桥接不可用或失败，则回退到只导出名称和描述的简易格式。
    """
    dsl = _export_material_function_to_matlang_text(mf)
    if dsl:
        return dsl.splitlines()

    # 回退：仅导出壳信息，保持兼容旧行为
    return [
        f'(material-function "{mf.get_path_name()}"',
        f'  :description "{(mf.get_editor_property("description") or "").strip()}"',
        ")",
    ]


def _generate_dsl(asset) -> str:
    cls = asset.get_class().get_name()
    if cls == "Material":
        lines = _lines_material(asset)
    elif cls in ("MaterialInstanceConstant", "MaterialInstance"):
        lines = _lines_material_instance(asset)
    elif cls == "MaterialFunction":
        lines = _lines_material_function(asset)
    else:
        lines = [f'(unknown-material-asset "{asset.get_path_name()}" :class "{cls}")']
    return "\n".join(lines) + "\n"


# ── 公开 API ──────────────────────────────────────────────────────────────────

_MATERIAL_CLASSES = {
    "Material",
    "MaterialInstanceConstant",
    "MaterialInstance",
    "MaterialFunction",
}


def _export_one_material(asset) -> bool:
    package_path = asset.get_path_name().split(".")[0]
    out_path = _dsl_path(package_path)
    cls = asset.get_class().get_name()
    try:
        dsl = _generate_dsl(asset)
        ok = _write(out_path, dsl)
        status = "OK  " if ok else "FAIL"
        print(f"  [{status}] [{cls}] {package_path}")
        if ok:
            print(f"         → {out_path}")
        return ok
    except Exception as e:
        print(f"  [FAIL] [{cls}] {package_path}")
        print(f"         WARN: {e}")
        return False


def export_selected() -> None:
    """导出 Content Browser 中选中的 Material 相关资产。"""
    selected = unreal.EditorUtilityLibrary.get_selected_assets()
    if not selected:
        print("  [MaterialDSL] 没有选中任何资产")
        return

    targets = [a for a in selected if a.get_class().get_name() in _MATERIAL_CLASSES]
    if not targets:
        print(f"  [MaterialDSL] 选中资产中没有 Material 类型（选中了 "
              f"{[a.get_class().get_name() for a in selected]}）")
        return

    print(f"\n=== MaterialDSL Export Selected ({len(targets)} 个) ===")
    ok_count = sum(_export_one_material(a) for a in targets)
    print(f"\n=== 完成：{ok_count}/{len(targets)} 成功 ===")
    print(f"    输出目录：{{ProjectDir}}/Saved/BP2DSL/Materials/\n")


def export_path(package_path: str = "/Game") -> None:
    """导出指定路径（含子目录）下所有 Material 相关资产。"""
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    f  = unreal.ARFilter(
        class_names     = list(_MATERIAL_CLASSES),
        recursive_paths = True,
        package_paths   = [package_path],
    )
    assets = ar.get_assets(f)

    total = len(assets)
    print(f"\n=== MaterialDSL Export  ({total} 个 under '{package_path}') ===")
    ok_count = 0
    for asset_data in assets:
        obj = asset_data.get_asset()
        if obj and _export_one_material(obj):
            ok_count += 1

    print(f"\n=== 完成：{ok_count}/{total} 成功 ===")
    print(f"    输出目录：{{ProjectDir}}/Saved/BP2DSL/Materials/\n")


def export_all() -> None:
    """导出 /Game 下全部 Material 相关资产。"""
    export_path("/Game")
