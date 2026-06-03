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

**3. Geometry for printing — mesh repair (Blender headless + pymeshfix)** — watertight/manifold,
drop floating islands, fix normals, decimate. Scale to build volume; add a base so it stands;
hollow if wanted; check min wall thickness; split into parts if it exceeds build volume. *(Fully
automated. Artistic geometry tweaks — e.g. lengthen the cloak — are a script→render→look loop, or
manual Blender for fussy work.)*

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

## Open forks (these change the design — John decides, not me)

1. **One-off vs. reusable tool.** Is the goal a single figurine of this one character, or a tool
   where you drop in images + a printer profile and get a printable file repeatedly? This decides how
   much we parameterize/harden vs. just produce the file once. *(Default assumption until told
   otherwise: one-off figurine — no extra hardening.)*
2. **Target printer + color intent.** Which printer, how many spools, and do we attempt color or go
   monochrome-and-paint? This decides stages 4–6 entirely.

## Status

- Stage 2 (TRELLIS) installing on a rented RTX 3090. Stages 3–4 scripted (`pipeline/repair_mesh.py`,
  palette stage TBD). Stages 0, 5, 6 depend on the printer answer in fork #2.
