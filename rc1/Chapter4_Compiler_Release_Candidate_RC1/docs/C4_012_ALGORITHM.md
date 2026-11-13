# C4-012 Deterministic Conflict and Relation-Typing Algorithm

Input:
    C4-008 component bundle
    C4-009 invariants
    C4-010 exception/precedence result
    C4-011 temporal result
    explicit candidate-scope registry
    optional typed conflict evidence

A. Final relation typing
1. Validate R family against the selected operator.
2. Validate comparator/tolerance/order/bound parameters.
3. Normalize R to a formal constraint signature.
4. Emit stable relation_signature.

B. Candidate pair conflict detection
For each canonical candidate pair:
1. require same target/output;
2. require same explicit comparison_context_id;
3. compute applicability overlap;
4. compute temporal overlap from C4-011 half-open scope;
5. compute formal expectation-set compatibility;
6. create ExpectedRelationConflict only when:
      applicability == TRUE
      temporal overlap == TRUE
      expectation compatibility == FALSE

C. Unary temporal conflict detection
If C4-011 temporal truth is INDETERMINATE or temporal constraints are unsatisfiable:
    emit TemporalConflict record.

D. Other frozen conflict categories
Consume explicitly typed/versioned evidence records.
Never infer terminology, data, review, policy, or source-interpretation conflicts from silence.

E. Resolution
Allow a winner only from:
    explicit scope containment
    release-pinned non-superseded version
    source authority
    formal adjudication
Else:
    INDETERMINATE
    ABSTAIN
    ConflictResolved=Fail

F. Duplicate detection
Canonicalize C/T/R/I/E semantics and group identical signatures.

Output:
    final typed relations
    integrated conflict records
    duplicate records
    separate taxonomy-validation records
