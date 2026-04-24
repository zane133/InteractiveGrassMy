import importlib
import inspect
import sys
import traceback

import bpy

bl_info = {
    "name": "Channel Data Baker",
    "version": (1, 0, 1),
    "author": "matrix64",
    "blender": (3, 6, 0),
    "location": "3D Viewport > Sidebar > ChBaker",
    "description": "",
    "category": "Tool",
}

module_names = ["panel",
                "cdb_utils",
                "data_merge_transform",
                "batch_smart_pivot",
                "batch_active_attribute",
                "data_merge_linear_mask"]


class CDBPanelContext(bpy.types.PropertyGroup):
    items = [
        ("TRANSFORM", "Transform", "Transform", "EMPTY_ARROWS", 0),
        ("LINEAR_MASK", "Linear mask", "Linear mask", "MOD_MASK", 1),
        ("UTILS", "Utils", "Utils", "SHADERFX", 2),
    ]
    panel_enums: bpy.props.EnumProperty(
        items=(items),
        name="Addon Panels",
    )


class TransformProperty(bpy.types.PropertyGroup):
    channelToggle: bpy.props.BoolProperty(name="Pass Transform",
                                          description="",
                                          default=True)
    Mode: bpy.props.EnumProperty(name="Mode",
                                 description="",
                                 items=[('UV', "UV", ""),
                                        ('vCol', "vCol", "")])
    uvCh: bpy.props.IntProperty(name="UV Map",
                                default=0,
                                min=0,
                                max=7,
                                step=1,
                                description="Set the index of UV Map")
    scalePrecision: bpy.props.IntProperty(name="Scale Precision",
                                          default=4096,
                                          min=1,
                                          max=8192,
                                          step=1,
                                          description="Set the scale of pack number")
    axisPackGrp: bpy.props.EnumProperty(name="Pack Axis",
                                        description="",
                                        items=[('XY', "XY", ""),
                                               ('XZ', "XZ", ""),
                                               ('YZ', "YZ", "")])
    ChannelUV: bpy.props.EnumProperty(name="ChannelUV",
                                      description="",
                                      items=[('U', "U", ""),
                                             ('V', "V", "")])
    ChannelRGB: bpy.props.EnumProperty(name="ChannelRGB",
                                       description="",
                                       items=[('R', "R", ""),
                                              ('G', "G", ""),
                                              ('B', "B", ""),
                                              ('A', "A", "")])
    TransformOrientation: bpy.props.EnumProperty(name="Orientation",
                                      description="",
                                      items=[('Global', "Global", ""),
                                             ('Local', "Local", "")])
    negateValue: bpy.props.BoolProperty(name="Negate",
                                        description="Multiply baked value by -1 (e.g. Blender -Y → UE X)",
                                        default=False)


class CDBPropertyGroup(bpy.types.PropertyGroup):
    PosPackMode: bpy.props.EnumProperty(name="PackMode",
                                        description="",
                                        items=[('Individual', "Individual", ""),
                                               ('AB Pack', "AB Pack", ""),
                                               ('XYZ Pack', "XYZ Pack", "")])
    transformX: bpy.props.PointerProperty(type=TransformProperty)
    transformY: bpy.props.PointerProperty(type=TransformProperty)
    transformZ: bpy.props.PointerProperty(type=TransformProperty)
    linearMaskX: bpy.props.PointerProperty(type=TransformProperty)
    linearMaskY: bpy.props.PointerProperty(type=TransformProperty)
    linearMaskZ: bpy.props.PointerProperty(type=TransformProperty)
    transformAB: bpy.props.PointerProperty(type=TransformProperty)
    transformXYZ: bpy.props.PointerProperty(type=TransformProperty)
    pivotXScale: bpy.props.FloatProperty(name="Pivot X Scale")
    previewAttribute: bpy.props.StringProperty(name="Active Preview Attribute")


BASE_CLASSES = [TransformProperty, CDBPropertyGroup, CDBPanelContext]
classes = list(BASE_CLASSES)


def register():
    global classes
    classes = list(BASE_CLASSES)
    namespace = {}
    for name in module_names:
        fullname = '{}.{}.{}'.format(__package__, "lib", name)
        try:
            if fullname in sys.modules:
                namespace[name] = importlib.reload(sys.modules[fullname])
            else:
                namespace[name] = importlib.import_module(fullname)
        except Exception:
            print("### Channel Data Baker ### failed to import module:", fullname)
            traceback.print_exc()
            raise

    for module in module_names:
        for module_class in [obj for name, obj in inspect.getmembers(namespace[module]) if inspect.isclass(obj)]:
            if module_class not in classes:
                classes.append(module_class)

    for cls in classes:
        if not hasattr(bpy.types, cls.__name__):
            bpy.utils.register_class(cls)

    bpy.types.Scene.CDB_props = bpy.props.PointerProperty(type=CDBPropertyGroup)
    bpy.types.Scene.CDB_panel = bpy.props.PointerProperty(type=CDBPanelContext)

    print("### Channel Data Baker ### register success")


def unregister():
    for cls in reversed(classes):
        if hasattr(bpy.types, cls.__name__):
            bpy.utils.unregister_class(cls)

    if hasattr(bpy.types.Scene, 'CDB_props'):
        del bpy.types.Scene.CDB_props
    if hasattr(bpy.types.Scene, 'CDB_panel'):
        del bpy.types.Scene.CDB_panel
    classes.clear()
    classes.extend(BASE_CLASSES)

    print("### Channel Data Baker ### unregister success")


if __name__ == "__main__":
    register()
