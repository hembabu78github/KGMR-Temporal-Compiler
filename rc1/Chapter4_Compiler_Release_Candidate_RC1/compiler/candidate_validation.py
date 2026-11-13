ALLOWED_OPERATORS={
 "SHIFT_TIME","RESAMPLE_TRAJECTORY","DELAY_RESULT_ENTRY","SWAP_EQUIVALENT_ORDER",
 "REMOVE_REDUNDANT_OBSERVATION","MASK_REQUIRED_OBSERVATION","INCREASE_SLOPE",
 "DECREASE_SLOPE","INSERT_TRANSIENT_AKI","CONVERT_UNIT","PRESERVE_CLINICAL_STATE"
}
ALLOWED_R={
 "EQUALITY_WITHIN_TOLERANCE","MONOTONIC_INCREASE","MONOTONIC_DECREASE",
 "ORDINAL_NONDECREASE","ORDINAL_NONINCREASE","BOUNDED_CHANGE","DECISION_LEVEL"
}
ALLOWED_C_TYPES={"CLINICAL","DATA_AVAILABILITY","TEMPORAL","APPLICABILITY","TERMINOLOGY"}
ALLOWED_I_TYPES={"VALUE","IDENTITY","TIME","STATE","STRUCTURE","UNIT_CANONICAL_VALUE","CUSTOM_DECLARED"}
ALLOWED_P_TIERS={f"P{i}" for i in range(9)}

def _validate_condition(x,path="C"):
    errs=[]
    if "op" in x:
        if x["op"] in {"ALL","ANY"}:
            if not x.get("children"):
                errs.append(f"{path}: empty {x['op']}")
            for i,c in enumerate(x.get("children",[])):
                errs += _validate_condition(c,f"{path}.children[{i}]")
        elif x["op"]=="NOT":
            errs += _validate_condition(x["child"],f"{path}.child")
        else:
            errs.append(f"{path}: unsupported logical operator")
        return errs
    if x.get("predicate_type") not in ALLOWED_C_TYPES:
        errs.append(f"{path}: invalid predicate type")
    if x.get("missing_evidence_result")!="INDETERMINATE":
        errs.append(f"{path}: missing evidence must be INDETERMINATE")
    if not x.get("source_refs"):
        errs.append(f"{path}: source_refs required")
    if not x.get("evaluator_id"):
        errs.append(f"{path}: evaluator_id required")
    return errs

def validate_candidate(spec):
    errs=[]
    for k in ["candidate_mr_id","representation_version","candidate_status","C","T","R","I","E","P"]:
        if k not in spec: errs.append(f"missing top-level {k}")
    if errs: return errs
    if spec["representation_version"]!="CandidateMR-R1.0":
        errs.append("invalid representation_version")
    if spec["candidate_status"]!="COMPILED_CANDIDATE":
        errs.append("C4-013 may emit only COMPILED_CANDIDATE")

    errs += _validate_condition(spec["C"])

    T=spec["T"]
    if T.get("operator_id") not in ALLOWED_OPERATORS:
        errs.append("T operator outside frozen library")
    for p in T.get("bound_parameters",[]):
        if p.get("source_kind") not in {"kg","source_evidence","compiler_config"} or not p.get("source_ref"):
            errs.append("unprovenanced T parameter")

    R=spec["R"]
    fam=R.get("relation_family")
    if fam not in ALLOWED_R:
        errs.append("unsupported R family")
    if fam=="EQUALITY_WITHIN_TOLERANCE":
        if "epsilon" not in R.get("parameters",{}) or R["parameters"].get("tolerance_mode") not in {"absolute","relative","mixed"}:
            errs.append("equality tolerance incomplete")
    if fam in {"ORDINAL_NONDECREASE","ORDINAL_NONINCREASE"} and not R.get("parameters",{}).get("ordering_id"):
        errs.append("ordinal ordering missing")
    if fam=="BOUNDED_CHANGE":
        p=R.get("parameters",{})
        if not {"lower_bound","upper_bound","delta_definition"} <= set(p):
            errs.append("bounded change incomplete")
    if fam=="DECISION_LEVEL" and not R.get("parameters",{}).get("decision_comparator_id"):
        errs.append("decision comparator missing")

    for i,inv in enumerate(spec["I"]):
        if inv.get("invariant_type") not in ALLOWED_I_TYPES:
            errs.append(f"I[{i}] invalid type")
        if not inv.get("source_selector") or not inv.get("followup_selector"):
            errs.append(f"I[{i}] selector missing")
        if not inv.get("comparator_id") or not inv.get("source_refs"):
            errs.append(f"I[{i}] comparator/provenance missing")

    for i,e in enumerate(spec["E"]):
        if e.get("precedence_tier") not in ALLOWED_P_TIERS:
            errs.append(f"E[{i}] invalid precedence tier")
        c=e.get("condition",{})
        if c.get("predicate_type")!="EXCEPTION":
            errs.append(f"E[{i}] predicate_type must be EXCEPTION")
        if c.get("missing_evidence_result")!="INDETERMINATE":
            errs.append(f"E[{i}] missing evidence must be INDETERMINATE")
        if "observed_fixture_truth" in c:
            errs.append(f"E[{i}] leaked fixture truth into generic candidate spec")
        if not e.get("evidence_refs"):
            errs.append(f"E[{i}] exception evidence refs missing")

    P=spec["P"]
    required_p=[
      "source_knowledge_item_ids","source_locator_refs","graph_path_ids","kg_release",
      "ontology_release","shacl_release","proposition_ir_version","compiler_version",
      "operator_library_version","operator_selection_fingerprint","parameter_provenance_refs",
      "inference_profile","closure_policy_version","srew_version","compiler_config_id",
      "generation_status","mr_expert_validation_status"
    ]
    for k in required_p:
        if k not in P: errs.append(f"P missing {k}")
    if P.get("generation_status")!="CANDIDATE":
        errs.append("P generation_status must be CANDIDATE")
    if P.get("mr_expert_validation_status")!="UNREVIEWED":
        errs.append("C4-013 must not claim expert validation")
    if not P.get("source_knowledge_item_ids") or not P.get("source_locator_refs"):
        errs.append("P source provenance incomplete")
    return errs
