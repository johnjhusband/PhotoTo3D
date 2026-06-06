#!/usr/bin/env python3
"""render_review.py — render the MANDATORY look-at-it set for a deliverable, so you actually LOOK.

John, 2026-06-06: "you said the pieces fit but you never actually looked." Automated checks
(verify_deliverable) are necessary but NOT sufficient — the hat-on-spear and thin-shell-socket bugs
passed the math and were still wrong. So before claiming any visual/fit property, render EVERY part
from several angles (including the UNDERSIDE, where sockets/holes hide) plus the ASSEMBLY, then Read
every PNG and write what you see.

F3D can't read 3MF, so pass GLBs (or it converts 3MF→GLB via trimesh if a venv with lib3mf is on PATH).
Usage: render_review.py <out_dir> <part.glb> [more.glb ...]
  - any file with 'body' in the name + any with 'hat' → also renders the assembled (concatenated) views.
Outputs <out_dir>/<name>_{front,side,under}.png and assembled_{front,34,head}.png. Then LOOK at each.
"""
import os, sys, subprocess, tempfile
import numpy as np
import trimesh

ANGLES = {  # name: (azimuth, elevation)
    "front": (0, 4), "side": (90, 2), "under": (0, -55), "top": (15, 35),
}
ASM = {"front": (0, 4), "34": (35, 6), "head": (18, 18)}


def to_glb(path):
    if path.lower().endswith(".glb"):
        return path
    m = trimesh.load(path)
    m = m.to_geometry() if hasattr(m, "to_geometry") else m
    out = tempfile.mktemp(suffix=".glb")
    m.export(out)
    return out


def render(glb, out_png, az, el, res="640,720"):
    subprocess.run(["f3d", glb, "--output", out_png, "--resolution", res,
                    "--camera-azimuth-angle", str(az), "--camera-elevation-angle", str(el),
                    "--up", "+Y"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: render_review.py <out_dir> <part.glb> [more.glb ...]")
    out_dir, parts = sys.argv[1], sys.argv[2:]
    os.makedirs(out_dir, exist_ok=True)
    made = []
    glbs = {p: to_glb(p) for p in parts}
    for p, g in glbs.items():
        name = os.path.splitext(os.path.basename(p))[0]
        for a, (az, el) in ANGLES.items():
            out = os.path.join(out_dir, f"{name}_{a}.png")
            render(g, out, az, el)
            made.append(out)
    # assembled views if we have a body + a hat
    body = next((g for p, g in glbs.items() if "body" in p.lower()), None)
    hat = next((g for p, g in glbs.items() if "hat" in p.lower()), None)
    if body and hat:
        b = trimesh.load(body, process=False); b = b.to_geometry() if hasattr(b, "to_geometry") else b
        h = trimesh.load(hat, process=False); h = h.to_geometry() if hasattr(h, "to_geometry") else h
        asm = trimesh.util.concatenate([b, h])
        ag = os.path.join(out_dir, "_assembled.glb"); asm.export(ag)
        for a, (az, el) in ASM.items():
            out = os.path.join(out_dir, f"assembled_{a}.png")
            render(ag, out, az, el, res="700,860")
            made.append(out)
    print(f"[render_review] {len(made)} images in {out_dir}:")
    for m in made:
        print("  LOOK ->", m)
    print("Now Read EVERY one and write what you see. Automated PASS is not 'I looked.'")


if __name__ == "__main__":
    main()
