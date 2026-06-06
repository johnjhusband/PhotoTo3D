#!/usr/bin/env bash
# ai_build.sh — RUN ON A FRESH vast box for the AI fork. Lean install (NO SDXL/IP-Adapter — the 2D ref
# is gpt-image-1, supplied as ref_v4.png) then: Hunyuan shape -> paint -> repair -> add weapon -> split
# hat (clean, NO peg) -> body 4-color (grey dress) + straw hat. Pull the GLBs and render+LOOK locally.
set -uo pipefail
cd /workspace
log(){ echo "[ai_build $(date -u +%H:%M:%S)] $*"; }
export DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
which aria2c >/dev/null 2>&1 || apt-get install -y -q aria2 >/dev/null 2>&1
pip install -q huggingface_hub 2>&1 | tail -1

log "1) python deps (PyPI, fast)"
pip install -q trimesh rembg onnxruntime scipy scikit-learn lib3mf xatlas pymeshfix pillow numpy \
  fast_simplification manifold3d networkx lxml \
  "diffusers>=0.30,<0.32" accelerate peft safetensors transformers==4.46.3 imageio imageio-ffmpeg 2>&1 | tail -2

log "2) clone Hunyuan3D-2.1 (GitHub)"
git config --global http.version HTTP/1.1
[ -d Hunyuan3D-2.1 ] || for a in 1 2 3; do git clone https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1.git && break; sleep 4; done

log "3) aria2c Hunyuan weights (paint + dino + shape) + RealESRGAN (NO SDXL)"
mkdir -p _hunyuan/weights _hunyuan/dinov2-giant _hunyuan/hy3d21 out_ap
python gpu/fetch_hf.py tencent/Hunyuan3D-2.1 _hunyuan/weights "hunyuan3d-paintpbr-v2-1/*"
python gpu/fetch_hf.py facebook/dinov2-giant _hunyuan/dinov2-giant
aria2c -x16 -s16 --file-allocation=none -q -d _hunyuan/weights -o RealESRGAN_x4plus.pth \
  "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth" || true
bash gpu/fetch_hunyuan_shape_weights.sh /workspace/_hunyuan/hy3d21

log "4) build Hunyuan paint env + alpha-wrap"
bash gpu/install_hunyuan.sh 2>&1 | tail -8
bash gpu/install_alpha_wrap.sh 2>&1 | tail -4

log "5) 3D from the v4 reference: shape(octree384) -> paint -> repair(alpha360) -> 4color"
cp ref_v4.png out_ap/canonical.png
HY_SHAPE_MODEL=/workspace/_hunyuan/hy3d21 REL_ALPHA=360 bash gpu/apose_3d.sh 2>&1 | tail -10
[ -f out_ap/printable_color.glb ] || { echo "AI_BUILD_FAIL: no printable_color.glb"; exit 1; }

log "6) graft the spear (auto-detect the fist)"
PYTHONPATH=/workspace/gpu:/workspace/pipeline python3 pipeline/add_weapon.py \
  out_ap/printable_color.glb out_ap/v4_weapon.glb --radius 0.05 2>&1 | tail -3

log "7) split the hat off (clean, NO peg — the hat seats on the head)"
LWEIGHT=1.0 COLORSMOOTH=20 SMOOTH_PASSES=10 PYTHONPATH=/workspace/gpu:/workspace/pipeline \
  python3 pipeline/palette_quantize.py out_ap/v4_weapon.glb out_ap/v4w 4 2>&1 | grep -aE "regions|wrote.*glb"
PYTHONPATH=/workspace/gpu:/workspace/pipeline python3 pipeline/split_hat_puzzle.py \
  out_ap/v4w_4color.glb out_ap/final --color out_ap/v4_weapon.glb --mm 150 --peg-mode none 2>&1 | grep -aE "hatsplit"

log "8) body -> 4 colors (grey dress: LWEIGHT 1.6); force the staff dark first"
python3 -c "
import trimesh,numpy as np
m=trimesh.load('out_ap/final/figurine_body_colored.glb',process=False); m=m.to_geometry() if hasattr(m,'to_geometry') else m
v=np.asarray(m.vertices); vc=np.asarray(m.visual.vertex_colors).copy()
staff=(v[:,0]<-15)&(v[:,2]>15); vc[staff,:3]=[20,16,12]; vc[staff,3]=255
m.visual.vertex_colors=vc; m.export('out_ap/final/body_fixed.glb'); print('staff dark', int(staff.sum()))
"
COLORSMOOTH=15 LWEIGHT=1.6 MERGE_EXTRA=5 SMOOTH_PASSES=8 ISLAND_MIN=80 MIN_COMPONENT=50 \
  PYTHONPATH=/workspace/gpu:/workspace/pipeline python3 pipeline/palette_quantize.py \
  out_ap/final/body_fixed.glb out_ap/final/figurine_body 4 2>&1 | grep -aE "regions|dropped|wrote.*3mf"

log "AI_BUILD_DONE"; ls -la out_ap/final/*.3mf out_ap/final/figurine_body_4color.glb out_ap/final/figurine_hat_colored.glb 2>/dev/null
