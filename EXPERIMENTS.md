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
  locally that isnet-anime bg-removal PRESERVES the face** (root-cause fix for defect #1).
- 2026-06-04: `palette_quantize.py` rewritten (Lab k-means + flat per-face + ΔE). Verified locally on
  the old GLB: per-face regions are flat (splotch gone), and the ΔE check **proved the dark texture
  collapses 3/4 regions into browns** — color is the gating defect.
- 2026-06-04: built `color_correct.py` (gray-world WB + contrast stretch + saturation + gamma) and
  tested post-hoc rescue on the dark GLB. FINDING: correction can SEPARATE the 4 regions (ΔE rises,
  blue scarf 53→889 verts) BUT **distorts accuracy — the brown-dominant low-contrast model blows out
  to near-white** (mean 75→220) at any strength strong enough to separate. CONCLUSION: post-hoc
  correction is only a gentle final polish; brightness/contrast/accuracy MUST come from regeneration
  (source sRGB/gamma fix + delight, then a GENTLE resaturate on a good texture). Tool is ready for that.
- 2026-06-04 (more no-GPU fixes, parallel to the box wait — all built + checked, validate on box):
  - **Umbrella:** `preprocess_reference.py --top-crop` drops the overhead prop. Verified locally: the
    umbrella canopy is removed, face kept large. (Thin ribs at face height remain → SDXL inpaint later.)
  - **Geometry upgrade ready:** `gpu/install_trellis2.sh` + `gpu/run_trellis2.py` for **TRELLIS.2-4B**
    (O-Voxel, MIT, sharp geometry), grounded in the real API (`Trellis2ImageTo3DPipeline.run`,
    `o_voxel.postprocess.to_glb`). Flash-attn-on-3090 fallback to xformers handled. Needs box to build.
  - **Color-correct wired** into `run_pipeline.sh` (CC=1, gentle defaults) before quantize.
  - **Full-body decision:** default = **BUST** (MODE=bust) until an on-model full-body 2D ref is
    produced+approved (FLUX-Kontext/CharacterGen = optional E6). No 3D model is asked to invent legs.
- BLOCKED: GPU box (39215079) restart queued ~40min, slot not freed. Watcher polling to ~60min.
  Pending John: keep waiting (free, keeps install) vs rent fresh box (spend + reinstall). Next when box
  up: E1 (preprocessed bust, top-crop, SS_CFG 9, repair, 4-color, gentle CC), judge; then E4 (TRELLIS.2)
  if geometry still soft.

- 2026-06-04 **E1 RESULT (new box 39505355): FACE FIXED.** Preprocessed bust (isnet-anime/gray/top-crop)
  → TRELLIS preprocess_image=False, ss_cfg=9, 30 steps → `model.glb` (330k v / 538k f). Front render:
  the face now has real features — purple eye, eye-band, mouth/tongue, peace-sign hand — matching the
  reference. The #1 defect (blank mask) is SOLVED by the preprocessing fix. Remaining: still somewhat
  dark; an umbrella canopy remnant survives top-crop=0.18 (raise it / inpaint); repair step OOM-killed
  on the voxel fallback because alpha_wrap.cpp build path was wrong (FIXED install_alpha_wrap.sh to
  locate the .cpp in gpu/) — re-running repair (alpha-wrap, RAM-light) → color-correct → 4-color now.
  Next judge: the 4-color print render; then tune umbrella/color, consider E4 (TRELLIS.2) for geometry.

- 2026-06-04 **E1 fully judged.** After fixing repair (alpha_wrap build path; removed a 54GB/3min
  `m.split()` log hang): alpha-wrap repair → watertight 113k-face solid, fast. Color: the TRELLIS
  baseColorTexture is LINEAR (median 23/255 → near-black); **gamma 0.5 restores it** (mean 30→94,
  verified). 4-color: baked light/shadow made regions follow lighting (camo) → **chroma-weighted Lab
  k-means (LWEIGHT 0.3)** makes regions follow MATERIALS (blue scarf / rust hair / grey body). Both
  baked into defaults. VERDICT: face FIXED & recognizable, color recoverable, regions material-based —
  huge jump from faceless black blobs, but NOT yet acceptable: baked-highlight white blotches, the 4
  colors are muddy (subject is mostly brown/grey + 1 blue), umbrella remnant remains.
- 2026-06-04 **E3 (delighting) RUNNING:** `bootstrap_hunyuan.sh` installs Hunyuan3D-Paint + re-textures
  model.glb with delit (shadow-free) albedo → expect clean material color, no white blotches, 4 cleaner
  regions. Then repair + 4-color on the delit mesh. After: umbrella SDXL inpaint, and E4 (TRELLIS.2) if
  geometry still soft.

- 2026-06-04 **SPECKLE FIXED → clean vivid 4-color.** `palette_quantize.py` now COLOR-PRE-SMOOTHS
  (Laplacian blur of per-vertex colors over the mesh) before k-means → the delit texture's patchy
  artifacts average into CONTIGUOUS regions (solid brown hair / blue scarf / white coat / dark blue),
  not speckle. This + delighting + gamma + chroma-weight = a genuinely clean, vivid 4-color figurine
  with a real face. Consolidated to FINAL/ (figurine_4color.3mf + 4 material STLs + fullcolor_model.glb).
- 2026-06-04 **E4 TRELLIS.2 DEFERRED (env conflict).** Install ran (flash-attn built ~30min) but
  generation needs `DINOv3ViTModel` → transformers 5.x → **torch ≥2.6** (`float8_e8m0fnu`); TRELLIS-1
  needs torch 2.4.1. Hard conflict in the shared env. TRELLIS.2 would need its OWN torch-2.6 env +
  rebuilt flash-attn/o-voxel/CUDA-exts — big rabbit hole for uncertain geometry gain. Restored
  transformers 4.46.3 (TRELLIS-1/Hunyuan intact). Geometry sharpening parked behind this.
- **REMAINING (my honest quality verdict: GOOD, not perfect):** umbrella still attached (needs SDXL
  inpaint on the reference + a ~1hr full regen), geometry soft/lumpy (needs TRELLIS.2 = separate env),
  bust by design. Core deliverable (clean vivid 4-color figurine w/ real face) is achieved.

- 2026-06-05 **FULL-BODY v2, cheapest path first** (John: cheapest option, judge, escalate if short).
  `gpu/outpaint_fullbody.py` = SDXL-inpaint outpaint: keeps the waist-up pixels EXACTLY (identity free),
  generates only the legs below, IP-Adapter (scale 0.7) keeps them on-model. Result judged GOOD enough:
  upper body = exact original; legs = on-model dark leggings + bandage-wrap motif, standing. Minor: feet
  near bottom edge, legs a bit dark, faint bg seam at waist. Proceeding to 3D (full pipeline on the
  full-body ref: preprocess(full) → TRELLIS → Hunyuan delight → repair → color → 4-color). If 3D
  legs/feet are bad → escalate to FLUX-Kontext / give more canvas room for feet. RUNNING.

## Acceptance (when do we stop)
A rendered **4-color printable** where: the face has real features (eyes/mouth), color is bright and
matches the reference palette with 4 clean regions (no splotch), geometry is crisp, and nothing is
obviously invented. Judged by me each round against the reference; repeat until met.

- 2026-06-05 **GEOMETRY BREAKTHROUGH: Hunyuan3D-2.1 SHAPE >> TRELLIS-1.** Per John's escalate rule, before
  the TRELLIS.2 torch-2.6 rabbit hole I tried Hunyuan3D-2.1's SHAPE model (already-installed env, no
  conflict). Result on the full-body ref: 752k v / 1.5M f (~6× TRELLIS-1) and DRAMATICALLY sharper — real
  face with features, proper proportions, fingered hand, crisp boots, scarf-as-cape (no spiky tendrils).
  This is the college-grade geometry engine, and it's the CHEAPER escalation. New v2 pipeline:
  outpaint(core-crop) → `run_hunyuan_shape.py` → Hunyuan paint(delight) → repair(finer alpha REL_ALPHA 240)
  → color → 4-color. Running (out_fb2). TRELLIS.2 no longer needed for geometry.

- 2026-06-05 **VIEWING FIXED (John is on THIS Linux box):** F3D (installed) reads .glb/.stl/.ply but
  NOT .3mf (no 3MF reader) — that's why double-clicking the .3mf did nothing. Installed **MeshLab**
  (reads .3mf), set xdg-mime defaults (.3mf/.stl→meshlab, .glb→f3d). View a model:
  `f3d FINAL/print_files/figurine_fullcolor_lifelike.glb` or `meshlab <file.3mf>`.
- 2026-06-05 **"more lifelike":** the 4-color GLB looks abstract because printing forces 4 FLAT colors.
  Full-color per-vertex was NOISY (speckle). Fix: heavy Laplacian smoothing of the per-vertex colors →
  `figurine_fullcolor_lifelike.glb` (smooth natural colors). Next lever for MORE realism = the full
  UV-TEXTURED model (model_pbr, smoother than per-vertex) — needs a box restart; v2 UV-texture (G1) is
  the durable fix (per-vertex color is band-limited; RESEARCH_RENDERING_MATH.md).

- 2026-06-05 **FORM FIX (the real college-grade lever): clean A-POSE reference.** John: bare geometry was
  mid-high-school — blobby face, mitten hands, shard cape. ROOT CAUSE = the dramatic hand-on-face/flailing
  pose. FIX: SDXL+IP-Adapter regenerate the character in a CLEAN CALM A-POSE (832x1216, scale 0.4, face
  forward, arms relaxed, cape hanging) → Hunyuan-shape → form-preserving repair (finer alpha). RESULT:
  clean standing figure, REAL face shape, defined hands at sides, proper proportions, cape flows (no
  shards). Lifelike full-color = `figurine_apose_lifelike.glb`; 4-color = `figurine_apose_4color.glb`.
  Remaining: face soft at full-body scale, slight dress-color drift. Best result of the session.
- INFRA LESSONS (this box, vast.ai): (1) stop/restart is fragile — host "address already in use" port
  conflict can permanently brick a stopped instance (box 39505355). (2) HF download is throttled to
  ~1.3 KB/s per connection (hangs for hours) — **use aria2c -x16 -s16 (~138 MB/s)**, see
  `fetch_hunyuan_shape_weights.sh`. (3) consolidate.py scripts must NOT pipe through `tail` (swallows
  output/errors); run direct or to a file. (4) local SDXL at /workspace/_sdxl/sdxl-base (offline) avoids
  re-download. (5) John is ON the Linux box — view models with `f3d <file.glb>` (no 3MF reader; .3mf via
  MeshLab).

- 2026-06-05 **John review of the A-pose figurine — MORE WORK (see CHARACTER.md):**
  (1) HAT MISSING — her signature wide conical straw hat is in 5 of 6 sources; I used only 1 (umbrella img)
      and never looked at the rest. Fix: multi-image A-pose canonical (IP-Adapter on the hat sources) +
      explicit hat prompt. (2) Not enough DETAIL for a 150mm print — push fidelity. (3) Right HAND
      misshapen. (4) Snake-tongue detail noted (likely too fine to print). Box restart queued; regenerate
      when up. Reproducibility runbook = REPRODUCE.md. Hook now has step 4 = update docs.
