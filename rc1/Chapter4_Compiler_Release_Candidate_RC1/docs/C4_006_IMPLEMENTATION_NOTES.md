# C4-006 implementation notes

## Scientific boundary

C4-006 answers a narrow engineering question: given a structured and provenance-linked
`ClinicalPropositionIR`, which members of the declared operator library are compatible,
and can all required parameters be bound from allowed evidence sources?

It does not answer whether the resulting candidate MR is clinically valid.

## Deterministic selection

The operator registry has an explicit integer order. The engine iterates only in this order.
No random seed, ranking model, LLM call, embedding similarity, dictionary order, or heuristic
tie-break is used.

## Parameter provenance

A parameter can be bound only from:

- `kg`
- `source_evidence`
- `compiler_config`

Every bound parameter records `source_kind` and `source_ref`.
If a required parameter cannot be bound, the operator can remain semantically compatible
but is not emitted as a fully parameterised selection.

## Gate semantics

The selection engine separates:

1. **semantic prerequisites for selection**, and
2. **final MR admission**.

This implements the approved Chapter-4 interpretation of the frozen Chapter-3 gate system.
`ConflictResolved`, `LicensingAllowed`, and `ReleaseIntegrity` can remain pending while
compatibility is assessed; they still prevent final admission.

## K3

For temporal operators, `INDETERMINATE` does not become `FALSE`. The operator is not selected
for an invariant claim when the required temporal relation is indeterminate.

## R1.0 operator composition

The engine emits all compatible operators, but each future candidate MR uses one operator.
It does not compose multiple transformation operators into one candidate MR in R1.0.
