# TROUBLESHOOTING.md — Hard-won lessons

Every item here cost real time to discover during the first build (2026-06-03). All fixes are already
in the scripts; this is the "why" so a future instance doesn't re-learn them. If something breaks,
check here first.

## TRELLIS install (all fixed in `gpu/install_trellis.sh`)

- **`git clone` dies with `curl 92 HTTP/2 stream CANCEL` / `early EOF`.** The host's HTTP/2 to GitHub
  breaks on large packs. Fix: `git config --global http.version HTTP/1.1`, shallow clone, retries,
  init submodules separately.
- **`ResolutionImpossible` on basic deps (open3d 0.18 vs 0.19 / werkzeug).** pip backtracks. Fix:
  pre-pin `open3d==0.19.0 werkzeug>=3.0.0` before `setup.sh --basic`.
- **flash-attn fails to build (`No module named torch`, slow/OOM).** Don't build it. Use xformers:
  `ATTN_BACKEND=xformers` + prebuilt `xformers==0.0.28.post1` (cu121 wheel).
- **CUDA extensions fail: `No module named torch` then `Cannot compile … extension`.** Their setup.py
  imports torch, which pip's PEP517 build isolation hides. Fix: install them DIRECTLY (not via
  setup.sh) with `--no-build-isolation` and `CUDA_HOME=/usr/local/cuda` exported. setup.sh also only
  knows kaolin up to torch 2.4.0 (silently skips 2.4.1) — use the torch-2.4.0_cu121 kaolin wheels.
- **`destination path '/tmp/extensions/...' already exists`.** Leftover from a failed run. Fix:
  `rm -rf /tmp/extensions` at the start (script does this).
- **`Could not import module 'CLIPTextModel'`.** basic deps pull transformers 5.x; TRELLIS needs the
  4.x CLIP API. Fix: pin `transformers==4.46.3`.
- **Runtime `module 'xformers.ops.fmha' has no attribute 'BlockDiagonalMask'`.** xformers 0.0.28 moved
  it to `xformers.ops.fmha.attn_bias`. Fix: sed-patch TRELLIS's 3 sparse-attention files.
- **`No module named 'lxml'` on 3MF export / `No module named 'fast_simplification'` on decimate.**
  Add both to the mesh-deps pip line.
- **`No module named 'trellis'` when running run_trellis.py.** Python adds the *script's* dir to
  sys.path, not cwd. Fix: `PYTHONPATH=/workspace/TRELLIS` (run script also adds `TRELLIS_HOME`).

## vast.ai operations

- **Proxy SSH `ssh9.vast.ai:<port>` is flaky** for sustained sessions (timeouts, broken pipe). Use the
  **direct** endpoint: `ssh -i ~/.ssh/cto-deploy -p <directport> root@<public_ip>`
  (get it via `vastai ssh-url <id>`; this run it was `120.238.149.205:29698`).
- **`pkill -f install_trellis` silently kills your own SSH session** — the pattern matches the remote
  shell's command line. Use the bracket trick: `pkill -9 -f '[i]nstall_trellis'`, and don't mention
  the name elsewhere in the same command.
- **Detached launch over SSH:** `cd … && setsid bash x.sh </dev/null >log 2>&1 & disown; echo X`.
  Plain `nohup … &` can hang the SSH channel and the launch gets lost.
- **Billing:** "stop" still bills storage every second; only **delete** stops all charges. Reuse via
  `docker commit` → push to a registry → recreate from the image (zero idle cost).

## Don't download big models on the laptop with the Python/Xet path

John's laptop has only **7.6 GB RAM**. `snapshot_download` of SDXL buffered ~3.2 GB in memory and
pushed the machine into swap — visibly sluggish. The high-performance (Xet) transfer is memory-hungry.
If a large model MUST be fetched on the laptop, stream each file to disk with `curl`/`wget` (near-zero
RAM) instead, then rsync to the box. Better: avoid needing SDXL at all — a full-body reference image
runs through the working TRELLIS path directly (no SDXL, no download fight).

## A vast host that simply can't download a model

- Instance 39215079 downloaded TRELLIS weights fine but **could not download SDXL** (~7GB) at all —
  main HF CDN failed 20× over ~100 min, hf-mirror.com failed 8× more, with hf_transfer + shell
  `timeout` + retries all in place. Conclusion: some host↔CDN paths are just broken for large files
  and no client-side fix helps. Fallbacks: (1) download the model on a machine with good network and
  rsync the HF cache to the box; (2) destroy and rent a different instance. Don't burn hours retrying.
- Note: Step-A consolidation only matters when no single input image is good enough. If one reference
  clearly wins (it did for John's set), single-image TRELLIS already gives the best result — the SDXL
  consolidation is optional, so a download blocker on it is not a hard stop for the project.

## Long-running jobs (downloads, watchers)

- **Hugging Face model downloads stall** — SDXL hangs mid-fetch (leaves `*.incomplete`), both on the
  vast box AND on the laptop (unauthenticated rate limits don't help). The ONLY reliable fix is a
  **shell `timeout` wrapper + retry loop** around `snapshot_download` (resumes from partial): a stall
  gets killed and retried. `HF_HUB_ENABLE_HF_TRANSFER` is **deprecated/ignored** in huggingface_hub
  1.x — it's replaced by Xet (`HF_XET_HIGH_PERFORMANCE=1`). So don't rely on hf_transfer; rely on the
  timeout+retry. An HF_TOKEN would raise rate limits but we don't have one.
- **A process-presence watcher (`pgrep`) CANNOT detect a hang** — a frozen process is still "alive",
  so the watcher waits forever. Watch the **log mtime** instead: declare a stall if the log hasn't
  changed in N minutes (~7), in addition to success/error markers and process-gone. A bash launcher
  wrapper can also stay alive after its python child dies, further fooling pgrep.

## Color formats

- **STL has no color, ever** — geometry only, shows as one color in every viewer. Expected. Color
  lives in GLB/PLY/3MF. For multi-color PRINTING the standard is **3MF** (slicer assigns filaments →
  G-code). STL is a strict subset of 3MF and redundant for color work — prefer 3MF, drop STL.
- **trimesh's `.export(".3mf")` does NOT embed vertex colors** — the 3MF comes out geometry-only.
  So `repair_mesh.py`'s current 3MF has no color (color is only in the `*_color.glb`). To get a real
  color 3MF, use a proper writer (lib3mf, or build the 3MF color extension XML) — not trimesh's export.

## Mesh → printable

- **TRELLIS meshes are NOT watertight** — they're 1000+ disconnected shells (hair/body/clothing).
  "Keep largest component" is WRONG (drops ~99% of the figure). Fix: voxel-remesh ALL shells into one
  solid (`repair_mesh.py`), then smooth + decimate + pymeshfix.
- **Decimation re-opens the surface** → not watertight. Fix: decimate FIRST, run pymeshfix LAST.
- **`pymeshfix.clean_from_arrays` rejects trimesh arrays.** Cast: `np.asarray(v, float64)`,
  `np.asarray(f, int32)`.
- **Headless mesh rendering** (trimesh `save_image`) needs pyglet — not installed. Use **F3D** instead
  (installed locally via apt): it views AND renders STL/GLB/3MF/PLY/OBJ.
- **`repair_mesh.py` crashes at decimation with `ModuleNotFoundError: fast_simplification`** — current
  trimesh imports `fast_simplification` lazily inside `simplify_quadric_decimation`. On a fresh box it's
  not installed, so repair builds the watertight solid then dies at the decimate step — and because
  `apose_3d.sh` greps the repair output, the traceback was INVISIBLE and the pipeline printed
  `APOSE3D_DONE` with NO `printable_color.glb` (stage 5 then silently produced nothing). Fix: install
  `fast_simplification` (now in `bootstrap_fresh.sh`). Hardening: `apose_3d.sh` now `tee`s a full
  `out_ap/_repair.log` and GUARDS each deliverable (`REPAIR_FAILED`/`PALETTE_FAILED` + exit 1) so a
  stage that produces no file fails loudly instead of faking success.
- **LESSON: never let a pipeline grep-filter its own stage output down to a happy-path marker** — a crash
  after the marker becomes a silent success. Keep a full per-stage log and assert the output file exists.
- **Hunyuan PAINT `run_hunyuan_paint.py` exits with a `Segmentation fault` — this is BENIGN.** The painted
  `*_pbr.glb` is fully written FIRST (you'll see `[hy-paint] DONE -> ...pbr.glb` then an `OBJ import ...`
  line), and the segfault happens in a trailing Blender/Draco cleanup step after the file is on disk. The
  repair step loads the pbr glb fine. So: guard on the OUTPUT FILE existing, NOT on the paint process exit
  code (it's nonzero). Do NOT match `Segmentation` as a pipeline-failure signal in a monitor — it fires on
  this benign crash while later stages are still running. (Draco warning `libextern_draco.so not found` is
  also harmless — it just means no Draco compression.)

## Viewing / rendering with F3D (installed on the laptop)

- View interactively: `f3d <file>` (drag to rotate). Handles STL, GLB, 3MF, OBJ, PLY.
- Headless render to PNG: `f3d model.glb --output x.png --resolution 800,800 --camera-azimuth-angle <deg> --camera-elevation-angle <deg>`.
- **Background flag is `--bg-color R,G,B`** (space-separated), NOT `--background-color=` (that errors and
  the render silently produces nothing). Default bg is dark `0.2,0.2,0.2`.
- **Dark-colored models render near-black.** Use `--light-intensity 4-6` and a light-ish `--bg-color
  0.62,0.66,0.72` for contrast. Don't fix it with ImageMagick `-auto-level` — on dark-on-dark it blows
  the image out to white.
- **STL is geometry only (renders grey) — color lives in the GLB.** For a colored printable, repair_mesh
  transfers the GLB's texture color onto the watertight solid and writes `*_color.glb` / `*_color.ply`.
- Front of the umbrella-character model is azimuth ~0; azimuth 180 is the dark hair back.
