# DECISIONS.md — Settled decisions and why

Append-only log. Do not re-litigate these unless John reopens them. Newest at bottom.

| # | Decision | Why |
|---|----------|-----|
| 1 | Open-source only; no paid 3D-generation SaaS. Raw hourly GPU + LLM API tokens are OK. | John's constraint. Renting raw compute is infrastructure, not a banned "service". |
| 2 | For **concept art**, use generative (TRELLIS), NOT photogrammetry. | Photogrammetry triangulates the same physical point across consistent real photos. Drawings have nothing to triangulate. Generative *imagines* the form — the right tool for art. |
| 3 | **TRELLIS** is the generative engine. | MIT license (commercial-safe), high mesh quality, supports multi-image, runs on a 24 GB GPU. Competitors (Hunyuan3D-2, Stable Fast 3D) have restrictive licenses. |
| 4 | Rent GPU on **vast.ai** by the hour; delete after each job. | Cheapest (~$0.18/hr RTX 3090), prepaid, raw SSH box so we install/run TRELLIS ourselves. Hetzner Cloud has no GPU instances. |
| 5 | Deleted the CPU photogrammetry server. | Photogrammetry isn't needed for the current art inputs; the install (COLMAP/OpenMVS) is reproducible from the repo if revived. Stop billing. |
| 6 | Use TRELLIS **multi-image** mode for John's image set, AND compare against best single-image. | John has multiple images; multi-image is the right primitive. But mixed art styles can hurt, so compare. |
| 7 | Handle the printer's spool limit via a **palette-to-N quantization** stage. | TRELLIS outputs a continuous texture; multi-color FDM needs ≤ N flat colors. N = spool count is an input; agent arbitrates merges; bake into 3MF. |
| 8 | This is a **reusable tool**, not a one-off; the **printer is a parameter**. | John, 2026-06-03. Parameterize by printer profile (spool count, build volume, colors); don't hardcode one character or machine. |
| 9 | Persist all context as **markdown in the repo** (CLAUDE/SOUL/AGENTS/DESIGN/DECISIONS/STATE/TROUBLESHOOTING/README). | The chat is volatile; the repo is the durable brain. A fresh LLM reads the repo and is caught up. |
| 10 | Attention backend = **xformers**, not flash-attn. | flash-attn won't build (build-isolation + slow/OOM). xformers has prebuilt wheels and TRELLIS supports it. (Cost: had to patch a BlockDiagonalMask path — see TROUBLESHOOTING.) |
| 11 | Install TRELLIS's CUDA extensions **directly with `--no-build-isolation`**, bypassing `setup.sh`. | setup.sh omits the flag (their setup.py imports torch) and its kaolin branch silently skips torch 2.4.1. |
| 12 | Mesh repair = **voxel-remesh all shells into one solid**, NOT "keep largest component". | TRELLIS output is 1000+ disconnected shells; largest-component dropped ~99% of the figure. Voxel shrink-wrap yields a single watertight printable solid. |
| 13 | For John's image set, **single best image > multi-image**. | Multi-image over the mixed-style set produced a *lower-detail* model (21k vs 72k faces). Multi-image only helps with consistent views of one subject. Default to the cleanest single image unless inputs are consistent. |
| 14 | **Step A (consolidation) is required for 2+ images**; single image stays as-is (John, 2026-06-03). | Fuse the N inconsistent refs into ONE clean canonical image (SDXL + IP-Adapter, prompt written by the LLM), then run the existing single-image TRELLIS path. `gpu/run_pipeline.sh` branches on image count. |
| 15 | **Output must carry color** (John: "we need color"). | The watertight printable was geometry-only (voxel remesh drops texture). repair_mesh now transfers the GLB texture color onto the solid and exports `*_color.glb`/`*_color.ply` (vertex colors); STL/3MF stay geometry for single-color printing. Full per-filament color is the later palette-to-N stage. |
| 16 | **F3D is the mesh viewer/renderer** (apt, local). | Free, opens STL/GLB/3MF/OBJ/PLY, renders headless. Replaces the pyglet renderer that wasn't installable. |
