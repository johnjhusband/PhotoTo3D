# RESEARCH: The Math & Science of Rendering → Why we're "5th grade" and how to reach "college grade"

Synthesis of 5 deep research streams (2026, cited). This is the knowledge base that drives the v2 pipeline.
Every claim traces to the cited papers in the source briefs; the numbers below are the load-bearing math.

## Root causes of our current quality (ranked by impact), with the math

1. **Per-vertex color is band-limited by mesh resolution.** Per-vertex color interpolates barycentrically
   across each triangle → you literally cannot represent a color feature smaller than a triangle (an eye
   highlight, a sharp costume edge). We have been exporting PER-VERTEX color. A 4K UV **texture** carries
   ~100–300× more color samples than a 50k-tri mesh has vertices. **This is the #1 structural cap on our
   color/detail.** Fix: real UV unwrap (xatlas) + texture, not per-vertex.

2. **CGAL alpha-wrapping is a morphological closing** (dilate by `offset`, carve by `alpha`-ball). By
   construction it ROUNDS every convex feature to radius ≈ offset and FILLS every concavity narrower than
   ~2·alpha. We use it as the main surface former → that *is* the "blobby" look. Fix: demote alpha-wrap to
   **watertight repair only**, with `alpha ≈ D/200–D/300` (finer than the smallest feature) and
   `offset ≈ alpha/30`, run on an already-detailed mesh — never as the detail-bearer.

3. **TRELLIS-1 quantizes structure to a 64³ sparse-voxel grid** (~2.8mm cells on a 180mm figure). That is
   the hard ceiling on geometric detail; the 64→256 mesh upsample only interpolates, it invents nothing.
   Fix: **TRELLIS.2-4B** runs the structure grid at 512³/1024³ (8–16× resolution) with **O-Voxel dual
   contouring** (per-voxel free vertex placed by a Quadratic Error Function → snaps onto sharp edges/corners
   that marching-cubes-on-occupancy bevels off). Caveat: TRELLIS.2 needs torch≥2.6 → its OWN env (see plan).

4. **Single-view conditioning → hallucinated back/sides → lumps.** TRELLIS sees one silhouette; everything
   unseen is guessed. Fix: generate a **consistent multi-view set first**, then reconstruct (multi-view
   models the JOINT distribution → coherent unseen geometry).

5. **Dark color = linear/sRGB double-decode.** TRELLIS writes linear values into a texture read as sRGB →
   a mid linear 0.5 decodes to ~0.19 (black crush). Our gamma 0.5 ≈ approximate inverse; the PRINCIPLED fix
   is tag the basecolor **linear/raw** or apply the exact piecewise sRGB OETF ONCE (with the 12.92 toe),
   never a freehand gamma. (Albedo is data, not a picture.)

6. **Muddy color = baked lighting in the texture.** Shaded color `Lo = ∫ fr·Li·(n·ωi) dωi` bakes the
   lighting `Li` into the texture; a print needs the **albedo coefficient `c`**, not `Lo`. Delighting
   (Hunyuan-Paint's cross-lighting consistency loss `‖A(I_light1)−A(I_light2)‖`) recovers `c`. We did this;
   the math confirms it's correct, and says to also force matte (metallic=0, roughness→1) so specular ≈ 0.

## New ideas → the v2 pipeline (prioritized, all RTX-3090-feasible)

### Geometry (5th→college)
- **G1. UV texture, not per-vertex color** (xatlas unwrap, stretch-equalized to minimize L2 stretch
  σ; texel density ∝ 1/(σ₁σ₂); hide seams in low-visibility zones). *Biggest single quality jump.*
- **G2. Demote alpha-wrap to repair-only, fine alpha; stop using it as the surface.**
- **G3. TRELLIS.2-4B @ 512³ + O-Voxel** for sharp geometry (separate torch-2.6 env).
- **G4. Multi-view first** (MV-Adapter / Era3D row-wise attention fits 24GB) → feed multi-image path → kills
  hallucinated lumps.
- **G5. Normal-map → displacement re-injection:** estimate a normal map, integrate it (Poisson:
  `Δz = div(g)`, edge-preserving/TV variant to keep creases) → height field → displace a densely
  subdivided base. Converts crisp normals TRELLIS can encode into REAL printable geometry.
- **G6. Better mesh ops:** bilateral **normal** denoise (range weight on normal diff halts at edges) →
  crease-aware subdivision (semi-sharp σ decay) → **feature-constrained, curvature-weighted QEM**
  decimation (add perpendicular constraint planes at sharp edges) → alpha-wrap repair last.

### Color (vivid, accurate, clean 4 regions)
- **C1. Fix gamma at the root** (tag linear / exact OETF once), not freehand.
- **C2. Delit albedo + force matte** (metallic 0, roughness 1) so no baked specular.
- **C3. von Kries white-balance** the albedo (diagonal LMS scale by white_target/white_src) → true hues.
- **C4. Quantize in CIELAB with ΔE2000-weighted k-means, K=4** (perceptual, not RGB).
- **C5. Spatial coherence by GRAPH-CUT/MRF** (not just our neighbor-majority): smoothness term on labels →
  clean contiguous regions; NO dithering (unprintable speckle). (We have color-pre-smoothing; graph-cut is
  the principled upgrade.)
- **C6. Rendering-cycle QA gate:** re-render predicted albedo under flat light, compare → numeric "is the
  albedo clean?" metric to drive the self-judge loop.

### Texture fidelity
- **T1. Cosine^p multi-view bake** (`w = max(0,n·v)^p·vis`), **frequency-split**: blend low band smoothly,
  take per-texel MAX-weight for the high band (averaging high freq = blur).
- **T2. Poisson seam blending in UV space** (`Δf = div(v)`, boundary clamped) → invisible seams.
- **T3. Texture-space super-res (PBR-SR style):** optimize the single shared texture so its multi-view
  renders match a 2D SR prior + identity term `λ‖T−T_LR‖` → 4K without per-view hallucination/seams.
- **T4. Print-Nyquist discipline:** moderate unsharp-mask, then band-limit to the printer's region pitch;
  for 4-color, keep region BOUNDARIES clean/anti-aliased, don't chase sub-region detail the print can't show.

### Full body (REQUIRED next) — never let 3D invent legs; complete in 2D first
- **F1. Scaffold:** fit SMPL-X (or VRoid anime prior) to the waist-up → A-pose → derive depth+normal+DWpose
  skeleton (feet keypoints!) + Plücker raymaps, ALL from one scaffold (mutually consistent).
- **F2. Identity-preserving uncrop:** **FLUX.1-Kontext-dev** (token-concat identity, ~0.9 face sim) +
  depth/DWpose ControlNet (zero-conv = style-safe) + RePaint jump-steps at the waist seam.
- **F3. Identity-locked multi-view:** MV-Adapter/Era3D in canonical orthographic A-pose + IP-Adapter-FaceID
  (shared-query/separate-KV keeps the SAME face across all views).
- **F4. On-model GATE before meshing:** face-cosine>0.92, upper-region SSIM≈1, outfit color-EMD, DWpose
  joint error; resample only failing views. Only a green view-set reaches 3D.
- **F5. Reconstruct** (TRELLIS/TRELLIS.2/Hunyuan) with SMPL-X soft geo-prior in the LEGS only (invented
  region) so legs stay anatomical.

## Unifying principles (the "why")
- Every "stay on-model" guarantee = shared-query / separate-KV attention injection (IP-Adapter,
  reference-only ControlNet, MV-Adapter image-cross-attn, Kontext token-concat) + zero-init residual
  conditioning (ControlNet zero-conv) → add control without overwriting the frozen art-style prior.
- Every "consistent 3D" guarantee = make attention obey epipolar geometry (Plücker rays → epipolar/row-wise
  attention in a canonical camera).
- Every "clean albedo" guarantee = a rendering-cycle / cross-lighting consistency loss that divides out `Li`.
- Detail must be CAPTURED high-res, PARKED in a displacement/texture channel, and RE-INJECTED onto a clean
  printable base — never left to a smoothing/morphological op as the final detail-bearer.

## Source briefs
Five cited research briefs (TRELLIS/SLAT math, inverse-rendering/PBR, mesh reconstruction, full-body/
multi-view, texture/UV/SR) are archived in the conversation; key papers: TRELLIS 2412.01506, TRELLIS.2
2512.14692, FlexiCubes, Hunyuan3D-2.1 2506.15442, IntrinsicAnything 2404.11593, RGB↔X 2405.00666,
FLUX.1-Kontext 2506.15742, MV-Adapter 2412.03632, Era3D 2405.11616, SMPL-X, ControlNet 2302.05543,
PBR-SR 2506.02846, Poisson editing, ESRGAN, xatlas, CGAL Alpha Wrapping (Portaneri SIGGRAPH'22).
