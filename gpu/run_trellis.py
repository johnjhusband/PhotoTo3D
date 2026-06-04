#!/usr/bin/env python3
"""run_trellis.py — image(s) -> 3D mesh (GLB) with TRELLIS, then STL/3MF.

Accepts one OR many images. With >1 image it uses TRELLIS multi-image conditioning
(best when the images are consistent views of the SAME subject; very mixed styles can hurt).

Usage:
  python run_trellis.py <out_dir> <image1> [image2 ...] [--seed N]
  python run_trellis.py <out_dir> --dir <folder_of_images> [--seed N]

Outputs in <out_dir>: model.glb, model.stl, model.3mf, preview.png, preview.mp4
"""
import os, sys, glob
os.environ.setdefault("ATTN_BACKEND", "xformers")
os.environ.setdefault("SPCONV_ALGO", "native")

# Python puts THIS script's dir on sys.path, not the cwd, so the `trellis` package (in the cloned
# repo) isn't found when the script lives elsewhere. Add TRELLIS_HOME (or the common clone path).
_trellis_home = os.environ.get("TRELLIS_HOME", "/workspace/TRELLIS")
if os.path.isdir(os.path.join(_trellis_home, "trellis")) and _trellis_home not in sys.path:
    sys.path.insert(0, _trellis_home)

from PIL import Image
import imageio
from trellis.pipelines import TrellisImageTo3DPipeline
from trellis.utils import postprocessing_utils, render_utils


def parse_args(argv):
    if len(argv) < 3:
        sys.exit("usage: run_trellis.py <out_dir> <image1> [image2 ...] [--seed N]\n"
                 "       run_trellis.py <out_dir> --dir <folder> [--seed N]")
    outdir = argv[1]
    seed = 1
    imgs = []
    i = 2
    while i < len(argv):
        a = argv[i]
        if a == "--seed":
            seed = int(argv[i + 1]); i += 2
        elif a == "--dir":
            folder = argv[i + 1]; i += 2
            for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
                imgs += glob.glob(os.path.join(folder, ext))
        else:
            imgs.append(a); i += 1
    imgs = sorted(set(imgs))
    if not imgs:
        sys.exit("no input images given")
    return outdir, imgs, seed


def main():
    outdir, paths, seed = parse_args(sys.argv)
    os.makedirs(outdir, exist_ok=True)
    images = [Image.open(p) for p in paths]
    print(f"[trellis] {len(images)} input image(s): {', '.join(os.path.basename(p) for p in paths)}")

    print("[trellis] loading pipeline (downloads weights on first run)...")
    pipe = TrellisImageTo3DPipeline.from_pretrained("JeffreyXiang/TRELLIS-image-large")
    pipe.cuda()

    # quality settings (override via env). Higher steps = crisper geometry/texture.
    # SS_CFG raised 7.5->9 (research 2026): higher sparse-structure guidance forces TRELLIS to COMMIT
    # to the face/structure in the image — the main lever against the blank-mask face. slat stays 3.0
    # (raising it adds surface artifacts). PREPROCESS=0 when feeding an already-cleaned reference
    # (our isnet-anime bg removal on gray) so TRELLIS does NOT re-run its photo-trained rembg, which
    # is what ate the pale anime face.
    steps = int(os.environ.get("STEPS", "30"))
    ss_cfg = float(os.environ.get("SS_CFG", "9.0"))
    slat_cfg = float(os.environ.get("SLAT_CFG", "3.0"))
    preprocess = os.environ.get("PREPROCESS", "1") != "0"
    ss = {"steps": steps, "cfg_strength": ss_cfg}
    slat = {"steps": steps, "cfg_strength": slat_cfg}
    print(f"[trellis] steps={steps} ss_cfg={ss_cfg} slat_cfg={slat_cfg} preprocess_image={preprocess}")

    if len(images) == 1:
        print(f"[trellis] single-image run (seed={seed})")
        outputs = pipe.run(images[0], seed=seed, formats=["gaussian", "mesh"],
                           preprocess_image=preprocess,
                           sparse_structure_sampler_params=ss, slat_sampler_params=slat)
    else:
        print(f"[trellis] multi-image run over {len(images)} images (seed={seed})")
        # 'stochastic' multi-image mode conditions on all views jointly
        outputs = pipe.run_multi_image(images, seed=seed, formats=["gaussian", "mesh"],
                                       preprocess_image=preprocess, mode="stochastic",
                                       sparse_structure_sampler_params=ss, slat_sampler_params=slat)

    # turntable preview to eyeball before printing
    try:
        frames = render_utils.render_video(outputs["gaussian"][0], num_frames=30)["color"]
        imageio.mimsave(os.path.join(outdir, "preview.mp4"), frames, fps=15)
        imageio.imwrite(os.path.join(outdir, "preview.png"), frames[0])
        print(f"[trellis] wrote preview.png / preview.mp4")
    except Exception as e:
        print(f"[trellis] preview render skipped: {e}")

    print("[trellis] exporting textured GLB")
    tex = int(os.environ.get("TEX", "2048"))      # higher texture res = crisper color detail
    # NOTE on convention: native TRELLIS `simplify` = fraction of faces to REMOVE (0.9 = remove 90%,
    # aggressive — collapses small features like the face). We default LOW (0.5) to PRESERVE facial
    # geometry; the printable decimation happens later in repair_mesh, so we don't over-simplify here.
    simp = float(os.environ.get("SIMPLIFY", "0.5"))
    glb = postprocessing_utils.to_glb(outputs["gaussian"][0], outputs["mesh"][0],
                                      simplify=simp, texture_size=tex)
    glb_path = os.path.join(outdir, "model.glb")
    glb.export(glb_path)

    # GLB -> printable STL/3MF (geometry only)
    import trimesh
    scene = trimesh.load(glb_path)
    mesh = (trimesh.util.concatenate([g for g in scene.geometry.values()])
            if isinstance(scene, trimesh.Scene) else scene)
    mesh.export(os.path.join(outdir, "model.stl"))
    mesh.export(os.path.join(outdir, "model.3mf"))
    print(f"[trellis] DONE -> {outdir}/model.{{glb,stl,3mf}} | "
          f"verts={len(mesh.vertices)} faces={len(mesh.faces)} watertight={mesh.is_watertight}")


if __name__ == "__main__":
    main()
