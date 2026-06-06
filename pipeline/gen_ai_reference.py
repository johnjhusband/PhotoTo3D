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
import os, sys, json, base64, argparse, urllib.request, mimetypes

# Character design synthesized from ALL 6 source images in candidates/. Keeps the common features AND
# the forked SNAKE TONGUE (John wants it shown); only the held umbrella is dropped.
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
    "sandals. A long thin FORKED SNAKE-LIKE TONGUE sticking out of her mouth. Hands empty and open, no "
    "umbrella, no weapons. Crisp clean linework, a limited flat color palette of dark charcoal, cobalt "
    "blue, grey, and tan."
)

# Source-consistent style: when conditioning on the candidate images (--ref), match THEIR look —
# moody, atmospheric, painterly, semi-realistic anime with dramatic cool lighting and a violet/blue
# palette — while still rendering the WHOLE figure for 3D reconstruction.
STYLE_PROMPT = (
    "A single anime girl, full body head to toe, standing facing the viewer, the WHOLE figure visible "
    "from the top of her hat to her feet, centered. Render her in the SAME art style as the reference "
    "images: moody, atmospheric, painterly semi-realistic anime, dramatic cool lighting, deep violet "
    "and blue tones, detailed soft shading. "
    "She wears a wide conical woven straw hat (kasa) on her head; a dark horizontal band across her "
    "eyes with glowing violet eyes; long dark-brown hair; a cobalt-blue knit scarf; a grey ribbed knit "
    "dress; a dark cloak; purple-grey bandages wrapped around her forearms and lower legs; sandals. She "
    "is sticking out a long thin FORKED SNAKE-LIKE TONGUE. No umbrella in frame, hands empty. Keep her "
    "full body in view, standing in a relaxed neutral pose."
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


def _multipart(fields, files):
    """Build a multipart/form-data body (stdlib only). fields: dict; files: list of (name, path)."""
    boundary = "----phototo3dBoundary7MA4YWxkTrZu0gW"
    nl = b"\r\n"
    buf = b""
    for k, v in fields.items():
        buf += b"--" + boundary.encode() + nl
        buf += f'Content-Disposition: form-data; name="{k}"'.encode() + nl + nl
        buf += str(v).encode() + nl
    for name, path in files:
        fn = os.path.basename(path)
        ctype = mimetypes.guess_type(path)[0] or "image/png"
        buf += b"--" + boundary.encode() + nl
        buf += f'Content-Disposition: form-data; name="{name}"; filename="{fn}"'.encode() + nl
        buf += f"Content-Type: {ctype}".encode() + nl + nl
        buf += open(path, "rb").read() + nl
    buf += b"--" + boundary.encode() + b"--" + nl
    return buf, boundary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--prompt", default=None)
    ap.add_argument("--size", default="1024x1536")          # portrait, good for a standing figure
    ap.add_argument("--quality", default="medium", choices=["low", "medium", "high"])
    ap.add_argument("--model", default="gpt-image-1")
    ap.add_argument("--ref", action="append", default=[],
                    help="source image(s) to condition on for STYLE consistency (uses the edits "
                         "endpoint). Repeatable. When given, defaults the prompt to STYLE_PROMPT.")
    a = ap.parse_args()
    key = load_key()
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)

    if a.ref:
        # IMAGE-CONDITIONED: feed the source art so the output matches its style (snake tongue, moody).
        prompt = a.prompt or STYLE_PROMPT
        fields = {"model": a.model, "prompt": prompt, "size": a.size, "quality": a.quality, "n": 1}
        files = [("image[]", p) for p in a.ref]
        data, boundary = _multipart(fields, files)
        req = urllib.request.Request(
            "https://api.openai.com/v1/images/edits", data=data,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": f"multipart/form-data; boundary={boundary}"})
        print(f"[ai-ref] gpt-image-1 EDITS on {len(a.ref)} refs {a.size} q={a.quality} -> {a.out}")
    else:
        prompt = a.prompt or DEFAULT_PROMPT
        body = json.dumps({"model": a.model, "prompt": prompt, "size": a.size,
                           "quality": a.quality, "n": 1, "background": "opaque"}).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/images/generations", data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        print(f"[ai-ref] gpt-image-1 {a.size} q={a.quality} -> {a.out}")

    with urllib.request.urlopen(req, timeout=420) as r:
        d = json.load(r)
    open(a.out, "wb").write(base64.b64decode(d["data"][0]["b64_json"]))
    print(f"[ai-ref] wrote {a.out}  (usage: {d.get('usage', {})})")


if __name__ == "__main__":
    main()
