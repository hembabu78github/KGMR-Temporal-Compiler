# C4-011 Deterministic Temporal Satisfiability Algorithm

Input:
    candidate component c
    C4-010 precedence result p
    normalized temporal case q

1. Validate temporal entities:
     - declared time domain
     - timezone-aware normalized values
     - uncertainty lower <= upper
     - half-open interval start < end when end is known

2. Detect static contradictions among declared constraints:
     - incompatible relation pair on the same ordered variables
     - fixed-day minimum duration greater than maximum duration

3. Evaluate each constraint with C3-009 K3 semantics:
     TRUE          holds for every allowed temporal realization
     FALSE         holds for no allowed temporal realization
     INDETERMINATE varies by precision or required time is missing

4. Combine conditions using Strong-Kleene conjunction.

5. Assign:
     TRUE  -> TEMPORALLY_SATISFIABLE
     FALSE -> TEMPORALLY_UNSATISFIABLE
     INDETERMINATE -> TEMPORALLY_INDETERMINATE

6. Preserve upstream safety:
     if C4-010 system_action == ABSTAIN:
          final system action remains ABSTAIN

7. Emit:
     per-constraint trace
     static contradiction ledger
     normalized clinical temporal-scope hull
     deterministic temporal fingerprint

No `INDETERMINATE` result is coerced to `FALSE`.
