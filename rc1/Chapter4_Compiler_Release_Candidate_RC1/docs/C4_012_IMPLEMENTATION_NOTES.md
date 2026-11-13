# C4-012 — Conflict Detection and Final Output-Relation Typing

## Scope

C4-012 closes Sections 4.2.16-4.2.17:

1. final formal typing of the C4-008 output-relation draft;
2. conflict discovery under the frozen C3-013 scope definition;
3. duplicate detection;
4. generation of auditable ConflictResolutionRecord-compatible records.

It consumes the exact researcher-reproduced C4-008 through C4-011 outputs.

## Final output-relation typing

The seven formal families remain:

- EQUALITY_WITHIN_TOLERANCE
- MONOTONIC_INCREASE
- MONOTONIC_DECREASE
- ORDINAL_NONDECREASE
- ORDINAL_NONINCREASE
- BOUNDED_CHANGE
- DECISION_LEVEL

`ABSTAIN` is not an R type.

C4-012 normalizes each relation to an explicit semantic constraint where possible:

- absolute equality tolerance -> numeric delta interval;
- monotonic increase -> delta >= 0;
- monotonic decrease -> delta <= 0;
- ordinal non-decrease/non-increase -> rank-delta constraint under a named ordering;
- bounded change -> closed numeric interval under a named delta definition;
- decision-level -> named/versioned decision comparator;
- relative/mixed tolerances remain parametric until runtime output magnitude is known.

No relation is made “more specific” by lexical interpretation.

## Important logical correction: opposing non-strict relations are not automatically conflicts

The approved formal semantics define:

- MONOTONIC_INCREASE: y' >= y
- MONOTONIC_DECREASE: y' <= y
- ORDINAL_NONDECREASE: rank(y') >= rank(y)
- ORDINAL_NONINCREASE: rank(y') <= rank(y)

Therefore the opposing non-strict pairs have a non-empty intersection:

- numeric equality satisfies both monotonic relations;
- unchanged rank satisfies both ordinal relations.

C4-012 flags them as incompatible only when additional explicit semantics require strict change,
or when their formal feasible sets are otherwise disjoint.

This is not a change to Chapter 3. C3-013 requires **incompatible** expectations; C4-012 supplies
the formal compatibility test needed to decide whether incompatibility actually exists.

## Candidate-level comparison-context guard

Different transformations are not competing rules merely because they target the same CDS output.

For example:

- INCREASE_SLOPE + ORDINAL_NONDECREASE
- DECREASE_SLOPE + ORDINAL_NONINCREASE

are two different metamorphic tests. They are not automatically an ExpectedRelationConflict.

C4-012 compares expectations only when the candidate-scope registry declares the same
`comparison_context_id`, in addition to the frozen C3-013 conditions.

This prevents false-positive “conflicts” between intentionally different metamorphic transformations.

## C3-013 conjunctive conflict rule

ExpectedRelationConflict requires all of:

1. same target;
2. same output;
3. same declared comparison context;
4. overlapping applicability;
5. overlapping temporal scope;
6. provably incompatible formal expectation sets.

If any required overlap is FALSE, there is no conflict.
If incompatibility cannot be proven, C4-012 does not fabricate one.

## Applicability overlap

The current R1.0 compiler compares explicit sets for:

- care context;
- GFR categories;
- eligibility state.

Missing dimensions produce INDETERMINATE rather than presumed overlap.

## Temporal overlap

C4-012 uses the normalized C4-011 clinical-time hull and half-open boundary convention.
An upstream temporally INDETERMINATE candidate generates a TemporalConflict record rather
than being coerced to FALSE.

## Ten frozen conflict types

The implementation preserves all ten C3-013 types:

1. ExpectedRelationConflict
2. ApplicabilityConflict
3. ExceptionConflict
4. VersionConflict
5. TerminologyConflict
6. DataConflict
7. TemporalConflict
8. DecisionPolicyConflict
9. SourceInterpretationConflict
10. ReviewConflict

Not all conflict types can or should be inferred from C/T/R alone. For example:

- TerminologyConflict requires mapping evidence;
- DataConflict requires selected source-observation evidence;
- ReviewConflict requires reviewer records;
- SourceInterpretationConflict requires source-versus-interpretation provenance.

Accordingly, C4-012 has two input paths:

- deterministic pairwise candidate analysis for relation/applicability/time;
- explicitly typed evidence records for provenance-, mapping-, review-, policy-, and data-dependent conflicts.

The same ConflictResolutionRecord model is used for both.

## ConflictResolutionRecord

Every conflict or abstention record contains:

- stable conflict ID;
- frozen conflict type;
- involved candidate keys;
- common target/output when defined;
- applicability and temporal-overlap status;
- expectation compatibility;
- detection phase;
- resolution status/type;
- legitimate winner only when one is explicitly justified;
- semantic truth;
- system action;
- ConflictResolved gate result;
- mandatory rationale;
- provenance/source references;
- adjudication reference when used;
- record-model version.

## Resolution safety

Automatic resolution is restricted to frozen legitimate mechanisms:

- release-pinned non-superseded winner;
- explicit scope-containment evidence;
- source authority over author interpretation;
- formal adjudication record.

Guideline strength is never an automatic winner.
Lexical specificity is never used.

Unresolved conflict -> INDETERMINATE + ABSTAIN + ConflictResolved=Fail.

## Circularity guard with C4-010

C4-010 included a deliberately seeded ConflictException fixture to test P7/P8 precedence behavior.
C4-012 does not treat that seed as proof of an actual ExpectedRelationConflict.

Conflict discovery is independent: it must reproduce the full C3-013 scope predicate.
This prevents a test-control signal from becoming self-validating evidence of a real conflict.

## Duplicate detection

Duplicate identity uses a canonical semantic projection over:

- target/output/comparison context;
- C;
- T;
- final typed R;
- invariant semantics;
- exception semantics.

Candidate IDs and provenance-record IDs do not by themselves make two otherwise identical tests distinct.

## Evaluation boundary

The integrated 12-candidate set and ten taxonomy cases are software-validation fixtures.

The package deliberately reports separately:

- integrated conflict detection over the existing software fixtures;
- ten-type taxonomy-handler validation.

Neither number is a clinical conflict-prevalence result. Real Chapter 4 compiler conflict frequency
requires the final evidence-linked candidate population.
