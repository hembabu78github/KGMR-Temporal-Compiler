import json, unittest
from pathlib import Path
from compiler.exception_io import load_config,load_exception_inputs,load_components,load_invariants
from compiler.exception_precedence import resolve_exception_precedence
from compiler.exception_models import ExceptionEvidence,PrecedenceContext
from compiler.exception_assembly import assemble_exceptions

ROOT=Path(__file__).resolve().parents[1]
CFG=load_config(ROOT/"config"/"exception_precedence_c3_013_r1.json")
EVIDENCE,CONTEXTS=load_exception_inputs(ROOT/"fixtures"/"c4_010_exception_precedence_inputs.json")
COMPS=load_components(ROOT/"fixtures"/"researcher_c4_008_component_generation_results.json")
INVS=load_invariants(ROOT/"fixtures"/"researcher_c4_009_invariant_inference_results.json")
PAIRS={(x["proposition_id"],x["operator_id"]) for x in COMPS}

def res(prop,op):
    return resolve_exception_precedence(prop,op,EVIDENCE,CONTEXTS[(prop,op)],CFG)

class C4010Tests(unittest.TestCase):
    def test_exact_ten_frozen_exception_types(self):
        self.assertEqual(set(CFG["exception_types"]),{
          "ApplicabilityExclusion","DataQualityException","MissingDataException",
          "TemporalPrecisionException","ClinicalEventException","MedicationContextException",
          "TerminologyMappingException","LicensingReleaseException","ReviewGateException",
          "ConflictException"
        })

    def test_exact_p0_p8_tiers(self):
        self.assertEqual([x["tier"] for x in CFG["precedence_tiers"]],
                         [f"P{i}" for i in range(9)])

    def test_every_c4_008_component_has_c4_009_upstream_result(self):
        self.assertTrue(all(k in INVS for k in PAIRS))

    def test_explicit_operator_scope_prevents_unrelated_exception_assembly(self):
        a=assemble_exceptions("FIX-TRAJ-001","INCREASE_SLOPE",EVIDENCE,CFG)
        refs={x.exception_ref for x in a}
        self.assertNotIn("EX-SCOPE-OTHER",refs)
        self.assertNotIn("EX-CONF-001",refs)

    def test_missing_data_abstains(self):
        r=res("FIX-MASK-001","MASK_REQUIRED_OBSERVATION")
        self.assertEqual(r.precedence_outcome,"ABSTAIN")
        self.assertEqual(r.semantic_truth,"INDETERMINATE")
        self.assertEqual(r.system_action,"ABSTAIN")

    def test_temporal_indeterminate_never_coerced_false(self):
        r=res("FIX-ORDER-001","SWAP_EQUIVALENT_ORDER")
        self.assertEqual(r.precedence_outcome,"PENDING")
        self.assertEqual(r.semantic_truth,"INDETERMINATE")
        self.assertNotEqual(r.semantic_truth,"FALSE")

    def test_clinical_event_qualifies_only_linked_scope(self):
        r=res("FIX-AKI-001","INSERT_TRANSIENT_AKI")
        self.assertEqual(r.precedence_outcome,"QUALIFIED")
        self.assertTrue(any("linked segment/window" in n for n in r.notes))

    def test_medication_context_qualifies(self):
        r=res("FIX-TRAJ-001","RESAMPLE_TRAJECTORY")
        self.assertEqual(r.precedence_outcome,"QUALIFIED")

    def test_local_terminology_fallback_can_proceed(self):
        r=res("FIX-UNIT-001","CONVERT_UNIT")
        self.assertIn(r.precedence_outcome,{"PROCEED","QUALIFIED"})
        self.assertTrue(any("local concept" in n for n in r.notes))

    def test_licensing_exception_blocks_release(self):
        r=res("FIX-PENDING-ADMISSION-001","SHIFT_TIME")
        self.assertEqual(r.precedence_outcome,"RELEASE_BLOCKED")
        self.assertEqual(r.system_action,"ABSTAIN")

    def test_false_review_exception_does_not_block(self):
        r=res("FIX-STATE-001","PRESERVE_CLINICAL_STATE")
        self.assertEqual(r.precedence_outcome,"PROCEED")

    def test_false_data_quality_exception_does_not_block(self):
        r=res("FIX-REDUNDANT-001","REMOVE_REDUNDANT_OBSERVATION")
        self.assertEqual(r.precedence_outcome,"PROCEED")

    def test_unresolved_conflict_abstains_and_fails_gate(self):
        r=res("FIX-TRAJ-001","DECREASE_SLOPE")
        self.assertEqual(r.precedence_outcome,"UNRESOLVED")
        self.assertEqual(r.semantic_truth,"INDETERMINATE")
        self.assertEqual(r.system_action,"ABSTAIN")
        self.assertEqual(r.conflict_resolved_gate,"Fail")

    def test_guideline_strength_is_metadata_only(self):
        r=res("FIX-TRAJ-001","INCREASE_SLOPE")
        p6=[x for x in r.trace if x.tier=="P6"]
        self.assertEqual(p6[0].decision,"RECORDED_METADATA_ONLY")
        self.assertTrue(any("not used" in n for n in r.notes))

    def test_specificity_requires_explicit_scope_containment(self):
        r=res("FIX-STATE-001","PRESERVE_CLINICAL_STATE")
        p4=[x for x in r.trace if x.tier=="P4"]
        self.assertEqual(p4[0].decision,"EXPLICIT_SCOPE_CONTAINMENT_AVAILABLE")

    def test_no_lexical_specificity_rule_exists(self):
        text=(ROOT/"compiler"/"exception_precedence.py").read_text(encoding="utf-8")
        self.assertNotIn("string_similarity",text)
        self.assertNotIn("levenshtein",text.lower())

    def test_adjudicated_unresolved_conflict_can_proceed_only_with_record(self):
        c=PrecedenceContext(
          proposition_id="FIX-TRAJ-001",operator_id="DECREASE_SLOPE",
          unresolved_conflict=True,adjudication_status="ADJUDICATED",
          adjudication_ref="adjudication:fixture"
        )
        r=resolve_exception_precedence("FIX-TRAJ-001","DECREASE_SLOPE",EVIDENCE,c,CFG)
        self.assertEqual(r.precedence_outcome,"ADJUDICATED")
        self.assertEqual(r.conflict_resolved_gate,"Pass")

    def test_adjudicated_status_without_record_does_not_resolve(self):
        c=PrecedenceContext(
          proposition_id="FIX-TRAJ-001",operator_id="DECREASE_SLOPE",
          unresolved_conflict=True,adjudication_status="ADJUDICATED",
          adjudication_ref=None
        )
        r=resolve_exception_precedence("FIX-TRAJ-001","DECREASE_SLOPE",EVIDENCE,c,CFG)
        self.assertEqual(r.precedence_outcome,"UNRESOLVED")

    def test_superceded_release_is_ineligible(self):
        c=PrecedenceContext(
          proposition_id="FIX-TIME-001",operator_id="SHIFT_TIME",
          release_lineage_status="SUPERSEDED"
        )
        r=resolve_exception_precedence("FIX-TIME-001","SHIFT_TIME",EVIDENCE,c,CFG)
        self.assertEqual(r.precedence_outcome,"INELIGIBLE")

    def test_ambiguous_version_lineage_abstains_pending(self):
        c=PrecedenceContext(
          proposition_id="FIX-TIME-001",operator_id="SHIFT_TIME",
          release_lineage_status="AMBIGUOUS"
        )
        r=resolve_exception_precedence("FIX-TIME-001","SHIFT_TIME",EVIDENCE,c,CFG)
        self.assertEqual(r.precedence_outcome,"PENDING")
        self.assertEqual(r.system_action,"ABSTAIN")

    def test_applicability_false_means_rule_does_not_fire(self):
        c=PrecedenceContext(
          proposition_id="FIX-TIME-001",operator_id="SHIFT_TIME",
          applicability_truth="FALSE"
        )
        r=resolve_exception_precedence("FIX-TIME-001","SHIFT_TIME",EVIDENCE,c,CFG)
        self.assertEqual(r.precedence_outcome,"NOT_APPLICABLE")
        self.assertEqual(r.system_action,"DO_NOT_FIRE")

    def test_input_integrity_failure_not_clinical_false(self):
        c=PrecedenceContext(
          proposition_id="FIX-TIME-001",operator_id="SHIFT_TIME",
          input_integrity_truth="FALSE"
        )
        r=resolve_exception_precedence("FIX-TIME-001","SHIFT_TIME",EVIDENCE,c,CFG)
        self.assertEqual(r.semantic_truth,"INDETERMINATE")

    def test_invalid_exception_type_is_rejected_structurally(self):
        ev=ExceptionEvidence(
          "X","MadeUpException","FIX-TIME-001",["SHIFT_TIME"],"scope:x",
          "TRUE","cond:x","eval:x",["src:x"],"P2"
        )
        r=resolve_exception_precedence(
          "FIX-TIME-001","SHIFT_TIME",[ev],
          PrecedenceContext("FIX-TIME-001","SHIFT_TIME"),CFG
        )
        self.assertEqual(r.precedence_outcome,"INVALID_INPUT")
        self.assertEqual(r.semantic_truth,"INDETERMINATE")

    def test_exception_missing_provenance_is_invalid(self):
        ev=ExceptionEvidence(
          "X","ClinicalEventException","FIX-TIME-001",["SHIFT_TIME"],"scope:x",
          "TRUE","cond:x","eval:x",[],"P3"
        )
        a=assemble_exceptions("FIX-TIME-001","SHIFT_TIME",[ev],CFG)
        self.assertEqual(a[0].assembly_status,"INVALID")

    def test_nondefault_tier_without_justification_is_invalid(self):
        ev=ExceptionEvidence(
          "X","ClinicalEventException","FIX-TIME-001",["SHIFT_TIME"],"scope:x",
          "TRUE","cond:x","eval:x",["src:x"],"P2"
        )
        a=assemble_exceptions("FIX-TIME-001","SHIFT_TIME",[ev],CFG)
        self.assertEqual(a[0].assembly_status,"INVALID")

    def test_repeat_fingerprint_identical(self):
        a=res("FIX-AKI-001","INSERT_TRANSIENT_AKI")
        b=res("FIX-AKI-001","INSERT_TRANSIENT_AKI")
        self.assertEqual(a.exception_fingerprint,b.exception_fingerprint)

    def test_trace_is_ordered_by_p_tier(self):
        for prop,op in PAIRS:
            r=res(prop,op)
            nums=[int(x.tier[1:]) for x in r.trace]
            self.assertEqual(nums,sorted(nums))

    def test_c4_010_does_not_detect_cross_candidate_conflicts(self):
        # Cross-candidate conflict detection is deliberately deferred to C4-012.
        text=(ROOT/"docs"/"C4_010_IMPLEMENTATION_NOTES.md").read_text(encoding="utf-8")
        self.assertIn("C4-012",text)

if __name__=="__main__":
    unittest.main()
