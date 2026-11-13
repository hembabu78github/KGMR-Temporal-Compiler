from pathlib import Path
import subprocess, sys, datetime, hashlib, importlib

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "researcher_execution_output.txt"

def emit(text=""):
    print(text)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(text + "\n")

def run_step(title, script):
    emit("")
    emit("=" * 78)
    emit(title)
    emit("=" * 78)
    p = subprocess.run(
        [sys.executable, str(ROOT / script)],
        cwd=ROOT,
        text=True,
        capture_output=True
    )
    if p.stdout:
        emit(p.stdout.rstrip())
    if p.stderr:
        emit("[stderr]")
        emit(p.stderr.rstrip())
    emit(f"exit_code={p.returncode}")
    if p.returncode != 0:
        emit(f"STOPPED: {title} failed.")
        raise SystemExit(p.returncode)

OUT.write_text("", encoding="utf-8")
emit("CKD-TKG R1.0 researcher execution evidence")
emit("Timestamp: " + datetime.datetime.now().astimezone().isoformat())
emit("Python: " + sys.version.replace("\n", " "))

try:
    import rdflib
    emit("rdflib: " + rdflib.__version__)
except Exception as e:
    emit("FAIL importing rdflib: " + repr(e))
    raise SystemExit(1)

try:
    import pyshacl
    emit("pyshacl: " + getattr(pyshacl, "__version__", "unknown"))
except Exception as e:
    emit("FAIL importing pyshacl: " + repr(e))
    emit("Install dependencies with: python -m pip install -r requirements.txt")
    raise SystemExit(1)

run_step("C3-014 BUILD", "build_ckd_tkg_r1.py")
run_step("C3-014 STRUCTURAL VALIDATION", "validate_ckd_tkg_r1.py")
run_step("C3-015 SHACL REGRESSION", "run_ckd_tkg_r1_shacl.py")

emit("")
emit("=" * 78)
emit("FINAL ARTIFACT HASHES")
emit("=" * 78)
for name in [
    "ckd_tkg_r1_manifest.json",
    "ckd_tkg_r1_ontology.ttl",
    "ckd_tkg_r1_ontology.owl",
    "ckd_tkg_r1_shapes.ttl",
    "ckd_tkg_r1_shacl_positive_fixture.ttl",
    "ckd_tkg_r1_shacl_negative_fixture.ttl",
    "build_ckd_tkg_r1.py",
    "validate_ckd_tkg_r1.py",
    "run_ckd_tkg_r1_shacl.py",
]:
    p = ROOT / name
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    emit(f"{digest}  {name}")

emit("")
emit("ALL RESEARCHER EXECUTION CHECKS PASSED")
emit("Retain researcher_execution_output.txt and send it back for C3-014/C3-015 closure review.")
