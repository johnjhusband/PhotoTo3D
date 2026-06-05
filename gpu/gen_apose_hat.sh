#!/usr/bin/env bash
# gen_apose_hat.sh — RUN ON BOX. Multi-image clean A-pose canonical that INCLUDES the character's
# signature WIDE CONICAL STRAW HAT (kasa). The first attempt used one source (umbrella image) and
# dropped the hat — here we condition IP-Adapter on the HAT-bearing sources and demand the hat in the
# prompt. Needs the hat source images at /workspace/cands/ (download.png, Htvy.png, OIP.png).
set -uo pipefail
cd /workspace
mkdir -p out_ap
export SDXL_PATH="${SDXL_PATH:-/workspace/_sdxl/sdxl-base}" IPA_PATH="${IPA_PATH:-/workspace/_sdxl/ip-adapter}"
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}" TRANSFORMERS_OFFLINE="${TRANSFORMERS_OFFLINE:-1}" PYTHONUNBUFFERED=1
HEIGHT=1216 WIDTH=832 \
python gpu/consolidate.py out_ap/canonical.png \
  /workspace/cands/download.png /workspace/cands/Htvy.png /workspace/cands/OIP.png \
  --prompt "full body wide shot of a single anime girl head to toe, wearing a WIDE CONICAL STRAW HAT (kasa, sedge hat, large round woven straw hat on her head), thin horizontal band across the eyes, purple eyes, long brown hair, blue scarf around the neck, grey ribbed knit dress, bandage-wrapped arms and legs, dark cloak, standing upright in a calm neutral A-pose, arms relaxed at her sides, facing forward, both feet visible, full figure, centered, plain background, high detail" \
  --neg "no hat, hatless, bald, umbrella, parasol, hand on face, dramatic action pose, dynamic pose, cropped, cut off at waist, multiple characters, extra limbs, deformed hands, blurry, lowres" \
  --scale "${IPA_SCALE:-0.5}" --steps "${STEPS:-35}" --seed "${SEED:-7}" 2>&1 | grep -aE "consolidate\]|Error|Traceback"
echo "HAT_CANON_DONE"; ls -la /workspace/out_ap/canonical.png 2>/dev/null || echo NO_CANON
