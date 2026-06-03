#!/usr/bin/env python3
"""repair_mesh.py — turn a raw photogrammetry mesh into a watertight, printable STL/3MF.

Photogrammetry output (OpenMVS .ply) is almost never print-ready: it has holes,
non-manifold edges, floating islands, and isn't a closed solid. This step fixes that.

Steps:
  1. Load mesh (ply/obj).
  2. Keep only the largest connected component (drop floating noise islands).
  3. pymeshfix: remove self-intersections, fill holes -> watertight manifold.
  4. Optional decimation to a target triangle count (printers don't need millions).
  5. Report watertightness + write STL and 3MF.

Usage: repair_mesh.py <input_mesh> <out_basename> [target_tris]
Run with: /opt/meshenv/bin/python repair_mesh.py ...
"""
import sys
import numpy as np
import trimesh
import pymeshfix


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: repair_mesh.py <input_mesh> <out_basename> [target_tris]")
    inp, base = sys.argv[1], sys.argv[2]
    target = int(sys.argv[3]) if len(sys.argv) > 3 else 300_000

    print(f"[repair] loading {inp}")
    m = trimesh.load(inp, process=True)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate([g for g in m.geometry.values()])
    print(f"[repair] loaded: {len(m.vertices)} verts, {len(m.faces)} faces")

    # 1. drop floating islands — keep the biggest body
    parts = m.split(only_watertight=False)
    if len(parts) > 1:
        m = max(parts, key=lambda p: len(p.faces))
        print(f"[repair] kept largest of {len(parts)} components: {len(m.faces)} faces")

    # 2. watertight repair (hole fill + self-intersection removal)
    print("[repair] pymeshfix: filling holes, fixing manifold...")
    verts = np.asarray(m.vertices, dtype=np.float64)
    faces = np.asarray(m.faces, dtype=np.int32)
    vclean, fclean = pymeshfix.clean_from_arrays(verts, faces)
    m = trimesh.Trimesh(vertices=vclean, faces=fclean, process=True)
    print(f"[repair] after fix: {len(m.vertices)} verts, {len(m.faces)} faces, "
          f"watertight={m.is_watertight}")

    # 3. decimate if huge (keeps print slicers happy)
    if len(m.faces) > target:
        print(f"[repair] decimating {len(m.faces)} -> ~{target} faces")
        m = m.simplify_quadric_decimation(face_count=target)
        m = trimesh.Trimesh(vertices=m.vertices, faces=m.faces, process=True)

    # 4. fix normals/winding for printing
    m.fix_normals()

    stl, tmf = f"{base}.stl", f"{base}.3mf"
    m.export(stl)
    m.export(tmf)
    print(f"[repair] wrote {stl} and {tmf}")
    print(f"[repair] FINAL watertight={m.is_watertight} "
          f"volume={'n/a' if not m.is_watertight else round(m.volume,2)} "
          f"faces={len(m.faces)}")
    if not m.is_watertight:
        print("[repair] WARNING: mesh not fully watertight — may need manual touch-up in Blender")


if __name__ == "__main__":
    main()
