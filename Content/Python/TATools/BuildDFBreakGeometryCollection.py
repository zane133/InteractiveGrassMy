"""
编辑器脚本：从选中 StaticMesh 生成 GeometryCollection 资产。

「静态网格 → 再换 GC」的完整管线分为两段：

1) 编辑器（本脚本）：生成 GC .uasset，并可选用模板蓝图复制出带 Static + GC 组件的 BP，
   并写入 Rest Collection / StaticMesh。
2) 运行时（蓝图或 C++）：在受击/交互等事件里：隐藏 StaticMeshComponent、显示
   GeometryCollectionComponent、SetSimulatePhysics(true)（可加 Field）。Python 不会进包体执行。
"""

import unreal

TARGET_DATAFLOW = "/Game/XW_Art/RES/TAExample/ChaosBreak/GeometryCollections/DF_Break.DF_Break"
GC_NAME_PREFIX = "GC_"
BP_NAME_PREFIX = "BP_Breakable_"

# 默认走共享目录：
#   GC       -> <选中Mesh所属目录>/ChaosBreak/GeometryCollections
#   交换蓝图 -> <选中Mesh所属目录>/ChaosBreak/Blueprint
# 打开后回退到老逻辑：仍放在 TARGET_DATAFLOW 所在目录。
USE_LEGACY_OUTPUT_DIRECTORY = False

# --- 可选：从「静态换 GC」模板蓝图复制，并自动填好 GC + 主 StaticMesh ---
# 模板要求（在编辑器里手工建一次即可）：
#   - 父类 Actor（或你们项目基类）
#   - 子对象：至少一个 StaticMeshComponent + 一个 GeometryCollectionComponent
#   - 默认建议：GC 组件勾选 Hidden in Game，静态mesh可见（碎时再由蓝图反转）
SWAP_BLUEPRINT_TEMPLATE = "/Game/XW_Art/RES/TAExample/ChaosBreak/Blueprint/BP_Breakable_SubClass_Template.BP_Breakable_SubClass_Template"  # 例如 "/Game/XW_Art/.../BP_StaticSwapGC_Template.BP_StaticSwapGC_Template"
ENABLE_DUPLICATE_SWAP_BLUEPRINT = True


def _is_static_mesh(asset):
    return isinstance(asset, unreal.StaticMesh)


def _short_mesh_key(static_mesh):
    mesh_name = unreal.Paths.get_base_filename(static_mesh.get_path_name())
    mesh_name = mesh_name.strip()
    if not mesh_name:
        return "Mesh"

    for prefix in ("SM_", "S_", "SK_", "MESH_", "Mesh_"):
        if mesh_name.startswith(prefix):
            mesh_name = mesh_name[len(prefix):]
            break

    return mesh_name[:48] if len(mesh_name) > 48 else mesh_name


def _build_gc_base_name(primary_static_mesh):
    return f"{GC_NAME_PREFIX}{_short_mesh_key(primary_static_mesh)}"


def _build_bp_base_name(primary_static_mesh):
    return f"{BP_NAME_PREFIX}{_short_mesh_key(primary_static_mesh)}"


def _build_output_folder(*parts):
    clean_parts = [str(part).strip("/") for part in parts if part]
    return "/" + "/".join(clean_parts)


def _strip_asset_name(asset_path):
    if not asset_path:
        return asset_path
    return asset_path.split(".", 1)[0]


def _get_shared_output_root(primary_static_mesh):
    mesh_folder = unreal.Paths.get_path(primary_static_mesh.get_path_name())
    folder_name = unreal.Paths.get_base_filename(mesh_folder)
    if folder_name.lower() in {"mesh", "meshes", "staticmesh", "staticmeshes"}:
        return unreal.Paths.get_path(mesh_folder)
    return mesh_folder


def _resolve_output_folders(primary_static_mesh):
    if USE_LEGACY_OUTPUT_DIRECTORY:
        legacy_folder = unreal.Paths.get_path(TARGET_DATAFLOW)
        return legacy_folder, legacy_folder, "legacy-dataflow-folder"

    shared_root = _get_shared_output_root(primary_static_mesh)
    gc_folder = _build_output_folder(shared_root, "ChaosBreak", "GeometryCollections")
    bp_folder = _build_output_folder(shared_root, "ChaosBreak", "Blueprint")
    return gc_folder, bp_folder, "shared-mesh-folder"


def _ensure_directory_exists(folder_path):
    if not unreal.EditorAssetLibrary.does_directory_exist(folder_path):
        unreal.EditorAssetLibrary.make_directory(folder_path)


def _make_geometry_source(static_mesh):
    source = unreal.GeometryCollectionSource()
    source.source_geometry_object = unreal.SoftObjectPath(static_mesh.get_path_name())
    source.local_transform = unreal.Transform()
    source.source_material = _get_mesh_materials(static_mesh)
    source.add_internal_materials = False
    source.split_components = True     # 是否拆分组件
    source.set_internal_from_material_index = False
    return source


def _get_mesh_materials(static_mesh):
    materials = []
    try:
        static_materials = static_mesh.get_editor_property("static_materials")
        for static_material in static_materials:
            material = static_material.get_editor_property("material_interface")
            if material:
                materials.append(material)
    except Exception:
        pass
    return materials


def _collect_unique_materials(meshes):
    unique = []
    seen_paths = set()
    for mesh in meshes:
        for material in _get_mesh_materials(mesh):
            path = material.get_path_name()
            if path and path not in seen_paths:
                seen_paths.add(path)
                unique.append(material)
    return unique


def _create_geometry_collection_asset(package_path, base_asset_name):
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    unique_package_name, unique_asset_name = asset_tools.create_unique_asset_name(
        f"{package_path}/{base_asset_name}",
        ""
    )

    final_package_path = unreal.Paths.get_path(unique_package_name)
    factory = unreal.GeometryCollectionFactory()
    gc_asset = asset_tools.create_asset(
        unique_asset_name,
        final_package_path,
        unreal.GeometryCollection,
        factory
    )
    return gc_asset, unique_package_name


def _safe_set_editor_property(obj, property_name, value):
    try:
        obj.set_editor_property(property_name, value)
        return True
    except Exception:
        return False


def _disable_component_simulation(component):
    """关闭组件物理模拟（优先调用 API，失败再回退属性写入）。"""
    if not component:
        return False
    try:
        component.set_simulate_physics(False)
        return True
    except Exception:
        return _safe_set_editor_property(component, "simulate_physics", False)


def _get_bp_component_templates(bp):
    """返回蓝图组件模板列表：[(var_name, display_name, component_object), ...]"""
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    handles = subsystem.k2_gather_subobject_data_for_blueprint(bp)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    result = []
    for h in handles:
        data = lib.get_data(h)
        if not lib.is_component(data):
            continue
        comp = lib.get_object_for_blueprint(data, bp)
        if not comp:
            continue
        result.append((lib.get_variable_name(data), lib.get_display_name(data), comp))
    return result


def _find_bp_component_by_type(bp, type_substring):
    """按类名子串查找第一个组件模板（如 StaticMeshComponent、GeometryCollectionComponent）。"""
    for _var_name, _display_name, comp in _get_bp_component_templates(bp):
        comp_class = comp.get_class()
        if comp_class and type_substring in comp_class.get_name():
            return comp
    return None


def _duplicate_swap_blueprint_and_assign(gc_asset, blueprint_folder_path, primary_static_mesh):
    """
    复制 SWAP_BLUEPRINT_TEMPLATE，写入 Rest Collection 与主 StaticMesh，并保存、编译。
    返回新蓝图资产路径，失败或未启用则返回 None。
    """
    if not ENABLE_DUPLICATE_SWAP_BLUEPRINT or not SWAP_BLUEPRINT_TEMPLATE:
        return None
    if not unreal.EditorAssetLibrary.does_asset_exist(SWAP_BLUEPRINT_TEMPLATE):
        unreal.log_warning(
            f"[BuildDFBreakGeometryCollection] SWAP_BLUEPRINT_TEMPLATE 不存在，跳过复制: {SWAP_BLUEPRINT_TEMPLATE}"
        )
        return None

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    base_name = _build_bp_base_name(primary_static_mesh)
    unique_package, unique_name = asset_tools.create_unique_asset_name(f"{blueprint_folder_path}/{base_name}", "")
    dest_path = f"{unique_package}.{unique_name}"

    if not unreal.EditorAssetLibrary.duplicate_asset(SWAP_BLUEPRINT_TEMPLATE, dest_path):
        unreal.log_error(f"[BuildDFBreakGeometryCollection] 复制蓝图失败: {dest_path}")
        return None

    bp = unreal.EditorAssetLibrary.load_asset(dest_path)
    if not bp:
        unreal.log_error(f"[BuildDFBreakGeometryCollection] 加载新蓝图失败: {dest_path}")
        return None

    static_comp = _find_bp_component_by_type(bp, "StaticMeshComponent")
    gc_comp = _find_bp_component_by_type(bp, "GeometryCollectionComponent")

    if static_comp and primary_static_mesh:
        static_comp.set_static_mesh(primary_static_mesh)
        _safe_set_editor_property(static_comp, "b_hidden_in_game", False)

    if gc_comp and gc_asset:
        gc_comp.set_rest_collection(gc_asset, True)
        _safe_set_editor_property(gc_comp, "b_hidden_in_game", True)
        _disable_component_simulation(gc_comp)

    bel = getattr(unreal, "BlueprintEditorLibrary", None)
    if bel and hasattr(bel, "compile_blueprint"):
        try:
            bel.compile_blueprint(bp)
        except Exception as ex:
            unreal.log_warning(
                f"[BuildDFBreakGeometryCollection] compile_blueprint 失败（可忽略，已保存组件修改）: {ex}"
            )

    unreal.EditorAssetLibrary.save_loaded_asset(bp)
    unreal.log(f"[BuildDFBreakGeometryCollection] 已生成静态→GC 交换用蓝图: {dest_path}")
    unreal.log(
        "[BuildDFBreakGeometryCollection] 运行时请在蓝图中：隐藏 Static、显示 GC、"
        "GeometryCollection → SetSimulatePhysics(True)（可加 Field）。"
    )
    return dest_path


def _apply_selected_meshes_as_dataflow_input(gc_asset, selected_meshes):
    variable_names = ["targets", "Targets", "InputMeshes", "Meshes"]
    for variable_name in variable_names:
        if unreal.DataflowBlueprintLibrary.override_dataflow_variable_object_array(
            gc_asset,
            variable_name,
            selected_meshes
        ):
            return variable_name
    return None


def build_from_selected_assets():
    dataflow_asset = unreal.load_asset(TARGET_DATAFLOW)
    if not dataflow_asset:
        unreal.log_error(f"[BuildDFBreakGeometryCollection] Dataflow not found: {TARGET_DATAFLOW}")
        return

    if not isinstance(dataflow_asset, unreal.Dataflow):
        unreal.log_error(f"[BuildDFBreakGeometryCollection] Target is not Dataflow: {TARGET_DATAFLOW}")
        return

    selected_assets = unreal.EditorUtilityLibrary.get_selected_assets()
    selected_meshes = [asset for asset in selected_assets if _is_static_mesh(asset)]
    if not selected_meshes:
        unreal.log_warning("[BuildDFBreakGeometryCollection] No StaticMesh selected in Content Browser.")
        return

    primary_static_mesh = selected_meshes[0]
    gc_folder, blueprint_folder, output_mode = _resolve_output_folders(primary_static_mesh)
    _ensure_directory_exists(gc_folder)
    _ensure_directory_exists(blueprint_folder)

    gc_base_name = _build_gc_base_name(primary_static_mesh)
    gc_asset, gc_package_name = _create_geometry_collection_asset(gc_folder, gc_base_name)
    if not gc_asset:
        unreal.log_error("[BuildDFBreakGeometryCollection] Failed to create GeometryCollection asset.")
        return

    # Core path: always populate GeometryCollection geometry from selected meshes.
    geometry_sources = [_make_geometry_source(mesh) for mesh in selected_meshes]
    gc_asset.set_editor_property("geometry_source", geometry_sources)
    source_materials = _collect_unique_materials(selected_meshes)
    if source_materials:
        gc_asset.set_editor_property("materials", source_materials)

    # Optional path: keep Dataflow linkage for downstream graph-driven rebuild.
    gc_asset.set_dataflow_asset(dataflow_asset)

    applied_variable_name = _apply_selected_meshes_as_dataflow_input(gc_asset, selected_meshes)
    if not applied_variable_name:
        unreal.log_warning(
            "[BuildDFBreakGeometryCollection] Could not find a matching Dataflow object-array variable name."
        )
        unreal.log_warning(
            "[BuildDFBreakGeometryCollection] Tried: targets, Targets, InputMeshes, Meshes."
        )

    regen_ok = unreal.DataflowBlueprintLibrary.regenerate_asset_from_dataflow(gc_asset, True)

    # Re-apply post-regenerate options because Dataflow regeneration can overwrite asset properties.
    _safe_set_editor_property(gc_asset, "enable_clustering", False)
    _safe_set_editor_property(gc_asset, "object_type", unreal.ObjectStateTypeEnum.CHAOS_OBJECT_STATIC)

    # _safe_set_editor_property(gc_asset, "simulate_physics", False) # 貌似没暴露

    unreal.EditorAssetLibrary.save_loaded_asset(gc_asset)

    _duplicate_swap_blueprint_and_assign(gc_asset, blueprint_folder, primary_static_mesh)

    gc_asset_path = _strip_asset_name(gc_package_name)
    unreal.EditorAssetLibrary.sync_browser_to_objects([gc_asset_path])
    unreal.log(f"[BuildDFBreakGeometryCollection] Created: {gc_package_name}")
    unreal.log(f"[BuildDFBreakGeometryCollection] Dataflow source: {TARGET_DATAFLOW}")
    unreal.log(f"[BuildDFBreakGeometryCollection] Output mode: {output_mode}")
    unreal.log(f"[BuildDFBreakGeometryCollection] GC folder: {gc_folder}")
    unreal.log(f"[BuildDFBreakGeometryCollection] Blueprint folder: {blueprint_folder}")
    unreal.log(f"[BuildDFBreakGeometryCollection] Regenerate result: {regen_ok}")
    unreal.log(f"[BuildDFBreakGeometryCollection] Selected mesh count: {len(selected_meshes)}")
    unreal.log(f"[BuildDFBreakGeometryCollection] GeometrySource count: {len(geometry_sources)}")
    unreal.log(f"[BuildDFBreakGeometryCollection] Material count: {len(source_materials)}")
    unreal.log("[BuildDFBreakGeometryCollection] Enable Clustering: False")
    if applied_variable_name:
        unreal.log(f"[BuildDFBreakGeometryCollection] Applied Dataflow variable: {applied_variable_name}")
    for mesh in selected_meshes:
        unreal.log(f"  - {mesh.get_path_name()}")


def main():
    build_from_selected_assets()


if __name__ == "__main__":
    main()
