from .component_models import (
    ComponentGenerationInput, GeneratedPrecondition,
    PREDICATE_TYPE_ORDER, K3_VALUES
)

def _atom_sort_key(atom):
    return (
        PREDICATE_TYPE_ORDER.get(atom.predicate_type, 999),
        atom.predicate_type,
        atom.predicate_id,
    )

def generate_preconditions(inp: ComponentGenerationInput) -> GeneratedPrecondition:
    reasons = []
    if not inp.condition_atoms:
        return GeneratedPrecondition(
            "INVALID", None, 0, ["NO_PRECONDITION_ATOMS"]
        )

    seen_ids = set()
    ordered = []
    for atom in sorted(inp.condition_atoms, key=_atom_sort_key):
        if atom.predicate_id in seen_ids:
            reasons.append(f"DUPLICATE_PREDICATE_ID:{atom.predicate_id}")
            continue
        seen_ids.add(atom.predicate_id)

        if atom.predicate_type not in PREDICATE_TYPE_ORDER:
            reasons.append(f"UNSUPPORTED_PREDICATE_TYPE:{atom.predicate_type}")
        if not atom.evaluator_id:
            reasons.append(f"MISSING_EVALUATOR:{atom.predicate_id}")
        if not atom.source_refs:
            reasons.append(f"MISSING_SOURCE_REF:{atom.predicate_id}")
        if atom.missing_evidence_result != "INDETERMINATE":
            reasons.append(f"INVALID_MISSING_EVIDENCE_POLICY:{atom.predicate_id}")
        if atom.missing_evidence_result not in K3_VALUES:
            reasons.append(f"INVALID_K3_VALUE:{atom.predicate_id}")
        ordered.append(atom.to_dict())

    if reasons:
        return GeneratedPrecondition("INVALID", None, len(ordered), reasons)

    # Single atom is emitted directly; multiple atoms are canonical ALL.
    expr = ordered[0] if len(ordered) == 1 else {"op": "ALL", "children": ordered}
    return GeneratedPrecondition("GENERATED", expr, len(ordered), [])
