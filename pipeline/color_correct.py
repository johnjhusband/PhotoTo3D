#!/usr/bin/env python3
"""color_correct.py — brighten / white-balance / saturate a colored mesh's color before quantizing.

TRELLIS texture comes out dark/muddy (baked shading + possible gamma). For a multi-color PRINT we
don't need physically-correct albedo — we need vivid, separable color so k-means finds N distinct
filament regions instead of collapsing them into browns. This applies, per-vertex:
  1. gray-world WHITE BALANCE (removes the brown cast),
  2. per-channel CONTRAST STRETCH (black/white point to percentiles),
  3. SATURATION boost in HSV,
  4. BRIGHTNESS/gamma lift.
Operates on whatever color the mesh carries (texture sampled at UV, or vertex colors).

Usage: color_correct.py <colored_mesh> <out.glb> [--sat 1.6] [--gamma 0.8] [--lo 2] [--hi 98]
Run with a python that has trimesh + numpy.
"""
import os, sys, colorsys
import numpy as np
import trimesh


def _args(argv):
    if len(argv) < 3:
        sys.exit("usage: color_correct.py <colored_mesh> <out.glb> [--sat 1.6] [--gamma 0.8] [--lo 2] [--hi 98]")
    inp, out = argv[1], argv[2]
    o = {"sat": 1.6, "gamma": 0.8, "lo": 2.0, "hi": 98.0, "wb": 1.0}
    i = 3
    while i < len(argv):
        k = argv[i].lstrip("-")
        if k in o:
            o[k] = float(argv[i + 1]); i += 2
        else:
            i += 1
    return inp, out, o


def vcolors(m):
    vis = m.visual
    try:
        if isinstance(vis, trimesh.visual.TextureVisuals) and vis.uv is not None and vis.material is not None:
            mat = vis.material
            img = getattr(mat, "baseColorTexture", None) or getattr(mat, "image", None)
            if img is not None:
                tex = np.asarray(img.convert("RGB")); h, w = tex.shape[:2]
                uv = np.asarray(vis.uv, float)
                px = np.clip((uv[:, 0] % 1.0 * (w - 1)).astype(int), 0, w - 1)
                py = np.clip(((1.0 - uv[:, 1] % 1.0) * (h - 1)).astype(int), 0, h - 1)
                rgb = tex[py, px]
                if rgb.shape[0] == len(m.vertices):
                    return rgb.astype(float)
    except Exception:
        pass
    try:
        return np.asarray(vis.to_color().vertex_colors)[:, :3].astype(float)
    except Exception:
        return np.asarray(vis.vertex_colors)[:, :3].astype(float)


def correct(rgb, o):
    rgb = rgb.astype(float)
    # 1) gray-world white balance (partial: wb in [0,1]) — scale channels toward equal means.
    # Full WB whitens a brown-dominant anime image; blend it so the cast lifts without going gray.
    mean = rgb.reshape(-1, 3).mean(0)
    g = mean.mean()
    scale = 1.0 + o["wb"] * (g / np.maximum(mean, 1e-3) - 1.0)
    rgb = np.clip(rgb * scale, 0, 255)
    # 2) per-channel contrast stretch to [lo,hi] percentiles
    lo = np.percentile(rgb, o["lo"], axis=0)
    hi = np.percentile(rgb, o["hi"], axis=0)
    rgb = np.clip((rgb - lo) / np.maximum(hi - lo, 1e-3) * 255.0, 0, 255)
    # 3) saturation boost in HSV
    hsv = np.array([colorsys.rgb_to_hsv(*(c / 255.0)) for c in rgb])
    hsv[:, 1] = np.clip(hsv[:, 1] * o["sat"], 0, 1)
    rgb = np.array([colorsys.hsv_to_rgb(*c) for c in hsv]) * 255.0
    # 4) gamma/brightness lift (gamma<1 brightens)
    rgb = np.clip(((rgb / 255.0) ** o["gamma"]) * 255.0, 0, 255)
    return rgb


def main():
    inp, out, o = _args(sys.argv)
    m = trimesh.load(inp, process=False, force="mesh")
    if isinstance(m, trimesh.Scene):
        m = m.to_geometry()
    rgb = vcolors(m)
    print(f"[cc] in  mean RGB {rgb.mean(0).round(1).tolist()}")
    cc = correct(rgb, o)
    print(f"[cc] out mean RGB {cc.mean(0).round(1).tolist()}  (sat={o['sat']} gamma={o['gamma']})")
    rgba = np.full((len(cc), 4), 255, np.uint8)
    rgba[:, :3] = np.clip(np.round(cc), 0, 255).astype(np.uint8)
    mc = m.copy()
    mc.visual = trimesh.visual.ColorVisuals(mesh=mc, vertex_colors=rgba)
    mc.export(out)
    print(f"[cc] wrote {out}")


if __name__ == "__main__":
    main()
