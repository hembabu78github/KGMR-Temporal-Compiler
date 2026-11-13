# C4-016 — Determinism, Reproducibility, and Version Tracking

## Objective

C4-016 is the final individual engineering acceptance stage before the consolidated
Chapter 4 compiler release-candidate run.

Its acceptance criterion is:

> the same frozen upstream artifacts, configuration, and compiler versions must regenerate
> identical semantic CandidateMR artifacts, stable candidate identifiers, identical generated
> Python, and identical static-validation/admission outcomes.

## Two independent replays

The C4-016 runner reconstructs the C4-013 through C4-015 downstream artifacts twice in
separate working directories.

Each replay starts from the frozen C4-008 through C4-012 inputs already carried by the package.

For every candidate it regenerates:

- CandidateMR JSON semantics;
- YAML and semantic round-trip;
- CandidateMR ID;
- canonical semantic fingerprint;
- generated Python module;
- generated Python SHA-256;
- C4-015 static-validation result;
- execution-admission status.

The two replay directories are deleted after comparison so they cannot accidentally become
new authoritative artifacts.

## Reproducibility signature

C4-016 creates a deterministic release core containing:

- candidate IDs;
- candidate semantic fingerprints;
- operator IDs/versions;
- R families;
- generated Python hashes;
- static validation status;
- execution-admission status;
- expert-validation status;
- complete pinned version inventory.

A SHA-256 over the canonical release core is the C4-016 reproducibility signature.

## Environment metadata is deliberately excluded

Python/platform observations are recorded separately from the release core.

The following do not contribute to CandidateMR or release identity:

- wall-clock time;
- hostname;
- PID;
- filesystem path;
- OS label;
- expert-review lifecycle status.

This allows reproducibility to be assessed semantically across environments rather than
mistaking incidental machine metadata for research semantics.

## Version-sensitive identity

Version-bearing semantic compiler metadata remains inside candidate identity.

Controlled tests demonstrate that changes to:

- `compiler_config_id`;
- `operator_library_version`

change the CandidateMR identifier.

By contrast, changing `mr_expert_validation_status` does not change the CandidateMR identifier,
because expert review is a lifecycle state applied to the same candidate artifact.

## Cross-cycle researcher comparison

The replay is compared against the exact artifacts returned by the researcher:

- C4-013 candidate IDs and semantic fingerprints;
- C4-014 generated Python SHA-256 values;
- C4-015 static-validation status;
- C4-015 execution-admission status;
- C4-015 expert-validation status.

This verifies that the downstream artifact chain reproduced across the researcher's Windows
environment and the compiler package's deterministic replay.

## Version inventory

The release inventory records:

- CandidateMR representation;
- ClinicalPropositionIR version;
- candidate compiler version;
- operator-library version;
- KG release;
- ontology release;
- SHACL release;
- inference profile;
- closure policy;
- SREW;
- compiler-config ID;
- C4-014 runtime version;
- C4-015 validation version;
- C4-016 reproducibility version;
- C4-013 schema implementation.

## Research boundary

C4-016 establishes software reproducibility of the fixture compiler chain.

It does not establish:

- clinical validity;
- nephrologist acceptance;
- real KG compiler yield;
- real CDS robustness;
- novelty versus baselines.

Those belong to the subsequent evaluation stage.
