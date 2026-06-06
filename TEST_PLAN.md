# TEST_PLAN.md — what "done" means for a figurine deliverable

**Why this exists (John, 2026-06-06):** the hat-on-the-spear-tip bug shipped because I only checked
"is it mathematically correct," not "does it function and does it look right." A deliverable is NOT done
until it passes ALL THREE dimensions below. Every check here traces to a real defect we've already fixed —
run the whole list on every figurine before saying it's done. **Don't declare done on a green A section
alone; B (function) and C (aesthetics) are where the embarrassing bugs hide.**

How to run: section **A** is automated — `python pipeline/verify_deliverable.py <body.3mf> <hat.3mf>`
(run it on the EXACT shipped files, not an intermediate). Sections **B** and **C** require rendering and
LOOKING — render front / 3-4 / side / head-crop / **assembled (body+hat)** with F3D and eyeball each item.
A check you can't honestly tick is a FAIL.

---

## A. STRUCTURAL / MATHEMATICAL  (automated — trimesh on the shipped file)
Each printable part (body 3MF, hat 3MF) must pass:

| # | Check | Pass criteria | Defect it traces to |
|---|-------|---------------|---------------------|
| A1 | Watertight | `mesh.is_watertight == True` | non-watertight meshes, decimation re-opening surface |
| A2 | Single solid | `len(split(only_watertight=False)) == 1` | 2-face floating sliver; "kept largest of N blobs" |
| A3 | Welded, not exploded | `verts ≈ unique positions` (NOT 3×faces) | exploded "polygon soup" → Bambu floating-regions/empty-layers |
| A4 | Scale correct | longest extent == target mm (±1) | normalized units shipped instead of mm |
| A5 | Region count | body = exactly 4 face-colors; hat = 1 | blue scarf swallowed; >N or <N regions |
| A6 | No degenerate faces | zero zero-area / duplicate faces | repair artifacts |
| A7 | Loads in Bambu | load+re-export exits 0 | invalid 3MF / unreadable color |

## B. FUNCTIONAL  (does it actually assemble + print)
| # | Check | How | Defect it traces to |
|---|-------|-----|---------------------|
| B1 | **Hat seats on the HEAD** | concat body+hat at join coords, render — hat rests on the head crown, level, centered; NOT on the spear, NOT floating, NOT sunk into the face | **hat-on-spear-tip (peg placed at body global-max instead of head axis)** |
| B2 | Peg↔socket mate | peg edge + 2·clearance ≤ socket edge; same (x,z) axis; socket depth ≥ peg proud length | press-fit too tight/loose; misaligned axis |
| B3 | No floating mass in Bambu | slice (or A2) shows no disconnected/unsupported regions, no "empty layer", no "too thin/faulty mesh" | floating sliver; thin cape |
| B4 | Each color = ONE contiguous region | per-color faces form few connected patches, not scattered speckle | speckled 4-color; staff repainted skin by island-removal |
| B5 | Min feature printable | thinnest wall/feature ≥ ~0.8 mm at target scale; flag thin cape edge / tongue / spear shaft | thin cape truncated; tongue "too fine"; spear shaft dropped by image→3D |
| B6 | Grounded / printable pose | parts sit on the plate; staff planted, not floating mid-air | unsupported geometry |
| B7 | Right color COUNT per part | body=4 filaments (fits a 4-AMS), hat=1 (the 5th) — total 5 | tried to put 5 colors on one 4-filament print |

## C. AESTHETIC  (looks like the character, by eye, against `candidates/`)
| # | Check | Defect it traces to |
|---|-------|---------------------|
| C1 | All signature features present: **conical straw hat, eye-band, violet eyes, long hair, blue scarf, grey ribbed dress, dark cloak, arm+leg bandages, sandals, forked snake tongue, spear/polearm** | hat missing; tongue missing; weapon missing |
| C2 | Full body head-to-toe, calm A-pose, sane proportions (head/arm/leg lengths) | bust-only; "5th-grade" proportions; dramatic pose ruining face/hands |
| C3 | Hat ON the head — right size, centered, sitting like a hat | hat-on-spear; hat as a bust; hat dropped |
| C4 | Hands intact — not fused to the cape, not melted, not misshapen | hands fused to cape (alpha-wrap bridging); misshapen right hand |
| C5 | Cape/cloak continuous — no hole under the hands, not cut off at the shoulders | cape truncated by voxel repair; cape "missing then reconnects" under hands |
| C6 | Colors clean + distinct — not dark/muddy/low-contrast, not splotchy/speckled; scarf reads blue, tongue red, robe dark, skin warm | dark muddy color; splotchy math-path color; speckle |
| C7 | Weapon reads as a weapon — gripped in the hand, planted, taller-than-her, right thickness | spear shaft dropped; staff repainted skin; staff floating |
| C8 | Face legible — eyes/eye-band/mouth read at 150 mm | soft face at full-body scale; bg-removal clipping the pale face |
| C9 | Snake tongue visible (2D + 3D), printable thickness | tongue too fine; tongue missing |
| C10 | No stray geometry / artifacts / speckle / floating bits visible | boolean slivers; render speckle |
| C11 | **The render you SHOW John is the CLEAN 4-color print version** — never the lifelike preview (it carries Hunyuan texture speckle and looks unacceptable). LOOK at the exact image before sending. | shipped a speckly lifelike render as a deliverable |

---

## Render set to capture for B + C (F3D)
front (az 0), 3-4 (az 35), side (az 90), back (az 180), **head crop** (elev 18, zoom), and
**assembled body+hat** (the B1 fit test). Heavy meshes: render on the box or decimate first (local F3D
locks up on >800k-face GLBs).

## The standing rule
If a check fails, **say so plainly and fix it before delivering** — do not ship a green-A / red-B set.
"Mathematically correct" is necessary, not sufficient; function and aesthetics are the other two thirds.
