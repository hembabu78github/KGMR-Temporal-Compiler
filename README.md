# KG-to-MR Temporal Compiler — research reproducibility

Research code and **synthetic** verification fixtures for the deterministic compilation of evidence-bearing temporal specifications into executable metamorphic relations.

## What has been implemented

The **evaluated** compiler consumes prepared typed intermediate-representation (IR) fixtures and emits executable CandidateMR specifications and generated Python wrappers. The RDF/OWL graph and SHACL source are provided as a *separate source-representation and structural-validation component*. **A fully evaluated RDF-to-IR extraction pipeline is not claimed**.

## Main contents

| Path | Contents |
|---|---|
| `rc1/Chapter4_Compiler_Release_Candidate_RC1/` | Frozen historical RC1 compiler directory, retained under its original name for provenance and compatibility |
| `ontology/` | CKD-TKG R1.0 ontology, SHACL constraints, fixtures and graph validation scripts |
| `run_expanded.py` | Original small 24-mutant synthetic experiment runner |
| `experiment/study.py` | Mechanical AST mutation generation and original comparison scaffolding |
| `experiment/spec_baseline/` | Independently implemented *within-study* requirements-to-MR comparison |
| `experiments/legacy_24_mutants/` | Historical 24-mutant experiment records (separate from the 388-mutant study) |
| `SHA256SUMS.txt` | Hash manifest for the distributable snapshot |

## Key findings and interpretation

- Frozen compiler: 13 prepared IR seeds, 10 selected, 12 generated candidate artifacts covering 11 operators; 12/12 static passes, 8/12 execution-admissible; 291/291 integrated unit tests in the original acceptance record.
- Original 24-mutant synthetic pilot extension: 17/24 faults detected by the generated MRs. This is a separate small study.
- Expanded mechanical-mutation experiment: 388 mutants from synthetic target code; 103 were error-free and distinguishable *on evaluated inputs*; both generated MRs and within-study requirements baseline detected 57/103. 245 mutants showed no observed output difference; **global equivalence is not established**. Another 40 mutants raised at least one execution error and are reported separately.
- The baseline is **not** independently authored by a blinded outside research group. This comparison does not demonstrate mutation-kill-rate superiority for the compiler. The exact-output distinguishability control has additional oracle information.
- No patient data, clinical validation, or real-world clinical effectiveness are claimed.

## Quick start (Python)

Create an isolated Python environment. Install requirements separately using pip only from trusted sources. See `docs/REPRODUCE.md` for the checked commands and dependency details.

```bash
python scripts/verify_release.py
python experiment/spec_baseline/test_baseline.py
python experiment/spec_baseline/run_task2.py
```

Run the comparator from the **repository root**. It automatically resolves the provided `run_expanded.py` and RC1 fixture path; no `/mnt/data` location is needed.

## Licensing

- Author-written software: MIT (`LICENSE`).
- Author-created synthetic research fixtures and results: CC BY 4.0 (`LICENSES/DATA-CC-BY-4.0-NOTICE.md`).
- CKD-TKG ontology: retains its original project MIT notice (`LICENSES/ONTOLOGY-MIT.txt`).
- Third-party Python libraries: separately installed and governed by their original licenses (`LICENSES/THIRD_PARTY.md`).

## Integrity

`SHA256SUMS.txt` enumerates all release files other than itself. It is a *distribution integrity check*, not a proof of originality or source authenticity. Re-running scripts can overwrite committed frozen result files; work in a fresh clone to compare outputs with an untouched snapshot.

## Research boundaries

Source templates and clinical guideline material are not a validated clinical rulebase. The controlled comparison uses hand-authored requirements in the same study, not external blinded MR generation. Report the original RC1 compiler evidence and the expanded synthetic mutation results separately.

## Release evidence hygiene

This is a corrected successor snapshot to v1.0.0. The earlier version is preserved at Zenodo for provenance. The original RC1 directory name is historical and is retained to avoid breaking the frozen runner. A scratch file with alternative provisional counts was excluded; the reported 388-mutant analysis uses the verified `experiment/spec_baseline/` outputs and the 103-error-free-distinguishable denominator. The recorded methods are not claimed to have been preregistered before outcome inspection.
