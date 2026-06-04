// alpha_wrap.cpp — CGAL 3D Alpha Wrapping: triangle soup -> guaranteed watertight, manifold,
// intersection-free mesh that PRESERVES thin protruding features (capes/coats) — unlike voxel
// shrink-wrap which collapses them. (Research-recommended fix for the cape-truncation defect.)
//
// Build: g++ -O3 -DNDEBUG alpha_wrap.cpp -o alpha_wrap -lgmp -lmpfr
// Usage: alpha_wrap <input.ply|obj|off> <output.ply> [relative_alpha=150] [relative_offset=3000]
//   smaller alpha (larger relative_alpha) = finer carving, preserves narrower straits/thin features.
#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/alpha_wrap_3.h>
#include <CGAL/Polygon_mesh_processing/bbox.h>
#include <CGAL/IO/polygon_soup_io.h>
#include <CGAL/Polygon_mesh_processing/IO/polygon_mesh_io.h>
#include <vector>
#include <array>
#include <iostream>
#include <cstdlib>

using K = CGAL::Exact_predicates_inexact_constructions_kernel;
using Point = K::Point_3;
using Mesh = CGAL::Surface_mesh<Point>;

int main(int argc, char** argv) {
  if (argc < 3) { std::cerr << "usage: alpha_wrap <in> <out.ply> [rel_alpha] [rel_offset]\n"; return 1; }
  const char* in = argv[1];
  const char* out = argv[2];
  const double rel_alpha  = (argc > 3) ? std::atof(argv[3]) : 150.0;
  const double rel_offset = (argc > 4) ? std::atof(argv[4]) : 3000.0;

  std::vector<Point> points;
  std::vector<std::array<std::size_t, 3>> faces;
  if (!CGAL::IO::read_polygon_soup(in, points, faces) || points.empty()) {
    std::cerr << "alpha_wrap: could not read " << in << "\n"; return 2;
  }
  std::cerr << "alpha_wrap: " << points.size() << " pts, " << faces.size() << " faces\n";

  CGAL::Bbox_3 bb;
  for (const auto& p : points) bb += p.bbox();
  const double diag = std::sqrt(CGAL::square(bb.xmax()-bb.xmin())
                              + CGAL::square(bb.ymax()-bb.ymin())
                              + CGAL::square(bb.zmax()-bb.zmin()));
  const double alpha  = diag / rel_alpha;
  const double offset = diag / rel_offset;
  std::cerr << "alpha_wrap: diag=" << diag << " alpha=" << alpha << " offset=" << offset << "\n";

  Mesh wrap;
  CGAL::alpha_wrap_3(points, faces, alpha, offset, wrap);
  std::cerr << "alpha_wrap: result " << num_vertices(wrap) << " verts, " << num_faces(wrap) << " faces\n";

  if (!CGAL::IO::write_polygon_mesh(out, wrap, CGAL::parameters::stream_precision(17))) {
    std::cerr << "alpha_wrap: could not write " << out << "\n"; return 3;
  }
  return 0;
}
