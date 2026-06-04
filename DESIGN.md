# PhotoTo3D — End-to-End Design

Designed **backward from the printed object**: the deliverable is a physical print on a specific
printer, so the printer's constraints are inputs at the top, not surprises at the end. An LLM
(Claude) orchestrates; a disposable rented GPU runs the heavy model.

## The one constraint that shapes everything: the printer

Captured **first**, as job parameters, because they bound every later stage:

- **Build volume** — max object size; sets scaling and whether we must split into parts.
- **Material count** — single-extruder (1 effective color) vs multi-material (N spools).
- **Actual filament colors loaded** — the real palette we must map to.
- **Color intent** — full attempt at color, OR print monochrome and hand-paint.
- **Material** (PLA/PETG/resin) — sets min wall thickness / feature size.

Nothing downstream is decided without these.

## The pipeline (each stage's automation boundary is explicit)

**0. Target spec** — record the printer constraints above. *(input from John, once per printer)*

**1. Input curation** — gather images; classify whether they're consistent views of one subject
(use multi-image) or a mixed set (pick the best single). Cull blur/tiny/watermarked. Optional
**text-guided reference editing**: LLM + an inpainting model fixes the reference per instruction
(e.g. "remove the umbrella, give a clean full-body front view"). *(I drive this; John approves the
chosen/edited reference.)*

**2. 3D generation — TRELLIS** — reference image(s) → textured mesh (GLB). `gpu/run_trellis.py`
(STEPS=30, TEX=2048 for quality). *(Automated on the GPU box.)*

**2.5. Color re-texture — Hunyuan3D-Paint (optional, `HY_PAINT=1`)** — TRELLIS's baked texture is
dark/muddy (lighting baked in). Hunyuan-Paint re-textures the SAME geometry (`use_remesh=False`) with
delit, light/shadow-free PBR albedo → bright, accurate color. `gpu/run_hunyuan_paint.py`. Keeps TRELLIS
shape (research refuted Hunyuan's geometry being better; only its texture wins). *(Automated; ~21GB VRAM.)*

**3. Geometry for printing — `repair_mesh.py` (CGAL alpha-wrap)** — generative meshes are 1000+
disconnected shells, NOT a watertight solid. We wrap them with **CGAL 3D Alpha Wrapping** (`gpu/alpha_wrap.cpp`):
guaranteed watertight + manifold, and PRESERVES thin features (cape/scarf) that the old voxel shrink-wrap
collapsed. Then keep the largest blob, decimate to a printable budget, transfer the original color onto
the solid. Still to add: scale to build volume, base, hollow, min-wall-thickness, split if over volume.
*(Automated. `REL_ALPHA` env tunes feature fineness.)*

**4. Color output / palette-to-N** — deliverable is a **COLOR 3MF** (`gpu/export_color3mf.py`, lib3mf;
trimesh can't write color; STL dropped — it's colorless). For an N-spool multi-material printer,
`pipeline/palette_quantize.py` reduces the texture to N filament colors (k-means, snapped to the loaded
colors) and emits per-color STLs. The full color 3MF goes to a slicer that maps regions to filaments.

**5. Slicing — slicer → G-code** — load the 3MF/STL into a slicer (OrcaSlicer/PrusaSlicer/Bambu/Cura)
with the printer's profile; set infill, supports, layer height; multi-material color mapping becomes
filament swaps in the G-code. *(Automatable via slicer CLI once a profile exists, or handed to John
to slice on his setup.)*

**6. Print & finish** — print the G-code. If monochrome, hand-paint using TRELLIS's color render as
the reference. *(John's hardware/hands.)*

## Human decision points (everything else is automated)

1. Approve the chosen/edited **reference image** (end of stage 1).
2. Approve the **N-color palette** preview (end of stage 4).
3. Final **pre-slice** approval of the printable mesh.
4. The physical **print + paint** (stage 6).

## What I own end-to-end vs. what's John's

- **I own:** stages 1–4 and slicing-to-G-code — image prep, generation, mesh repair, color
  quantization, profile-based slicing. Run on the GPU box / Blender headless / slicer CLI.
- **John's:** the physical print, and artistic hand-finishing where a human in the Blender viewport
  beats my script→render→look loop.

## Resolved direction (John, 2026-06-03)

1. **Reusable tool**, not a one-off. The system must take images **+ a printer profile** as inputs
   and produce a printable file repeatedly. So everything is parameterized; nothing is hardcoded to
   one character or one machine.
2. **The printer is a parameter, not a fixed target.** Spool count N, build volume, loaded filament
   colors, and color-vs-paint intent are inputs supplied per job/printer profile (the "4 spools"
   case is just one value of N). Stage 4's palette-to-N is driven by that N. We do not assume a
   specific printer.

## Status

See **STATE.md** for live status. (Architecture: stages 1–4 + slicing automatable by the agent;
physical print + artistic finishing are John's.)
