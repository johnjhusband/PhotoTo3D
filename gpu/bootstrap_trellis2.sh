#!/usr/bin/env bash
# bootstrap_trellis2.sh — RUN ON BOX. Install TRELLIS.2-4B and generate from the preprocessed bust.
# Goal: sharper geometry (O-Voxel) + potentially cleaner/brighter PBR texture than TRELLIS-1+Hunyuan.
set -uo pipefail
cd /workspace
log(){ echo "[t2-boot $(date -u +%H:%M:%S)] $*"; }

log "1) install TRELLIS.2-4B (flash-attn may fall back to xformers on 3090)"
bash /workspace/gpu/install_trellis2.sh 2>&1 | tail -40

log "2) generate from the preprocessed bust (same clean ref as E1)"
export TRELLIS2_HOME=/workspace/TRELLIS.2 TEX=2048 DECIM=400000
python /workspace/gpu/run_trellis2.py /workspace/out_t2 /workspace/out_e1/_prep/ref_bust.png --seed 1 2>&1 | tail -30

log "T2_DONE"
ls -la /workspace/out_t2/model.glb 2>/dev/null && echo T2_OK || echo T2_NO_MODEL
