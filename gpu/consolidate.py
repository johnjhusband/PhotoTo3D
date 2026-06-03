#!/usr/bin/env python3
"""consolidate.py — Step A: fuse several inconsistent reference images into ONE clean canonical image.

Why: TRELLIS multi-image needs consistent views of one subject. Mixed-style references (different
artists, poses, headwear) produce garbage. This step distills the common character design from all
the references into a single clean, front-facing, plain-background image that the existing
single-image TRELLIS path can turn into a good 3D model.

How: Stable Diffusion XL + IP-Adapter. IP-Adapter conditions generation on the reference IMAGES
(their visual features), and the text prompt (ideally written by the orchestrating LLM after looking
at the references) pins identity and asks for a clean canonical view.

Usage:
  python consolidate.py <out_image> <ref1> <ref2> [ref3 ...] \
      [--prompt "..."] [--neg "..."] [--scale 0.7] [--steps 30] [--seed 0]

Run on a CUDA GPU. Downloads SDXL (~7GB) + IP-Adapter weights on first run.
"""
import sys, os, argparse
import torch
from PIL import Image
from diffusers import StableDiffusionXLPipeline, DDIMScheduler

DEFAULT_PROMPT = ("full-body character concept art of a single character, centered, standing, "
                  "front view, T-pose-ish neutral pose, plain white background, consistent clean "
                  "style, full figure head to feet, high detail")
DEFAULT_NEG = ("multiple characters, two people, umbrella, props, held objects, text, watermark, "
               "signature, cropped, out of frame, blurry, lowres, extra limbs, duplicate")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_image")
    ap.add_argument("refs", nargs="+")
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--neg", default=DEFAULT_NEG)
    ap.add_argument("--scale", type=float, default=0.7, help="IP-Adapter strength (ref influence)")
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    refs = [Image.open(p).convert("RGB") for p in a.refs]
    print(f"[consolidate] {len(refs)} reference images -> 1 canonical")
    print(f"[consolidate] prompt: {a.prompt}")

    # SDXL_PATH / IPA_PATH let us load from a local copy (avoids HF downloads on the box).
    sdxl = os.environ.get("SDXL_PATH", "stabilityai/stable-diffusion-xl-base-1.0")
    ipa = os.environ.get("IPA_PATH", "h94/IP-Adapter")
    pipe = StableDiffusionXLPipeline.from_pretrained(
        sdxl, torch_dtype=torch.float16, variant="fp16",
    ).to("cuda")
    pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config)
    pipe.load_ip_adapter(ipa, subfolder="sdxl_models", weight_name="ip-adapter_sdxl.bin")
    pipe.set_ip_adapter_scale(a.scale)

    g = torch.Generator(device="cuda").manual_seed(a.seed)
    # Pass all refs together: IP-Adapter combines their image embeddings -> features of each fused.
    image = pipe(
        prompt=a.prompt, negative_prompt=a.neg,
        # one IP-Adapter conditioned on ALL refs -> wrap as a single adapter's image set
        ip_adapter_image=[refs],
        num_inference_steps=a.steps, guidance_scale=6.0, generator=g,
        height=1024, width=1024,
    ).images[0]

    os.makedirs(os.path.dirname(os.path.abspath(a.out_image)), exist_ok=True)
    image.save(a.out_image)
    print(f"[consolidate] wrote {a.out_image}")


if __name__ == "__main__":
    main()
