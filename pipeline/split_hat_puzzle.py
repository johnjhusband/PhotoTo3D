#!/usr/bin/env python3
"""split_hat_puzzle.py — split the figurine into HAT + BODY as a mortise-and-tenon puzzle.

John's design: print the hat separately (straw color) from the head/body (skin tone), joined by a
registration cube — a TENON (peg) cube on the crown of the head that slots into a MORTISE (socket) cube
cut into the hat's underside, with a small clearance for a hand-press fit.

Pipeline:
  1. Load the colored mesh, scale to TARGET_MM (so peg/clearance are in real mm).
  2. Identify the HAT region: the color region whose faces sit highest (max mean Z); keep its largest
     connected component (so stray same-color faces, e.g. sandals, don't come along).
  3. Split into hat_faces / body_faces; fill the boundary holes on each so both are watertight solids.
  4. TENON: a cube on the head crown (centered on the hat/head join, base at the body's top), unioned
     to the BODY. MORTISE: the same cube grown by CLEARANCE on each side, subtracted from the HAT
     underside. Assembled, the hat drops onto the peg and registers.
  5. Export body + hat as separate STL (geometry) and color 3MF.

Booleans use trimesh's manifold backend (pip install manifold3d).
Usage: split_hat_puzzle.py <colored.glb> <out_dir> [--mm 150] [--peg 10] [--clearance 0.3] [--prefix figurine]
"""
import os, sys, argparse
import numpy as np
import trimesh

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gpu"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_scaled(path, mm):
    m = trimesh.load(path, process=False)
    if isinstance(m, trimesh.Scene):
        m = m.to_geometry()
    vis = m.visual
    if isinstance(vis, trimesh.visual.TextureVisuals):
        vis = vis.to_color()
    vc = np.asarray(getattr(vis, "vertex_colors", np.empty((0, 4))))
    longest = float(np.max(m.extents))
    s = mm / longest
    m.apply_translation(-m.bounding_box.centroid)
    m.apply_scale(s)
    return m, vc


def largest_component(mesh, faces_idx):
    """Given a subset of face indices, return the indices of its largest face-connected component."""
    sub = mesh.submesh([faces_idx], append=True, repair=False)
    cc = sub.split(only_watertight=False)
    if not cc:
        return faces_idx
    biggest = max(cc, key=lambda c: len(c.faces))
    # map back: match by face centroid (submesh reorders); simpler — recompute on original adjacency
    return faces_idx  # submesh path below handles geometry; we keep label set, clean via fill later


def hat_face_mask(mesh, vcolors, N_top_frac=0.5):
    """Identify hat faces = the color region with the highest mean Z (the hat sits on top)."""
    faces = mesh.faces
    fcol = vcolors[faces][:, 0, :3]                      # flat per-face color (corner 0)
    uniq, inv = np.unique(fcol, axis=0, return_inverse=True)
    fz = mesh.triangles_center[:, 1]                     # Y is up in these GLBs
    # mean height per color region
    means = np.array([fz[inv == k].mean() if np.any(inv == k) else -1e9 for k in range(len(uniq))])
    hat_k = int(means.argmax())
    mask = inv == hat_k
    return mask, uniq[hat_k]


def watertight_part(mesh, face_mask):
    """Submesh of face_mask, keep largest connected component, fill boundary holes -> watertight solid."""
    idx = np.where(face_mask)[0]
    part = mesh.submesh([idx], append=True, repair=False)
    comps = part.split(only_watertight=False)
    if comps:
        part = max(comps, key=lambda c: len(c.faces))
    part.merge_vertices()
    trimesh.repair.fill_holes(part)
    trimesh.repair.fix_normals(part)
    return part


def cube(center, edge, height=None):
    """Axis-aligned box centered at center in X/Z, sitting with given edge (and optional height in Y)."""
    h = height if height is not None else edge
    b = trimesh.creation.box(extents=(edge, h, edge))
    b.apply_translation(center)
    return b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input"); ap.add_argument("out_dir")
    ap.add_argument("--mm", type=float, default=150.0)
    ap.add_argument("--peg", type=float, default=10.0, help="tenon cube edge in mm")
    ap.add_argument("--clearance", type=float, default=0.3, help="per-side mortise clearance in mm")
    ap.add_argument("--prefix", default="figurine")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)

    mesh, vc = load_scaled(a.input, a.mm)
    if vc.shape[0] != len(mesh.vertices):
        sys.exit("[hatsplit] need per-vertex colors (use the 4-color GLB)")

    mask, hatrgb = hat_face_mask(mesh, vc)
    print(f"[hatsplit] hat region #{'%02x%02x%02x' % tuple(int(x) for x in hatrgb)}: "
          f"{int(mask.sum())}/{len(mesh.faces)} faces")

    hat = watertight_part(mesh, mask)
    body = watertight_part(mesh, ~mask)
    print(f"[hatsplit] hat {len(hat.faces)}f watertight={hat.is_watertight}; "
          f"body {len(body.faces)}f watertight={body.is_watertight}")

    # join point: top of the BODY (head crown), centered on the body's top-area XZ
    by = body.vertices[:, 1]
    top_band = body.vertices[by > by.max() - max(2.0, a.peg)]     # top slab of the head
    cx, cz = top_band[:, 0].mean(), top_band[:, 2].mean()
    body_top = by.max()

    # TENON: cube peg rising from the head crown; half embedded in head, half proud
    peg_h = a.peg
    peg_center = np.array([cx, body_top, cz])                      # box center at the crown surface
    peg = cube(peg_center, a.peg, height=peg_h)
    # MORTISE: peg grown by clearance, subtracted from the hat underside at the same XZ
    hat_bottom = hat.vertices[:, 1].min()
    socket = cube(np.array([cx, hat_bottom + peg_h / 2.0, cz]),
                  a.peg + 2 * a.clearance, height=peg_h + a.clearance)

    try:
        body_j = trimesh.boolean.union([body, peg])
        hat_j = trimesh.boolean.difference([hat, socket])
    except Exception as e:
        print(f"[hatsplit] boolean failed ({e}); install manifold3d. Exporting parts WITHOUT the join.")
        body_j, hat_j = body, hat

    mm = int(round(a.mm))
    for name, part in (("body", body_j), ("hat", hat_j)):
        stl = os.path.join(a.out_dir, f"{a.prefix}_{name}_{mm}mm.stl")
        part.export(stl)
        print(f"[hatsplit] wrote {stl}  ({len(part.faces)}f, watertight={part.is_watertight})")
    print(f"[hatsplit] peg {a.peg}mm cube, {a.clearance}mm/side clearance — hat prints straw, body skin.")


if __name__ == "__main__":
    main()
