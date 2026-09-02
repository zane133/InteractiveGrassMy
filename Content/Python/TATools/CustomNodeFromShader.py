# -*- coding: utf-8 -*-
"""PySide6 tool: paste HLSL and create an Unreal Material Custom node."""

from __future__ import annotations

import importlib

import unreal

from PackageInstall import install_packages

install_packages([("PySide6", "PySide6")])

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import unreal_stylesheet
import TATools.custom_node_shader_core as shader_core

importlib.reload(shader_core)


_WINDOW = None
_OUTPUT_TYPES = {
    1: unreal.CustomMaterialOutputType.CMOT_FLOAT1,
    2: unreal.CustomMaterialOutputType.CMOT_FLOAT2,
    3: unreal.CustomMaterialOutputType.CMOT_FLOAT3,
    4: unreal.CustomMaterialOutputType.CMOT_FLOAT4,
}
_DEFAULT_TEXTURE_PATH = "/Engine/EngineResources/WhiteSquareTexture.WhiteSquareTexture"


def _selected_material_path() -> str:
    for asset in unreal.EditorUtilityLibrary.get_selected_assets():
        if isinstance(asset, unreal.Material):
            return asset.get_path_name()
    return ""


def _load_material(path: str):
    asset = unreal.load_asset(path.strip()) if path.strip() else None
    if not isinstance(asset, unreal.Material):
        raise ValueError("请选择一个 Material 资产（暂不支持 Material Instance）。")
    return asset


def _create_input(name: str):
    custom_input = unreal.CustomInput()
    custom_input.set_editor_property("input_name", unreal.Name(name))
    return custom_input


def _create_default_input_node(
    material,
    input_name: str,
    code: str,
    x: int,
    y: int,
    parameter_group: str,
    sort_priority: int,
):
    kind = shader_core.infer_default_node_kind(code, input_name)

    if kind == shader_core.DEFAULT_NODE_TEXTURE:
        node_class = unreal.MaterialExpressionTextureSampleParameter2D
    elif kind == shader_core.DEFAULT_NODE_VECTOR:
        node_class = unreal.MaterialExpressionVectorParameter
    else:
        node_class = unreal.MaterialExpressionScalarParameter

    node = unreal.MaterialEditingLibrary.create_material_expression(
        material, node_class, x, y
    )
    if node is None:
        raise RuntimeError("无法为输入 {} 创建默认节点。".format(input_name))

    node.modify()
    node.set_editor_property("parameter_name", unreal.Name(input_name))
    node.set_editor_property("group", unreal.Name(parameter_group))
    # Unreal displays lower Sort Priority values higher in Material Instances.
    node.set_editor_property("sort_priority", sort_priority)

    if kind == shader_core.DEFAULT_NODE_TEXTURE:
        default_texture = unreal.load_asset(_DEFAULT_TEXTURE_PATH)
        if default_texture is not None:
            node.set_editor_property("texture", default_texture)
    elif kind == shader_core.DEFAULT_NODE_VECTOR:
        node.set_editor_property("default_value", unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
    else:
        node.set_editor_property("default_value", 0.0)

    return node, kind


def _create_and_connect_default_nodes(
    material,
    custom_node,
    inputs,
    code,
    custom_x,
    custom_y,
    parameter_group,
):
    if not inputs:
        return 0, []

    connected_count = 0
    failed_inputs = []

    # Keep the exact Inputs declaration order. In the material graph, increasing
    # Y means moving down, so the first input is always the top-most node.
    layout = shader_core.build_top_to_bottom_layout(inputs, custom_x, custom_y)
    for sort_priority, (input_name, input_x, input_y) in enumerate(layout):
        input_node, _ = _create_default_input_node(
            material,
            input_name,
            code,
            input_x,
            input_y,
            parameter_group,
            sort_priority,
        )
        connected = unreal.MaterialEditingLibrary.connect_material_expressions(
            input_node,
            "",
            custom_node,
            input_name,
        )
        if connected:
            connected_count += 1
        else:
            failed_inputs.append(input_name)
            unreal.log_warning(
                "[ShaderToCustomNode] Failed to connect default node -> {}".format(
                    input_name
                )
            )

    return connected_count, failed_inputs


class CustomNodeFromShaderWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shader → Custom Node")
        self.resize(1080, 760)
        self.setMinimumSize(760, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        target_row = QHBoxLayout()
        target_row.addWidget(QLabel("目标材质：", self))
        self.material_edit = QLineEdit(self)
        self.material_edit.setPlaceholderText("先在 Content Browser 选中一个 Material")
        self.material_edit.setText(_selected_material_path())
        target_row.addWidget(self.material_edit, 1)
        pick_button = QPushButton("使用当前选择", self)
        pick_button.clicked.connect(self.use_selection)
        target_row.addWidget(pick_button)
        root.addLayout(target_row)

        settings = QHBoxLayout()
        form = QFormLayout()
        self.description_edit = QLineEdit("Pasted Custom HLSL", self)
        form.addRow("节点名称：", self.description_edit)
        self.output_combo = QComboBox(self)
        for components in range(1, 5):
            self.output_combo.addItem("Float{}".format(components), components)
        form.addRow("输出类型：", self.output_combo)
        self.parameter_group_edit = QLineEdit("Custom Node Inputs", self)
        self.parameter_group_edit.setPlaceholderText("Material Instance 参数组名称")
        form.addRow("实例参数组：", self.parameter_group_edit)
        settings.addLayout(form, 1)

        position_form = QFormLayout()
        self.x_spin = QSpinBox(self)
        self.y_spin = QSpinBox(self)
        for spin in (self.x_spin, self.y_spin):
            spin.setRange(-100000, 100000)
            spin.setSingleStep(100)
        self.x_spin.setValue(400)
        position_form.addRow("节点 X：", self.x_spin)
        position_form.addRow("节点 Y：", self.y_spin)
        settings.addLayout(position_form)
        root.addLayout(settings)

        splitter = QSplitter(Qt.Horizontal, self)

        code_panel = QWidget(splitter)
        code_layout = QVBoxLayout(code_panel)
        code_layout.setContentsMargins(0, 0, 4, 0)
        code_header = QHBoxLayout()
        code_header.addWidget(QLabel("HLSL（可直接 Ctrl+V）", code_panel))
        code_header.addStretch(1)
        paste_button = QPushButton("从剪贴板粘贴", code_panel)
        paste_button.clicked.connect(self.paste_clipboard)
        code_header.addWidget(paste_button)
        parse_button = QPushButton("解析注释", code_panel)
        parse_button.clicked.connect(self.parse_code)
        code_header.addWidget(parse_button)
        code_layout.addLayout(code_header)
        self.code_edit = QPlainTextEdit(code_panel)
        self.code_edit.setPlaceholderText(
            "粘贴 Custom Node HLSL。支持从注释自动读取：\n"
            "// Output Type: CMOT Float 3\n"
            "// Inputs (names must match exactly):\n"
            "//   MyInput - description"
        )
        self.code_edit.setLineWrapMode(QPlainTextEdit.NoWrap)
        self._parse_timer = QTimer(self)
        self._parse_timer.setSingleShot(True)
        self._parse_timer.setInterval(300)
        self._parse_timer.timeout.connect(self._auto_parse_code)
        self.code_edit.textChanged.connect(self._parse_timer.start)
        code_layout.addWidget(self.code_edit, 1)
        splitter.addWidget(code_panel)

        input_panel = QWidget(splitter)
        input_layout = QVBoxLayout(input_panel)
        input_layout.setContentsMargins(4, 0, 0, 0)
        input_layout.addWidget(QLabel("输入 Pin（每行一个，可手动修改）", input_panel))
        self.inputs_edit = QPlainTextEdit(input_panel)
        self.inputs_edit.setPlaceholderText("DyeIdRGB\nClothPrimary\nClothSecondary")
        self.inputs_edit.setLineWrapMode(QPlainTextEdit.NoWrap)
        input_layout.addWidget(self.inputs_edit, 1)
        self.parse_status = QLabel("等待粘贴 Shader", input_panel)
        self.parse_status.setWordWrap(True)
        input_layout.addWidget(self.parse_status)
        splitter.addWidget(input_panel)
        splitter.setSizes([760, 300])
        root.addWidget(splitter, 1)

        monospace = QFont("Consolas")
        monospace.setStyleHint(QFont.Monospace)
        monospace.setPointSize(10)
        self.code_edit.setFont(monospace)
        self.inputs_edit.setFont(monospace)

        footer = QHBoxLayout()
        self.default_nodes_checkbox = QCheckBox("创建并连接左侧默认参数节点", self)
        self.default_nodes_checkbox.setChecked(True)
        footer.addWidget(self.default_nodes_checkbox)
        self.save_checkbox = QCheckBox("创建后保存材质", self)
        self.save_checkbox.setChecked(False)
        footer.addWidget(self.save_checkbox)
        footer.addStretch(1)
        create_button = QPushButton("创建 Custom Node", self)
        create_button.setDefault(True)
        create_button.clicked.connect(self.create_node)
        footer.addWidget(create_button)
        root.addLayout(footer)

    def use_selection(self):
        path = _selected_material_path()
        if not path:
            QMessageBox.warning(self, "未选择材质", "请在 Content Browser 选中一个 Material。")
            return
        self.material_edit.setText(path)

    def paste_clipboard(self):
        clipboard = QApplication.clipboard()
        self.code_edit.setPlainText(clipboard.text())
        self.parse_code()

    def parse_code(self):
        parsed = shader_core.parse_shader(self.code_edit.toPlainText())
        self.code_edit.blockSignals(True)
        try:
            self.code_edit.setPlainText(parsed.code)
        finally:
            self.code_edit.blockSignals(False)
        self._apply_parsed(parsed)

    def _auto_parse_code(self):
        source = self.code_edit.toPlainText()
        if not source.strip():
            return
        self._apply_parsed(shader_core.parse_shader(source))

    def _apply_parsed(self, parsed):
        self.inputs_edit.setPlainText("\n".join(parsed.inputs))
        self.output_combo.setCurrentIndex(max(0, parsed.output_components - 1))
        self.description_edit.setText(parsed.description)
        self.parse_status.setText(
            "已解析 {} 个输入，输出 Float{}；已清理 HTML / Markdown 转义。".format(
                len(parsed.inputs), parsed.output_components
            )
        )

    def create_node(self):
        try:
            material = _load_material(self.material_edit.text())
            code = shader_core.clean_shader_text(self.code_edit.toPlainText())
            inputs = shader_core.normalize_manual_inputs(self.inputs_edit.toPlainText())
            if not code:
                raise ValueError("Shader 代码不能为空。")

            description = self.description_edit.text().strip() or "Pasted Custom HLSL"
            output_components = int(self.output_combo.currentData())
            parameter_group = (
                self.parameter_group_edit.text().strip() or "Custom Node Inputs"
            )
            connected_count = 0
            failed_inputs = []

            with unreal.ScopedEditorTransaction("Create Custom Node From Shader"):
                material.modify()
                node = unreal.MaterialEditingLibrary.create_material_expression(
                    material,
                    unreal.MaterialExpressionCustom,
                    self.x_spin.value(),
                    self.y_spin.value(),
                )
                if node is None:
                    raise RuntimeError("Unreal 未能创建 MaterialExpressionCustom。")
                node.modify()
                node.set_editor_property("code", code)
                node.set_editor_property("inputs", [_create_input(name) for name in inputs])
                node.set_editor_property("output_type", _OUTPUT_TYPES[output_components])
                node.set_editor_property("description", description)

                if self.default_nodes_checkbox.isChecked():
                    connected_count, failed_inputs = _create_and_connect_default_nodes(
                        material,
                        node,
                        inputs,
                        code,
                        self.x_spin.value(),
                        self.y_spin.value(),
                        parameter_group,
                    )

            unreal.MaterialEditingLibrary.recompile_material(material)
            if self.save_checkbox.isChecked():
                unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=True)

            unreal.EditorAssetLibrary.sync_browser_to_objects(
                asset_paths=[material.get_path_name()]
            )
            self.parse_status.setText(
                "创建成功：{}（{} 个输入，已连接 {} 个，实例参数已排序）".format(
                    material.get_name(), len(inputs), connected_count
                )
            )
            unreal.log(
                "[ShaderToCustomNode] Created '{}' in {}".format(
                    description, material.get_path_name()
                )
            )
            QMessageBox.information(
                self,
                "创建成功",
                "已在 {} 创建 Custom Node。\n输入：{} 个；默认节点已连接：{} 个；"
                "输出：Float{}\n实例参数组：{}（按 Inputs 顺序排列）{}".format(
                    material.get_name(),
                    len(inputs),
                    connected_count,
                    output_components,
                    parameter_group,
                    "\n连接失败：{}".format(", ".join(failed_inputs))
                    if failed_inputs
                    else "",
                ),
            )
        except Exception as exc:
            unreal.log_error("[ShaderToCustomNode] {}".format(exc))
            QMessageBox.critical(self, "创建失败", str(exc))


def show_window():
    global _WINDOW

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    unreal_stylesheet.setup()

    if _WINDOW is not None and _WINDOW.isVisible():
        _WINDOW.activateWindow()
        _WINDOW.raise_()
        return _WINDOW

    _WINDOW = CustomNodeFromShaderWindow()
    _WINDOW.show()
    return _WINDOW


def main():
    window = show_window()
    try:
        unreal.parent_external_window_to_slate(int(window.winId()))
    except Exception as exc:
        unreal.log_warning("parent_external_window_to_slate failed: {}".format(exc))
    return window


if __name__ == "__main__":
    main()
