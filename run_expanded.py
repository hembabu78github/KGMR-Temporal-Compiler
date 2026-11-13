#!/usr/bin/env python3
"""Controlled synthetic mutation study using unmodified RC1 generated CandidateMR modules.
Mutation operators affect only synthetic target programs. No clinical validity claims.
"""
import sys,json,csv,hashlib,platform,importlib.util,copy,zipfile
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent
RC1=ROOT/'rc1/Chapter4_Compiler_Release_Candidate_RC1'
sys.path.insert(0,str(RC1))
F=json.loads((RC1/'fixtures/c4_014_execution_cases.json').read_text())['cases']
MODULES={}
for path in sorted((RC1/'fixtures/researcher_c4_014_generated_modules').glob('mr_*.py')):
 sp=importlib.util.spec_from_file_location('frozen_'+path.stem,path); m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
 if m.CONTROL['execution_gate']=='PROCEED':MODULES[m.SPEC['T']['operator_id']]=(m,path)
OPS=['DELAY_RESULT_ENTRY','REMOVE_REDUNDANT_OBSERVATION','PRESERVE_CLINICAL_STATE','RESAMPLE_TRAJECTORY','INCREASE_SLOPE','INSERT_TRANSIENT_AKI','SHIFT_TIME','CONVERT_UNIT']
assert set(OPS)==set(MODULES),set(MODULES)
FIX={x['candidate_key'].split('::')[-1]:x for x in F if x['candidate_key'].split('::')[-1] in OPS and x['candidate_key']!='FIX-PENDING-ADMISSION-001::SHIFT_TIME'}
MUTANTS={
'DELAY_RESULT_ENTRY':['use_issued_as_effective','staleness_guard','wrong_threshold'],
'REMOVE_REDUNDANT_OBSERVATION':['use_mean','use_count','use_first'],
'PRESERVE_CLINICAL_STATE':['aux_threshold','aux_parity','aux_offset'],
'RESAMPLE_TRAJECTORY':['count_based_risk','mean_based_risk','last_three_risk'],
'INCREASE_SLOPE':['reverse_slope_risk','last_value_risk','count_based_risk'],
'INSERT_TRANSIENT_AKI':['use_minimum','use_observation_count','use_mean'],
'SHIFT_TIME':['use_day_of_year','use_month_index','use_epoch_days'],
'CONVERT_UNIT':['ignore_units','bad_conversion_factor','fixed_bias_by_unit'],
}
ORDER=['LOW','MODERATE','HIGH']
def dt(s):return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc)
def classify(n):return 'LOW' if n<-1.8 else ('MODERATE' if n<-1.0 else 'HIGH')
def slope(rows):
 a,b=rows[0],rows[-1];return (float(b['value'])-float(a['value']))/(float(b['time_index'])-float(a['time_index']))
def target(op,case,mode,policy):
 rows=case.get('observations',[])
 if op=='DELAY_RESULT_ENTRY':
  o=rows[0];effect=dt(o['effective_time']);issued=dt(o['issued_time']);decision=dt('2026-02-10T00:00:00Z')
  if issued>decision:return 'ABSTAIN'
  if mode=='staleness_guard' and (issued-effect).days>2:return 'REVIEW'
  t=issued if mode=='use_issued_as_effective' else effect
  threshold=60 if mode=='wrong_threshold' else 50
  return 'REVIEW' if float(o['value'])<threshold or t<policy['cutoff'] else 'MONITOR_3M'
 if op=='REMOVE_REDUNDANT_OBSERVATION':
  vals=[float(x['value']) for x in rows]
  return {'reference':min(vals),'use_mean':sum(vals)/len(vals),'use_count':float(len(vals)),'use_first':vals[0]}[mode]
 if op=='PRESERVE_CLINICAL_STATE':
  cat=case['state_defining_fields']['gfr_category']; aux=case['non_state_auxiliary_field']
  if mode=='aux_threshold':return cat if aux<11 else cat+'_ALT'
  if mode=='aux_parity':return cat if aux%2==0 else cat+'_ALT'
  if mode=='aux_offset':return cat+('_ALT' if aux>10 else '')
  return cat
 if op=='RESAMPLE_TRAJECTORY':
  anchors=[x for x in rows if x.get('anchor') or x.get('protected_anchor')]
  decline=float(anchors[0]['value'])-float(anchors[-1]['value'])
  if mode=='count_based_risk':return 'HIGH' if len(rows)>=5 else 'LOW'
  if mode=='mean_based_risk':return 'HIGH' if sum(float(x['value']) for x in rows)/len(rows)<58 else 'LOW'
  if mode=='last_three_risk':return 'HIGH' if sum(float(x['value']) for x in rows[-3:])/len(rows[-3:])<58 else 'LOW'
  return 'HIGH' if decline>=3 else 'MODERATE'
 if op=='INCREASE_SLOPE':
  sl=slope(rows)
  if mode=='reverse_slope_risk':return classify(-sl-3)
  if mode=='last_value_risk':return 'LOW' if rows[-1]['value']>=56 else 'HIGH'
  if mode=='count_based_risk':return 'HIGH' if len(rows)>3 else 'LOW'
  return classify(sl)
 if op=='INSERT_TRANSIENT_AKI':
  vals=[float(x['value']) for x in rows]
  if mode=='use_minimum':return min(vals)/10
  if mode=='use_observation_count':return float(len(vals))
  if mode=='use_mean':return sum(vals)/len(vals)/100
  return vals[0]/100
 if op=='SHIFT_TIME':
  t=dt(rows[0]['effective_time'])
  if mode=='use_day_of_year':return float(t.timetuple().tm_yday)
  if mode=='use_month_index':return float(t.month)
  if mode=='use_epoch_days':return t.timestamp()/86400
  return float(rows[0]['value'])
 if op=='CONVERT_UNIT':
  val=float(rows[0]['value']);unit=rows[0]['unit'];factor=1000 if unit.startswith('L/') else 1
  if mode=='ignore_units':return val
  if mode=='bad_conversion_factor':return val*(100 if factor==1000 else 1)
  if mode=='fixed_bias_by_unit':return val*factor+(1 if factor==1000 else 0)
  return val*factor
 raise ValueError(op)
def derive_cases(op):
 f=FIX[op];base=f['source_case'];out=[]
 for i in range(3):
  case=copy.deepcopy(base);policy={}
  if op=='DELAY_RESULT_ENTRY':policy['cutoff']=dt(['2026-01-31T00:00:00Z','2026-02-03T00:00:00Z','2026-02-06T00:00:00Z'][i]);case['observations'][0]['value']=[55.,55.,48.][i]
  if op=='REMOVE_REDUNDANT_OBSERVATION':case['observations'][-1]['value']=[49.,48.,47.][i]
  if op=='PRESERVE_CLINICAL_STATE':case['non_state_auxiliary_field']=[10,12,20][i]
  if op=='RESAMPLE_TRAJECTORY':
   for j,r in enumerate(case['observations']):r['value']=r['value']+[0,-1,1][i]
  if op=='INCREASE_SLOPE':
   for j,r in enumerate(case['observations']):r['value']+= [0,-0.3,0.3][i]*j
  if op=='INSERT_TRANSIENT_AKI':case['observations'][0]['value']=[100.,80.,60.][i]
  if op=='SHIFT_TIME':case['observations'][0]['value']=[48.,49.,50.][i]
  if op=='CONVERT_UNIT':case['observations'][0]['value']=[0.09,0.08,0.07][i]
  out.append((case,policy))
 return out

def run():
 results=[];reference_checks=[];case_manifest=[];module_manifest={}
 for op in OPS:
  m,path=MODULES[op];module_manifest[op]={'candidate_mr_id':m.SPEC['candidate_mr_id'],'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'relation_family':m.SPEC['R']['relation_family']}
  for ci,(case,policy) in enumerate(derive_cases(op),1):
   fixture=FIX[op];context=fixture['execution_context'];oracle_ctx=fixture['oracle_context']; cfg={}
   if m.SPEC['R']['relation_family'].startswith('ORDINAL'):
    cfg['ordinal_orderings']={'risk_low_moderate_high_v1':ORDER}
   if op=='CONVERT_UNIT':cfg['unit_conversions']={'UCUM-FIX-001':{'source_unit':'L/min/1.73m2','target_unit':'mL/min/1.73m2','factor':1000.,'offset':0.}}
   reference_sut=lambda x:target(op,x,'reference',policy)
   reference=m.execute(copy.deepcopy(case),reference_sut,execution_context=context,oracle_context=oracle_ctx,runtime_config=cfg)
   reference_checks.append({'operator':op,'case':ci,'status':reference['status'],'oracle_truth':reference['oracle']['truth'],'source_output':reference['source_output'],'followup_output':reference['followup_output']})
   if reference['status']!='EXECUTED' or reference['oracle']['truth']!='TRUE':
    raise AssertionError(('REFERENCE_FAILED',op,ci,reference))
   followup=reference['followup_case']
   case_manifest.append({'operator':op,'case':ci,'source':case,'followup':followup,'policy':{k:(v.isoformat() if isinstance(v,datetime) else v) for k,v in policy.items()}})
   for mode in MUTANTS[op]:
    mut_sut=lambda x,md=mode:target(op,x,md,policy)
    got=m.execute(copy.deepcopy(case),mut_sut,execution_context=context,oracle_context=oracle_ctx,runtime_config=cfg)
    assert got['status']=='EXECUTED'
    # Independent exact-output conventional tests: reference expected results on BOTH source/follow-up inputs.
    conventional_killed=(got['source_output']!=reference['source_output'] or got['followup_output']!=reference['followup_output'])
    results.append({'operator':op,'mutant':mode,'case':ci,'candidate_mr_id':m.SPEC['candidate_mr_id'], 'source_output':str(got['source_output']), 'followup_output':str(got['followup_output']), 'mr_truth':got['oracle']['truth'], 'mr_reason':got['oracle']['reason'], 'mr_killed':int(got['oracle']['truth']=='FALSE'), 'conventional_exact_output_killed':int(conventional_killed), 'reference_source_output':str(reference['source_output']), 'reference_followup_output':str(reference['followup_output'])})
 out=ROOT/'results';out.mkdir(exist_ok=True)
 with open(out/'mutation_case_results.csv','w',newline='') as f:
  wr=csv.DictWriter(f,results[0].keys());wr.writeheader();wr.writerows(results)
 (out/'reference_checks.json').write_text(json.dumps(reference_checks,indent=2)+'\n')
 (out/'case_manifest.json').write_text(json.dumps(case_manifest,indent=2)+'\n')
 (out/'generated_module_manifest.json').write_text(json.dumps(module_manifest,indent=2)+'\n')
 per=[]
 for op in OPS:
  for mode in MUTANTS[op]:
   a=[r for r in results if r['operator']==op and r['mutant']==mode]
   per.append({'operator':op,'mutant':mode,'cases':len(a),'mr_killed':int(any(r['mr_killed'] for r in a)),'conventional_killed':int(any(r['conventional_exact_output_killed'] for r in a)), 'output_distinguishable':int(any(r['conventional_exact_output_killed'] for r in a))})
 with open(out/'mutant_summary.csv','w',newline='') as f:
  wr=csv.DictWriter(f,per[0].keys());wr.writeheader();wr.writerows(per)
 totals={'operators':len(OPS),'archived_generated_mrs_executed':len(OPS),'constructed_mutants':len(per),'cases_per_mutant':3,'mutant_case_executions':len(results),'reference_pairs_verified':len(reference_checks), 'mr_killed_mutants':sum(x['mr_killed'] for x in per),'conventional_exact_output_killed_mutants':sum(x['conventional_killed'] for x in per),'output_distinguishable_mutants':sum(x['output_distinguishable'] for x in per),'mr_false_outcomes':sum(x['mr_killed'] for x in results),'mr_true_outcomes':sum(x['mr_truth']=='TRUE' for x in results),'mr_indeterminate_outcomes':sum(x['mr_truth']=='INDETERMINATE' for x in results), 'methodology':'synthetic fault seeding; original generated MR oracle; conventional baseline exact output assertions from deterministic synthetic reference model using same source and followup inputs (2 executions each); not independent real-world baseline; no clinical inference', 'environment':{'python':sys.version.split()[0], 'platform':platform.platform()},'limitations':['Mutants were authored against the same synthetic reference implementations used to derive the expected conventional outputs.', 'The conventional exact-output baseline uses stronger oracle information than metamorphic relations, although both evaluate the same source and follow-up cases.', 'Observationally indistinguishable mutants are not necessarily globally equivalent.', 'Synthetic temporal/trajectory policies are not clinical CDS implementations.', 'Selected synthetic cases were constructed to exercise the archived transformations, not random samples.']}
 (out/'summary.json').write_text(json.dumps(totals,indent=2)+'\n')
 print(json.dumps(totals,indent=2))
 print('MUTANTS:',json.dumps(per,indent=1))
 return totals
if __name__=='__main__':run()
