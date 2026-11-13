import hashlib,json
from .temporal_models import ConstraintEvaluation, TemporalSatisfiabilityResult
from .temporal_time import parse_utc,fixed_duration_seconds,iso_utc
from .temporal_eval import (
    k3_and,eval_relation,eval_duration,eval_within,eval_within_horizon,
    eval_occurs_during,eval_persists_for
)

ALLEN_RELATIONS={
 "before","after","meets","metBy","overlaps","overlappedBy","starts","startedBy",
 "during","contains","finishes","finishedBy","equalsTime","sameClinicalTime",
 "overlapsEventWindow","eventWindowOverlaps"
}

INVERSE_EXCLUSIVE={
 ("before","after"),("after","before"),
 ("before","meets"),("meets","before"),
 ("after","metBy"),("metBy","after"),
 ("during","contains"),("contains","during"),
 ("starts","startedBy"),("startedBy","starts"),
 ("finishes","finishedBy"),("finishedBy","finishes"),
}

def _canon(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def _sha(x):
    return hashlib.sha256(_canon(x).encode("utf-8")).hexdigest()

def validate_entity(e):
    errors=[]
    if e.time_domain not in {"clinical","availability","provenance"}:
        errors.append(f"INVALID_TIME_DOMAIN:{e.entity_id}")
    if e.kind not in {"INSTANT","INTERVAL","UNCERTAIN_INSTANT","OPEN_INTERVAL"}:
        errors.append(f"INVALID_ENTITY_KIND:{e.entity_id}")
    try:
        s0=parse_utc(e.start_earliest)
        s1=parse_utc(e.start_latest)
        e0=parse_utc(e.end_earliest)
        e1=parse_utc(e.end_latest)
    except Exception as ex:
        errors.append(f"INVALID_NORMALIZED_TIME:{e.entity_id}:{ex}")
        return errors
    if s0 and s1 and s0>s1:
        errors.append(f"START_UNCERTAINTY_REVERSED:{e.entity_id}")
    if e0 and e1 and e0>e1:
        errors.append(f"END_UNCERTAINTY_REVERSED:{e.entity_id}")
    # Exact/uncertain intervals must have positive half-open extent when end known.
    if e.kind in {"INTERVAL","OPEN_INTERVAL"} and s0 and e1 and e.kind!="OPEN_INTERVAL":
        if s0>=e1:
            errors.append(f"NONPOSITIVE_HALF_OPEN_INTERVAL:{e.entity_id}")
    return errors

def detect_static_constraint_conflicts(constraints):
    conflicts=[]
    by_pair={}
    for c in constraints:
        key=(c.left,c.right,c.time_domain)
        by_pair.setdefault(key,[]).append(c)

    for key,rows in by_pair.items():
        rels=[c.operator for c in rows if c.operator in ALLEN_RELATIONS]
        for a,b in INVERSE_EXCLUSIVE:
            if a in rels and b in rels:
                conflicts.append(f"INCOMPATIBLE_RELATIONS:{key}:{a}+{b}")

        # Detect incompatible fixed-day lower/upper bounds on the same ordered pair.
        lowers=[]
        uppers=[]
        for c in rows:
            if c.operator in {"AT_LEAST","AT_MOST"} and c.duration:
                sec=fixed_duration_seconds(c.duration)
                if sec is not None:
                    if c.operator=="AT_LEAST": lowers.append((sec,c.constraint_id))
                    else: uppers.append((sec,c.constraint_id))
        if lowers and uppers:
            max_low=max(x[0] for x in lowers)
            min_up=min(x[0] for x in uppers)
            if max_low>min_up:
                conflicts.append(
                    f"INCOMPATIBLE_DURATION_BOUNDS:{key}:min={max_low}:max={min_up}"
                )
    return sorted(set(conflicts))

def _domain_ok(entity, constraint_domain):
    if constraint_domain=="clinical":
        return entity.time_domain=="clinical"
    if constraint_domain=="availability":
        return entity.time_domain=="availability"
    if constraint_domain=="provenance":
        return entity.time_domain=="provenance"
    return False

def evaluate_constraint(c,entities):
    if c.left not in entities:
        return ConstraintEvaluation(c.constraint_id,c.operator,"INDETERMINATE",
                                    "LEFT_ENTITY_MISSING",sorted(c.source_refs))
    a=entities[c.left]
    b=entities.get(c.right) if c.right else None

    if not _domain_ok(a,c.time_domain):
        return ConstraintEvaluation(c.constraint_id,c.operator,"INDETERMINATE",
                                    "TIME_DOMAIN_MISMATCH_LEFT",sorted(c.source_refs))
    if b is not None and not _domain_ok(b,c.time_domain):
        return ConstraintEvaluation(c.constraint_id,c.operator,"INDETERMINATE",
                                    "TIME_DOMAIN_MISMATCH_RIGHT",sorted(c.source_refs))

    try:
        if c.operator in ALLEN_RELATIONS:
            if b is None:
                return ConstraintEvaluation(c.constraint_id,c.operator,"INDETERMINATE",
                                            "RIGHT_ENTITY_MISSING",sorted(c.source_refs))
            truth,reason=eval_relation(a,b,c.operator)
        elif c.operator in {"AT_LEAST","AT_MOST"}:
            if b is None or not c.duration:
                return ConstraintEvaluation(c.constraint_id,c.operator,"INDETERMINATE",
                                            "DURATION_ARGUMENT_MISSING",sorted(c.source_refs))
            truth,reason=eval_duration(a,b,c.operator,c.duration)
        elif c.operator=="WITHIN":
            if b is None or not c.duration:
                return ConstraintEvaluation(c.constraint_id,c.operator,"INDETERMINATE",
                                            "WITHIN_ARGUMENT_MISSING",sorted(c.source_refs))
            truth,reason=eval_within(a,b,c.duration)
        elif c.operator=="WITHIN_HORIZON":
            if b is None or not c.duration:
                return ConstraintEvaluation(c.constraint_id,c.operator,"INDETERMINATE",
                                            "HORIZON_ARGUMENT_MISSING",sorted(c.source_refs))
            truth,reason=eval_within_horizon(a,b,c.duration)
        elif c.operator=="PERSISTS_FOR":
            if not c.duration:
                return ConstraintEvaluation(c.constraint_id,c.operator,"INDETERMINATE",
                                            "PERSISTENCE_DURATION_MISSING",sorted(c.source_refs))
            truth,reason=eval_persists_for(a,c.duration)
        elif c.operator=="OCCURS_DURING":
            if b is None:
                return ConstraintEvaluation(c.constraint_id,c.operator,"INDETERMINATE",
                                            "EVENT_WINDOW_MISSING",sorted(c.source_refs))
            truth,reason=eval_occurs_during(a,b)
        elif c.operator=="OVERLAPS":
            if b is None:
                return ConstraintEvaluation(c.constraint_id,c.operator,"INDETERMINATE",
                                            "OVERLAP_ENTITY_MISSING",sorted(c.source_refs))
            truth,reason=eval_relation(a,b,"overlapsEventWindow")
        else:
            return ConstraintEvaluation(c.constraint_id,c.operator,"INDETERMINATE",
                                        "UNSUPPORTED_TEMPORAL_OPERATOR",sorted(c.source_refs))
    except Exception as ex:
        return ConstraintEvaluation(c.constraint_id,c.operator,"INDETERMINATE",
                                    f"EVALUATION_ERROR:{ex}",sorted(c.source_refs))
    return ConstraintEvaluation(c.constraint_id,c.operator,truth,reason,sorted(c.source_refs))

def temporal_scope_hull(entities):
    starts=[]
    ends=[]
    for e in entities.values():
        if e.time_domain!="clinical":
            continue
        try:
            s0=parse_utc(e.start_earliest)
            s1=parse_utc(e.start_latest)
            e0=parse_utc(e.end_earliest)
            e1=parse_utc(e.end_latest)
        except Exception:
            continue
        if s0: starts.append(s0)
        if s1: starts.append(s1)
        if e0: ends.append(e0)
        if e1: ends.append(e1)
        # Instants contribute their start as both hull start/end.
        if e.kind in {"INSTANT","UNCERTAIN_INSTANT"}:
            if s0: ends.append(s0)
            if s1: ends.append(s1)
    return {
      "earliest_clinical_time":iso_utc(min(starts)) if starts else None,
      "latest_clinical_time":iso_utc(max(ends)) if ends else None,
      "boundary":"[start,end)"
    }

def check_temporal_satisfiability(component,precedence_result,case):
    entities={e.entity_id:e for e in case.entities}
    entity_errors=[]
    for e in case.entities:
        entity_errors.extend(validate_entity(e))

    structural_conflicts=detect_static_constraint_conflicts(case.constraints)
    evaluations=[evaluate_constraint(c,entities) for c in sorted(case.constraints,key=lambda x:x.constraint_id)]
    truth=k3_and(x.truth for x in evaluations)

    notes=[]
    if entity_errors:
        status="INVALID_TEMPORAL_INPUT"
        truth="INDETERMINATE"
        action="ABSTAIN"
        structural_conflicts=sorted(set(structural_conflicts+entity_errors))
    elif structural_conflicts:
        status="TEMPORALLY_UNSATISFIABLE"
        truth="FALSE"
        action="REJECT_CANDIDATE"
    elif truth=="TRUE":
        status="TEMPORALLY_SATISFIABLE"
        action="PROCEED"
    elif truth=="FALSE":
        status="TEMPORALLY_UNSATISFIABLE"
        action="REJECT_CANDIDATE"
    else:
        status="TEMPORALLY_INDETERMINATE"
        action="ABSTAIN"

    # C4-011 never overrides an upstream safety block.
    if precedence_result["system_action"]=="ABSTAIN":
        notes.append(
          "C4-010 upstream system action is ABSTAIN; temporal evaluation does not override it."
        )
        action="ABSTAIN"

    if not case.constraints:
        notes.append("No temporal constraint is declared; conjunction is vacuously TRUE.")

    semantic={
      "proposition_id":component["proposition_id"],
      "operator_id":component["operator_id"],
      "component_fingerprint":component["component_fingerprint"],
      "c4_010_exception_fingerprint":precedence_result["exception_fingerprint"],
      "temporal_status":status,
      "temporal_truth":truth,
      "constraint_evaluations":[x.to_dict() for x in evaluations],
      "structural_conflicts":structural_conflicts,
      "temporal_scope_hull":temporal_scope_hull(entities),
      "release_ref":case.release_ref,
    }
    fp=_sha(semantic)
    return TemporalSatisfiabilityResult(
      proposition_id=component["proposition_id"],
      operator_id=component["operator_id"],
      component_fingerprint=component["component_fingerprint"],
      c4_010_exception_fingerprint=precedence_result["exception_fingerprint"],
      temporal_status=status,
      temporal_truth=truth,
      system_action=action,
      constraint_evaluations=evaluations,
      structural_conflicts=structural_conflicts,
      temporal_scope_hull=semantic["temporal_scope_hull"],
      temporal_fingerprint=fp,
      notes=notes
    )
