import unreal

# 要创建节点的目标材质路径。
# 示例：MATERIAL_PATH = "/Game/XW_Art/RES/TAExample/BUff/M_buff1"
MATERIAL_PATH = "/Game/XW_Art/RES/TAExample/BUff/M_buff1"

INPUTS = [
    # InputName, NodeClass, DefaultValue
    ("NormalWS",      unreal.MaterialExpressionPixelNormalWS, None),
    ("ViewDirWS",     unreal.MaterialExpressionCameraVectorWS, None),
    ("RimColor",      unreal.MaterialExpressionVectorParameter,
                      unreal.LinearColor(0.1, 0.5, 1.0, 1.0)),
    ("RimPower",      unreal.MaterialExpressionScalarParameter, 2.0),
    ("GradientStart", unreal.MaterialExpressionScalarParameter, 0.1),
    ("GradientEnd",   unreal.MaterialExpressionScalarParameter, 0.8),
    ("Intensity",     unreal.MaterialExpressionScalarParameter, 5.0),
    ("Opacity",       unreal.MaterialExpressionScalarParameter, 0.7),
    ("Mask",          unreal.MaterialExpressionScalarParameter, 1.0),
    ("TimeValue",     unreal.MaterialExpressionTime, None),
    ("PulseSpeed",    unreal.MaterialExpressionScalarParameter, 6.0),
    ("PulseAmount",   unreal.MaterialExpressionScalarParameter, 0.0),
]

CUSTOM_CODE = """
float3 N = normalize(NormalWS);
float3 V = normalize(ViewDirWS);

float NdotV = saturate(abs(dot(N, V)));
float Rim = pow(saturate(1.0 - NdotV), max(RimPower, 0.001));

float MinGradient = min(GradientStart, GradientEnd);
float MaxGradient = max(GradientStart, GradientEnd);
Rim = smoothstep(MinGradient, MaxGradient, Rim);

float Pulse = 0.5 + 0.5 * sin(TimeValue * PulseSpeed);
Pulse = lerp(1.0, Pulse, saturate(PulseAmount));

float FinalMask = Rim * saturate(Mask) * Pulse;
float3 FinalColor = RimColor * Intensity * FinalMask;
float FinalOpacity = saturate(FinalMask * Opacity);

return float4(FinalColor, FinalOpacity);
"""


def create_custom_node():
    material = unreal.load_asset(MATERIAL_PATH)
    if not isinstance(material, unreal.Material):
        raise RuntimeError(
            "MATERIAL_PATH 不是有效的 Material：{}".format(MATERIAL_PATH)
        )

    custom_node = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionCustom,
        400,
        0
    )
    if custom_node is None:
        raise RuntimeError("创建 Custom Node 失败。")

    return material, custom_node


def create_input_struct(input_name):
    custom_input = unreal.CustomInput()
    custom_input.set_editor_property(
        "input_name",
        unreal.Name(input_name)
    )
    return custom_input


def configure_custom_node():
    material, custom_node = create_custom_node()

    material.modify()
    custom_node.modify()

    # 重建 Custom Node 输入
    custom_inputs = [
        create_input_struct(name)
        for name, _, _ in INPUTS
    ]

    custom_node.set_editor_property("inputs", custom_inputs)
    custom_node.set_editor_property("code", CUSTOM_CODE)
    custom_node.set_editor_property(
        "output_type",
        unreal.CustomMaterialOutputType.CMOT_FLOAT4
    )
    custom_node.set_editor_property(
        "description",
        "Overlay Buff Rim Light"
    )

    custom_x = custom_node.get_editor_property(
        "material_expression_editor_x"
    )
    custom_y = custom_node.get_editor_property(
        "material_expression_editor_y"
    )

    # 在 Custom Node 左侧排列参数
    start_x = custom_x - 420
    start_y = custom_y - 300
    spacing_y = 90

    for index, (input_name, node_class, default_value) in enumerate(INPUTS):
        node = unreal.MaterialEditingLibrary.create_material_expression(
            material,
            node_class,
            start_x,
            start_y + index * spacing_y
        )

        if isinstance(node, unreal.MaterialExpressionScalarParameter):
            node.set_editor_property(
                "parameter_name",
                unreal.Name(input_name)
            )
            node.set_editor_property(
                "default_value",
                float(default_value)
            )

        elif isinstance(node, unreal.MaterialExpressionVectorParameter):
            node.set_editor_property(
                "parameter_name",
                unreal.Name(input_name)
            )
            node.set_editor_property(
                "default_value",
                default_value
            )

        connected = unreal.MaterialEditingLibrary.connect_material_expressions(
            node,
            "",
            custom_node,
            input_name
        )

        if not connected:
            unreal.log_warning(
                "连接失败：{} -> {}".format(
                    node.get_name(),
                    input_name
                )
            )

    unreal.MaterialEditingLibrary.recompile_material(material)

    unreal.EditorAssetLibrary.save_loaded_asset(
        material,
        only_if_is_dirty=True
    )

    unreal.log(
        "完成：已配置 Custom Node：{}".format(
            material.get_path_name()
        )
    )


configure_custom_node()