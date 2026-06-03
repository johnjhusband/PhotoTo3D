#!/usr/bin/env bash
# run_pipeline.sh — full generative path: image(s) -> printable mesh.
#   1 image   -> straight to TRELLIS single-image (unchanged).
#   2+ images -> Step A consolidation (fuse refs -> 1 canonical image) -> TRELLIS single-image.
#
# Usage: run_pipeline.sh <out_dir> <img1> [img2 ...] [--prompt "..."]
# Env:   TRELLIS_HOME (default /workspace/TRELLIS)
set -euo pipefail
TRELLIS_HOME="${TRELLIS_HOME:-/workspace/TRELLIS}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:?usage: run_pipeline.sh <out_dir> <img...> [--prompt ...]}"; shift

# split args into images and an optional --prompt
IMGS=(); PROMPT=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --prompt) PROMPT="$2"; shift 2 ;;
    *) IMGS+=("$1"); shift ;;
  esac
done
[ "${#IMGS[@]}" -ge 1 ] || { echo "need at least one image"; exit 1; }
mkdir -p "$OUT"

run_trellis() {  # <single_image>
  PYTHONPATH="$TRELLIS_HOME" ATTN_BACKEND=xformers SPCONV_ALGO=native \
    python "$HERE/run_trellis.py" "$OUT" "$1"
}

if [ "${#IMGS[@]}" -eq 1 ]; then
  echo "[pipeline] single image -> TRELLIS (no consolidation)"
  run_trellis "${IMGS[0]}"
else
  echo "[pipeline] ${#IMGS[@]} images -> Step A consolidation first"
  CANON="$OUT/canonical.png"
  if [ -n "$PROMPT" ]; then
    python "$HERE/consolidate.py" "$CANON" "${IMGS[@]}" --prompt "$PROMPT"
  else
    python "$HERE/consolidate.py" "$CANON" "${IMGS[@]}"
  fi
  echo "[pipeline] consolidated -> $CANON ; now TRELLIS single-image on it"
  run_trellis "$CANON"
fi
echo "[pipeline] DONE -> $OUT/model.{glb,stl,3mf}"
