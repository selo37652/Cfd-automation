# FreeCADCmd top-level script: generate the *fluid domain*, not the pipe wall.
# Run via FreeCADCmd.exe create_pipe_step.py
import os
import math
import json
from pathlib import Path
import FreeCAD as App
import Part

DIAMETER_MM = 160.0
LENGTH_MM = 3000.0
RADIUS_MM = DIAMETER_MM / 2
out = Path(os.environ.get("CFD_STEP_OUT", "pipe_fluid_volume.step")).resolve()
out.parent.mkdir(parents=True, exist_ok=True)

shape = Part.makeCylinder(RADIUS_MM, LENGTH_MM)
if shape.isNull() or not shape.isValid() or len(shape.Solids) != 1:
    raise RuntimeError("FreeCAD pipe fluid domain is not one valid solid")

expected_volume = math.pi * RADIUS_MM**2 * LENGTH_MM
if abs(shape.Volume / expected_volume - 1) > 1e-7:
    raise RuntimeError("Solid volume differs from analytical cylinder volume")

shape.exportStep(str(out))
if not out.exists() or out.stat().st_size < 1000:
    raise RuntimeError("STEP export file is missing or unexpectedly small")
with out.open("rb") as handle:
    header = handle.read(512)
if b"ISO-10303-21" not in header:
    raise RuntimeError("STEP file header not found")

report = {
    "geometry": "cylindrical fluid domain",
    "diameter_mm": DIAMETER_MM,
    "length_mm": LENGTH_MM,
    "volume_mm3": shape.Volume,
    "expected_volume_mm3": expected_volume,
    "faces": len(shape.Faces),
    "solids": len(shape.Solids),
    "valid": bool(shape.isValid()),
    "step_bytes": out.stat().st_size,
    "step_path": str(out),
    "units": "mm"
}
report_file = out.with_suffix(".json")
report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("CFD_STEP_OK " + json.dumps(report))
