#!/usr/bin/env bash
# bootstrap_new_box.sh — RUN ON THE GPU BOX. Fresh-box setup + first improved generation (E1).
# Brings a fresh vast.ai pytorch:2.4.1-cuda12.1 box from zero to a 4-color printable, with the
# blank-face + color fixes. Reproducible from the repo (no manual steps). Run from /workspace.
#
# Expects this repo's gpu/ + pipeline/ already copied to /workspace (scp/rsync from the laptop),
# and the reference image at /workspace/ref.png.
set -uo pipefail
cd /workspace
log(){ echo "[bootstrap $(date -u +%H:%M:%S)] $*"; }

log "1) TRELLIS-1 install (proven scripts; fastest path to a first result)"
bash /workspace/gpu/install_trellis.sh 2>&1 | tail -20

log "2) CGAL alpha-wrap binary (detail-preserving watertight repair)"
bash /workspace/gpu/install_alpha_wrap.sh 2>&1 | tail -8 || log "alpha-wrap build failed (repair will use voxel fallback)"

# repair_mesh + export_color3mf must sit where run_pipeline expects; palette/preprocess/color_correct too.
export REPAIR_PY=/workspace/pipeline/repair_mesh.py
export ALPHA_WRAP_BIN=/workspace/alpha_wrap
export TRELLIS_HOME=/workspace/TRELLIS
# lib3mf for the color 3MF writer; scikit-learn for Lab k-means
pip install -q lib3mf scikit-learn 2>&1 | tail -1 || true

log "3) E1 generation: preprocessed BUST (isnet-anime, gray, umbrella top-crop) -> TRELLIS SS_CFG 9 -> repair -> color-correct -> 4-color"
PREP=1 MODE=bust TOPCROP=0.18 CC=1 \
  bash /workspace/gpu/run_pipeline.sh /workspace/out_e1 /workspace/ref.png 2>&1 | tail -40

log "DONE — outputs in /workspace/out_e1 (model.glb, printable*, print_4color.*). Pull + render to judge."
