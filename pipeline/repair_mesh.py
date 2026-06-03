#!/usr/bin/env python3
"""repair_mesh.py — turn a raw generated/photogrammetry mesh into a watertight, printable STL/3MF.

Generative meshes (TRELLIS) and photogrammetry meshes are NOT print-ready: they're often made of
many disconnected shells (hair, body, clothing as separate surfaces), with holes and self-intersections.
Picking the "largest component" is wrong — it discards most of the figure. The robust fix for printing
is to remesh ALL the occupied space into a single watertight solid (shrink-wrap), then clean it.

Steps:
  1. Load mesh (glb/ply/obj/stl); flatten a scene to one mesh.
  2. Voxel-remesh the whole thing -> one solid (fills interior, fuses all shells) -> watertight.
  3. Keep the largest connected blob of the REMESHED solid (now meaningful: drops stray voxel specks).
  4. Taubin smooth (removes voxel stair-stepping without shrinking).
  5. pymeshfix final pass + decimate to a printable triangle budget.
  6. Report watertightness; write STL + 3MF.

Usage: repair_mesh.py <input_mesh> <out_basename> [voxel_div] [target_tris]
  voxel_div  resolution = max_extent / voxel_div  (higher = finer; default 192)
Run with the env python that has trimesh+pymeshfix (e.g. /opt/conda/bin/python).
"""
import sys
import numpy as np
import trimesh
import pymeshfix


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: repair_mesh.py <input_mesh> <out_basename> [voxel_div] [target_tris]")
    inp, base = sys.argv[1], sys.argv[2]
    voxel_div = float(sys.argv[3]) if len(sys.argv) > 3 else 192.0
    target = int(sys.argv[4]) if len(sys.argv) > 4 else 200_000

    print(f"[repair] loading {inp}")
    m = trimesh.load(inp, process=True, force='mesh')
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate([g for g in m.geometry.values()])
    print(f"[repair] loaded: {len(m.vertices)} verts, {len(m.faces)} faces, "
          f"{len(m.split(only_watertight=False))} components")

    # Capture original color (from texture or vertex colors) BEFORE remeshing, so we can transfer
    # it back onto the watertight solid afterward — the voxel remesh itself is geometry-only.
    src_pts = np.asarray(m.vertices)
    src_colors = None
    try:
        src_colors = np.asarray(m.visual.to_color().vertex_colors)
        if src_colors.shape[0] != src_pts.shape[0]:
            src_colors = None
    except Exception as e:
        print(f"[repair] no source color ({e})")
    print(f"[repair] source has color: {src_colors is not None}")

    # 1. voxel remesh -> single solid that encloses ALL shells
    pitch = float(m.extents.max()) / voxel_div
    print(f"[repair] voxelizing at pitch={pitch:.5f} (~{voxel_div:.0f} per axis) and filling interior")
    vg = m.voxelized(pitch=pitch).fill()
    solid = vg.marching_cubes
    solid = trimesh.Trimesh(vertices=np.asarray(solid.vertices), faces=np.asarray(solid.faces),
                            process=True)
    print(f"[repair] remeshed solid: {len(solid.vertices)} verts, {len(solid.faces)} faces")

    # 2. keep largest blob (drops disconnected voxel specks); now the figure is one body
    parts = solid.split(only_watertight=False)
    if len(parts) > 1:
        solid = max(parts, key=lambda p: len(p.faces))
        print(f"[repair] kept largest of {len(parts)} remeshed blobs: {len(solid.faces)} faces")

    # 3. smooth away voxel stair-stepping (Taubin doesn't shrink like Laplacian)
    trimesh.smoothing.filter_taubin(solid, iterations=12)

    # 4. decimate to a printable budget FIRST (decimation can open the surface)
    if len(solid.faces) > target:
        print(f"[repair] decimating {len(solid.faces)} -> ~{target} faces")
        solid = solid.simplify_quadric_decimation(face_count=target)
        solid = trimesh.Trimesh(vertices=solid.vertices, faces=solid.faces, process=True)

    # 5. final watertight guarantee via pymeshfix (LAST, so decimation can't re-open it)
    verts = np.asarray(solid.vertices, dtype=np.float64)
    faces = np.asarray(solid.faces, dtype=np.int32)
    vclean, fclean = pymeshfix.clean_from_arrays(verts, faces)
    solid = trimesh.Trimesh(vertices=vclean, faces=fclean, process=True)
    solid.fix_normals()

    # Transfer original color onto the watertight solid (nearest source point per vertex).
    colored = False
    if src_colors is not None:
        from scipy.spatial import cKDTree
        _, idx = cKDTree(src_pts).query(np.asarray(solid.vertices))
        solid.visual.vertex_colors = src_colors[idx]
        colored = True
        print("[repair] transferred color onto watertight solid")

    stl, tmf = f"{base}.stl", f"{base}.3mf"
    solid.export(stl)   # geometry only (single-color printing / painting base)
    solid.export(tmf)
    print(f"[repair] wrote {stl} and {tmf}")
    if colored:
        # color-carrying formats (vertex colors): GLB + PLY for viewing / color workflows
        solid.export(f"{base}_color.glb")
        solid.export(f"{base}_color.ply")
        print(f"[repair] wrote {base}_color.glb and {base}_color.ply (with color)")
    print(f"[repair] FINAL watertight={solid.is_watertight} faces={len(solid.faces)} "
          f"volume={round(solid.volume,4) if solid.is_watertight else 'n/a'}")
    if not solid.is_watertight:
        print("[repair] WARNING: not fully watertight — raise voxel_div or touch up in Blender")


if __name__ == "__main__":
    main()
