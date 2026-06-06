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

## v2 (research-driven, "college-grade") — see RESEARCH_RENDERING_MATH.md

The math says our "5th-grade" quality has specific root causes: per-vertex color (band-limited by mesh
res → use UV texture), alpha-wrap blobbing (morphological closing → repair-only), TRELLIS-1's 64³ ceiling
(→ TRELLIS.2 512³ + O-Voxel), single-view hallucination (→ multi-view first), linear-texture gamma, and
baked lighting (→ delit albedo + matte BRDF). Full-body is done by completing the body in **2D first**
(FLUX-Kontext identity uncrop + SMPL-X/DWpose A-pose scaffold + IP-Adapter, on-model gate), then
reconstructing — never letting the 3D model invent legs. Full prioritized idea list + the math in
**RESEARCH_RENDERING_MATH.md**.

## Status

See **STATE.md** for live status. (Architecture: stages 1–4 + slicing automatable by the agent;
physical print + artistic finishing are John's.)

## Design pattern: split a figure into MULTIPLE PRINTS (for color + assembly)

**Standard thinking for this kind of art (John, 2026-06-06).** A 4-filament printer prints only 4
colors per object. When a figure wants more colors than that — or you just want color modularity —
split it into separate prints and assemble them. The HAT was the first one (straw, separate from the
4-color body). The question every time: **what is EASY to separate AND easy to assemble?**

**Pick parts to separate by this rule:**
- **GOOD — separate these first.** Parts that are LARGE, RIGID, sit on a NATURAL SEAM, and join with a
  SIMPLE registration feature (a cube/cylinder peg into a matching socket, or a tab into a slot). They
  print flat/easily and snap together one way only.
  - **Hat** — sits on the head, peg-in-socket. (done)
  - **Staff / weapon** — a rigid rod that drops into a hole in the hand. The EASIEST of all: it barely
    touches the body (just the grip), prints as a simple rod, and can even be multi-colored on its own.
  - **Cloak / cape** — ONLY if it is a distinct shell over a complete body. **In a fused 3D
    reconstruction (the normal case here) the cloak is NOT separable** — it IS the outer surface, so
    removing it SHATTERS the body into ~1000 disconnected fragments (tested + confirmed 2026-06-06: the
    "body" became a hollow front panel + floating bits, not a printable solid). Don't try to split a
    fused layer. The hat/staff separate cleanly only because they are TOPOLOGICALLY DISTINCT (a cap on
    top, a rod in the hand); the cloak is structural.
- **BAD — never separate these.** SMALL, THIN, FRAGILE parts, parts with a hidden/complex interface, or
  any layer FUSED into the body shell. They are hard to print and far harder to align and glue.
  - **Tongue, fingers, thin straps, eye-band, the cloak.** Keep them attached.

**How to actually solve a color overflow (the tongue problem, tested 2026-06-06):**
Body wants 5 colors: dark cloak, grey dress, skin, blue scarf, red tongue — but a 4-filament print does
4. Splitting the cloak FAILS (it's fused; shatters the body). The tongue is too small to split. So the
real fix is **drop the least important color in the quantizer, not split geometry.** Re-quantize the
body to the 4 that matter — `LWEIGHT 1.6` (lightness-weighted) gives {black cloak, grey dress, skin,
blue scarf}; the tiny red tongue merges into the dark. The tongue is still THERE geometrically, just not
its own color. Net: a clean, non-dark 4-color body. (Keeping the red tongue instead costs the grey dress
its slot → the body reads dark. It's a genuine pick, not a bug.) The hat stays a separate straw print.

**Always:**
1. Add a registration feature so parts fit ONE way and assemble by hand (peg/socket like the hat).
2. Standard order to consider separating: **hat → weapon → cloak → large accessories.** Stop before
   anything small/fragile.
3. Each print gets its own up-to-N colors; total colors = sum across prints.
4. Tooling: `split_hat_puzzle.py` is the template (detect part by color/region → split → cap → peg/socket).
