# Reproduction guide

Work from the repository root in an isolated environment. Suggested environment: CPython 3.11. The archive was reconstructed using the original code and frozen results; byte equality across different Python runtimes or operating systems is not guaranteed.

## 1. Verify distribution integrity

```python
from pathlib import Path
import hashlib
root = Path('.')
for row in (root/'SHA256SUMS.txt').read_text().splitlines():
    digest, filename = row.split('  ', 1)
    assert hashlib.sha256((root/filename).read_bytes()).hexdigest() == digest, filename
print('All release file hashes match')
```

## 2. Compiler tests

```bash
python scripts/verify_release.py
```

Some historical runs require dependencies listed in the original RC1 requirements; do not assume an arbitrary Python version reproduces generated-source bytes.

## 3. Requirements-based MR baseline

```bash
python experiment/spec_baseline/test_baseline.py
```

## 4. Expanded matched comparison

```bash
python experiment/spec_baseline/run_task2.py
```

This script rewrites `task2_case_results.csv`, `task2_mutant_classifications.csv`, and `task2_summary.json` under `experiment/spec_baseline/`. Run it in a **copy** if comparing byte hashes to the committed results. It evaluates 388 syntactic mutants against 24 synthetic source cases. For publication, distinguish 103 error-free locally distinguishable mutants, 245 with no observed difference, and 40 with errors. The comparison is **same-source-case and matched-budget**, but three of the 24 transformed follow-ups differ between implementations.

## 5. Ontology validation

Ontology files and SHACL fixtures reside in `ontology/`. Use the supplied `ontology/validate_ckd_tkg_r1.py` and `ontology/run_ckd_tkg_r1_shacl.py` with pinned RDFLib/pySHACL dependencies. Structural checks and SHACL are separate from the fixture-driven IR-to-MR compiler's executable evaluation.

## 6. Review boundaries

- No RDF-to-IR extraction run is claimed.
- No global mutant-equivalence proof or external blind evaluation is claimed.
- Comparison / ablation outputs in `experiments/original_controlled/` are archived records; a complete standalone original regeneration harness was not recovered.
- Avoid treating 103/103 exact-output distinguishability as a balanced MR-generation baseline.
