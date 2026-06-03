#!/usr/bin/env bash
# photogrammetry.sh — multiple photos -> textured mesh, CPU-only (COLMAP sparse + OpenMVS dense).
#
# Usage: photogrammetry.sh <images_dir> <work_dir>
#   <images_dir>  folder of input photos (jpg/png) of one object, many overlapping views
#   <work_dir>    output workspace (created); final mesh ends up at <work_dir>/model/
#
# Stages (all CPU, no CUDA):
#   1 COLMAP feature_extractor   -> detect SIFT features per photo
#   2 COLMAP exhaustive_matcher  -> match features across photos
#   3 COLMAP mapper              -> solve camera poses + sparse point cloud (SfM)
#   4 COLMAP image_undistorter   -> rectified images for dense step
#   5 OpenMVS InterfaceCOLMAP    -> import poses into OpenMVS scene
#   6 OpenMVS DensifyPointCloud  -> dense point cloud (CPU patch-match)
#   7 OpenMVS ReconstructMesh    -> surface mesh from dense cloud
#   8 OpenMVS RefineMesh         -> photometric mesh refinement (slow, optional via REFINE=0)
#   9 OpenMVS TextureMesh        -> bake color texture onto mesh
set -euo pipefail
IMAGES="${1:?usage: photogrammetry.sh <images_dir> <work_dir>}"
WORK="${2:?usage: photogrammetry.sh <images_dir> <work_dir>}"
REFINE="${REFINE:-1}"   # set REFINE=0 to skip the slow refinement stage
NPROC="$(nproc)"
log() { echo "[photogram $(date -u +%H:%M:%S)] $*"; }

mkdir -p "$WORK"/{sparse,dense,model}
DB="$WORK/database.db"

log "1/9 feature extraction (CPU)"
colmap feature_extractor --database_path "$DB" --image_path "$IMAGES" \
  --ImageReader.single_camera 1 --SiftExtraction.use_gpu 0

log "2/9 exhaustive matching (CPU)"
colmap exhaustive_matcher --database_path "$DB" --SiftMatching.use_gpu 0

log "3/9 sparse reconstruction / SfM (CPU)"
colmap mapper --database_path "$DB" --image_path "$IMAGES" --output_path "$WORK/sparse"

# mapper writes sparse/0, sparse/1, ... pick the largest model (most images)
BEST="$(ls -d "$WORK"/sparse/*/ 2>/dev/null | head -1)"
[ -n "$BEST" ] || { echo "ERROR: SfM produced no model — photos likely lack overlap/texture"; exit 2; }
log "    using sparse model: $BEST"

log "4/9 undistort images for dense step"
colmap image_undistorter --image_path "$IMAGES" --input_path "${BEST%/}" \
  --output_path "$WORK/dense" --output_type COLMAP --max_image_size 2400

log "5/9 import to OpenMVS"
cd "$WORK/dense"
InterfaceCOLMAP -i . -o "$WORK/model/scene.mvs" --image-folder ./images

cd "$WORK/model"
log "6/9 densify point cloud (CPU — this is the long one)"
DensifyPointCloud scene.mvs --cuda-device -1 --number-views 0

log "7/9 reconstruct surface mesh"
ReconstructMesh scene_dense.mvs

MESH=scene_dense_mesh
if [ "$REFINE" = "1" ]; then
  log "8/9 refine mesh (CPU, slow — REFINE=0 to skip)"
  RefineMesh scene_dense_mesh.mvs --cuda-device -1 --max-face-area 16 || log "refine failed, continuing with unrefined mesh"
  [ -f scene_dense_mesh_refine.mvs ] && MESH=scene_dense_mesh_refine
else
  log "8/9 refinement skipped (REFINE=0)"
fi

log "9/9 texture mesh"
TextureMesh "${MESH}.mvs"

log "DONE. Textured mesh: $WORK/model/${MESH}_texture.ply"
echo "${WORK}/model/${MESH}_texture.ply"
