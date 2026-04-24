import bpy


class VIEW3D_PT_tools_channel_data_baker(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ChBaker'
    bl_label = "Channel Data Baker"

    # bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        props = context.scene.CDB_props
        panel = context.scene.CDB_panel

        box = self.layout.box()
        row = box.row(align=True)
        row.scale_y = 1
        row.scale_x = 1
        row.prop(panel, "panel_enums", icon_only=True, expand=True)
        if panel.panel_enums == 'TRANSFORM':
            row.label(text="Transform")
            box_transform = self.layout.box()
            box_transform.prop(props, "PosPackMode")
            if props.PosPackMode == 'Individual':
                for axis in ['X', 'Y', 'Z']:
                    transform = getattr(props, f"transform{axis}")
                    box = box_transform.box()
                    row_toggle = box.row()
                    row_toggle.prop(transform, "channelToggle", text=f"{axis}")
                    row_toggle.prop(transform, "negateValue")
                    box.prop(transform, "Mode")
                    if transform.Mode == 'UV':
                        box.prop(transform, "uvCh")
                        box.prop(transform, "ChannelUV")
                    else:
                        box.prop(transform, "ChannelRGB")

            elif props.PosPackMode == 'AB Pack':
                transform = props.transformAB
                box = box_transform.box()
                box.prop(transform, "channelToggle", text='AB')
                box.prop(transform, "scalePrecision")
                box.prop(transform, "uvCh")
                box.prop(transform, "axisPackGrp")
                box.prop(transform, "ChannelUV")

            elif props.PosPackMode == 'XYZ Pack':
                transform = props.transformXYZ
                box = box_transform.box()
                box.prop(transform, "channelToggle", text='XYZ')
                box.prop(transform, "uvCh")
                box.prop(transform, "ChannelUV")

            box = self.layout.box()
            row = box.row()
            row.prop(props, "pivotXScale")
            row.operator("object.get_pivot_x_scale")

            box = self.layout.box()
            box.operator("object.data_merge_transform")
        elif panel.panel_enums == 'LINEAR_MASK':
            row.label(text="Linear Mask")
            box_linearMask = self.layout.box()
            for axis in ['X', 'Y', 'Z']:
                linearMask = getattr(props, f"linearMask{axis}")
                box = box_linearMask.box()
                box.prop(linearMask, "channelToggle", text=f"{axis}")
                box.prop(linearMask, "Mode")
                box.prop(linearMask, "TransformOrientation")
                if linearMask.Mode == 'UV':
                    box.prop(linearMask, "uvCh")
                    box.prop(linearMask, "ChannelUV")
                else:
                    box.prop(linearMask, "ChannelRGB")

            box = self.layout.box()
            box.operator("object.data_merge_linear_mask")
        elif panel.panel_enums == 'UTILS':
            row.label(text="Utils")
            box = self.layout.box()
            row = box.row()
            row.operator("object.delete_pos_uvmap")
            row.operator("object.delete_pos_vcolor")

            box = self.layout.box()
            row = box.row()
            row.prop(props, "previewAttribute")
            row.operator("object.batch_active_attribute")

            box = self.layout.box()
            box.operator("object.batch_smart_pivot")
