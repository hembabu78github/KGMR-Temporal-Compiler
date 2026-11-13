from pathlib import Path
import hashlib, sys

ROOT = Path(__file__).resolve().parent
manifest = ROOT / "PACKAGE_INITIAL_CHECKSUMS.sha256"
failures = []
for line in manifest.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    expected, name = line.split("  ", 1)
    p = ROOT / name
    if not p.exists():
        failures.append(f"MISSING: {name}")
        continue
    got = hashlib.sha256(p.read_bytes()).hexdigest()
    if got != expected:
        failures.append(f"MISMATCH: {name}")
    else:
        print(f"OK: {name}")
if failures:
    for x in failures:
        print("FAIL:", x)
    raise SystemExit(1)
print("PACKAGE CHECKSUMS PASS")
