#!/usr/bin/env python3
"""palette_quantize.py — Stage 4: reduce a colored mesh to N FLAT color regions for an N-spool printer.

A multi-color FDM printer lays down only its N loaded filaments. TRELLIS output has a continuous
texture (hundreds of shades), so we cluster into exactly N groups and snap every surface to its group
color. The N filament colors are assigned in the slicer at print time — only the N REGIONS live here.

Fixes over the naive version (research 2026):
  - Cluster in **CIE-Lab** (perceptually uniform), not RGB — clean anime-palette separation.
  - Take color from the **albedo texture** sampled at vertex UVs, not trimesh `to_color()` (which
    mishandles multi-map PBR and muddies the palette).
  - Emit **flat per-face** regions by EXPLODING vertices (each triangle gets its own 3 vertices, all
    one palette color) → the color 3MF has NO barycentric bleed at region boundaries (the splotch fix).
  - Warn if two palette colors are within ΔE < 25 (visually indistinct → effectively fewer regions).

Usage: palette_quantize.py <colored_mesh> <out_base> [N]
Outputs: <base>_<N>color.glb/.ply (flat per-face), <base>_<N>color.3mf (clean N-region print file),
         <base>_part<i>_<hex>.stl (one per color, for separate-object multi-material loading)
Run with a python that has trimesh + scikit-learn + numpy.
"""
import os, sys
import numpy as np
import trimesh
from sklearn.cluster import KMeans

# export_color3mf lives in gpu/ in the repo, but may sit flat alongside this on the box — try both.
_here = os.path.dirname(os.path.abspath(__file__))
for _p in (_here, os.path.join(_here, "..", "gpu"), "/workspace", "/workspace/gpu"):
    if os.path.isdir(_p):
        sys.path.insert(0, _p)


def srgb_to_lab(rgb):
    """rgb uint8/float 0..255 (Nx3) -> CIE-Lab (Nx3), D65."""
    c = np.asarray(rgb, float) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805],
                  [0.2126, 0.7152, 0.0722],
                  [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16.0 / 116.0)
    return np.stack([116 * f[:, 1] - 16,
                     500 * (f[:, 0] - f[:, 1]),
                     200 * (f[:, 1] - f[:, 2])], 1)


def vertex_colors_from_texture(m):
    """Per-vertex RGB by sampling the albedo texture at each vertex UV; fall back to vertex colors.
    trimesh to_color() mishandles multi-map PBR (muddies the palette), so we sample directly."""
    vis = getattr(m, "visual", None)
    try:
        if isinstance(vis, trimesh.visual.TextureVisuals) and vis.uv is not None and vis.material is not None:
            mat = vis.material
            img = getattr(mat, "baseColorTexture", None) or getattr(mat, "image", None)
            if img is not None:
                tex = np.asarray(img.convert("RGB"))
                h, w = tex.shape[:2]
                uv = np.asarray(vis.uv, float)
                px = np.clip((uv[:, 0] % 1.0 * (w - 1)).astype(int), 0, w - 1)
                py = np.clip(((1.0 - uv[:, 1] % 1.0) * (h - 1)).astype(int), 0, h - 1)
                rgb = tex[py, px]
                if rgb.shape[0] == len(m.vertices):
                    return rgb.astype(float)
    except Exception as e:
        print(f"[palette] texture sampling failed ({e}); falling back")
    try:
        vc = np.asarray(vis.to_color().vertex_colors)[:, :3].astype(float)
        if vc.shape[0] == len(m.vertices):
            return vc
    except Exception:
        pass
    return np.asarray(vis.vertex_colors)[:, :3].astype(float)


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: palette_quantize.py <colored_mesh> <out_base> [N]")
    inp, base = sys.argv[1], sys.argv[2]
    N = int(sys.argv[3]) if len(sys.argv) > 3 else 4

    m = trimesh.load(inp, process=False, force="mesh")
    if isinstance(m, trimesh.Scene):
        m = m.to_geometry()
    vc = vertex_colors_from_texture(m)
    # COLOR PRE-SMOOTHING (the speckle fix): blur per-vertex colors over the mesh surface BEFORE
    # clustering so the texture's patchy artifacts average into coherent zones → contiguous print
    # regions instead of speckle. Far more effective than post-quantization label smoothing alone.
    csm = int(os.environ.get("COLORSMOOTH", "12"))
    if csm > 0:
        from scipy.sparse import coo_matrix
        e = m.edges_unique
        nv = len(m.vertices)
        A = coo_matrix((np.ones(len(e) * 2),
                        (np.concatenate([e[:, 0], e[:, 1]]),
                         np.concatenate([e[:, 1], e[:, 0]]))), shape=(nv, nv)).tocsr()
        deg = np.asarray(A.sum(1)).ravel(); deg[deg == 0] = 1
        for _ in range(csm):
            vc = 0.5 * vc + 0.5 * (A.dot(vc) / deg[:, None])
        print(f"[palette] color pre-smoothing: {csm} Laplacian iters")
    # LWEIGHT downweights Lab lightness before clustering so lit+shadowed parts of the SAME material
    # (TRELLIS bakes lighting into the texture) cluster together by HUE/CHROMA → regions = materials,
    # not light/shadow. 1.0 = standard Lab; ~0.3 = mostly chroma. Env LWEIGHT (default 0.35).
    lw = float(os.environ.get("LWEIGHT", "0.35"))
    print(f"[palette] {len(vc)} vertices -> {N} flat regions (Lab k-means, L-weight={lw})")

    # cluster in Lab with lightness downweighted; representative color = MEDIAN rgb (robust)
    lab = srgb_to_lab(vc)
    labw = lab.copy(); labw[:, 0] *= lw
    km = KMeans(n_clusters=N, n_init=10, random_state=0).fit(labw)
    labels = km.labels_
    centroids = np.array([np.median(vc[labels == i], axis=0) if np.any(labels == i)
                          else [128, 128, 128] for i in range(N)])
    centroids = np.clip(np.round(centroids), 0, 255).astype(np.uint8)
    counts = np.bincount(labels, minlength=N)
    print(f"[palette] regions (rgb, #verts): "
          f"{[(tuple(int(x) for x in centroids[i]), int(counts[i])) for i in range(N)]}")

    # ΔE distinctness check (Lab euclidean ~= ΔE76)
    clab = srgb_to_lab(centroids)
    for i in range(N):
        for j in range(i + 1, N):
            de = float(np.linalg.norm(clab[i] - clab[j]))
            if de < 25:
                print(f"[palette] WARN: regions {i} (#{'%02x%02x%02x' % tuple(centroids[i])}) and "
                      f"{j} (#{'%02x%02x%02x' % tuple(centroids[j])}) are ΔE={de:.1f} (<25) — "
                      f"visually similar; effective regions < {N}")

    # per-FACE label = majority vote of the face's 3 vertices
    faces = np.asarray(m.faces)
    flab = np.array([np.bincount(labels[f], minlength=N).argmax() for f in faces])

    # SPATIAL CLEANUP: the texture has per-face noise that quantizes into SPECKLES (brown spots on a
    # white coat). Smooth the per-face labels by neighbor-majority voting over the face-adjacency graph
    # so each material becomes one CONTIGUOUS region (what a multi-color print needs). Env SMOOTH_PASSES.
    passes = int(os.environ.get("SMOOTH_PASSES", "6"))
    if passes > 0:
        adj = m.face_adjacency  # Kx2 pairs of touching faces
        from scipy.sparse import coo_matrix
        nf = len(faces)
        A = coo_matrix((np.ones(len(adj) * 2),
                        (np.concatenate([adj[:, 0], adj[:, 1]]),
                         np.concatenate([adj[:, 1], adj[:, 0]]))), shape=(nf, nf)).tocsr()
        for _ in range(passes):
            # for each face, tally neighbor labels (+ itself) and take the majority
            onehot = np.zeros((nf, N))
            onehot[np.arange(nf), flab] = 1.0
            votes = A.dot(onehot) + onehot   # neighbors + self
            flab = votes.argmax(1)
        print(f"[palette] spatial label smoothing: {passes} neighbor-majority passes")

    # EXPLODE: each triangle gets its own 3 vertices, all one flat palette color -> no bleed
    tri_verts = np.asarray(m.vertices)[faces].reshape(-1, 3)
    tri_faces = np.arange(len(tri_verts)).reshape(-1, 3)
    face_rgb = centroids[flab]                              # Mx3
    corner_rgba = np.empty((len(tri_verts), 4), np.uint8)
    corner_rgba[:, :3] = np.repeat(face_rgb, 3, axis=0)
    corner_rgba[:, 3] = 255

    flat = trimesh.Trimesh(vertices=tri_verts, faces=tri_faces, process=False)
    flat.visual.vertex_colors = corner_rgba
    flat.export(f"{base}_{N}color.glb")
    flat.export(f"{base}_{N}color.ply")
    print(f"[palette] wrote flat per-face {base}_{N}color.glb/.ply")

    # clean N-region color 3MF (flat corners -> no barycentric interpolation)
    try:
        from export_color3mf import export_color_3mf
        n = export_color_3mf(tri_verts.astype(np.float64), tri_faces.astype(np.int64),
                             corner_rgba, f"{base}_{N}color.3mf")
        print(f"[palette] wrote {base}_{N}color.3mf ({n} distinct colors)")
    except Exception as e:
        print(f"[palette] color-3MF skipped ({e})")

    # one STL per color region (shared-vertex, for separate-object multi-material loading)
    for i in range(N):
        fi = faces[flab == i]
        if len(fi) == 0:
            continue
        part = trimesh.Trimesh(vertices=np.asarray(m.vertices).copy(), faces=fi, process=True)
        part.remove_unreferenced_vertices()
        hexc = "%02x%02x%02x" % tuple(int(x) for x in centroids[i])
        part.export(f"{base}_part{i}_{hexc}.stl")
        print(f"[palette] region {i} #{hexc}: {len(fi)} faces -> {base}_part{i}_{hexc}.stl")


if __name__ == "__main__":
    main()
