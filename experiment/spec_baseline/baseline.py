"""Standalone requirement-to-MR compiler for controlled synthetic evaluation.

No dependencies on the CKD compiler, generated modules or their oracle/runtime.
The requirements document is explicitly human-authored and is not a blinded external baseline.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import copy, json, hashlib, math

ROOT=Path(__file__).resolve().parent

class ConstructionFailure(Exception): pass

def _parse(path):
    # A small, deliberately independent structural selector language.
    import re
    parts = re.findall(r'[^.\[\]]+|\[\d+\]',path)
    if not parts or ''.join(parts).replace('[','').replace(']','')=='':
        raise ConstructionFailure('empty selector')
    return [int(p[1:-1]) if p.startswith('[') else p for p in parts]

def _lookup(root,path):
    parts=_parse(path)
    obj=root
    for key in parts[:-1]:obj=obj[key]
    return obj,parts[-1]

def _replace_date(value,days):
    stamp=datetime.fromisoformat(value.replace('Z','+00:00'))
    if stamp.tzinfo is None:raise ValueError('timestamp must be timezone-aware')
    return (stamp+timedelta(days=days)).astimezone(timezone.utc).isoformat().replace('+00:00','Z')

def _change(case, action):
    x=copy.deepcopy(case)
    method=action['method']
    obj,key=_lookup(x,action['path'])
    if method=='shift_datetime':obj[key]=_replace_date(obj[key],action['days'])
    elif method=='remove_matching':obj[key]=[r for r in obj[key] if r.get('id')!=action['id']]
    elif method=='add_numeric':obj[key]+=action['delta']
    elif method=='add_slope':
        rows=obj[key];t0=rows[0]['time_index']
        for row in rows[1:]:row['value']+=action['factor']*(row['time_index']-t0)
    elif method=='insert_transient':
        rows=obj[key];value=float(rows[0]['value'])
        rows.extend([
          {'id':'baseline_trigger','value':value*action['trigger_factor'],'effective_time':action['trigger_time']},
          {'id':'baseline_recovery','value':value*action['recovery_factor'],'effective_time':action['recovery_time']}
        ])
    elif method=='change_unit':
        obj[key]['value']*=action['factor'];obj[key]['unit']=action['to_unit']
    else: raise ConstructionFailure(f'unknown transformation: {method}')
    # Consistency for sequences with a denormalized order field.
    if method=='remove_matching' and action['path']=='observations' and 'observation_order' in x:
        x['observation_order']=[r['id'] for r in x['observations']]
    return x

def _relation(src, follow, clause):
    if src is None or follow is None:return None
    kind=clause['kind']
    if kind=='same_output':return src==follow
    if kind=='absolute_difference':
        if isinstance(src,bool) or isinstance(follow,bool):return None
        if not (isinstance(src,(float,int)) and isinstance(follow,(float,int))):return None
        if not (math.isfinite(src) and math.isfinite(follow)):return None
        return abs(src-follow)<=clause['tolerance']
    if kind=='ordinal_nondecrease':
        rank={v:i for i,v in enumerate(clause['levels'])}
        if src not in rank or follow not in rank:return None
        return rank[follow]>=rank[src]
    raise ConstructionFailure(f'unknown relation: {kind}')

@dataclass(frozen=True)
class CompiledRelation:
    requirement_id:str
    domain:str
    statement:str
    transformation:dict
    comparison:dict
    source_digest:str
    def followup(self,case):return _change(case,self.transformation)
    def check(self,source_output,followup_output):return _relation(source_output,followup_output,self.comparison)

def compile_requirements(path:Path=ROOT/'requirements.json'):
    original=path.read_bytes();doc=json.loads(original)
    if not isinstance(doc.get('requirements'),list):raise ConstructionFailure('missing requirements')
    seen=set();results=[]
    for rule in doc['requirements']:
        for field in ['id','domain','requirement','transformation','oracle']:
            if field not in rule:raise ConstructionFailure(f'missing {field}')
        if rule['id'] in seen or rule['domain'] in [x.domain for x in results]:
            raise ConstructionFailure('duplicate identifier or domain')
        seen.add(rule['id'])
        # Ensure all transformation/relation vocab entries are supported at build time.
        if rule['transformation']['method'] not in {'shift_datetime','remove_matching','add_numeric','add_slope','insert_transient','change_unit'}:raise ConstructionFailure('unsupported action')
        if rule['oracle']['kind'] not in {'same_output','absolute_difference','ordinal_nondecrease'}:raise ConstructionFailure('unsupported relation')
        key=json.dumps(rule,sort_keys=True,separators=(',',':')).encode()
        results.append(CompiledRelation(rule['id'],rule['domain'],rule['requirement'],rule['transformation'],rule['oracle'],hashlib.sha256(key).hexdigest()))
    return tuple(results)

if __name__=='__main__':
    relations=compile_requirements()
    print(json.dumps({'count':len(relations),'requirement_sha256':hashlib.sha256((ROOT/'requirements.json').read_bytes()).hexdigest(),'ids':[r.requirement_id for r in relations]},indent=2))
