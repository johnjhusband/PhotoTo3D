#!/usr/bin/env python3
"""repair_mesh.py — turn a raw generated mesh into a watertight, printable COLOR 3MF.

Deliverable is a color 3MF (DECISIONS #19: STL dropped — it carries no color; 3MF is the
multi-color printing standard). Color is written via lib3mf (export_color3mf), not trimesh.


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


def sample_albedo_colors(m):
    """Per-vertex RGBA by sampling the albedo texture at each vertex UV. Falls back to vertex_colors,
    then to trimesh to_color(). Returns Nx4 uint8 aligned to m.vertices, or None."""
    import PIL.Image
    vis = getattr(m, "visual", None)
    try:
        if isinstance(vis, trimesh.visual.TextureVisuals) and vis.uv is not None and vis.material is not None:
            mat = vis.material
            img = getattr(mat, "baseColorTexture", None)
            if img is None:
                img = getattr(mat, "image", None)
            if img is not None:
                tex = np.asarray(img.convert("RGB"))
                h, w = tex.shape[:2]
                uv = np.asarray(vis.uv, dtype=float)
                px = np.clip((uv[:, 0] % 1.0 * (w - 1)).astype(int), 0, w - 1)
                py = np.clip(((1.0 - uv[:, 1] % 1.0) * (h - 1)).astype(int), 0, h - 1)
                rgb = tex[py, px]
                out = np.full((len(rgb), 4), 255, np.uint8)
                out[:, :3] = rgb
                if out.shape[0] == len(m.vertices):
                    return out
    except Exception as e:
        print(f"[repair] albedo-UV sampling failed ({e}); falling back")
    # fallbacks
    try:
        vc = np.asarray(vis.vertex_colors)
        if vc.shape[0] == len(m.vertices):
            return vc
    except Exception:
        pass
    try:
        vc = np.asarray(vis.to_color().vertex_colors)
        if vc.shape[0] == len(m.vertices):
            return vc
    except Exception:
        return None
    return None


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
    # NOTE: do NOT call m.split() here just to count components — on a generative mesh with thousands
    # of disconnected shells it is pathologically slow + memory-heavy (observed 54GB/3min hang). The
    # alpha-wrap step doesn't need it; the only split we need is on the watertight result (1 shell).
    print(f"[repair] loaded: {len(m.vertices)} v, {len(m.faces)} f")

    # capture original color before remeshing (transferred back onto the solid afterward).
    # For a textured/PBR mesh, sample the ALBEDO (baseColorTexture) at each vertex's UV — trimesh's
    # to_color() mishandles multi-map PBR materials (returns dark/wrong color -> magenta artifacts).
    src_pts = np.asarray(m.vertices)
    src_colors = sample_albedo_colors(m)
    print(f"[repair] source has color: {src_colors is not None}"
          + (f" (mean {np.asarray(src_colors)[:, :3].mean(0).round(0).tolist()})" if src_colors is not None else ""))

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

    # Deliverable = COLOR 3MF (DECISIONS #19: drop STL — it carries no color; 3MF is the
    # multi-color printing standard). Color is written via lib3mf (trimesh's 3MF has no color).
    if colored:
        solid.export(f"{base}_color.glb")   # for viewing in F3D
        solid.export(f"{base}_color.ply")
        try:
            from export_color3mf import export_color_3mf  # same dir on the box
            vc = np.asarray(solid.visual.vertex_colors)
            n = export_color_3mf(np.asarray(solid.vertices), np.asarray(solid.faces), vc, f"{base}.3mf")
            print(f"[repair] wrote COLOR 3MF {base}.3mf ({n} colors) + {base}_color.glb/.ply")
        except Exception as e:
            print(f"[repair] color-3MF failed ({e}); colorless 3MF fallback")
            solid.export(f"{base}.3mf")
    else:
        solid.export(f"{base}.3mf")  # geometry-only when the source had no color
    print(f"[repair] FINAL watertight={solid.is_watertight} faces={len(solid.faces)} "
          f"volume={round(solid.volume, 4) if solid.is_watertight else 'n/a'}")


if __name__ == "__main__":
    main()
