# C4-014 — Executable Python Transformation and Oracle Generation

C4-014 converts each C4-013 CandidateMR specification into a deterministic Python module exposing:

- `transform(...)` — executable T;
- `oracle(...)` — executable R;
- `execute(...)` — safety-gated source/follow-up CDS invocation plus oracle evaluation.

## Code generation is not admission

All 12 software CandidateMR specifications can be compiled into Python, but a generated module
is allowed to call the target CDS only when the researcher-returned C4-013 manifest indicates:

- C4-013 validation = VALID;
- C4-010 exception action = PROCEED;
- C4-011 temporal action = PROCEED and truth = TRUE;
- no unresolved C4-012 conflict ID.

Otherwise `execute()` returns `ABSTAIN` before the CDS callable is invoked.

This deliberately separates **executable artifact generation** from **admission to execute**.

## All 11 frozen transformations are implemented

`SHIFT_TIME`, `RESAMPLE_TRAJECTORY`, `DELAY_RESULT_ENTRY`, `SWAP_EQUIVALENT_ORDER`,
`REMOVE_REDUNDANT_OBSERVATION`, `MASK_REQUIRED_OBSERVATION`, `INCREASE_SLOPE`,
`DECREASE_SLOPE`, `INSERT_TRANSIENT_AKI`, `CONVERT_UNIT`, and `PRESERVE_CLINICAL_STATE`.

The AKI identifier remains an operational name only. The runtime emits AKI-like deterioration/recovery
observations with `formal_diagnosis_AKI=False`; it never asserts a formal AKI diagnosis.

## Oracle support

All seven formal R families are supported:

- equality within tolerance;
- monotonic increase;
- monotonic decrease;
- ordinal non-decrease;
- ordinal non-increase;
- bounded change;
- decision-level relations.

Missing/non-computable outputs return `INDETERMINATE`. `ABSTAIN` remains a control value, not an R family.

## Source immutability

Every transformation deep-copies its source case. Software tests verify the original case is unchanged.

## CDS-neutral interface

The generated `execute()` function accepts a Python callable representing the target CDS. No CDS model,
threshold, vendor, or architecture is embedded in C4-014.

## Cross-platform C4-013 verification

Windows and Unix newline conventions may differ at the byte level. C4-014 therefore verifies the
canonical `semantic_spec_fingerprint` from the researcher manifest, not cross-platform byte identity.
All 12 semantic fingerprints must match before code generation.

## Research boundary

All cases and outputs in this package are software fixtures. They do not establish clinical validity,
real CDS robustness, clinical error rates, or expert-approved MR yield.
