# C4-013 Narrow Schema Correction Note

The approved C4-007 formal representation remains:

`MR = <C,T,R,I,E,P>`

No semantic component, relation family, K3 rule, operator rule, provenance obligation,
or validation status has been changed.

A narrow implementation inconsistency was discovered when C4-010 outputs were first
assembled into the C4-007 JSON Schema:

- `C.conditionAtom.predicate_type` correctly allows only:
  `CLINICAL`, `DATA_AVAILABILITY`, `TEMPORAL`, `APPLICABILITY`, `TERMINOLOGY`.
- `E.condition` was referencing that same condition-atom definition.
- C4-010 exception conditions are correctly typed as `EXCEPTION`.

Therefore an exception clause could not validate against the literal C4-007 schema even
though the formal prose explicitly defined `ExceptionClause(condition, ...)`.

C4-013 fixes this only by introducing a dedicated `exceptionCondition` schema with:

`predicate_type = EXCEPTION`

and pointing `E.condition` to it.

The top-level representation version remains `CandidateMR-R1.0`.
The corrected schema implementation is identified as:

`CandidateMR-R1.0 / C4-013 schema patch 1`.

This is a schema implementation correction, not a redesign of Chapter 3 or the approved
six-component MR formalism.
