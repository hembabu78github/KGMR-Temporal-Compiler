# C4-013 — Deterministic Candidate-MR JSON/YAML Specification Generation

## Objective

C4-013 serializes the compiler artifacts produced by C4-006 through C4-012 into the
approved six-component representation:

`MR = <C,T,R,I,E,P>`

Each software-validation candidate is emitted in:

- canonical JSON;
- deterministic human-readable YAML;
- a manifest that records upstream fingerprints and control-state snapshots.

## Why control metadata is outside the CandidateMR semantic object

C4-010 and C4-011 software fixtures contain runtime truth/control outcomes such as:

- MissingDataException observed TRUE;
- temporal-precision INDETERMINATE;
- seeded precedence conflict controls;
- licensing/release blocking test controls.

Those values are useful for validating compiler behavior but are not generic MR semantics.

Therefore C4-013:

- retains the **exception predicate definition** in E;
- removes `observed_fixture_truth` from the generic E condition;
- keeps upstream system actions, temporal truth, and C4-012 conflict IDs in the
  external candidate manifest rather than inside `<C,T,R,I,E,P>`.

This prevents a software test outcome from becoming a permanent part of a reusable MR specification.

## Candidate identity

`candidate_mr_id` is generated from a canonical semantic projection of:

- C;
- T;
- final typed R;
- I;
- generic E;
- stable provenance/version fields from P.

It excludes:

- wall-clock generation timestamps;
- hostnames;
- process IDs;
- filesystem paths;
- runtime fixture truth;
- transient system-action snapshots.

Consequently, semantically identical compiler inputs yield the same candidate identity.

## JSON

JSON is emitted with:

- sorted keys;
- UTF-8;
- deterministic indentation;
- one file per candidate.

## YAML

The package implements a deterministic stdlib-only YAML emitter.

Strings are JSON-quoted where needed. JSON string syntax is valid YAML scalar syntax,
which gives deterministic escaping without introducing a PyYAML runtime dependency.

The generated YAML is intended as a review and interchange view of the same CandidateMR object.

## Validation

C4-013 applies:

1. a patched C4-007 JSON Schema interface;
2. an independent stdlib semantic validator;
3. deterministic ID/fingerprint repeat checks;
4. checks that no fixture truth leaks into E;
5. checks that expert MR validation remains `UNREVIEWED`.

C4-013 does not claim expert clinical validation.

## Schema correction

See `docs/C4_013_SCHEMA_CORRECTION_NOTE.md`.

The correction adds a dedicated `EXCEPTION` condition type for E only.
C condition-atom types remain unchanged.

## Downstream boundary

C4-013 does not generate executable Python transformations/oracles.
That remains C4-014.

It also does not perform the later full static-validation stage of C4-015;
C4-013 performs serialization/schema validation sufficient to ensure the generated
specification is well-formed for downstream code generation.

## Research interpretation

All generated specs are software-validation CandidateMR fixtures.
The generated count must not be reported as expert-valid MR yield or clinical compiler performance.
