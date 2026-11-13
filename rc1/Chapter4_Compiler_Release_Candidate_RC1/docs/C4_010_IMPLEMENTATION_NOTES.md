# C4-010 — Exception Assembly and P0-P8 Precedence

## Authoritative Chapter-3 interface

C4-010 implements the final C3-013 exception vocabulary exactly:

1. ApplicabilityExclusion
2. DataQualityException
3. MissingDataException
4. TemporalPrecisionException
5. ClinicalEventException
6. MedicationContextException
7. TerminologyMappingException
8. LicensingReleaseException
9. ReviewGateException
10. ConflictException

The final P0-P8 sequence is also used exactly:

- P0 input integrity / legality
- P1 applicability
- P2 explicit linked exception
- P3 temporal/event semantics
- P4 specificity
- P5 release/version
- P6 guideline strength metadata only
- P7 human adjudication
- P8 unresolved safety

## Important correction of working terminology

Earlier Chapter-4 planning notes used a different working list of exception labels.
C4-010 does **not** preserve those obsolete names. The final Chapter-3 ontology and C3-013
closed design are authoritative.

This is an interface alignment, not a redesign of Chapter 3.

## Exception assembly

An exception is assembled into candidate-MR component E only if:

- its type is a frozen C3-013 type;
- it explicitly links to the current proposition;
- an operator restriction, when present, includes the current operator;
- it has an explicit scope reference;
- its condition/evaluator are named;
- it has source provenance;
- its precedence tier is valid.

The compiler never applies an exception globally to unrelated rules.

## Precedence execution

The resolver evaluates P0 through P8 in order and records every visited tier.

Key safety properties:

- invalid or release-prohibited evidence cannot support execution;
- out-of-scope rules do not fire;
- exception scope is explicit and local;
- temporal/event INDETERMINATE is never coerced to FALSE;
- specificity is used only when an explicit scope-containment reference exists;
- release-pinned non-superseded lineage is current;
- guideline strength is metadata only and never an automatic tiebreaker;
- unresolved clinically meaningful contradictions require adjudication;
- unresolved contradiction produces ABSTAIN/INDETERMINATE and ConflictResolved fails.

## Boundary with C4-012

C4-010 **does not discover cross-candidate conflicts**.

`ConflictException` and the `unresolved_conflict` context are inputs to the precedence primitive.
C4-012 remains responsible for grouping candidates by common target/output, testing
applicability/temporal overlap, detecting incompatible expectations, classifying the ten
conflict types, and invoking the C4-010 precedence primitive.

This prevents exception assembly from being confused with global conflict detection.

## Compile-time versus runtime

Exception evidence records carry `phase=compile_time|runtime`.

Static source/mapping/release/review exceptions can be evaluated at compile time.
Subject-dependent missingness, event, and temporal-precision exceptions can be evaluated
at runtime. The representation and precedence trace are identical in both cases.

## Interpretation of fixture results

The fixtures exercise software behavior only. Their number of exceptions, precedence outcomes,
ABSTAIN cases, or qualified cases must not be reported as clinical prevalence, real compiler
yield, or observed CKD rule-conflict frequency.
