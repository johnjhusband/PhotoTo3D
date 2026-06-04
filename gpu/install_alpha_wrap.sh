#!/usr/bin/env bash
# install_alpha_wrap.sh — build the CGAL alpha-wrap repair tool on the GPU box.
# CGAL's apt package (5.4 on Ubuntu 24.04) is too old for alpha_wrap_3 (needs >=5.5), and CGAL is
# header-only, so we just fetch a newer release's headers and compile alpha_wrap.cpp against them.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"      # alpha_wrap.cpp sits next to this script (gpu/)
CPP="$HERE/alpha_wrap.cpp"
[ -f "$CPP" ] || CPP="/workspace/alpha_wrap.cpp"   # fallback to flat layout
cd /workspace
export DEBIAN_FRONTEND=noninteractive
apt-get install -y --no-install-recommends g++ libgmp-dev libmpfr-dev libboost-dev >/dev/null 2>&1 || true

# CGAL 5.6.1 headers. The box's network can stall on this download — if it does, fetch the tarball on
# a machine with good network and rsync it to /workspace/CGAL-5.6.1.tar.xz, then re-run.
if [ ! -f CGAL-5.6.1/include/CGAL/alpha_wrap_3.h ]; then
  [ -s CGAL-5.6.1.tar.xz ] || curl -sL --retry 10 --retry-all-errors \
    -o CGAL-5.6.1.tar.xz https://github.com/CGAL/cgal/releases/download/v5.6.1/CGAL-5.6.1.tar.xz
  tar xf CGAL-5.6.1.tar.xz
fi

g++ -O3 -DNDEBUG -DCGAL_NDEBUG -I/workspace/CGAL-5.6.1/include "$CPP" -o /workspace/alpha_wrap -lgmp -lmpfr
echo "alpha_wrap built:"; ls -la /workspace/alpha_wrap
