# C4-015 — Static Validation of the Complete CandidateMR Package

## Purpose

C4-015 performs a fail-closed static validation pass over the complete software CandidateMR bundle:

- C4-013 JSON specification;
- deterministic YAML counterpart;
- C4-014 generated Python module;
- upstream semantic fingerprint;
- generated-source SHA-256;
- execution-control gate;
- end-to-end gate result;
- shared runtime dependencies.

No target CDS is executed by the C4-015 validator.

## Static validation is not clinical validation

A C4-015 `STATIC_VALIDATION_PASS` means only that the candidate package is structurally,
semantically, provenance-wise, and code-wise self-consistent under the frozen compiler contracts.

It does **not** change:

`candidate_status = COMPILED_CANDIDATE`

and it does **not** change:

`P.mr_expert_validation_status = UNREVIEWED`.

Static validation is recorded in a separate immutable registry.

## Static pass is also not execution admission

A candidate can satisfy every static check while remaining control-blocked.

C4-015 therefore distinguishes:

- `STATICALLY_VALID_EXECUTION_ADMISSIBLE`
- `STATICALLY_VALID_BUT_CONTROL_BLOCKED`
- `STATIC_VALIDATION_FAILED`

An upstream `ABSTAIN` is never overridden by static validation.

## Per-candidate checks

Each candidate is checked for:

1. CandidateMR semantic conformance;
2. representation version;
3. lifecycle status;
4. expert status remains UNREVIEWED;
5. semantic fingerprint chain;
6. recomputed candidate ID;
7. JSON/YAML semantic equivalence using the restricted deterministic C4-013 YAML grammar;
8. frozen operator membership;
9. parameter provenance;
10. touch/forbidden-touch separation;
11. invariant direct-contact safety;
12. formal R-family membership;
13. `ABSTAIN` exclusion from R;
14. exception type/tier/provenance conformance;
15. provenance closure;
16. exact C4-014 generated-module SHA-256;
17. Python compilation;
18. AST import/name safety;
19. embedded generated-module SPEC equality;
20. embedded CONTROL equality;
21. derived gate consistency;
22. researcher end-to-end gate consistency;
23. no CDS call for blocked candidate, or exactly two for an admitted fixture;
24. researcher end-to-end test pass;
25. runtime dependency resolution.

The exact number of checks can vary slightly by gate branch, because a blocked candidate receives
the blocked-CDS check while an admitted candidate receives the two-CDS-call check.

## Static generated-code audit

Generated per-candidate modules may import only:

- `json`;
- `runtime.executable_runtime` functions.

The static AST audit rejects unexpected imports and code names such as:

- `os`
- `subprocess`
- `socket`
- `exec`
- `eval`
- `open`
- dynamic import/process/network primitives.

The shared runtime is independently compiled and audited against a separate allow-list.

## Immutable code/spec chain

C4-015 verifies:

`CandidateMR semantic fingerprint`
→ `researcher C4-013 manifest`
→ `generated Python module`
→ `researcher C4-014 generated source SHA-256`
→ `embedded SPEC`
→ `embedded CONTROL`
→ `researcher C4-014 end-to-end gate result`.

A mismatch at any point fails static validation.

## Runtime dependency closure

Static validation confirms that any named:

- unit conversion;
- ordinal ordering;
- decision comparator

needed by the generated candidate exists in the pinned C4-014 runtime configuration.

The validator does not invent missing dependencies.

## Negative controls

The unit suite deliberately verifies rejection of:

- candidate-ID tampering;
- semantic-fingerprint tampering;
- unknown operators;
- unprovenanced parameters;
- touch/forbidden overlap;
- invariant contact with transformed selectors;
- ABSTAIN used as an R family;
- leaked fixture truth;
- false expert acceptance;
- generated-code hash tampering;
- malicious imports;
- embedded-spec mismatch;
- gate mismatch;
- blocked candidate invoking the CDS;
- admitted fixture not invoking source/follow-up CDS;
- YAML tampering;
- missing unit/ordinal/decision runtime dependencies.

## Research boundary

All static-pass counts are software-validation fixture results.
They are not expert-valid MR yield, clinical correctness, or real CDS robustness results.
