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

## Next

1. Send John the single-vs-multi comparison + the watertight `printable.stl` (in progress).
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
