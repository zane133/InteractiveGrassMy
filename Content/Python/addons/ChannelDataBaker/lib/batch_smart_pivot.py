import bpy


class BatchSmartPivot(bpy.types.Operator):
    bl_idname = "object.batch_smart_pivot"
    bl_label = "Batch Smart Pivot"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        if context.object.mode == 'EDIT':
            selected_objects = context.selected_objects
            for obj in selected_objects:
                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.select_all(action='DESELECT')

                obj.select_set(True)
                context.view_layer.objects.active = obj

                bpy.ops.object.mode_set(mode='EDIT')

                if bpy.context.object.data.total_vert_sel > 0:
                    cursor_init_loc = context.scene.cursor.location.copy()

                    bpy.ops.view3d.snap_cursor_to_selected()

                    bpy.ops.object.mode_set(mode='OBJECT')
                    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

                    context.scene.cursor.location = cursor_init_loc
                    bpy.ops.object.mode_set(mode='EDIT')

            bpy.ops.object.mode_set(mode='OBJECT')
            for obj in selected_objects:
                obj.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT')

        else:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='BOUNDS')
        return {'FINISHED'}
