#!/usr/bin/env python3
"""export_color3mf.py — write a COLOR 3MF that slicers open IN COLOR.

Why: trimesh's `mesh.export('x.3mf')` does NOT embed per-vertex colors — the 3MF
comes out colorless and a slicer (Bambu Studio / PrusaSlicer / OrcaSlicer) shows a
flat grey model. So we do NOT use trimesh for the 3MF write. Instead we build the
3MF with the official lib3mf bindings using the 3MF Materials-and-Properties color
extension: a single ColorGroup holding one color per (unique) vertex color, and a
per-triangle property assigning each triangle's 3 corners their vertex colors.
That per-corner color group is exactly what the slicers read to render color.

How:
  1. Load the input mesh with trimesh. Flatten a GLB scene to one mesh. Get
     per-vertex RGB. If the mesh only has a texture (no vertex colors), sample the
     texture into vertex colors via `visual.to_color()`.
  2. Build the 3MF with lib3mf: add vertices + triangles, add a ColorGroup with one
     entry per distinct vertex color, and set per-triangle properties pointing each
     triangle corner at its color.
  3. Write the file and print a clear success / failure line.

Usage:
  python export_color3mf.py <input_colored_mesh> <output.3mf>
"""
import sys
import os
import argparse

import numpy as np
import trimesh
import lib3mf


def load_colored_mesh(path):
    """Load `path` with trimesh and return (vertices Nx3 float, faces Mx3 int,
    vertex_colors Nx4 uint8). Handles GLB scenes and texture-only meshes."""
    loaded = trimesh.load(path, force=None, process=False)

    # A GLB/GLTF (or any multi-geometry file) loads as a Scene — flatten to one mesh.
    if isinstance(loaded, trimesh.Scene):
        if len(loaded.geometry) == 0:
            raise ValueError(f"{path}: scene contains no geometry")
        # to_geometry()/dump(concatenate=True) bakes transforms and merges geometries.
        mesh = loaded.to_geometry() if hasattr(loaded, "to_geometry") else \
            loaded.dump(concatenate=True)
    else:
        mesh = loaded

    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError(f"{path}: could not resolve to a single mesh (got {type(mesh)})")

    verts = np.asarray(mesh.vertices, dtype=np.float64)
    faces = np.asarray(mesh.faces, dtype=np.int64)

    # Resolve per-vertex colors.
    visual = mesh.visual
    vcolors = None

    # Texture-only mesh: convert the texture/material into vertex colors.
    if isinstance(visual, trimesh.visual.TextureVisuals):
        try:
            visual = visual.to_color()
        except Exception as exc:  # noqa: BLE001
            print(f"[export_color3mf] WARN: to_color() failed ({exc}); using grey")
            visual = None

    if visual is not None and hasattr(visual, "vertex_colors"):
        vc = np.asarray(visual.vertex_colors)
        if vc.shape[0] == verts.shape[0] and vc.size > 0:
            vcolors = vc

    if vcolors is None:
        # No usable color info — fall back to mid-grey so the file is still valid.
        print("[export_color3mf] WARN: no vertex colors found; defaulting to grey")
        vcolors = np.tile(np.array([180, 180, 180, 255], np.uint8), (verts.shape[0], 1))

    # Normalize to Nx4 uint8 RGBA.
    vcolors = np.asarray(vcolors)
    if vcolors.dtype.kind == "f":
        # floats are 0..1
        vcolors = np.clip(np.round(vcolors * 255.0), 0, 255).astype(np.uint8)
    else:
        vcolors = vcolors.astype(np.uint8)
    if vcolors.shape[1] == 3:
        alpha = np.full((vcolors.shape[0], 1), 255, np.uint8)
        vcolors = np.hstack([vcolors, alpha])

    return verts, faces, vcolors


def export_color_3mf(verts, faces, vcolors, out_path):
    """Write a color 3MF using lib3mf. One ColorGroup, per-triangle corner colors."""
    wrapper = lib3mf.Wrapper()
    model = wrapper.CreateModel()
    mesh = model.AddMeshObject()
    mesh.SetName("colored_mesh")

    # --- geometry ---
    # AddVertex takes a Position whose .Coordinates is a length-3 float array.
    for v in verts:
        pos = lib3mf.Position()
        pos.Coordinates = (float(v[0]), float(v[1]), float(v[2]))
        mesh.AddVertex(pos)

    for f in faces:
        tri = lib3mf.Triangle()
        tri.Indices = (int(f[0]), int(f[1]), int(f[2]))
        mesh.AddTriangle(tri)

    # --- color group: deduplicate vertex colors -> one ColorGroup entry each ---
    color_group = model.AddColorGroup()
    # Map an (r,g,b,a) tuple -> the property index returned by AddColor.
    color_to_pid = {}
    vertex_pid = np.empty(len(vcolors), dtype=np.uint32)
    for i, c in enumerate(vcolors):
        key = (int(c[0]), int(c[1]), int(c[2]), int(c[3]))
        pid = color_to_pid.get(key)
        if pid is None:
            color = wrapper.RGBAToColor(key[0], key[1], key[2], key[3])
            pid = color_group.AddColor(color)  # returns the property id within the group
            color_to_pid[key] = pid
        vertex_pid[i] = pid

    group_res_id = color_group.GetResourceID()

    # --- per-triangle properties: each corner gets its vertex's color id ---
    for idx, f in enumerate(faces):
        props = lib3mf.TriangleProperties()
        props.ResourceID = group_res_id
        props.PropertyIDs = (
            int(vertex_pid[f[0]]),
            int(vertex_pid[f[1]]),
            int(vertex_pid[f[2]]),
        )
        mesh.SetTriangleProperties(idx, props)

    # Object-level default property (first color) so the object is never colorless
    # even if a slicer ignores per-triangle data.
    first_pid = int(vertex_pid[0])
    mesh.SetObjectLevelProperty(group_res_id, first_pid)

    # Add the mesh to the build with an identity transform, then write.
    model.AddBuildItem(mesh, wrapper.GetIdentityTransform())

    writer = model.QueryWriter("3mf")
    writer.WriteToFile(out_path)
    return len(color_to_pid)


def main():
    ap = argparse.ArgumentParser(description="Export a per-vertex-colored mesh to a color 3MF.")
    ap.add_argument("input", help="input colored mesh (PLY or GLB with vertex colors)")
    ap.add_argument("output", help="output .3mf path")
    a = ap.parse_args()

    if not os.path.isfile(a.input):
        print(f"[export_color3mf] FAILURE: input not found: {a.input}")
        sys.exit(1)

    try:
        verts, faces, vcolors = load_colored_mesh(a.input)
        n_unique = export_color_3mf(verts, faces, vcolors, a.output)
    except Exception as exc:  # noqa: BLE001
        print(f"[export_color3mf] FAILURE: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    print(
        f"[export_color3mf] SUCCESS: wrote {a.output} "
        f"({len(verts)} verts, {len(faces)} tris, {n_unique} distinct colors in 1 color group)"
    )


if __name__ == "__main__":
    main()
