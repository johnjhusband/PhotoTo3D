# REPRODUCE.md — end-to-end runbook to recreate the figurine result

This is the exact, working pipeline that produced `FINAL/print_files/figurine_apose_4color_150mm.3mf`
(a clean full-body, A-pose, 4-color printable anime figurine from a single concept-art image). Someone
with this repo cloned can follow these steps and reproduce it. All scripts referenced are in `gpu/` and
`pipeline/` and are committed.

## What it does (stages)
`single image → clean A-pose 2D reference (SDXL+IP-Adapter) → 3D shape (Hunyuan3D-2.1) → delit color
(Hunyuan-Paint) → watertight repair (CGAL alpha-wrap) → gentle color-correct → 4 flat print regions
(Lab k-means, overcluster+merge, color pre-smooth) → scaled STL/3MF print files.`

## Hardware
- One rented GPU: **vast.ai RTX 3090, 24 GB**, image `pytorch/pytorch:2.4.1-cuda12.1-cudnn9-devel`, ~120 GB disk.
- A laptop/desktop to drive it over SSH and do the light final mesh export (CPU).
- `.env` holds `VAST_API_KEY` (gitignored). Rent: `vastai create instance <offer> --image pytorch/pytorch:2.4.1-cuda12.1-cudnn9-devel --disk 120 --ssh --direct`.

## Fastest path: one-command fresh-box bootstrap
On a fresh vast.ai box, after copying `gpu/` + `pipeline/` + the source images to `/workspace`:
```
bash gpu/bootstrap_fresh.sh   # no TRELLIS; aria2c all weights; build envs; multi-image A-pose (hat) -> 3D
```
This does everything below automatically. The manual steps are kept for reference / debugging.

## On the GPU box — install (once)
Copy `gpu/` and `pipeline/` to `/workspace`, then:
```
bash gpu/install_trellis.sh          # base CUDA stack, trimesh, rembg (isnet-anime), xformers, etc.
bash gpu/install_alpha_wrap.sh       # CGAL alpha-wrap binary (watertight repair)
bash gpu/install_hunyuan.sh          # Hunyuan3D-2.1 paint env (hyvenv); fixes bpy/basicsr/custom_rasterizer
bash gpu/install_consolidate.sh      # diffusers + IP-Adapter for SDXL
bash gpu/fetch_hunyuan_shape_weights.sh   # Hunyuan SHAPE weights via aria2c (see INFRA GOTCHAS)
```
Weights: SDXL + IP-Adapter (~11 GB) and Hunyuan paint/dino (~17 GB) are downloaded by the install
scripts; the SHAPE DiT+VAE (~8 GB) by `fetch_hunyuan_shape_weights.sh`.

## Generate (the result)
```
# 0) put the source concept art at /workspace/ref.png
# 1) clean calm A-POSE full-body 2D reference (the form-fix; a dramatic/action pose ruins face+hands)
SDXL_PATH=/workspace/_sdxl/sdxl-base IPA_PATH=/workspace/_sdxl/ip-adapter HF_HUB_OFFLINE=1 \
HEIGHT=1216 WIDTH=832 \
  python gpu/consolidate.py out_ap/canonical.png /workspace/ref.png \
    --prompt "full body wide shot of a single anime girl head to toe, standing A-pose, arms relaxed at sides, facing forward, <character description>, plain background, full figure" \
    --neg "umbrella, props, hand on face, dramatic pose, cropped, extra limbs" --scale 0.4 --steps 30 --seed 5
#    (run DIRECT, do NOT pipe through `tail` — it swallows output/errors)
# 2) 3D: A-pose ref -> Hunyuan shape -> paint -> repair -> color -> 4-color
HY_SHAPE_MODEL=/workspace/_hunyuan/hy3d21 bash gpu/apose_3d.sh
#    outputs: out_ap/model.glb (geometry), model_pbr.glb (color), printable_color.glb, print_4color_4color.*
```

## On the laptop — pull + make print files
```
scp box:/workspace/out_ap/printable_color.glb out_ap/print_4color_4color.glb ./
# lifelike full-color (smooth the per-vertex noise) for viewing:
python pipeline/color_correct.py print_4color... ; (Laplacian color smooth) -> figurine_apose_lifelike.glb
# print files (scaled to a chosen height, e.g. 150 mm): single STL + color 3MF + per-material STLs
#   load the 4-color GLB, scale to TARGET_MM/extents.max(), export .stl, per-color .stl, and
#   gpu/export_color3mf.py for the colored .3mf.  (See FINAL/print_files for the produced set.)
```

## Key parameters that matter (tuned)
- A-pose gen: `--scale 0.4` (IP-Adapter; low = prompt controls pose for full-body), portrait `832x1216`.
- Repair: `REL_ALPHA=240–320` (finer alpha = preserves face/hands; alpha-wrap rounds features if too coarse).
- Color: `color_correct --wb 0 --sat 1.0 --gamma 0.7` (gentle; strong sat amplifies texture bleed).
- 4-color: `LWEIGHT=1.0 MERGE_EXTRA=3 COLORSMOOTH=25` (overcluster+merge unifies near-identical darks;
  color pre-smoothing kills speckle).

## INFRA GOTCHAS (these cost hours — read them)
1. **vast.ai HF download is throttled per-connection to ~57 B/s – 1.3 KB/s** (single-stream hangs for
   HOURS) — and it affects EVERY HF model (SDXL, IP-Adapter, Hunyuan paint/dino/shape), not just one.
   PyPI and GitHub are NOT throttled (pip/git work fine). The bypass is **aria2c -x16 -s16** (~12–138 MB/s):
   `gpu/fetch_hf.py <repo> <dest> [globs]` lists files via the (un-throttled) HF API then aria2c's them.
   `bootstrap_fresh.sh` uses it for all weights. TRELLIS is NOT needed (pipeline uses Hunyuan shape).
2. **stop/restart is fragile**: a host "address already in use" port conflict can permanently brick a
   stopped instance. Keep the box running, or expect to rent fresh.
3. **Do NOT pipe generation scripts through `tail`** — Python block-buffers to a pipe and you see nothing
   (and lose errors on crash). Run direct or redirect to a file, with `PYTHONUNBUFFERED=1`.
4. SDXL re-downloads unless pointed at the local copy: `SDXL_PATH=/workspace/_sdxl/sdxl-base` + `HF_HUB_OFFLINE=1`.
5. Output is in **normalized units (~2 units tall)** → scale to physical mm before printing.

## Known quality limits (honest)
- Face is soft at full-body scale (a face shape, not razor-sharp eyes) — needs a face-focused/high-res pass.
- Slight color drift in the texture; 4-color is grey/blue-dominant (matches the subject).

See `RESEARCH_RENDERING_MATH.md` for the math behind every choice, `EXPERIMENTS.md` for the full log,
`STATE.md` for live status.
