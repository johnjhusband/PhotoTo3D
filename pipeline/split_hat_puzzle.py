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
    ap.add_argument("--peg", type=float, default=8.0, help="peg diameter (mm) when peg-mode=down")
    ap.add_argument("--peg-mode", dest="peg_mode", choices=["none", "down"], default="none",
                    help="none = hat just seats on the head (clean, nothing protrudes); "
                         "down = peg points DOWN from the hat into a head hole (internal lock)")
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

    hvidx = np.unique(mesh.faces[mask])
    cx, cz = mesh.vertices[hvidx, 0].mean(), mesh.vertices[hvidx, 2].mean()

    # --- BODY: watertight; optional DOWN-peg join ---
    body = watertight(mesh.submesh([np.where(~mask)[0]], append=True, repair=False))
    # PEG MODE (default 'none'): a conical hat sits ~FLUSH on the head, so a peg pointing UP from the head
    # punches through the thin cone and the socket cut notches the apex (the bug John caught). So:
    #   none = no peg; the hollow hat just seats on the head by its cone shape (clean, nothing protrudes).
    #   down = peg points DOWN from the hat into a HOLE in the head crown — internal, nothing pokes out.
    near = np.hypot(body.vertices[:, 0] - cx, body.vertices[:, 2] - cz) < max(a.peg * 2.5, 12)
    crown = body.vertices[near, 1].max() if near.any() else body.vertices[:, 1].max()
    if a.peg_mode == "down":
        # hole down into the head crown (slightly larger than the peg, for clearance)
        hole = trimesh.creation.cylinder(radius=a.peg/2 + a.clearance, height=a.peg*1.4, sections=24)
        hole.apply_translation([cx, crown - a.peg*0.5, cz])
        try:
            body = trimesh.boolean.difference([body, hole])
        except Exception as e:
            print(f"[hatsplit] head-hole cut failed ({e})", flush=True)
    _, idx = tree.query(body.vertices)
    body.visual.vertex_colors = vcs[idx]
    body.export(os.path.join(a.out_dir, f"{a.prefix}_body_colored.glb"))
    print(f"[hatsplit] body {len(body.faces)}f watertight={body.is_watertight} peg_mode={a.peg_mode} "
          f"-> body_colored.glb", flush=True)

    # --- HAT: watertight; optional DOWN-peg ---
    hat = watertight(mesh.submesh([np.where(mask)[0]], append=True, repair=False))
    if a.peg_mode == "down":
        hb = hat.vertices[:, 1].min()
        # peg hangs down from the hat's inner apex into the head hole (a bit shorter than the hole is deep)
        peg = trimesh.creation.cylinder(radius=a.peg/2, height=a.peg*1.2, sections=24)
        peg.apply_translation([cx, crown - a.peg*0.35, cz])
        try:
            hat = trimesh.boolean.union([hat, peg])
        except Exception as e:
            print(f"[hatsplit] hat-peg union failed ({e})", flush=True)
    hat.visual.vertex_colors = np.tile(straw, (len(hat.vertices), 1))
    from export_color3mf import export_color_3mf
    hv = np.asarray(hat.vertices, np.float64); hf = np.asarray(hat.faces, np.int64)
    export_color_3mf(hv, hf, np.tile(straw, (len(hat.vertices), 1)), os.path.join(a.out_dir, f"{a.prefix}_hat_straw.3mf"))
    hat.export(os.path.join(a.out_dir, f"{a.prefix}_hat_colored.glb"))
    print(f"[hatsplit] hat {len(hat.faces)}f watertight={hat.is_watertight} -> hat_straw.3mf (#{a.straw})", flush=True)
    print(f"[hatsplit] DONE. Next: palette_quantize body_colored.glb -> body 4-color 3mf.", flush=True)


if __name__ == "__main__":
    main()
