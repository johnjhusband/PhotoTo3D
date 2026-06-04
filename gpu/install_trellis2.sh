#!/usr/bin/env bash
# install_trellis2.sh — install Microsoft TRELLIS.2-4B (image-to-3D, O-Voxel, MIT) on a CUDA GPU box.
# Geometry upgrade over TRELLIS-1 (sharper features). Needs ~24GB VRAM (RTX 3090 is at the floor).
# Adapted from install_trellis.sh: same network-hardening (HTTP/1.1 + retries) for the hostile box.
#
# Official install (model card):
#   git clone -b main https://github.com/microsoft/TRELLIS.2.git --recursive
#   . ./setup.sh --new-env --basic --flash-attn --nvdiffrast --nvdiffrec --cumesh --o-voxel --flexgemm
# CAVEAT for RTX 3090 (sm_86): flash-attn source builds are slow/fragile here (v1 used xformers
# instead). If --flash-attn fails, retry setup.sh without it and set ATTN_BACKEND=xformers, OR install
# a prebuilt flash-attn wheel matching torch/cu. Validate the import block at the end before trusting.
set -uo pipefail
log() { echo "[trellis2-install $(date -u +%H:%M:%S)] $*"; }
export DEBIAN_FRONTEND=noninteractive
export TORCH_CUDA_ARCH_LIST="8.6"     # RTX 3090
export SPCONV_ALGO=native
export FORCE_CUDA=1
export CUDA_HOME=/usr/local/cuda
export PATH="$CUDA_HOME/bin:$PATH"

log "system packages"
apt-get update -y
apt-get install -y --no-install-recommends git build-essential ninja-build \
  libgl1 libglib2.0-0 libegl1 libgles2 ca-certificates wget unzip

# network hardening (same root-cause fix as v1: HTTP/2 multiplexing -> early-EOF on this host)
git config --global http.version HTTP/1.1
git config --global http.postBuffer 524288000
git config --global http.lowSpeedLimit 0
git config --global http.lowSpeedTime 999999

cd /workspace 2>/dev/null || cd /root
log "clone TRELLIS.2 (shallow retries; submodules separately to avoid large-pack early-EOF)"
rm -rf TRELLIS.2
for a in 1 2 3 4 5; do
  git clone -b main https://github.com/microsoft/TRELLIS.2.git && break
  log "clone attempt $a failed; retry"; rm -rf TRELLIS.2; sleep 5
done
[ -d TRELLIS.2 ] || { echo "FATAL: TRELLIS.2 clone failed"; exit 1; }
cd TRELLIS.2
for a in 1 2 3 4 5; do
  git submodule update --init --recursive --depth 1 && break
  log "submodule attempt $a failed; retry"; sleep 5
done

pip install --upgrade pip setuptools wheel ninja

# Install into the BASE conda env (no --new-env) so it shares the working torch/cuda, like v1.
# Try the full O-Voxel stack. If flash-attn is the only failure on sm_86, fall back to xformers attn.
log "setup.sh: basic + o-voxel stack (flash-attn may need fallback on 3090)"
if ! . ./setup.sh --basic --nvdiffrast --nvdiffrec --cumesh --o-voxel --flexgemm --flash-attn ; then
  log "full setup failed (likely flash-attn on sm_86); retrying without flash-attn + xformers"
  . ./setup.sh --basic --nvdiffrast --nvdiffrec --cumesh --o-voxel --flexgemm || true
  pip install xformers==0.0.28.post1 --index-url https://download.pytorch.org/whl/cu121 || true
  export ATTN_BACKEND=xformers
fi

log "mesh export deps (shared with the rest of the pipeline)"
pip install trimesh xatlas pyvista pymeshfix rembg onnxruntime imageio imageio-ffmpeg lxml lib3mf scikit-learn || true

log "verify imports"
python - <<'PY'
import torch
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
try:
    from trellis2.pipelines import Trellis2ImageTo3DPipeline
    import o_voxel
    print("TRELLIS.2 import OK")
except Exception as e:
    print("TRELLIS.2 import FAILED:", e)
PY
log "DONE (if import FAILED, fix attention backend / o_voxel build before running run_trellis2.py)"
