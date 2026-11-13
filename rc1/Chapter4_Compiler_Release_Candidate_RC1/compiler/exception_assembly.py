from .exception_models import AssembledException, K3_VALUES, PRECEDENCE_TIERS

def assemble_exceptions(proposition_id, operator_id, evidence_rows, config):
    frozen_types = set(config["exception_types"])
    out = []

    for ev in sorted(evidence_rows, key=lambda x:(x.precedence_tier, x.exception_type, x.exception_ref)):
        # P2 safety: an exception affects only its explicit rule/operator scope.
        if ev.linked_proposition_id != proposition_id:
            continue
        if ev.linked_operator_ids and operator_id not in set(ev.linked_operator_ids):
            continue

        reasons = []
        if ev.exception_type not in frozen_types:
            reasons.append("UNKNOWN_EXCEPTION_TYPE")
        if ev.precedence_tier not in PRECEDENCE_TIERS:
            reasons.append("INVALID_PRECEDENCE_TIER")
        if ev.condition_truth not in K3_VALUES:
            reasons.append("INVALID_K3_TRUTH")
        if not ev.scope_ref:
            reasons.append("MISSING_EXPLICIT_SCOPE")
        if not ev.condition_id or not ev.evaluator_id:
            reasons.append("MISSING_CONDITION_EVALUATOR")
        if not ev.source_refs:
            reasons.append("MISSING_EXCEPTION_PROVENANCE")

        expected_tier = config["exception_types"].get(ev.exception_type,{}).get("default_precedence_tier")
        if expected_tier and ev.precedence_tier != expected_tier:
            reasons.append(f"NONDEFAULT_PRECEDENCE_REQUIRES_EXPLICIT_JUSTIFICATION:{expected_tier}")

        status = "ASSEMBLED" if not reasons else "INVALID"
        out.append(AssembledException(
            exception_ref=ev.exception_ref,
            exception_type=ev.exception_type,
            linked_proposition_id=proposition_id,
            linked_operator_id=operator_id,
            scope_ref=ev.scope_ref,
            condition={
                "predicate_id": ev.condition_id,
                "predicate_type": "EXCEPTION",
                "arguments": {"exception_type":ev.exception_type,"scope_ref":ev.scope_ref},
                "evaluator_id": ev.evaluator_id,
                "source_refs": sorted(ev.source_refs),
                "observed_fixture_truth": ev.condition_truth,
                "missing_evidence_result": "INDETERMINATE"
            },
            precedence_tier=ev.precedence_tier,
            effect_mode=ev.effect_mode,
            phase=ev.phase,
            source_refs=sorted(ev.source_refs),
            assembly_status=status,
            reasons=reasons
        ))

    return out
