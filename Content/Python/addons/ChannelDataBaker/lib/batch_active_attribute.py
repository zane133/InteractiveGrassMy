import bpy

from ChannelDataBaker.lib.cdb_utils import set_active_color_attribute


class BatchActiveAttribute(bpy.types.Operator):
    bl_idname = "object.batch_active_attribute"
    bl_label = "Batch Active Attribute"

    def execute(self, context):
        props = context.scene.CDB_props
        attribute_name = props.previewAttribute

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            set_active_color_attribute(obj.data, attribute_name)
        return {'FINISHED'}
