# Source interface notes

C4-006 is designed against the frozen Chapter-3 controls:

- CKD-TKG R1.0 ontology
- SHACL constraint layer
- 8 frozen compilation gates
- K3 clinical truth: TRUE / FALSE / INDETERMINATE
- ABSTAIN as a system action, not clinical truth or output relation
- SREW-R1.0 with sole runtime symmetric-normalisation member `ckd:overlapsEvent`
- reviewed source population with 8 reviewed knowledge items
- Chapter-3 decision to defer `ExecutableClinicalRule` population until Chapter 4

The actual RDF-to-`ClinicalPropositionIR` extraction remains a C4-003 implementation interface and is deliberately
not replaced here with free-text parsing. This prevents C4-006 from silently inferring antecedents, parameters, or
clinical directions from `rdfs:comment` strings.
