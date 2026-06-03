#!/usr/bin/env python3
"""palette_quantize.py — Stage 4: reduce a colored mesh to N flat colors for an N-spool printer.

A multi-color FDM printer can only lay down its N loaded filaments. TRELLIS output has a continuous
texture (hundreds of shades), so we cluster the colors into exactly N groups (k-means) and snap every
surface to its group's color. Output is both a single N-color mesh (for viewing) and one STL per color
(for assigning to filaments / multi-material slicing).

Usage: palette_quantize.py <colored_mesh> <out_base> [N]
Outputs: <base>_<N>color.glb/.ply  and  <base>_part<i>_<hex>.stl (one per color)
Run with a python that has trimesh + scipy (e.g. /opt/conda/bin/python).
"""
import sys
import numpy as np
import trimesh
from scipy.cluster.vq import kmeans2


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: palette_quantize.py <colored_mesh> <out_base> [N]")
    inp, base = sys.argv[1], sys.argv[2]
    N = int(sys.argv[3]) if len(sys.argv) > 3 else 4

    m = trimesh.load(inp, process=False, force="mesh")
    try:
        vc = np.asarray(m.visual.to_color().vertex_colors)[:, :3].astype(float)
    except Exception:
        vc = np.asarray(m.visual.vertex_colors)[:, :3].astype(float)
    print(f"[palette] {len(vc)} vertices -> {N} colors")

    np.random.seed(0)
    centroids, labels = kmeans2(vc, N, minit="++", missing="warn")
    centroids = np.clip(np.round(centroids), 0, 255).astype(np.uint8)
    counts = np.bincount(labels, minlength=N)
    palette = [(tuple(int(x) for x in centroids[i]), int(counts[i])) for i in range(N)]
    print(f"[palette] colors (rgb, #verts): {palette}")

    # single N-color mesh
    qcolors = np.full((len(vc), 4), 255, np.uint8)
    qcolors[:, :3] = centroids[labels]
    mq = m.copy()
    mq.visual.vertex_colors = qcolors
    mq.export(f"{base}_{N}color.glb")
    mq.export(f"{base}_{N}color.ply")
    print(f"[palette] wrote {base}_{N}color.glb/.ply")

    # split into one STL per color (face -> majority vertex color)
    faces = m.faces
    flab = np.array([np.bincount(labels[f], minlength=N).argmax() for f in faces])
    for i in range(N):
        fi = faces[flab == i]
        if len(fi) == 0:
            continue
        part = trimesh.Trimesh(vertices=m.vertices.copy(), faces=fi, process=True)
        part.remove_unreferenced_vertices()
        hexc = "%02x%02x%02x" % tuple(int(x) for x in centroids[i])
        part.export(f"{base}_part{i}_{hexc}.stl")
        print(f"[palette] part {i} color #{hexc}: {len(fi)} faces -> {base}_part{i}_{hexc}.stl")


if __name__ == "__main__":
    main()
