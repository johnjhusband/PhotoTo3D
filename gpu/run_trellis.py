#!/usr/bin/env python3
"""run_trellis.py — single image -> 3D mesh (GLB) with TRELLIS, then STL/3MF.

Usage: python run_trellis.py <input_image> <out_dir> [seed]
Outputs in <out_dir>: model.glb, model.stl, model.3mf, preview.png
"""
import os, sys
os.environ.setdefault("ATTN_BACKEND", "flash-attn")
os.environ.setdefault("SPCONV_ALGO", "native")

import numpy as np
from PIL import Image
import imageio
from trellis.pipelines import TrellisImageTo3DPipeline
from trellis.utils import postprocessing_utils, render_utils


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: run_trellis.py <input_image> <out_dir> [seed]")
    inp, outdir = sys.argv[1], sys.argv[2]
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    os.makedirs(outdir, exist_ok=True)

    print(f"[trellis] loading pipeline (downloads weights first run)...")
    pipe = TrellisImageTo3DPipeline.from_pretrained("JeffreyXiang/TRELLIS-image-large")
    pipe.cuda()

    print(f"[trellis] preprocessing + running on {inp} (seed={seed})")
    img = Image.open(inp)
    # pipe.run handles background removal + 3D generation
    outputs = pipe.run(
        img,
        seed=seed,
        formats=["gaussian", "mesh"],
        preprocess_image=True,
        sparse_structure_sampler_params={"steps": 12, "cfg_strength": 7.5},
        slat_sampler_params={"steps": 12, "cfg_strength": 3.0},
    )

    # a turntable preview render so we can eyeball it before printing
    try:
        frames = render_utils.render_video(outputs["gaussian"][0], num_frames=30)["color"]
        imageio.mimsave(os.path.join(outdir, "preview.mp4"), frames, fps=15)
        imageio.imwrite(os.path.join(outdir, "preview.png"), frames[0])
    except Exception as e:
        print(f"[trellis] preview render skipped: {e}")

    print("[trellis] exporting GLB (textured)")
    glb = postprocessing_utils.to_glb(
        outputs["gaussian"][0], outputs["mesh"][0],
        simplify=0.95, texture_size=1024,
    )
    glb_path = os.path.join(outdir, "model.glb")
    glb.export(glb_path)
    print(f"[trellis] wrote {glb_path}")

    # GLB -> printable STL/3MF (geometry only)
    import trimesh
    scene = trimesh.load(glb_path)
    mesh = (trimesh.util.concatenate([g for g in scene.geometry.values()])
            if isinstance(scene, trimesh.Scene) else scene)
    mesh.export(os.path.join(outdir, "model.stl"))
    mesh.export(os.path.join(outdir, "model.3mf"))
    print(f"[trellis] wrote STL/3MF  | verts={len(mesh.vertices)} faces={len(mesh.faces)} "
          f"watertight={mesh.is_watertight}")


if __name__ == "__main__":
    main()
