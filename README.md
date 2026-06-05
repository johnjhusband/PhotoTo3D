# PhotoTo3D

**Current result + how to reproduce it: see [REPRODUCE.md](REPRODUCE.md).**
It documents the working end-to-end pipeline (single image → clean A-pose 2D ref → Hunyuan3D-2.1 shape →
delit color → watertight repair → 4 flat print regions → scaled STL/3MF). Live status in STATE.md, the
full experiment log in EXPERIMENTS.md, and the math/rationale in RESEARCH_RENDERING_MATH.md.

---

_(Older overview below — predates the A-pose/Hunyuan pipeline.)_

# PhotoTo3D

Turn 2D images into 3D-printable mesh files (STL / 3MF), using only open-source software.
An LLM agent orchestrates the pipeline; disposable rented GPU compute runs the heavy models.
**No paid 3D-generation service** — the only costs are raw infrastructure (hourly GPU) and optional LLM API tokens.

## Two pipelines, two jobs

There is no single "image to 3D" tool — the right one depends on what your images *are*.

### 1. Real photos of a real object → photogrammetry (CPU)
`pipeline/` — measures geometry by triangulating the same physical points across many
overlapping photographs. Faithful reconstruction. CPU-only, runs on a plain Linux VPS.

- `prep_images.py` — cull blurry frames, optional background removal
- `photogrammetry.sh` — COLMAP (Structure-from-Motion) → OpenMVS (dense mesh + texture)
- `repair_mesh.py` — pymeshfix/pymeshlab → watertight STL/3MF
- `run.sh` — end to end: photos dir → printable file

Needs **many overlapping real photos of one rigid object**. Will not work on drawings or
on a handful of unrelated images.

### 2. Concept art / a single image → generative (GPU)
`gpu/` — does **not** measure; a neural net *imagines* a plausible complete 3D form from one
image (including the parts it never saw). The right tool for a figurine from character art.

- `install_trellis.sh` — install Microsoft [TRELLIS](https://github.com/microsoft/TRELLIS)
  (MIT licensed) + CUDA deps on a GPU box
- `run_trellis.py` — image → textured GLB → STL/3MF

Needs an **NVIDIA GPU (~24 GB)**. We rent one by the hour on vast.ai and delete it after.

## Cost control

- **Hetzner (CPU pipeline):** powering a server off does *not* stop billing — only deletion does.
  `deploy/park.sh` snapshots then deletes; `deploy/wake.sh` recreates from the snapshot.
- **vast.ai (GPU pipeline):** stopping still charges storage. The $0-when-idle path is to bake the
  installed box into a Docker image, push it to a registry, delete the instance, and recreate from
  the image next time.

## Layout

```
pipeline/   CPU photogrammetry (COLMAP + OpenMVS + mesh repair)
gpu/        GPU generative (TRELLIS) install + runner
deploy/     Hetzner provisioning + snapshot park/wake cost scripts
```

## Status

The generative (GPU) pipeline works end to end: image(s) → TRELLIS → textured mesh → watertight,
printable STL/3MF. See `STATE.md` for live status and `TROUBLESHOOTING.md` for the install/ops gotchas
(there are many — GitHub HTTP/2, dependency pins, build isolation, xformers, vast SSH quirks).

## Secrets

API keys live in `.env` (gitignored), e.g. `VAST_API_KEY=...`. Never committed.
