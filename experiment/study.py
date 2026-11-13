import sys,ast,copy,json,inspect,hashlib,collections,csv,datetime,types,pathlib,math
P=pathlib.Path(__file__).parent
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import run_expanded as old
# This program is independent of the original generated transform and oracle for its baseline.
# The old module is used for reference SUT and original MR evaluation ONLY.
OPS=old.OPS

def independent_transform(op,x):
 y=copy.deepcopy(x)
 a=y.get('observations',[])
 if op=='DELAY_RESULT_ENTRY':
  d=datetime.datetime.fromisoformat(a[0]['issued_time'].replace('Z','+00:00'))+datetime.timedelta(days=3)
  a[0]['issued_time']=d.isoformat().replace('+00:00','Z')
 elif op=='REMOVE_REDUNDANT_OBSERVATION':
  a[:]=[z for z in a if z.get('id')!='obs_non_anchor_3']
  if 'observation_order' in y:y['observation_order']=[z['id'] for z in a]
 elif op=='PRESERVE_CLINICAL_STATE':y['non_state_auxiliary_field']+=1
 elif op=='RESAMPLE_TRAJECTORY':
  a[:]=[z for z in a if z.get('id')!='c']
  if 'observation_order' in y:y['observation_order']=[z['id'] for z in a]
 elif op=='INCREASE_SLOPE':
  t0=a[0]['time_index']
  for o in a[1:]:o['value']+=0.5*(o['time_index']-t0)
 elif op=='INSERT_TRANSIENT_AKI':
  a.extend([{'id':'independent_trigger','value':float(a[0]['value'])*.75,'effective_time':'2026-01-02T00:00:00Z'}, {'id':'independent_recovery','value':float(a[0]['value'])*.975,'effective_time':'2026-01-16T00:00:00Z'}])
 elif op=='SHIFT_TIME':
  t=datetime.datetime.fromisoformat(a[0]['effective_time'].replace('Z','+00:00'))+datetime.timedelta(days=7)
  a[0]['effective_time']=t.isoformat().replace('+00:00','Z')
 elif op=='CONVERT_UNIT':
  a[0]['value']=float(a[0]['value'])*1000;a[0]['unit']='mL/min/1.73m2'
 else:raise ValueError(op)
 return y

def independent_relation(op,s,f):
 if s is None or f is None:return None
 if op in ('DELAY_RESULT_ENTRY','PRESERVE_CLINICAL_STATE'):return s==f
 if op in ('REMOVE_REDUNDANT_OBSERVATION','SHIFT_TIME','CONVERT_UNIT'):return isinstance(s,(int,float)) and isinstance(f,(int,float)) and abs(s-f)<=1e-7
 if op in ('RESAMPLE_TRAJECTORY','INCREASE_SLOPE'):
  ranks={'LOW':0,'MODERATE':1,'HIGH':2}
  return s in ranks and f in ranks and ranks[f]>=ranks[s]
 if op=='INSERT_TRANSIENT_AKI':return isinstance(s,(int,float)) and isinstance(f,(int,float)) and abs(s-f)<=.5
 raise ValueError(op)

src=inspect.getsource(old.target)
T=ast.parse(src)
node=T.body[0]
# Uniform, syntactically mechanical single-site changes with no oracle feedback.
class Sites(ast.NodeVisitor):
 def __init__(self):self.sites=[]
 def visit(self,node):
  if isinstance(node,ast.Compare) and len(node.ops)==1:
   vals=[ast.Lt,ast.LtE,ast.Gt,ast.GtE,ast.Eq,ast.NotEq]
   self.sites.extend((node,cls) for cls in vals if not isinstance(node.ops[0],cls))
  elif isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Add,ast.Sub,ast.Mult,ast.Div)):
   vals=[ast.Add,ast.Sub,ast.Mult,ast.Div]
   self.sites.extend((node,cls) for cls in vals if not isinstance(node.op,cls))
  elif isinstance(node,ast.Constant) and type(node.value) in (int,float) and not isinstance(node.value,bool):
   self.sites.extend((node,v) for v in (0,1,-1) if node.value!=v)
  elif isinstance(node,ast.IfExp):self.sites.append((node,'swap'))
  super().visit(node)
all_sites=Sites();all_sites.visit(node)
# AST paths (rather than line numbers) identify mutation sites in future copies.
def enumerate_paths(root):
 out=[]
 def walk(n,path):
  if isinstance(n,ast.AST):
   out.append((path,n))
   for key,value in ast.iter_fields(n):
    if isinstance(value,list):
     for i,z in enumerate(value):walk(z,path+((key,i),))
    elif isinstance(value,ast.AST):walk(value,path+((key,None),))
 walk(root,());return out
nodes=enumerate_paths(node);byid={id(x):p for p,x in nodes}
mutants=[];seen=set()
for n,repl in all_sites.sites:
 path=byid[id(n)]
 clone=copy.deepcopy(node); z=clone
 for k,i in path:z=getattr(z,k) if i is None else getattr(z,k)[i]
 if isinstance(n,ast.Compare):z.ops[0]=repl(); fam='compare';rv=repl.__name__
 elif isinstance(n,ast.BinOp):z.op=repl();fam='arithmetic';rv=repl.__name__
 elif isinstance(n,ast.IfExp):z.body,z.orelse=z.orelse,z.body;fam='branch_swap';rv='swap'
 else:z.value=repl;fam='numeric_constant';rv=str(repl)
 ast.fix_missing_locations(clone)
 try:
  tree=ast.Module(body=[clone],type_ignores=[]); compiled=compile(tree,'<auto-mutant>','exec')
 except Exception:continue
 dumped=ast.dump(clone,include_attributes=False)
 if dumped in seen:continue
 seen.add(dumped)
 namespace=dict(vars(old));exec(compiled,namespace)
 fn=namespace['target']
 mutants.append((f'M{len(mutants)+1:03}',fam,f'{getattr(n,"lineno",0)}:{getattr(n,"col_offset",0)}:{rv}',fn))
print('candidate syntactic mutants',len(mutants),'families',dict(collections.Counter(x[1] for x in mutants)),flush=True)

cases=[]
for op in OPS:
 for ix,(source,policy) in enumerate(old.derive_cases(op),1):
  baseline_follow=independent_transform(op,source)
  ref_src=old.target(op,source,'reference',policy)
  ref_fu=old.target(op,baseline_follow,'reference',policy)
  valid=independent_relation(op,ref_src,ref_fu)
  # Use archived generated MR for a genuinely distinct MR construction route.
  m=old.MODULES[op][0];fx=old.FIX[op];cfg={}
  if m.SPEC['R']['relation_family'].startswith('ORDINAL'):cfg['ordinal_orderings']={'risk_low_moderate_high_v1':old.ORDER}
  if op=='CONVERT_UNIT':cfg['unit_conversions']={'UCUM-FIX-001':{'source_unit':'L/min/1.73m2','target_unit':'mL/min/1.73m2','factor':1000.,'offset':0.}}
  generated=m.execute(copy.deepcopy(source),lambda x:old.target(op,x,'reference',policy),execution_context=fx['execution_context'],oracle_context=fx['oracle_context'],runtime_config=cfg)
  assert generated['status']=='EXECUTED' and generated['oracle']['truth']=='TRUE',(op,ix,generated)
  cases.append((op,ix,source,policy,baseline_follow,valid,generated['followup_case'],fx,cfg))
print('baseline reference validity',sum(x[5] is True for x in cases),'of',len(cases),'invalid',[(x[0],x[1]) for x in cases if x[5] is not True],flush=True)
records=[]
for mid,family,site,fn in mutants:
 for op,ix,source,policy,baseline_follow,b_valid,generated_follow,fx,cfg in cases:
  try:
   so=fn(op,copy.deepcopy(source),'reference',policy);bf=fn(op,copy.deepcopy(baseline_follow),'reference',policy)
   gfo=fn(op,copy.deepcopy(generated_follow),'reference',policy)
   baseline_result=independent_relation(op,so,bf) if b_valid is True else None
   m=old.MODULES[op][0]
   # Original published runtime oracle, on original generated followup paired with mutant source.
   generated_result=m.oracle(so,gfo,oracle_context=fx['oracle_context'],runtime_config=cfg)['truth']
   gkill=generated_result=='FALSE'
   bkill=baseline_result is False
   distinguished=(so!=old.target(op,source,'reference',policy) or bf!=old.target(op,baseline_follow,'reference',policy) or gfo!=old.target(op,generated_follow,'reference',policy))
   status='ok'
  except Exception as exc:
   status=type(exc).__name__;baseline_result=None;generated_result=None;gkill=False;bkill=False;distinguished=False
  records.append(dict(mutant_id=mid,family=family,site=site,operator=op,case=ix,status=status,baseline_eligible=b_valid is True,baseline_false=baseline_result is False,generated_false=gkill,distinguished=distinguished))
agg=[]
for mid,family,site,_ in mutants:
 rows=[r for r in records if r['mutant_id']==mid]
 agg.append(dict(mutant_id=mid,family=family,site=site,valid_execution=sum(r['status']=='ok' for r in rows),errors=sum(r['status']!='ok' for r in rows),baseline_detected=any(r['baseline_false'] for r in rows),generated_detected=any(r['generated_false'] for r in rows),locally_distinguished=any(r['distinguished'] for r in rows)))
summary=dict(protocol_sha256=hashlib.sha256((P/'protocol.json').read_bytes()).hexdigest(),syntactic_mutants=len(mutants),source_cases=len(cases),baseline_reference_valid=sum(x[5] is True for x in cases),families=dict(collections.Counter(x['family'] for x in agg)),mutation_case_runs=len(records),runs_with_errors=sum(r['status']!='ok' for r in records),generated_detected=sum(x['generated_detected'] for x in agg),baseline_detected=sum(x['baseline_detected'] for x in agg),both_detected=sum(x['generated_detected'] and x['baseline_detected'] for x in agg),generated_only=sum(x['generated_detected'] and not x['baseline_detected'] for x in agg),baseline_only=sum(x['baseline_detected'] and not x['generated_detected'] for x in agg),locally_distinguished=sum(x['locally_distinguished'] for x in agg),locally_not_distinguished=sum(not x['locally_distinguished'] for x in agg),evaluation_scope='Code-level mutations of existing synthetic target; independent baseline transformation and oracle implementation, authored in the same study; no blindness or external authorship; same source-case set; non-eligible baseline cases excluded')
(P/'scratch_results.json').write_text(json.dumps(summary,indent=2))
with (P/'scratch_mutants.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(agg[0]));w.writeheader();w.writerows(agg)
with (P/'scratch_cases.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
print(json.dumps(summary,indent=2))
