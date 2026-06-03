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

## Mesh → printable

- **TRELLIS meshes are NOT watertight** — they're 1000+ disconnected shells (hair/body/clothing).
  "Keep largest component" is WRONG (drops ~99% of the figure). Fix: voxel-remesh ALL shells into one
  solid (`repair_mesh.py`), then smooth + decimate + pymeshfix.
- **Decimation re-opens the surface** → not watertight. Fix: decimate FIRST, run pymeshfix LAST.
- **`pymeshfix.clean_from_arrays` rejects trimesh arrays.** Cast: `np.asarray(v, float64)`,
  `np.asarray(f, int32)`.
- **Headless mesh rendering** (trimesh `save_image`) needs pyglet/a display — not installed. To preview
  geometry, use TRELLIS's own turntable `preview.mp4`, or install a render stack if truly needed.
