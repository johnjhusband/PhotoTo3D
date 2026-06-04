#!/usr/bin/env bash
# install_hunyuan.sh — install Hunyuan3D-Paint (texture-only re-texturing) on the GPU box.
# We use it to re-texture TRELLIS geometry with bright, delit PBR albedo (fixes dark/muddy color).
#
# Prereqs already on the box: the pytorch-cuda-devel conda env (torch 2.4.1+cu121), CUDA toolkit at
# /usr/local/cuda. We build a SEPARATE venv that INHERITS that torch (--system-site-packages) so we
# don't re-download torch and don't disturb the TRELLIS/SDXL conda env (Hunyuan pins different
# numpy/open3d/diffusers versions).
#
# Weights are downloaded SEPARATELY by curl-stream (the box stalls on HF auto-download). You need:
#   - tencent/Hunyuan3D-2.1  ->  hunyuan3d-paintpbr-v2-1/*   (~7GB)  -> /workspace/_hunyuan/weights/
#   - facebook/dinov2-giant                                  (~4.5GB) -> /workspace/_hunyuan/dinov2-giant/
#   - RealESRGAN_x4plus.pth (GitHub release)                          -> /workspace/_hunyuan/weights/
# (enumerate file lists via the HF api/models JSON, curl -L -C - each file.)
set -uo pipefail
cd /workspace/Hunyuan3D-2.1
log(){ echo "[hy $(date -u +%H:%M:%S)] $*"; }

# bpy (Blender as a module, used for GLB export) needs X11/render libs even headless.
apt-get install -y --no-install-recommends libxrender1 libxi6 libxxf86vm1 libxfixes3 libxkbcommon0 libgl1 libsm6 libice6 >/dev/null 2>&1 || true

log "venv inheriting conda torch (no torch re-download, isolated from TRELLIS deps)"
/opt/conda/bin/python -m venv --system-site-packages /workspace/hyvenv
source /workspace/hyvenv/bin/activate
python -c 'import torch;print("torch",torch.__version__,"cuda",torch.cuda.is_available())'
pip install -q --upgrade pip

log "requirements (strip CN mirrors + torch pins; bpy==4.0 is unavailable on py3.11 -> 4.2.0)"
grep -v 'mirrors\.' requirements.txt \
  | grep -viE '^torch|^torchvision|^torchaudio' \
  | sed 's/^bpy==4\.0$/bpy==4.2.0/' > /tmp/hyreq.txt
pip install -r /tmp/hyreq.txt   # one bad pin fails the WHOLE resolve, so this must succeed cleanly

export CUDA_HOME=/usr/local/cuda PATH="/usr/local/cuda/bin:$PATH" TORCH_CUDA_ARCH_LIST=8.6
log "build custom_rasterizer (--no-build-isolation: its setup.py imports torch)"
( cd hy3dpaint/custom_rasterizer && pip install -e . --no-build-isolation )
log "build DifferentiableRenderer"
( cd hy3dpaint/DifferentiableRenderer && bash compile_mesh_painter.sh )

# basicsr 1.4.2 imports torchvision.transforms.functional_tensor, removed in torchvision 0.17+.
# Patch by FIND, not by `import basicsr` — importing it triggers the very error, so the path probe
# returns empty and the patch silently skips (chicken-and-egg). Rewrite every offending file.
SP=$(/workspace/hyvenv/bin/python -c "import site;print(site.getsitepackages()[0])" 2>/dev/null)
grep -rl "torchvision.transforms.functional_tensor" "$SP" 2>/dev/null \
  | xargs -r sed -i "s/torchvision.transforms.functional_tensor/torchvision.transforms.functional/g" || true

log "place RealESRGAN weight where the pipeline expects it"
mkdir -p hy3dpaint/ckpt && cp /workspace/_hunyuan/weights/RealESRGAN_x4plus.pth hy3dpaint/ckpt/

log "HY_INSTALL_DONE"
