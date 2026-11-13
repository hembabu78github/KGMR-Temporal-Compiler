from .component_models import OutputRelationDraft, RELATION_FAMILIES

def _expand_permitted(permitted):
    expanded = set(permitted)
    # C4-006 may carry the internal compatibility token PRESERVE_OUTPUT.
    # C4-008 normalises it to evidence-backed formal R families.
    if "PRESERVE_OUTPUT" in expanded:
        expanded.update({"EQUALITY_WITHIN_TOLERANCE", "DECISION_LEVEL"})
    return expanded

def _validate_relation_parameters(ev):
    fam = ev.relation_family
    p = ev.parameters
    reasons = []

    if fam == "EQUALITY_WITHIN_TOLERANCE":
        if p.get("tolerance_mode") not in {"absolute","relative","mixed"}:
            reasons.append("EQUALITY_TOLERANCE_MODE_REQUIRED")
        if "epsilon" not in p:
            reasons.append("EQUALITY_EPSILON_REQUIRED")

    elif fam in {"MONOTONIC_INCREASE","MONOTONIC_DECREASE"}:
        pass

    elif fam in {"ORDINAL_NONDECREASE","ORDINAL_NONINCREASE"}:
        if not p.get("ordering_id"):
            reasons.append("ORDINAL_ORDERING_REQUIRED")

    elif fam == "BOUNDED_CHANGE":
        for key in ("lower_bound","upper_bound","delta_definition"):
            if key not in p:
                reasons.append(f"BOUNDED_CHANGE_REQUIRED:{key}")

    elif fam == "DECISION_LEVEL":
        if not p.get("decision_comparator_id"):
            reasons.append("DECISION_COMPARATOR_REQUIRED")

    return reasons

def generate_output_relation(inp, operator_decision):
    operator_id = operator_decision.get("operator_id")
    permitted_raw = list(operator_decision.get("permitted_relations", []))
    permitted_set = _expand_permitted(permitted_raw)

    relevant = [
        ev for ev in inp.relation_evidence
        if ev.relation_family in permitted_set
        and (not ev.applicable_operators or operator_id in set(ev.applicable_operators))
    ]
    relevant.sort(key=lambda ev: (ev.evidence_priority, ev.relation_family, ev.source_ref))

    candidate_families = sorted({ev.relation_family for ev in relevant})

    if not relevant:
        return OutputRelationDraft(
            status="UNRESOLVED",
            relation_family=None,
            source_output_selector=None,
            followup_output_selector=None,
            comparator_id=None,
            parameters={},
            source_ref=None,
            candidate_families=sorted(permitted_set & set(RELATION_FAMILIES)),
            reasons=["NO_EVIDENCE_BACKED_RELATION_FOR_OPERATOR"]
        )

    best_priority = relevant[0].evidence_priority
    best = [ev for ev in relevant if ev.evidence_priority == best_priority]
    best_families = sorted({ev.relation_family for ev in best})

    if len(best_families) != 1:
        return OutputRelationDraft(
            status="AMBIGUOUS",
            relation_family=None,
            source_output_selector=None,
            followup_output_selector=None,
            comparator_id=None,
            parameters={},
            source_ref=None,
            candidate_families=best_families,
            reasons=["MULTIPLE_EQUAL_PRIORITY_RELATION_FAMILIES"]
        )

    chosen = sorted(
        [ev for ev in best if ev.relation_family == best_families[0]],
        key=lambda ev: ev.source_ref
    )[0]

    if chosen.relation_family not in RELATION_FAMILIES:
        return OutputRelationDraft(
            "INVALID", None, None, None, None, {}, None,
            candidate_families, ["UNSUPPORTED_RELATION_FAMILY"]
        )

    reasons = _validate_relation_parameters(chosen)
    if reasons:
        return OutputRelationDraft(
            "INVALID", chosen.relation_family,
            chosen.source_output_selector, chosen.followup_output_selector,
            chosen.comparator_id, dict(chosen.parameters), chosen.source_ref,
            candidate_families, reasons
        )

    return OutputRelationDraft(
        "GENERATED", chosen.relation_family,
        chosen.source_output_selector, chosen.followup_output_selector,
        chosen.comparator_id, dict(chosen.parameters), chosen.source_ref,
        candidate_families, []
    )
