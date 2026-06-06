# AI fork — text→2D→3D→4-color (the new approach)

**Branch:** `AI` (the `maths` branch preserves the old IP-Adapter/texture-transfer pipeline that came
out splotchy). Decided 2026-06-05 after John judged the math-built renders too splotchy: "even the
simplest image described by text on an AI image generator would be better."

## Why
The splotch came from the MATH path: IP-Adapter consolidation of mismatched source art + Hunyuan delit
texture baked to per-vertex color + k-means palette. Replacing the noisy 2D reference with a CLEAN
AI-generated, flat-colored 2D image removes the noise at the source — cleaner input → cleaner 3D →
trivial 4-color reduction.

## Pipeline
1. **Inspect → prompt** (done by a vision model, me): read all 6 `candidates/` images, keep the common
   features, drop conflicting props. Result = one text prompt (see `pipeline/gen_ai_reference.py`
   `DEFAULT_PROMPT`). Character: wide conical straw hat (kasa), thin band across the eyes, violet eyes,
   long dark-brown hair, cobalt-blue knit scarf, grey ribbed knit sweater-dress, dark charcoal cloak,
   purple-grey arm/leg bandages, sandals. Dropped: the umbrella (a held prop in 1 image) and the snake
   tongue (too fine to print).
2. **Text → clean 2D**: `pipeline/gen_ai_reference.py` → OpenAI **gpt-image-1**, portrait 1024x1536,
   flat cel-shade, plain white bg, full-body A-pose. ~$0.01–0.04/image. Key: `OPENAI_API_KEY` (lives in
   `CTO/.env`; John's existing key — no new account needed). First output: `AI_out/ref_ai_v1.png` (clean).
3. **2D → 3D**: reuse Hunyuan3D-2.1 SHAPE (`run_hunyuan_shape.py`, octree 384) — same as the maths fork.
4. **Color → 4 regions**: `palette_quantize.py` (now with island-removal speckle fix). The flat AI
   colors reduce cleanly to 4.

## Cheap AI image-gen options (researched 2026-06-05)
- **gpt-image-1** (OpenAI) — key on hand, ~$0.01 (low) – $0.04 (medium)/image. CHOSEN (no new credential).
- gpt-image-1-mini — ~$0.005/image, also available on the same key.
- Flux Schnell / Flux 2 Flex (fal.ai, Replicate, SiliconFlow) — $0.003–0.015/image, better anime style,
  but needs a NEW account/key. Hold in reserve if gpt-image-1 style isn't anime enough.

## Style variants (gen_ai_reference.py supports two modes)
- **Text-only** (`generations`): flat cel-shade, plain bg — BEST for 3D + 4-color. `ref_ai_v1.png`,
  `ref_ai_v2.png` (v2 = clear eye-band + bandages + open A-pose).
- **Image-conditioned** (`--ref <source imgs>` → `edits` endpoint): matches the SOURCE art style.
  `ref_source_style.png` = moody/painterly, violet-blue, glowing eyes, **forked snake tongue** (John
  wanted it shown). `ref_photoreal.png` = photorealistic, kept SEPARATE (heavy realism/shadow may not
  reconstruct in 3D — John's call).

## Key tradeoff (surfaced to John 2026-06-05)
Flat clean input → clean 3D + easy 4-color. Moody/source-consistent input is dark & low-contrast =
the exact thing that made early 3D muddy. So: drive the 3D off the FLAT reference for a clean print and
treat the moody/photoreal images as the "look" target — OR push the moody one through 3D to see. Awaiting
John's pick. Snake tongue is in the 2D; at 150 mm it is likely below printable detail (noted before).

## Status
2D stage validated, 4 style variants in `AI_out/`. v1 (flat) running through 3D now (clean path).
Next: judge v1 3D → palette-to-4 → 150mm print set → FINAL on the AI branch (style per John's pick).
