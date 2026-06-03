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

## In flight

- **TRELLIS install running** on instance 39215079, past the clone, in the pip/CUDA-build phase.
- **Clone failure resolved.** Root cause was `curl 92 HTTP/2 stream CANCEL / early EOF` — fixed by
  `git config --global http.version HTTP/1.1` (now in `install_trellis.sh`) plus shallow clone +
  retries + separate submodule init.
- **SSH gotchas (important for any future instance):**
  - The vast **proxy** endpoint `ssh9.vast.ai:15078` is flaky for sustained sessions. Use the
    **direct** endpoint instead: `ssh -i ~/.ssh/cto-deploy -p 29698 root@120.238.149.205` (stable).
  - **Never `pkill -f install_trellis`** plainly — the pattern matches the SSH command's own shell and
    kills the session (silent no-output). Use the bracket trick: `pkill -9 -f '[i]nstall_trellis'`.

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
