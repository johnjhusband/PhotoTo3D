#!/usr/bin/env bash
# install_consolidate.sh — deps for Step A (reference consolidation via SDXL + IP-Adapter).
# Run on the same GPU box after install_trellis.sh (reuses its torch/transformers/pillow).
set -euo pipefail
log() { echo "[consolidate-install $(date -u +%H:%M:%S)] $*"; }

# diffusers + accelerate for the SDXL/IP-Adapter pipeline. transformers is already pinned 4.46.3 by
# install_trellis.sh (compatible). peft is used by IP-Adapter loading paths.
log "pip: diffusers, accelerate, peft, safetensors"
pip install "diffusers>=0.30,<0.32" accelerate peft safetensors

log "verify diffusers + IP-Adapter import"
python - <<'PY'
import torch, diffusers
from diffusers import StableDiffusionXLPipeline
print("diffusers", diffusers.__version__, "torch", torch.__version__, "cuda", torch.cuda.is_available())
print("consolidate deps OK")
PY
log "DONE"
