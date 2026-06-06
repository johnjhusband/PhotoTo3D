#!/usr/bin/env python3
"""verify_deliverable.py — automated SECTION A of TEST_PLAN.md (structural correctness).

Run on the EXACT shipped 3MFs before declaring a figurine done. Catches the structural defects that
have actually shipped (non-watertight, floating slivers, exploded soup, wrong scale, wrong color count).
Sections B (function: hat seats on head, peg/socket) and C (aesthetics) still need rendering + eyeballing
per TEST_PLAN.md — this only covers what a machine can check.

Usage: verify_deliverable.py <part.3mf> [<part.3mf> ...] [--mm 150]
Exit code 0 only if EVERY part passes every check.
"""
import sys, os, zipfile, re, argparse
import numpy as np
import trimesh


def color_count_3mf(path):
    """Count distinct colors declared in the 3MF color extension (trimesh can't read per-face color)."""
    try:
        with zipfile.ZipFile(path) as z:
            name = next((n for n in z.namelist() if n.endswith(".model")), None)
            if not name:
                return None
            xml = z.read(name).decode("utf-8", "ignore")
        # <m:color color="#RRGGBBAA"/> entries inside colorgroups
        cols = set(re.findall(r'color="(#[0-9A-Fa-f]{6,8})"', xml))
        return len(cols) if cols else None
    except Exception:
        return None


def check_part(path, expect_colors, mm, is_full):
    print(f"\n=== {os.path.basename(path)} ===")
    ok = True
    def rec(name, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}{'  — ' + detail if detail else ''}")

    if not os.path.isfile(path):
        print("  [FAIL] file exists"); return False
    try:
        m = trimesh.load(path)
        if hasattr(m, "to_geometry"):
            m = m.to_geometry()
    except Exception as e:
        rec("A7 loads", False, str(e)); return False
    rec("A7 loads in trimesh", True)

    nv, nf = len(m.vertices), len(m.faces)
    rec("A1 watertight", bool(m.is_watertight))
    comps = m.split(only_watertight=False)
    rec("A2 single solid (no floating bits)", len(comps) == 1, f"{len(comps)} components")
    rec("A3 welded (not exploded soup)", nv < 1.5 * nf, f"{nv}v / {nf}f (exploded would be 3v:1f)")
    longest = float(np.max(m.extents))
    if is_full:
        # the full-height part (body) must equal the target height
        rec("A4 scale == target mm", abs(longest - mm) <= 2.0, f"longest extent {longest:.1f} mm")
    else:
        # a sub-part (hat) is correctly SMALLER than the whole, but must still be in mm (not the ~2-unit
        # normalized output) and at the shared scale (<= the target). Catches "shipped normalized units".
        rec("A4 scale (sub-part, in mm)", 5.0 <= longest <= mm * 1.05,
            f"longest extent {longest:.1f} mm (sub-part; should be 5..{mm:.0f})")
    deg = int((m.area_faces <= 1e-9).sum())
    rec("A6 no degenerate faces", deg == 0, f"{deg} zero-area faces")
    nc = color_count_3mf(path)
    if expect_colors is not None:
        rec("A5 color/region count", nc == expect_colors, f"{nc} colors (want {expect_colors})")
    else:
        print(f"  [info] colors declared: {nc}")
    return ok


def _load(path):
    m = trimesh.load(path)
    return m.to_geometry() if hasattr(m, "to_geometry") else m


def check_fit(body_path, hat_path):
    """B-PUZZLE FIT: the parts must interlock like a puzzle when placed at their shared coords —
    the hat must seat ON THE HEAD (head fills the hat, crown reaches the hat's inner top), NOT float,
    sink, or sit off on the spear tip. (This is the automated version of the hat-on-spear bug.)"""
    print("\n=== PUZZLE FIT: body + hat ===")
    body, hat = _load(body_path), _load(hat_path)
    hv = hat.vertices
    cx, cz = float(hv[:, 0].mean()), float(hv[:, 2].mean())          # hat axis
    hlo, hhi = float(hv[:, 1].min()), float(hv[:, 1].max())
    R = 0.25 * float(max(np.ptp(hv[:, 0]), np.ptp(hv[:, 2])))        # ~quarter of the brim width
    d = np.hypot(body.vertices[:, 0] - cx, body.vertices[:, 2] - cz)
    near = body.vertices[d < max(R, 8.0)]
    ok = True
    def rec(name, passed, detail=""):
        nonlocal ok; ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}{'  — ' + detail if detail else ''}")
    # 1. the head must actually be inside the hat (body geometry within the hat footprint + Y span)
    inside = near[(near[:, 1] >= hlo) & (near[:, 1] <= hhi)]
    rec("head sits inside the hat (not off on the spear / not floating)",
        len(inside) > 200, f"{len(inside)} body verts under the hat axis within its height")
    # 2. the head crown / peg must reach the hat's inner top (so the peg enters the socket)
    crown = float(near[:, 1].max()) if len(near) else -1e9
    rec("crown/peg reaches the hat's inner top (peg in socket)",
        hlo <= crown <= hhi + 3.0, f"crown Y {crown:.1f} vs hat Y [{hlo:.1f},{hhi:.1f}]")
    # 3. hat centered over the head, not off-axis (the spear tip is far from the body centre)
    bxz = body.vertices[:, [0, 2]].mean(0)
    off = float(np.hypot(cx - bxz[0], cz - bxz[1]))
    rec("hat centered over the head (not off-axis)", off < 25.0, f"hat axis {off:.1f}mm from body centre")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("parts", nargs="+", help="3MF files. Name a body part *body* (expects 4 colors), "
                                             "a hat part *hat* (expects 1).")
    ap.add_argument("--mm", type=float, default=150.0)
    a = ap.parse_args()
    allok = True
    for p in a.parts:
        low = os.path.basename(p).lower()
        is_body = "body" in low
        expect = 4 if is_body else (1 if "hat" in low else None)
        # the body spans the full figure height; the hat is a sub-part
        allok = check_part(p, expect, a.mm, is_full=is_body) and allok
    # PUZZLE-FIT: if a body part and a hat part are both present, they must mate like a puzzle.
    bp = next((p for p in a.parts if "body" in os.path.basename(p).lower()), None)
    hp = next((p for p in a.parts if "hat" in os.path.basename(p).lower()), None)
    if bp and hp:
        allok = check_fit(bp, hp) and allok
    print("\n" + ("ALL CHECKS PASSED (A + puzzle-fit). Now do the rest of B + C by eye." if allok
                  else "FAILURES above — FIX before delivering."))
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
