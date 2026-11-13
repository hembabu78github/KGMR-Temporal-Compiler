import ast,copy,hashlib,json,tempfile,unittest
from pathlib import Path

from compiler.static_validation import validate_static_bundle,validate_shared_runtime
from compiler.python_codegen import derive_control

ROOT=Path(__file__).resolve().parents[1]
POL=json.loads((ROOT/"config"/"static_validation_policy_r1.json").read_text())
CFG=json.loads((ROOT/"config"/"executable_runtime_r1.json").read_text())
MAN=json.loads((ROOT/"fixtures"/"researcher_c4_014_codegen_manifest.json").read_text())["modules"]
GATES=json.loads((ROOT/"fixtures"/"researcher_c4_014_end_to_end_gate_results.json").read_text())["results"]
GM={x["candidate_mr_id"]:x for x in GATES}
C13=json.loads((ROOT/"fixtures"/"researcher_c4_013_candidate_manifest.json").read_text())["candidates"]
C13M={x["candidate_mr_id"]:x for x in C13}

def spec(cid):
    return json.loads((ROOT/"fixtures"/"c4_013_candidate_specs"/(cid+".json")).read_text())

def row(cid):
    return next(x for x in MAN if x["candidate_mr_id"]==cid)

def validate(cid,s=None,m=None,g=None,module=None,yaml=None):
    m=m or row(cid); g=g or GM[cid]; s=s or spec(cid)
    module=module or (ROOT/"fixtures"/"researcher_c4_014_generated_modules"/m["module_path"])
    yaml=yaml or (ROOT/"fixtures"/"c4_013_candidate_specs"/(cid+".yaml"))
    return validate_static_bundle(s,m,C13M[cid],g,module,yaml,POL,CFG)

class C4015Tests(unittest.TestCase):
    def test_researcher_c4_014_manifest_has_12(self):
        self.assertEqual(len(MAN),12)

    def test_researcher_gate_results_have_12(self):
        self.assertEqual(len(GATES),12)

    def test_all_12_static_validate(self):
        for m in MAN:
            r=validate(m["candidate_mr_id"])
            self.assertEqual(r["static_validation_status"],"STATIC_VALIDATION_PASS",m["candidate_key"])
            self.assertEqual(r["failed_check_count"],0,m["candidate_key"])

    def test_eight_execution_admissible(self):
        rs=[validate(m["candidate_mr_id"]) for m in MAN]
        self.assertEqual(sum(x["execution_admission_status"]=="STATICALLY_VALID_EXECUTION_ADMISSIBLE" for x in rs),8)

    def test_four_control_blocked_remain_blocked(self):
        rs=[validate(m["candidate_mr_id"]) for m in MAN]
        self.assertEqual(sum(x["execution_admission_status"]=="STATICALLY_VALID_BUT_CONTROL_BLOCKED" for x in rs),4)

    def test_all_expert_status_unreviewed(self):
        for m in MAN:
            self.assertEqual(validate(m["candidate_mr_id"])["expert_validation_status"],"UNREVIEWED")

    def test_candidate_id_tamper_fails(self):
        cid=MAN[0]["candidate_mr_id"]; s=spec(cid); s["candidate_mr_id"]="CMR-TAMPER"
        r=validate(cid,s=s)
        self.assertEqual(r["static_validation_status"],"STATIC_VALIDATION_FAIL")
        self.assertTrue(any("CANDIDATE_ID_RECOMPUTE" in e for e in r["errors"]))

    def test_semantic_fingerprint_tamper_fails(self):
        cid=MAN[0]["candidate_mr_id"]; m=copy.deepcopy(row(cid))
        m["semantic_spec_fingerprint"]="0"*64
        r=validate(cid,m=m)
        self.assertTrue(any("SEMANTIC_FINGERPRINT_CHAIN" in e for e in r["errors"]))

    def test_invalid_operator_fails(self):
        cid=MAN[0]["candidate_mr_id"]; s=spec(cid); s["T"]["operator_id"]="MADE_UP"
        r=validate(cid,s=s)
        self.assertTrue(any("FROZEN_OPERATOR_MEMBERSHIP" in e or "CANDIDATE_SEMANTIC_VALIDATION" in e for e in r["errors"]))

    def test_unprovenanced_parameter_fails(self):
        cid=next(x["candidate_mr_id"] for x in MAN if x["operator_id"]=="SHIFT_TIME" and x["execution_gate"]=="PROCEED")
        s=spec(cid); s["T"]["bound_parameters"][0]["source_ref"]=""
        r=validate(cid,s=s)
        self.assertTrue(any("PARAMETER_PROVENANCE_COMPLETE" in e for e in r["errors"]))

    def test_touch_forbidden_overlap_fails(self):
        cid=next(x["candidate_mr_id"] for x in MAN if x["operator_id"]=="DELAY_RESULT_ENTRY")
        s=spec(cid); s["T"]["forbidden_touch_set"].append("observations[selected].issued_time")
        r=validate(cid,s=s)
        self.assertTrue(any("TOUCH_FORBIDDEN_SEPARATION" in e for e in r["errors"]))

    def test_invariant_touch_contact_fails(self):
        cid=next(x["candidate_mr_id"] for x in MAN if x["operator_id"]=="SHIFT_TIME" and x["execution_gate"]=="PROCEED")
        s=spec(cid)
        s["I"].append({
          "invariant_id":"INV-TAMPER","invariant_type":"TIME",
          "source_selector":"observations[selected].effective_time",
          "followup_selector":"observations[selected].effective_time",
          "comparator_id":"exact_equal_v1","parameters":{},"source_refs":["src"]
        })
        r=validate(cid,s=s)
        self.assertTrue(any("INVARIANTS_DIRECTLY_UNTOUCHED" in e for e in r["errors"]))

    def test_abstain_as_R_fails(self):
        cid=MAN[0]["candidate_mr_id"]; s=spec(cid); s["R"]["relation_family"]="ABSTAIN"
        r=validate(cid,s=s)
        self.assertTrue(any("ABSTAIN_NOT_RELATION_FAMILY" in e or "FORMAL_RELATION_MEMBERSHIP" in e for e in r["errors"]))

    def test_exception_fixture_truth_leak_fails(self):
        cid=next(x["candidate_mr_id"] for x in MAN if spec(x["candidate_mr_id"])["E"])
        s=spec(cid); s["E"][0]["condition"]["observed_fixture_truth"]="TRUE"
        r=validate(cid,s=s)
        self.assertTrue(any("EXCEPTION_STATIC_CONFORMANCE" in e for e in r["errors"]))

    def test_false_expert_acceptance_fails(self):
        cid=MAN[0]["candidate_mr_id"]; s=spec(cid); s["P"]["mr_expert_validation_status"]="ACCEPTED"
        r=validate(cid,s=s)
        self.assertTrue(any("EXPERT_STATUS_UNREVIEWED" in e for e in r["errors"]))

    def test_module_hash_tamper_fails(self):
        cid=MAN[0]["candidate_mr_id"]; m=row(cid)
        src=ROOT/"fixtures"/"researcher_c4_014_generated_modules"/m["module_path"]
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/src.name
            p.write_text(src.read_text(encoding="utf-8")+"\n# tamper\n",encoding="utf-8")
            r=validate(cid,module=p)
            self.assertTrue(any("GENERATED_MODULE_SHA256" in e for e in r["errors"]))

    def test_malicious_import_fails_ast_safety(self):
        cid=MAN[0]["candidate_mr_id"]; m=row(cid)
        src=ROOT/"fixtures"/"researcher_c4_014_generated_modules"/m["module_path"]
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/src.name
            p.write_text("import os\n"+src.read_text(encoding="utf-8"),encoding="utf-8")
            r=validate(cid,module=p)
            self.assertTrue(any("GENERATED_MODULE_AST_SAFETY" in e for e in r["errors"]))

    def test_embedded_spec_mismatch_fails(self):
        cid=MAN[0]["candidate_mr_id"]; m=row(cid)
        src=ROOT/"fixtures"/"researcher_c4_014_generated_modules"/m["module_path"]
        text=src.read_text(encoding="utf-8")
        # Deterministically change one embedded candidate id string only.
        text=text.replace(cid,cid+"X",1)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/src.name; p.write_text(text,encoding="utf-8")
            r=validate(cid,module=p)
            self.assertTrue(any("EMBEDDED_SPEC_EQUALS_CANDIDATE" in e or "GENERATED_MODULE_SHA256" in e for e in r["errors"]))

    def test_gate_mismatch_fails(self):
        cid=MAN[0]["candidate_mr_id"]; g=copy.deepcopy(GM[cid])
        g["execution_gate"]="PROCEED" if g["execution_gate"]=="ABSTAIN" else "ABSTAIN"
        r=validate(cid,g=g)
        self.assertTrue(any("END_TO_END_GATE_EQUALS_MANIFEST" in e for e in r["errors"]))

    def test_blocked_candidate_calling_cds_fails(self):
        cid=next(x["candidate_mr_id"] for x in MAN if x["execution_gate"]=="ABSTAIN")
        g=copy.deepcopy(GM[cid]); g["cds_call_count"]=2
        r=validate(cid,g=g)
        self.assertTrue(any("BLOCKED_CANDIDATE_DID_NOT_CALL_CDS" in e for e in r["errors"]))

    def test_proceed_candidate_not_calling_twice_fails(self):
        cid=next(x["candidate_mr_id"] for x in MAN if x["execution_gate"]=="PROCEED")
        g=copy.deepcopy(GM[cid]); g["cds_call_count"]=0
        r=validate(cid,g=g)
        self.assertTrue(any("PROCEED_CANDIDATE_E2E_CALLED_CDS_TWICE" in e for e in r["errors"]))

    def test_yaml_tamper_fails(self):
        cid=MAN[0]["candidate_mr_id"]
        yp=ROOT/"fixtures"/"c4_013_candidate_specs"/(cid+".yaml")
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/yp.name; p.write_text(yp.read_text(encoding="utf-8")+"# tamper\n",encoding="utf-8")
            r=validate(cid,yaml=p)
            self.assertTrue(any("JSON_YAML_SEMANTIC_EQUIVALENCE" in e for e in r["errors"]))

    def test_runtime_config_missing_unit_mapping_fails(self):
        cid=next(x["candidate_mr_id"] for x in MAN if x["operator_id"]=="CONVERT_UNIT")
        cfg=copy.deepcopy(CFG); cfg["unit_conversions"]={}
        m=row(cid); g=GM[cid]; s=spec(cid)
        module=ROOT/"fixtures"/"researcher_c4_014_generated_modules"/m["module_path"]
        yaml=ROOT/"fixtures"/"c4_013_candidate_specs"/(cid+".yaml")
        r=validate_static_bundle(s,m,C13M[cid],g,module,yaml,POL,cfg)
        self.assertTrue(any("RUNTIME_DEPENDENCIES_RESOLVED" in e for e in r["errors"]))

    def test_runtime_config_missing_ordinal_ordering_fails(self):
        cid=next(x["candidate_mr_id"] for x in MAN if x["operator_id"]=="INCREASE_SLOPE")
        cfg=copy.deepcopy(CFG); cfg["ordinal_orderings"]={}
        m=row(cid); g=GM[cid]; s=spec(cid)
        module=ROOT/"fixtures"/"researcher_c4_014_generated_modules"/m["module_path"]
        yaml=ROOT/"fixtures"/"c4_013_candidate_specs"/(cid+".yaml")
        r=validate_static_bundle(s,m,C13M[cid],g,module,yaml,POL,cfg)
        self.assertTrue(any("RUNTIME_DEPENDENCIES_RESOLVED" in e for e in r["errors"]))

    def test_runtime_config_missing_decision_comparator_fails(self):
        cid=next(x["candidate_mr_id"] for x in MAN if x["operator_id"]=="PRESERVE_CLINICAL_STATE")
        cfg=copy.deepcopy(CFG); cfg["decision_comparators"]=[]
        m=row(cid); g=GM[cid]; s=spec(cid)
        module=ROOT/"fixtures"/"researcher_c4_014_generated_modules"/m["module_path"]
        yaml=ROOT/"fixtures"/"c4_013_candidate_specs"/(cid+".yaml")
        r=validate_static_bundle(s,m,C13M[cid],g,module,yaml,POL,cfg)
        self.assertTrue(any("RUNTIME_DEPENDENCIES_RESOLVED" in e for e in r["errors"]))

    def test_shared_runtime_static_audit_passes(self):
        r=validate_shared_runtime(ROOT/"runtime"/"executable_runtime.py",POL)
        self.assertTrue(r["compile_pass"])
        self.assertTrue(r["ast_safety_pass"])
        self.assertEqual(r["errors"],[])

    def test_shared_runtime_malicious_import_fails(self):
        src=(ROOT/"runtime"/"executable_runtime.py").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"runtime.py"; p.write_text("import os\n"+src,encoding="utf-8")
            r=validate_shared_runtime(p,POL)
            self.assertFalse(r["ast_safety_pass"])

    def test_manifest_module_names_unique(self):
        names=[x["module_name"] for x in MAN]
        self.assertEqual(len(names),len(set(names)))

    def test_manifest_candidate_ids_unique(self):
        ids=[x["candidate_mr_id"] for x in MAN]
        self.assertEqual(len(ids),len(set(ids)))

    def test_manifest_hashes_unique(self):
        hs=[x["generated_python_sha256"] for x in MAN]
        self.assertEqual(len(hs),len(set(hs)))

    def test_static_pass_does_not_change_candidate_status(self):
        cid=MAN[0]["candidate_mr_id"]
        s=spec(cid); before=s["candidate_status"]; validate(cid,s=s)
        self.assertEqual(s["candidate_status"],before)
        self.assertEqual(before,"COMPILED_CANDIDATE")

    def test_static_pass_does_not_change_expert_status(self):
        cid=MAN[0]["candidate_mr_id"]
        s=spec(cid); before=s["P"]["mr_expert_validation_status"]; validate(cid,s=s)
        self.assertEqual(s["P"]["mr_expert_validation_status"],before)
        self.assertEqual(before,"UNREVIEWED")

if __name__=="__main__":
    unittest.main()
