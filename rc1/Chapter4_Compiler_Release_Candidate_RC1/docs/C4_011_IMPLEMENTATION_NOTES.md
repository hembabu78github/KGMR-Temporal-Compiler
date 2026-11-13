# C4-011 — Temporal Satisfiability Checking

## Authoritative source

C4-011 implements the design-closed C3-009 temporal grammar:

- half-open `[start,end)` intervals;
- explicit-offset UTC normalization with lexical preservation upstream;
- uncertainty intervals;
- `TRUE / FALSE / INDETERMINATE`;
- calendar-anchored month/year arithmetic;
- local Allen-style interval relations;
- duration/window operators;
- clinical versus availability time separation;
- no broad property-chain inference;
- `INDETERMINATE` never coerced to `FALSE`.

## What “temporal satisfiability” means here

C4-011 performs two distinct checks.

### 1. Internal temporal-contract consistency

The compiler rejects a candidate when its declared temporal constraints are internally contradictory.

Examples:

- the same ordered pair requires both `AT_LEAST P90D` and `AT_MOST P14D`;
- the same pair is simultaneously required to be `before` and `after`.

These are static compiler contradictions, not patient-level clinical negatives.

### 2. K3 evaluation under temporal precision

Given admissible temporal evidence, every temporal condition evaluates to:

- `TRUE` if satisfied for every instant allowed by the recorded precision;
- `FALSE` if unsatisfied for every allowed instant;
- `INDETERMINATE` if truth varies across allowed instants or a required time is missing.

The conjunction of temporal conditions uses Strong-Kleene logic.

## Half-open boundaries

Intervals are `[start,end)`.

Therefore:

- `[A,B)` and `[B,C)` `meet`;
- they do not overlap;
- a shared boundary instant is not double-counted.

## Calendar arithmetic

`PnM` and `PnY` are calendar-anchored rather than converted to fixed days.

For example:

`2024-02-29 + P1Y = 2025-02-28`

under the deterministic end-of-month clipping rule used by this implementation.

This avoids leap-year drift in the two-year D1 analysis horizon.

## Time domains

C4-011 keeps three channels separate:

- clinical time — specimen/effective ordering;
- availability time — issued time;
- provenance time — recorded/imported time.

A clinical constraint cannot silently substitute an issued timestamp.
A domain mismatch produces `INDETERMINATE`/invalid temporal evidence behavior, never a fabricated clinical FALSE.

## `sameClinicalTime`

For equal available precision and identical uncertainty ranges, `sameClinicalTime` can evaluate TRUE.

Overlapping or mixed-precision ranges that cannot establish equality deterministically evaluate INDETERMINATE.

This deliberately avoids transitive inference across mixed temporal precision.

## Open intervals

End-dependent relations over an open interval evaluate INDETERMINATE unless the relation can be decided without the missing end.

## Upstream safety

C4-011 never overrides an upstream C4-010 ABSTAIN, licensing block, pending temporal exception, or unresolved conflict.

A temporally satisfiable candidate can therefore still have `system_action=ABSTAIN` due to an earlier gate.

## Output for C4-012

Each result exposes a normalized clinical temporal scope hull:

- earliest clinical time;
- latest clinical time;
- half-open boundary convention.

C4-012 may use these normalized scopes when testing temporal overlap for conflict detection.

## Research boundary

Fixture counts are software-validation results only.
They must not be reported as clinical temporal robustness, candidate-MR validity, or real conflict frequency.
