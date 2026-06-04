#!/usr/bin/env python3
"""run_trellis2.py — image -> 3D mesh (GLB) with TRELLIS.2-4B (O-Voxel: sharp geometry + PBR).

Geometry upgrade over TRELLIS-1 (research 2026): TRELLIS.2's O-Voxel representation keeps SHARP
features and arbitrary topology that v1's SDF softened — the fix for "soft/low-detail" geometry.
MIT-licensed. Needs ~24GB VRAM (3090 is exactly at the floor; use texture_size 2048, not 4096).

API (from the microsoft/TRELLIS.2 model card):
    from trellis2.pipelines import Trellis2ImageTo3DPipeline
    pipeline = Trellis2ImageTo3DPipeline.from_pretrained("microsoft/TRELLIS.2-4B"); pipeline.cuda()
    mesh = pipeline.run(image)[0]
    glb  = o_voxel.postprocess.to_glb(vertices=..., faces=..., attr_volume=mesh.attrs, ...)

Usage: run_trellis2.py <out_dir> <image> [--seed N]
Env:   TRELLIS2_HOME (default /workspace/TRELLIS.2), MODEL (default microsoft/TRELLIS.2-4B),
       TEX (texture_size, default 2048), DECIM (decimation_target, default 400000)
"""
import os, sys

_home = os.environ.get("TRELLIS2_HOME", "/workspace/TRELLIS.2")
if os.path.isdir(os.path.join(_home, "trellis2")) and _home not in sys.path:
    sys.path.insert(0, _home)

from PIL import Image
from trellis2.pipelines import Trellis2ImageTo3DPipeline
import o_voxel


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: run_trellis2.py <out_dir> <image> [--seed N]")
    outdir, img_path = sys.argv[1], sys.argv[2]
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 1
    os.makedirs(outdir, exist_ok=True)

    image = Image.open(img_path).convert("RGB")
    model = os.environ.get("MODEL", "microsoft/TRELLIS.2-4B")
    print(f"[trellis2] loading {model}")
    pipe = Trellis2ImageTo3DPipeline.from_pretrained(model)
    pipe.cuda()

    print(f"[trellis2] run (seed={seed})")
    try:
        mesh = pipe.run(image, seed=seed)[0]      # seed if the build supports it
    except TypeError:
        mesh = pipe.run(image)[0]

    tex = int(os.environ.get("TEX", "2048"))
    decim = int(os.environ.get("DECIM", "400000"))
    print(f"[trellis2] to_glb texture_size={tex} decimation_target={decim}")
    glb = o_voxel.postprocess.to_glb(
        vertices=mesh.vertices, faces=mesh.faces, attr_volume=mesh.attrs,
        coords=mesh.coords, attr_layout=mesh.layout, voxel_size=mesh.voxel_size,
        aabb=[[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]],
        decimation_target=decim, texture_size=tex, remesh=True)

    out = os.path.join(outdir, "model.glb")
    glb.export(out)
    print(f"[trellis2] DONE -> {out}")


if __name__ == "__main__":
    main()
