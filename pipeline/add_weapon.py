#!/usr/bin/env python3
"""add_weapon.py — graft a procedural STAFF/SPEAR onto the figure (image->3D drops the thin shaft).

The character grips a polearm (OIP1/OIP2). Hunyuan reconstructs the gripping fist but not the thin pole,
so we model it: a dark cylinder shaft threaded through the fist and planted on the ground + a cone
spearhead on top, unioned to the figure. Colored dark so it joins the dark-clothing region (no 5th body
color). Booleans (manifold3d) drop vertex color, so we re-transfer color afterward (cKDTree): figure
verts keep their color, staff verts go dark.

Usage: add_weapon.py <figure_color.glb> <out.glb> --fist X,Y,Z [--radius 0.05] [--head 0.16] [--top 0.18]
"""
import sys, argparse
import numpy as np
import trimesh
from scipy.spatial import cKDTree


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input"); ap.add_argument("out")
    ap.add_argument("--fist", required=True, help="gripping-hand centroid 'x,y,z' (mesh units)")
    ap.add_argument("--radius", type=float, default=0.05)
    ap.add_argument("--head", type=float, default=0.16, help="spearhead length")
    ap.add_argument("--top", type=float, default=0.18, help="how far above the head the shaft rises")
    ap.add_argument("--dark", default="191512", help="staff color hex")
    a = ap.parse_args()
    fx, fy, fz = [float(x) for x in a.fist.split(",")]

    fig = trimesh.load(a.input, process=False)
    if hasattr(fig, "to_geometry"):
        fig = fig.to_geometry()
    ovc = np.asarray(fig.visual.vertex_colors)[:, :4].copy()
    ov = np.asarray(fig.vertices).copy()
    ymin, ymax = ov[:, 1].min(), ov[:, 1].max()
    shaft_top = ymax + a.top
    h = shaft_top - ymin
    rot = trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])  # cylinder Z-axis -> Y

    shaft = trimesh.creation.cylinder(radius=a.radius, height=h, sections=28)
    shaft.apply_transform(rot)
    shaft.apply_translation([fx, ymin + h / 2.0, fz])

    head = trimesh.creation.cone(radius=a.radius * 2.3, height=a.head, sections=28)
    head.apply_transform(rot)
    head.apply_translation([fx, shaft_top, fz])  # cone base sits at shaft top, points up

    staff = trimesh.boolean.union([shaft, head])
    combined = trimesh.boolean.union([fig, staff])

    # re-color: nearest original figure color; staff verts (near the axis, far from any figure vert) -> dark
    tree = cKDTree(ov)
    d, idx = tree.query(combined.vertices)
    cols = ovc[idx]
    axis_d = np.hypot(combined.vertices[:, 0] - fx, combined.vertices[:, 2] - fz)
    dark = np.array([int(a.dark[i:i+2], 16) for i in (0, 2, 4)] + [255], np.uint8)
    staff_mask = (axis_d < a.radius * 2.6) & (d > 0.02)
    cols[staff_mask] = dark
    combined.visual.vertex_colors = cols
    combined.export(a.out)
    print(f"[weapon] staff r={a.radius} at ({fx:.2f},{fz:.2f}), shaft y[{ymin:.2f}->{shaft_top:.2f}] "
          f"+ {a.head} spearhead. staff verts={int(staff_mask.sum())}. "
          f"-> {a.out} ({len(combined.faces)}f, watertight={combined.is_watertight})")


if __name__ == "__main__":
    main()
