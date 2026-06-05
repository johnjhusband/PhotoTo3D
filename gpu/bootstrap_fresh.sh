#!/usr/bin/env bash
# bootstrap_fresh.sh — RUN ON A FRESH vast.ai box. Full setup + hat regeneration, WITHOUT TRELLIS
# (the working pipeline uses Hunyuan shape). HF is throttled (~57 B/s single-stream) so ALL model
# weights come via aria2c (gpu/fetch_hf.py); pip/git are fast and used normally.
set -uo pipefail
cd /workspace
log(){ echo "[fresh $(date -u +%H:%M:%S)] $*"; }
export DEBIAN_FRONTEND=noninteractive
which aria2c >/dev/null 2>&1 || apt-get install -y -q aria2 >/dev/null 2>&1
pip install -q huggingface_hub 2>&1 | tail -1

log "1) base mesh/diffusion python deps (PyPI, fast) — no TRELLIS"
pip install -q trimesh rembg onnxruntime scipy scikit-learn lib3mf xatlas pymeshfix pillow numpy \
  fast_simplification \
  "diffusers>=0.30,<0.32" accelerate peft safetensors transformers==4.46.3 imageio imageio-ffmpeg 2>&1 | tail -2
# fast_simplification: trimesh's simplify_quadric_decimation imports it lazily; without it the
# repair step crashes at decimation (AFTER building the watertight solid) — see TROUBLESHOOTING.

log "2) clone Hunyuan3D-2.1 (GitHub, fast) + build paint env (hyvenv)"
git config --global http.version HTTP/1.1
[ -d Hunyuan3D-2.1 ] || for a in 1 2 3; do git clone https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1.git && break; sleep 4; done

log "3) aria2c ALL HF weights (bypass throttle)"
mkdir -p _sdxl _hunyuan/weights _hunyuan/dinov2-giant _hunyuan/hy3d21
python gpu/fetch_hf.py stabilityai/stable-diffusion-xl-base-1.0 _sdxl/sdxl-base
python gpu/fetch_hf.py h94/IP-Adapter _sdxl/ip-adapter "sdxl_models/ip-adapter_sdxl.bin" "sdxl_models/image_encoder/*"
python gpu/fetch_hf.py tencent/Hunyuan3D-2.1 _hunyuan/weights "hunyuan3d-paintpbr-v2-1/*"
python gpu/fetch_hf.py facebook/dinov2-giant _hunyuan/dinov2-giant
aria2c -x16 -s16 --file-allocation=none -q -d _hunyuan/weights -o RealESRGAN_x4plus.pth \
  "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth" || true
bash gpu/fetch_hunyuan_shape_weights.sh /workspace/_hunyuan/hy3d21

log "4) build Hunyuan paint env (custom_rasterizer etc.) + alpha-wrap"
bash gpu/install_hunyuan.sh 2>&1 | tail -15
bash gpu/install_alpha_wrap.sh 2>&1 | tail -4

log "5) GENERATE: multi-image A-pose WITH HAT"
bash gpu/gen_apose_hat.sh 2>&1 | tail -6
[ -f out_ap/canonical.png ] || { echo "HAT_CANON_FAILED"; exit 1; }

log "6) 3D: shape -> paint -> repair -> color -> 4-color"
HY_SHAPE_MODEL=/workspace/_hunyuan/hy3d21 bash gpu/apose_3d.sh 2>&1 | tail -12

log "FRESH_DONE"; ls -la out_ap/print_4color_4color.glb out_ap/printable_color.glb out_ap/canonical.png 2>/dev/null
