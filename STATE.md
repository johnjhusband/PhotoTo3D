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

- Printer profile (spool count N, build volume, loaded filament colors, color-vs-paint) — needed for
  stages 4–6. Per-job input; do NOT assume a specific printer.
- Reusable-tool packaging shape (CLI? web upload?) — not yet specified; don't invent it.

## Cost note

Instance **39215079 is running and billing (~$0.20/hr).** Destroy it when not actively needed
(`vastai destroy instance 39215079`); reuse via a committed Docker image. SSH/ops gotchas: see
TROUBLESHOOTING.md (use the direct endpoint, bracket-trick pkill, setsid for detached launches).
