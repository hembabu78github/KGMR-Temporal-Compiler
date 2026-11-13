# C4-010 Deterministic Exception/Precedence Algorithm

Input:
    candidate component c
    declared exception evidence E_raw
    precedence context q

1. Assemble only exception records explicitly linked to c.
2. Validate frozen exception type, scope, K3 condition, source provenance, and P-tier.
3. P0:
     enforce input integrity/legality;
     apply active DataQuality, MissingData, TerminologyMapping,
     LicensingRelease, and ReviewGate controls.
4. P1:
     evaluate applicability; excluded rule does not fire.
5. P2:
     confirm exception effects remain restricted to explicit linked scope.
6. P3:
     apply temporal/event K3 semantics and linked ClinicalEvent/Medication qualifiers.
7. P4:
     allow specificity only if explicit scope-containment evidence exists.
8. P5:
     use release-pinned non-superseded version within one lineage.
9. P6:
     record guideline strength/certainty only; never use it as an automatic tiebreak.
10. P7:
     apply a human adjudication only when an explicit adjudication record exists.
11. P8:
     if contradiction remains unresolved:
         semantic truth = INDETERMINATE
         system action = ABSTAIN
         ConflictResolved = Fail
         no winning candidate is fabricated.
12. Emit ordered precedence trace and deterministic semantic fingerprint.

Cross-candidate conflict discovery is deferred to C4-012.
