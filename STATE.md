# STATE.md — Live status

**Last updated:** 2026-06-03 by Claude. Keep this current; it is the working memory a fresh instance
inherits. Observed facts only — no guesses.

## Direction (locked)

Reusable tool: images + printer profile → printable file. Printer (spool count N, build volume,
filament colors, color-vs-paint) is a parameter. Current input type: concept art → TRELLIS.

## Done

- Research complete; generative-not-photogrammetry decided (DECISIONS #2).
- Repo created and public: https://github.com/johnjhusband/PhotoTo3D (push over HTTPS — SSH key is RO).
- vast.ai account funded ($25), API key saved in `.env` and `~/repos/CTO/.env`. `vastai` CLI in `.venv`.
- GPU rented: instance **39215079**, RTX 3090, **running**, SSH `ssh9.vast.ai:15078`, key `~/.ssh/cto-deploy`.
- CPU photogrammetry server deleted (path dormant; scripts kept).
- Context system written (CLAUDE/SOUL/AGENTS/DESIGN/DECISIONS/STATE/README).
- Reference image chosen: `candidates/gXAmE1Bn2dubu5B-OCEe4.png` (umbrella illustration); runner
  updated for multi-image.

## In flight / BROKEN

- **TRELLIS install on the GPU box FAILED at the git clone** — `gpu/install_trellis.sh` died with
  `fatal: early EOF` / `invalid index-pack output` while doing `git clone --recurse-submodules`.
  The large submodule pack choked. **Needs a more robust clone** (e.g. clone shallow without
  submodules, then `git submodule update --init --depth 1`, with retries).

## Next

1. Fix the clone in `install_trellis.sh` and re-run the install on instance 39215079.
2. Run TRELLIS: multi-image over the usable `candidates/` set, plus single-image on the umbrella ref;
   compare previews.
3. Send John the preview(s); on approval, repair → STL/3MF.
4. Build the **palette-to-N** color stage (input: spool count). Needs John's printer profile when he
   provides it.
5. Once a good run exists: `docker commit` the box → push image to GHCR (reuse without idle cost) →
   destroy the instance.

## Open questions for John

- Printer profile details (spool count N, build volume, loaded filament colors, color-vs-paint) —
  needed to finish stages 4–6. Treat as a per-job input; do not assume a specific printer.

## Cost note

Instance 39215079 is **running and billing** (~$0.20/hr). Destroy it when not actively needed
(`vastai destroy instance 39215079`); reuse via the committed Docker image.
