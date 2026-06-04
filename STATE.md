# STATE.md — Live status

**Last updated:** 2026-06-03 by Claude. Keep this current; it is the working memory a fresh instance
inherits. Observed facts only — no guesses.

## Direction (locked)

Reusable tool: images + printer profile → printable file. Printer (spool count N, build volume,
filament colors, color-vs-paint) is a parameter. Current input type: concept art → TRELLIS.

## Done

- Research complete; generative-not-photogrammetry decided (DECISIONS #2).
- Repo created and public: https://github.com/johnjhusband/PhotoTo3D (push over HTTPS — SSH key is RO).
- vast.ai account funded ($25), API key saved in `.env` and `~/repos/CTO/.env`. `vastai` CLI in `.venv`.
- GPU rented: instance **39215079**, RTX 3090, **running**, SSH `ssh9.vast.ai:15078`, key `~/.ssh/cto-deploy`.
- CPU photogrammetry server deleted (path dormant; scripts kept).
- Context system written (CLAUDE/SOUL/AGENTS/DESIGN/DECISIONS/STATE/README).
- Reference image chosen: `candidates/gXAmE1Bn2dubu5B-OCEe4.png` (umbrella illustration); runner
  updated for multi-image.

## DONE — pipeline works end to end (2026-06-03)

- TRELLIS install fully working on instance 39215079 (xformers backend; all CUDA extensions built).
  Every install pitfall hit + fixed is in TROUBLESHOOTING.md; all fixes committed to install scripts.
- **Single-image** generation from the umbrella ref → `out_single/` (glb/stl, preview.mp4, montage).
  Recognizable character; umbrella excluded by bg-removal. Sent to John. ~72k-face raw mesh.
- **Multi-image** generation over the candidate set → `out_multi/`. LOWER detail (~21k faces) — the
  mixed art styles hurt it, as expected. Single best image is the better input here.
- **Watertight printable** produced via `repair_mesh.py` (voxel-remesh → one solid → smooth →
  decimate → pymeshfix): `out_single/printable.{stl,3mf}`, 199,908 faces, watertight=True. Pulled to
  laptop.

## Added this cycle (2026-06-03)

- **F3D** installed on the laptop (apt) — mesh viewer + headless renderer. Render flags in TROUBLESHOOTING.
- **Color requirement** ("we need color"): `repair_mesh.py` now transfers GLB texture color onto the
  watertight solid → `*_color.glb`/`*_color.ply` (needs a fresh repair run on the box to produce them;
  the existing `out_single/printable.*` predate the color edit). Sent John lit color renders of model.glb.
- **Step A consolidation** built (`consolidate.py` SDXL+IP-Adapter, `run_pipeline.sh`, `install_consolidate.sh`)
  and RUNNING on the box over the 6 candidates with an LLM-written character prompt → `out_consol/`
  (currently downloading SDXL). Will produce `canonical.png` + a 3D model to compare vs single/multi.

## Step A run note (2026-06-03)

First consolidation run STALLED on a hung Hugging Face SDXL download (process alive but frozen 30+ min;
process-presence watcher couldn't detect it). Restarted via `launch_consol2.sh`: pre-downloads SDXL +
IP-Adapter with resume + retry loop + `HF_HUB_DOWNLOAD_TIMEOUT=30`, then runs the pipeline. New watcher
is **stall-aware** (log-mtime + markers + process). End-of-turn Stop hook for repo sync is now live.

## Done since (2026-06-03, color)

- Color-transfer repair RUN: `out_single/printable_color.{glb,ply}` (watertight + color, 199,908 faces).
- **Stage 4 palette-to-N RUN** at N=4 → `out_single/pal_4color.{glb,ply}` + 4 per-color STLs
  (`pal_part{0-3}_<hex>.stl`). Sent John. Finding: 4 colors all dark (source texture is dark/low
  contrast) → effectively hair-vs-body. Lever: supply explicit filament colors + region mapping.

## QUALITY PASS (2026-06-03) — defect backlog from deep-research, implementing all

Research report (verified) → fix backlog. Status:
1. **Cape/detail (DONE)** — CGAL alpha-wrap repair (`gpu/alpha_wrap.cpp`, `repair_mesh.py`), preserves
   thin features. Validated sharper. Committed.
2. **Color 3MF (DONE)** — `gpu/export_color3mf.py` (lib3mf, real slicer-readable color; trimesh can't).
   Built+tested by a parallel agent. Committed. TODO: wire into pipeline as the deliverable, drop STL.
3. **Color QUALITY (IN PROGRESS)** — Hunyuan3D-Paint re-texture. KEY: paint-only re-textures our
   EXISTING TRELLIS mesh (`use_remesh=False`), ~21GB VRAM (fits 3090, texture-only). Only need the
   paint model (`tencent/Hunyuan3D-2.1` → `hunyuan3d-paintpbr-v2-1/*`, ~7GB) — NOT the shape model.
   Downloading to `/workspace/_hunyuan/weights` (curl-stream) + repo tarball. Recipe in git history of
   this commit / agent output. Run: `Hunyuan3DPaintPipeline(...)(mesh_path, image_path, use_remesh=False)`.
   Build its 2 CUDA exts (`custom_rasterizer`, `DifferentiableRenderer`) in a SEPARATE venv with
   `--no-build-isolation`. License: Tencent community (excludes EU/UK/SK, 1M MAU cap — fine for us).
4. **PBR-SR (DEPRIORITIZED)** — needs separate CUDA-11.8 env; Hunyuan-Paint already gives higher-res
   texture. Optional polish later. Fallback: Real-ESRGAN on the UV map (BSD, <1GB).

Parallelism note: used 3 parallel agents to produce recipes 2/3/4 concurrently — works for prep, but
GPU runs serialize on the one box. Box network is the recurring blocker (downloads stall/collapse
intermittently; SSH stays up). Resumable curl + rsync is how we get past it.

## (superseded) earlier quality-pass note

John: outputs "still have a ways to go." Concrete gaps to fix:
- Color is dark, low-contrast, muddy, inaccurate (GLB contrast poor).
- Voxel-remesh repair TRUNCATES thin features — full-body cape cut off at the shoulders.
- Geometry soft/low-detail.
- Output format: switch to **color 3MF** as the single deliverable, DROP STL (DECISIONS #19). Current
  3MF is geometry-only (trimesh limitation) — needs a real color-3MF writer (lib3mf).
Deep-research running on improvements (better models like Hunyuan3D-2.1/Hi3DGen/Step1X-3D, detail-
preserving watertight repair like alpha-wrap/ManifoldPlus, texture/color quality). Apply findings next.

Hooks now live (~/.claude): Stop hook cleanup (sweeps render frames/empty dirs) + repo-sync.

## FULL-BODY FIGURINE achieved (2026-06-03)

Got the head-to-toe figurine John wanted. Recipe (see DECISIONS #18): consolidate at low IP scale
(0.4) + "full figure head to toe" prompt → SDXL full-body sheet → crop central figure (`out_consol/
fb_final.png`) → HQ TRELLIS → `out_fb/` (model + watertight `printable.stl` 79k faces + color). Sent
John the render. Quality: complete figure but softer/lower-detail than the busts. Key fact: only 1 of
6 inputs (the 120x98 pixel sprite `OIP (1).png`) is full-body — the rest are portraits.
Open quality dial: high IP scale = faithful bust; low IP scale = full body but softer.

## Consolidation pipeline WORKS (2026-06-03)

SDXL+IP-Adapter consolidation runs end-to-end on the box from a LOCAL copy of SDXL (11GB, curl-streamed
on laptop → rsync to /workspace/_sdxl; no HF on the box). Fixes that got it working: `ip_adapter_image=[refs]`
(single adapter, multi-image), local SDXL_PATH/IPA_PATH, HF_HUB_OFFLINE=1. Output `out_consol/`:
`canonical.png` (clean fused character — cleaner than any single input) + figurine (cleanest BUST yet).
STILL a portrait/bust, not full-body: IP-Adapter scale 0.7 followed the portrait references over the
"full figure head to feet" prompt. **Next lever:** lower IP-Adapter `--scale` (~0.4) so the prompt's
full-body framing dominates (trades some character fidelity). Iterate the canonical (SDXL-only, ~30s,
cheap) BEFORE running TRELLIS.

## HQ re-run done (2026-06-03) — improved but still a bust

High-quality re-run (STEPS=30, TEX=2048, enhanced/autocontrast reference, repair voxel_div=256) →
`out_hq/{model.glb, printable.stl, printable_color.glb}`. Clearly better than first pass: cleaner
geometry, brighter scarf, readable sweater/bandages/face, less muddy. Sent John. STILL a BUST (upper
body) because the reference is upper-body — input is the hard ceiling. **Lever for a full figurine:**
the SDXL consolidation prompt asks for "full figure head to feet", so SDXL can GENERATE a full-body
canonical reference from the upper-body art — this is why the SDXL download matters for quality, not
just multi-image.

Laptop SDXL download (to bypass the box's broken HF path) stalled at 4.1GB; restarted robustly
(`_hfcache/robust_dl.sh`, timeout+retry). When done → rsync `_hfcache` to box → run consolidation.

## QUALITY: outputs not yet acceptable (John, 2026-06-03)

John: "None of the output is acceptable quality yet." Two ceilings: (1) input image quality — the
umbrella ref is upper-body, dark, cluttered (umbrella prop), so TRELLIS gives a dark bust with an
invented blobby back; (2) I ran fast/low settings (12 steps, 1024 texture, voxel_div 192). Plan:
high-quality re-run on a CLEANED input (crop umbrella, boost contrast, rembg) at 30 steps + 2048
texture (run_trellis now reads STEPS/TEX env) + finer repair (raise voxel_div). Input is the hard
ceiling — a clean full-body reference would help most. Spend so far: **$3.95** of $25 vast credit.

## BLOCKED: Step A consolidation on this box

SDXL download is impossible on instance 39215079 (HF main 20× + hf-mirror 8× all failed, ~2h GPU
wasted). Consolidation cannot run here. **Awaiting John's call (2026-06-03):** wrap up (docker-commit
+ destroy box, single-image + 4-color are the deliverables) vs. push SDXL from laptop via rsync.
Single-image path is unaffected and is the working deliverable.

## Next

1. Per John's decision: either docker-commit + destroy box, OR rsync SDXL laptop→box then run Step A.
2. When/if Step A runs: pull `out_consol/{canonical.png,model.*}`, render with F3D, send comparison.
2. If John wants vivid color: add explicit-target-filament-color mapping to `palette_quantize.py`.
3. GPU box still billing — offer docker-commit + destroy when John is done reviewing.
2. **Decide with John: keep generating / iterate, or wrap up.** If wrapping: `docker commit` the box
   → push image to a registry (GHCR under johnjhusband) → `vastai destroy instance 39215079` to stop
   billing. Reuse later from the image.
3. Build the **palette-to-N** color stage (input: spool count) — needs John's printer profile.
4. Remaining mesh-repair extras (scale to build volume, base, hollow, min-wall-thickness, split).

## Open questions for John

- Spool count: ANSWERED — N=4. Filament colors: N/A (slicer-time, swappable — never ask). Build
  volume + color-vs-paint still per-job inputs for a *different* printer; do NOT assume a specific one.
- Reusable-tool packaging shape (CLI? web upload?) — not yet specified; don't invent it.

## Cost note

Instance **39215079 STOPPED 2026-06-04** (`vastai stop instance 39215079`) — compute billing halted,
disk preserved, restart on demand (`vastai start instance 39215079`) AS LONG AS that GPU slot is still
free. John's call: stop (not destroy) until he likes the images; destroy+Docker-image is NOT the path
yet. Small storage fee continues while stopped. Use `vastai show instances-v1` (the old `show instances`
is deprecated/410). SSH/ops gotchas: see TROUBLESHOOTING.md.

## Quality pass COMPLETE (2026-06-04) — all 4 backlog fixes implemented, honest caveats

1. Cape/detail: CGAL alpha-wrap repair — DONE, tested (sharper, watertight).
2. Color-3MF deliverable, STL dropped — DONE, tested.
3. Hunyuan-Paint re-texture — DONE end-to-end (install + run, `model_pbr.glb`). Delit albedo is correct
   (white coat white, etc.) but only a MODEST brightness gain — the character is inherently dark.
   Good color lives in the textured GLB. CAVEAT: converting the UV texture to PER-VERTEX color in
   repair is lossy/splotchy (saturated purple scarf bleeds). For real multi-color PRINTING this is
   moot — `palette_quantize.py` (palette-to-N) reduces to N clean filament regions, the actual print
   color path. `repair_mesh.py` now samples the albedo texture at UVs (not trimesh to_color which
   mishandles multi-map PBR).
4. PBR-SR: deprioritized (Hunyuan texture supersedes; needs separate CUDA-11.8 env).

Reproducible: `gpu/run_pipeline.sh ... ` (HY_PAINT=1 for re-texture). Hunyuan install = `gpu/install_hunyuan.sh`.
Spend so far ~$5.5 of $25 vast credit. Box still up.

## 4-MATERIAL DELIVERABLE SHIPPED (2026-06-04)

Produced and delivered to John: `FINAL/figurine_4material.3mf` (4 distinct color REGIONS, 15673 v /
31354 tris, written by `gpu/export_color3mf.py`) + `FINAL/material1..4.stl` (same regions split per
material). Path: Hunyuan albedo GLB → `palette_quantize.py` to 4 colors → `export_color3mf`.

**N=4 is SETTLED — do not re-ask spool count.** In multi-material printing only the N color *regions*
go in the file; the physical filament color per slot is chosen in the slicer at print time and is
swappable. NEVER ask John which filament color goes where, and NEVER ask the spool count again.
(See memory `feedback_multicolor_print_regions_not_filament_colors`.) John's words: "i have four
spools 4 colors it's fucking 4! You don't fucking need to know what the fuck the colors are because
they can be changed based on the need of the print!"

## Folder hygiene (2026-06-04) — for QA, look ONLY in FINAL/

Cleaned up per John ("clean up after yourself"). The single place to QA outputs is **`FINAL/`**:
- `1_FULLBODY_render.png`, `2_BUST_render.png`, `3_4COLOR_render.png` — the QA images (3 angles each).
- `1_FULLBODY_color.glb`, `2_BUST_color.glb` — full-color models. `*_printable.stl` — watertight geometry.
- `figurine_4material.3mf` + `material1..4.stl` — the 4-region print deliverable.
Inputs live in `candidates/` (the 6 fw.zip refs) + `samples/_montage.png`. Everything else was scratch.
DELETED the `_qa/` scratch folder (intermediate + FAILED Hunyuan re-texture renders — the 06-04 Hunyuan
per-vertex color came out splotchy/magenta, WORSE than the clean 06-03 deliverable) and the superseded
`FINAL/pal_part*` STLs (old dark palette; `material*.stl` is the brighter Hunyuan-albedo palette-to-4).
All regenerable from the box. NOTE: best color currently is the pre-Hunyuan textured GLB; the Hunyuan
re-texture did not improve the final per-vertex/printable color. Color quality is the open QA item.

NEXT (needs John): printer profile (spool count) to run palette-to-N for the real color print; decide
whether the modest Hunyuan color gain is worth keeping in the default path or only the textured-GLB view.

## Print-color path VALIDATED (2026-06-04)
Hunyuan albedo → `palette_quantize.py` N=4 → 4 CLEAN distinct filament regions (white coat #cdc3d4,
purple scarf #8d66af, dark dress #452e43, near-black #13090d) — NO splotches. Proves the per-vertex
artifact is resolved by quantizing to N filament colors (the real multi-color print path). Sent John.
Blocked on John: real spool count + loaded filament colors to snap the palette; box park/destroy decision.

