# -*- coding: utf-8 -*-
"""
Core logic for batch-reparenting Material Instances from one master Material
to another. Pure helpers at the top have no unreal dependency.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import unreal

_MEL = unreal.MaterialEditingLibrary

MATERIAL_INSTANCE_CLASS_NAMES = [
    "MaterialInstanceConstant",
    "MaterialInstance",
]

MASTER_MATERIAL_CLASS = "Material"

# Content Browser virtual roots — not valid AssetRegistry package_paths.
_CONTENT_BROWSER_VIRTUAL_ROOTS = frozenset(
    {"All", "Local", "Shared", "Collections", "Developers"}
)


# ── Pure helpers (no unreal) ───────────────────────────────────────────────────


def normalize_scan_folder_path(path: str) -> str:
    """
    Convert a Content Browser folder path to an Asset Registry package path.

    e.g. /All/Game/XW_Art/Foo -> /Game/XW_Art/Foo
    """
    path = (path or "").strip().replace("\\", "/")
    if not path:
        raise ValueError("路径不能为空")
    if not path.startswith("/"):
        raise ValueError(f"路径必须以 / 开头: {path}")

    parts = [part for part in path.split("/") if part]
    if parts and parts[0] in _CONTENT_BROWSER_VIRTUAL_ROOTS:
        parts = parts[1:]

    if not parts:
        return "/Game"

    return normalize_package_path("/" + "/".join(parts))


def normalize_package_path(path: str) -> str:
    """Normalize user input to a package path, e.g. /Game/Foo/M."""
    path = (path or "").strip()
    if not path:
        raise ValueError("路径不能为空")
    if not path.startswith("/"):
        raise ValueError(f"路径必须以 / 开头: {path}")
    if "." in path.rsplit("/", 1)[-1]:
        path = path.rsplit(".", 1)[0]
    return path


def normalize_object_path(path: str) -> str:
    """Normalize user input to an object path, e.g. /Game/Foo/M.M."""
    package = normalize_package_path(path)
    asset_name = package.rsplit("/", 1)[-1]
    return f"{package}.{asset_name}"


def partition_override_names(
    override_names: set[str],
    new_master_names: set[str],
) -> tuple[list[str], list[str]]:
    """Return (kept, discarded) name lists sorted for stable reporting."""
    kept = sorted(override_names & new_master_names)
    discarded = sorted(override_names - new_master_names)
    return kept, discarded


def partition_overrides_by_kind(
    overrides_by_kind: dict[str, dict[str, Any]],
    new_master_names_by_kind: dict[str, set[str]],
) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]]]:
    """
    Split instance overrides into values to re-apply vs discarded param names.

    Returns (kept_values_by_kind, discarded_names_by_kind).
    """
    kept: dict[str, dict[str, Any]] = {}
    discarded: dict[str, list[str]] = {}
    for kind, values in overrides_by_kind.items():
        master_names = new_master_names_by_kind.get(kind, set())
        kept_names, discarded_names = partition_override_names(
            set(values.keys()), master_names
        )
        kept[kind] = {name: values[name] for name in kept_names}
        discarded[kind] = discarded_names
    return kept, discarded


# ── UE asset helpers ───────────────────────────────────────────────────────────


@dataclass
class InstancePreview:
    object_path: str
    kept: dict[str, list[str]] = field(default_factory=dict)
    discarded: dict[str, list[str]] = field(default_factory=dict)
    error: str | None = None


@dataclass
class ReplaceRunResult:
    dry_run: bool
    old_master_path: str
    new_master_path: str
    scan_paths: list[str]
    instances: list[InstancePreview] = field(default_factory=list)
    modified_paths: list[str] = field(default_factory=list)
    error: str | None = None
    scanned_instance_count: int = 0
    parent_mismatch_samples: list[str] = field(default_factory=list)

    @property
    def instance_count(self) -> int:
        return len(self.instances)


def load_master_material(path: str) -> unreal.Material:
    object_path = normalize_object_path(path)
    asset = unreal.EditorAssetLibrary.load_asset(object_path)
    if asset is None:
        raise ValueError(f"无法加载资产: {object_path}")
    if asset.get_class().get_name() != MASTER_MATERIAL_CLASS:
        raise ValueError(
            f"必须是母材质 (Material)，当前类型: {asset.get_class().get_name()} — {object_path}"
        )
    return asset


def package_path_for_asset(asset) -> str:
    """Resolve a loaded asset to its canonical /Game/.../Asset package path."""
    try:
        loaded_path = unreal.EditorAssetLibrary.get_path_name_for_loaded_asset(asset)
        if loaded_path:
            return normalize_package_path(str(loaded_path))
    except Exception:
        pass

    raw = str(asset.get_path_name())
    if ":" in raw:
        raw = raw.split(":", 1)[0]
    if "'" in raw:
        # e.g. /Script/Engine.Material'/Game/Foo/M.M'
        quote_parts = raw.split("'")
        for part in reversed(quote_parts):
            if part.startswith("/"):
                raw = part
                break
    return normalize_package_path(raw)


def _sync_asset_registry(scan_paths: list[str]) -> None:
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    try:
        registry.scan_paths_synchronous(scan_paths, True)
    except TypeError:
        try:
            registry.scan_paths_synchronous(scan_paths)
        except Exception as exc:
            unreal.log_warning(f"[MaterialParentReplace] AssetRegistry scan failed: {exc}")
    except Exception as exc:
        unreal.log_warning(f"[MaterialParentReplace] AssetRegistry scan failed: {exc}")


def validate_masters(old_path: str, new_path: str) -> tuple[unreal.Material, unreal.Material]:
    old_pkg = normalize_package_path(old_path)
    new_pkg = normalize_package_path(new_path)
    if old_pkg == new_pkg:
        raise ValueError("旧母材质与新母材质不能相同")

    old_mat = load_master_material(old_path)
    new_mat = load_master_material(new_path)
    return old_mat, new_mat


def _default_scan_paths() -> list[str]:
    raw_paths: list[str] = []
    try:
        folders = unreal.EditorUtilityLibrary.get_selected_folder_paths()
        if folders:
            raw_paths.append(str(folders[0]))
        else:
            folders = unreal.EditorUtilityLibrary.get_selected_path_view_folder_paths()
            if folders:
                raw_paths.append(str(folders[0]))
            else:
                current = unreal.EditorUtilityLibrary.get_current_content_browser_path()
                if current:
                    raw_paths.append(str(current))
    except Exception:
        pass

    if not raw_paths:
        return ["/Game"]

    normalized: list[str] = []
    for raw in raw_paths:
        try:
            folder = normalize_scan_folder_path(raw)
            if raw != folder:
                unreal.log(
                    f"[MaterialParentReplace] 扫描路径已规范化: {raw} -> {folder}"
                )
            normalized.append(folder)
        except ValueError:
            continue
    return normalized or ["/Game"]


def resolve_scan_paths(folder_text: str, scan_entire_project: bool) -> list[str]:
    if scan_entire_project:
        return ["/Game"]
    text = (folder_text or "").strip()
    if not text:
        return _default_scan_paths()

    normalized: list[str] = []
    for part in text.split(";"):
        part = part.strip()
        if not part:
            continue
        folder = normalize_scan_folder_path(part)
        if part != folder:
            unreal.log(
                f"[MaterialParentReplace] 扫描路径已规范化: {part} -> {folder}"
            )
        normalized.append(folder)
    return normalized or ["/Game"]


def _read_master_param_names(master: unreal.Material) -> dict[str, set[str]]:
    switch_names = _MEL.get_static_switch_parameter_names(master) or []
    if not switch_names and hasattr(
        _MEL, "get_material_instance_static_switch_parameter_names"
    ):
        switch_names = (
            _MEL.get_material_instance_static_switch_parameter_names(master) or []
        )
    return {
        "scalar": {str(n) for n in (_MEL.get_scalar_parameter_names(master) or [])},
        "vector": {str(n) for n in (_MEL.get_vector_parameter_names(master) or [])},
        "texture": {str(n) for n in (_MEL.get_texture_parameter_names(master) or [])},
        "static_switch": {str(n) for n in switch_names},
    }


def _param_name_from_entry(entry) -> str:
    if hasattr(entry, "parameter_info"):
        return str(entry.parameter_info.name)
    return str(entry.get_editor_property("parameter_info").name)


def _param_value_from_entry(entry):
    if hasattr(entry, "parameter_value"):
        return entry.parameter_value
    return entry.get_editor_property("parameter_value")


def _read_overrides_from_editor_array(mi, property_name: str) -> dict[str, Any]:
    try:
        entries = mi.get_editor_property(property_name)
    except Exception:
        return {}

    overrides: dict[str, Any] = {}
    for entry in entries or []:
        try:
            overrides[_param_name_from_entry(entry)] = _param_value_from_entry(entry)
        except Exception:
            continue
    return overrides


def _read_scalar_value(mi, name: str):
    return _MEL.get_material_instance_scalar_parameter_value(mi, name)


def _read_vector_value(mi, name: str):
    return _MEL.get_material_instance_vector_parameter_value(mi, name)


def _read_texture_value(mi, name: str):
    return _MEL.get_material_instance_texture_parameter_value(mi, name)


def _read_static_switch_value(mi, name: str):
    result = _MEL.get_material_instance_static_switch_parameter_value(mi, name)
    if isinstance(result, tuple):
        return result[1] if len(result) > 1 else result[0]
    return result


def _read_overrides_by_getters(
    mi,
    names_fn,
    value_fn,
) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    for name in names_fn(mi) or []:
        key = str(name)
        try:
            overrides[key] = value_fn(mi, key)
        except Exception:
            continue
    return overrides


def _read_kind_overrides(
    mi,
    editor_property: str,
    names_fn,
    value_fn,
) -> dict[str, Any]:
    overrides = _read_overrides_from_editor_array(mi, editor_property)
    if overrides:
        return overrides
    return _read_overrides_by_getters(mi, names_fn, value_fn)


def _read_instance_overrides(mi) -> dict[str, dict[str, Any]]:
    return {
        "scalar": _read_kind_overrides(
            mi,
            "scalar_parameter_values",
            _MEL.get_scalar_parameter_names,
            _read_scalar_value,
        ),
        "vector": _read_kind_overrides(
            mi,
            "vector_parameter_values",
            _MEL.get_vector_parameter_names,
            _read_vector_value,
        ),
        "texture": _read_kind_overrides(
            mi,
            "texture_parameter_values",
            _MEL.get_texture_parameter_names,
            _read_texture_value,
        ),
        "static_switch": _read_kind_overrides(
            mi,
            "static_switch_parameter_values",
            _MEL.get_static_switch_parameter_names,
            _read_static_switch_value,
        ),
    }


def _kept_discarded_report(
    overrides: dict[str, dict[str, Any]],
    new_master_names: dict[str, set[str]],
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    kept_values, discarded = partition_overrides_by_kind(overrides, new_master_names)
    kept_report = {kind: sorted(values.keys()) for kind, values in kept_values.items()}
    return kept_report, discarded


def _apply_kept_overrides(mi, kept_values: dict[str, dict[str, Any]]) -> None:
    for name, value in kept_values.get("scalar", {}).items():
        _MEL.set_material_instance_scalar_parameter_value(mi, name, value)
    for name, value in kept_values.get("vector", {}).items():
        _MEL.set_material_instance_vector_parameter_value(mi, name, value)
    for name, value in kept_values.get("texture", {}).items():
        if value is not None:
            _MEL.set_material_instance_texture_parameter_value(mi, name, value)
    for name, value in kept_values.get("static_switch", {}).items():
        _MEL.set_material_instance_static_switch_parameter_value(mi, name, value)


def _apply_instance_reparent(
    mi,
    new_master: unreal.Material,
    kept_values: dict[str, dict[str, Any]],
) -> None:
    _MEL.set_material_instance_parent(mi, new_master)
    _apply_kept_overrides(mi, kept_values)


def _get_instance_parent_info(mi) -> tuple[str | None, str | None]:
    try:
        parent = mi.get_editor_property("parent")
    except Exception:
        return None, None
    if parent is None:
        return None, None
    try:
        parent_path = package_path_for_asset(parent)
    except Exception:
        parent_path = str(parent.get_path_name())
    return parent.get_class().get_name(), parent_path


def _is_direct_child_of_master(mi, old_master: unreal.Material) -> bool:
    parent_class, parent_path = _get_instance_parent_info(mi)
    if parent_class != MASTER_MATERIAL_CLASS or parent_path is None:
        return False
    try:
        old_pkg = package_path_for_asset(old_master)
    except Exception:
        old_pkg = normalize_package_path(old_master.get_path_name())
    return parent_path == old_pkg


def collect_material_instances(scan_paths: list[str]) -> list[unreal.AssetData]:
    _sync_asset_registry(scan_paths)
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    seen: set[str] = set()
    results: list[unreal.AssetData] = []

    for folder in scan_paths:
        for class_name in MATERIAL_INSTANCE_CLASS_NAMES:
            asset_filter = unreal.ARFilter(
                package_paths=[folder],
                class_names=[class_name],
                recursive_paths=True,
                include_only_on_disk_assets=False,
            )
            for asset_data in registry.get_assets(asset_filter):
                key = str(asset_data.package_name)
                if key not in seen:
                    seen.add(key)
                    results.append(asset_data)

    return results


def find_matching_instances(
    old_master: unreal.Material,
    scan_paths: list[str],
) -> tuple[list[tuple[str, Any]], int, list[str]]:
    """
    Return (matches, scanned_count, parent_mismatch_samples).
    """
    matches: list[tuple[str, Any]] = []
    mismatch_samples: list[str] = []
    scanned = collect_material_instances(scan_paths)
    old_pkg = package_path_for_asset(old_master)

    for asset_data in scanned:
        object_path = f"{asset_data.package_name}.{asset_data.asset_name}"
        try:
            mi = unreal.EditorAssetLibrary.load_asset(object_path)
        except Exception:
            continue
        if mi is None:
            continue
        if _is_direct_child_of_master(mi, old_master):
            matches.append((object_path, mi))
            continue

        parent_class, parent_path = _get_instance_parent_info(mi)
        if parent_path and parent_path != old_pkg and len(mismatch_samples) < 8:
            mismatch_samples.append(
                f"{object_path} -> {parent_class}: {parent_path}"
            )

    return matches, len(scanned), mismatch_samples


def preview_instance(
    mi,
    new_master: unreal.Material,
) -> InstancePreview:
    object_path = mi.get_path_name()
    try:
        overrides = _read_instance_overrides(mi)
        new_names = _read_master_param_names(new_master)
        kept, discarded = _kept_discarded_report(overrides, new_names)
        return InstancePreview(object_path=object_path, kept=kept, discarded=discarded)
    except Exception as exc:
        return InstancePreview(object_path=object_path, error=str(exc))


def run_material_parent_replace(
    old_path: str,
    new_path: str,
    scan_folder_text: str,
    scan_entire_project: bool,
    dry_run: bool,
    auto_save: bool,
) -> ReplaceRunResult:
    try:
        old_master, new_master = validate_masters(old_path, new_path)
    except ValueError as exc:
        return ReplaceRunResult(
            dry_run=dry_run,
            old_master_path=old_path,
            new_master_path=new_path,
            scan_paths=[],
            error=str(exc),
        )

    scan_paths = resolve_scan_paths(scan_folder_text, scan_entire_project)
    new_master_names = _read_master_param_names(new_master)
    old_master_pkg = normalize_package_path(old_master.get_path_name())
    new_master_pkg = normalize_package_path(new_master.get_path_name())

    result = ReplaceRunResult(
        dry_run=dry_run,
        old_master_path=old_master_pkg,
        new_master_path=new_master_pkg,
        scan_paths=scan_paths,
    )

    candidates, scanned_count, mismatch_samples = find_matching_instances(
        old_master, scan_paths
    )
    result.scanned_instance_count = scanned_count
    result.parent_mismatch_samples = mismatch_samples

    unreal.log(
        f"{'[DRY RUN] ' if dry_run else ''}Material Parent Replace: "
        f"scanned {scanned_count} instance(s), matched {len(candidates)} "
        f"under {scan_paths}, old master {old_master_pkg}"
    )
    if not candidates and scanned_count > 0:
        unreal.log_warning(
            "[Material Parent Replace] 未匹配到实例。"
            "请确认旧母材质路径正确，且实例的直接 Parent 仍是该母材质。"
        )
        for sample in mismatch_samples:
            unreal.log_warning(f"  {sample}")

    modified_assets = []

    if dry_run:
        for object_path, mi in candidates:
            result.instances.append(preview_instance(mi, new_master))
        return result

    for object_path, mi in candidates:
        preview = preview_instance(mi, new_master)
        if preview.error:
            result.instances.append(preview)
            continue

        try:
            overrides = _read_instance_overrides(mi)
            kept_values, discarded = partition_overrides_by_kind(
                overrides, new_master_names
            )

            _apply_instance_reparent(mi, new_master, kept_values)

            preview.kept = {k: sorted(v.keys()) for k, v in kept_values.items()}
            preview.discarded = discarded
            result.instances.append(preview)
            result.modified_paths.append(object_path)
            modified_assets.append(mi)
        except Exception as exc:
            preview.error = str(exc)
            result.instances.append(preview)

    if auto_save and modified_assets:
        unreal.EditorAssetLibrary.save_loaded_assets(modified_assets)

    if result.modified_paths:
        try:
            unreal.EditorAssetLibrary.sync_browser_to_objects(
                asset_paths=result.modified_paths
            )
        except Exception as exc:
            unreal.log_warning(
                f"sync_browser_to_objects failed: {exc}"
            )

    return result


# ── Reporting ──────────────────────────────────────────────────────────────────

_KIND_LABELS = {
    "scalar": "标量",
    "vector": "向量",
    "texture": "贴图",
    "static_switch": "静态开关",
}


def format_instance_summary(item: InstancePreview) -> str:
    if item.error:
        return f"{item.object_path}\n  错误: {item.error}"

    lines = [item.object_path]
    for kind, label in _KIND_LABELS.items():
        kept = item.kept.get(kind) or []
        discarded = item.discarded.get(kind) or []
        if kept:
            lines.append(f"  保留{label}: {', '.join(kept)}")
        if discarded:
            lines.append(f"  丢弃{label}: {', '.join(discarded)}")
    if len(lines) == 1:
        lines.append("  (无参数覆盖)")
    return "\n".join(lines)


def format_zero_match_hint(result: ReplaceRunResult) -> str:
    lines = [
        "未找到需要替换的材质实例。",
        f"旧母材质: {result.old_master_path}",
        f"扫描路径: {', '.join(result.scan_paths)}",
    ]
    if result.scanned_instance_count <= 0:
        lines.append("扫描范围内未发现任何 MaterialInstance，请检查扫描路径。")
    else:
        lines.append(
            f"扫描范围内共 {result.scanned_instance_count} 个材质实例，"
            "但没有实例的直接 Parent 等于旧母材质。"
        )
        if result.parent_mismatch_samples:
            lines.append("部分实例当前 Parent：")
            lines.extend(f"  {sample}" for sample in result.parent_mismatch_samples)
        lines.append(
            "若实例已挂在其他母材质（例如上次已成功替换），"
            "需先将 Parent 改回旧母材质，或更换“旧母材质”路径。"
        )
    return "\n".join(lines)


def write_report(result: ReplaceRunResult) -> str:
    report_dir = os.path.join(
        unreal.Paths.project_saved_dir(),
        "MaterialParentReplace",
    )
    os.makedirs(report_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(report_dir, f"{timestamp}.txt")

    prefix = "[DRY RUN] " if result.dry_run else ""
    lines = [
        f"{prefix}Material Parent Replace",
        f"Time: {datetime.now().isoformat(timespec='seconds')}",
        f"Old master: {result.old_master_path}",
        f"New master: {result.new_master_path}",
        f"Scan paths: {', '.join(result.scan_paths)}",
        f"Mode: {'预演' if result.dry_run else '执行'}",
        "",
    ]

    if result.error:
        lines.extend(["ERROR:", result.error, ""])
        _write_and_log(report_path, lines, prefix)
        return report_path

    lines.append(f"Scanned instances: {result.scanned_instance_count}")
    lines.append(f"Matched instances: {result.instance_count}")
    lines.append("")

    if result.instance_count == 0 and not result.error:
        lines.append(format_zero_match_hint(result))
        lines.append("")

    for item in result.instances:
        lines.append(format_instance_summary(item))
        lines.append("")

    if not result.dry_run:
        lines.append(f"Modified: {len(result.modified_paths)}")
        for path in result.modified_paths:
            lines.append(f"  {path}")

    _write_and_log(report_path, lines, prefix)
    return report_path


def _write_and_log(report_path: str, lines: list[str], prefix: str) -> None:
    text = "\n".join(lines)
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(text)
    unreal.log(f"{prefix}Report written: {report_path}")
    unreal.log(text)
