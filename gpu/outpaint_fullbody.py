#!/usr/bin/env python3
"""outpaint_fullbody.py — CHEAPEST full-body path: SDXL-inpaint outpaint a waist-up character down to a
standing full body. The original upper-body pixels are KEPT EXACTLY (identity preserved for free); only
the legs/lower outfit below the waist are generated, conditioned on the character via IP-Adapter.

Pipeline math (research): masked latent inpainting blends known (kept) + generated (legs) each step;
IP-Adapter's decoupled cross-attention injects the character's appearance into the invented region so
the legs stay on-model. Output is a clean full-body character on a plain background, ready for TRELLIS.

Usage: outpaint_fullbody.py <clean_subject_image> <out.png> [--prompt ...] [--scale 0.7] [--seed 0]
Env:   SDXL_INPAINT (default diffusers/stable-diffusion-xl-1.0-inpainting-0.1), IPA_PATH (h94/IP-Adapter)
Run on CUDA. Input should already be the character on a plain (gray) background (our preprocessed ref).
"""
import sys, os, argparse
import numpy as np
import torch
from PIL import Image
from diffusers import StableDiffusionXLInpaintPipeline

GRAY = (128, 128, 128)
CANVAS_W, CANVAS_H = 832, 1216          # SDXL portrait ratio, good for a standing figure
TOP_FRAC = 0.50                          # waist-up subject occupies the top half; legs fill the rest
OVERLAP = 0.06                           # mask starts slightly INTO the kept region so legs connect

PROMPT = ("full body of the same single anime character, standing, A-pose, legs and feet visible, "
          "head to toe, same outfit and color scheme continued downward, plain flat gray background, "
          "centered, clean lineart, consistent art style, full figure")
NEG = ("cropped, cut off, out of frame, multiple characters, extra limbs, duplicate, umbrella, props, "
       "text, watermark, signature, blurry, lowres, deformed, floating, sitting")


def subject_bbox(rgb, bg=GRAY, tol=10):
    a = np.asarray(rgb).astype(int)
    mask = (np.abs(a - np.array(bg)).sum(2) > tol)
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return (0, 0, rgb.width, rgb.height)
    return (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--prompt", default=PROMPT); ap.add_argument("--neg", default=NEG)
    ap.add_argument("--scale", type=float, default=0.7)
    ap.add_argument("--steps", type=int, default=40); ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    src = Image.open(a.inp).convert("RGB")
    l, t, r, b = subject_bbox(src)
    subj = src.crop((l, t, r, b))                      # tight waist-up character
    sw, sh = subj.size

    # place the waist-up subject in the TOP_FRAC band of the portrait canvas, centered horizontally
    target_h = int(CANVAS_H * TOP_FRAC)
    scale = min(target_h / sh, (CANVAS_W * 0.9) / sw)
    nw, nh = int(sw * scale), int(sh * scale)
    subj_r = subj.resize((nw, nh), Image.LANCZOS)

    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), GRAY)
    ox, oy = (CANVAS_W - nw) // 2, 0
    canvas.paste(subj_r, (ox, oy))

    # mask: white = generate (legs). Start a touch above the subject's bottom so legs attach at the waist.
    mask = Image.new("L", (CANVAS_W, CANVAS_H), 0)
    m = np.asarray(mask).copy()
    waist_y = int(oy + nh * (1 - OVERLAP))
    m[waist_y:, :] = 255
    mask = Image.fromarray(m, "L")

    sdxl_inp = os.environ.get("SDXL_INPAINT", "diffusers/stable-diffusion-xl-1.0-inpainting-0.1")
    ipa = os.environ.get("IPA_PATH", "h94/IP-Adapter")
    print(f"[outpaint] subject {subj.size} -> canvas {CANVAS_W}x{CANVAS_H}, waist_y={waist_y}, model={sdxl_inp}")

    pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
        sdxl_inp, torch_dtype=torch.float16, variant="fp16").to("cuda")
    pipe.load_ip_adapter(ipa, subfolder="sdxl_models", weight_name="ip-adapter_sdxl.bin")
    pipe.set_ip_adapter_scale(a.scale)                 # identity of the invented legs from the character

    g = torch.Generator(device="cuda").manual_seed(a.seed)
    out = pipe(prompt=a.prompt, negative_prompt=a.neg, image=canvas, mask_image=mask,
               ip_adapter_image=subj, num_inference_steps=a.steps, strength=0.99,
               guidance_scale=7.5, generator=g, width=CANVAS_W, height=CANVAS_H).images[0]

    # force the KEPT region back to the exact original pixels (inpaint can bleed slightly outside mask)
    out_np = np.asarray(out).copy()
    keep = np.asarray(canvas)
    keepmask = (np.asarray(mask) == 0)
    out_np[keepmask] = keep[keepmask]
    Image.fromarray(out_np).save(a.out)
    print(f"[outpaint] wrote {a.out}")


if __name__ == "__main__":
    main()
