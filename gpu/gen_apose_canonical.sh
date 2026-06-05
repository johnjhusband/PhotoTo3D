#!/usr/bin/env bash
# gen_apose_canonical.sh — RUN ON BOX. Generate a CLEAN, CALM, FRONT-FACING A-POSE full-body canonical
# of the character (SDXL + IP-Adapter from the original reference). The original art is a dramatic
# action pose (hand on face, flailing cape, umbrella) → that's what makes the 3D face/hands/cape bad.
# A calm A-pose with the face visible, hands relaxed, and the cape hanging straight gives clean form.
set -uo pipefail
cd /workspace
mkdir -p out_ap
python gpu/consolidate.py out_ap/canonical.png /workspace/ref.png \
  --prompt "full body illustration of a single anime girl standing in a calm neutral A-pose, arms relaxed and straight down at her sides slightly away from the body, facing forward, symmetric, both hands visible and open, long brown hair, purple eyes, blue scarf around the neck, grey ribbed knit dress, bandage-wrapped arms and legs, dark cape hanging straight down behind her, plain white background, full figure from head to feet, standing on both feet, centered, clean lineart, high detail" \
  --neg "umbrella, parasol, props, held objects, hand on face, covering face, dramatic action pose, dynamic pose, leaning, twisted torso, multiple characters, two people, cropped, out of frame, cut off, extra limbs, missing limbs, blurry, lowres" \
  --scale "${IPA_SCALE:-0.6}" --steps 40 --seed "${SEED:-3}" 2>&1 | tail -8
echo "APOSE_CANON_DONE"; ls -la /workspace/out_ap/canonical.png 2>/dev/null || echo NO_CANON
