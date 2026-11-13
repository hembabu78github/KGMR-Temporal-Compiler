from __future__ import annotations
import ast
import copy
import hashlib
import json
import py_compile
import re
from pathlib import Path

from compiler.candidate_assembly import stable_candidate_id
from compiler.candidate_validation import validate_candidate
from compiler.deterministic_yaml import dumps_yaml_document, loads_deterministic_yaml_document
from compiler.python_codegen import derive_control, semantic_fp

def _sha_bytes(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _canon(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def _selector_glob_match(selector,pattern):
    import fnmatch
    p=str(pattern).replace("[*]","*").replace("[selected]","*").replace("[equivalent_set]","*")
    return selector==pattern or fnmatch.fnmatch(selector,p)

def _extract_generated_constants(path):
    tree=ast.parse(Path(path).read_text(encoding="utf-8"),filename=str(path))
    vals={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            name=node.targets[0].id
            if name in {"_SPEC_JSON","_CONTROL_JSON"}:
                try:
                    vals[name]=ast.literal_eval(node.value)
                except Exception:
                    vals[name]=None
    spec=json.loads(vals["_SPEC_JSON"]) if vals.get("_SPEC_JSON") is not None else None
    control=json.loads(vals["_CONTROL_JSON"]) if vals.get("_CONTROL_JSON") is not None else None
    return tree,spec,control

def _audit_generated_module(path,policy):
    errors=[]
    tree,spec,control=_extract_generated_constants(path)
    allowed_import=set(policy["generated_module_allowed_imports"]["import"])
    allowed_from=policy["generated_module_allowed_imports"]["from"]

    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            for a in node.names:
                if a.name not in allowed_import:
                    errors.append("UNAPPROVED_IMPORT:"+a.name)
        elif isinstance(node,ast.ImportFrom):
            module=node.module or ""
            if module not in allowed_from:
                errors.append("UNAPPROVED_IMPORT_FROM:"+module)
            else:
                allowed_names=set(allowed_from[module])
                for a in node.names:
                    if a.name not in allowed_names:
                        errors.append("UNAPPROVED_IMPORTED_NAME:"+module+":"+a.name)
        elif isinstance(node,ast.Name) and node.id in set(policy["forbidden_code_names"]):
            errors.append("FORBIDDEN_CODE_NAME:"+node.id)
        elif isinstance(node,ast.Attribute):
            if node.attr in {"system","popen","Popen","run","call","check_output","urlopen"}:
                errors.append("FORBIDDEN_CODE_ATTRIBUTE:"+node.attr)

    if spec is None:
        errors.append("EMBEDDED_SPEC_NOT_EXTRACTABLE")
    if control is None:
        errors.append("EMBEDDED_CONTROL_NOT_EXTRACTABLE")
    return sorted(set(errors)),spec,control

def _audit_shared_runtime(path,policy):
    errors=[]
    tree=ast.parse(Path(path).read_text(encoding="utf-8"),filename=str(path))
    allowed=set(policy["shared_runtime_allowed_import_roots"])
    forbidden=set(policy["forbidden_code_names"])
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            for a in node.names:
                root=a.name.split(".")[0]
                if root not in allowed:
                    errors.append("RUNTIME_UNAPPROVED_IMPORT:"+a.name)
        elif isinstance(node,ast.ImportFrom):
            root=(node.module or "").split(".")[0]
            if root not in allowed:
                errors.append("RUNTIME_UNAPPROVED_IMPORT_FROM:"+(node.module or ""))
        elif isinstance(node,ast.Name) and node.id in forbidden:
            errors.append("RUNTIME_FORBIDDEN_NAME:"+node.id)
        elif isinstance(node,ast.Attribute) and node.attr in {
            "system","popen","Popen","run","call","check_output","urlopen","remove","unlink"
        }:
            errors.append("RUNTIME_FORBIDDEN_ATTRIBUTE:"+node.attr)
    return sorted(set(errors))

def _recompute_candidate_id(spec):
    return stable_candidate_id(spec["C"],spec["T"],spec["R"],spec["I"],spec["E"],spec["P"])

def validate_static_bundle(spec,manifest_row,c4_013_manifest_row,gate_row,module_path,yaml_path,policy,runtime_config):
    checks=[]
    errors=[]
    warnings=[]

    def record(name,passed,detail=""):
        checks.append({"check":name,"passed":bool(passed),"detail":detail})
        if not passed:
            errors.append(name+((":"+detail) if detail else ""))

    # 1. Candidate structure and formal semantics.
    semantic_errors=validate_candidate(spec)
    record("CANDIDATE_SEMANTIC_VALIDATION",not semantic_errors,";".join(semantic_errors))
    record("REPRESENTATION_VERSION",spec.get("representation_version")==policy["representation_version"])
    record("CANDIDATE_LIFECYCLE_STATUS",spec.get("candidate_status")==policy["required_candidate_status"])
    record("EXPERT_STATUS_UNREVIEWED",
           spec.get("P",{}).get("mr_expert_validation_status")==policy["required_expert_validation_status"])

    # 2. Candidate semantic identity.
    actual_fp=semantic_fp(spec)
    record("SEMANTIC_FINGERPRINT_CHAIN",
           actual_fp==manifest_row.get("semantic_spec_fingerprint"),
           f"actual={actual_fp};manifest={manifest_row.get('semantic_spec_fingerprint')}")
    recomputed_id=_recompute_candidate_id(spec)
    record("CANDIDATE_ID_RECOMPUTE",
           recomputed_id==spec.get("candidate_mr_id"),
           f"actual={recomputed_id};declared={spec.get('candidate_mr_id')}")

    # 3. Deterministic YAML counterpart.
    try:
        actual_yaml_obj=loads_deterministic_yaml_document(Path(yaml_path).read_text(encoding="utf-8"))
        yaml_ok=(actual_yaml_obj==spec)
        yaml_detail=""
    except Exception as ex:
        yaml_ok=False
        yaml_detail=str(ex)
    record("JSON_YAML_SEMANTIC_EQUIVALENCE",yaml_ok,yaml_detail)

    # 4. Operator and parameter/provenance contract.
    op=spec["T"].get("operator_id")
    record("FROZEN_OPERATOR_MEMBERSHIP",op in set(policy["allowed_operators"]))
    p_errors=[]
    for p in spec["T"].get("bound_parameters",[]):
        if p.get("source_kind") not in {"kg","source_evidence","compiler_config"} or not p.get("source_ref"):
            p_errors.append(str(p.get("name")))
    record("PARAMETER_PROVENANCE_COMPLETE",not p_errors,",".join(p_errors))

    # 5. Touch/forbidden separation.
    touch=list(spec["T"].get("touch_set",[]))
    forbidden=list(spec["T"].get("forbidden_touch_set",[]))
    overlaps=[]
    for t in touch:
        for f in forbidden:
            if _selector_glob_match(t,f) or _selector_glob_match(f,t):
                overlaps.append(t+"<->"+f)
    record("TOUCH_FORBIDDEN_SEPARATION",not overlaps,";".join(overlaps))

    # 6. Invariant direct-contact safety.
    inv_contacts=[]
    for inv in spec.get("I",[]):
        sel=inv.get("source_selector","")
        for t in touch:
            if _selector_glob_match(sel,t) or _selector_glob_match(t,sel):
                inv_contacts.append(inv.get("invariant_id","?")+"@"+sel+"~"+t)
    record("INVARIANTS_DIRECTLY_UNTOUCHED",not inv_contacts,";".join(inv_contacts))

    # 7. R type membership and ABSTAIN separation.
    fam=spec["R"].get("relation_family")
    record("FORMAL_RELATION_MEMBERSHIP",fam in set(policy["allowed_relation_families"]))
    record("ABSTAIN_NOT_RELATION_FAMILY",fam!="ABSTAIN")

    # 8. Exception vocabulary/precedence/provenance and no fixture truth.
    exc_errors=[]
    for e in spec.get("E",[]):
        if e.get("exception_type") not in set(policy["allowed_exception_types"]):
            exc_errors.append("TYPE:"+str(e.get("exception_ref")))
        if e.get("precedence_tier") not in set(policy["allowed_precedence_tiers"]):
            exc_errors.append("TIER:"+str(e.get("exception_ref")))
        if not e.get("evidence_refs"):
            exc_errors.append("PROV:"+str(e.get("exception_ref")))
        if "observed_fixture_truth" in json.dumps(e):
            exc_errors.append("FIXTURE_TRUTH:"+str(e.get("exception_ref")))
    record("EXCEPTION_STATIC_CONFORMANCE",not exc_errors,";".join(exc_errors))

    # 9. P provenance closure.
    P=spec["P"]
    prov_ok=bool(P.get("source_knowledge_item_ids") and P.get("source_locator_refs")
                 and P.get("graph_path_ids") and P.get("operator_selection_fingerprint")
                 and P.get("kg_release") and P.get("ontology_release") and P.get("shacl_release"))
    record("PROVENANCE_CLOSURE",prov_ok)

    # 10. Generated Python exact byte identity to researcher C4-014 manifest.
    module_hash=_sha_bytes(module_path)
    record("GENERATED_MODULE_SHA256",
           module_hash==manifest_row.get("generated_python_sha256"),
           f"actual={module_hash};manifest={manifest_row.get('generated_python_sha256')}")

    # 11. Python compilation.
    try:
        py_compile.compile(str(module_path),doraise=True)
        compile_ok=True; compile_detail=""
    except Exception as ex:
        compile_ok=False; compile_detail=str(ex)
    record("GENERATED_MODULE_PY_COMPILE",compile_ok,compile_detail)

    # 12. Static AST audit and embedded immutable SPEC.
    ast_errors,embedded_spec,embedded_control=_audit_generated_module(module_path,policy)
    record("GENERATED_MODULE_AST_SAFETY",not ast_errors,";".join(ast_errors))
    record("EMBEDDED_SPEC_EQUALS_CANDIDATE",embedded_spec==spec)

    expected_control=derive_control(c4_013_manifest_row)
    record("EMBEDDED_CONTROL_EQUALS_DERIVED_CONTROL",embedded_control==expected_control)

    # 13. Execution-gate and researcher end-to-end evidence consistency.
    record("C4_014_MANIFEST_GATE_EQUALS_DERIVED_GATE",
           manifest_row.get("execution_gate")==expected_control.get("execution_gate"))
    record("C4_014_BLOCKING_REASONS_EQUAL_DERIVED_CONTROL",
           sorted(manifest_row.get("blocking_reasons",[]))==sorted(expected_control.get("blocking_reasons",[])))
    record("END_TO_END_GATE_EQUALS_MANIFEST",
           gate_row.get("execution_gate")==manifest_row.get("execution_gate"))
    if manifest_row.get("execution_gate")=="ABSTAIN":
        record("BLOCKED_CANDIDATE_DID_NOT_CALL_CDS",gate_row.get("cds_call_count")==0)
        admission="STATICALLY_VALID_BUT_CONTROL_BLOCKED"
    else:
        record("PROCEED_CANDIDATE_E2E_CALLED_CDS_TWICE",gate_row.get("cds_call_count")==2)
        admission="STATICALLY_VALID_EXECUTION_ADMISSIBLE"

    record("END_TO_END_GATE_TEST_PASS",gate_row.get("pass") is True)

    # 14. Runtime mapping dependencies for operator families that require config.
    runtime_deps=[]
    if op=="CONVERT_UNIT":
        pmap={p["name"]:p["value"] for p in spec["T"].get("bound_parameters",[])}
        cid=pmap.get("conversion_id")
        if cid not in runtime_config.get("unit_conversions",{}):
            runtime_deps.append("MISSING_UNIT_CONVERSION:"+str(cid))
    if fam in {"ORDINAL_NONDECREASE","ORDINAL_NONINCREASE"}:
        oid=spec["R"].get("parameters",{}).get("ordering_id")
        if oid not in runtime_config.get("ordinal_orderings",{}):
            runtime_deps.append("MISSING_ORDINAL_ORDERING:"+str(oid))
    if fam=="DECISION_LEVEL":
        did=spec["R"].get("parameters",{}).get("decision_comparator_id")
        if did not in set(runtime_config.get("decision_comparators",[])):
            runtime_deps.append("MISSING_DECISION_COMPARATOR:"+str(did))
    record("RUNTIME_DEPENDENCIES_RESOLVED",not runtime_deps,";".join(runtime_deps))

    static_status="STATIC_VALIDATION_PASS" if not errors else "STATIC_VALIDATION_FAIL"
    if errors:
        admission="STATIC_VALIDATION_FAILED"

    return {
      "candidate_mr_id":spec["candidate_mr_id"],
      "candidate_key":manifest_row["candidate_key"],
      "operator_id":op,
      "static_validation_status":static_status,
      "execution_admission_status":admission,
      "expert_validation_status":spec["P"]["mr_expert_validation_status"],
      "check_count":len(checks),
      "passed_check_count":sum(x["passed"] for x in checks),
      "failed_check_count":sum(not x["passed"] for x in checks),
      "checks":checks,
      "errors":errors,
      "warnings":warnings,
      "semantic_spec_fingerprint":actual_fp,
      "generated_module_sha256":module_hash
    }

def validate_shared_runtime(runtime_path,policy):
    errors=_audit_shared_runtime(runtime_path,policy)
    try:
        py_compile.compile(str(runtime_path),doraise=True)
        compile_ok=True
    except Exception as ex:
        compile_ok=False
        errors.append("RUNTIME_COMPILE_FAILED:"+str(ex))
    return {
      "runtime_path":str(runtime_path),
      "sha256":_sha_bytes(runtime_path),
      "compile_pass":compile_ok,
      "ast_safety_pass":not errors,
      "errors":sorted(set(errors))
    }
