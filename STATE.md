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

## Next

1. When Step A finishes: pull `out_consol/{canonical.png,model.*}`, render with F3D, send John the
   consolidation comparison (canonical image + resulting figurine vs single-image baseline).
2. Re-run `repair_mesh.py` to produce the colored watertight outputs (`*_color.glb/.ply`).
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
