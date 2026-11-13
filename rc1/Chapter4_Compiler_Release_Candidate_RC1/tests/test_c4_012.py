import json, unittest
from pathlib import Path
from compiler.conflict_io import load_components,load_scopes,load_result_map,load_conflict_evidence
from compiler.output_relation_typing import final_type_relation,relation_compatibility
from compiler.conflict_detection import (
  candidate_key,detect_expected_relation_conflicts,detect_temporal_conflicts,
  records_from_explicit_evidence,detect_duplicates
)
from compiler.conflict_models import TypedOutputRelation,CandidateScope

ROOT=Path(__file__).resolve().parents[1]
COMPS=load_components(ROOT/"fixtures"/"researcher_c4_008_component_generation_results.json")
SCOPES=load_scopes(ROOT/"fixtures"/"c4_012_candidate_scope_registry.json")
INV=load_result_map(ROOT/"fixtures"/"researcher_c4_009_invariant_inference_results.json")
EXC=load_result_map(ROOT/"fixtures"/"researcher_c4_010_exception_precedence_results.json")
TEMP=load_result_map(ROOT/"fixtures"/"researcher_c4_011_temporal_satisfiability_results.json")
TYPED=[final_type_relation(c) for c in COMPS]
TYPED_MAP={candidate_key(x.proposition_id,x.operator_id):x for x in TYPED}

def synthetic(fam,norm,params=None,op="INCREASE_SLOPE",sig="S"):
    return TypedOutputRelation("P",op,"FINAL_TYPED",fam,"out","out","cmp",params or {},"NUMERIC",norm,sig,[])

class C4012Tests(unittest.TestCase):
    def test_researcher_c4_011_upstream_has_12_results(self):
        self.assertEqual(len(TEMP),12)

    def test_all_12_integrated_relations_final_type(self):
        self.assertEqual(sum(x.typing_status=="FINAL_TYPED" for x in TYPED),12)

    def test_equality_absolute_normalizes_to_delta_interval(self):
        x=TYPED_MAP["FIX-TIME-001::SHIFT_TIME"]
        self.assertEqual(x.normalized_constraint["kind"],"NUMERIC_DELTA_INTERVAL")
        self.assertEqual(x.normalized_constraint["lower"],-0.001)
        self.assertEqual(x.normalized_constraint["upper"],0.001)

    def test_mixed_equality_is_parametric_not_falsely_numeric(self):
        x=TYPED_MAP["FIX-UNIT-001::CONVERT_UNIT"]
        self.assertEqual(x.normalized_constraint["kind"],"PARAMETRIC_EQUALITY_TOLERANCE")

    def test_ordinal_ordering_retained(self):
        x=TYPED_MAP["FIX-TRAJ-001::INCREASE_SLOPE"]
        self.assertEqual(x.normalized_constraint["ordering_id"],"risk_low_moderate_high_v1")

    def test_decision_comparator_retained(self):
        x=TYPED_MAP["FIX-MASK-001::MASK_REQUIRED_OBSERVATION"]
        self.assertEqual(x.normalized_constraint["decision_comparator_id"],"safe_missingness_response_v1")

    def test_bounded_change_normalizes_interval(self):
        x=TYPED_MAP["FIX-AKI-001::INSERT_TRANSIENT_AKI"]
        self.assertEqual(x.normalized_constraint["lower"],-1.0)
        self.assertEqual(x.normalized_constraint["upper"],1.0)

    def test_monotonic_increase_synthetic_typing(self):
        c={
          "proposition_id":"S","operator_id":"INCREASE_SLOPE",
          "R":{"status":"GENERATED","relation_family":"MONOTONIC_INCREASE",
               "source_output_selector":"o","followup_output_selector":"o",
               "comparator_id":"c","parameters":{}}
        }
        r=final_type_relation(c)
        self.assertEqual(r.typing_status,"FINAL_TYPED")
        self.assertEqual(r.normalized_constraint["lower"],0.0)

    def test_monotonic_decrease_synthetic_typing(self):
        c={
          "proposition_id":"S","operator_id":"DECREASE_SLOPE",
          "R":{"status":"GENERATED","relation_family":"MONOTONIC_DECREASE",
               "source_output_selector":"o","followup_output_selector":"o",
               "comparator_id":"c","parameters":{}}
        }
        r=final_type_relation(c)
        self.assertEqual(r.typing_status,"FINAL_TYPED")
        self.assertEqual(r.normalized_constraint["upper"],0.0)

    def test_nonstrict_monotonic_up_down_are_not_logically_incompatible(self):
        a=synthetic("MONOTONIC_INCREASE",{"kind":"NUMERIC_DELTA_INTERVAL","lower":0.0,"upper":"INF","strict_change_required":False})
        b=synthetic("MONOTONIC_DECREASE",{"kind":"NUMERIC_DELTA_INTERVAL","lower":"-INF","upper":0.0,"strict_change_required":False})
        self.assertEqual(relation_compatibility(a,b)[0],"TRUE")

    def test_strict_monotonic_up_down_are_incompatible(self):
        a=synthetic("MONOTONIC_INCREASE",{"kind":"NUMERIC_DELTA_INTERVAL","lower":0.0,"upper":"INF","strict_change_required":True})
        b=synthetic("MONOTONIC_DECREASE",{"kind":"NUMERIC_DELTA_INTERVAL","lower":"-INF","upper":0.0,"strict_change_required":True})
        self.assertEqual(relation_compatibility(a,b)[0],"FALSE")

    def test_nonstrict_ordinal_up_down_overlap_at_unchanged_rank(self):
        a=synthetic("ORDINAL_NONDECREASE",{"kind":"ORDINAL_RANK_DELTA","ordering_id":"o","direction":"NONDECREASE","strict_change_required":False})
        b=synthetic("ORDINAL_NONINCREASE",{"kind":"ORDINAL_RANK_DELTA","ordering_id":"o","direction":"NONINCREASE","strict_change_required":False})
        self.assertEqual(relation_compatibility(a,b)[0],"TRUE")

    def test_strict_ordinal_up_down_incompatible(self):
        a=synthetic("ORDINAL_NONDECREASE",{"kind":"ORDINAL_RANK_DELTA","ordering_id":"o","direction":"NONDECREASE","strict_change_required":True})
        b=synthetic("ORDINAL_NONINCREASE",{"kind":"ORDINAL_RANK_DELTA","ordering_id":"o","direction":"NONINCREASE","strict_change_required":True})
        self.assertEqual(relation_compatibility(a,b)[0],"FALSE")

    def test_disjoint_bounded_intervals_incompatible(self):
        a=synthetic("BOUNDED_CHANGE",{"kind":"NUMERIC_DELTA_INTERVAL","lower":1.0,"upper":2.0,"delta_definition":"d"})
        b=synthetic("BOUNDED_CHANGE",{"kind":"NUMERIC_DELTA_INTERVAL","lower":-2.0,"upper":-1.0,"delta_definition":"d"})
        self.assertEqual(relation_compatibility(a,b)[0],"FALSE")

    def test_overlapping_bounded_intervals_compatible(self):
        a=synthetic("BOUNDED_CHANGE",{"kind":"NUMERIC_DELTA_INTERVAL","lower":0.0,"upper":2.0,"delta_definition":"d"})
        b=synthetic("BOUNDED_CHANGE",{"kind":"NUMERIC_DELTA_INTERVAL","lower":1.0,"upper":3.0,"delta_definition":"d"})
        self.assertEqual(relation_compatibility(a,b)[0],"TRUE")

    def test_different_delta_definitions_indeterminate(self):
        a=synthetic("BOUNDED_CHANGE",{"kind":"NUMERIC_DELTA_INTERVAL","lower":0.0,"upper":2.0,"delta_definition":"d1"})
        b=synthetic("BOUNDED_CHANGE",{"kind":"NUMERIC_DELTA_INTERVAL","lower":1.0,"upper":3.0,"delta_definition":"d2"})
        self.assertEqual(relation_compatibility(a,b)[0],"INDETERMINATE")

    def test_cross_transformation_contexts_are_not_compared(self):
        recs=detect_expected_relation_conflicts(TYPED,SCOPES,EXC,TEMP)
        # Current integrated fixtures intentionally declare each different transform as a separate comparison context.
        self.assertEqual(recs,[])

    def test_pending_licensing_candidate_not_used_as_stable_pairwise_comparator(self):
        # FIX-PENDING-ADMISSION and FIX-TIME share SHIFT_TIME context, but licensing block excludes the former.
        recs=detect_expected_relation_conflicts(TYPED,SCOPES,EXC,TEMP)
        self.assertEqual(recs,[])

    def test_temporal_indeterminate_creates_temporal_conflict_record(self):
        recs=detect_temporal_conflicts(TYPED,SCOPES,TEMP)
        keys=[x.involved_candidate_keys for x in recs]
        self.assertIn(["FIX-ORDER-001::SWAP_EQUIVALENT_ORDER"],keys)

    def test_temporal_conflict_abstains(self):
        recs=detect_temporal_conflicts(TYPED,SCOPES,TEMP)
        r=next(x for x in recs if x.involved_candidate_keys==["FIX-ORDER-001::SWAP_EQUIVALENT_ORDER"])
        self.assertEqual(r.system_action,"ABSTAIN")
        self.assertEqual(r.semantic_truth,"INDETERMINATE")
        self.assertEqual(r.conflict_resolved_gate,"Fail")

    def test_conflict_requires_same_target_output(self):
        # Scope registry deliberately separates D1, D2 and D3 targets.
        self.assertNotEqual(SCOPES["FIX-TIME-001::SHIFT_TIME"].target_id,
                            SCOPES["FIX-DELAY-001::DELAY_RESULT_ENTRY"].target_id)

    def test_taxonomy_fixture_has_exactly_10_types(self):
        ev=load_conflict_evidence(ROOT/"fixtures"/"c4_012_conflict_taxonomy_test_cases.json")
        self.assertEqual({x.conflict_type for x in ev},{
          "ExpectedRelationConflict","ApplicabilityConflict","ExceptionConflict","VersionConflict",
          "TerminologyConflict","DataConflict","TemporalConflict","DecisionPolicyConflict",
          "SourceInterpretationConflict","ReviewConflict"
        })

    def test_version_conflict_can_resolve_only_with_release_pinned_winner(self):
        ev=load_conflict_evidence(ROOT/"fixtures"/"c4_012_conflict_taxonomy_test_cases.json")
        recs=records_from_explicit_evidence(ev,{})
        r=next(x for x in recs if x.conflict_type=="VersionConflict")
        self.assertEqual(r.resolution_status,"RESOLVED")
        self.assertEqual(r.resolution_type,"RELEASE_PINNED_NON_SUPERSEDED")

    def test_applicability_conflict_can_resolve_with_explicit_containment(self):
        ev=load_conflict_evidence(ROOT/"fixtures"/"c4_012_conflict_taxonomy_test_cases.json")
        r=next(x for x in records_from_explicit_evidence(ev,{}) if x.conflict_type=="ApplicabilityConflict")
        self.assertEqual(r.resolution_status,"RESOLVED")
        self.assertEqual(r.resolution_type,"EXPLICIT_SCOPE_CONTAINMENT")

    def test_source_interpretation_source_authority_can_resolve(self):
        ev=load_conflict_evidence(ROOT/"fixtures"/"c4_012_conflict_taxonomy_test_cases.json")
        r=next(x for x in records_from_explicit_evidence(ev,{}) if x.conflict_type=="SourceInterpretationConflict")
        self.assertEqual(r.resolution_status,"RESOLVED")
        self.assertEqual(r.resolution_type,"SOURCE_AUTHORITATIVE")

    def test_review_conflict_needs_formal_adjudication(self):
        ev=load_conflict_evidence(ROOT/"fixtures"/"c4_012_conflict_taxonomy_test_cases.json")
        r=next(x for x in records_from_explicit_evidence(ev,{}) if x.conflict_type=="ReviewConflict")
        self.assertEqual(r.resolution_status,"RESOLVED")
        self.assertEqual(r.resolution_type,"FORMAL_ADJUDICATION")
        self.assertTrue(r.adjudication_ref)

    def test_unresolved_expected_relation_conflict_has_no_winner(self):
        ev=load_conflict_evidence(ROOT/"fixtures"/"c4_012_conflict_taxonomy_test_cases.json")
        r=next(x for x in records_from_explicit_evidence(ev,{}) if x.conflict_type=="ExpectedRelationConflict")
        self.assertEqual(r.resolution_status,"UNRESOLVED")
        self.assertIsNone(r.legitimate_winner_key)
        self.assertEqual(r.system_action,"ABSTAIN")

    def test_guideline_strength_never_appears_as_resolution_hint(self):
        ev=load_conflict_evidence(ROOT/"fixtures"/"c4_012_conflict_taxonomy_test_cases.json")
        self.assertTrue(all(x.resolution_hint!="GUIDELINE_STRENGTH" for x in ev))

    def test_lexical_specificity_not_implemented(self):
        txt=(ROOT/"compiler"/"conflict_detection.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("levenshtein",txt)
        self.assertNotIn("string_similarity",txt)

    def test_no_integrated_duplicates(self):
        dups=detect_duplicates(COMPS,TYPED_MAP,INV,EXC,SCOPES)
        self.assertEqual(dups,[])

    def test_synthetic_duplicate_detection(self):
        c=COMPS[0]
        fake1=dict(c); fake1["proposition_id"]="DUP-A"
        fake2=dict(c); fake2["proposition_id"]="DUP-B"
        # Use identical semantic payload but separate IDs/scopes and type records.
        from compiler.conflict_detection import duplicate_signature
        orig=TYPED_MAP[candidate_key(c["proposition_id"],c["operator_id"])]
        s=SCOPES[candidate_key(c["proposition_id"],c["operator_id"])]
        sc1=CandidateScope("DUP-A",c["operator_id"],s.target_id,s.output_id,s.comparison_context_id,s.care_contexts,s.gfr_categories,s.eligibility_states,s.temporal_scope_policy,s.release_lineage,s.release_version,s.source_interpretation_id,s.review_state)
        sc2=CandidateScope("DUP-B",c["operator_id"],s.target_id,s.output_id,s.comparison_context_id,s.care_contexts,s.gfr_categories,s.eligibility_states,s.temporal_scope_policy,s.release_lineage,s.release_version,s.source_interpretation_id,s.review_state)
        # candidate ID itself is intentionally absent from duplicate projection.
        sig1=duplicate_signature(fake1,orig,INV[candidate_key(c["proposition_id"],c["operator_id"])],EXC[candidate_key(c["proposition_id"],c["operator_id"])],sc1)
        sig2=duplicate_signature(fake2,orig,INV[candidate_key(c["proposition_id"],c["operator_id"])],EXC[candidate_key(c["proposition_id"],c["operator_id"])],sc2)
        self.assertEqual(sig1,sig2)

    def test_relation_signatures_repeatable(self):
        a=[final_type_relation(c).relation_signature for c in COMPS]
        b=[final_type_relation(c).relation_signature for c in COMPS]
        self.assertEqual(a,b)

    def test_conflict_ids_repeatable(self):
        a=[x.conflict_id for x in detect_temporal_conflicts(TYPED,SCOPES,TEMP)]
        b=[x.conflict_id for x in detect_temporal_conflicts(TYPED,SCOPES,TEMP)]
        self.assertEqual(a,b)

    def test_seeded_c4_010_conflict_does_not_force_expected_relation_conflict(self):
        # The C4-010 ConflictException was a precedence test control. C4-012 requires
        # the full C3-013 conflict scope to independently prove an actual conflict.
        expected=detect_expected_relation_conflicts(TYPED,SCOPES,EXC,TEMP)
        self.assertFalse(any("FIX-TRAJ-001::DECREASE_SLOPE" in x.involved_candidate_keys for x in expected))

if __name__=="__main__":
    unittest.main()
