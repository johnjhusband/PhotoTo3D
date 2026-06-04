#!/usr/bin/env python3
"""preprocess_reference.py — make a clean reference TRELLIS won't mangle into a blank-mask face.

Root cause of the blank/mask face (research 2026): the default rembg model (u2net, photo-trained)
clips a PALE anime face against a WHITE background, and a waist-up frame makes the face too small to
survive TRELLIS's structure binning. Fixes applied here:
  1. Background removal with the ANIME model (isnet-anime), not the photo model.
  2. Composite onto a NON-WHITE backing (mid-gray) so pale skin doesn't bleed into white.
  3. Auto-crop to the subject; optionally emit a tight FACE/BUST crop where the face fills the frame.

Outputs (PNG, RGB on gray — feed to TRELLIS with preprocess_image=False so it does NOT re-remove bg):
  <out>/ref_full.png   — whole subject, bg removed, on gray, squared
  <out>/ref_bust.png   — head+shoulders crop (face large) for a faithful bust
Usage: preprocess_reference.py <input_image> <out_dir> [--bg gray|white|none] [--bust-frac 0.55]
"""
import os, sys
import numpy as np
from PIL import Image
from rembg import remove, new_session

GRAY = (128, 128, 128)


def _args(argv):
    if len(argv) < 3:
        sys.exit("usage: preprocess_reference.py <input_image> <out_dir> [--bg gray|white|none] [--bust-frac 0.55]")
    inp, out = argv[1], argv[2]
    bg, bust_frac = "gray", 0.55
    i = 3
    while i < len(argv):
        if argv[i] == "--bg":
            bg = argv[i + 1]; i += 2
        elif argv[i] == "--bust-frac":
            bust_frac = float(argv[i + 1]); i += 2
        else:
            i += 1
    return inp, out, bg, bust_frac


def composite(rgba, bg):
    """RGBA -> RGB on the chosen backing."""
    if bg == "none":
        return rgba
    base = Image.new("RGBA", rgba.size, (255, 255, 255, 255) if bg == "white" else (*GRAY, 255))
    base.alpha_composite(rgba)
    return base.convert("RGB")


def subject_bbox(rgba, pad=0.06):
    """Tight bbox of the non-transparent subject, padded; returns (l, t, r, b)."""
    a = np.asarray(rgba)[:, :, 3]
    ys, xs = np.where(a > 16)
    if len(xs) == 0:
        return (0, 0, rgba.width, rgba.height)
    l, r, t, b = xs.min(), xs.max(), ys.min(), ys.max()
    pw, ph = int((r - l) * pad), int((b - t) * pad)
    return (max(0, l - pw), max(0, t - ph),
            min(rgba.width, r + pw), min(rgba.height, b + ph))


def square(img, bg):
    """Pad to a centered square on the backing color so TRELLIS gets a non-distorted frame."""
    w, h = img.size
    s = max(w, h)
    fill = (255, 255, 255) if bg == "white" else GRAY
    canvas = Image.new("RGB", (s, s), fill)
    canvas.paste(img.convert("RGB"), ((s - w) // 2, (s - h) // 2))
    return canvas


def main():
    inp, out, bg, bust_frac = _args(sys.argv)
    os.makedirs(out, exist_ok=True)
    src = Image.open(inp).convert("RGBA")
    print(f"[prep] {inp} {src.size} -> bg-removal (isnet-anime), backing={bg}")

    session = new_session("isnet-anime")
    cut = remove(src, session=session)  # RGBA with anime-tuned alpha

    # full subject, cropped + squared
    l, t, r, b = subject_bbox(cut)
    full = cut.crop((l, t, r, b))
    full_rgb = square(composite(full, bg), bg)
    full_rgb.save(os.path.join(out, "ref_full.png"))
    print(f"[prep] ref_full.png {full_rgb.size}")

    # bust crop: top bust_frac of the subject height (head + shoulders) -> face fills the frame
    bh = int((b - t) * bust_frac)
    bust = cut.crop((l, t, r, t + bh))
    bl, bt, br, bb = subject_bbox(bust)
    bust = bust.crop((bl, bt, br, bb))
    bust_rgb = square(composite(bust, bg), bg)
    bust_rgb.save(os.path.join(out, "ref_bust.png"))
    print(f"[prep] ref_bust.png {bust_rgb.size}")


if __name__ == "__main__":
    main()
