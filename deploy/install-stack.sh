#!/usr/bin/env bash
# install-stack.sh — install the CPU-only photos->printable-mesh stack on Ubuntu 24.04.
#
# Pipeline tools installed:
#   COLMAP        — Structure-from-Motion (sparse): feature extract, match, mapper. CPU path.
#   OpenMVS       — dense point cloud, mesh, refine, texture. Built CPU-only (no CUDA).
#   Python repair — pymeshlab, pymeshfix, trimesh, open3d for watertight STL/3MF + cleanup.
#   rembg         — automatic background removal / object masking for input photos.
#
# Idempotent-ish: re-running re-pulls/rebuilds. Logs every step so failures are diagnosable.
# Run as root on a fresh server.  Total time ~20-40 min on 8 cores (OpenMVS build dominates).
set -euo pipefail
log() { echo "[install $(date -u +%H:%M:%S)] $*"; }

export DEBIAN_FRONTEND=noninteractive
SRC=/opt/src
mkdir -p "$SRC"

log "apt update + base build tooling"
apt-get update -y
apt-get install -y --no-install-recommends \
  build-essential cmake git ca-certificates pkg-config wget unzip \
  python3 python3-pip python3-venv python3-dev python3-numpy

log "COLMAP (sparse SfM) from apt — CPU capable"
apt-get install -y colmap

log "OpenMVS build dependencies"
apt-get install -y --no-install-recommends \
  libpng-dev libjpeg-dev libtiff-dev libglu1-mesa-dev \
  libboost-all-dev \
  libopencv-dev libcgal-dev libcgal-qt5-dev \
  libatlas-base-dev libsuitesparse-dev libeigen3-dev \
  libceres-dev libglew-dev freeglut3-dev \
  libnanoflann-dev libgoogle-glog-dev libgflags-dev

log "Fetch VCGlib (OpenMVS dependency)"
rm -rf "$SRC/vcglib"
git clone --depth 1 https://github.com/cdcseacave/VCG.git "$SRC/vcglib"

log "Build TinyEXIF (OpenMVS dependency, not in apt)"
apt-get install -y --no-install-recommends libtinyxml2-dev
rm -rf "$SRC/TinyEXIF"
git clone --depth 1 https://github.com/cdcseacave/TinyEXIF.git "$SRC/TinyEXIF"
mkdir -p "$SRC/TinyEXIF/build" && cd "$SRC/TinyEXIF/build"
cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON
make -j"$(nproc)" && make install && ldconfig

log "Build TinyNPY (OpenMVS dependency, not in apt)"
rm -rf "$SRC/TinyNPY"
git clone --depth 1 https://github.com/cdcseacave/TinyNPY.git "$SRC/TinyNPY"
mkdir -p "$SRC/TinyNPY/build" && cd "$SRC/TinyNPY/build"
cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON
make -j"$(nproc)" && make install && ldconfig

log "Build PoseLib (OpenMVS dependency, not in apt)"
rm -rf "$SRC/PoseLib"
git clone --recursive --depth 1 https://github.com/PoseLib/PoseLib.git "$SRC/PoseLib"
mkdir -p "$SRC/PoseLib/build" && cd "$SRC/PoseLib/build"
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j"$(nproc)" && make install && ldconfig

log "Fetch + build OpenMVS (CPU-only, no CUDA)"
rm -rf "$SRC/openMVS"
git clone --depth 1 https://github.com/cdcseacave/openMVS.git "$SRC/openMVS"
mkdir -p "$SRC/openMVS/build"
cd "$SRC/openMVS/build"
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DVCG_ROOT="$SRC/vcglib" \
  -DOpenMVS_USE_CUDA=OFF \
  -DOpenMVS_USE_OPENMP=ON
make -j"$(nproc)"
make install
ldconfig
# OpenMVS installs binaries to /usr/local/bin/OpenMVS by default; symlink onto PATH
if [ -d /usr/local/bin/OpenMVS ]; then
  for b in /usr/local/bin/OpenMVS/*; do ln -sf "$b" "/usr/local/bin/$(basename "$b")"; done
fi

log "Python mesh-repair + masking tools (system venv)"
python3 -m venv /opt/meshenv
/opt/meshenv/bin/pip install --upgrade pip wheel
/opt/meshenv/bin/pip install \
  numpy pillow opencv-python-headless \
  trimesh pymeshfix pymeshlab open3d rembg onnxruntime

log "Verify installs"
echo "--- colmap ---"; colmap -h 2>&1 | head -3 || echo "COLMAP MISSING"
echo "--- OpenMVS DensifyPointCloud ---"; (DensifyPointCloud --help 2>&1 | head -3) || echo "OPENMVS MISSING"
echo "--- python ---"; /opt/meshenv/bin/python -c "import trimesh, pymeshfix, pymeshlab, open3d; print('py mesh tools OK')"

log "DONE. Stack installed."
