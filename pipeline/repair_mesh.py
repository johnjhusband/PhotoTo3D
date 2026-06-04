#!/usr/bin/env python3
"""repair_mesh.py — turn a raw generated mesh into a watertight, printable mesh.

Generative meshes (TRELLIS) are many disconnected shells (hair/body/clothing) with holes — not
print-ready. PREFERRED method: CGAL 3D Alpha Wrapping (via the `alpha_wrap` binary) — produces a
guaranteed watertight, manifold, intersection-free mesh that PRESERVES thin protruding features
(capes/coats) instead of collapsing them the way voxel shrink-wrap does. FALLBACK (if the binary is
absent): voxel remesh.

After wrapping: keep largest blob, decimate to a printable budget, transfer color, export.

Usage: repair_mesh.py <input_mesh> <out_basename> [voxel_div_fallback] [target_tris]
Env:   ALPHA_WRAP_BIN (default /workspace/alpha_wrap), REL_ALPHA (default 150), REL_OFFSET (default 3000)
       Higher REL_ALPHA = finer carving = preserves thinner features (e.g. a cape).
Run with the env python that has trimesh+pymeshfix+scipy (e.g. /opt/conda/bin/python).
"""
import os, sys, subprocess, tempfile
import numpy as np
import trimesh


def watertight_alpha_wrap(m, awbin, rel_alpha, rel_offset):
    """Run the CGAL alpha_wrap binary on mesh m; return a watertight Trimesh, or None on failure."""
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "in.ply")
        dst = os.path.join(td, "out.ply")
        m.export(src)
        try:
            subprocess.run([awbin, src, dst, str(rel_alpha), str(rel_offset)],
                           check=True, timeout=600)
        except Exception as e:
            print(f"[repair] alpha_wrap failed ({e}); falling back to voxel remesh")
            return None
        w = trimesh.load(dst, process=True, force="mesh")
        return trimesh.Trimesh(vertices=np.asarray(w.vertices), faces=np.asarray(w.faces), process=True)


def watertight_voxel(m, voxel_div):
    pitch = float(m.extents.max()) / voxel_div
    print(f"[repair] voxel remesh fallback at pitch={pitch:.5f}")
    vg = m.voxelized(pitch=pitch).fill()
    s = vg.marching_cubes
    s = trimesh.Trimesh(vertices=np.asarray(s.vertices), faces=np.asarray(s.faces), process=True)
    trimesh.smoothing.filter_taubin(s, iterations=12)
    return s


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: repair_mesh.py <input_mesh> <out_basename> [voxel_div] [target_tris]")
    inp, base = sys.argv[1], sys.argv[2]
    voxel_div = float(sys.argv[3]) if len(sys.argv) > 3 else 192.0
    target = int(sys.argv[4]) if len(sys.argv) > 4 else 200_000
    awbin = os.environ.get("ALPHA_WRAP_BIN", "/workspace/alpha_wrap")
    rel_alpha = float(os.environ.get("REL_ALPHA", "150"))
    rel_offset = float(os.environ.get("REL_OFFSET", "3000"))

    print(f"[repair] loading {inp}")
    m = trimesh.load(inp, process=True, force="mesh")
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate([g for g in m.geometry.values()])
    print(f"[repair] loaded: {len(m.vertices)} v, {len(m.faces)} f, "
          f"{len(m.split(only_watertight=False))} components")

    # capture original color before remeshing (transferred back onto the solid afterward)
    src_pts = np.asarray(m.vertices)
    src_colors = None
    try:
        c = np.asarray(m.visual.to_color().vertex_colors)
        if c.shape[0] == src_pts.shape[0]:
            src_colors = c
    except Exception as e:
        print(f"[repair] no source color ({e})")
    print(f"[repair] source has color: {src_colors is not None}")

    # PREFERRED: alpha-wrap (detail-preserving). FALLBACK: voxel remesh.
    solid = None
    if os.path.exists(awbin):
        print(f"[repair] alpha-wrap (rel_alpha={rel_alpha}, rel_offset={rel_offset})")
        solid = watertight_alpha_wrap(m, awbin, rel_alpha, rel_offset)
    if solid is None:
        solid = watertight_voxel(m, voxel_div)
    print(f"[repair] watertight solid: {len(solid.vertices)} v, {len(solid.faces)} f")

    # keep the largest body (drop stray specks)
    parts = solid.split(only_watertight=False)
    if len(parts) > 1:
        solid = max(parts, key=lambda p: len(p.faces))
        print(f"[repair] kept largest of {len(parts)} blobs: {len(solid.faces)} f")

    # decimate to a printable budget
    if len(solid.faces) > target:
        print(f"[repair] decimating {len(solid.faces)} -> ~{target}")
        solid = solid.simplify_quadric_decimation(face_count=target)
        solid = trimesh.Trimesh(vertices=solid.vertices, faces=solid.faces, process=True)
    solid.fix_normals()

    # transfer color onto the solid (nearest source vertex)
    colored = False
    if src_colors is not None:
        from scipy.spatial import cKDTree
        _, idx = cKDTree(src_pts).query(np.asarray(solid.vertices))
        solid.visual.vertex_colors = src_colors[idx]
        colored = True
        print("[repair] transferred color onto solid")

    solid.export(f"{base}.stl")
    solid.export(f"{base}.3mf")
    if colored:
        solid.export(f"{base}_color.glb")
        solid.export(f"{base}_color.ply")
        print(f"[repair] wrote {base}_color.glb/.ply (with color)")
    print(f"[repair] FINAL watertight={solid.is_watertight} faces={len(solid.faces)} "
          f"volume={round(solid.volume, 4) if solid.is_watertight else 'n/a'}")


if __name__ == "__main__":
    main()
