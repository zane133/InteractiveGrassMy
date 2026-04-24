import bpy


def _build_vertex_islands(mesh):
    # Build adjacency from edges.
    adjacency = {v.index: set() for v in mesh.vertices}
    for edge in mesh.edges:
        a = edge.vertices[0]
        b = edge.vertices[1]
        adjacency[a].add(b)
        adjacency[b].add(a)

    visited = set()
    islands = []

    for v in mesh.vertices:
        if v.index in visited:
            continue

        stack = [v.index]
        visited.add(v.index)
        island = []

        while stack:
            current = stack.pop()
            island.append(current)
            for n in adjacency[current]:
                if n not in visited:
                    visited.add(n)
                    stack.append(n)

        islands.append(island)

    return islands


def bake_grass_root_to_uv2(vertices_per_blade=4, use_world_xy=False, use_islands=True):
    selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
    if not selected_objects:
        print("No mesh objects selected.")
        return

    for obj in selected_objects:
        mesh = obj.data
        total_vertices = len(mesh.vertices)

        if total_vertices == 0:
            print(f"[{obj.name}] Skipped: mesh has no vertices.")
            continue

        # Ensure UV2 exists (channel index 1).
        if len(mesh.uv_layers) < 2:
            mesh.uv_layers.new(name="UVMap_2")
        uv_layer = mesh.uv_layers[1]

        vertex_to_root_uv = {}

        if use_islands:
            islands = _build_vertex_islands(mesh)
            blade_count = len(islands)
            for island in islands:
                root_vertex_index = min(island, key=lambda i: mesh.vertices[i].co.z)
                root_local = mesh.vertices[root_vertex_index].co

                if use_world_xy:
                    root_world = obj.matrix_world @ root_local
                    root_uv = (root_world.x, root_world.y)
                else:
                    root_uv = (root_local.x, root_local.y)

                for vertex_index in island:
                    vertex_to_root_uv[vertex_index] = root_uv
        else:
            if total_vertices % vertices_per_blade != 0:
                print(
                    f"[{obj.name}] Warning: vertex count ({total_vertices}) "
                    f"is not divisible by vertices_per_blade ({vertices_per_blade})."
                )

            blade_count = total_vertices // vertices_per_blade
            if blade_count <= 0:
                print(f"[{obj.name}] Skipped: no complete blade groups.")
                continue

            for blade_index in range(blade_count):
                start = blade_index * vertices_per_blade
                end = start + vertices_per_blade
                blade_verts = mesh.vertices[start:end]

                root_vert = min(blade_verts, key=lambda v: v.co.z)
                root_local = root_vert.co

                if use_world_xy:
                    root_world = obj.matrix_world @ root_local
                    root_uv = (root_world.x, root_world.y)
                else:
                    root_uv = (root_local.x, root_local.y)

                for vertex_index in range(start, end):
                    vertex_to_root_uv[vertex_index] = root_uv

        # Write UV2 by loop (face corner) using the loop's vertex index.
        for poly in mesh.polygons:
            for loop_index in poly.loop_indices:
                vertex_index = mesh.loops[loop_index].vertex_index
                root_uv = vertex_to_root_uv.get(vertex_index)
                if root_uv is not None:
                    uv_layer.data[loop_index].uv = root_uv

        mesh.update()
        print(f"[{obj.name}] Done. Blades detected: {blade_count}")


if __name__ == "__main__":
    bake_grass_root_to_uv2(vertices_per_blade=4, use_world_xy=False, use_islands=True)
