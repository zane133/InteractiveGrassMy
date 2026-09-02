# -*- coding: utf-8 -*-
"""Launch material-parent replacement outside the live renderer."""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


TOOL_VERSION = "3.2-nullrhi-handshake"
JOB_SCHEMA_VERSION = 1


def _absolute_path(value: str) -> Path:
    return Path(os.path.abspath(str(value)))


def build_job_payload(
    old_path: str,
    new_path: str,
    scan_folder_text: str,
    scan_entire_project: bool,
    *,
    auto_save: bool = True,
) -> dict[str, Any]:
    """Build the serializable contract consumed by the NullRHI worker."""
    return {
        "schema_version": JOB_SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "old_path": old_path.strip(),
        "new_path": new_path.strip(),
        "scan_folder_text": scan_folder_text.strip(),
        "scan_entire_project": bool(scan_entire_project),
        "auto_save": bool(auto_save),
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    os.replace(temporary, path)


def _editor_paths(unreal_module) -> tuple[Path, Path]:
    engine_dir = _absolute_path(unreal_module.Paths.engine_dir())
    binaries = engine_dir / "Binaries" / "Win64"
    return binaries / "UnrealEditor-Cmd.exe", binaries / "UnrealEditor.exe"


def queue_nullrhi_replace(
    old_path: str,
    new_path: str,
    scan_folder_text: str,
    scan_entire_project: bool,
) -> dict[str, str]:
    """
    Queue a detached helper which waits for this editor to exit, runs the
    replacement under NullRHI, then relaunches the normal editor.
    """
    if os.name != "nt":
        raise RuntimeError("安全替换进程目前仅支持 Windows")

    import unreal

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    saved_root = _absolute_path(unreal.Paths.project_saved_dir()) / "MaterialParentReplace"
    job_path = saved_root / "jobs" / f"{run_id}.json"
    result_path = saved_root / "results" / f"{run_id}.json"
    progress_path = saved_root / "progress" / f"{run_id}.json"
    ready_path = saved_root / "ready" / f"{run_id}.json"
    helper_log_path = saved_root / "logs" / f"{run_id}_helper.log"

    python_root = _absolute_path(unreal.Paths.project_content_dir()) / "Python" / "TATools"
    worker_script = python_root / "MaterialParentReplaceWorker.py"
    helper_script = python_root / "RunMaterialParentReplace.ps1"
    project_path = _absolute_path(unreal.Paths.get_project_file_path())
    editor_cmd, editor = _editor_paths(unreal)

    required = [worker_script, helper_script, project_path, editor_cmd, editor]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("安全执行所需文件不存在: " + "; ".join(missing))

    payload = build_job_payload(
        old_path,
        new_path,
        scan_folder_text,
        scan_entire_project,
        auto_save=True,
    )
    payload.update(
        {
            "run_id": run_id,
            "project_path": str(project_path),
            "result_path": str(result_path),
        }
    )
    _write_json(job_path, payload)
    helper_log_path.parent.mkdir(parents=True, exist_ok=True)

    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    powershell = Path(system_root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    if not powershell.is_file():
        raise RuntimeError(f"找不到 PowerShell: {powershell}")

    command = [
        str(powershell),
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-WindowStyle",
        "Hidden",
        "-File",
        str(helper_script),
        "-EditorPid",
        str(os.getpid()),
        "-UnrealEditorCmd",
        str(editor_cmd),
        "-UnrealEditor",
        str(editor),
        "-ProjectPath",
        str(project_path),
        "-WorkerScript",
        str(worker_script),
        "-JobPath",
        str(job_path),
        "-ResultPath",
        str(result_path),
        "-ProgressPath",
        str(progress_path),
        "-ReadyPath",
        str(ready_path),
        "-HelperLogPath",
        str(helper_log_path),
        "-RelaunchEditor",
        "1",
    ]
    # The helper must survive UnrealEditor exiting. DETACHED_PROCESS is the
    # lifecycle boundary; -WindowStyle Hidden suppresses only its console, not
    # the WinForms progress window it creates.
    creation_flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
        subprocess, "CREATE_NEW_PROCESS_GROUP", 0
    )
    subprocess.Popen(
        command,
        close_fds=True,
        creationflags=creation_flags,
    )
    return {
        "run_id": run_id,
        "job_path": str(job_path),
        "result_path": str(result_path),
        "progress_path": str(progress_path),
        "ready_path": str(ready_path),
        "helper_log_path": str(helper_log_path),
    }


def read_helper_ready_state(path: str) -> dict[str, Any] | None:
    ready_path = Path(path)
    if not ready_path.is_file():
        return None
    try:
        with ready_path.open("r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or "success" not in payload:
        return None
    return payload


def show_pending_result_notification() -> None:
    """Show the latest unseen worker result after the normal editor restarts."""
    import unreal

    result_dir = _absolute_path(unreal.Paths.project_saved_dir()) / "MaterialParentReplace" / "results"
    if not result_dir.is_dir():
        return

    for result_path in sorted(result_dir.glob("*.json"), reverse=True):
        try:
            with result_path.open("r", encoding="utf-8-sig") as handle:
                payload = json.load(handle)
        except Exception as exc:
            unreal.log_warning(f"[MaterialParentReplace] 无法读取后台结果 {result_path}: {exc}")
            continue
        if not payload.get("notification_pending"):
            continue

        success = bool(payload.get("success"))
        modified = int(payload.get("modified_count") or 0)
        matched = int(payload.get("matched_count") or 0)
        report_path = str(payload.get("report_path") or "")
        error = str(payload.get("error") or "")
        helper_log = str(payload.get("helper_log_path") or "")
        progress_path = str(payload.get("progress_path") or "")
        ready_path = str(payload.get("ready_path") or "")
        if success:
            message = (
                "NullRHI 安全替换已完成。\n"
                f"匹配: {matched}，已修改并保存: {modified}\n"
                f"报告: {report_path}"
            )
            title = "母材质批量替换完成"
        else:
            message = (
                "NullRHI 安全替换未完成。\n"
                f"错误: {error or '后台进程异常退出'}\n"
                f"日志: {helper_log or result_path}"
            )
            title = "母材质批量替换失败"

        payload["notification_pending"] = False
        try:
            _write_json(result_path, payload)
        except Exception as exc:
            unreal.log_warning(f"[MaterialParentReplace] 无法更新通知状态: {exc}")
        if progress_path:
            try:
                Path(progress_path).unlink(missing_ok=True)
            except Exception as exc:
                unreal.log_warning(f"[MaterialParentReplace] 无法清理进度文件: {exc}")
        if ready_path:
            try:
                Path(ready_path).unlink(missing_ok=True)
            except Exception as exc:
                unreal.log_warning(f"[MaterialParentReplace] 无法清理握手文件: {exc}")
        unreal.EditorDialog.show_message(
            title,
            message,
            unreal.AppMsgType.OK,
        )
        return
