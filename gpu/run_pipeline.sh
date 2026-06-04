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

# 0) PREP=1: clean the reference ourselves (isnet-anime bg removal on gray + bust crop) so TRELLIS's
# photo-trained rembg never eats the pale anime face. MODE=bust (default) uses the face-filling crop;
# MODE=full uses the whole subject. Sets PREPROCESS=0 so TRELLIS keeps our cleaned ref as-is.
if [ "${PREP:-0}" = "1" ] && [ "${#IMGS[@]}" -eq 1 ]; then
  echo "[pipeline] PREP: preprocess_reference (isnet-anime, gray, ${MODE:-bust} crop)"
  python "$HERE/../pipeline/preprocess_reference.py" "${IMGS[0]}" "$OUT/_prep" --bg gray
  case "${MODE:-bust}" in
    full) IMGS=("$OUT/_prep/ref_full.png") ;;
    *)    IMGS=("$OUT/_prep/ref_bust.png") ;;
  esac
  export PREPROCESS=0
  echo "[pipeline] PREP done -> ${IMGS[0]} (PREPROCESS=0)"
fi

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

# 4) palette-to-N: reduce to exactly N flat color REGIONS for the multi-material print (N=4 settled).
# Quantizes in CIE-Lab + flat per-face (no splotch). Runs on the COLORED repaired GLB.
NCOLOR="${NCOLOR:-4}"
if [ -f "$OUT/printable_color.glb" ]; then
  echo "[pipeline] palette-to-$NCOLOR (4-color print deliverable)"
  python "$HERE/../pipeline/palette_quantize.py" "$OUT/printable_color.glb" "$OUT/print_${NCOLOR}color" "$NCOLOR" || \
    echo "[pipeline] palette_quantize failed (non-fatal)"
fi

echo "[pipeline] DONE -> $OUT/printable.3mf (full color) + $OUT/print_${NCOLOR}color.3mf ($NCOLOR-region print)"
