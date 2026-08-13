# -*- coding: utf-8 -*-
import unreal

from PackageInstall import install_packages

required_packages = [("PySide6", "PySide6")]
install_packages(required_packages)

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QCheckBox,
    QMessageBox,
    QProgressBar,
)
from PySide6.QtCore import Qt, QTimer

import importlib

import unreal_stylesheet

import TATools.material_parent_replace_core as material_parent_replace_core

importlib.reload(material_parent_replace_core)

from TATools.material_parent_replace_core import (
    MASTER_MATERIAL_CLASS,
    MaterialParentReplaceJob,
    format_instance_summary,
    format_zero_match_hint,
    normalize_object_path,
    normalize_scan_folder_path,
    run_material_parent_replace,
    write_report,
)

_MATERIAL_PARENT_REPLACE_WINDOW = None


def _selected_material_paths() -> list[str]:
    selected = unreal.EditorUtilityLibrary.get_selected_assets()
    paths: list[str] = []
    for asset in selected:
        if asset.get_class().get_name() == MASTER_MATERIAL_CLASS:
            paths.append(asset.get_path_name())
    return paths


def _default_scan_folder() -> str:
    try:
        folders = unreal.EditorUtilityLibrary.get_selected_folder_paths()
        if folders:
            return normalize_scan_folder_path(str(folders[0]))
        folders = unreal.EditorUtilityLibrary.get_selected_path_view_folder_paths()
        if folders:
            return normalize_scan_folder_path(str(folders[0]))
        current = unreal.EditorUtilityLibrary.get_current_content_browser_path()
        if current:
            return normalize_scan_folder_path(str(current))
    except Exception:
        pass
    return "/Game"


def _prefill_from_selection() -> tuple[str, str, str]:
    materials = _selected_material_paths()
    old_path = materials[0] if len(materials) >= 1 else ""
    new_path = materials[1] if len(materials) >= 2 else ""
    return old_path, new_path, _default_scan_folder()


class MaterialParentReplaceWindow(QWidget):
    def __init__(
        self,
        old_path: str = "",
        new_path: str = "",
        scan_folder: str = "/Game",
    ):
        super().__init__()
        self.setWindowTitle("母材质批量替换")
        self.resize(960, 640)

        main_layout = QVBoxLayout(self)

        self.old_edit = QLineEdit(self)
        self.new_edit = QLineEdit(self)
        self.scan_edit = QLineEdit(self)

        self.old_edit.setPlaceholderText("/Game/Path/OldMaster")
        self.new_edit.setPlaceholderText("/Game/Path/NewMaster")
        self.scan_edit.setPlaceholderText("/Game/YourFolder")

        self.old_edit.setText(old_path)
        self.new_edit.setText(new_path)
        self.scan_edit.setText(scan_folder)

        main_layout.addLayout(
            self._material_row("旧母材质：", self.old_edit, self._fill_old_from_selection)
        )
        main_layout.addLayout(
            self._material_row("新母材质：", self.new_edit, self._fill_new_from_selection)
        )

        scan_row = QHBoxLayout()
        scan_row.addWidget(QLabel("扫描路径：", self))
        scan_row.addWidget(self.scan_edit, 1)
        self.scan_all_checkbox = QCheckBox("全项目扫描 (/Game)", self)
        self.scan_all_checkbox.toggled.connect(self._on_scan_all_toggled)
        scan_row.addWidget(self.scan_all_checkbox)
        main_layout.addLayout(scan_row)

        options_row = QHBoxLayout()
        self.dry_run_checkbox = QCheckBox("仅预演（不修改）", self)
        self.dry_run_checkbox.setChecked(True)
        self.auto_save_checkbox = QCheckBox("执行后自动保存", self)
        self.auto_save_checkbox.setChecked(False)
        options_row.addWidget(self.dry_run_checkbox)
        options_row.addWidget(self.auto_save_checkbox)
        options_row.addStretch(1)
        main_layout.addLayout(options_row)

        action_row = QHBoxLayout()
        self.preview_button = QPushButton("预演", self)
        self.execute_button = QPushButton("执行替换", self)
        self.preview_button.clicked.connect(self.on_preview_clicked)
        self.execute_button.clicked.connect(self.on_execute_clicked)
        action_row.addWidget(self.preview_button)
        action_row.addWidget(self.execute_button)
        action_row.addStretch(1)
        main_layout.addLayout(action_row)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        main_layout.addWidget(self.progress_bar)

        self.result_list = QListWidget(self)
        self.result_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        main_layout.addWidget(self.result_list, 1)

        stats_row = QHBoxLayout()
        self.status_label = QLabel("就绪", self)
        self.count_label = QLabel("匹配实例: 0", self)
        stats_row.addWidget(self.status_label)
        stats_row.addStretch(1)
        stats_row.addWidget(self.count_label)
        main_layout.addLayout(stats_row)
        self._replace_job = None

    def _material_row(
        self,
        label_text: str,
        line_edit: QLineEdit,
        fill_callback,
    ) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label_text, self))
        row.addWidget(line_edit, 1)
        fill_button = QPushButton("从选中填入", self)
        fill_button.clicked.connect(fill_callback)
        locate_button = QPushButton("定位", self)
        locate_button.clicked.connect(
            lambda: self._locate_asset(line_edit.text().strip())
        )
        row.addWidget(fill_button)
        row.addWidget(locate_button)
        return row

    def _on_scan_all_toggled(self, checked: bool) -> None:
        self.scan_edit.setEnabled(not checked)

    def _fill_old_from_selection(self) -> None:
        materials = _selected_material_paths()
        if not materials:
            self._set_status("请在 Content Browser 中选中一个 Material 作为旧母材质")
            return
        self.old_edit.setText(materials[0])

    def _fill_new_from_selection(self) -> None:
        materials = _selected_material_paths()
        if not materials:
            self._set_status("请在 Content Browser 中选中一个 Material 作为新母材质")
            return
        target = materials[1] if len(materials) >= 2 else materials[0]
        self.new_edit.setText(target)

    def _locate_asset(self, path: str) -> None:
        if not path:
            return
        try:
            object_path = normalize_object_path(path)
            unreal.EditorAssetLibrary.sync_browser_to_objects(asset_paths=[object_path])
        except Exception as exc:
            unreal.log_warning(f"定位失败: {path} — {exc}")

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def _run(self, dry_run: bool, progress_callback=None) -> None:
        old_path = self.old_edit.text().strip()
        new_path = self.new_edit.text().strip()
        if not old_path or not new_path:
            self._set_status("请填写旧母材质与新母材质路径")
            return

        result = run_material_parent_replace(
            old_path=old_path,
            new_path=new_path,
            scan_folder_text=self.scan_edit.text().strip(),
            scan_entire_project=self.scan_all_checkbox.isChecked(),
            dry_run=dry_run,
            auto_save=self.auto_save_checkbox.isChecked() and not dry_run,
            progress_callback=progress_callback,
        )

        if result.error:
            self._populate_results([])
            self._set_status(f"错误: {result.error}")
            write_report(result)
            return

        self._populate_results(result.instances)
        report_path = write_report(result)

        if result.instance_count == 0:
            self._set_status(format_zero_match_hint(result))
            self.count_label.setText(f"匹配实例: 0 (扫描 {result.scanned_instance_count})")
            return

        if dry_run:
            self._set_status(f"预演完成，报告: {report_path}")
        else:
            self._set_status(
                f"已修改 {len(result.modified_paths)} 个实例，报告: {report_path}"
            )

        self.count_label.setText(f"匹配实例: {result.instance_count}")

    def _populate_results(self, instances) -> None:
        self.result_list.clear()
        for item in instances:
            summary = format_instance_summary(item)
            first_line = summary.split("\n", 1)[0]
            list_item = QListWidgetItem(first_line, self.result_list)
            list_item.setData(Qt.UserRole, item.object_path)
            list_item.setToolTip(summary)
        self.count_label.setText(f"匹配实例: {len(instances)}")

    def on_preview_clicked(self) -> None:
        self._begin_progress("正在扫描匹配实例…")
        self._run(dry_run=True, progress_callback=self._on_replace_progress)

    def on_execute_clicked(self) -> None:
        if self.dry_run_checkbox.isChecked():
            self._begin_progress("正在扫描匹配实例…")
            self._run(dry_run=True, progress_callback=self._on_replace_progress)
            self._set_status("当前为“仅预演”模式；取消勾选后再执行替换，或先点“预演”查看结果")
            return

        old_path = self.old_edit.text().strip()
        new_path = self.new_edit.text().strip()
        if not old_path or not new_path:
            self._set_status("请填写旧母材质与新母材质路径")
            return

        self._begin_progress("正在准备替换…")
        self.preview_button.setEnabled(False)
        self.execute_button.setEnabled(False)
        try:
            self._replace_job = MaterialParentReplaceJob(
                old_path,
                new_path,
                self.scan_edit.text().strip(),
                self.scan_all_checkbox.isChecked(),
                self.auto_save_checkbox.isChecked(),
            )
        except ValueError as exc:
            self.preview_button.setEnabled(True)
            self.execute_button.setEnabled(True)
            self._set_status(f"错误: {exc}")
            return
        QTimer.singleShot(1, self._collect_execute_candidates)

    def _collect_execute_candidates(self) -> None:
        try:
            total = self._replace_job.collect_candidates()
        except Exception as exc:
            self._finish_execute_error(exc)
            return
        if total == 0:
            self._finish_execute_preview()
            return
        self._set_progress("scanning", 0, total)
        QTimer.singleShot(1, self._scan_execute_next)

    def _scan_execute_next(self) -> None:
        try:
            completed, total, object_path = self._replace_job.scan_next()
        except Exception as exc:
            self._finish_execute_error(exc)
            return
        self._set_progress("scanning", completed, total, object_path)
        if self._replace_job.scan_complete:
            if self._replace_job.candidate_count:
                self._set_progress("previewing", 0, self._replace_job.candidate_count)
                QTimer.singleShot(1, self._preview_execute_next)
            else:
                self._finish_execute_preview()
            return
        QTimer.singleShot(1, self._scan_execute_next)

    def _preview_execute_next(self) -> None:
        try:
            completed, total, object_path = self._replace_job.preview_next()
        except Exception as exc:
            self._finish_execute_error(exc)
            return
        self._set_progress("previewing", completed, total, object_path)
        if self._replace_job.preview_complete:
            self._finish_execute_preview()
            return
        QTimer.singleShot(1, self._preview_execute_next)

    def _finish_execute_preview(self) -> None:
        preview = self._replace_job.result
        preview.dry_run = True
        self.preview_button.setEnabled(True)
        self.execute_button.setEnabled(True)
        count = preview.instance_count
        if count == 0:
            self._populate_results([])
            self._set_status(format_zero_match_hint(preview))
            self.count_label.setText(
                f"匹配实例: 0 (扫描 {preview.scanned_instance_count})"
            )
            write_report(preview)
            return

        reply = QMessageBox.question(
            self,
            "确认执行替换",
            f"将修改 {count} 个材质实例的母材质。\n"
            "此操作不支持 Ctrl+Z 撤销，建议先预演确认。\n\n是否继续？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            self._populate_results(preview.instances)
            self.count_label.setText(f"匹配实例: {count}")
            self._set_status("已取消执行（预演结果已列出）")
            write_report(preview)
            return

        self._deferred_execute()

    def _deferred_execute(self) -> None:
        """Apply on the next event-loop tick to avoid D3D12 crashes mid-draw."""
        self._replace_job.result.dry_run = False
        self._set_status("正在执行替换…")
        self._set_progress("replacing", 0, self._replace_job.candidate_count)
        self.preview_button.setEnabled(False)
        self.execute_button.setEnabled(False)
        QTimer.singleShot(1, self._execute_apply_next)

    def _execute_apply_next(self) -> None:
        try:
            completed, total, object_path = self._replace_job.apply_next()
        except Exception as exc:
            self._finish_execute_error(exc)
            return
        self._set_progress("replacing", completed, total, object_path)
        if self._replace_job.apply_complete:
            result = self._replace_job.finish()
            self._populate_results(result.instances)
            report_path = write_report(result)
            self._set_status(
                f"已修改 {len(result.modified_paths)} 个实例，报告: {report_path}"
            )
            self.preview_button.setEnabled(True)
            self.execute_button.setEnabled(True)
            return
        QTimer.singleShot(1, self._execute_apply_next)

    def _finish_execute_error(self, exc: Exception) -> None:
        self.preview_button.setEnabled(True)
        self.execute_button.setEnabled(True)
        self._set_status(f"错误: {exc}")

    def _set_progress(
        self,
        phase: str,
        completed: int,
        total: int,
        object_path: str = "",
    ) -> None:
        self.progress_bar.setRange(0, max(total, 1))
        self.progress_bar.setValue(min(completed, max(total, 1)))
        labels = {"scanning": "扫描", "previewing": "预演", "replacing": "替换"}
        label = labels.get(phase, "处理")
        self.progress_bar.setFormat(f"{label}: %v / %m  (%p%)")
        self._set_status(f"正在{label} {completed} / {total}: {object_path}")
        if phase == "replacing":
            self.count_label.setText(f"匹配实例: {total}")

    def _on_replace_progress(
        self,
        phase: str,
        completed: int,
        total: int,
        object_path: str = "",
    ) -> None:
        self._set_progress(phase, completed, total, object_path)

    def _begin_progress(self, text: str) -> None:
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat(text)
        self._set_status(text)

    def on_item_double_clicked(self, item: QListWidgetItem) -> None:
        asset_path = item.data(Qt.UserRole)
        if not asset_path:
            return
        try:
            unreal.EditorAssetLibrary.sync_browser_to_objects(asset_paths=[asset_path])
        except Exception as exc:
            unreal.log_warning(f"定位失败: {asset_path} — {exc}")


def show_window(
    old_path: str | None = None,
    new_path: str | None = None,
    scan_folder: str | None = None,
):
    global _MATERIAL_PARENT_REPLACE_WINDOW

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    unreal_stylesheet.setup()

    if (
        _MATERIAL_PARENT_REPLACE_WINDOW is not None
        and _MATERIAL_PARENT_REPLACE_WINDOW.isVisible()
    ):
        try:
            _MATERIAL_PARENT_REPLACE_WINDOW.activateWindow()
            _MATERIAL_PARENT_REPLACE_WINDOW.raise_()
            return _MATERIAL_PARENT_REPLACE_WINDOW
        except Exception:
            pass

    if old_path is None and new_path is None and scan_folder is None:
        old_path, new_path, scan_folder = _prefill_from_selection()
    else:
        old_path = old_path or ""
        new_path = new_path or ""
        scan_folder = scan_folder or _default_scan_folder()

    window = MaterialParentReplaceWindow(old_path, new_path, scan_folder)
    window.show()
    _MATERIAL_PARENT_REPLACE_WINDOW = window
    return window


def main():
    window = show_window()
    try:
        unreal.parent_external_window_to_slate(int(window.winId()))
    except Exception as exc:
        unreal.log_warning(f"parent_external_window_to_slate failed: {exc}")


if __name__ == "__main__":
    main()
