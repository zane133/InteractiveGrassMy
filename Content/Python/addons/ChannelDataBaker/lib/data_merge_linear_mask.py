import bmesh
import bpy
from ChannelDataBaker.lib.cdb_utils import ensure_color_attribute, prepare_uv_channel


class DataMergeLinearMask(bpy.types.Operator):
    bl_idname = "object.data_merge_linear_mask"
    bl_label = "Bake linear mask data"

    def execute(self, context):
        props = context.scene.CDB_props
        selected_objects = bpy.context.selected_objects
        if not selected_objects:
            return {'CANCELLED'}

        for activeObj in selected_objects:
            bpy.context.view_layer.objects.active = activeObj
            bpy.ops.object.mode_set(mode='EDIT')

            bm = bmesh.from_edit_mesh(activeObj.data)
            bm.faces.active = None

            for axis in ['X', 'Y', 'Z']:
                linearMask = getattr(props, f"linearMask{axis}")
                axis_min = axis_max = 0
                if linearMask.TransformOrientation == 'Global':
                    axis_min = min(getattr(activeObj.matrix_world @ v.co, axis.lower()) for v in bm.verts)
                    axis_max = max(getattr(activeObj.matrix_world @ v.co, axis.lower()) for v in bm.verts)
                elif linearMask.TransformOrientation == 'Local':
                    axis_min = min(getattr(v.co, axis.lower()) for v in bm.verts)
                    axis_max = max(getattr(v.co, axis.lower()) for v in bm.verts)

                if linearMask.Mode == 'UV':
                    pack_to_uv(linearMask, bm, axis, axis_min, axis_max, activeObj)
                if linearMask.Mode == 'vCol':
                    pack_to_rgb(linearMask, bm, axis, axis_min, axis_max, activeObj)

            bmesh.update_edit_mesh(activeObj.data)
            bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}


def pack_to_rgb(linear_mask, bm, axis, axis_min, axis_max, obj):
    if linear_mask.channelToggle:
        color_layer_name = ensure_color_attribute(obj.data)
        color_layer = bm.loops.layers.color.get(color_layer_name)
        axis_range = axis_max - axis_min

        axis_normalized = 0
        for v in bm.verts:
            if axis_range == 0:
                axis_normalized = 0.0
            elif linear_mask.TransformOrientation == 'Global':
                axis_normalized = (getattr(obj.matrix_world @ v.co, axis.lower()) - axis_min) / axis_range
            elif linear_mask.TransformOrientation == 'Local':
                axis_normalized = (getattr(v.co, axis.lower()) - axis_min) / axis_range
            for loop in v.link_loops:
                if linear_mask.ChannelRGB == 'R':
                    loop[color_layer][0] = axis_normalized
                if linear_mask.ChannelRGB == 'G':
                    loop[color_layer][1] = axis_normalized
                if linear_mask.ChannelRGB == 'B':
                    loop[color_layer][2] = axis_normalized
                if linear_mask.ChannelRGB == 'A':
                    loop[color_layer][3] = axis_normalized


def pack_to_uv(linear_mask, bm, axis, axis_min, axis_max, obj):
    if linear_mask.channelToggle:
        uv_channel = bm.loops.layers.uv.get(prepare_uv_channel(linear_mask, obj).name)
        axis_range = axis_max - axis_min

        axis_normalized = 0
        for v in bm.verts:
            if axis_range == 0:
                axis_normalized = 0.0
            elif linear_mask.TransformOrientation == 'Global':
                axis_normalized = (getattr(obj.matrix_world @ v.co, axis.lower()) - axis_min) / axis_range
            elif linear_mask.TransformOrientation == 'Local':
                axis_normalized = (getattr(v.co, axis.lower()) - axis_min) / axis_range
            for loop in v.link_loops:
                if linear_mask.ChannelUV == 'U':
                    loop[uv_channel].uv.x = axis_normalized
                elif linear_mask.ChannelUV == 'V':
                    loop[uv_channel].uv.y = axis_normalized
