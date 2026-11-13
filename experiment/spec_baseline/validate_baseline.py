"""Pre-mutation control checks for standalone requirement compiler.
The external existing study is used ONLY to supply synthetic test cases and target program.
No generated MRs or generated oracle implementation are used in constructing relations.
"""
import json,sys,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from run_expanded import derive_cases,target,OPS
from baseline import compile_requirements

compiled=compile_requirements()
by_domain={r.domain:r for r in compiled}
assert set(by_domain)==set(OPS)
results=[]
for domain in OPS:
 rel=by_domain[domain]
 for case_no,(source,policy) in enumerate(derive_cases(domain),1):
  try:
   follow=rel.followup(source)
   start=target(domain,source,'reference',policy)
   end=target(domain,follow,'reference',policy)
   verdict=rel.check(start,end)
   status='pass' if verdict is True else 'invalid_reference_pair'
  except Exception as exc:
   status='execution_error';verdict=None;start=None;end=None
   detail=f'{type(exc).__name__}:{exc}'
  else:detail=''
  results.append({'requirement_id':rel.requirement_id,'domain':domain,'case':case_no,'status':status,'source_output':start,'followup_output':end,'error':detail})
summary={'baseline_rules':len(compiled),'cases':len(results),'valid_reference_pairs':sum(x['status']=='pass' for x in results),'invalid_reference_pairs':[{'domain':x['domain'],'case':x['case'],'error':x['error']} for x in results if x['status']!='pass'],'requirements_sha256':hashlib.sha256((P/'requirements.json').read_bytes()).hexdigest(),'baseline_source_sha256':hashlib.sha256((P/'baseline.py').read_bytes()).hexdigest(),'limitations':['Rules were authored in this study and describe known operator domains. Not a blinded externally authored baseline.','Validation uses pre-existing synthetic source cases and target logic.','Does not compare mutation-detection rates or independently establish correctness of requirements.']}
(P/'baseline_precheck.json').write_text(json.dumps({'summary':summary,'case_results':results},indent=2)+'\n')
print(json.dumps(summary,indent=2))
