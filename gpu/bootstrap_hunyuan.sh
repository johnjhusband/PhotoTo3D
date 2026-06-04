#!/usr/bin/env bash
# bootstrap_hunyuan.sh — RUN ON BOX. Install Hunyuan3D-Paint, download weights, and re-texture the
# E1 mesh with DELIT (light/shadow-free) PBR albedo so the 4 print regions become clean MATERIAL
# colors instead of baked light/shadow. Then repair + 4-color on the delit result.
# Reproducible; all pitfalls are encoded in install_hunyuan.sh.
set -uo pipefail
cd /workspace
log(){ echo "[hy-boot $(date -u +%H:%M:%S)] $*"; }
git config --global http.version HTTP/1.1

log "1) clone Hunyuan3D-2.1"
if [ ! -d Hunyuan3D-2.1 ]; then
  for a in 1 2 3 4 5; do git clone https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1.git && break; log "clone retry $a"; sleep 5; done
fi
[ -d Hunyuan3D-2.1 ] || { echo "FATAL: clone failed"; exit 1; }

log "2) download weights (huggingface_hub; US box has good net)"
pip install -q huggingface_hub
mkdir -p /workspace/_hunyuan/weights /workspace/_hunyuan/dinov2-giant
python - <<'PY'
from huggingface_hub import snapshot_download
print("paint weights..."); snapshot_download("tencent/Hunyuan3D-2.1",
    allow_patterns=["hunyuan3d-paintpbr-v2-1/*"], local_dir="/workspace/_hunyuan/weights")
print("dinov2-giant..."); snapshot_download("facebook/dinov2-giant", local_dir="/workspace/_hunyuan/dinov2-giant")
print("weights done")
PY
log "RealESRGAN weight"
curl -sL --retry 8 -o /workspace/_hunyuan/weights/RealESRGAN_x4plus.pth \
  https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth

log "3) install Hunyuan (encodes bpy/basicsr/custom_rasterizer fixes)"
bash /workspace/gpu/install_hunyuan.sh 2>&1 | tail -20

log "4) re-texture model.glb with delit PBR albedo -> model_pbr.glb (keeps geometry)"
cd /workspace/Hunyuan3D-2.1
HY_WEIGHTS=/workspace/_hunyuan/weights HY_DINO=/workspace/_hunyuan/dinov2-giant \
  /workspace/hyvenv/bin/python /workspace/gpu/run_hunyuan_paint.py \
  /workspace/out_e1/model.glb /workspace/out_e1/_prep/ref_bust.png /workspace/out_e1/model_pbr.glb 2>&1 | tail -25

log "HY_RETEXTURE_DONE -> /workspace/out_e1/model_pbr.glb"
ls -la /workspace/out_e1/model_pbr.glb 2>/dev/null || echo "NO model_pbr.glb (retexture failed)"
