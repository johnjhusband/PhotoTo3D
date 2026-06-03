#!/usr/bin/env bash
# install_trellis.sh — install Microsoft TRELLIS (image-to-3D, MIT) on a CUDA GPU box.
# Target: pytorch/pytorch:2.4.1-cuda12.1-cudnn9-devel image (torch 2.4.1, CUDA 12.1, py3.11), RTX 3090 (sm_86).
set -euo pipefail
log() { echo "[trellis-install $(date -u +%H:%M:%S)] $*"; }
export DEBIAN_FRONTEND=noninteractive
export TORCH_CUDA_ARCH_LIST="8.6"          # RTX 3090
export ATTN_BACKEND=xformers                # xformers: prebuilt wheels, no flash-attn source build
export SPCONV_ALGO=native
export FORCE_CUDA=1

log "system packages"
apt-get update -y
apt-get install -y --no-install-recommends git build-essential ninja-build \
  libgl1 libglib2.0-0 libegl1 libgles2 ca-certificates wget unzip

cd /workspace 2>/dev/null || cd /root
log "clone TRELLIS (shallow + retries, then submodules separately — avoids large-pack early-EOF)"
# Root cause of 'curl 92 HTTP/2 stream CANCEL / early EOF' on some hosts: HTTP/2 multiplexing.
git config --global http.version HTTP/1.1
git config --global http.postBuffer 524288000
git config --global http.lowSpeedLimit 0
git config --global http.lowSpeedTime 999999
rm -rf TRELLIS
for attempt in 1 2 3 4 5; do
  git clone --depth 1 https://github.com/microsoft/TRELLIS.git && break
  log "clone attempt $attempt failed; retrying"; rm -rf TRELLIS; sleep 5
done
[ -d TRELLIS ] || { echo "FATAL: TRELLIS clone failed after retries"; exit 1; }
cd TRELLIS
for attempt in 1 2 3 4 5; do
  git submodule update --init --recursive --depth 1 && break
  log "submodule attempt $attempt failed; retrying"; sleep 5
done

log "pip baseline tooling"
pip install --upgrade pip setuptools wheel
pip install ninja

# TRELLIS ships setup.sh that installs each heavy dep with the right wheel/build.
# Install into the base env (no --new-env). Order chosen so CUDA extensions build last.

# Pre-pin open3d so setup.sh's large 'basic' resolve doesn't backtrack between open3d
# 0.18/0.19 (different werkzeug pins) and bail with ResolutionImpossible.
log "pre-install open3d (pinned) to avoid resolver conflict in basic deps"
pip install "open3d==0.19.0" "werkzeug>=3.0.0"

log "TRELLIS setup.sh: basic deps"
. ./setup.sh --basic
log "xformers (attention backend; matches torch 2.4.1, prebuilt cu121 wheel — no source build)"
pip install xformers==0.0.28.post1 --index-url https://download.pytorch.org/whl/cu121
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
