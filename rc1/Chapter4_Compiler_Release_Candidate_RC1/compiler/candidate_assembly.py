import hashlib, json, re
from pathlib import Path

def _canon(x):
    return json.dumps(x, sort_keys=True, separators=(",",":"), ensure_ascii=False)

def _sha(x):
    return hashlib.sha256(_canon(x).encode("utf-8")).hexdigest()

def key(prop,op):
    return f"{prop}::{op}"

def stable_candidate_id(C,T,R,I,E,P):
    # P projection excludes volatile/runtime fixture truth and filesystem metadata.
    pproj={
      "source_knowledge_item_ids":P["source_knowledge_item_ids"],
      "source_locator_refs":P["source_locator_refs"],
      "graph_path_ids":P["graph_path_ids"],
      "kg_release":P["kg_release"],
      "ontology_release":P["ontology_release"],
      "shacl_release":P["shacl_release"],
      "proposition_ir_version":P["proposition_ir_version"],
      "compiler_version":P["compiler_version"],
      "operator_library_version":P["operator_library_version"],
      "operator_selection_fingerprint":P["operator_selection_fingerprint"],
      "parameter_provenance_refs":P["parameter_provenance_refs"],
      "inference_profile":P["inference_profile"],
      "closure_policy_version":P["closure_policy_version"],
      "srew_version":P["srew_version"],
      "compiler_config_id":P["compiler_config_id"],
    }
    payload={"C":C,"T":T,"R":R,"I":I,"E":E,"P":pproj}
    return "CMR-"+_sha(payload)[:24]

def clean_exception(e):
    cond=dict(e["condition"])
    cond.pop("observed_fixture_truth",None)
    # This is now a generic executable exception predicate, not a fixture outcome.
    return {
      "exception_ref":e["exception_ref"],
      "exception_type":e["exception_type"],
      "condition":{
        "predicate_id":cond["predicate_id"],
        "predicate_type":"EXCEPTION",
        "arguments":dict(cond.get("arguments",{})),
        "evaluator_id":cond["evaluator_id"],
        "source_refs":sorted(cond.get("source_refs",[])),
        "missing_evidence_result":"INDETERMINATE",
      },
      "precedence_tier":e["precedence_tier"],
      "evidence_refs":sorted(e.get("source_refs",[])),
      "resolution_status":"DECLARED",
    }

def build_provenance(component,typed,inv,exc,temp,conflicts):
    param_refs=sorted({
      p["source_ref"] for p in component["T"].get("bound_parameters",[])
      if p.get("source_ref")
    })
    source_refs=sorted(set(component.get("source_refs",[])))
    source_kis=[x for x in source_refs if "knowledge-item" in x.lower()]
    if not source_kis:
        # Fixture/compiler source ref fallback remains explicit and non-clinical.
        source_kis=source_refs[:1]
    conflict_refs=sorted({
      c["conflict_id"] for c in conflicts
      if key(component["proposition_id"],component["operator_id"]) in c["involved_candidate_keys"]
    })
    return {
      "source_knowledge_item_ids":source_kis,
      "source_locator_refs":source_refs,
      "graph_path_ids":sorted(component.get("graph_path_ids",[])),
      "kg_release":component.get("release_ref") or "CKD-TKG-R1.0",
      "ontology_release":"CKD-TKG-R1.0",
      "shacl_release":"CKD-TKG-SHACL-R1.0",
      "proposition_ir_version":"ClinicalPropositionIR-1.0",
      "compiler_version":"C4-013-R1.0",
      "operator_library_version":component["T"]["operator_version"],
      "operator_selection_fingerprint":component["c4_006_selection_fingerprint"],
      "parameter_provenance_refs":param_refs,
      "source_review_refs":[],
      "inference_profile":"RDFS+SREW-R1.0",
      "closure_policy_version":"C3-016-R1.0",
      "srew_version":"SREW-R1.0",
      "compiler_config_id":"C4-006-CompilerConfig-R1.0",
      "generation_status":"CANDIDATE",
      "mr_expert_validation_status":"UNREVIEWED",
    }, conflict_refs

def build_candidate(component,typed,inv,exc,temp,conflicts):
    C=component["C"]["expression"]
    T={
      "operator_id":component["T"]["operator_id"],
      "operator_version":component["T"]["operator_version"],
      "bound_parameters":list(component["T"].get("bound_parameters",[])),
      "read_set":list(component["T"].get("read_set",[])),
      "touch_set":list(component["T"].get("touch_set",[])),
      "forbidden_touch_set":list(component["T"].get("forbidden_touch_set",[])),
    }
    R={
      "relation_family":typed["relation_family"],
      "source_output_selector":typed["source_output_selector"],
      "followup_output_selector":typed["followup_output_selector"],
      "comparator_id":typed["comparator_id"],
      "parameters":dict(typed.get("parameters",{})),
    }
    I=sorted(inv.get("inferred_invariants",[]), key=lambda x:x["invariant_id"])
    E=sorted([clean_exception(x) for x in exc.get("assembled_exceptions",[])],
             key=lambda x:(x["precedence_tier"],x["exception_type"],x["exception_ref"]))
    P,conflict_refs=build_provenance(component,typed,inv,exc,temp,conflicts)

    cmr_id=stable_candidate_id(C,T,R,I,E,P)
    spec={
      "candidate_mr_id":cmr_id,
      "representation_version":"CandidateMR-R1.0",
      "candidate_status":"COMPILED_CANDIDATE",
      "C":C,"T":T,"R":R,"I":I,"E":E,"P":P
    }

    control={
      "candidate_mr_id":cmr_id,
      "candidate_key":key(component["proposition_id"],component["operator_id"]),
      "proposition_id":component["proposition_id"],
      "operator_id":component["operator_id"],
      "c4_008_component_fingerprint":component["component_fingerprint"],
      "c4_009_invariant_fingerprint":inv["invariant_fingerprint"],
      "c4_010_exception_fingerprint":exc["exception_fingerprint"],
      "c4_011_temporal_fingerprint":temp["temporal_fingerprint"],
      "c4_012_relation_signature":typed["relation_signature"],
      "c4_012_conflict_ids":conflict_refs,
      "upstream_exception_system_action":exc["system_action"],
      "upstream_temporal_system_action":temp["system_action"],
      "upstream_temporal_truth":temp["temporal_truth"],
      "fixture_control_status":"SOFTWARE_VALIDATION_ONLY",
    }
    return spec,control

def semantic_fingerprint(spec):
    return _sha(spec)

def safe_filename(spec):
    return spec["candidate_mr_id"]+".json"
