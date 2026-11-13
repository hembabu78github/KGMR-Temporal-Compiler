# C4-007 — Formal Six-Component Candidate MR Representation

## 1. Scope

This artifact formalizes the Chapter 4 candidate metamorphic-relation representation:

\[
MR = \langle C,T,R,I,E,P\rangle
\]

where:

- **C** — preconditions;
- **T** — transformation;
- **R** — expected output relation;
- **I** — invariants;
- **E** — exceptions;
- **P** — provenance.

The representation is a Chapter-4 compiler artifact. It does not alter the Chapter-3 CKD-TKG ontology.

Every emitted object remains a **candidate MR** until independent expert validation and adjudication are complete.

## 2. Semantic domains

Let:

- \(X\) be the space of admissible source clinical-data instances supplied to a target CDS;
- \(Y\) be the target CDS output space;
- \(\mathbb{K}_3 = \{\mathrm{TRUE},\mathrm{FALSE},\mathrm{INDETERMINATE}\}\) be the frozen Strong-Kleene clinical truth domain;
- \(\Omega_{R1}\) be the frozen 11-operator transformation library.

For a target CDS \(S:X\rightarrow Y\), a candidate MR \(m\) is evaluated only when its structural contract is valid and its applicability is not blocked by a higher-precedence exception.

The source instance is denoted \(x\). The deterministic transformed follow-up instance is:

\[
x' = T(x)
\]

The corresponding target-CDS outputs are:

\[
y = S(x), \qquad y' = S(x')
\]

The candidate MR tests whether \(R(y,y')\) is satisfied, subject to preconditions \(C\), invariants \(I\), exceptions \(E\), and provenance contract \(P\).

This is not a claim that \(T\) is "semantics-preserving". Any preservation claim must be represented explicitly by \(I\) and/or \(R\) and later validated empirically.

## 3. Component C — Preconditions

### 3.1 Syntax

`C` is a typed Boolean/K3 expression tree:

```text
ConditionExpression :=
    Atom
  | ALL(ConditionExpression+)
  | ANY(ConditionExpression+)
  | NOT(ConditionExpression)

Atom :=
    ClinicalPredicate
  | DataAvailabilityPredicate
  | TemporalPredicate
  | ApplicabilityPredicate
  | TerminologyPredicate
```

Each atom carries:

- `predicate_id`
- `predicate_type`
- `arguments`
- `evaluator_id`
- `source_refs`
- optional temporal specification
- missing-evidence policy fixed to `INDETERMINATE`

### 3.2 Semantics

\[
C(x)\in\mathbb{K}_3
\]

Composition follows Strong Kleene K3. Absence of required clinical evidence never becomes FALSE solely by absence.

- `TRUE` — candidate MR is conditionally applicable, subject to E and admission status.
- `FALSE` — candidate MR is not applicable to this source instance.
- `INDETERMINATE` — applicability cannot be safely resolved from admissible evidence.

### 3.3 Computability requirement

Every atom must map to a deterministic evaluator over explicit data bindings. Free-text interpretation at runtime is prohibited.

## 4. Component T — Transformation

### 4.1 Syntax

R1.0 uses exactly one declared operator invocation:

```text
T = OperatorInvocation(
    operator_id,
    operator_version,
    bound_parameters,
    read_set,
    touch_set,
    forbidden_touch_set
)
```

`operator_id` must be one member of the frozen bounded library:

1. SHIFT_TIME
2. RESAMPLE_TRAJECTORY
3. DELAY_RESULT_ENTRY
4. SWAP_EQUIVALENT_ORDER
5. REMOVE_REDUNDANT_OBSERVATION
6. MASK_REQUIRED_OBSERVATION
7. INCREASE_SLOPE
8. DECREASE_SLOPE
9. INSERT_TRANSIENT_AKI
10. CONVERT_UNIT
11. PRESERVE_CLINICAL_STATE

### 4.2 Semantics

For admissible \(x\), \(T\) deterministically constructs a derived follow-up case \(x'\). It does not mutate the source case.

R1.0 prohibits unrestricted transformation synthesis and arbitrary multi-operator composition.

### 4.3 Computability requirement

All required parameters must be bound from approved evidence sources:

- KG evidence;
- source evidence;
- versioned compiler configuration.

Every parameter must retain source provenance.

## 5. Component R — Expected output relation

### 5.1 Syntax

`R` is a tagged relation specification.

Supported R1.0 relation families:

- `EQUALITY_WITHIN_TOLERANCE`
- `MONOTONIC_INCREASE`
- `MONOTONIC_DECREASE`
- `ORDINAL_NONDECREASE`
- `ORDINAL_NONINCREASE`
- `BOUNDED_CHANGE`
- `DECISION_LEVEL`

`ABSTAIN` is **not** an R relation family. It is a system/control action that may appear as an observed or allowed decision-level outcome where appropriate.

### 5.2 Semantics

For scalar numeric output:

**Equality within tolerance**
\[
|y'-y|\leq \epsilon
\]
or another explicitly declared absolute/relative/mixed tolerance comparator.

**Monotonic increase**
\[
y' \geq y
\]

**Monotonic decrease**
\[
y' \leq y
\]

**Ordinal non-decrease**
\[
rank(y') \geq rank(y)
\]

**Ordinal non-increase**
\[
rank(y') \leq rank(y)
\]

**Bounded change**
\[
L \leq \Delta(y,y') \leq U
\]
where `delta_definition`, `L`, and `U` are explicit.

**Decision-level relation**
A declared comparator over typed decision objects or actions, such as equality, allowed-set membership, or a declared partial/ordinal ordering. The comparator must be named and versioned; no lexical comparison is allowed.

### 5.3 Computability requirement

The output adapter, comparator, ordering (if any), tolerance/bounds, and missing-output handling must all be explicit.

## 6. Component I — Invariants

### 6.1 Syntax

`I` is a finite ordered set of invariant clauses:

```text
InvariantClause(
    invariant_id,
    invariant_type,
    source_selector,
    followup_selector,
    comparator,
    parameters,
    source_refs
)
```

### 6.2 Semantics

Each invariant asserts a property that must remain unchanged or within a declared equivalence class between \(x\) and \(x'\).

\[
I(x,x') = \bigwedge_{j=1}^{n} I_j(x,x')
\]

Examples include:

- subject identity unchanged;
- clinical value unchanged under unit conversion after canonicalization;
- effective/specimen time unchanged under result-entry delay;
- state-defining predicates remain in the same state for PRESERVE_CLINICAL_STATE;
- protected trajectory anchors remain unchanged during resampling.

### 6.3 Computability requirement

No invariant may be inferred from silence. Every invariant must have explicit selectors, comparator, evidence basis, and later a deterministic evaluator. Automatic inference from unaffected KG neighborhoods is deferred to C4-009.

## 7. Component E — Exceptions

### 7.1 Syntax

`E` is an ordered finite set of exception clauses:

```text
ExceptionClause(
    exception_ref,
    exception_type,
    condition,
    precedence_tier,
    evidence_refs,
    resolution_status
)
```

`precedence_tier` is drawn from the frozen Chapter-3 P0-P8 precedence model.

### 7.2 Semantics

Exceptions restrict or qualify application of the candidate MR. A matching exception is evaluated before the expected output relation is interpreted as a violation.

Chapter-3 precedence controls remain authoritative. An unresolved same-tier conflict does not select an arbitrary winner; it yields safe ABSTAIN/INDETERMINATE behavior and prevents conflict-gate completion.

### 7.3 Computability requirement

Every exception condition must be computable from admissible data or explicitly produce INDETERMINATE. Exception assembly and precedence execution are deferred to C4-010.

## 8. Component P — Provenance

### 8.1 Syntax

`P` is a structured provenance bundle containing at least:

- source knowledge-item IDs;
- precise source locator/reference IDs;
- matched graph/path IDs;
- CKD-TKG release;
- ontology release/hash;
- SHACL release/hash;
- rule/proposition extraction version;
- compiler version;
- operator-library version;
- operator-selection fingerprint;
- bound-parameter provenance;
- review/adjudication references available at compilation time;
- active inference/closure policy;
- SREW version;
- compiler configuration identity;
- generation status;
- later MR-level expert validation references (kept separate from source-rule review).

### 8.2 Semantics

`P` explains why the candidate exists and permits reconstruction of the exact compilation context. It is not clinical evidence itself.

### 8.3 Computability requirement

Mandatory provenance fields are locally closed for the versioned compilation contract. Missing required provenance makes the candidate non-admissible; it is not interpreted as a clinical FALSE.

## 9. Overall candidate-MR validity

A six-tuple is **structurally well-formed** when all six components satisfy their schema.

A six-tuple is **computable** when all component evaluators and parameter bindings needed for execution are available.

A six-tuple is **admissible for candidate-MR emission** only when the applicable compilation-gate policy permits admission.

A six-tuple is **not a clinically validated MR** until independent expert review/adjudication is complete.

## 10. Runtime state separation

The following channels must remain distinct:

1. structural status: `CONFORMANT | INVALID_INPUT`;
2. precondition truth: `TRUE | FALSE | INDETERMINATE`;
3. exception/conflict control: applicable / blocked / unresolved;
4. MR oracle truth: `TRUE | FALSE | INDETERMINATE`;
5. system action: may include `ABSTAIN`;
6. clinical-validation status: `UNREVIEWED | ACCEPTED | REJECTED | ADJUDICATED`.

A SHACL/schema failure is never directly a metamorphic violation.

## 11. Candidate identity and deterministic fingerprint

A stable `candidate_mr_id` is derived from a canonical JSON projection containing semantic fields only.

The fingerprint MUST include:

- C, T, R, I, E semantic content;
- stable provenance/release identifiers from P;
- compiler/operator-library versions;
- operator-selection fingerprint.

The fingerprint MUST NOT include nondeterministic operational metadata such as wall-clock generation timestamps, filesystem paths, hostnames, or process IDs.

This allows repeated compilation of identical semantic inputs to produce the same identity.

## 12. C4-006 → C4-007 mapping

For each fully parameterised operator returned by C4-006:

```text
ClinicalPropositionIR
        +
OperatorSelectionResult[operator_i]
        |
        v
CandidateMR skeleton
  C <- proposition antecedents/applicability
  T <- selected operator + bound parameters
  R <- permitted relation family placeholder/typed candidate
  I <- invariant slots/evidence links
  E <- Chapter-3 exception references
  P <- source + graph + compiler + selection provenance
```

C4-007 defines this representation only. Generation of executable C, T and R functions is C4-008.

## 13. Validation rules

A candidate MR must be rejected as structurally invalid when:

- any of C/T/R/I/E/P is missing;
- T contains zero or more than one operator in R1.0;
- T references an operator outside the frozen library;
- T contains an unprovenanced required parameter;
- R uses an unsupported relation family;
- R uses `ABSTAIN` as a relation family;
- an ordinal R lacks a named ordering;
- equality lacks a declared tolerance policy;
- bounded change lacks bounds and delta definition;
- any invariant lacks source/follow-up selectors;
- an exception lacks a Chapter-3 exception reference or precedence tier;
- required provenance/version fields are missing;
- the candidate status is labelled "validated" before independent MR-level expert validation.

## 14. C4-007 closure criterion

C4-007 is design-complete when:

1. the six components have fixed syntax;
2. semantics are explicitly separated from structural conformance;
3. every component has computability requirements;
4. the JSON/YAML representation is schema-validatable;
5. C4-006 selected operators map deterministically into T;
6. K3, ABSTAIN, exception precedence and provenance remain consistent with Chapter 3;
7. no C4-008 executable-generation logic is silently introduced.
