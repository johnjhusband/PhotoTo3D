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
# HY_OCTREE=384 (vs default 256) ~doubles raw faces and gives a markedly sharper face/hands/folds that
# SURVIVES the 200k decimation — confirmed better than 256 (2026-06-05). Override via env if VRAM-tight.
HY_SHAPE_MODEL="${HY_SHAPE_MODEL:-/workspace/_hunyuan/hy3d21}" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  HY_OCTREE="${HY_OCTREE:-384}" HY_STEPS="${HY_STEPS:-50}" \
  /workspace/hyvenv/bin/python gpu/run_hunyuan_shape.py out_ap/_prep/ref_full.png out_ap/model.glb 2>&1 | tail -6
[ -f out_ap/model.glb ] || { echo "SHAPE_FAILED"; exit 1; }

log "3) Hunyuan PAINT (delit color)"
( cd /workspace/Hunyuan3D-2.1 && HY_VIEWS=8 HY_RES=512 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  HY_WEIGHTS=/workspace/_hunyuan/weights HY_DINO=/workspace/_hunyuan/dinov2-giant \
  /workspace/hyvenv/bin/python /workspace/gpu/run_hunyuan_paint.py \
  /workspace/out_ap/model.glb /workspace/out_ap/_prep/ref_full.png /workspace/out_ap/model_pbr.glb 2>&1 | tail -6 )
MESH=out_ap/model_pbr.glb; [ -f "$MESH" ] || MESH=out_ap/model.glb

log "4) detail-preserving repair (finer alpha to keep face/hands; lighter decimation)"
# NOTE: do NOT hide the full output behind a narrow grep — a crash AFTER "watertight solid"
# (e.g. in color-transfer) would be invisible and the pipeline would "succeed" with no file.
# Keep a full log and GUARD the actual deliverable.
# REL_ALPHA env-overridable: HIGHER = finer alpha = the wrap fits into narrow gaps (e.g. between a
# hand and the cape) instead of BRIDGING them into one webbed mass. Default 320; raise for hands-near-body.
REL_ALPHA="${REL_ALPHA:-320}" python pipeline/repair_mesh.py "$MESH" out_ap/printable 300000 2>&1 | tee out_ap/_repair.log | grep -aE "repair\]|watertight|Error|Traceback" | tail -8
[ -f out_ap/printable_color.glb ] || { echo "REPAIR_FAILED: no printable_color.glb (see out_ap/_repair.log)"; tail -20 out_ap/_repair.log; exit 1; }

log "5) gentle color + 4-color + lifelike full-color"
python pipeline/color_correct.py out_ap/printable_color.glb out_ap/printable_cc.glb --wb 0.0 --sat 1.0 --gamma 0.7 --lo 1 --hi 99 2>&1 | grep -aE "out mean|Error|Traceback"
[ -f out_ap/printable_cc.glb ] || { echo "COLOR_CORRECT_FAILED: no printable_cc.glb"; exit 1; }
COLORSMOOTH=25 LWEIGHT=1.0 MERGE_EXTRA=3 SMOOTH_PASSES=12 python pipeline/palette_quantize.py out_ap/printable_cc.glb out_ap/print_4color 4 2>&1 | grep -aE "regions|WARN|Error|Traceback"
[ -f out_ap/print_4color_4color.glb ] || { echo "PALETTE_FAILED: no print_4color_4color.glb"; exit 1; }

log "APOSE3D_DONE"; ls -la out_ap/print_4color_4color.glb out_ap/printable_color.glb out_ap/model.glb 2>/dev/null
