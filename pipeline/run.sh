#!/usr/bin/env bash
# run.sh — end-to-end: folder of photos -> printable STL/3MF. CPU-only.
#
# Usage: run.sh <images_dir> <work_dir> [--mask] [--no-refine]
#   --mask       remove photo backgrounds before reconstruction (good for cluttered scenes)
#   --no-refine  skip the slow OpenMVS RefineMesh stage (faster, slightly lower detail)
#
# Output: <work_dir>/result.stl and <work_dir>/result.3mf
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY=/opt/meshenv/bin/python
IMAGES="${1:?usage: run.sh <images_dir> <work_dir> [--mask] [--no-refine]}"
WORK="${2:?usage: run.sh <images_dir> <work_dir> [--mask] [--no-refine]}"
shift 2 || true
MASK=""; export REFINE=1
for arg in "$@"; do
  case "$arg" in
    --mask) MASK="--mask" ;;
    --no-refine) REFINE=0 ;;
  esac
done

mkdir -p "$WORK"
echo "[run] === 1. prep images ==="
"$PY" "$HERE/prep_images.py" "$IMAGES" "$WORK/prepped" $MASK --blur-drop 0.15

echo "[run] === 2. photogrammetry (COLMAP + OpenMVS) ==="
MESH_PLY="$(REFINE=$REFINE bash "$HERE/photogrammetry.sh" "$WORK/prepped" "$WORK/photogram" | tail -1)"
echo "[run] textured mesh: $MESH_PLY"

echo "[run] === 3. repair -> watertight printable ==="
"$PY" "$HERE/repair_mesh.py" "$MESH_PLY" "$WORK/result"

echo "[run] === DONE ==="
ls -lh "$WORK"/result.* 2>/dev/null
echo "[run] Printable files: $WORK/result.stl , $WORK/result.3mf"
