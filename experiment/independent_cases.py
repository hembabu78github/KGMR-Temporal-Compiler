"""Supplementary source-case sensitivity check; does not overwrite frozen original outputs.
New cases are generated from the supplied fixture schema with a fixed PRNG seed,
without querying mutants or using detection labels. This is not blinded external authorship.
"""
import sys,copy,random,json,csv,hashlib,collections,datetime,math,pathlib
HERE=pathlib.Path(__file__).parent
sys.path.insert(0,str(HERE))
import study as st
import run_expanded as old
rng=random.Random(231104)
# Pre-specified perturbations of original fixture templates. Changes are selected
# without reading mutant outputs. Designed to retain type/shape invariants.
def jitter(op,src,policy):
 x=copy.deepcopy(src);p=copy.deepcopy(policy)
 obs=x.get('observations',[])
 if op=='DELAY_RESULT_ENTRY':
  obs[0]['value']=rng.choice([44.,49.,53.,57.,61.])
  p['cutoff']=old.dt(rng.choice(['2026-01-29T00:00:00Z','2026-02-01T00:00:00Z','2026-02-05T00:00:00Z']))
 elif op=='REMOVE_REDUNDANT_OBSERVATION':
  # Preserve protected selector but vary non-anchor observations.
  for o in obs:
   if o.get('id')=='obs_non_anchor_3':o['value']=rng.choice([45.,46.,47.,48.,49.])
 elif op=='PRESERVE_CLINICAL_STATE':
  x['non_state_auxiliary_field']=rng.choice([3,7,9,11,13,16,19,22])
 elif op=='RESAMPLE_TRAJECTORY':
  delta=rng.choice([-2.,-1.,0.5,1.5,2.]);
  for o in obs:o['value']=round(float(o['value'])+delta,3)
 elif op=='INCREASE_SLOPE':
  delta=rng.choice([-0.6,-0.4,-0.2,0.2,0.4,0.6]);
  for j,o in enumerate(obs):o['value']=round(float(o['value'])+delta*j,3)
 elif op=='INSERT_TRANSIENT_AKI':obs[0]['value']=rng.choice([65.,70.,75.,85.,90.,95.,105.])
 elif op=='SHIFT_TIME':obs[0]['value']=rng.choice([42.,46.,47.,52.,54.,58.])
 elif op=='CONVERT_UNIT':obs[0]['value']=rng.choice([0.045,0.055,0.065,0.075,0.085,0.095])
 return x,p

# Create 3 unseen synthetic source cases for each of 8 operators.
# The baseline's 24 fixed fixtures are not copied as test cases; schema templates are reused.
case_spec=[]; accepted=[]; rejected=[]
for op in old.OPS:
  base_cases=old.derive_cases(op)
  m=old.MODULES[op][0];fx=old.FIX[op]
  cfg={}
  if m.SPEC['R']['relation_family'].startswith('ORDINAL'):cfg['ordinal_orderings']={'risk_low_moderate_high_v1':old.ORDER}
  if op=='CONVERT_UNIT':cfg['unit_conversions']={'UCUM-FIX-001':{'source_unit':'L/min/1.73m2','target_unit':'mL/min/1.73m2','factor':1000.,'offset':0.}}
  for ix in range(3):
    source,policy=jitter(op,*base_cases[ix]); bf=st.independent_transform(op,source)
    sf=old.target(op,source,'reference',policy); bfo=old.target(op,bf,'reference',policy)
    valid_baseline=st.independent_relation(op,sf,bfo)
    try:
      gen=m.execute(copy.deepcopy(source),lambda x:old.target(op,x,'reference',policy), execution_context=fx['execution_context'],oracle_context=fx['oracle_context'],runtime_config=cfg)
      valid_generated=gen['status']=='EXECUTED' and gen['oracle']['truth']=='TRUE'
      detail=''
    except Exception as exc:valid_generated=False;gen=None;detail=f'{type(exc).__name__}: {exc}'
    case_spec.append(dict(operator=op,case=ix+1,source=source,policy={k:(v.isoformat() if isinstance(v,datetime.datetime) else v) for k,v in policy.items()},baseline_valid=valid_baseline is True,generated_valid=valid_generated,rejection_reason=detail))
    if valid_baseline is True and valid_generated:
      accepted.append((op,ix+1,source,policy,bf,gen['followup_case'],fx,cfg))
    else:rejected.append((op,ix+1,valid_baseline,valid_generated,detail))
print('Generated',len(case_spec),'accepted',len(accepted),'rejected',len(rejected),rejected,flush=True)

rows=[]
for mid,fam,site,fn in st.mutants:
 for op,ix,source,policy,bfollow,gfollow,fx,cfg in accepted:
  try:
   so=fn(op,copy.deepcopy(source),'reference',policy); bo=fn(op,copy.deepcopy(bfollow),'reference',policy);go=fn(op,copy.deepcopy(gfollow),'reference',policy)
   bl=st.independent_relation(op,so,bo)
   g=old.MODULES[op][0].oracle(so,go,oracle_context=fx['oracle_context'],runtime_config=cfg)['truth']
   refso=old.target(op,source,'reference',policy); refbo=old.target(op,bfollow,'reference',policy);refgo=old.target(op,gfollow,'reference',policy)
   dist=(so!=refso or bo!=refbo or go!=refgo)
   status='ok'
  except Exception as exc:status=type(exc).__name__;bl=None;g=None;dist=False
  rows.append(dict(mutant_id=mid,operator=op,case=ix,family=fam,status=status,generated_kill=g=='FALSE',baseline_kill=bl is False,locally_distinguished=dist))

old_mut={x['mutant_id']:x for x in csv.DictReader(open(HERE/'scratch_mutants.csv'))}
agg=[]
for mid,fam,site,fn in st.mutants:
 rr=[r for r in rows if r['mutant_id']==mid]
 errors=sum(r['status']!='ok' for r in rr)
 agg.append(dict(mutant_id=mid,family=fam,errors=errors,generated_kill=any(r['generated_kill'] for r in rr),baseline_kill=any(r['baseline_kill'] for r in rr),distinguished=any(r['locally_distinguished'] for r in rr)))

def overview(data):
 return {'mutants':len(data),'with_errors':sum(x['errors']>0 for x in data),'fully_valid':sum(x['errors']==0 for x in data),'distinguished':sum(x['distinguished'] for x in data),'valid_distinguished':sum(x['distinguished'] and x['errors']==0 for x in data),'generated_kills':sum(x['generated_kill'] for x in data),'baseline_kills':sum(x['baseline_kill'] for x in data)}
previous=[]
for x in old_mut.values():previous.append({'mutant_id':x['mutant_id'],'errors':int(x['errors']),'distinguished':x['locally_distinguished']=='True','generated_kill':x['generated_detected']=='True','baseline_kill':x['baseline_detected']=='True'})
combined=[]
for x in agg:
 p=old_mut[x['mutant_id']]
 combined.append(dict(mutant_id=x['mutant_id'],errors=int(p['errors'])+x['errors'],distinguished=(p['locally_distinguished']=='True') or x['distinguished'],generated_kill=(p['generated_detected']=='True') or x['generated_kill'],baseline_kill=(p['baseline_detected']=='True') or x['baseline_kill']))
summary={'random_seed':231104,'original_protocol_checksum':hashlib.sha256((HERE/'protocol.json').read_bytes()).hexdigest(),'source_cases_generated':len(case_spec),'source_cases_accepted':len(accepted),'source_cases_rejected':len(rejected),'mutation_evaluations':len(rows),'original':overview(previous),'additional_cases':overview(agg),'combined':overview(combined),'constraints':'Supplementary sensitivity experiment from fixture schemas, not independent clinical samples or blinded authorship. Reference validity screened before mutation evaluation.'}
(HERE/'case_sensitivity_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(HERE/'case_sensitivity_manifest.json').write_text(json.dumps(case_spec,indent=2,default=str)+'\n')
for fname,data in [('case_sensitivity_results.csv',rows),('case_sensitivity_mutants.csv',agg),('case_sensitivity_combined.csv',combined)]:
 with (HERE/fname).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
print(json.dumps(summary,indent=2),flush=True)
