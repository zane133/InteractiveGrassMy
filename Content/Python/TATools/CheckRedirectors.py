# -*- coding: utf-8 -*-
import unreal

from PackageInstall import install_packages

# 安装 Qt 依赖
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
)
from PySide6.QtCore import Qt

import unreal_stylesheet

# 保持窗口引用，防止被 GC 回收导致“一闪而过”
_CHECK_REDIRECTORS_WINDOW = None

asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()


def get_all_redirectors(folders):
    """
    在指定目录下查找所有 ObjectRedirector（重定向资产）。
    """
    all_redirectors = []

    for folder in folders:
        asset_filter = unreal.ARFilter(
            package_paths=[folder],
            class_names=["ObjectRedirector"],
            recursive_paths=True,
            include_only_on_disk_assets=False,
        )

        assets = asset_registry.get_assets(asset_filter)
        all_redirectors.extend(assets)

    return all_redirectors


def describe_redirector(asset_data: unreal.AssetData):
    """
    返回 (描述字符串, 目标资产路径或 None)
    """
    asset_path = f"{asset_data.package_name}.{asset_data.asset_name}"

    # 尝试通过 ObjectRedirector 自身的 destination_object 属性解析真实资产
    dest_path = None
    try:
        redirector_obj = unreal.load_object(None, asset_path)
        dest_object = None
        if redirector_obj is not None:
            # 在 C++ 中是 ObjectRedirector::DestinationObject
            try:
                dest_object = redirector_obj.get_editor_property("destination_object")
            except Exception:
                # 某些版本上属性名可能不同，这里做一次兜底，避免刷 Warning
                dest_object = None
        if dest_object:
            dest_outer = dest_object.get_outer()
            if dest_outer:
                dest_pkg_name = dest_outer.get_name()
                dest_asset_name = dest_object.get_name()
                dest_path = f"{dest_pkg_name}.{dest_asset_name}"
            else:
                dest_path = dest_object.get_name()
    except Exception as e:
        # 解析失败不影响后续流程，只在日志里打一条 Debug 级别日志即可
        unreal.log_warning(f"Failed to resolve redirector target for {asset_path}: {e}")

    if dest_path:
        desc = f"{asset_path}  ->  {dest_path}"
    else:
        desc = f"{asset_path}  ->  <未能解析目标>"

    return desc, dest_path


def find_redirectors(folders):
    unreal.log("========== Check Redirectors ==========")
    unreal.log(f"Scan folders: {folders}")

    redirectors = get_all_redirectors(folders)
    unreal.log(f"Total redirectors found: {len(redirectors)}")

    results = []
    for a in redirectors:
        desc, dest = describe_redirector(a)
        unreal.log(desc)
        results.append((a, desc, dest))

    unreal.log("============== Done =======================")
    return redirectors, results


class CheckRedirectorsWindow(QWidget):
    def __init__(self):
        super().__init__()
        # self.setWindowTitle("Check Redirectors")
        self.setWindowTitle("检查 Redirector")
        self.resize(900, 600)

        self.all_redirectors = []
        self.redirector_results = []  # [(AssetData, desc, dest_path), ...]

        main_layout = QVBoxLayout(self)

        # 顶部：输入扫描目录 + 按钮
        top_layout = QHBoxLayout()
        self.folder_edit = QLineEdit(self)
        self.folder_edit.setPlaceholderText(
            "输入要扫描的目录，多个目录用 ; 分隔，例如：/Game;/Game/Characters"
        )
        self.folder_edit.setText("/Game")

        self.scan_button = QPushButton("扫描 Redirector", self)
        self.scan_button.clicked.connect(self.on_scan_clicked)

        top_layout.addWidget(QLabel("扫描目录：", self))
        top_layout.addWidget(self.folder_edit, 1)
        top_layout.addWidget(self.scan_button)

        # 中间：结果列表 + 操作按钮
        center_layout = QVBoxLayout()

        self.result_list = QListWidget(self)
        # 双击跳转到内容浏览器
        self.result_list.itemDoubleClicked.connect(self.on_item_double_clicked)

        button_row = QHBoxLayout()
        self.copy_button = QPushButton("复制路径", self)
        self.copy_button.clicked.connect(self.on_copy_clicked)
        self.locate_button = QPushButton("在内容浏览器中定位", self)
        self.locate_button.clicked.connect(self.on_locate_clicked)
        self.delete_all_button = QPushButton("修复全部 Redirector", self)
        self.delete_all_button.clicked.connect(self.on_fix_all_clicked)
        button_row.addWidget(self.copy_button)
        button_row.addWidget(self.locate_button)
        button_row.addWidget(self.delete_all_button)
        button_row.addStretch(1)

        center_layout.addWidget(self.result_list, 1)
        center_layout.addLayout(button_row)

        # 底部：统计信息
        stats_layout = QHBoxLayout()
        self.total_label = QLabel("Redirectors: 0", self)
        self.total_label.setAlignment(Qt.AlignLeft)
        stats_layout.addWidget(self.total_label)
        stats_layout.addStretch(1)

        main_layout.addLayout(top_layout)
        main_layout.addLayout(center_layout, 1)
        main_layout.addLayout(stats_layout)

    def on_scan_clicked(self):
        text = self.folder_edit.text().strip()
        if not text:
            return

        # 支持多个目录，用 ; 分隔
        folders = [p.strip() for p in text.split(";") if p.strip()]
        if not folders:
            return

        redirectors, results = find_redirectors(folders)

        self.all_redirectors = redirectors
        self.redirector_results = results

        self.result_list.clear()
        for asset_data, desc, dest_path in results:
            item = QListWidgetItem(desc, self.result_list)
            # 保存真实路径，方便后续复制/跳转
            asset_path = f"{asset_data.package_name}.{asset_data.asset_name}"
            item.setData(Qt.UserRole, asset_path)

        self.total_label.setText(f"Redirectors: {len(redirectors)}")

    def _get_selected_asset_path(self):
        item = self.result_list.currentItem()
        if item is None:
            return None
        asset_path = item.data(Qt.UserRole)
        return asset_path

    def on_copy_clicked(self):
        asset_path = self._get_selected_asset_path()
        if not asset_path:
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(asset_path)
        unreal.log(f"Copied redirector path to clipboard: {asset_path}")

    def on_locate_clicked(self):
        asset_path = self._get_selected_asset_path()
        if not asset_path:
            return
        try:
            unreal.EditorAssetLibrary.sync_browser_to_objects(asset_paths=[asset_path])
        except Exception as e:
            unreal.log_warning(
                f"Failed to locate redirector in content browser: {asset_path}, error: {e}"
            )

    def on_fix_all_clicked(self):
        # 没有扫描结果时直接返回
        if not self.redirector_results:
            return

        # 弹出一次确认对话框，避免误操作
        try:
            result = unreal.EditorDialog.show_message(
                "修复全部 Redirector",
                f"当前列表中共有 {len(self.redirector_results)} 个 Redirector。\n\n"
                "将尝试调用 AssetTools.fixup_redirectors 来修复它们并更新引用。\n"
                "该操作相当于内容浏览器中的“Fix Up Redirectors in Folder…”，建议在执行前备份工程。",
                unreal.AppMsgType.OK_CANCEL,
                unreal.AppReturnType.CANCEL,
            )
            if result != unreal.AppReturnType.OK:
                return
        except Exception as e:
            # 如果对话框调用失败，则在日志中提示，但仍然继续执行修复逻辑
            unreal.log_warning(f"Failed to show confirmation dialog, continue fixing: {e}")

        redirector_objects = []
        for asset_data, desc, dest_path in list(self.redirector_results):
            asset_path = f"{asset_data.package_name}.{asset_data.asset_name}"
            try:
                obj = unreal.load_object(None, asset_path)
                if obj is not None:
                    redirector_objects.append(obj)
                else:
                    unreal.log_warning(f"Failed to load redirector object: {asset_path}")
            except Exception as e:
                unreal.log_warning(f"Exception while loading redirector {asset_path}: {e}")

        if not redirector_objects:
            unreal.log_warning("No redirector objects loaded, aborting fixup.")
            return

        try:
            asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
            # 某些版本的 API 可能返回 bool，也可能返回修复后的对象数组，这里统一记录日志即可
            result = asset_tools.fixup_redirectors(redirector_objects)
            unreal.log(f"Fixup redirectors finished. Result: {result}, Count: {len(redirector_objects)}")
        except Exception as e:
            unreal.log_warning(f"Exception while fixing redirectors: {e}")

        # 修复完成后，重新扫描一次以刷新界面
        self.on_scan_clicked()

        # 如果还有剩余的 redirector，允许用户选择直接删除这些“无法修复”的 redirector
        if not self.redirector_results:
            return

        try:
            remain_result = unreal.EditorDialog.show_message(
                "删除剩余 Redirector",
                f"修复完成后仍然剩余 {len(self.redirector_results)} 个 Redirector。\n\n"
                "这些通常是无法自动修复的 Redirector，是否直接删除它们？\n"
                "删除将移除 Redirector 资源本身，可能导致仍然引用旧路径的地方出现缺失，请确保已备份工程。",
                unreal.AppMsgType.OK_CANCEL,
                unreal.AppReturnType.CANCEL,
            )
            if remain_result != unreal.AppReturnType.OK:
                return
        except Exception as e:
            unreal.log_warning(f"Failed to show delete remaining dialog, continue deleting: {e}")

        deleted_count = 0
        failed_count = 0

        for asset_data, desc, dest_path in list(self.redirector_results):
            asset_path = f"{asset_data.package_name}.{asset_data.asset_name}"
            try:
                ok = unreal.EditorAssetLibrary.delete_asset(asset_path)
                if ok:
                    deleted_count += 1
                else:
                    failed_count += 1
                    unreal.log_warning(f"Failed to delete redirector asset: {asset_path}")
            except Exception as e:
                failed_count += 1
                unreal.log_warning(f"Exception while deleting remaining redirector {asset_path}: {e}")

        unreal.log(
            f"Delete remaining redirectors finished. Deleted: {deleted_count}, Failed: {failed_count}, Total: {len(self.redirector_results)}"
        )

        # 最后再刷新一次
        self.on_scan_clicked()

    def on_item_double_clicked(self, item: QListWidgetItem):
        asset_path = item.data(Qt.UserRole)
        if not asset_path:
            return
        try:
            unreal.EditorAssetLibrary.sync_browser_to_objects(asset_paths=[asset_path])
        except Exception as e:
            unreal.log_warning(
                f"Failed to locate redirector in content browser: {asset_path}, error: {e}"
            )


def show_window():
    global _CHECK_REDIRECTORS_WINDOW
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    unreal_stylesheet.setup()

    # 如果已经有窗口并且还在显示，就激活并返回
    if _CHECK_REDIRECTORS_WINDOW is not None and _CHECK_REDIRECTORS_WINDOW.isVisible():
        try:
            _CHECK_REDIRECTORS_WINDOW.activateWindow()
            _CHECK_REDIRECTORS_WINDOW.raise_()
            return _CHECK_REDIRECTORS_WINDOW
        except Exception:
            # 如果旧窗口已经失效，则重新创建
            pass

    window = CheckRedirectorsWindow()
    window.show()
    _CHECK_REDIRECTORS_WINDOW = window
    return _CHECK_REDIRECTORS_WINDOW


def main():
    window = show_window()
    try:
        unreal.parent_external_window_to_slate(int(window.winId()))
    except Exception as e:
        unreal.log_warning(f"parent_external_window_to_slate failed: {e}")


if __name__ == "__main__":
    main()

