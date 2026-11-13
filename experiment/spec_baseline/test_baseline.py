import copy, tempfile, json, unittest
from pathlib import Path
from baseline import compile_requirements,ConstructionFailure
class TestBaseline(unittest.TestCase):
 def setUp(self):
  self.rels=compile_requirements();self.by={r.domain:r for r in self.rels}
 def test_eight_distinct_requirements(self):
  self.assertEqual(len(self.rels),8)
  self.assertEqual(len(set(x.requirement_id for x in self.rels)),8)
 def test_datetime_shift_and_no_source_mutation(self):
  src={'observations':[{'issued_time':'2026-01-01T00:00:00Z'}]};snapshot=copy.deepcopy(src)
  fu=self.by['DELAY_RESULT_ENTRY'].followup(src)
  self.assertEqual(src,snapshot)
  self.assertEqual(fu['observations'][0]['issued_time'],'2026-01-04T00:00:00Z')
 def test_guard_unknown_outputs(self):
  self.assertIsNone(self.by['CONVERT_UNIT'].check(None,4.0))
  self.assertIsNone(self.by['CONVERT_UNIT'].check('wrong',4.0))
 def test_oracle_true_false(self):
  self.assertTrue(self.by['PRESERVE_CLINICAL_STATE'].check('G3','G3'))
  self.assertFalse(self.by['PRESERVE_CLINICAL_STATE'].check('G3','G4'))
 def test_invalid_spec_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'bad.json'
   p.write_text(json.dumps({'requirements':[{'id':'x','domain':'x','requirement':'x','transformation':{'method':'arbitrary_python'},'oracle':{'kind':'same_output'}}]}))
   with self.assertRaises(ConstructionFailure):compile_requirements(p)
if __name__=='__main__':unittest.main()
