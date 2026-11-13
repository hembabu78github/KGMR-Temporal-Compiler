import json,unittest
from pathlib import Path
from compiler.temporal_io import load_temporal_cases,load_components,load_precedence_results
from compiler.temporal_models import TemporalEntity,TemporalConstraint,TemporalCase
from compiler.temporal_satisfiability import (
  check_temporal_satisfiability,detect_static_constraint_conflicts,evaluate_constraint
)
from compiler.temporal_time import parse_utc,add_calendar_duration
from compiler.temporal_eval import eval_relation,eval_duration,eval_within_horizon,eval_persists_for

ROOT=Path(__file__).resolve().parents[1]
CASES=load_temporal_cases(ROOT/"fixtures"/"c4_011_temporal_cases.json")
COMPS=load_components(ROOT/"fixtures"/"researcher_c4_008_component_generation_results.json")
PREC=load_precedence_results(ROOT/"fixtures"/"researcher_c4_010_exception_precedence_results.json")
COMP={(x["proposition_id"],x["operator_id"]):x for x in COMPS}

def result(prop,op):
    return check_temporal_satisfiability(COMP[(prop,op)],PREC[(prop,op)],CASES[prop])

def ent(eid,kind,domain,s0,s1,e0=None,e1=None,precision="exact"):
    return TemporalEntity(eid,kind,domain,s0,s1,e0,e1,precision,None,["src"])

class C4011Tests(unittest.TestCase):
    def test_researcher_c4_010_upstream_has_12_components(self):
        self.assertEqual(len(PREC),12)

    def test_explicit_offsets_normalize_to_same_utc(self):
        a=parse_utc("2026-01-01T10:00:00-05:00")
        b=parse_utc("2026-01-01T15:00:00Z")
        self.assertEqual(a,b)

    def test_calendar_year_from_leap_day_clips_correctly(self):
        a=parse_utc("2024-02-29T10:00:00Z")
        self.assertEqual(add_calendar_duration(a,"P1Y").isoformat(),
                         "2025-02-28T10:00:00+00:00")

    def test_calendar_two_year_horizon_true(self):
        a=ent("a","INSTANT","clinical","2025-02-28T10:00:00Z","2025-02-28T10:00:00Z")
        b=ent("b","INSTANT","clinical","2024-02-29T10:00:00Z","2024-02-29T10:00:00Z")
        t,_=eval_within_horizon(a,b,"P2Y")
        self.assertEqual(t,"TRUE")

    def test_half_open_meets_is_not_before(self):
        a=ent("a","INTERVAL","clinical","2026-01-01T00:00:00Z","2026-01-01T00:00:00Z",
              "2026-01-02T00:00:00Z","2026-01-02T00:00:00Z")
        b=ent("b","INTERVAL","clinical","2026-01-02T00:00:00Z","2026-01-02T00:00:00Z",
              "2026-01-03T00:00:00Z","2026-01-03T00:00:00Z")
        self.assertEqual(eval_relation(a,b,"meets")[0],"TRUE")
        self.assertEqual(eval_relation(a,b,"before")[0],"FALSE")

    def test_half_open_adjacent_event_windows_do_not_overlap(self):
        a=ent("a","INTERVAL","clinical","2026-01-01T00:00:00Z","2026-01-01T00:00:00Z",
              "2026-01-02T00:00:00Z","2026-01-02T00:00:00Z")
        b=ent("b","INTERVAL","clinical","2026-01-02T00:00:00Z","2026-01-02T00:00:00Z",
              "2026-01-03T00:00:00Z","2026-01-03T00:00:00Z")
        self.assertEqual(eval_relation(a,b,"overlapsEventWindow")[0],"FALSE")

    def test_uncertain_before_can_be_indeterminate(self):
        a=ent("a","UNCERTAIN_INSTANT","clinical","2026-01-01T00:00:00Z","2026-01-03T00:00:00Z")
        b=ent("b","UNCERTAIN_INSTANT","clinical","2026-01-02T00:00:00Z","2026-01-04T00:00:00Z")
        self.assertEqual(eval_relation(a,b,"before")[0],"INDETERMINATE")

    def test_missing_time_is_indeterminate_not_false(self):
        a=ent("a","UNCERTAIN_INSTANT","clinical",None,None)
        b=ent("b","INSTANT","clinical","2026-01-01T00:00:00Z","2026-01-01T00:00:00Z")
        self.assertEqual(eval_relation(a,b,"before")[0],"INDETERMINATE")

    def test_same_clinical_time_same_precision_true(self):
        a=ent("a","UNCERTAIN_INSTANT","clinical","2026-01-01T00:00:00Z","2026-01-01T23:59:59Z",precision="date")
        b=ent("b","UNCERTAIN_INSTANT","clinical","2026-01-01T00:00:00Z","2026-01-01T23:59:59Z",precision="date")
        self.assertEqual(eval_relation(a,b,"sameClinicalTime")[0],"TRUE")

    def test_same_clinical_time_mixed_precision_indeterminate(self):
        r=result("FIX-ORDER-001","SWAP_EQUIVALENT_ORDER")
        self.assertEqual(r.temporal_truth,"INDETERMINATE")
        self.assertEqual(r.system_action,"ABSTAIN")

    def test_90_day_confirmation_true(self):
        a=ent("a","INSTANT","clinical","2026-04-15T00:00:00Z","2026-04-15T00:00:00Z")
        b=ent("b","INSTANT","clinical","2026-01-01T00:00:00Z","2026-01-01T00:00:00Z")
        self.assertEqual(eval_duration(a,b,"AT_LEAST","P90D")[0],"TRUE")

    def test_90_day_confirmation_false(self):
        a=ent("a","INSTANT","clinical","2026-03-01T00:00:00Z","2026-03-01T00:00:00Z")
        b=ent("b","INSTANT","clinical","2026-01-01T00:00:00Z","2026-01-01T00:00:00Z")
        self.assertEqual(eval_duration(a,b,"AT_LEAST","P90D")[0],"FALSE")

    def test_two_week_uncertainty_can_be_indeterminate(self):
        a=ent("a","UNCERTAIN_INSTANT","clinical","2026-01-10T00:00:00Z","2026-01-20T00:00:00Z")
        b=ent("b","INSTANT","clinical","2026-01-01T00:00:00Z","2026-01-01T00:00:00Z")
        from compiler.temporal_eval import eval_within
        self.assertEqual(eval_within(a,b,"P14D")[0],"INDETERMINATE")

    def test_one_year_persistence_calendar_true(self):
        a=ent("a","INTERVAL","clinical","2024-02-29T00:00:00Z","2024-02-29T00:00:00Z",
              "2025-03-01T00:00:00Z","2025-03-01T00:00:00Z")
        self.assertEqual(eval_persists_for(a,"P1Y")[0],"TRUE")

    def test_static_duration_contradiction_detected(self):
        rows=[
          TemporalConstraint("c1","AT_LEAST","A","B","P90D","clinical",["s1"]),
          TemporalConstraint("c2","AT_MOST","A","B","P14D","clinical",["s2"])
        ]
        conflicts=detect_static_constraint_conflicts(rows)
        self.assertTrue(any(x.startswith("INCOMPATIBLE_DURATION_BOUNDS") for x in conflicts))

    def test_static_relation_contradiction_detected(self):
        rows=[
          TemporalConstraint("c1","before","A","B",None,"clinical",["s1"]),
          TemporalConstraint("c2","after","A","B",None,"clinical",["s2"])
        ]
        conflicts=detect_static_constraint_conflicts(rows)
        self.assertTrue(any(x.startswith("INCOMPATIBLE_RELATIONS") for x in conflicts))

    def test_temporally_unsatisfiable_structural_conflict_rejects_candidate(self):
        c=TemporalCase(
          "FIX-TIME-001",
          [ent("A","INSTANT","clinical","2026-04-15T00:00:00Z","2026-04-15T00:00:00Z"),
           ent("B","INSTANT","clinical","2026-01-01T00:00:00Z","2026-01-01T00:00:00Z")],
          [
            TemporalConstraint("c1","AT_LEAST","A","B","P90D","clinical",["s1"]),
            TemporalConstraint("c2","AT_MOST","A","B","P14D","clinical",["s2"])
          ],"R1"
        )
        r=check_temporal_satisfiability(
          COMP[("FIX-TIME-001","SHIFT_TIME")],PREC[("FIX-TIME-001","SHIFT_TIME")],c
        )
        self.assertEqual(r.temporal_status,"TEMPORALLY_UNSATISFIABLE")
        self.assertEqual(r.temporal_truth,"FALSE")
        self.assertEqual(r.system_action,"REJECT_CANDIDATE")

    def test_clinical_constraint_cannot_use_availability_entity(self):
        e=ent("issued","INSTANT","availability","2026-01-01T00:00:00Z","2026-01-01T00:00:00Z")
        c=TemporalConstraint("x","AT_LEAST","issued","issued","P1D","clinical",["src"])
        r=evaluate_constraint(c,{"issued":e})
        self.assertEqual(r.truth,"INDETERMINATE")
        self.assertIn("TIME_DOMAIN_MISMATCH",r.reason)

    def test_time_shift_fixture_true(self):
        r=result("FIX-TIME-001","SHIFT_TIME")
        self.assertEqual(r.temporal_status,"TEMPORALLY_SATISFIABLE")
        self.assertEqual(r.temporal_truth,"TRUE")

    def test_aki_like_temporal_fixture_true(self):
        r=result("FIX-AKI-001","INSERT_TRANSIENT_AKI")
        self.assertEqual(r.temporal_truth,"TRUE")

    def test_trajectory_all_three_operators_share_true_temporal_contract(self):
        for op in ["RESAMPLE_TRAJECTORY","INCREASE_SLOPE","DECREASE_SLOPE"]:
            r=result("FIX-TRAJ-001",op)
            self.assertEqual(r.temporal_truth,"TRUE")

    def test_upstream_unresolved_conflict_remains_abstain_even_if_temporally_true(self):
        r=result("FIX-TRAJ-001","DECREASE_SLOPE")
        self.assertEqual(r.temporal_truth,"TRUE")
        self.assertEqual(r.system_action,"ABSTAIN")

    def test_upstream_licensing_block_remains_abstain_even_if_temporally_true(self):
        r=result("FIX-PENDING-ADMISSION-001","SHIFT_TIME")
        self.assertEqual(r.temporal_truth,"TRUE")
        self.assertEqual(r.system_action,"ABSTAIN")

    def test_no_temporal_constraints_is_vacuously_true(self):
        r=result("FIX-STATE-001","PRESERVE_CLINICAL_STATE")
        self.assertEqual(r.temporal_truth,"TRUE")
        self.assertTrue(any("vacuously" in n for n in r.notes))

    def test_open_interval_end_dependent_relation_indeterminate(self):
        a=ent("a","OPEN_INTERVAL","clinical","2026-01-01T00:00:00Z","2026-01-01T00:00:00Z",None,None)
        b=ent("b","INTERVAL","clinical","2026-02-01T00:00:00Z","2026-02-01T00:00:00Z",
              "2026-03-01T00:00:00Z","2026-03-01T00:00:00Z")
        self.assertEqual(eval_relation(a,b,"before")[0],"INDETERMINATE")

    def test_nonpositive_half_open_interval_is_invalid_input(self):
        bad=TemporalCase(
          "FIX-TIME-001",
          [ent("x","INTERVAL","clinical","2026-01-01T00:00:00Z","2026-01-01T00:00:00Z",
               "2026-01-01T00:00:00Z","2026-01-01T00:00:00Z")],
          [],"R1"
        )
        r=check_temporal_satisfiability(
          COMP[("FIX-TIME-001","SHIFT_TIME")],PREC[("FIX-TIME-001","SHIFT_TIME")],bad
        )
        self.assertEqual(r.temporal_status,"INVALID_TEMPORAL_INPUT")
        self.assertEqual(r.temporal_truth,"INDETERMINATE")

    def test_naive_datetime_rejected_as_invalid_input(self):
        bad=TemporalCase(
          "FIX-TIME-001",
          [ent("x","INSTANT","clinical","2026-01-01T00:00:00","2026-01-01T00:00:00")],
          [],"R1"
        )
        r=check_temporal_satisfiability(
          COMP[("FIX-TIME-001","SHIFT_TIME")],PREC[("FIX-TIME-001","SHIFT_TIME")],bad
        )
        self.assertEqual(r.temporal_status,"INVALID_TEMPORAL_INPUT")

    def test_temporal_fingerprint_repeatable(self):
        a=result("FIX-AKI-001","INSERT_TRANSIENT_AKI")
        b=result("FIX-AKI-001","INSERT_TRANSIENT_AKI")
        self.assertEqual(a.temporal_fingerprint,b.temporal_fingerprint)

    def test_temporal_scope_hull_emitted_for_clinical_evidence(self):
        r=result("FIX-TIME-001","SHIFT_TIME")
        self.assertIsNotNone(r.temporal_scope_hull["earliest_clinical_time"])
        self.assertIsNotNone(r.temporal_scope_hull["latest_clinical_time"])
        self.assertEqual(r.temporal_scope_hull["boundary"],"[start,end)")

    def test_allen_relation_vocabulary_is_frozen(self):
        cfg=json.loads((ROOT/"config"/"temporal_grammar_c3_009_r1.json").read_text())
        self.assertEqual(len(cfg["relation_set"]),16)

    def test_duration_operator_vocabulary_is_frozen(self):
        cfg=json.loads((ROOT/"config"/"temporal_grammar_c3_009_r1.json").read_text())
        self.assertEqual(set(cfg["duration_window_operators"]),{
          "WITHIN","AT_LEAST","AT_MOST","PERSISTS_FOR",
          "OCCURS_DURING","OVERLAPS","WITHIN_HORIZON"
        })

if __name__=="__main__":
    unittest.main()
