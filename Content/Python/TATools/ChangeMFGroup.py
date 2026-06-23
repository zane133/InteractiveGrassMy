import json
from collections import defaultdict
import unreal

py_lib = unreal.PyToolsBPLibrary


# ========== 配置 ==========
selected_assets = unreal.EditorUtilityLibrary.get_selected_assets()
if not selected_assets:
    raise Exception("没有选中任何资产")

first_asset = selected_assets[0]
if not isinstance(first_asset, unreal.MaterialFunction):
    raise Exception("第一个选中资产不是 MaterialFunction")

# 自动获取函数名并去掉 MF_ 前缀
raw_name = first_asset.get_name()
if "_" in raw_name:
    NEW_GROUP_NAME = raw_name.split("_", 1)[1]  # 只保留第一个下划线后的内容
else:
    NEW_GROUP_NAME = raw_name

print(f"使用分组名（来自函数名）：{NEW_GROUP_NAME}")
# ==========================

def cast(typ, obj):
    """
    unreal cast 类型转换
    """
    try:
        return getattr(unreal, typ).cast(obj)
    except:
        return None

# def _get_material_paramters(expressions):
#     """
#     inspire by https://github.com/20tab/UnrealEnginePython/issues/103
#     reference from MaterialFunctionInterface.h `GetParameterGroupName`
#     """
#     paramters = defaultdict(set)
#     for expresion in expressions:
#         # NOTE 查找 material function 内部节点
#         func = cast("MaterialExpressionMaterialFunctionCall", expresion)
#         if func:
#             func = func.get_editor_property("material_function")
#             expressions = py_lib.get_material_function_expressions(func)
#             # NOTE 递归查找参数节点
#             params = _get_material_paramters(expressions)
#             for group, param in params.items():
#                 for p in param:
#                     paramters[str(group)].add(str(p))
#             continue

#         # NOTE 查找转换参数节点
#         param = cast("MaterialExpressionParameter", expresion)
#         if not param:
#             param = cast("MaterialExpressionTextureSampleParameter", expresion)
#         if not param:
#             param = cast("MaterialExpressionFontSampleParameter", expresion)

#         # NOTE 查找参数节点的 分组 和 参数命名
#         if param:
#             group = param.get_editor_property("group")
#             parameter_name = param.get_editor_property("parameter_name")
#             paramters[str(group)].add(str(parameter_name))

#     return paramters

# selected_assets = unreal.EditorUtilityLibrary.get_selected_assets()
# count_total = 0

for asset in selected_assets:
    if isinstance(asset, unreal.MaterialFunction):
        changed = 0
        expressions = py_lib.get_material_function_expressions(asset)
        # param = _get_material_paramters(expressions)
        # print("参数分组:", param)


# expressions 是 MaterialFunction 的所有表达式
for expr in expressions:
    # 判断是否是参数类节点（你已经写好了）
    param = cast("MaterialExpressionParameter", expr)
    if not param:
        param = cast("MaterialExpressionTextureSampleParameter", expr)
    if not param:
        param = cast("MaterialExpressionFontSampleParameter", expr)
    if param:
        # 设置新分组
        py_lib.set_material_expression_group(expr, NEW_GROUP_NAME)

        # 修改名字前缀为组名
        old_name = str(param.get_editor_property("parameter_name"))
        new_prefix = f"{NEW_GROUP_NAME}_"

        if old_name.startswith("Layer") and "_" in old_name:
            suffix = old_name.split("_", 1)[1]
            new_name = new_prefix + suffix
        else:
            if not old_name.startswith(new_prefix):
                new_name = new_prefix + old_name
            else:
                new_name = old_name

        if new_name != old_name:
            param.set_editor_property("parameter_name", new_name)
            changed += 1

# for asset in selected_assets:
#     if isinstance(asset, unreal.MaterialFunction):
#         changed = 0
#         expressions = py_lib.get_material_function_expressions(asset)
#         param = _get_material_paramters(expressions)
#         print("参数分组:", param)
    unreal.EditorAssetLibrary.save_asset(asset.get_path_name())
