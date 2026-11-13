from .component_models import GeneratedTransformation

def generate_transformation(operator_decision, transformation_contracts):
    op = operator_decision["operator_id"]
    reasons = []

    if not operator_decision.get("compatible"):
        reasons.append("C4_006_OPERATOR_NOT_COMPATIBLE")
    if not operator_decision.get("parameterized"):
        reasons.append("C4_006_OPERATOR_NOT_PARAMETERIZED")

    contract = transformation_contracts.get(op)
    if contract is None:
        reasons.append("MISSING_TRANSFORMATION_CONTRACT")

    for p in operator_decision.get("bound_parameters", []):
        if p.get("source_kind") not in {"kg","source_evidence","compiler_config"}:
            reasons.append(f"UNSUPPORTED_PARAMETER_SOURCE:{p.get('name')}")
        if not p.get("source_ref"):
            reasons.append(f"MISSING_PARAMETER_PROVENANCE:{p.get('name')}")

    if reasons:
        return GeneratedTransformation(
            "INVALID", op, "OperatorLibrary-R1.0",
            list(operator_decision.get("bound_parameters", [])),
            [] if contract is None else list(contract["read_set"]),
            [] if contract is None else list(contract["touch_set"]),
            [] if contract is None else list(contract["forbidden_touch_set"]),
            reasons
        )

    return GeneratedTransformation(
        "GENERATED", op, "OperatorLibrary-R1.0",
        list(operator_decision.get("bound_parameters", [])),
        list(contract["read_set"]),
        list(contract["touch_set"]),
        list(contract["forbidden_touch_set"]),
        []
    )
