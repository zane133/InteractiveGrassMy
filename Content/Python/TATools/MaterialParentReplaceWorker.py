# -*- coding: utf-8 -*-
"""UnrealEditor-Cmd entry point for NullRHI material replacement."""

from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

import unreal


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    os.replace(temporary, path)


def _write_progress(
    phase: str,
    completed: int = 0,
    total: int = 0,
    object_path: str = "",
    message: str = "",
) -> None:
    progress_path_text = os.environ.get("MPR_PROGRESS_PATH", "")
    if not progress_path_text:
        return
    _write_json(
        Path(progress_path_text),
        {
            "phase": phase,
            "completed": int(completed),
            "total": int(total),
            "object_path": object_path,
            "message": message,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        },
    )


def main() -> None:
    job_path_text = os.environ.get("MPR_JOB_PATH", "")
    result_path_text = os.environ.get("MPR_RESULT_PATH", "")
    helper_log_path = os.environ.get("MPR_HELPER_LOG_PATH", "")
    progress_path_text = os.environ.get("MPR_PROGRESS_PATH", "")
    ready_path_text = os.environ.get("MPR_READY_PATH", "")
    if not job_path_text or not result_path_text:
        raise RuntimeError("MPR_JOB_PATH / MPR_RESULT_PATH 未设置")

    job_path = Path(job_path_text)
    result_path = Path(result_path_text)
    with job_path.open("r", encoding="utf-8-sig") as handle:
        job = json.load(handle)
    if int(job.get("schema_version") or 0) != 1:
        raise RuntimeError(f"不支持的任务格式: {job.get('schema_version')}")

    content_python = os.path.abspath(str(unreal.Paths.project_content_dir())) + os.sep + "Python"
    if content_python not in sys.path:
        sys.path.insert(0, content_python)

    from TATools.material_parent_replace_core import (
        run_material_parent_replace,
        write_report,
    )

    unreal.log(
        "[MaterialParentReplace] NullRHI worker started: "
        f"run_id={job.get('run_id')}, auto_save={bool(job.get('auto_save', True))}"
    )
    _write_progress("starting", message="正在初始化资产注册表…")
    result = run_material_parent_replace(
        old_path=job["old_path"],
        new_path=job["new_path"],
        scan_folder_text=job.get("scan_folder_text", ""),
        scan_entire_project=bool(job.get("scan_entire_project")),
        dry_run=False,
        auto_save=bool(job.get("auto_save", True)),
        progress_callback=lambda phase, completed, total, object_path: _write_progress(
            phase,
            completed,
            total,
            object_path,
        ),
    )
    _write_progress(
        "reporting",
        len(result.modified_paths),
        result.instance_count,
        message="正在生成执行报告…",
    )
    report_path = write_report(result)
    item_errors = [item.error for item in result.instances if item.error]
    success = (
        result.error is None
        and not item_errors
        and result.instance_count > 0
        and len(result.modified_paths) == result.instance_count
    )
    error = result.error or ("; ".join(item_errors) if item_errors else "")
    if not error and result.instance_count == 0:
        error = "后台执行时未找到仍挂在旧母材质下的实例"
    payload = {
        "run_id": job.get("run_id"),
        "completed_at": datetime.now().isoformat(timespec="seconds"),
        "success": success,
        "matched_count": result.instance_count,
        "modified_count": len(result.modified_paths),
        "modified_paths": result.modified_paths,
        "report_path": report_path,
        "helper_log_path": helper_log_path,
        "progress_path": progress_path_text,
        "ready_path": ready_path_text,
        "error": error,
        "notification_pending": True,
    }
    _write_json(result_path, payload)
    if not success:
        raise RuntimeError(payload["error"] or "部分材质实例未能替换")
    unreal.log(
        "[MaterialParentReplace] NullRHI worker completed: "
        f"modified={len(result.modified_paths)}"
    )
    _write_progress(
        "completed",
        len(result.modified_paths),
        result.instance_count,
        message="替换与保存已完成",
    )


try:
    main()
except Exception:
    try:
        _write_progress("failed", message="后台替换失败，请查看日志")
    except Exception:
        pass
    unreal.log_error("[MaterialParentReplace] NullRHI worker failed:\n" + traceback.format_exc())
    raise
