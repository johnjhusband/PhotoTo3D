#!/usr/bin/env python3
"""gen_ai_reference.py — AI-fork Stage 1: text -> clean 2D character reference.

The "maths" fork built the 2D reference by IP-Adapter consolidation + baked texture transfer,
which came out splotchy. This fork instead writes ONE clean text prompt (synthesized by a vision
model from the source art) and lets a text-to-image model render a crisp, flat-colored, full-body
reference — far cleaner input for image->3D and for 4-color reduction.

Model: OpenAI gpt-image-1 (key already on hand; ~$0.01-0.04/image). The prompt bakes in everything
(no negative-prompt field): full-body A-pose, plain white bg, flat cel-shade, limited palette.

Usage: gen_ai_reference.py <out.png> [--prompt "..."] [--size 1024x1536] [--quality medium]
Env: OPENAI_API_KEY (falls back to /home/john/repos/CTO/.env).
"""
import os, sys, json, base64, argparse, urllib.request

# Character design synthesized from ALL 6 source images in candidates/ (commonalities kept,
# conflicting props — umbrella, snake tongue — dropped for a clean printable figure).
DEFAULT_PROMPT = (
    "Full-body character reference of a single anime girl, standing upright facing the viewer in a "
    "calm symmetric A-pose, arms relaxed at her sides, both feet flat on the ground, the entire figure "
    "visible from the top of her hat down to her feet, centered in frame. Clean flat cel-shaded anime "
    "illustration with simple flat color areas and soft even lighting, on a plain solid white "
    "background, no cast shadows, no extra props. "
    "She wears: a wide conical woven straw hat (kasa / sedge hat) with a large round dark-grey brim on "
    "her head; a thin dark horizontal band across her eyes with large glowing violet eyes visible "
    "beneath it; long dark-brown hair falling past her shoulders; a thick cobalt-blue chunky knit scarf "
    "around her neck; a grey ribbed knit high-neck sweater dress; a dark charcoal-grey cloak draped over "
    "her shoulders; purple-grey cloth bandages wrapped around her forearms and lower legs; simple "
    "sandals. Hands empty and open, no umbrella, no weapons. Crisp clean linework, a limited flat color "
    "palette of dark charcoal, cobalt blue, grey, and tan."
)


def load_key():
    k = os.environ.get("OPENAI_API_KEY", "").strip()
    if k:
        return k
    for f in ("/home/john/repos/CTO/.env", os.path.expanduser("~/repos/CTO/.env")):
        if os.path.isfile(f):
            for line in open(f):
                if line.startswith("OPENAI_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("no OPENAI_API_KEY (env or CTO/.env)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--size", default="1024x1536")          # portrait, good for a standing figure
    ap.add_argument("--quality", default="medium", choices=["low", "medium", "high"])
    ap.add_argument("--model", default="gpt-image-1")
    a = ap.parse_args()

    body = json.dumps({
        "model": a.model, "prompt": a.prompt, "size": a.size,
        "quality": a.quality, "n": 1, "background": "opaque",
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/images/generations", data=body,
        headers={"Authorization": f"Bearer {load_key()}", "Content-Type": "application/json"})
    print(f"[ai-ref] gpt-image-1 {a.size} q={a.quality} -> {a.out}")
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.load(r)
    b64 = d["data"][0]["b64_json"]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, "wb").write(base64.b64decode(b64))
    u = d.get("usage", {})
    print(f"[ai-ref] wrote {a.out}  (usage: {u})")


if __name__ == "__main__":
    main()
