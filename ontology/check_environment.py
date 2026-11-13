import sys
print("Python:", sys.version.replace("\n", " "))
try:
    import rdflib
    print("rdflib:", rdflib.__version__)
except Exception as e:
    print("FAIL: rdflib import:", e)
    raise SystemExit(1)
try:
    import pyshacl
    print("pyshacl:", getattr(pyshacl, "__version__", "unknown"))
except Exception as e:
    print("FAIL: pyshacl import:", e)
    raise SystemExit(1)
print("ENVIRONMENT PASS")
