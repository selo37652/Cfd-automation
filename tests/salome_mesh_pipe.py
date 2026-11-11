# SALOME 9.16 (run in SALOME's own Python, NOT system Python).
# Example: salome -t -w1 tests/salome_mesh_pipe.py
# Input STEP is a 50-mm-inner-diameter, 5000-mm-high *fluid domain*, in mm.
# This first mesh is a geometry/import smoke test, NOT mesh-independent CFD.
import os
import json
import math
from pathlib import Path
import salome
salome.salome_init()

from salome.geom import geomBuilder
from salome.smesh import smeshBuilder
import SMESH

geompy = geomBuilder.New()
smesh = smeshBuilder.New()

step_path = Path(os.environ.get("CFD_STEP_IN", "outputs/pipe_50mm_5m.step")).resolve()
out_path = Path(os.environ.get("CFD_UNV_OUT", "outputs/pipe_50mm_5m.unv")).resolve()
max_cells = int(os.environ.get("CFD_MAX_CELLS", "400000"))
max_size_mm = float(os.environ.get("CFD_MESH_MAX_MM", "15"))
min_size_mm = float(os.environ.get("CFD_MESH_MIN_MM", "4"))
if not (0 < min_size_mm <= max_size_mm <= 50):
    raise RuntimeError("Invalid positive mesh size parameters")
if not (1000 <= max_cells <= 2000000):
    raise RuntimeError("Invalid CFD_MAX_CELLS")
if not step_path.is_file():
    raise FileNotFoundError("Missing STEP file: " + str(step_path))

fluid = geompy.ImportSTEP(str(step_path), False, False)
if isinstance(fluid, (tuple, list)):
    if len(fluid) != 1:
        raise RuntimeError("Expected only one fluid solid in STEP")
    fluid = fluid[0]
if geompy.NumberOfSolids(fluid) != 1:
    raise RuntimeError("STEP must contain exactly one closed solid")
bbox = geompy.BoundingBox(fluid, True)
expected_bbox = [-25.0, 25.0, -25.0, 25.0, 0.0, 5000.0]
if any(abs(a - b) > 0.2 for a, b in zip(bbox, expected_bbox)):
    raise RuntimeError("STEP dimensions or units incorrect: %s" % str(bbox))
volume_mm3 = geompy.BasicProperties(fluid)[2]
expected_mm3 = math.pi * 25.0**2 * 5000.0
if abs(volume_mm3 / expected_mm3 - 1) > 0.001:
    raise RuntimeError("Incorrect internal fluid volume: %g" % volume_mm3)

faces = geompy.ExtractShapes(fluid, geompy.ShapeType["FACE"], True)
if len(faces) != 3:
    raise RuntimeError("Expected 3 cylinder faces (inlet, outlet, wall), got %d" % len(faces))
face_ids = {"inlet": [], "outlet": [], "wall": []}
for face in faces:
    centroid = geompy.PointCoordinates(geompy.MakeCDG(face))
    z = centroid[2]
    f_id = geompy.GetSubShapeID(fluid, face)
    if abs(z) < 0.1:
        face_ids["inlet"].append(f_id)
    elif abs(z - 5000.0) < 0.1:
        face_ids["outlet"].append(f_id)
    else:
        face_ids["wall"].append(f_id)
if any(len(ids) != 1 for ids in face_ids.values()):
    raise RuntimeError("Cannot uniquely identify inlet/outlet/wall: %s" % str(face_ids))

geompy.addToStudy(fluid, "pipe_fluid_volume_50mm_5m")
groups = {}
for name, ids in face_ids.items():
    group = geompy.CreateGroup(fluid, geompy.ShapeType["FACE"])
    geompy.UnionIDs(group, ids)
    geompy.addToStudyInFather(fluid, group, name)
    groups[name] = group

mesh = smesh.Mesh(fluid, "pipe_50mm_5m_NETGEN")
algo = mesh.Tetrahedron(smeshBuilder.NETGEN_1D2D3D)
params = algo.Parameters()
params.SetMaxSize(max_size_mm)
params.SetMinSize(min_size_mm)
if not mesh.Compute():
    raise RuntimeError("NETGEN Compute() failed")
n_tet = mesh.NbTetras()
n_nodes = mesh.NbNodes()
if n_tet <= 0 or n_nodes <= 0:
    raise RuntimeError("SALOME did not create a valid 3D tetrahedral mesh")
if n_tet > max_cells:
    raise RuntimeError("Mesh has %d tetrahedra, above safety limit %d" % (n_tet, max_cells))

count_groups = {}
for name, shape_group in groups.items():
    boundary = mesh.GroupOnGeom(shape_group, name, SMESH.FACE)
    size = boundary.Size()
    if size <= 0:
        raise RuntimeError("Empty boundary group: " + name)
    count_groups[name] = size

out_path.parent.mkdir(parents=True, exist_ok=True)
mesh.ExportUNV(str(out_path))
if not out_path.is_file() or out_path.stat().st_size < 1024:
    raise RuntimeError("Missing or empty UNV export")
report = {
    "geometry": "vertical 50mm ID x 5m fluid cylinder",
    "unit": "mm",
    "cfd_conversion_note": "Convert mesh length mm -> m (scale 0.001) before solving in OpenFOAM",
    "volume_mm3": volume_mm3,
    "nodes": n_nodes,
    "tetrahedra": n_tet,
    "boundary_face_counts": count_groups,
    "max_element_size_mm": max_size_mm,
    "min_element_size_mm": min_size_mm,
    "unv_path": str(out_path),
    "unv_bytes": out_path.stat().st_size,
    "verified_by": "SALOME script runtime only; not CFD mesh-independence assessment"
}
out_path.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("CFD_SALOME_MESH_OK " + json.dumps(report))
