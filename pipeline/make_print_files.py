#!/usr/bin/env python3
"""make_print_files.py — turn the final 4-color GLB into a complete, scaled PRINT SET.

This is the single reproducible step that produces everything in `FINAL/print_files/`
from the pipeline's `print_4color_4color.glb` (the per-region-colored mesh out of
`palette_quantize.py`). Before this script the scaling + STL + 3MF + per-material split
were ad-hoc shell steps; now it is one command so the repo reproduces the print files.

What it writes (into <out_dir>, all scaled so the longest extent == TARGET_MM):
  <prefix>_<MM>mm.stl              single watertight geometry STL (no color)
  <prefix>_4color_<MM>mm.3mf       color 3MF (slicer opens in color; lib3mf writer)
  material<k>_<hex>_<MM>mm.stl     one STL per distinct color region (k = 1..N)

Why scale here: the pipeline mesh is normalized (~2 units tall). Printers want mm, so we
scale the longest bounding-box extent to TARGET_MM (default 150) and bake it into every
exported file. STL carries geometry only (no color); the 3MF carries the N color regions;
the per-material STLs let a single-extruder workflow print each color separately.

Usage:
  python make_print_files.py <print_4color.glb> <out_dir> [--prefix figurine] [--mm 150]
                             [--geometry printable_color.glb]

--geometry: the WATERTIGHT colored mesh (printable_color.glb) to use for the single
geometry STL. The 4-color mesh is vertex-exploded by palette_quantize (non-manifold by
vertex identity), so its STL reports watertight=False; the repaired mesh is the clean
geometry. Both are scaled by the SAME factor (computed from the geometry mesh) so they
register. If omitted, the STL falls back to the 4-color mesh.
"""
import os
import sys
import argparse

import numpy as np
import trimesh

# reuse the lib3mf color writer (lives in gpu/)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gpu"))
from export_color3mf import export_face_color_3mf  # noqa: E402


def load_mesh_with_colors(path):
    """Load `path` to a single Trimesh with per-vertex RGBA uint8 colors."""
    loaded = trimesh.load(path, process=False)
    if isinstance(loaded, trimesh.Scene):
        if len(loaded.geometry) == 0:
            raise ValueError(f"{path}: no geometry")
        mesh = loaded.to_geometry() if hasattr(loaded, "to_geometry") else \
            loaded.dump(concatenate=True)
    else:
        mesh = loaded
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError(f"{path}: not a single mesh ({type(mesh)})")

    visual = mesh.visual
    if isinstance(visual, trimesh.visual.TextureVisuals):
        visual = visual.to_color()
    vc = np.asarray(getattr(visual, "vertex_colors", np.empty((0, 4))))
    if vc.shape[0] != len(mesh.vertices) or vc.size == 0:
        raise ValueError(f"{path}: expected per-vertex colors (got shape {vc.shape}); "
                         "this script wants the 4-color GLB from palette_quantize.py")
    if vc.dtype.kind == "f":
        vc = np.clip(np.round(vc * 255.0), 0, 255).astype(np.uint8)
    else:
        vc = vc.astype(np.uint8)
    if vc.shape[1] == 3:
        vc = np.hstack([vc, np.full((vc.shape[0], 1), 255, np.uint8)])
    return mesh, vc


def main():
    ap = argparse.ArgumentParser(description="Build the scaled print set from the 4-color GLB.")
    ap.add_argument("input", help="4-color GLB (print_4color_4color.glb from palette_quantize.py)")
    ap.add_argument("out_dir", help="output directory for the print files")
    ap.add_argument("--prefix", default="figurine", help="filename prefix (default figurine)")
    ap.add_argument("--mm", type=float, default=150.0, help="longest extent in mm (default 150)")
    ap.add_argument("--geometry", default=None,
                    help="watertight colored mesh (printable_color.glb) for the geometry STL")
    a = ap.parse_args()

    if not os.path.isfile(a.input):
        print(f"[print] FAILURE: input not found: {a.input}")
        sys.exit(1)
    os.makedirs(a.out_dir, exist_ok=True)

    mesh, vcolors = load_mesh_with_colors(a.input)

    # --- scale factor: longest extent of the GEOMETRY mesh -> TARGET_MM ---
    # Use the watertight geometry mesh to set the scale so both meshes register; the
    # 4-color mesh shares the same geometry/bbox so the same factor fits it.
    geom = None
    if a.geometry and os.path.isfile(a.geometry):
        geom, _ = load_mesh_with_colors(a.geometry)
        longest = float(np.max(geom.extents))
    else:
        if a.geometry:
            print(f"[print] WARN: --geometry {a.geometry} not found; STL from 4-color mesh")
        longest = float(np.max(mesh.extents))
    if longest <= 0:
        print("[print] FAILURE: degenerate mesh (zero extent)")
        sys.exit(1)
    scale = a.mm / longest
    mm = int(round(a.mm))

    # apply the same scale (and self-centering) to whichever meshes we export
    mesh.apply_translation(-mesh.bounding_box.centroid)
    mesh.apply_scale(scale)
    print(f"[print] scaled x{scale:.4f}: 4-color extents {np.round(mesh.extents, 2)} mm "
          f"({len(mesh.vertices)} v / {len(mesh.faces)} tris)")

    # --- welded color 3MF (the only deliverable; STLs dropped — no color, and Bambu wants 3MF).
    # The input 4-color GLB is vertex-EXPLODED; merge_vertices welds it back to a manifold so the 3MF
    # is one watertight solid (not floating-region soup), with one flat color per triangle.
    face_rgb = vcolors[mesh.faces][:, 0, :3]             # per-face color (corner 0; flat after quantize)
    mesh.merge_vertices()
    mf_path = os.path.join(a.out_dir, f"{a.prefix}_4color_{mm}mm.3mf")
    n_colors = export_face_color_3mf(np.asarray(mesh.vertices, np.float64),
                                     np.asarray(mesh.faces, np.int64), face_rgb, mf_path)
    print(f"[print] wrote {mf_path}  ({n_colors} colors, welded {len(mesh.vertices)}v/{len(mesh.faces)}f, "
          f"watertight={mesh.is_watertight})")
    print(f"[print] SUCCESS at {mm} mm")


if __name__ == "__main__":
    main()
