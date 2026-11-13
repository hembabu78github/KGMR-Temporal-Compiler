import json,unittest,tempfile,subprocess,sys
from pathlib import Path
from compiler.candidate_assembly import build_candidate,stable_candidate_id,key,semantic_fingerprint
from compiler.candidate_validation import validate_candidate
from compiler.deterministic_yaml import dumps_yaml_document

ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def rmap(p): return {key(x["proposition_id"],x["operator_id"]):x for x in load(p)["results"]}

COMPS=load(ROOT/"fixtures"/"researcher_c4_008_component_generation_results.json")["results"]
INV=rmap(ROOT/"fixtures"/"researcher_c4_009_invariant_inference_results.json")
EXC=rmap(ROOT/"fixtures"/"researcher_c4_010_exception_precedence_results.json")
TEMP=rmap(ROOT/"fixtures"/"researcher_c4_011_temporal_satisfiability_results.json")
TYPED=rmap(ROOT/"fixtures"/"researcher_c4_012_output_relation_typing_results.json")
CONFLICTS=load(ROOT/"fixtures"/"researcher_c4_012_integrated_conflict_records.json")["records"]

def spec_for(prop,op):
    c=next(x for x in COMPS if x["proposition_id"]==prop and x["operator_id"]==op)
    k=key(prop,op)
    return build_candidate(c,TYPED[k],INV[k],EXC[k],TEMP[k],CONFLICTS)

class C4013Tests(unittest.TestCase):
    def test_upstream_c4_012_has_12_typed_relations(self):
        self.assertEqual(len(TYPED),12)

    def test_every_candidate_has_C_T_R_I_E_P(self):
        for c in COMPS:
            s,_=spec_for(c["proposition_id"],c["operator_id"])
            self.assertTrue(all(x in s for x in ["C","T","R","I","E","P"]))

    def test_all_candidates_validate(self):
        for c in COMPS:
            s,_=spec_for(c["proposition_id"],c["operator_id"])
            self.assertEqual(validate_candidate(s),[])

    def test_candidate_status_is_compiled_not_validated(self):
        s,_=spec_for("FIX-TIME-001","SHIFT_TIME")
        self.assertEqual(s["candidate_status"],"COMPILED_CANDIDATE")
        self.assertEqual(s["P"]["mr_expert_validation_status"],"UNREVIEWED")

    def test_exactly_one_operator_in_T(self):
        for c in COMPS:
            s,_=spec_for(c["proposition_id"],c["operator_id"])
            self.assertIsInstance(s["T"]["operator_id"],str)
            self.assertNotIn("operators",s["T"])

    def test_abstain_is_never_R_family(self):
        for c in COMPS:
            s,_=spec_for(c["proposition_id"],c["operator_id"])
            self.assertNotEqual(s["R"]["relation_family"],"ABSTAIN")

    def test_c4_012_final_relation_used(self):
        s,_=spec_for("FIX-TRAJ-001","DECREASE_SLOPE")
        self.assertEqual(s["R"]["relation_family"],"ORDINAL_NONINCREASE")

    def test_invariants_are_carried_from_c4_009(self):
        s,_=spec_for("FIX-TIME-001","SHIFT_TIME")
        self.assertEqual(len(s["I"]),len(INV["FIX-TIME-001::SHIFT_TIME"]["inferred_invariants"]))

    def test_exception_fixture_truth_is_removed(self):
        s,_=spec_for("FIX-AKI-001","INSERT_TRANSIENT_AKI")
        text=json.dumps(s["E"])
        self.assertNotIn("observed_fixture_truth",text)

    def test_exception_condition_is_typed_exception(self):
        s,_=spec_for("FIX-AKI-001","INSERT_TRANSIENT_AKI")
        self.assertEqual(s["E"][0]["condition"]["predicate_type"],"EXCEPTION")

    def test_exception_missing_evidence_still_indeterminate(self):
        s,_=spec_for("FIX-AKI-001","INSERT_TRANSIENT_AKI")
        self.assertEqual(s["E"][0]["condition"]["missing_evidence_result"],"INDETERMINATE")

    def test_provenance_contains_c4_006_selection_fingerprint(self):
        s,_=spec_for("FIX-TIME-001","SHIFT_TIME")
        self.assertTrue(s["P"]["operator_selection_fingerprint"])

    def test_parameter_provenance_preserved(self):
        s,_=spec_for("FIX-TIME-001","SHIFT_TIME")
        self.assertIn("fixture:temporal-window",s["P"]["parameter_provenance_refs"])

    def test_srew_version_preserved(self):
        s,_=spec_for("FIX-TIME-001","SHIFT_TIME")
        self.assertEqual(s["P"]["srew_version"],"SREW-R1.0")

    def test_expert_validation_is_separate_from_source_review(self):
        s,_=spec_for("FIX-TIME-001","SHIFT_TIME")
        self.assertEqual(s["P"]["mr_expert_validation_status"],"UNREVIEWED")

    def test_candidate_id_repeatable(self):
        a,_=spec_for("FIX-TIME-001","SHIFT_TIME")
        b,_=spec_for("FIX-TIME-001","SHIFT_TIME")
        self.assertEqual(a["candidate_mr_id"],b["candidate_mr_id"])

    def test_semantic_fingerprint_repeatable(self):
        a,_=spec_for("FIX-AKI-001","INSERT_TRANSIENT_AKI")
        b,_=spec_for("FIX-AKI-001","INSERT_TRANSIENT_AKI")
        self.assertEqual(semantic_fingerprint(a),semantic_fingerprint(b))

    def test_candidate_id_changes_when_semantics_change(self):
        s,_=spec_for("FIX-TIME-001","SHIFT_TIME")
        changed=json.loads(json.dumps(s))
        changed["R"]["parameters"]["epsilon"]=0.5
        # Recompute using the helper's semantic fields.
        p=changed["P"]
        new_id=stable_candidate_id(changed["C"],changed["T"],changed["R"],changed["I"],changed["E"],p)
        self.assertNotEqual(new_id,s["candidate_mr_id"])

    def test_candidate_id_does_not_include_wall_clock_time(self):
        s,_=spec_for("FIX-TIME-001","SHIFT_TIME")
        self.assertNotIn("timestamp",json.dumps(s).lower())
        self.assertNotIn("hostname",json.dumps(s).lower())

    def test_yaml_has_document_marker(self):
        s,_=spec_for("FIX-TIME-001","SHIFT_TIME")
        y=dumps_yaml_document(s)
        self.assertTrue(y.startswith("---\n"))

    def test_yaml_contains_all_six_component_keys(self):
        s,_=spec_for("FIX-TIME-001","SHIFT_TIME")
        y=dumps_yaml_document(s)
        for k in ["C:","T:","R:","I:","E:","P:"]:
            self.assertIn(k,y)

    def test_empty_exception_list_serializes_validly(self):
        s,_=spec_for("FIX-TRAJ-001","INCREASE_SLOPE")
        self.assertEqual(s["E"],[])
        self.assertIn("E: []",dumps_yaml_document(s))


    def test_yaml_scientific_float_is_numeric_for_common_yaml_parser(self):
        s,_=spec_for("FIX-UNIT-001","CONVERT_UNIT")
        y=dumps_yaml_document(s)
        try:
            import yaml
        except Exception:
            self.skipTest("PyYAML not installed; stdlib emitter has no runtime dependency")
        parsed=yaml.safe_load(y)
        self.assertIsInstance(parsed["R"]["parameters"]["epsilon"],float)
        self.assertEqual(parsed,s)

    def test_patched_schema_has_dedicated_exception_condition(self):
        sch=load(ROOT/"formal"/"candidate_mr_r1_c4_013_patch1.schema.json")
        self.assertEqual(sch["$defs"]["exceptionCondition"]["properties"]["predicate_type"]["const"],"EXCEPTION")
        self.assertEqual(sch["$defs"]["exception"]["properties"]["condition"]["$ref"],
                         "#/$defs/exceptionCondition")

    def test_C_predicate_types_not_broadened_to_exception(self):
        sch=load(ROOT/"formal"/"candidate_mr_r1_c4_013_patch1.schema.json")
        enum=sch["$defs"]["conditionAtom"]["properties"]["predicate_type"]["enum"]
        self.assertNotIn("EXCEPTION",enum)

    def test_representation_version_not_changed_by_schema_patch(self):
        s,_=spec_for("FIX-AKI-001","INSERT_TRANSIENT_AKI")
        self.assertEqual(s["representation_version"],"CandidateMR-R1.0")

    def test_control_metadata_kept_outside_candidate_spec(self):
        s,control=spec_for("FIX-PENDING-ADMISSION-001","SHIFT_TIME")
        self.assertNotIn("upstream_exception_system_action",s)
        self.assertEqual(control["upstream_exception_system_action"],"ABSTAIN")

    def test_temporal_conflict_id_kept_in_manifest_not_candidate_semantics(self):
        s,control=spec_for("FIX-ORDER-001","SWAP_EQUIVALENT_ORDER")
        self.assertTrue(control["c4_012_conflict_ids"])
        self.assertNotIn("c4_012_conflict_ids",s)

    def test_runtime_fixture_outcomes_do_not_change_generic_E(self):
        s,_=spec_for("FIX-MASK-001","MASK_REQUIRED_OBSERVATION")
        self.assertTrue(s["E"])
        self.assertNotIn("observed_fixture_truth",json.dumps(s))

    def test_all_P_source_knowledge_items_nonempty(self):
        for c in COMPS:
            s,_=spec_for(c["proposition_id"],c["operator_id"])
            self.assertTrue(s["P"]["source_knowledge_item_ids"])

    def test_all_candidate_ids_unique_in_fixture_set(self):
        ids=[]
        for c in COMPS:
            s,_=spec_for(c["proposition_id"],c["operator_id"])
            ids.append(s["candidate_mr_id"])
        self.assertEqual(len(ids),len(set(ids)))

    def test_all_R_families_are_formal(self):
        allowed={
          "EQUALITY_WITHIN_TOLERANCE","MONOTONIC_INCREASE","MONOTONIC_DECREASE",
          "ORDINAL_NONDECREASE","ORDINAL_NONINCREASE","BOUNDED_CHANGE","DECISION_LEVEL"
        }
        for c in COMPS:
            s,_=spec_for(c["proposition_id"],c["operator_id"])
            self.assertIn(s["R"]["relation_family"],allowed)

    def test_aki_candidate_keeps_formal_diagnosis_forbidden_touch(self):
        s,_=spec_for("FIX-AKI-001","INSERT_TRANSIENT_AKI")
        self.assertIn("formal_diagnosis.AKI",s["T"]["forbidden_touch_set"])

    def test_mask_candidate_remains_decision_level(self):
        s,_=spec_for("FIX-MASK-001","MASK_REQUIRED_OBSERVATION")
        self.assertEqual(s["R"]["relation_family"],"DECISION_LEVEL")

    def test_output_relation_selector_is_explicit(self):
        for c in COMPS:
            s,_=spec_for(c["proposition_id"],c["operator_id"])
            self.assertTrue(s["R"]["source_output_selector"])
            self.assertTrue(s["R"]["followup_output_selector"])

    def test_invariant_ids_unique_within_candidate(self):
        for c in COMPS:
            s,_=spec_for(c["proposition_id"],c["operator_id"])
            ids=[x["invariant_id"] for x in s["I"]]
            self.assertEqual(len(ids),len(set(ids)))

    def test_exception_refs_unique_within_candidate(self):
        for c in COMPS:
            s,_=spec_for(c["proposition_id"],c["operator_id"])
            ids=[x["exception_ref"] for x in s["E"]]
            self.assertEqual(len(ids),len(set(ids)))

if __name__=="__main__":
    unittest.main()
