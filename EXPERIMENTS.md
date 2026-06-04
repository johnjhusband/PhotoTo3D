# EXPERIMENTS.md — iterate-until-good log for the 4-color printable figurine

John's directive (2026-06-04): "render a 4-color printable 3D file, look at it, determine if it's good
quality, if not repeat until it is. Iterate continuously until you have created an acceptable solution."
Others have solved this → it's possible. This file is the live experiment log + the research that drives it.

## The four defects (from looking at the actual output) and their researched fixes

### 1. FACE = blank white mask (the #1 defect)
Root cause: the OLD pipeline used TRELLIS's built-in rembg (u2net, photo-trained), which clips a PALE
anime face against a WHITE background; a waist-up frame also makes the face too small to survive
structure binning.
Fix (built in `pipeline/preprocess_reference.py`, VERIFIED locally — face is preserved):
- bg removal with **isnet-anime** (not photo model), composite on **mid-gray** (not white).
- tight **bust crop** so the face fills the frame.
- feed TRELLIS with `preprocess_image=False` so it does NOT re-remove bg with the bad model.
- TRELLIS settings: ss steps 25–30, **ss_guidance 9–10** (was 7.5), slat_guidance 3.0, texture_size 2048,
  mesh_simplify ≥0.97, try 3–5 seeds.
- anime upscale = `RealESRGAN_x4plus_anime_6B` (NOT GFPGAN/CodeFormer — they destroy anime faces).
- STILL TODO: the **umbrella** the character holds is kept by bg-removal and would become geometry →
  must inpaint it out (SDXL/FLUX inpaint on the box).

### 2. FULL BODY = invented legs/dress/boots (reference is waist-up only)
Fix: never let the 3D model invent. Complete the reference in **2D first**, then go to 3D:
- **FLUX.1-Kontext-dev outpaint** (identity-preserving uncrop) waist-up → full body, OR
- **CharacterGen** (Apache-2.0, anime-native, single image → A-pose multi-view) for a full character.
- Gate: confirm it's still the character; if it drifts → **ship the BUST** (a faithful bust beats an
  unfaithful full body). Default for now: **bust**, until a full-body 2D ref is approved.

### 3. COLOR = dark/muddy + splotchy 4-color
- Darkness = likely **sRGB↔linear double-gamma** bug on the baseColor read (fix first, cheap) + baked
  TRELLIS shading (delight) + albedo flattening (re-saturate toward the bright reference).
- Splotchy 4-color = **per-vertex barycentric interpolation** in the 3MF. Fix: k-means in **CIE-Lab**
  (k=4) on the **texture image**, recolor to 4 flats, assign color **PER-FACE** (not per-vertex). Keep
  color as texture as far as possible; per-face kills the bleed.

### 4. GEOMETRY = soft/low detail
- Upgrade model: **TRELLIS.2-4B** (May 2026, **MIT**, "O-Voxel" sharp geometry + PBR, fits 3090 ~18GB
  at 512³) is the in-family fix. **StdGEN** (Apache-2.0) is the anime-specialized alternative (forces
  A-pose). Hybrid: TRELLIS.2 geometry + Hunyuan3D-2.1 texture if color still weak (US-licensing only).

## Experiment ladder (cheapest/highest-leverage first; stop when a 4-color print looks good)

- **E1 — preprocessing + current TRELLIS, BUST.** New `preprocess_reference.py` (isnet-anime, gray,
  bust crop) + `preprocess_image=False` + ss_guidance 9, texture_size 2048. Tests whether the face is
  fixed with zero new model installs. (Umbrella still present — first see if face reconstructs.)
- **E2 — add umbrella inpaint** (SDXL/FLUX) to the bust ref, re-run E1.
- **E3 — color fix:** gamma check + Lab k-means(4) on texture + per-face 3MF. Render the 4-color print.
- **E4 — if geometry still soft:** swap to TRELLIS.2-4B.
- **E5 — if color still weak:** TRELLIS.2 geometry + Hunyuan3D-2.1 texture-only.
- **E6 — full body (optional):** FLUX-Kontext outpaint or CharacterGen, gated; else stay bust.

## Log
- 2026-06-04: research done (4 parallel streams, cited). `preprocess_reference.py` built; **verified
  locally that isnet-anime bg-removal PRESERVES the face** (root-cause fix for defect #1). Next: restart
  box, run E1.

## Acceptance (when do we stop)
A rendered **4-color printable** where: the face has real features (eyes/mouth), color is bright and
matches the reference palette with 4 clean regions (no splotch), geometry is crisp, and nothing is
obviously invented. Judged by me each round against the reference; repeat until met.
