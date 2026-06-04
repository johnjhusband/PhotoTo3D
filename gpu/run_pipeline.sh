#!/usr/bin/env bash
# run_pipeline.sh — full generative path: image(s) -> watertight, color, printable 3MF.
#   1 image   -> TRELLIS single-image.
#   2+ images -> Step A consolidation (fuse refs -> 1 canonical image) -> TRELLIS single-image.
# Then: [optional Hunyuan-Paint re-texture] -> alpha-wrap repair -> COLOR 3MF deliverable.
#
# Usage: run_pipeline.sh <out_dir> <img1> [img2 ...] [--prompt "..."]
# Env:   TRELLIS_HOME (default /workspace/TRELLIS)
#        REPAIR_PY    (default /workspace/repair_mesh.py)
#        ALPHA_WRAP_BIN (default /workspace/alpha_wrap)   -- detail-preserving watertight repair
#        HY_PAINT=1   -- re-texture TRELLIS geometry with Hunyuan-Paint (bright delit PBR albedo)
#                        before repair (needs the Hunyuan install + hyvenv). Off by default.
set -euo pipefail
TRELLIS_HOME="${TRELLIS_HOME:-/workspace/TRELLIS}"
REPAIR_PY="${REPAIR_PY:-/workspace/repair_mesh.py}"
export ALPHA_WRAP_BIN="${ALPHA_WRAP_BIN:-/workspace/alpha_wrap}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:?usage: run_pipeline.sh <out_dir> <img...> [--prompt ...]}"; shift

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

# 1) generate geometry (+texture) with TRELLIS; REF = the image TRELLIS actually used.
if [ "${#IMGS[@]}" -eq 1 ]; then
  echo "[pipeline] single image -> TRELLIS"
  REF="${IMGS[0]}"
  run_trellis "$REF"
else
  echo "[pipeline] ${#IMGS[@]} images -> Step A consolidation"
  REF="$OUT/canonical.png"
  if [ -n "$PROMPT" ]; then
    python "$HERE/consolidate.py" "$REF" "${IMGS[@]}" --prompt "$PROMPT"
  else
    python "$HERE/consolidate.py" "$REF" "${IMGS[@]}"
  fi
  echo "[pipeline] consolidated -> $REF ; TRELLIS single-image on it"
  run_trellis "$REF"
fi

MESH="$OUT/model.glb"

# 2) optional: re-texture TRELLIS geometry with Hunyuan-Paint (bright delit PBR albedo).
if [ "${HY_PAINT:-0}" = "1" ]; then
  echo "[pipeline] Hunyuan-Paint re-texture (keeps geometry)"
  ( cd /workspace/Hunyuan3D-2.1 && \
    /workspace/hyvenv/bin/python "$HERE/run_hunyuan_paint.py" "$MESH" "$REF" "$OUT/model_pbr.glb" ) \
    && MESH="$OUT/model_pbr.glb" || echo "[pipeline] Hunyuan re-texture failed; using TRELLIS texture"
fi

# 3) repair: alpha-wrap -> watertight, detail-preserving -> COLOR 3MF deliverable.
echo "[pipeline] repair -> color 3MF ($MESH)"
python "$REPAIR_PY" "$MESH" "$OUT/printable"

echo "[pipeline] DONE -> $OUT/printable.3mf (color) + $OUT/printable_color.glb"
