# AGENTS.md — Your operating manual

What you do, what you own, and the tools/infra to do it. Read SOUL.md first (who you are), then this.

## What this project is

A **reusable tool**: inputs are (1) image(s) of a subject and (2) a printer profile; output is a
file that prints correctly on that printer. You orchestrate; heavy models run on disposable rented
GPU compute. Full flow is in DESIGN.md.

## Two subject types → two engines

- **Concept art / a single image (CURRENT FOCUS):** generative — **Microsoft TRELLIS** (MIT) on a
  GPU. It *imagines* a plausible full 3D form. Code in `gpu/`.
- **Real photos of a real object (NOT ACTIVE):** photogrammetry — COLMAP + OpenMVS on CPU. Faithful
  measurement. Code in `pipeline/`. The CPU server was deleted; this path is dormant but the scripts
  remain for when real-object photos are the input.

## What you own end-to-end

Stages 1–4 of DESIGN.md plus slicing-to-G-code:
1. **Input curation** — `pipeline/prep_images.py` (cull blur, mask background); optional text-guided
   reference editing via an inpainting model.
2. **Generation** — `gpu/run_trellis.py` (single or multi-image → textured GLB → STL/3MF).
3. **Mesh repair for printing** — `pipeline/repair_mesh.py` (+ Blender headless for geometry edits;
   artistic edits = script→render→look loop).
4. **Palette-to-N color** — quantize the texture to N = the printer's spool count, snap to real
   filament colors, bake per-region into 3MF. *(Stage to be implemented; spool count is an input.)*
5. **Slicing** — slicer CLI (OrcaSlicer/PrusaSlicer/Cura) with the printer profile → G-code.

**John owns:** the physical print, and fussy artistic hand-finishing.

## Tools & commands

- **vast.ai** (GPU rental). CLI at `.venv/bin/vastai`. `unset VAST_API_KEY` first or the shell env
  overrides the saved key. Search → `vastai search offers '...'`; rent → `vastai create instance`;
  list → `vastai show instances`; kill → `vastai destroy instance <id>`.
- **GPU box install** — `gpu/install_trellis.sh` (TRELLIS + CUDA deps on a pytorch-cuda-devel image).
- **GPU box run** — `gpu/run_trellis.py <out_dir> <img...>` (multi-image auto when >1).
- **CPU photogrammetry** — `pipeline/run.sh <images_dir> <work_dir>` (dormant).
- **Hetzner** (CPU infra, if revived) — `deploy/provision-? `, `deploy/park.sh` / `deploy/wake.sh`.

## Infrastructure & secrets

- **Secrets** in `.env` (gitignored): `VAST_API_KEY`. Hetzner token lives in `~/repos/CTO/.env`
  (`HETZNER_API_TOKEN`). Never commit secrets.
- **SSH** to rented boxes uses `~/.ssh/cto-deploy` (its public key is registered on the vast account).
- **GitHub**: repo is `johnjhusband/PhotoTo3D` (public). The git **SSH key is read-only** — push over
  HTTPS: `gh auth setup-git && git remote set-url origin https://github.com/johnjhusband/PhotoTo3D.git`.

## Cost control (critical)

- **vast.ai:** "stop" still bills storage every second. **Delete** to stop all charges. To reuse
  without paying to idle: `docker commit` the box → push image to a registry (plan: GHCR under
  johnjhusband) → destroy instance → recreate from the image next time.
- **Hetzner:** power-off does NOT stop billing; only deletion does. `park.sh` snapshots then deletes.
- **Default behavior:** destroy rented compute as soon as a job is done. Never leave a GPU running.
