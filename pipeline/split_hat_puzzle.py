#!/usr/bin/env python3
"""split_hat_puzzle.py — split the figurine into a 4-COLOR BODY + a STRAW HAT (5 colors total),
joined by a mortise-and-tenon cube (peg on the head crown into a socket in the hat underside).

Why 5 colors: a 4-filament printer does the BODY in 4 colors; the HAT prints separately in a 5th
(straw) and presses on. STL carries no color, so every output here is a color 3MF.

Pipeline (geometry first, color last — manifold booleans drop vertex color, so we re-transfer after):
  1. Load the 4-color GLB (clean discrete colors → robust hat detection) + the lifelike GLB (--color
     source for the body's true colors). Same geometry; scale both to TARGET_MM identically.
  2. Hat = highest SAME-COLOR connected component (the tan also paints the sandals, so a plain
     region-mean fails). Weld verts first (the 4-color GLB is vertex-exploded → no adjacency otherwise).
  3. BODY = rest → watertight (pymeshfix) → union a cube peg on the head crown → transfer lifelike color
     by nearest vertex (peg picks up the head color) → export body_colored.glb.
  4. HAT → watertight → subtract the socket cube (peg + clearance) → flat straw → export hat_straw.3mf.
Then run palette_quantize on body_colored.glb (N=4) to get body_4color.3mf. The hat 3MF is one color.

Usage: split_hat_puzzle.py <4color.glb> --color <lifelike.glb> <out_dir>
       [--mm 150] [--peg 10] [--clearance 0.3] [--prefix figurine] [--straw c9a86a]
"""
import os, sys, argparse
import numpy as np
import trimesh
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gpu"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_colored(path):
    m = trimesh.load(path, process=False)
    if isinstance(m, trimesh.Scene):
        m = m.to_geometry()
    vis = m.visual
    if isinstance(vis, trimesh.visual.TextureVisuals):
        vis = vis.to_color()
    vc = np.asarray(getattr(vis, "vertex_colors", np.empty((0, 4))))
    if vc.dtype.kind == "f":
        vc = np.clip(np.round(vc * 255), 0, 255).astype(np.uint8)
    if vc.size and vc.shape[1] == 3:
        vc = np.hstack([vc, np.full((len(vc), 1), 255, np.uint8)])
    return m, vc


def hat_mask(mesh, fcol):
    """Face mask of the hat = highest sizable same-color connected component."""
    uniq, inv = np.unique(fcol, axis=0, return_inverse=True)
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import connected_components
    adj = mesh.face_adjacency
    same = inv[adj[:, 0]] == inv[adj[:, 1]]
    nf = len(mesh.faces)
    e = adj[same]
    G = csr_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(nf, nf))
    ncomp, comp = connected_components(G, directed=False)
    sizes = np.bincount(comp, minlength=ncomp)
    fy = mesh.triangles_center[:, 1]
    big = np.where(sizes >= max(200, 0.01 * nf))[0]
    best = max(big, key=lambda c: fy[comp == c].mean())
    return comp == best


def watertight(part):
    import pymeshfix
    part.merge_vertices()
    v = np.asarray(part.vertices, np.float64)
    f = np.asarray(part.faces, np.int32)
    vc, fc = pymeshfix.clean_from_arrays(v, f)
    out = trimesh.Trimesh(vertices=vc, faces=fc, process=False)
    trimesh.repair.fix_normals(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="4-color GLB (hat detection)")
    ap.add_argument("out_dir")
    ap.add_argument("--color", required=True, help="lifelike colored GLB (body's true colors)")
    ap.add_argument("--mm", type=float, default=150.0)
    ap.add_argument("--peg", type=float, default=10.0)
    ap.add_argument("--clearance", type=float, default=0.3)
    ap.add_argument("--prefix", default="figurine")
    ap.add_argument("--straw", default="c9a86a", help="hat color hex")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)

    mesh, vc4 = load_colored(a.input)
    src, vcs = load_colored(a.color)
    # common scale to mm (both share geometry → same centroid/extent)
    center = mesh.bounding_box.centroid.copy()
    scale = a.mm / float(mesh.extents.max())
    for m in (mesh, src):
        m.apply_translation(-center); m.apply_scale(scale)

    fcol = vc4[mesh.faces][:, 0, :3]
    mesh.merge_vertices()
    mask = hat_mask(mesh, fcol)
    print(f"[hatsplit] hat {int(mask.sum())}/{len(mesh.faces)} faces", flush=True)

    # lifelike color lookup (mm frame)
    tree = cKDTree(src.vertices)
    straw = np.array([int(a.straw[i:i+2], 16) for i in (0, 2, 4)] + [255], np.uint8)

    # --- BODY: watertight, + peg, then color from lifelike ---
    body = watertight(mesh.submesh([np.where(~mask)[0]], append=True, repair=False))
    crown = body.vertices[body.vertices[:, 1] > body.vertices[:, 1].max() - max(2.0, a.peg)]
    cx, cz, top = crown[:, 0].mean(), crown[:, 2].mean(), body.vertices[:, 1].max()
    peg = trimesh.creation.box(extents=(a.peg, a.peg, a.peg))
    peg.apply_translation([cx, top, cz])
    try:
        body = trimesh.boolean.union([body, peg])
    except Exception as e:
        print(f"[hatsplit] peg union failed ({e}); body without peg", flush=True)
    _, idx = tree.query(body.vertices)
    body.visual.vertex_colors = vcs[idx]
    body.export(os.path.join(a.out_dir, f"{a.prefix}_body_colored.glb"))
    print(f"[hatsplit] body {len(body.faces)}f watertight={body.is_watertight} -> body_colored.glb", flush=True)

    # --- HAT: watertight, - socket, flat straw ---
    hat = watertight(mesh.submesh([np.where(mask)[0]], append=True, repair=False))
    hb = hat.vertices[:, 1].min()
    socket = trimesh.creation.box(extents=(a.peg + 2*a.clearance, a.peg + a.clearance, a.peg + 2*a.clearance))
    socket.apply_translation([cx, hb + a.peg/2.0, cz])
    try:
        hat = trimesh.boolean.difference([hat, socket])
    except Exception as e:
        print(f"[hatsplit] socket cut failed ({e}); hat without socket", flush=True)
    hat.visual.vertex_colors = np.tile(straw, (len(hat.vertices), 1))
    from export_color3mf import export_color_3mf
    hv = np.asarray(hat.vertices, np.float64); hf = np.asarray(hat.faces, np.int64)
    export_color_3mf(hv, hf, np.tile(straw, (len(hat.vertices), 1)), os.path.join(a.out_dir, f"{a.prefix}_hat_straw.3mf"))
    hat.export(os.path.join(a.out_dir, f"{a.prefix}_hat_colored.glb"))
    print(f"[hatsplit] hat {len(hat.faces)}f watertight={hat.is_watertight} -> hat_straw.3mf (#{a.straw})", flush=True)
    print(f"[hatsplit] DONE. Next: palette_quantize body_colored.glb -> body 4-color 3mf.", flush=True)


if __name__ == "__main__":
    main()
