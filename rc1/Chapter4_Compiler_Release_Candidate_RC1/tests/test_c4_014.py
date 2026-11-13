import copy,json,unittest,tempfile,py_compile
from pathlib import Path
from runtime.executable_runtime import apply_transformation,evaluate_oracle,execute_mr
from compiler.python_codegen import generate_modules,derive_control,semantic_fp

ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/"config"/"executable_runtime_r1.json").read_text())
MAN=json.loads((ROOT/"fixtures"/"researcher_c4_013_candidate_manifest.json").read_text())["candidates"]
CASES={x["candidate_key"]:x for x in json.loads((ROOT/"fixtures"/"c4_014_execution_cases.json").read_text())["cases"]}
SPECS={m["candidate_key"]:json.loads((ROOT/"fixtures"/"c4_013_candidate_specs"/f"{m['candidate_mr_id']}.json").read_text()) for m in MAN}

class C4014Tests(unittest.TestCase):
    def test_manifest_semantic_fingerprints_12(self):
        self.assertEqual(sum(semantic_fp(SPECS[m["candidate_key"]])==m["semantic_spec_fingerprint"] for m in MAN),12)

    def test_all_11_operators_present(self):
        self.assertEqual(len({s["T"]["operator_id"] for s in SPECS.values()}),11)

    def test_shift_time(self):
        k="FIX-TIME-001::SHIFT_TIME"; src=copy.deepcopy(CASES[k]["source_case"])
        out=apply_transformation(SPECS[k],src,CASES[k]["execution_context"],CFG)
        self.assertEqual(out["observations"][0]["effective_time"],"2024-06-22T10:00:00Z")
        self.assertEqual(src,CASES[k]["source_case"])

    def test_delay_result_entry(self):
        k="FIX-DELAY-001::DELAY_RESULT_ENTRY"; src=copy.deepcopy(CASES[k]["source_case"])
        out=apply_transformation(SPECS[k],src,CASES[k]["execution_context"],CFG)
        self.assertEqual(out["observations"][0]["effective_time"],src["observations"][0]["effective_time"])
        self.assertEqual(out["observations"][0]["issued_time"],"2026-02-05T14:00:00Z")

    def test_swap_order(self):
        k="FIX-ORDER-001::SWAP_EQUIVALENT_ORDER"
        out=apply_transformation(SPECS[k],CASES[k]["source_case"],CASES[k]["execution_context"],CFG)
        self.assertEqual(out["observation_order"],["b","a"])

    def test_remove_redundant(self):
        k="FIX-REDUNDANT-001::REMOVE_REDUNDANT_OBSERVATION"
        out=apply_transformation(SPECS[k],CASES[k]["source_case"],{},CFG)
        self.assertNotIn("obs_non_anchor_3",{x["id"] for x in out["observations"]})

    def test_remove_protected_refused(self):
        k="FIX-REDUNDANT-001::REMOVE_REDUNDANT_OBSERVATION"; s=copy.deepcopy(SPECS[k])
        for p in s["T"]["bound_parameters"]:
            if p["name"]=="redundancy_key": p["value"]="anchor"
        with self.assertRaises(ValueError):
            apply_transformation(s,CASES[k]["source_case"],{},CFG)

    def test_mask_required(self):
        k="FIX-MASK-001::MASK_REQUIRED_OBSERVATION"
        out=apply_transformation(SPECS[k],CASES[k]["source_case"],{},CFG)
        self.assertFalse(out["observations"][0]["available"])
        self.assertEqual(out["observations"][0]["value"],45.0)

    def test_resample_retains_anchors(self):
        k="FIX-TRAJ-001::RESAMPLE_TRAJECTORY"
        out=apply_transformation(SPECS[k],CASES[k]["source_case"],{},CFG)
        ids={x["id"] for x in out["observations"]}
        self.assertIn("a",ids); self.assertIn("e",ids)
        self.assertLess(len(out["observations"]),5)

    def test_increase_slope_preserves_anchor(self):
        k="FIX-TRAJ-001::INCREASE_SLOPE"; src=CASES[k]["source_case"]
        out=apply_transformation(SPECS[k],src,{},CFG)
        self.assertEqual(out["observations"][0]["value"],src["observations"][0]["value"])
        self.assertGreater(out["observations"][2]["value"],src["observations"][2]["value"])

    def test_decrease_slope_preserves_anchor(self):
        k="FIX-TRAJ-001::DECREASE_SLOPE"; src=CASES[k]["source_case"]
        out=apply_transformation(SPECS[k],src,{},CFG)
        self.assertEqual(out["observations"][0]["value"],src["observations"][0]["value"])
        self.assertLess(out["observations"][2]["value"],src["observations"][2]["value"])

    def test_aki_like_no_formal_diagnosis(self):
        k="FIX-AKI-001::INSERT_TRANSIENT_AKI"
        out=apply_transformation(SPECS[k],CASES[k]["source_case"],{},CFG)
        new=[x for x in out["observations"] if str(x["id"]).startswith("mr_aki_like_")]
        self.assertEqual(len(new),2)
        self.assertTrue(all(x["formal_diagnosis_AKI"] is False for x in new))

    def test_unit_conversion(self):
        k="FIX-UNIT-001::CONVERT_UNIT"
        out=apply_transformation(SPECS[k],CASES[k]["source_case"],CASES[k]["execution_context"],CFG)
        self.assertAlmostEqual(out["observations"][0]["value"],90.0)
        self.assertEqual(out["observations"][0]["unit"],"mL/min/1.73m2")

    def test_preserve_state(self):
        k="FIX-STATE-001::PRESERVE_CLINICAL_STATE"; src=CASES[k]["source_case"]
        out=apply_transformation(SPECS[k],src,CASES[k]["execution_context"],CFG)
        self.assertEqual(out["state_defining_fields"],src["state_defining_fields"])
        self.assertNotEqual(out["non_state_auxiliary_field"],src["non_state_auxiliary_field"])

    def test_all_sources_immutable(self):
        for k,s in SPECS.items():
            src=copy.deepcopy(CASES[k]["source_case"]); before=copy.deepcopy(src)
            apply_transformation(s,src,CASES[k].get("execution_context",{}),CFG)
            self.assertEqual(src,before,k)

    def test_equality_oracle(self):
        s=SPECS["FIX-TIME-001::SHIFT_TIME"]
        self.assertEqual(evaluate_oracle(s,1.0,1.0005,{},CFG)["truth"],"TRUE")
        self.assertEqual(evaluate_oracle(s,1.0,1.01,{},CFG)["truth"],"FALSE")

    def test_ordinal_up_oracle(self):
        s=SPECS["FIX-TRAJ-001::INCREASE_SLOPE"]
        self.assertEqual(evaluate_oracle(s,"moderate","high",{},CFG)["truth"],"TRUE")

    def test_ordinal_down_oracle(self):
        s=SPECS["FIX-TRAJ-001::DECREASE_SLOPE"]
        self.assertEqual(evaluate_oracle(s,"high","moderate",{},CFG)["truth"],"TRUE")

    def test_bounded_oracle(self):
        s=SPECS["FIX-AKI-001::INSERT_TRANSIENT_AKI"]
        self.assertEqual(evaluate_oracle(s,1.0,1.5,{},CFG)["truth"],"TRUE")
        self.assertEqual(evaluate_oracle(s,1.0,3.0,{},CFG)["truth"],"FALSE")

    def test_missingness_oracle(self):
        s=SPECS["FIX-MASK-001::MASK_REQUIRED_OBSERVATION"]
        self.assertEqual(evaluate_oracle(s,"NO_REFERRAL","ABSTAIN",{"required_observation_available":False},CFG)["truth"],"TRUE")

    def test_delay_oracle_preserve(self):
        s=SPECS["FIX-DELAY-001::DELAY_RESULT_ENTRY"]
        self.assertEqual(evaluate_oracle(s,"M3","M3",{"available_at_decision":True},CFG)["truth"],"TRUE")

    def test_delay_oracle_abstain_unavailable(self):
        s=SPECS["FIX-DELAY-001::DELAY_RESULT_ENTRY"]
        self.assertEqual(evaluate_oracle(s,"M3","ABSTAIN",{"available_at_decision":False},CFG)["truth"],"TRUE")

    def test_preserve_decision_oracle(self):
        s=SPECS["FIX-STATE-001::PRESERVE_CLINICAL_STATE"]
        self.assertEqual(evaluate_oracle(s,"M3","M3",{},CFG)["truth"],"TRUE")

    def test_missing_output_indeterminate(self):
        s=SPECS["FIX-TIME-001::SHIFT_TIME"]
        self.assertEqual(evaluate_oracle(s,None,1.0,{},CFG)["truth"],"INDETERMINATE")

    def test_control_proceed(self):
        m=next(x for x in MAN if x["candidate_key"]=="FIX-TIME-001::SHIFT_TIME")
        self.assertEqual(derive_control(m)["execution_gate"],"PROCEED")

    def test_control_abstain_licensing(self):
        m=next(x for x in MAN if x["candidate_key"]=="FIX-PENDING-ADMISSION-001::SHIFT_TIME")
        self.assertEqual(derive_control(m)["execution_gate"],"ABSTAIN")

    def test_control_abstain_temporal_conflict(self):
        m=next(x for x in MAN if x["candidate_key"]=="FIX-ORDER-001::SWAP_EQUIVALENT_ORDER")
        c=derive_control(m)
        self.assertEqual(c["execution_gate"],"ABSTAIN")
        self.assertTrue(any("C4_012" in x for x in c["blocking_reasons"]))

    def test_blocked_execute_never_calls_cds(self):
        k="FIX-PENDING-ADMISSION-001::SHIFT_TIME"; m=next(x for x in MAN if x["candidate_key"]==k)
        calls={"n":0}
        def cds(_): calls["n"]+=1; return 1.0
        r=execute_mr(SPECS[k],derive_control(m),CASES[k]["source_case"],cds,CASES[k]["execution_context"],{},CFG)
        self.assertEqual(r["status"],"ABSTAIN"); self.assertEqual(calls["n"],0)

    def test_admitted_execute_calls_twice(self):
        k="FIX-TIME-001::SHIFT_TIME"; m=next(x for x in MAN if x["candidate_key"]==k)
        calls={"n":0}
        def cds(_): calls["n"]+=1; return 0.2
        r=execute_mr(SPECS[k],derive_control(m),CASES[k]["source_case"],cds,CASES[k]["execution_context"],{},CFG)
        self.assertEqual(r["status"],"EXECUTED"); self.assertEqual(calls["n"],2); self.assertEqual(r["oracle"]["truth"],"TRUE")

    def test_codegen_12_compile(self):
        with tempfile.TemporaryDirectory() as td:
            rows=generate_modules(ROOT/"fixtures"/"c4_013_candidate_specs",MAN,td)
            self.assertEqual(len(rows),12)
            for r in rows: py_compile.compile(str(Path(td)/r["module_path"]),doraise=True)

    def test_codegen_deterministic_hashes(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            ra=generate_modules(ROOT/"fixtures"/"c4_013_candidate_specs",MAN,a)
            rb=generate_modules(ROOT/"fixtures"/"c4_013_candidate_specs",MAN,b)
            self.assertEqual([x["generated_python_sha256"] for x in ra],[x["generated_python_sha256"] for x in rb])

if __name__=="__main__":
    unittest.main()
