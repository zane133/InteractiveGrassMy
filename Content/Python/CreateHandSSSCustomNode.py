import unreal

# 目标材质路径
MATERIAL_PATH = "/Game/XW_Art/RES/TAExample/BUff/M_buff3"


# 仅 Noise 可视化：投影 UV → Sample → 灰度输出
INPUTS = [
    ("NoiseTex",      unreal.MaterialExpressionTextureObjectParameter, None),

    ("colorLo",       unreal.MaterialExpressionVectorParameter,
                      unreal.LinearColor(0.0, 0.0, 0.0, 1.0)),
    ("colorHi",       unreal.MaterialExpressionVectorParameter,
                      unreal.LinearColor(0.0, 0.0, 0.0, 1.0)),

    ("sssAxis0",      unreal.MaterialExpressionVectorParameter,
                      unreal.LinearColor(1.0, 0.0, 0.0, 1.0)),
    ("sssAxis1",      unreal.MaterialExpressionVectorParameter,
                      unreal.LinearColor(1.0, 0.0, 0.0, 1.0)),
    ("sssAxis2",      unreal.MaterialExpressionVectorParameter,
                      unreal.LinearColor(0.0, 1.0, 0.0, 1.0)),
    ("sssAxis3",      unreal.MaterialExpressionVectorParameter,
                      unreal.LinearColor(0.0, 1.0, 0.0, 1.0)),

    ("noiseUVBase0",  unreal.MaterialExpressionVectorParameter,
                      unreal.LinearColor(0.0, 0.0, 0.0, 1.0)),
    ("noiseUVBase1",  unreal.MaterialExpressionVectorParameter,
                      unreal.LinearColor(0.0, 0.0, 0.0, 1.0)),
    ("noiseUVLerp",   unreal.MaterialExpressionScalarParameter, 0.0),
    ("noiseUVScale",  unreal.MaterialExpressionScalarParameter, 0.01),
    ("timeParam",     unreal.MaterialExpressionTime, None),
]

CUSTOM_CODE = """
float3 center = colorHi + colorLo;
float3 fromCenter = pos - center;

float2 noiseScroll = noiseUVLerp * (noiseUVBase1.xy - noiseUVBase0.xy) + noiseUVBase0.xy;

float2 noiseUV;
noiseUV.x = dot(center, sssAxis1) * dot(fromCenter, sssAxis0);
noiseUV.y = dot(center, sssAxis3) * dot(fromCenter, sssAxis2);
noiseUV = noiseUVScale * noiseUV;
noiseUV = timeParam * noiseScroll + noiseUV;

float n = NoiseTex.SampleLevel(NoiseTexSampler, noiseUV, 0).r;
return float4(n, n, n, n);
"""


def create_input_struct(input_name):
    custom_input = unreal.CustomInput()
    custom_input.set_editor_property("input_name", unreal.Name(input_name))
    return custom_input


def configure_input_node(node, input_name, default_value):
    if isinstance(node, unreal.MaterialExpressionScalarParameter):
        node.set_editor_property("parameter_name", unreal.Name(input_name))
        node.set_editor_property("default_value", float(default_value))
    elif isinstance(node, unreal.MaterialExpressionVectorParameter):
        node.set_editor_property("parameter_name", unreal.Name(input_name))
        node.set_editor_property("default_value", default_value)
    elif isinstance(node, unreal.MaterialExpressionTextureObjectParameter):
        node.set_editor_property("parameter_name", unreal.Name(input_name))
        if default_value:
            tex = unreal.load_asset(default_value)
            if tex is not None:
                node.set_editor_property("texture", tex)
    elif isinstance(node, unreal.MaterialExpressionTextureCoordinate):
        node.set_editor_property("coordinate_index", 0)


def connect_pos_local(material, custom_node, x, y):
    world_pos = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionWorldPosition, x, y
    )
    actor_pos = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionActorPositionWS, x, y + 80
    )
    subtract = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionSubtract, x + 220, y + 40
    )
    unreal.MaterialEditingLibrary.connect_material_expressions(
        world_pos, "", subtract, "A"
    )
    unreal.MaterialEditingLibrary.connect_material_expressions(
        actor_pos, "", subtract, "B"
    )
    ok = unreal.MaterialEditingLibrary.connect_material_expressions(
        subtract, "", custom_node, "pos"
    )
    if not ok:
        unreal.log_warning("连接失败：Subtract -> pos")


def configure_custom_node():
    material = unreal.load_asset(MATERIAL_PATH)
    if not isinstance(material, unreal.Material):
        raise RuntimeError(
            "MATERIAL_PATH 不是有效的 Material：{}".format(MATERIAL_PATH)
        )

    material.modify()
    material.set_editor_property(
        "blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT
    )
    material.set_editor_property(
        "shading_model", unreal.MaterialShadingModel.MSM_UNLIT
    )
    material.set_editor_property("two_sided", True)

    custom_node = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionCustom, 400, 0
    )
    if custom_node is None:
        raise RuntimeError("创建 Custom Node 失败。")

    custom_node.modify()

    all_names = ["pos"] + [name for name, _, _ in INPUTS]
    custom_node.set_editor_property(
        "inputs", [create_input_struct(n) for n in all_names]
    )
    custom_node.set_editor_property("code", CUSTOM_CODE)
    custom_node.set_editor_property(
        "output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT4
    )
    custom_node.set_editor_property("description", "Hand SSS — Noise RGB+A")

    custom_x = custom_node.get_editor_property("material_expression_editor_x")
    custom_y = custom_node.get_editor_property("material_expression_editor_y")
    start_x = custom_x - 520
    start_y = custom_y - 100
    spacing_y = 72

    connect_pos_local(material, custom_node, start_x - 280, start_y)

    for index, (input_name, node_class, default_value) in enumerate(INPUTS):
        node = unreal.MaterialEditingLibrary.create_material_expression(
            material, node_class, start_x, start_y + (index + 2) * spacing_y
        )
        configure_input_node(node, input_name, default_value)
        ok = unreal.MaterialEditingLibrary.connect_material_expressions(
            node, "", custom_node, input_name
        )
        if not ok:
            unreal.log_warning(
                "连接失败：{} -> {}".format(node.get_name(), input_name)
            )

    ok_rgb = unreal.MaterialEditingLibrary.connect_material_property(
        custom_node, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR
    )
    ok_a = unreal.MaterialEditingLibrary.connect_material_property(
        custom_node, "A", unreal.MaterialProperty.MP_OPACITY
    )
    if not ok_rgb:
        unreal.log_warning("连接失败：Custom.RGB -> Emissive Color")
    if not ok_a:
        unreal.log_warning("连接失败：Custom.A -> Opacity")

    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=True)

    unreal.log(
        "完成 Noise Custom：return float4(n,n,n,n)；RGB→Emissive，A→Opacity。{}".format(
            material.get_path_name()
        )
    )


configure_custom_node()
