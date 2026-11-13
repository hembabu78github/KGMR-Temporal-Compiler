"""Task 2 internal evaluation; no publication versions or claims of external blindness."""
import sys, json, csv, hashlib, collections, pathlib, copy
P=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent))
import study as prior
from baseline import compile_requirements
old=prior.old
relations={r.domain:r for r in compile_requirements()}
assert len(relations)==8

cases=[]
for op in old.OPS:
    for ci,(source,policy) in enumerate(old.derive_cases(op),1):
        rel=relations[op]
        independent_follow=rel.followup(source)
        ref_source=old.target(op,source,'reference',policy)
        ref_follow=old.target(op,independent_follow,'reference',policy)
        assert rel.check(ref_source,ref_follow) is True,(op,ci)
        m=old.MODULES[op][0];fixture=old.FIX[op];cfg={}
        if m.SPEC['R']['relation_family'].startswith('ORDINAL'):
            cfg['ordinal_orderings']={'risk_low_moderate_high_v1':old.ORDER}
        if op=='CONVERT_UNIT':
            cfg['unit_conversions']={'UCUM-FIX-001':{'source_unit':'L/min/1.73m2','target_unit':'mL/min/1.73m2','factor':1000.,'offset':0.}}
        reference=m.execute(copy.deepcopy(source),lambda x:old.target(op,x,'reference',policy),execution_context=fixture['execution_context'],oracle_context=fixture['oracle_context'],runtime_config=cfg)
        assert reference['status']=='EXECUTED' and reference['oracle']['truth']=='TRUE'
        cases.append((op,ci,source,policy,independent_follow,reference['followup_case'],m,fixture,cfg))
records=[]
for mid,family,site,fn in prior.mutants:
    for op,ci,source,policy,independent_follow,generated_follow,m,fixture,cfg in cases:
        r=dict(mutant_id=mid,family=family,site=site,operator=op,case=ci,source_case_id=f'{op}:{ci}',baseline_requirement_id=relations[op].requirement_id,baseline_valid=True,generated_valid=True,baseline_detected=False,generated_detected=False,baseline_result='NA',generated_result='NA',error_type='',distinguished=False,identical_followup=independent_follow==generated_follow)
        try:
            s=fn(op,copy.deepcopy(source),'reference',policy)
            b=fn(op,copy.deepcopy(independent_follow),'reference',policy)
            g=fn(op,copy.deepcopy(generated_follow),'reference',policy)
            r['baseline_result']=str(relations[op].check(s,b))
            r['baseline_detected']=relations[op].check(s,b) is False
            gt=m.oracle(s,g,oracle_context=fixture['oracle_context'],runtime_config=cfg)['truth']
            r['generated_result']=gt
            r['generated_detected']=gt=='FALSE'
            r['distinguished']= any((s!=old.target(op,source,'reference',policy),b!=old.target(op,independent_follow,'reference',policy),g!=old.target(op,generated_follow,'reference',policy)))
        except Exception as e:
            r['error_type']=type(e).__name__
        records.append(r)
agg=[]
for mid,family,site,_ in prior.mutants:
    rr=[r for r in records if r['mutant_id']==mid]
    assert len(rr)==24
    agg.append(dict(mutant_id=mid,family=family,site=site,errors=sum(bool(r['error_type']) for r in rr),error_free=all(not r['error_type'] for r in rr),locally_distinguished=any(r['distinguished'] for r in rr),original_kill=any(r['generated_detected'] for r in rr),new_baseline_kill=any(r['baseline_detected'] for r in rr),paired_followups_identical=sum(r['identical_followup'] for r in rr)))
clean_d=[a for a in agg if a['error_free'] and a['locally_distinguished']]
paired=collections.Counter(('both' if a['original_kill'] and a['new_baseline_kill'] else 'original_only' if a['original_kill'] else 'new_only' if a['new_baseline_kill'] else 'neither') for a in clean_d)
summary={
 'study':'V3.4 Task 2, internal unversioned frozen requirements-to-MR baseline comparison',
 'baseline_requirements_sha256':hashlib.sha256((P/'requirements.json').read_bytes()).hexdigest(),
 'baseline_source_sha256':hashlib.sha256((P/'baseline.py').read_bytes()).hexdigest(),
 'mutants':len(agg),'cases':len(cases),'evaluations':len(records),
 'reference_pairs_valid_original':24,'reference_pairs_valid_new_baseline':24,
 'mutants_with_execution_errors':sum(not a['error_free'] for a in agg),
 'mutants_error_free_with_observed_difference':len(clean_d),
 'mutants_error_free_without_observed_difference':sum(a['error_free'] and not a['locally_distinguished'] for a in agg),
 'clean_distinguishable_paired':dict(paired),
 'clean_distinguishable_original_killed':sum(a['original_kill'] for a in clean_d),
 'clean_distinguishable_new_baseline_killed':sum(a['new_baseline_kill'] for a in clean_d),
 'case_pairs_with_identical_followup':sum(c[4]==c[5] for c in cases),
 'mutant_case_rows_with_errors':sum(bool(r['error_type']) for r in records),
 'limitations':['same-study authorship and requirements domains, not blinded or externally developed','same source cases, but transformed followups may differ','behavioral distinguishability only within tested fixture inputs; not global non-equivalence','errors excluded in primary comparison; not automatically counted as kills','synthetic target program, not clinical validation'],
}
for name,items in [('task2_case_results.csv',records),('task2_mutant_classifications.csv',agg)]:
 with (P/name).open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(items[0]));w.writeheader();w.writerows(items)
(P/'task2_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
