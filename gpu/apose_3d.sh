#!/usr/bin/env bash
# apose_3d.sh — RUN ON BOX after gen_apose_canonical.sh produces a GOOD A-pose canonical.
# A-pose canonical → preprocess → Hunyuan SHAPE → detail-preserving repair → color → 4-color + lifelike.
# Form-preserving: REL_ALPHA high (finer alpha-wrap = less feature rounding on face/hands), light decimation.
set -uo pipefail
cd /workspace
export PYTHONPATH=/workspace/gpu:/workspace/pipeline ALPHA_WRAP_BIN=/workspace/alpha_wrap REPAIR_PY=/workspace/pipeline/repair_mesh.py
mkdir -p out_ap
log(){ echo "[apose3d $(date -u +%H:%M:%S)] $*"; }

log "1) preprocess canonical (isnet-anime, gray)"
python pipeline/preprocess_reference.py out_ap/canonical.png out_ap/_prep --bg gray 2>&1 | tail -3

log "2) Hunyuan SHAPE (crisp geometry, A-pose) — LOCAL weights (box HF is throttled; aria2c-fetched)"
HY_SHAPE_MODEL="${HY_SHAPE_MODEL:-/workspace/_hunyuan/hy3d21}" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  /workspace/hyvenv/bin/python gpu/run_hunyuan_shape.py out_ap/_prep/ref_full.png out_ap/model.glb 2>&1 | tail -6
[ -f out_ap/model.glb ] || { echo "SHAPE_FAILED"; exit 1; }

log "3) Hunyuan PAINT (delit color)"
( cd /workspace/Hunyuan3D-2.1 && HY_VIEWS=8 HY_RES=512 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  HY_WEIGHTS=/workspace/_hunyuan/weights HY_DINO=/workspace/_hunyuan/dinov2-giant \
  /workspace/hyvenv/bin/python /workspace/gpu/run_hunyuan_paint.py \
  /workspace/out_ap/model.glb /workspace/out_ap/_prep/ref_full.png /workspace/out_ap/model_pbr.glb 2>&1 | tail -6 )
MESH=out_ap/model_pbr.glb; [ -f "$MESH" ] || MESH=out_ap/model.glb

log "4) detail-preserving repair (finer alpha to keep face/hands; lighter decimation)"
REL_ALPHA=320 python pipeline/repair_mesh.py "$MESH" out_ap/printable 300000 2>&1 | grep -aE "repair\] FINAL|watertight"

log "5) gentle color + 4-color + lifelike full-color"
python pipeline/color_correct.py out_ap/printable_color.glb out_ap/printable_cc.glb --wb 0.0 --sat 1.0 --gamma 0.7 --lo 1 --hi 99 2>&1 | grep "out mean"
COLORSMOOTH=25 LWEIGHT=1.0 MERGE_EXTRA=3 SMOOTH_PASSES=12 python pipeline/palette_quantize.py out_ap/printable_cc.glb out_ap/print_4color 4 2>&1 | grep -aE "regions|WARN"

log "APOSE3D_DONE"; ls -la out_ap/print_4color_4color.glb out_ap/printable_color.glb out_ap/model.glb 2>/dev/null
