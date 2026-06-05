#!/usr/bin/env bash
# fetch_hunyuan_shape_weights.sh — download the Hunyuan3D-2.1 SHAPE model (DiT + VAE) onto the box.
# WHY aria2c: vast.ai boxes are throttled to ~1.3 KB/s per HF connection (single-stream curl/HF download
# hangs for hours). aria2c with 16 parallel connections bypasses the per-connection throttle → ~138 MB/s.
# Point run_hunyuan_shape.py at the result with HY_SHAPE_MODEL=$DEST + HF_HUB_OFFLINE=1.
set -uo pipefail
DEST="${1:-/workspace/_hunyuan/hy3d21}"
B=https://huggingface.co/tencent/Hunyuan3D-2.1/resolve/main
which aria2c >/dev/null 2>&1 || apt-get install -y -q aria2 >/dev/null 2>&1
mkdir -p "$DEST/hunyuan3d-dit-v2-1" "$DEST/hunyuan3d-vae-v2-1"
dl(){ # <dir> <name> <url>  — clean target name first to avoid aria2's ".1" rename
  rm -f "$1/$2" "$1/$2.aria2"
  aria2c -x16 -s16 -k1M --max-tries=3 --retry-wait=2 --file-allocation=none --allow-overwrite=true \
    -q -d "$1" -o "$2" "$3"
}
dl "$DEST/hunyuan3d-dit-v2-1" model.fp16.ckpt "$B/hunyuan3d-dit-v2-1/model.fp16.ckpt"
dl "$DEST/hunyuan3d-dit-v2-1" config.yaml     "$B/hunyuan3d-dit-v2-1/config.yaml"
dl "$DEST/hunyuan3d-vae-v2-1" model.fp16.ckpt "$B/hunyuan3d-vae-v2-1/model.fp16.ckpt"
dl "$DEST/hunyuan3d-vae-v2-1" config.yaml     "$B/hunyuan3d-vae-v2-1/config.yaml"
echo "shape weights at $DEST:"; find "$DEST" -name "*.ckpt" -exec ls -la {} \;
