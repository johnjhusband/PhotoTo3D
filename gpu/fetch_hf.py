#!/usr/bin/env python3
"""fetch_hf.py — download a HuggingFace repo (or a subset) FAST via aria2c, bypassing vast.ai's
per-connection HF throttle (~57 B/s single-stream → hangs for hours). The HF *API* (file list,
small JSON) is not throttled; only the CDN file pulls are — so we list files via the API, then
aria2c every file with 16 parallel connections each.

Usage: fetch_hf.py <repo_id> <dest_dir> [allow_glob ...]
  e.g. fetch_hf.py stabilityai/stable-diffusion-xl-base-1.0 /workspace/_sdxl/sdxl-base
       fetch_hf.py h94/IP-Adapter /workspace/_sdxl/ip-adapter sdxl_models/*
       fetch_hf.py tencent/Hunyuan3D-2.1 /workspace/_hunyuan/weights hunyuan3d-paintpbr-v2-1/*
"""
import os, sys, subprocess, fnmatch
from huggingface_hub import HfApi

def main():
    if len(sys.argv) < 3:
        sys.exit("usage: fetch_hf.py <repo_id> <dest_dir> [allow_glob ...]")
    repo, dest = sys.argv[1], sys.argv[2]
    globs = sys.argv[3:]
    files = HfApi().list_repo_files(repo)
    if globs:
        files = [f for f in files if any(fnmatch.fnmatch(f, g) or f.startswith(g.rstrip("*")) for g in globs)]
    files = [f for f in files if not f.endswith(".gitattributes")]
    print(f"[fetch_hf] {repo}: {len(files)} files -> {dest}")
    lines = []
    for f in files:
        url = f"https://huggingface.co/{repo}/resolve/main/{f}"
        outdir = os.path.join(dest, os.path.dirname(f))
        os.makedirs(outdir, exist_ok=True)
        lines.append(f"{url}\n  dir={outdir}\n  out={os.path.basename(f)}\n")
    inp = "/tmp/aria_%s.in" % repo.replace("/", "_")
    open(inp, "w").write("".join(lines))
    # -j4: 4 files at a time, each with 16 connections; --auto-file-renaming=false to keep names
    subprocess.run(["aria2c", "-x16", "-s16", "-k1M", "-j4", "--max-tries=4", "--retry-wait=2",
                    "--file-allocation=none", "--auto-file-renaming=false", "--allow-overwrite=true",
                    "-i", inp], check=True)
    print(f"[fetch_hf] done -> {dest}")

if __name__ == "__main__":
    main()
