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
_FIND_UNUSED_MATERIALS_WINDOW = None


# 要认为是“材质类”的资产类型名称
MATERIAL_CLASS_NAMES = [
    "Material",
    # "MaterialInstanceConstant",
    # "MaterialInstanceDynamic",  # 一般是运行时创建，通常不在 Content Browser 里，可按需打开
]

asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()


def get_all_material_assets(folders):
    all_materials = []

    for folder in folders:
        for class_name in MATERIAL_CLASS_NAMES:
            asset_filter = unreal.ARFilter(
                package_paths=[folder],
                class_names=[class_name],
                recursive_paths=True,
                include_only_on_disk_assets=False,
            )

            assets = asset_registry.get_assets(asset_filter)
            all_materials.extend(assets)

    return all_materials


def get_hard_referencers(package_name: str):
    """
    只查硬引用（Hard References），忽略软引用和管理引用。
    package_name 形如 '/Game/Path/AssetName'
    """
    dep_options = unreal.AssetRegistryDependencyOptions(
        include_soft_package_references=False,
        include_hard_package_references=True,
        include_searchable_names=False,
        include_soft_management_references=False,
        include_hard_management_references=False,
    )

    referencers = asset_registry.get_referencers(package_name, dep_options)
    return referencers


def find_unused_materials(folders):
    unreal.log("========== Find Unused Materials ==========")
    unreal.log(f"Scan folders: {folders}")

    materials = get_all_material_assets(folders)
    unreal.log(f"Total materials found: {len(materials)}")

    unused_materials = []

    for asset_data in materials:
        package_name = asset_data.package_name  # '/Game/xxx'
        referencers = get_hard_referencers(package_name)

        # 没有任何硬引用，认为是“疑似未使用材质”
        if not referencers:
            unused_materials.append(asset_data)

    unreal.log("-------------------------------------------")
    unreal.log(f"Unused materials (no hard referencers): {len(unused_materials)}")

    for a in unused_materials:
        asset_path = f"{a.package_name}.{a.asset_name}"
        unreal.log(f"UNUSED: {asset_path}  (class={a.asset_class})")

    unreal.log("============== Done =======================")

    return materials, unused_materials


class FindUnusedMaterialsWindow(QWidget):
    def __init__(self):
        super().__init__()
        # self.setWindowTitle("Find Unused Materials")
        self.setWindowTitle("查找未引用的材质")
        self.resize(800, 600)

        self.all_materials = []
        self.unused_materials = []

        main_layout = QVBoxLayout(self)

        # 顶部：输入扫描目录 + 按钮
        top_layout = QHBoxLayout()
        self.folder_edit = QLineEdit(self)
        self.folder_edit.setPlaceholderText("输入要扫描的目录，多个目录用 ; 分隔，例如：/Game;/Game/Characters")
        self.folder_edit.setText("/Game")

        self.scan_button = QPushButton("扫描未引用材质", self)
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
        button_row.addWidget(self.copy_button)
        button_row.addWidget(self.locate_button)
        button_row.addStretch(1)

        center_layout.addWidget(self.result_list, 1)
        center_layout.addLayout(button_row)

        # 底部：统计信息
        stats_layout = QHBoxLayout()
        self.total_label = QLabel("All materials: 0", self)
        self.unused_label = QLabel("Unused materials: 0", self)
        self.total_label.setAlignment(Qt.AlignLeft)
        self.unused_label.setAlignment(Qt.AlignLeft)
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.unused_label)
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

        materials, unused_materials = find_unused_materials(folders)

        self.all_materials = materials
        self.unused_materials = unused_materials

        self.result_list.clear()
        for a in unused_materials:
            asset_path = f"{a.package_name}.{a.asset_name}"
            item_text = f"{asset_path}  (class={a.asset_class})"
            item = QListWidgetItem(item_text, self.result_list)
            # 保存真实路径，方便后续复制/跳转
            item.setData(Qt.UserRole, asset_path)

        self.total_label.setText(f"All materials: {len(materials)}")
        self.unused_label.setText(f"Unused materials: {len(unused_materials)}")

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
            # UE5.6 中 SyncBrowserToObjects 接收资产路径字符串数组参数 asset_paths
            unreal.EditorAssetLibrary.sync_browser_to_objects(asset_paths=[asset_path])
        except Exception as e:
            unreal.log_warning(f"Failed to locate asset in content browser: {asset_path}, error: {e}")

    def on_item_double_clicked(self, item: QListWidgetItem):
        asset_path = item.data(Qt.UserRole)
        if not asset_path:
            return
        try:
            unreal.EditorAssetLibrary.sync_browser_to_objects(asset_paths=[asset_path])
        except Exception as e:
            unreal.log_warning(f"Failed to locate asset in content browser: {asset_path}, error: {e}")


def show_window():
    global _FIND_UNUSED_MATERIALS_WINDOW
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    unreal_stylesheet.setup()

    # 如果已经有窗口并且还在显示，就激活并返回
    if _FIND_UNUSED_MATERIALS_WINDOW is not None and _FIND_UNUSED_MATERIALS_WINDOW.isVisible():
        try:
            _FIND_UNUSED_MATERIALS_WINDOW.activateWindow()
            _FIND_UNUSED_MATERIALS_WINDOW.raise_()
            return _FIND_UNUSED_MATERIALS_WINDOW
        except Exception:
            # 如果旧窗口已经失效，则重新创建
            pass

    window = FindUnusedMaterialsWindow()
    window.show()
    _FIND_UNUSED_MATERIALS_WINDOW = window
    return _FIND_UNUSED_MATERIALS_WINDOW


def main():
    window = show_window()
    try:
        unreal.parent_external_window_to_slate(int(window.winId()))
    except Exception as e:
        unreal.log_warning(f"parent_external_window_to_slate failed: {e}")


if __name__ == "__main__":
    main()