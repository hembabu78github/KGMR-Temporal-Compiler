import json
import unittest
from pathlib import Path
from compiler.io import load_ir_list, load_json
from compiler.selection import select_operators
from compiler.operator_registry import OPERATOR_REGISTRY

ROOT = Path(__file__).resolve().parents[1]
IR_PATH = ROOT / "fixtures" / "c4_006_ir_test_fixtures.json"
CFG_PATH = ROOT / "config" / "compiler_config_r1.json"

class C4006Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.irs = {x.proposition_id:x for x in load_ir_list(IR_PATH)}
        cls.cfg = load_json(CFG_PATH)

    def sel(self, pid):
        return select_operators(self.irs[pid], self.cfg)

    def test_registry_has_exactly_11_bounded_operators(self):
        self.assertEqual(len(OPERATOR_REGISTRY), 11)
        self.assertEqual([x.operator_id for x in OPERATOR_REGISTRY], [
            "SHIFT_TIME","RESAMPLE_TRAJECTORY","DELAY_RESULT_ENTRY",
            "SWAP_EQUIVALENT_ORDER","REMOVE_REDUNDANT_OBSERVATION",
            "MASK_REQUIRED_OBSERVATION","INCREASE_SLOPE","DECREASE_SLOPE",
            "INSERT_TRANSIENT_AKI","CONVERT_UNIT","PRESERVE_CLINICAL_STATE"
        ])

    def test_shift_time_selected(self):
        r = self.sel("FIX-TIME-001")
        self.assertIn("SHIFT_TIME", r.selected_operators)

    def test_trajectory_emits_all_compatible_operators_in_canonical_order(self):
        r = self.sel("FIX-TRAJ-001")
        self.assertEqual(r.selected_operators, ["RESAMPLE_TRAJECTORY","INCREASE_SLOPE","DECREASE_SLOPE"])

    def test_delay_result_entry_selected(self):
        self.assertIn("DELAY_RESULT_ENTRY", self.sel("FIX-DELAY-001").selected_operators)

    def test_swap_order_selected(self):
        self.assertIn("SWAP_EQUIVALENT_ORDER", self.sel("FIX-ORDER-001").selected_operators)

    def test_remove_redundant_selected(self):
        self.assertIn("REMOVE_REDUNDANT_OBSERVATION", self.sel("FIX-REDUNDANT-001").selected_operators)

    def test_mask_required_requires_decision_level(self):
        r = self.sel("FIX-MASK-001")
        self.assertEqual(r.selected_operators, ["MASK_REQUIRED_OBSERVATION"])
        d = next(x for x in r.operator_decisions if x.operator_id == "MASK_REQUIRED_OBSERVATION")
        self.assertEqual(d.permitted_relations, ["DECISION_LEVEL"])

    def test_aki_identifier_is_aki_like_only(self):
        r = self.sel("FIX-AKI-001")
        self.assertIn("INSERT_TRANSIENT_AKI", r.selected_operators)
        self.assertIn("AKI-like", self.irs["FIX-AKI-001"].notes)

    def test_unit_conversion_selected(self):
        self.assertIn("CONVERT_UNIT", self.sel("FIX-UNIT-001").selected_operators)

    def test_preserve_state_selected(self):
        self.assertIn("PRESERVE_CLINICAL_STATE", self.sel("FIX-STATE-001").selected_operators)

    def test_context_only_is_blocked(self):
        r = self.sel("FIX-CONTEXT-001")
        self.assertEqual(r.selection_status, "BLOCKED")
        self.assertEqual(r.selected_operators, [])
        self.assertEqual(r.admission_status, "INELIGIBLE")

    def test_temporal_indeterminate_rejects_time_shift(self):
        r = self.sel("FIX-INDET-001")
        d = next(x for x in r.operator_decisions if x.operator_id == "SHIFT_TIME")
        self.assertFalse(d.compatible)
        self.assertIn("TEMPORAL_INDETERMINATE", d.reasons)

    def test_pending_release_license_conflict_does_not_prevent_compatibility_assessment(self):
        r = self.sel("FIX-PENDING-ADMISSION-001")
        self.assertIn("SHIFT_TIME", r.selected_operators)
        self.assertEqual(r.admission_status, "PENDING")

    def test_missing_parameter_blocks_parameterization_not_compatibility(self):
        r = self.sel("FIX-MISSING-PARAM-001")
        d = next(x for x in r.operator_decisions if x.operator_id == "CONVERT_UNIT")
        self.assertTrue(d.compatible)
        self.assertFalse(d.parameterized)
        self.assertTrue(any(x.startswith("MISSING_PARAMETER:conversion_id") for x in d.reasons))
        self.assertEqual(r.selection_status, "PARAMETERIZATION_BLOCKED")

    def test_repeat_run_fingerprint_identical(self):
        a = self.sel("FIX-TRAJ-001")
        b = self.sel("FIX-TRAJ-001")
        self.assertEqual(a.selection_fingerprint, b.selection_fingerprint)

if __name__ == "__main__":
    unittest.main()
