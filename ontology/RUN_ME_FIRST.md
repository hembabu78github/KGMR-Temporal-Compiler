# CKD-TKG R1.0 — Researcher Execution Package

This package contains the corrected C3-014 RDF/OWL implementation and the
corrected C3-015 SHACL regression suite. It intentionally contains no virtual
environment, cache, or site-packages files.

## Expected baseline

- Ontology after build: 1,303 triples
- OWL classes: 93
- Object properties: 107
- Datatype properties: 39
- C3-014 structural validator: PASS
- C3-015 positive fixture: Conforms=True
- C3-015 negative fixture: Conforms=False
- Final runner line: SHACL regression suite PASS

The validator includes explicit regression checks for:
- KidneyFailureRiskAssessment vs ProgressionRiskAssessment disjointness
- KDIGOCGARiskCategory vs MRTestingRiskCategory disjointness

The corrected SHACL file does NOT use the pySHACL-incompatible `VALUES`
construct in its eight-gate completeness constraint.

## 1. Create your virtual environment

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Windows Command Prompt

```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 2. Verify the package before running

```bash
python verify_package_checksums.py
python check_environment.py
```

`PACKAGE_INITIAL_CHECKSUMS.sha256` verifies the files as delivered. After
`build_ckd_tkg_r1.py` runs, the ontology serializations are intentionally
regenerated, so their byte-level checksums may change.

## 3. Recommended: run everything with one command

```bash
python run_all_checks.py
```

This performs, in order:

1. C3-014 ontology rebuild
2. C3-014 structural validation
3. C3-015 pySHACL positive/negative regression suite
4. SHA-256 hashes of the final generated artifacts

It also writes the complete run evidence to:

`researcher_execution_output.txt`

Please keep that file unchanged and return it for the closure review.

## 4. Equivalent manual commands

```bash
python build_ckd_tkg_r1.py
python validate_ckd_tkg_r1.py
python run_ckd_tkg_r1_shacl.py
```

## Important

Use the files in THIS package together. Do not mix them with an older
1,301-triple ontology or the earlier SHACL shapes containing a `VALUES`
clause.
