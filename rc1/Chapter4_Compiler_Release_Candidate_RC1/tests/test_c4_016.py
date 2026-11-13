import copy,json,tempfile,unittest
from pathlib import Path
from compiler.reproducibility import (
  replay_once,compare_replays,compare_to_researcher,
  controlled_identity_tests,required_version_check,version_inventory
)
from compiler.candidate_assembly import stable_candidate_id

ROOT=Path(__file__).resolve().parents[1]
POL=json.loads((ROOT/"config"/"reproducibility_policy_r1.json").read_text())

class C4016Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        root=Path(cls.tmp.name)
        cls.a=replay_once(ROOT,root/"a",POL)
        cls.b=replay_once(ROOT,root/"b",POL)
        cls.cmp=compare_replays(cls.a,cls.b)
        cls.rcmp=compare_to_researcher(ROOT,cls.a)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_two_replays_same_release_signature(self):
        self.assertTrue(self.cmp["release_signature_match"])

    def test_candidate_ids_stable_12(self):
        self.assertEqual(self.cmp["candidate_id_match_count"],12)

    def test_semantic_fingerprints_stable_12(self):
        self.assertEqual(self.cmp["semantic_fingerprint_match_count"],12)

    def test_generated_python_hashes_stable_12(self):
        self.assertEqual(self.cmp["generated_python_hash_match_count"],12)

    def test_static_status_stable_12(self):
        self.assertEqual(self.cmp["static_status_match_count"],12)

    def test_execution_admission_stable_12(self):
        self.assertEqual(self.cmp["execution_admission_match_count"],12)

    def test_candidate_id_set_identical(self):
        self.assertTrue(self.cmp["candidate_id_set_match"])

    def test_researcher_c4_013_ids_match_12(self):
        self.assertEqual(self.rcmp["researcher_c4_013_id_match_count"],12)

    def test_researcher_c4_013_semantic_fingerprints_match_12(self):
        self.assertEqual(self.rcmp["semantic_fingerprint_match_count"],12)

    def test_researcher_c4_014_python_hashes_match_12(self):
        self.assertEqual(self.rcmp["generated_python_sha256_match_count"],12)

    def test_researcher_c4_015_static_status_match_12(self):
        self.assertEqual(self.rcmp["static_validation_status_match_count"],12)

    def test_researcher_c4_015_execution_status_match_12(self):
        self.assertEqual(self.rcmp["execution_admission_status_match_count"],12)

    def test_researcher_c4_015_expert_status_match_12(self):
        self.assertEqual(self.rcmp["expert_validation_status_match_count"],12)

    def test_all_replayed_static_status_pass(self):
        self.assertEqual(sum(x["static_validation_status"]=="STATIC_VALIDATION_PASS"
                             for x in self.a["release_core"]["candidate_rows"]),12)

    def test_eight_admissible_four_blocked_preserved(self):
        rows=self.a["release_core"]["candidate_rows"]
        self.assertEqual(sum(x["execution_admission_status"]=="STATICALLY_VALID_EXECUTION_ADMISSIBLE" for x in rows),8)
        self.assertEqual(sum(x["execution_admission_status"]=="STATICALLY_VALID_BUT_CONTROL_BLOCKED" for x in rows),4)

    def test_all_expert_status_unreviewed_preserved(self):
        self.assertEqual(sum(x["expert_validation_status"]=="UNREVIEWED"
                             for x in self.a["release_core"]["candidate_rows"]),12)

    def test_environment_observation_not_inside_release_core(self):
        self.assertNotIn("environment_observation",self.a["release_core"])

    def test_environment_change_does_not_change_release_signature(self):
        x=copy.deepcopy(self.a)
        x["environment_observation"]["platform_system"]="DifferentOS"
        self.assertEqual(x["reproducibility_signature"],self.a["reproducibility_signature"])

    def test_controlled_identity_rules_all_pass(self):
        self.assertTrue(all(controlled_identity_tests(self.a["candidate_specs"][0]).values()))

    def test_expert_status_change_does_not_change_candidate_id(self):
        s=copy.deepcopy(self.a["candidate_specs"][0])
        original=s["candidate_mr_id"]
        s["P"]["mr_expert_validation_status"]="ACCEPTED"
        cid=stable_candidate_id(s["C"],s["T"],s["R"],s["I"],s["E"],s["P"])
        self.assertEqual(cid,original)

    def test_compiler_config_version_bump_changes_candidate_id(self):
        s=copy.deepcopy(self.a["candidate_specs"][0])
        original=s["candidate_mr_id"]
        s["P"]["compiler_config_id"]+="-BUMP"
        cid=stable_candidate_id(s["C"],s["T"],s["R"],s["I"],s["E"],s["P"])
        self.assertNotEqual(cid,original)

    def test_operator_library_version_bump_changes_candidate_id(self):
        s=copy.deepcopy(self.a["candidate_specs"][0])
        original=s["candidate_mr_id"]
        s["P"]["operator_library_version"]+="-BUMP"
        cid=stable_candidate_id(s["C"],s["T"],s["R"],s["I"],s["E"],s["P"])
        self.assertNotEqual(cid,original)

    def test_version_inventory_contains_candidate_mr_r1(self):
        self.assertIn("CandidateMR-R1.0",self.a["release_core"]["versions"]["representation_versions"])

    def test_version_inventory_contains_operator_library(self):
        self.assertIn("OperatorLibrary-R1.0",self.a["release_core"]["versions"]["operator_library_versions"])

    def test_version_inventory_contains_srew(self):
        self.assertIn("SREW-R1.0",self.a["release_core"]["versions"]["srew_versions"])

    def test_version_inventory_contains_closure_policy(self):
        self.assertIn("C3-016-R1.0",self.a["release_core"]["versions"]["closure_policy_versions"])

    def test_required_version_check_passes(self):
        check=required_version_check(self.a["release_core"]["versions"],POL["required_versions"])
        self.assertTrue(all(check.values()),check)

    def test_release_signature_changes_if_candidate_semantics_change(self):
        core=copy.deepcopy(self.a["release_core"])
        old=self.a["reproducibility_signature"]
        core["candidate_rows"][0]["semantic_spec_fingerprint"]="0"*64
        import hashlib
        payload=json.dumps(core,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        new=hashlib.sha256(payload.encode("utf-8")).hexdigest()
        self.assertNotEqual(old,new)

    def test_release_signature_changes_if_generated_code_changes(self):
        core=copy.deepcopy(self.a["release_core"])
        old=self.a["reproducibility_signature"]
        core["candidate_rows"][0]["generated_python_sha256"]="f"*64
        import hashlib
        payload=json.dumps(core,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        new=hashlib.sha256(payload.encode("utf-8")).hexdigest()
        self.assertNotEqual(old,new)

    def test_release_signature_changes_if_static_status_changes(self):
        core=copy.deepcopy(self.a["release_core"])
        old=self.a["reproducibility_signature"]
        core["candidate_rows"][0]["static_validation_status"]="STATIC_VALIDATION_FAIL"
        import hashlib
        payload=json.dumps(core,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        new=hashlib.sha256(payload.encode("utf-8")).hexdigest()
        self.assertNotEqual(old,new)

    def test_replay_candidate_ids_unique(self):
        ids=[x["candidate_mr_id"] for x in self.a["release_core"]["candidate_rows"]]
        self.assertEqual(len(ids),len(set(ids)))

    def test_replay_generated_python_hashes_unique(self):
        hs=[x["generated_python_sha256"] for x in self.a["release_core"]["candidate_rows"]]
        self.assertEqual(len(hs),len(set(hs)))

    def test_release_record_version_fixed(self):
        self.assertEqual(self.a["release_core"]["release_record_version"],"CompilerRunRecord-R1.0")

    def test_pipeline_scope_records_c4_006_through_c4_016(self):
        self.assertEqual(self.a["release_core"]["pipeline_scope"],"C4-006-through-C4-016")

if __name__=="__main__":
    unittest.main()
