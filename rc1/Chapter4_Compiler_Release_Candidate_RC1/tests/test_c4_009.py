import json, unittest
from pathlib import Path
from compiler.invariant_io import load_neighbourhoods, load_c4_008_components
from compiler.invariant_inference import infer_invariants
from compiler.invariant_models import InvariantNeighbourhood

ROOT=Path(__file__).resolve().parents[1]
COMPS=load_c4_008_components(ROOT/"fixtures"/"researcher_c4_008_component_generation_results.json")
NEIGHS=load_neighbourhoods(ROOT/"fixtures"/"c4_009_neighbourhoods.json")
COMP={(x["proposition_id"],x["operator_id"]):x for x in COMPS}

def inf(prop, op):
    return infer_invariants(COMP[(prop,op)],NEIGHS[prop])

class C4009Tests(unittest.TestCase):
    def test_shift_infers_explicit_unaffected_value_and_unit(self):
        r=inf("FIX-TIME-001","SHIFT_TIME")
        sels={x.source_selector for x in r.inferred_invariants}
        self.assertIn("observations[selected].value",sels)
        self.assertIn("observations[selected].unit",sels)

    def test_shift_rejects_touched_effective_time(self):
        r=inf("FIX-TIME-001","SHIFT_TIME")
        self.assertTrue(any(x.selector=="observations[selected].effective_time" and
                            x.reason=="SELECTOR_TOUCHED_BY_TRANSFORMATION"
                            for x in r.rejected_candidates))

    def test_delay_preserves_effective_time_but_not_issued_time(self):
        r=inf("FIX-DELAY-001","DELAY_RESULT_ENTRY")
        sels={x.source_selector for x in r.inferred_invariants}
        self.assertIn("observations[selected].effective_time",sels)
        self.assertNotIn("observations[selected].issued_time",sels)

    def test_mask_preserves_clinical_value_not_availability(self):
        r=inf("FIX-MASK-001","MASK_REQUIRED_OBSERVATION")
        sels={x.source_selector for x in r.inferred_invariants}
        self.assertIn("observations[selected].clinical_value",sels)
        self.assertNotIn("observations[selected].availability",sels)

    def test_swap_preserves_value_and_effective_time_not_sequence(self):
        r=inf("FIX-ORDER-001","SWAP_EQUIVALENT_ORDER")
        sels={x.source_selector for x in r.inferred_invariants}
        self.assertIn("observations[equivalent_set].effective_time",sels)
        self.assertIn("observations[equivalent_set].value",sels)
        self.assertNotIn("observations[equivalent_set].sequence_position",sels)

    def test_remove_redundant_preserves_protected_anchors_and_required_set(self):
        r=inf("FIX-REDUNDANT-001","REMOVE_REDUNDANT_OBSERVATION")
        sels={x.source_selector for x in r.inferred_invariants}
        self.assertIn("trajectory.protected_anchors",sels)
        self.assertIn("required_observations",sels)

    def test_resample_preserves_protected_anchor(self):
        r=inf("FIX-TRAJ-001","RESAMPLE_TRAJECTORY")
        sels={x.source_selector for x in r.inferred_invariants}
        self.assertIn("trajectory.protected_anchors",sels)

    def test_dependency_on_touched_selector_blocks_inference(self):
        r=inf("FIX-TRAJ-001","INCREASE_SLOPE")
        self.assertTrue(any(x.selector=="derived.risk_context" and
                            x.reason=="DEPENDS_ON_TRANSFORMED_SELECTOR"
                            for x in r.rejected_candidates))

    def test_increase_slope_preserves_protected_anchor(self):
        r=inf("FIX-TRAJ-001","INCREASE_SLOPE")
        self.assertIn("trajectory.protected_anchors",{x.source_selector for x in r.inferred_invariants})

    def test_decrease_slope_preserves_protected_anchor(self):
        r=inf("FIX-TRAJ-001","DECREASE_SLOPE")
        self.assertIn("trajectory.protected_anchors",{x.source_selector for x in r.inferred_invariants})

    def test_aki_forbidden_formal_diagnosis_not_inferred_from_silence(self):
        r=inf("FIX-AKI-001","INSERT_TRANSIENT_AKI")
        sels={x.source_selector for x in r.inferred_invariants}
        self.assertNotIn("formal_diagnosis.AKI",sels)
        self.assertIn("subject.id",sels)

    def test_convert_unit_does_not_call_touched_value_or_unit_unaffected(self):
        r=inf("FIX-UNIT-001","CONVERT_UNIT")
        sels={x.source_selector for x in r.inferred_invariants}
        self.assertNotIn("observations[selected].value",sels)
        self.assertNotIn("observations[selected].unit",sels)
        self.assertIn("observations[selected].effective_time",sels)

    def test_preserve_state_infers_explicit_state_signature(self):
        r=inf("FIX-STATE-001","PRESERVE_CLINICAL_STATE")
        clauses={x.source_selector:x for x in r.inferred_invariants}
        self.assertIn("state_defining_fields",clauses)
        self.assertEqual(clauses["state_defining_fields"].comparator_id,"state_signature_equal_v1")

    def test_pending_admission_component_can_have_invariants_without_becoming_admitted(self):
        r=inf("FIX-PENDING-ADMISSION-001","SHIFT_TIME")
        self.assertTrue(r.inferred_invariants)
        # C4-009 does not carry or override final admission status.
        self.assertEqual(r.inference_status,"INVARIANTS_INFERRED")

    def test_no_positive_support_means_no_invariant_even_if_untouched(self):
        comp=COMP[("FIX-AKI-001","INSERT_TRANSIENT_AKI")]
        n=InvariantNeighbourhood.from_obj({
          "proposition_id":"FIX-AKI-001",
          "seed_nodes":["seed"],
          "max_hops":2,
          "release_ref":"fixture:R1",
          "nodes":[
            {"node_id":"seed","selector":"compiler.seed","invariant_type":"STRUCTURE"},
            {"node_id":"x","selector":"some.untouched.field","invariant_type":"VALUE"}
          ],
          "edges":[]
        })
        r=infer_invariants(comp,n)
        self.assertEqual(r.inferred_invariants,[])
        self.assertEqual(r.inference_status,"NO_SUPPORTED_INVARIANTS")

    def test_operator_scoping_on_support_edge(self):
        comp=COMP[("FIX-TIME-001","SHIFT_TIME")]
        n=InvariantNeighbourhood.from_obj({
          "proposition_id":"FIX-TIME-001",
          "seed_nodes":["seed"],
          "max_hops":2,
          "release_ref":"fixture:R1",
          "nodes":[
            {"node_id":"seed","selector":"compiler.seed","invariant_type":"STRUCTURE"},
            {"node_id":"x","selector":"some.untouched.field","invariant_type":"VALUE"}
          ],
          "edges":[{
            "source":"seed","relation":"supports_invariant","target":"x",
            "source_ref":"src","comparator_id":"exact_equal_v1",
            "operators":["CONVERT_UNIT"]
          }]
        })
        r=infer_invariants(comp,n)
        self.assertEqual(r.inferred_invariants,[])

    def test_missing_comparator_rejected(self):
        comp=COMP[("FIX-TIME-001","SHIFT_TIME")]
        n=InvariantNeighbourhood.from_obj({
          "proposition_id":"FIX-TIME-001","seed_nodes":["seed"],"max_hops":2,"release_ref":"R1",
          "nodes":[
            {"node_id":"seed","selector":"compiler.seed","invariant_type":"STRUCTURE"},
            {"node_id":"x","selector":"some.field","invariant_type":"VALUE"}
          ],
          "edges":[{"source":"seed","relation":"supports_invariant","target":"x","source_ref":"src","operators":["SHIFT_TIME"]}]
        })
        r=infer_invariants(comp,n)
        self.assertTrue(any(x.reason=="MISSING_COMPARATOR" for x in r.rejected_candidates))

    def test_invariant_ids_are_repeatable(self):
        a=inf("FIX-TIME-001","SHIFT_TIME")
        b=inf("FIX-TIME-001","SHIFT_TIME")
        self.assertEqual([x.invariant_id for x in a.inferred_invariants],
                         [x.invariant_id for x in b.inferred_invariants])

    def test_invariant_fingerprint_repeatable(self):
        a=inf("FIX-TRAJ-001","RESAMPLE_TRAJECTORY")
        b=inf("FIX-TRAJ-001","RESAMPLE_TRAJECTORY")
        self.assertEqual(a.invariant_fingerprint,b.invariant_fingerprint)

    def test_evidence_records_exist_for_every_inferred_invariant(self):
        for prop,op in COMP:
            if prop in NEIGHS:
                r=inf(prop,op)
                self.assertEqual(len(r.inferred_invariants),len(r.evidence_records))

    def test_every_invariant_has_positive_source_refs(self):
        for prop,op in COMP:
            if prop in NEIGHS:
                r=inf(prop,op)
                for inv in r.inferred_invariants:
                    self.assertTrue(inv.source_refs)

    def test_every_invariant_uses_same_source_and_followup_selector_for_unaffected_inference(self):
        for prop,op in COMP:
            if prop in NEIGHS:
                r=inf(prop,op)
                for inv in r.inferred_invariants:
                    self.assertEqual(inv.source_selector,inv.followup_selector)

if __name__=="__main__":
    unittest.main()
