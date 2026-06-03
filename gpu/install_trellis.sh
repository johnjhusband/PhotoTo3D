#!/usr/bin/env bash
# install_trellis.sh — install Microsoft TRELLIS (image-to-3D, MIT) on a CUDA GPU box.
# Target: pytorch/pytorch:2.4.1-cuda12.1-cudnn9-devel image (torch 2.4.1, CUDA 12.1, py3.11), RTX 3090 (sm_86).
set -euo pipefail
log() { echo "[trellis-install $(date -u +%H:%M:%S)] $*"; }
export DEBIAN_FRONTEND=noninteractive
export TORCH_CUDA_ARCH_LIST="8.6"          # RTX 3090
export ATTN_BACKEND=flash-attn
export SPCONV_ALGO=native
export FORCE_CUDA=1

log "system packages"
apt-get update -y
apt-get install -y --no-install-recommends git build-essential ninja-build \
  libgl1 libglib2.0-0 libegl1 libgles2 ca-certificates wget unzip

cd /workspace 2>/dev/null || cd /root
log "clone TRELLIS (+submodules)"
rm -rf TRELLIS
git clone --recurse-submodules https://github.com/microsoft/TRELLIS.git
cd TRELLIS

log "pip baseline tooling"
pip install --upgrade pip setuptools wheel
pip install ninja

# TRELLIS ships setup.sh that installs each heavy dep with the right wheel/build.
# Install into the base env (no --new-env). Order chosen so CUDA extensions build last.
log "TRELLIS setup.sh: basic deps"
. ./setup.sh --basic
log "TRELLIS setup.sh: flash-attn"
. ./setup.sh --flash-attn
log "TRELLIS setup.sh: spconv"
. ./setup.sh --spconv
log "TRELLIS setup.sh: nvdiffrast"
. ./setup.sh --nvdiffrast
log "TRELLIS setup.sh: kaolin"
. ./setup.sh --kaolin
log "TRELLIS setup.sh: diffoctreerast + mipgaussian (CUDA builds)"
. ./setup.sh --diffoctreerast
. ./setup.sh --mipgaussian

# Mesh post-processing libs used by to_glb / our repair step
log "mesh export deps"
pip install trimesh xatlas pyvista pymeshfix open3d rembg onnxruntime igraph imageio imageio-ffmpeg

log "verify imports"
python - <<'PY'
import os
os.environ.setdefault("ATTN_BACKEND","flash-attn"); os.environ.setdefault("SPCONV_ALGO","native")
import torch
print("torch", torch.__version__, "cuda", torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "-")
from trellis.pipelines import TrellisImageTo3DPipeline
print("TRELLIS import OK")
PY
log "DONE"
