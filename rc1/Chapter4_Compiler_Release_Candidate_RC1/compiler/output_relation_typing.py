import hashlib, json, math
from .conflict_models import TypedOutputRelation, RELATION_FAMILIES

FORMAL_ALLOWED_BY_OPERATOR = {
    "SHIFT_TIME":{"EQUALITY_WITHIN_TOLERANCE","BOUNDED_CHANGE","DECISION_LEVEL"},
    "RESAMPLE_TRAJECTORY":{"EQUALITY_WITHIN_TOLERANCE","BOUNDED_CHANGE","ORDINAL_NONDECREASE","ORDINAL_NONINCREASE"},
    "DELAY_RESULT_ENTRY":{"DECISION_LEVEL","BOUNDED_CHANGE","EQUALITY_WITHIN_TOLERANCE"},
    "SWAP_EQUIVALENT_ORDER":{"EQUALITY_WITHIN_TOLERANCE"},
    "REMOVE_REDUNDANT_OBSERVATION":{"EQUALITY_WITHIN_TOLERANCE","BOUNDED_CHANGE"},
    "MASK_REQUIRED_OBSERVATION":{"DECISION_LEVEL"},
    "INCREASE_SLOPE":{"MONOTONIC_INCREASE","MONOTONIC_DECREASE","ORDINAL_NONDECREASE","ORDINAL_NONINCREASE","BOUNDED_CHANGE"},
    "DECREASE_SLOPE":{"MONOTONIC_INCREASE","MONOTONIC_DECREASE","ORDINAL_NONDECREASE","ORDINAL_NONINCREASE","BOUNDED_CHANGE"},
    "INSERT_TRANSIENT_AKI":{"MONOTONIC_INCREASE","MONOTONIC_DECREASE","ORDINAL_NONDECREASE","ORDINAL_NONINCREASE","BOUNDED_CHANGE","DECISION_LEVEL"},
    "CONVERT_UNIT":{"EQUALITY_WITHIN_TOLERANCE"},
    "PRESERVE_CLINICAL_STATE":{"EQUALITY_WITHIN_TOLERANCE","ORDINAL_NONDECREASE","ORDINAL_NONINCREASE","DECISION_LEVEL"},
}

def _canon(x):
    return json.dumps(x, sort_keys=True, separators=(",",":"), ensure_ascii=False)

def _sha(x):
    return hashlib.sha256(_canon(x).encode("utf-8")).hexdigest()

def _normalized_constraint(family, params):
    if family=="EQUALITY_WITHIN_TOLERANCE":
        eps=params.get("epsilon")
        mode=params.get("tolerance_mode")
        if eps is None or mode not in {"absolute","relative","mixed"}:
            return None,"INVALID_EQUALITY_TOLERANCE"
        # Only absolute tolerance maps to a direct delta interval. Relative/mixed remains typed but
        # cannot be compared numerically without source-output magnitude.
        if mode=="absolute":
            e=float(eps)
            return {"kind":"NUMERIC_DELTA_INTERVAL","lower":-e,"upper":e,"closed":True},""
        return {"kind":"PARAMETRIC_EQUALITY_TOLERANCE","mode":mode,"epsilon":eps},""

    if family=="MONOTONIC_INCREASE":
        strict=bool(params.get("strict_change_required",False))
        return {"kind":"NUMERIC_DELTA_INTERVAL","lower":0.0,"upper":"INF",
                "closed_lower":not strict,"closed_upper":False,
                "strict_change_required":strict},""

    if family=="MONOTONIC_DECREASE":
        strict=bool(params.get("strict_change_required",False))
        return {"kind":"NUMERIC_DELTA_INTERVAL","lower":"-INF","upper":0.0,
                "closed_lower":False,"closed_upper":not strict,
                "strict_change_required":strict},""

    if family=="ORDINAL_NONDECREASE":
        ordering=params.get("ordering_id")
        if not ordering:
            return None,"ORDINAL_ORDERING_REQUIRED"
        strict=bool(params.get("strict_change_required",False))
        return {"kind":"ORDINAL_RANK_DELTA","ordering_id":ordering,"direction":"NONDECREASE",
                "strict_change_required":strict},""

    if family=="ORDINAL_NONINCREASE":
        ordering=params.get("ordering_id")
        if not ordering:
            return None,"ORDINAL_ORDERING_REQUIRED"
        strict=bool(params.get("strict_change_required",False))
        return {"kind":"ORDINAL_RANK_DELTA","ordering_id":ordering,"direction":"NONINCREASE",
                "strict_change_required":strict},""

    if family=="BOUNDED_CHANGE":
        needed={"lower_bound","upper_bound","delta_definition"}
        if not needed <= set(params):
            return None,"BOUNDED_CHANGE_PARAMETERS_REQUIRED"
        lo=float(params["lower_bound"]); hi=float(params["upper_bound"])
        if lo>hi:
            return None,"BOUNDED_CHANGE_REVERSED_BOUNDS"
        return {"kind":"NUMERIC_DELTA_INTERVAL","lower":lo,"upper":hi,"closed":True,
                "delta_definition":params["delta_definition"]},""

    if family=="DECISION_LEVEL":
        dc=params.get("decision_comparator_id")
        if not dc:
            return None,"DECISION_COMPARATOR_REQUIRED"
        return {"kind":"DECISION_RELATION","decision_comparator_id":dc,
                "allowed_relation":params.get("allowed_relation"),
                "allowed_values":params.get("allowed_values")},""

    return None,"UNSUPPORTED_RELATION_FAMILY"

def final_type_relation(component):
    r=component["R"]
    family=r.get("relation_family")
    op=component["operator_id"]
    reasons=[]

    if r.get("status")!="GENERATED":
        reasons.append("C4_008_RELATION_NOT_GENERATED")
    if family not in RELATION_FAMILIES:
        reasons.append("UNSUPPORTED_FORMAL_RELATION_FAMILY")
    if family not in FORMAL_ALLOWED_BY_OPERATOR.get(op,set()):
        reasons.append("RELATION_NOT_ALLOWED_FOR_OPERATOR")

    normalized,err=_normalized_constraint(family,r.get("parameters",{})) if family else (None,"MISSING_RELATION_FAMILY")
    if err:
        reasons.append(err)

    status="FINAL_TYPED" if not reasons else "INVALID_RELATION_TYPE"
    domain = (
        "DECISION" if family=="DECISION_LEVEL" else
        "ORDINAL" if family in {"ORDINAL_NONDECREASE","ORDINAL_NONINCREASE"} else
        "NUMERIC"
    )
    signature_payload={
        "operator_id":op,
        "relation_family":family,
        "source_output_selector":r.get("source_output_selector"),
        "followup_output_selector":r.get("followup_output_selector"),
        "comparator_id":r.get("comparator_id"),
        "parameters":r.get("parameters",{}),
        "normalized_constraint":normalized,
    }
    sig="REL-"+_sha(signature_payload)[:20]
    return TypedOutputRelation(
        proposition_id=component["proposition_id"],
        operator_id=op,
        typing_status=status,
        relation_family=family or "",
        source_output_selector=r.get("source_output_selector") or "",
        followup_output_selector=r.get("followup_output_selector") or "",
        comparator_id=r.get("comparator_id") or "",
        parameters=dict(r.get("parameters",{})),
        semantic_domain=domain,
        normalized_constraint=normalized or {},
        relation_signature=sig,
        reasons=reasons,
    )

def _bound_value(x, which):
    if x=="INF": return math.inf
    if x=="-INF": return -math.inf
    return float(x)

def relation_compatibility(a,b):
    """
    Returns TRUE when compatibility is proven, FALSE when incompatibility is proven,
    INDETERMINATE when the formal relation domains cannot safely be compared.
    """
    if a.typing_status!="FINAL_TYPED" or b.typing_status!="FINAL_TYPED":
        return "INDETERMINATE","UNTYPED_RELATION"

    ca=a.normalized_constraint; cb=b.normalized_constraint
    ka=ca.get("kind"); kb=cb.get("kind")

    if ka=="NUMERIC_DELTA_INTERVAL" and kb=="NUMERIC_DELTA_INTERVAL":
        # BOUNDED_CHANGE delta definitions must agree when both declare one.
        da=ca.get("delta_definition"); db=cb.get("delta_definition")
        if da and db and da!=db:
            return "INDETERMINATE","DIFFERENT_DELTA_DEFINITIONS"
        alo=_bound_value(ca["lower"],"lower"); ahi=_bound_value(ca["upper"],"upper")
        blo=_bound_value(cb["lower"],"lower"); bhi=_bound_value(cb["upper"],"upper")
        lo=max(alo,blo); hi=min(ahi,bhi)
        if lo<hi:
            return "TRUE","NONEMPTY_NUMERIC_INTERSECTION"
        if lo>hi:
            return "FALSE","DISJOINT_NUMERIC_EXPECTATION_SETS"
        # Single-point intersection. Reject if either side explicitly requires strict movement at that bound.
        strict_a=bool(ca.get("strict_change_required",False))
        strict_b=bool(cb.get("strict_change_required",False))
        if (strict_a or strict_b) and lo==0.0:
            return "FALSE","ONLY_EQUALITY_INTERSECTION_BUT_STRICT_CHANGE_REQUIRED"
        return "TRUE","SINGLE_POINT_NUMERIC_INTERSECTION"

    if ka=="ORDINAL_RANK_DELTA" and kb=="ORDINAL_RANK_DELTA":
        if ca.get("ordering_id")!=cb.get("ordering_id"):
            return "INDETERMINATE","DIFFERENT_ORDINAL_ORDERINGS"
        da=ca.get("direction"); db=cb.get("direction")
        if da==db:
            return "TRUE","SAME_ORDINAL_DIRECTION"
        # NONDECREASE and NONINCREASE intersect at unchanged rank.
        if ca.get("strict_change_required") or cb.get("strict_change_required"):
            return "FALSE","ONLY_EQUAL_RANK_INTERSECTION_BUT_STRICT_CHANGE_REQUIRED"
        return "TRUE","UNCHANGED_RANK_SATISFIES_BOTH_NONSTRICT_RELATIONS"

    if ka=="DECISION_RELATION" and kb=="DECISION_RELATION":
        if ca.get("decision_comparator_id")!=cb.get("decision_comparator_id"):
            return "INDETERMINATE","DIFFERENT_DECISION_COMPARATORS"
        va=ca.get("allowed_values"); vb=cb.get("allowed_values")
        if va is not None and vb is not None:
            inter=set(va)&set(vb)
            return ("TRUE","NONEMPTY_DECISION_ALLOWED_SET_INTERSECTION") if inter else ("FALSE","DISJOINT_DECISION_ALLOWED_SETS")
        if ca.get("allowed_relation")==cb.get("allowed_relation"):
            return "TRUE","SAME_DECISION_RELATION"
        return "INDETERMINATE","DECISION_RELATION_COMPATIBILITY_NOT_PROVABLE"

    # Parametric equality (relative/mixed) cannot be compared statically without output magnitude.
    if ka=="PARAMETRIC_EQUALITY_TOLERANCE" or kb=="PARAMETRIC_EQUALITY_TOLERANCE":
        if a.relation_signature==b.relation_signature:
            return "TRUE","IDENTICAL_PARAMETRIC_RELATION"
        return "INDETERMINATE","PARAMETRIC_TOLERANCE_NEEDS_RUNTIME_OUTPUT"

    return "INDETERMINATE","CROSS_DOMAIN_RELATION_COMPARISON_UNDEFINED"
