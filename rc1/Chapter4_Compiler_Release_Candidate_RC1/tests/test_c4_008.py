import json, unittest
from pathlib import Path
from compiler.component_io import load_component_inputs, load_selection_results
from compiler.component_generation import generate_components
from compiler.precondition_generator import generate_preconditions
from compiler.output_relation_generator import generate_output_relation
from compiler.component_models import ComponentGenerationInput, ConditionAtom, RelationEvidence

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = json.loads((ROOT/"config"/"transformation_contracts_r1.json").read_text())
INPUTS = {x.proposition_id:x for x in load_component_inputs(ROOT/"fixtures"/"c4_008_component_inputs.json")}
SELS = load_selection_results(ROOT/"fixtures"/"c4_006_operator_selection_results.json")

def results(pid):
    return generate_components(INPUTS[pid], SELS[pid], CONTRACTS)

def fake_decision(operator_id, permitted):
    return {
        "operator_id":operator_id,
        "compatible":True,
        "parameterized":True,
        "permitted_relations":list(permitted),
        "bound_parameters":[]
    }

class C4008Tests(unittest.TestCase):
    def test_time_generates_C_T_R(self):
        r=results("FIX-TIME-001")[0]
        self.assertEqual(r.generation_status,"COMPONENTS_GENERATED")
        self.assertEqual(r.T.operator_id,"SHIFT_TIME")
        self.assertEqual(r.R.relation_family,"EQUALITY_WITHIN_TOLERANCE")

    def test_preserve_output_token_normalises_to_formal_equality_when_evidence_supports_it(self):
        r=results("FIX-PENDING-ADMISSION-001")[0]
        self.assertEqual(r.R.relation_family,"EQUALITY_WITHIN_TOLERANCE")

    def test_precondition_order_is_canonical(self):
        c=generate_preconditions(INPUTS["FIX-TIME-001"])
        self.assertEqual(c.expression["children"][0]["predicate_type"],"APPLICABILITY")
        self.assertEqual(c.expression["children"][1]["predicate_type"],"TEMPORAL")

    def test_missing_evidence_policy_is_k3_indeterminate(self):
        c=generate_preconditions(INPUTS["FIX-TIME-001"])
        for child in c.expression["children"]:
            self.assertEqual(child["missing_evidence_result"],"INDETERMINATE")

    def test_trajectory_emits_three_operator_component_results(self):
        rs=results("FIX-TRAJ-001")
        self.assertEqual([x.operator_id for x in rs],["RESAMPLE_TRAJECTORY","INCREASE_SLOPE","DECREASE_SLOPE"])

    def test_trajectory_relation_evidence_is_operator_scoped(self):
        rs={x.operator_id:x for x in results("FIX-TRAJ-001")}
        self.assertEqual(rs["RESAMPLE_TRAJECTORY"].R.relation_family,"ORDINAL_NONDECREASE")
        self.assertEqual(rs["INCREASE_SLOPE"].R.relation_family,"ORDINAL_NONDECREASE")
        self.assertEqual(rs["DECREASE_SLOPE"].R.relation_family,"ORDINAL_NONINCREASE")

    def test_delay_result_entry_touch_set_only_issued_time(self):
        r=results("FIX-DELAY-001")[0]
        self.assertEqual(r.T.touch_set,["observations[selected].issued_time"])
        self.assertIn("observations[selected].effective_time",r.T.forbidden_touch_set)

    def test_swap_order_generated(self):
        self.assertEqual(results("FIX-ORDER-001")[0].T.operator_id,"SWAP_EQUIVALENT_ORDER")

    def test_remove_redundant_generated(self):
        self.assertEqual(results("FIX-REDUNDANT-001")[0].T.operator_id,"REMOVE_REDUNDANT_OBSERVATION")

    def test_mask_is_decision_level(self):
        r=results("FIX-MASK-001")[0]
        self.assertEqual(r.R.relation_family,"DECISION_LEVEL")

    def test_aki_like_does_not_touch_formal_aki_diagnosis(self):
        r=results("FIX-AKI-001")[0]
        self.assertIn("formal_diagnosis.AKI",r.T.forbidden_touch_set)
        self.assertEqual(r.R.relation_family,"BOUNDED_CHANGE")

    def test_convert_unit_generated(self):
        self.assertEqual(results("FIX-UNIT-001")[0].T.operator_id,"CONVERT_UNIT")

    def test_preserve_state_uses_evidence_backed_decision_level_relation(self):
        r=results("FIX-STATE-001")[0]
        self.assertEqual(r.R.relation_family,"DECISION_LEVEL")

    def test_pending_admission_does_not_block_component_generation(self):
        r=results("FIX-PENDING-ADMISSION-001")[0]
        self.assertEqual(r.generation_status,"COMPONENTS_GENERATED")
        self.assertTrue(any("PENDING" in n for n in r.notes))

    def test_component_fingerprint_repeatable(self):
        a=results("FIX-TIME-001")[0].component_fingerprint
        b=results("FIX-TIME-001")[0].component_fingerprint
        self.assertEqual(a,b)

    def test_transformation_parameters_retain_provenance(self):
        r=results("FIX-TIME-001")[0]
        p=r.T.bound_parameters[0]
        self.assertEqual(p["source_kind"],"source_evidence")
        self.assertTrue(p["source_ref"])

    def test_no_operator_composition(self):
        for pid in INPUTS:
            if pid in SELS:
                for r in results(pid):
                    self.assertIsInstance(r.T.operator_id,str)

    def test_all_11_transformation_contracts_exist(self):
        self.assertEqual(len(CONTRACTS),11)

    def test_all_7_relation_families_supported_by_generator_contract(self):
        from compiler.component_models import RELATION_FAMILIES
        self.assertEqual(set(RELATION_FAMILIES),{
            "EQUALITY_WITHIN_TOLERANCE","MONOTONIC_INCREASE","MONOTONIC_DECREASE",
            "ORDINAL_NONDECREASE","ORDINAL_NONINCREASE","BOUNDED_CHANGE","DECISION_LEVEL"
        })

    def test_ordinal_nonincrease_generation_supported(self):
        inp = ComponentGenerationInput(
            proposition_id="ORD-DOWN",
            condition_atoms=[ConditionAtom("P","APPLICABILITY",{},"eval",["src"])],
            relation_evidence=[RelationEvidence(
                "ORDINAL_NONINCREASE","src-r",{"ordering_id":"severity_order_v1"},
                "ordinal_compare_v1","cds.output","cds.output",10,["PRESERVE_CLINICAL_STATE"]
            )],
            source_refs=["src"],graph_path_ids=["path"],release_ref="R1"
        )
        rr=generate_output_relation(inp,fake_decision("PRESERVE_CLINICAL_STATE",["ORDINAL_NONINCREASE"]))
        self.assertEqual(rr.status,"GENERATED")
        self.assertEqual(rr.relation_family,"ORDINAL_NONINCREASE")


    def test_monotonic_increase_generation_supported(self):
        inp = ComponentGenerationInput(
            proposition_id="MON-UP",
            condition_atoms=[ConditionAtom("P","APPLICABILITY",{},"eval",["src"])],
            relation_evidence=[RelationEvidence(
                "MONOTONIC_INCREASE","src-r",{},"numeric_nondecreasing_v1",
                "cds.output","cds.output",10,["INCREASE_SLOPE"]
            )],
            source_refs=["src"],graph_path_ids=["path"],release_ref="R1"
        )
        rr=generate_output_relation(inp,fake_decision("INCREASE_SLOPE",["MONOTONIC_INCREASE"]))
        self.assertEqual(rr.status,"GENERATED")
        self.assertEqual(rr.relation_family,"MONOTONIC_INCREASE")

    def test_monotonic_decrease_generation_supported(self):
        inp = ComponentGenerationInput(
            proposition_id="MON-DOWN",
            condition_atoms=[ConditionAtom("P","APPLICABILITY",{},"eval",["src"])],
            relation_evidence=[RelationEvidence(
                "MONOTONIC_DECREASE","src-r",{},"numeric_nonincreasing_v1",
                "cds.output","cds.output",10,["DECREASE_SLOPE"]
            )],
            source_refs=["src"],graph_path_ids=["path"],release_ref="R1"
        )
        rr=generate_output_relation(inp,fake_decision("DECREASE_SLOPE",["MONOTONIC_DECREASE"]))
        self.assertEqual(rr.status,"GENERATED")
        self.assertEqual(rr.relation_family,"MONOTONIC_DECREASE")

    def test_invalid_equality_without_epsilon_is_rejected(self):
        inp = ComponentGenerationInput(
            proposition_id="BAD-EQ",
            condition_atoms=[ConditionAtom("P","APPLICABILITY",{},"eval",["src"])],
            relation_evidence=[RelationEvidence(
                "EQUALITY_WITHIN_TOLERANCE","src-r",{"tolerance_mode":"absolute"},
                "cmp","cds.output","cds.output",10,[]
            )],
            source_refs=["src"],graph_path_ids=["path"],release_ref="R1"
        )
        rr=generate_output_relation(inp,fake_decision("SHIFT_TIME",["EQUALITY_WITHIN_TOLERANCE"]))
        self.assertEqual(rr.status,"INVALID")

    def test_ordinal_requires_ordering_id(self):
        inp = ComponentGenerationInput(
            proposition_id="BAD-ORD",
            condition_atoms=[ConditionAtom("P","APPLICABILITY",{},"eval",["src"])],
            relation_evidence=[RelationEvidence(
                "ORDINAL_NONINCREASE","src-r",{},"cmp","cds.output","cds.output",10,[]
            )],
            source_refs=["src"],graph_path_ids=["path"],release_ref="R1"
        )
        rr=generate_output_relation(inp,fake_decision("PRESERVE_CLINICAL_STATE",["ORDINAL_NONINCREASE"]))
        self.assertEqual(rr.status,"INVALID")

    def test_bounded_change_requires_bounds(self):
        inp = ComponentGenerationInput(
            proposition_id="BAD-BOUND",
            condition_atoms=[ConditionAtom("P","APPLICABILITY",{},"eval",["src"])],
            relation_evidence=[RelationEvidence(
                "BOUNDED_CHANGE","src-r",{"lower_bound":-1},
                "cmp","cds.output","cds.output",10,[]
            )],
            source_refs=["src"],graph_path_ids=["path"],release_ref="R1"
        )
        rr=generate_output_relation(inp,fake_decision("INSERT_TRANSIENT_AKI",["BOUNDED_CHANGE"]))
        self.assertEqual(rr.status,"INVALID")

    def test_decision_level_requires_comparator(self):
        inp = ComponentGenerationInput(
            proposition_id="BAD-DEC",
            condition_atoms=[ConditionAtom("P","APPLICABILITY",{},"eval",["src"])],
            relation_evidence=[RelationEvidence(
                "DECISION_LEVEL","src-r",{},"cmp","cds.output","cds.output",10,[]
            )],
            source_refs=["src"],graph_path_ids=["path"],release_ref="R1"
        )
        rr=generate_output_relation(inp,fake_decision("MASK_REQUIRED_OBSERVATION",["DECISION_LEVEL"]))
        self.assertEqual(rr.status,"INVALID")

    def test_ambiguous_equal_priority_evidence_is_deferred_to_c4_012(self):
        inp = ComponentGenerationInput(
            proposition_id="AMBIG",
            condition_atoms=[ConditionAtom("P","APPLICABILITY",{},"eval",["src"])],
            relation_evidence=[
                RelationEvidence("MONOTONIC_INCREASE","r1",{},"cmp1","cds.output","cds.output",10,[]),
                RelationEvidence("ORDINAL_NONDECREASE","r2",{"ordering_id":"o"},"cmp2","cds.output","cds.output",10,[])
            ],
            source_refs=["src"],graph_path_ids=["path"],release_ref="R1"
        )
        rr=generate_output_relation(inp,fake_decision("INCREASE_SLOPE",["MONOTONIC_INCREASE","ORDINAL_NONDECREASE"]))
        self.assertEqual(rr.status,"AMBIGUOUS")

if __name__=="__main__":
    unittest.main()
