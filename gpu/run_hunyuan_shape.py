#!/usr/bin/env python3
"""run_hunyuan_shape.py — image -> mesh with Hunyuan3D-2.1 SHAPE model (Hunyuan3D-DiT flow matching).

Cheaper geometry escalation than TRELLIS.2 (no torch-2.6 env needed — reuses the installed Hunyuan env).
Hunyuan3D-2.1 geometry is rated top-tier (beats TRELLIS on detail). We feed an ALREADY anime-cut RGBA
image (transparent bg) so Hunyuan does NOT run its photo-trained rembg (which clips pale anime faces).

Usage: run_hunyuan_shape.py <image> <out.glb>
Run with the hyvenv python from /workspace/Hunyuan3D-2.1. Downloads the DiT shape weights on first run.
"""
import os, sys
import torch  # noqa: F401  (load torch libs before Hunyuan CUDA bits)
from PIL import Image
import numpy as np

HY = os.environ.get("HY_ROOT", "/workspace/Hunyuan3D-2.1")
sys.path.insert(0, os.path.join(HY, "hy3dshape"))
from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline


def ensure_rgba_cut(path):
    """Return an RGBA PIL image with a real alpha cutout. If the input is opaque RGB on a flat bg,
    use anime-aware isnet-anime (not Hunyuan's photo rembg) so the face survives."""
    img = Image.open(path).convert("RGBA")
    a = np.asarray(img)[:, :, 3]
    if a.min() == 255:  # fully opaque -> needs cutting
        from rembg import remove, new_session
        img = remove(img.convert("RGB"), session=new_session("isnet-anime"))
    return img


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: run_hunyuan_shape.py <image> <out.glb>")
    inp, out = sys.argv[1], sys.argv[2]
    img = ensure_rgba_cut(inp)
    model = os.environ.get("HY_SHAPE_MODEL", "tencent/Hunyuan3D-2.1")
    print(f"[hy-shape] loading {model}")
    pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(model)

    # Detail knobs (env-driven; omitted -> pipeline defaults, so reproducibility is unchanged).
    # octree_resolution is the big lever for geometric sharpness (default 256). Higher = finer
    # face/hands/cloth folds at the cost of VRAM+time; 384 is safe on a 24GB 3090, 512 can OOM.
    kw = {}
    if os.environ.get("HY_OCTREE"):    kw["octree_resolution"]  = int(os.environ["HY_OCTREE"])
    if os.environ.get("HY_STEPS"):     kw["num_inference_steps"] = int(os.environ["HY_STEPS"])
    if os.environ.get("HY_GUIDANCE"):  kw["guidance_scale"]      = float(os.environ["HY_GUIDANCE"])
    if os.environ.get("HY_MC_LEVEL"):  kw["mc_level"]            = float(os.environ["HY_MC_LEVEL"])
    print(f"[hy-shape] generating mesh (knobs: {kw or 'defaults'})")
    mesh = pipe(image=img, **kw)[0]
    mesh.export(out)
    print(f"[hy-shape] DONE -> {out}  (verts={len(mesh.vertices)}, faces={len(mesh.faces)})")


if __name__ == "__main__":
    main()
