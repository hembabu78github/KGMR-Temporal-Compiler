# C4-009 — Invariant Inference from Unaffected KG Neighbourhoods

## Objective

C4-009 implements the Chapter 4 Section 4.2.12 operation:

> infer unaffected variables and clinical conditions from relevant KG neighbourhoods.

This is one of the compiler operations that must later be evaluated against the simple rule-to-template baseline.
The proposal treats its added value as an empirical question rather than an automatic novelty claim.

## Central safety rule: no inference from silence

The compiler **does not** classify a field as invariant merely because the transformation does not list it in its `touch_set`.

An invariant is emitted only when all of the following hold:

1. the candidate is reachable from an explicit compilation seed within a bounded, whitelisted neighbourhood;
2. a positive preservation edge exists (`supports_invariant`, `declares_preserved`, `protects_anchor`, or `defines_preserved_state`);
3. the positive edge is applicable to the selected operator;
4. the candidate selector is not directly touched by T;
5. no explicit whitelisted dependency path connects the candidate to a touched selector;
6. the candidate has a supported invariant type;
7. a deterministic comparator is named;
8. positive source provenance is retained.

This is consistent with Chapter 3's open-world discipline: absence of a graph assertion is not transformed into a preservation claim.

## Relevant-neighbourhood model

C4-009 consumes a bounded `InvariantNeighbourhood` extracted from the Chapter 3 KG interface:

- `seed_nodes`
- typed variable/state nodes with executable selectors
- positive preservation edges
- dependency edges
- source references
- release identity

Traversal is bounded and restricted to declared relations. It is not unrestricted ontology graph mining.

## Dependency blocking

Even if a candidate has explicit preservation support, the inference is rejected if the candidate explicitly depends on a selector modified by the transformation.

Example:

`derived.risk_context --depends_on--> trajectory.modifiable_observations`

For `INCREASE_SLOPE` or `DECREASE_SLOPE`, `trajectory.modifiable_observations` is touched. Therefore `derived.risk_context` is not inferred as an invariant.

## Important distinction

`forbidden_touch_set` is a transformation safety contract; it is not itself sufficient positive evidence for an invariant.

For example, `INSERT_TRANSIENT_AKI` forbids changing `formal_diagnosis.AKI`. C4-009 still does **not** infer that a formal AKI diagnosis is invariant unless the KG neighbourhood positively supports such a preservation claim. The supplied test intentionally demonstrates that no such invariant is created.

## Output

Each inference result contains:

- formal `InvariantClause` objects compatible with CandidateMR-R1.0 `I`;
- evidence paths;
- positive source references;
- rejected candidate records and reasons;
- a deterministic semantic fingerprint.

## Deferred work

C4-009 does not:

- assemble or prioritize exceptions (C4-010);
- solve temporal satisfiability (C4-011);
- detect duplicate/conflicting relations or finalize output typing (C4-012);
- perform static validation of the full candidate package (C4-013);
- generate or run executable Python transformations/oracles (C4-014);
- perform independent clinical validation.

All bundled counts are software-validation fixture results only.
