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

## Status
2D stage validated. `AI_out/ref_ai_v1.png` = first clean output; `AI_out/ref_ai_v2.png` = **chosen
reference** (stronger prompt: clear blindfold eye-band, visible spiral arm/leg bandages, open A-pose so
hands reconstruct). v1 is running through 3D as a splotch-check comparison; v2 is the definitive run.
Next: judge v1 3D → run v2 3D → palette-to-4 → 150mm print set → FINAL on the AI branch.
