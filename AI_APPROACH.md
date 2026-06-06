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

## Status — AI FORK VALIDATED, hands FIXED, watertight (2026-06-05)
Clean flat AI 2D ref → 3D is MUCH cleaner than the maths fork (no splotch patchwork). Iterations:
- v1 (arms-down ref, alpha 320): clean but HANDS FUSED into the cape (alpha-wrap bridged the gap).
- **v2b (arms-out v2 ref, alpha 360): CURRENT DELIVERABLE** — hands separated from the cape, watertight,
  island-removal speckle cleanup. (alpha 440 separated hands but broke watertight; 360 is the sweet spot.)

`AI_out/` is reorganized (2026-06-05, John "clean it up"):
- `2d_references/` — ref_ai_v1, ref_ai_v2, ref_source_style, ref_photoreal (4 PNGs).
- `3d_renders/`   — 3d_lifelike_front, 3d_4color_front, 3d_lifelike_34 (the v2b figurine).
- `3d_models/`    — figurine_ai_lifelike.glb, figurine_ai_4color.glb (v2b).
- `print_files/`  — figurine_ai_4color_150mm.3mf + _150mm.stl + material1-4_*.stl. Watertight, 58×150×54mm.

Residual: 4-color still lumps skin+dress+legs into one grey region — the HAT-PUZZLE split (separate straw
hat + skin-tone body) is the path to a real skin tone. Snake tongue is 2D-only (too fine at 150mm).
Bambu: loads our 3MF (load+re-export exit 0); headless slicer segfaults w/o a display; GUI double-click
is John's to confirm. .3mf association + home access set (see TROUBLESHOOTING).

## Google Drive sync — LIVE
`gdrive:` remote (rclone) → folder `1INrnKYrmYm9DwYDbhvaKUZ_AK9nSjhIu`, token in `~/.config/rclone/`.
`bash pipeline/sync_to_drive.sh` mirrors `AI_out/` (subfolders included). Drive now mirrors the clean
structure. Re-run after each new batch. Setup details in TROUBLESHOOTING.

## Hat-as-puzzle-piece (in progress)
`pipeline/split_hat_puzzle.py` — mortise-tenon cube join so the hat prints straw and the body skin tone.
Booleans (manifold3d) were hanging on the 200k mesh; debugging the fill_holes/boolean step.
