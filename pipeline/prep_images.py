#!/usr/bin/env python3
"""prep_images.py — clean a folder of photos before photogrammetry.

Two jobs that materially improve reconstruction quality:
  1. Cull blurry frames — a single soft photo poisons feature matching.
     Sharpness = variance of the Laplacian; drop the bottom fraction.
  2. (optional) Background removal — rembg masks out the background so SfM
     locks onto the object, not the room behind it. Writes RGBA pngs.

Usage:
  prep_images.py <in_dir> <out_dir> [--mask] [--blur-drop 0.15]
Run with: /opt/meshenv/bin/python prep_images.py ...
"""
import os, sys, glob, argparse
import cv2
import numpy as np


def sharpness(path):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return -1.0
    return float(cv2.Laplacian(img, cv2.CV_64F).var())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("in_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--mask", action="store_true", help="remove background with rembg")
    ap.add_argument("--blur-drop", type=float, default=0.15,
                    help="fraction of blurriest images to discard (0 = keep all)")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)

    files = sorted(sum([glob.glob(os.path.join(a.in_dir, e))
                        for e in ("*.jpg", "*.JPG", "*.jpeg", "*.png", "*.PNG")], []))
    if not files:
        sys.exit(f"no images found in {a.in_dir}")
    print(f"[prep] {len(files)} input images")

    scored = sorted(((sharpness(f), f) for f in files), key=lambda x: x[0])
    n_drop = int(len(scored) * a.blur_drop)
    keep = [f for _, f in scored[n_drop:]]
    if n_drop:
        print(f"[prep] dropping {n_drop} blurriest images (keeping {len(keep)})")

    masker = None
    if a.mask:
        from rembg import remove, new_session
        masker = new_session("u2net")

    for i, f in enumerate(sorted(keep)):
        out = os.path.join(a.out_dir, f"img_{i:04d}.png")
        if masker is not None:
            from rembg import remove
            with open(f, "rb") as fh:
                data = remove(fh.read(), session=masker)
            with open(out, "wb") as fh:
                fh.write(data)
        else:
            img = cv2.imread(f)
            cv2.imwrite(out, img)
    print(f"[prep] wrote {len(keep)} prepared images to {a.out_dir}"
          + (" (background removed)" if a.mask else ""))


if __name__ == "__main__":
    main()
