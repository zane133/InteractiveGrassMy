COLOR_ATTRIBUTE_NAME = "cbd_vcolor"


def prepare_uv_channel(transform, active_obj):
    if transform.uvCh < len(active_obj.data.uv_layers):
        uv_layer = active_obj.data.uv_layers[transform.uvCh]
        if uv_layer.data:
            uv_layer.name = "cdb_UVMap"
        return uv_layer
    else:
        return active_obj.data.uv_layers.new(name="cdb_UVMap")


def ensure_color_attribute(mesh, attribute_name=COLOR_ATTRIBUTE_NAME):
    color_attributes = getattr(mesh, "color_attributes", None)
    if color_attributes is not None:
        attribute = color_attributes.get(attribute_name)
        if attribute is not None and (
            attribute.domain != 'CORNER' or attribute.data_type != 'BYTE_COLOR'
        ):
            color_attributes.remove(attribute)
            attribute = None

        if attribute is None:
            attribute = color_attributes.new(attribute_name, 'BYTE_COLOR', 'CORNER')

        color_attributes.active_color_name = attribute.name
        if hasattr(color_attributes, "default_color_name"):
            color_attributes.default_color_name = attribute.name
        return attribute.name

    vertex_colors = mesh.vertex_colors
    color_layer = vertex_colors.get(attribute_name)
    if color_layer is None:
        color_layer = vertex_colors.new(name=attribute_name)

    if hasattr(vertex_colors, "active_index"):
        vertex_colors.active_index = list(vertex_colors.keys()).index(color_layer.name)
    return color_layer.name


def remove_color_attribute(mesh, attribute_name=COLOR_ATTRIBUTE_NAME):
    color_attributes = getattr(mesh, "color_attributes", None)
    if color_attributes is not None:
        attribute = color_attributes.get(attribute_name)
        if attribute is not None:
            color_attributes.remove(attribute)
        return

    vertex_colors = getattr(mesh, "vertex_colors", None)
    if vertex_colors is None:
        return

    color_layer = vertex_colors.get(attribute_name)
    if color_layer is not None:
        vertex_colors.remove(color_layer)


def set_active_color_attribute(mesh, attribute_name):
    color_attributes = getattr(mesh, "color_attributes", None)
    if color_attributes is not None:
        attribute = color_attributes.get(attribute_name)
        if attribute is None or attribute.data_type not in {'BYTE_COLOR', 'FLOAT_COLOR'}:
            return False

        color_attributes.active_color_name = attribute.name
        if hasattr(color_attributes, "default_color_name"):
            color_attributes.default_color_name = attribute.name
        return True

    vertex_colors = getattr(mesh, "vertex_colors", None)
    if vertex_colors is None:
        return False

    color_layer = vertex_colors.get(attribute_name)
    if color_layer is None:
        return False

    if hasattr(vertex_colors, "active_index"):
        vertex_colors.active_index = list(vertex_colors.keys()).index(color_layer.name)
    return True
