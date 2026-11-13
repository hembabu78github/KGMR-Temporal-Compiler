from pathlib import Path
import sys

try:
    from pyshacl import validate
except ImportError:
    raise SystemExit(
        "pyshacl is not installed. Install it in the researcher environment, then rerun this script."
    )

ROOT=Path(__file__).resolve().parent
ontology=ROOT/"ckd_tkg_r1_ontology.ttl"
shapes=ROOT/"ckd_tkg_r1_shapes.ttl"

def run(data_file, expected):
    conforms, report_graph, report_text = validate(
        data_graph=str(ROOT/data_file),
        shacl_graph=str(shapes),
        ont_graph=str(ontology),
        inference="rdfs",
        abort_on_first=False,
        allow_infos=True,
        allow_warnings=True,
        meta_shacl=True,
        advanced=True,
        debug=False,
    )
    print(f"\n=== {data_file} ===")
    print(report_text)
    if bool(conforms) != expected:
        raise SystemExit(f"FAIL: expected conforms={expected}, got {conforms}")
    print(f"PASS expected conforms={expected}")

run("ckd_tkg_r1_shacl_positive_fixture.ttl", True)
run("ckd_tkg_r1_shacl_negative_fixture.ttl", False)
print("\nSHACL regression suite PASS")
