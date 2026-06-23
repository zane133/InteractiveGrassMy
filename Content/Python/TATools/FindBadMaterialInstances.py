# -*- coding: utf-8 -*-
import unreal
import time

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
_FIND_BAD_MATERIAL_INSTANCES_WINDOW = None

# 要认为是“材质实例类”的资产类型名称
MATERIAL_INSTANCE_CLASS_NAMES = [
    "MaterialInstanceConstant",
    "MaterialInstance",
]

asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()


def get_all_material_instance_assets(folders):
    all_instances = []

    for folder in folders:
        for class_name in MATERIAL_INSTANCE_CLASS_NAMES:
            asset_filter = unreal.ARFilter(
                package_paths=[folder],
                class_names=[class_name],
                recursive_paths=True,
                include_only_on_disk_assets=False,
            )

            assets = asset_registry.get_assets(asset_filter)
            all_instances.extend(assets)

    return all_instances


def is_suspicious_material_instance(asset_data: unreal.AssetData):
    """
    返回 (is_suspicious: bool, reason: str)

    主要判定：
    - 资产加载异常
    - 父材质为 None
    - 访问父材质属性抛异常
    """
    asset_path = f"{asset_data.package_name}.{asset_data.asset_name}"

    # 1) 使用 EditorAssetLibrary 加载资产（与编辑器行为更一致）
    try:
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    except Exception as e:
        reason = f"加载失败: {e}"
        return True, reason

    if asset is None:
        reason = "加载失败: 返回 None（可能是坏引用或资产损坏）"
        return True, reason

    # 2) 通过编辑器属性读取父材质（Python API 中没有 get_parent）
    try:
        parent = asset.get_editor_property("parent")
    except Exception as e:
        reason = f"访问父材质属性失败(parent): {e}"
        return True, reason

    # 3) 父材质为 None
    if parent is None:
        reason = "父材质为 None"
        return True, reason

    # 4) 访问父材质一些基本信息，确认对象还“活着”
    try:
        parent_name = parent.get_name()
        outer = parent.get_outer()
        outer_name = outer.get_name() if outer is not None else "None"
    except Exception as e:
        reason = f"父材质疑似坏引用: {e}"
        return True, reason

    # 一切正常，则认为不是可疑坏实例
    return False, f"父材质正常: {outer_name}/{parent_name}"


def find_bad_material_instances(folders):
    unreal.log("========== Find Bad Material Instances ==========")
    unreal.log(f"Scan folders: {folders}")

    instances = get_all_material_instance_assets(folders)
    unreal.log(f"Total material instances found: {len(instances)}")

    bad_instances = []

    for asset_data in instances:
        is_bad, reason = is_suspicious_material_instance(asset_data)
        asset_path = f"{asset_data.package_name}.{asset_data.asset_name}"

        if is_bad:
            bad_instances.append((asset_data, reason))
            unreal.log(f"[SUSPECT] {asset_path}  (class={asset_data.asset_class})  -> {reason}")

    unreal.log("-------------------------------------------")
    unreal.log(f"Suspicious / bad material instances: {len(bad_instances)}")
    unreal.log("============== Done =======================")

    return instances, bad_instances


class FindBadMaterialInstancesWindow(QWidget):
    def __init__(self):
        super().__init__()
        # self.setWindowTitle("Find Bad Material Instances")
        self.setWindowTitle("查找坏的材质实例")
        self.resize(900, 600)

        self.all_instances = []
        self.bad_instances = []  # [(AssetData, reason), ...]

        main_layout = QVBoxLayout(self)

        # 顶部：输入扫描目录 + 按钮
        top_layout = QHBoxLayout()
        self.folder_edit = QLineEdit(self)
        self.folder_edit.setPlaceholderText(
            "输入要扫描的目录，多个目录用 ; 分隔，例如：/Game;/Game/Characters"
        )
        self.folder_edit.setText("/Game")

        self.scan_button = QPushButton("扫描坏材质实例", self)
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
        self.delete_all_button = QPushButton("删除全部坏的材质实例", self)
        self.delete_all_button.clicked.connect(self.on_delete_all_clicked)
        button_row.addWidget(self.copy_button)
        button_row.addWidget(self.locate_button)
        button_row.addWidget(self.delete_all_button)
        button_row.addStretch(1)

        center_layout.addWidget(self.result_list, 1)
        center_layout.addLayout(button_row)

        # 底部：统计信息
        stats_layout = QHBoxLayout()
        self.total_label = QLabel("All material instances: 0", self)
        self.bad_label = QLabel("Bad / suspicious instances: 0", self)
        self.total_label.setAlignment(Qt.AlignLeft)
        self.bad_label.setAlignment(Qt.AlignLeft)
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.bad_label)
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

        instances, bad_instances = find_bad_material_instances(folders)

        self.all_instances = instances
        self.bad_instances = bad_instances

        self.result_list.clear()
        for asset_data, reason in bad_instances:
            asset_path = f"{asset_data.package_name}.{asset_data.asset_name}"
            item_text = f"{asset_path}  (class={asset_data.asset_class})  -> {reason}"
            item = QListWidgetItem(item_text, self.result_list)
            # 保存真实路径，方便后续复制/跳转
            item.setData(Qt.UserRole, asset_path)

        self.total_label.setText(f"All material instances: {len(instances)}")
        self.bad_label.setText(f"Bad / suspicious instances: {len(bad_instances)}")

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
        unreal.log(f"Copied asset path to clipboard: {asset_path}")

    def on_locate_clicked(self):
        asset_path = self._get_selected_asset_path()
        if not asset_path:
            return
        try:
            unreal.EditorAssetLibrary.sync_browser_to_objects(asset_paths=[asset_path])
        except Exception as e:
            unreal.log_warning(
                f"Failed to locate asset in content browser: {asset_path}, error: {e}"
            )

    def _delete_assets(self, asset_paths):
        if not asset_paths:
            return

        try:
            msg = (
                f"即将删除 {len(asset_paths)} 个“坏材质实例”资产。\n\n"
                "删除操作不可撤销，可能导致仍然引用这些材质实例的资源出现缺失。\n"
                "请确认已经备份工程，是否继续？"
            )
            result = unreal.EditorDialog.show_message(
                "删除坏材质实例",
                msg,
                unreal.AppMsgType.OK_CANCEL,
                unreal.AppReturnType.CANCEL,
            )
            if result != unreal.AppReturnType.OK:
                return
        except Exception as e:
            unreal.log_warning(f"Failed to show delete bad materials dialog, continue deleting: {e}")

        deleted = 0
        failed = 0

        # 分批删除，尽量减小对渲染线程的冲击
        batch_size = 50
        total = len(asset_paths)
        for batch_start in range(0, total, batch_size):
            batch = asset_paths[batch_start : batch_start + batch_size]
            unreal.log(
                f"Deleting bad material instances batch {batch_start} - {batch_start + len(batch) - 1} / {total - 1}"
            )

            for path in batch:
                try:
                    ok = unreal.EditorAssetLibrary.delete_asset(path)
                    if ok:
                        deleted += 1
                    else:
                        failed += 1
                        unreal.log_warning(
                            f"Failed to delete bad material instance asset: {path}"
                        )
                except Exception as e:
                    failed += 1
                    unreal.log_warning(
                        f"Exception while deleting bad material instance {path}: {e}"
                    )

            # 每批删完，尝试触发一次 GC，并稍微等待一会儿
            try:
                unreal.SystemLibrary.collect_garbage()
            except Exception as e:
                unreal.log_warning(f"collect_garbage failed after batch delete: {e}")

            time.sleep(0.1)

        unreal.log(
            f"Delete bad material instances finished. Deleted: {deleted}, Failed: {failed}, Total: {len(asset_paths)}"
        )

        # 删除后重新扫描，刷新列表和统计
        self.on_scan_clicked()

    def on_delete_all_clicked(self):
        if not self.bad_instances:
            return
        asset_paths = [
            f"{asset_data.package_name}.{asset_data.asset_name}"
            for asset_data, reason in self.bad_instances
        ]
        self._delete_assets(asset_paths)

    def on_item_double_clicked(self, item: QListWidgetItem):
        asset_path = item.data(Qt.UserRole)
        if not asset_path:
            return
        try:
            unreal.EditorAssetLibrary.sync_browser_to_objects(asset_paths=[asset_path])
        except Exception as e:
            unreal.log_warning(
                f"Failed to locate asset in content browser: {asset_path}, error: {e}"
            )


def show_window():
    global _FIND_BAD_MATERIAL_INSTANCES_WINDOW
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    unreal_stylesheet.setup()

    # 如果已经有窗口并且还在显示，就激活并返回
    if (
        _FIND_BAD_MATERIAL_INSTANCES_WINDOW is not None
        and _FIND_BAD_MATERIAL_INSTANCES_WINDOW.isVisible()
    ):
        try:
            _FIND_BAD_MATERIAL_INSTANCES_WINDOW.activateWindow()
            _FIND_BAD_MATERIAL_INSTANCES_WINDOW.raise_()
            return _FIND_BAD_MATERIAL_INSTANCES_WINDOW
        except Exception:
            # 如果旧窗口已经失效，则重新创建
            pass

    window = FindBadMaterialInstancesWindow()
    window.show()
    _FIND_BAD_MATERIAL_INSTANCES_WINDOW = window
    return _FIND_BAD_MATERIAL_INSTANCES_WINDOW


def main():
    window = show_window()
    try:
        unreal.parent_external_window_to_slate(int(window.winId()))
    except Exception as e:
        unreal.log_warning(f"parent_external_window_to_slate failed: {e}")


if __name__ == "__main__":
    main()

