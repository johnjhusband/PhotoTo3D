#!/usr/bin/env python3
"""run_hunyuan_paint.py — RE-TEXTURE an existing mesh with Hunyuan3D-Paint, keeping its geometry.

Hunyuan3D-Paint produces light/shadow-free (delit) PBR albedo — the fix for TRELLIS's dark/muddy
baked-lighting color. We keep the TRELLIS geometry (use_remesh=False) and only swap the texture.

Loads weights from a LOCAL copy (the box can't reliably hit HF): we monkeypatch
huggingface_hub.snapshot_download to return the local dir when given a local path, so the upstream
loader (utils/multiview_utils.py) uses our curl-downloaded weights instead of downloading.

Usage:  run_hunyuan_paint.py <mesh.glb|obj> <reference_image> <out.glb>
Env:    HY_WEIGHTS  dir CONTAINING hunyuan3d-paintpbr-v2-1/  (default /workspace/_hunyuan/weights)
        HY_DINO     local dinov2-giant dir                  (default /workspace/_hunyuan/dinov2-giant)
Run from /workspace/Hunyuan3D-2.1 with the hyvenv python.
"""
import os, sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
HY_ROOT = os.environ.get("HY_ROOT", "/workspace/Hunyuan3D-2.1")
sys.path.insert(0, HY_ROOT)
sys.path.insert(0, os.path.join(HY_ROOT, "hy3dpaint"))

# Import torch FIRST so its libs (libc10.so) are loaded before the custom_rasterizer CUDA extension
# (built against torch) tries to dlopen them — otherwise ImportError: libc10.so not found.
import torch  # noqa: F401

# Patch snapshot_download BEFORE importing the pipeline (which binds it at import time).
import huggingface_hub
_orig_snapshot = huggingface_hub.snapshot_download
def _local_snapshot(repo_id=None, **kw):
    if repo_id and os.path.isdir(str(repo_id)):
        return str(repo_id)
    return _orig_snapshot(repo_id=repo_id, **kw)
huggingface_hub.snapshot_download = _local_snapshot

from textureGenPipeline import Hunyuan3DPaintPipeline, Hunyuan3DPaintConfig  # noqa: E402

# belt-and-suspenders: patch the name as imported into the loader module, if present
for modname in ("utils.multiview_utils", "hy3dpaint.utils.multiview_utils"):
    m = sys.modules.get(modname)
    if m is not None and hasattr(m, "snapshot_download"):
        m.snapshot_download = _local_snapshot


def main():
    if len(sys.argv) < 4:
        sys.exit("usage: run_hunyuan_paint.py <mesh> <reference_image> <out.glb>")
    mesh, image, out = sys.argv[1], sys.argv[2], sys.argv[3]

    cfg = Hunyuan3DPaintConfig(max_num_view=6, resolution=512)
    cfg.multiview_pretrained_path = os.environ.get("HY_WEIGHTS", "/workspace/_hunyuan/weights")
    cfg.dino_ckpt_path = os.environ.get("HY_DINO", "/workspace/_hunyuan/dinov2-giant")
    cfg.realesrgan_ckpt_path = os.environ.get(
        "HY_REALESRGAN", os.path.join(HY_ROOT, "hy3dpaint/ckpt/RealESRGAN_x4plus.pth"))
    print(f"[hy-paint] weights={cfg.multiview_pretrained_path} dino={cfg.dino_ckpt_path}")

    pipe = Hunyuan3DPaintPipeline(cfg)
    res = pipe(mesh_path=mesh, image_path=image, output_mesh_path=out,
               use_remesh=False, save_glb=True)   # keep TRELLIS geometry exactly
    print(f"[hy-paint] DONE -> {res}")


if __name__ == "__main__":
    main()
