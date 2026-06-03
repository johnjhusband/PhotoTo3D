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

**2. 3D generation — TRELLIS** — reference image(s) → textured mesh (GLB). Render a turntable
preview. *(Fully automated on the GPU box.)*

**3. Geometry for printing — mesh repair (`repair_mesh.py`)** — generative meshes come out as 1000+
disconnected shells (hair/body/clothing), NOT a watertight solid, so this stage is mandatory. It
**voxel-remeshes all shells into one solid** (shrink-wrap), smooths the voxel stair-stepping (Taubin),
decimates to a printable triangle budget, then runs pymeshfix LAST as the watertight guarantee. (Order
matters: decimating after pymeshfix re-opens the surface.) Still to add: scale to build volume, add a
base, hollow, min-wall-thickness check, split if over build volume. *(Automated. Artistic geometry
tweaks — e.g. lengthen the cloak — are a script→render→look loop, or manual Blender. Note: headless
geometry rendering needs a display stack that isn't installed; use TRELLIS's turntable preview.)*

**4. Color resolution — palette-to-N** — TRELLIS outputs a continuous texture (hundreds of shades);
a multi-color FDM printer can't do that, so we **must** reduce it. Quantize surface colors to
**exactly N = spool count**, snapped to the real loaded filament colors. When the design wants more
distinct regions than spools, the LLM arbitrates the merges (or John specifies: "keep hair+cloak
distinct, merge gloves into sleeves"), then renders the N-color preview for approval. Bake the N
regions into the 3MF as per-region materials. If monochrome printer: drop color, output a clean STL
as a paint base. *(I drive; John approves the palette preview.)*

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
