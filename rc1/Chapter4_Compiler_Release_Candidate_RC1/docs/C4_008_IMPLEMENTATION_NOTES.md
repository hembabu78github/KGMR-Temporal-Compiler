# C4-008 — Precondition, Transformation and Output-Relation Generation

## Scope

C4-008 consumes:

- a structured Chapter-4 proposition/component context;
- the C4-006 `OperatorSelectionResult`;
- the frozen 11-operator transformation-contract registry.

It emits one deterministic intermediate component bundle per fully parameterised selected operator:

- `C` — a typed, canonically ordered K3 precondition expression;
- `T` — a single bounded operator invocation with provenance-linked parameters and explicit read/touch/forbidden-touch sets;
- `R` — an evidence-backed output-relation draft.

## Boundary with C4-012

C4-008 **does not claim to perform final output-relation typing**.

If exactly one highest-priority evidence-backed relation family is compatible with the operator, it creates a typed draft.
If evidence is ambiguous or insufficient, it emits `RELATION_TYPING_PENDING`.

C4-012 remains authoritative for:

- final output-relation typing;
- duplicate detection;
- incompatible relation detection;
- cross-candidate conflict analysis.

This separation prevents C4-008 from silently choosing among equally supported clinical relations.

## Relation support

The generator supports all seven approved R families:

- equality within tolerance;
- monotonic increase;
- monotonic decrease;
- ordinal non-decrease;
- ordinal non-increase;
- bounded change;
- decision-level.

`ABSTAIN` is not a relation family.

## Safety boundaries

- no free-text runtime interpretation;
- no arbitrary operator composition;
- no transformation execution at C4-008;
- no invariant inference;
- no exception precedence execution;
- no temporal satisfiability solver;
- no clinical-validity claim.

Python transformation and oracle execution remains C4-014.

## C4-006 compatibility-token normalization

`PRESERVE_OUTPUT` may appear in C4-006 as an internal compatibility token. It is not a final Chapter-4 R family. C4-008 converts it only through explicit relation evidence, normally to `EQUALITY_WITHIN_TOLERANCE` or a typed `DECISION_LEVEL` preservation relation. No preservation semantics are assumed without evidence.
