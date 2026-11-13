import hashlib,json
from itertools import combinations
from .conflict_models import ConflictResolutionRecord,DuplicateRecord,ConflictEvidence,CONFLICT_TYPES
from .conflict_scope import applicability_overlap,temporal_overlap
from .output_relation_typing import relation_compatibility

def _canon(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def _sha(x):
    return hashlib.sha256(_canon(x).encode("utf-8")).hexdigest()

def candidate_key(prop,op):
    return f"{prop}::{op}"

def _stable_conflict_id(payload):
    return "CONFLICT-"+_sha(payload)[:20]

def _resolve_record(conflict_type, keys, target, output, app, temp, compat, rationale, refs,
                    hint=None,winner=None,adjudication_ref=None,detection_phase="compile_time"):
    # Mechanical resolutions are allowed only when a legitimate rule from C3-013 is explicit.
    resolved=False
    resolution_type="UNRESOLVED_SAFE_ABSTENTION"
    legitimate=None

    if winner and hint in {
        "RELEASE_PINNED_NON_SUPERSEDED",
        "EXPLICIT_SCOPE_CONTAINMENT",
        "SOURCE_AUTHORITATIVE",
        "FORMAL_ADJUDICATION"
    }:
        resolved=True
        legitimate=winner
        resolution_type=hint

    if resolved:
        status="RESOLVED"
        truth="TRUE"
        action="PROCEED"
        gate="Pass"
    else:
        status="UNRESOLVED"
        truth="INDETERMINATE"
        action="ABSTAIN"
        gate="Fail"

    payload={
      "conflict_type":conflict_type,"keys":sorted(keys),"target":target,"output":output,
      "app":app,"temp":temp,"compat":compat,"rationale":rationale,"refs":sorted(refs),
      "resolution_type":resolution_type,"winner":legitimate,"adjudication_ref":adjudication_ref
    }
    return ConflictResolutionRecord(
      conflict_id=_stable_conflict_id(payload),
      conflict_type=conflict_type,
      involved_candidate_keys=sorted(keys),
      common_target_id=target,
      common_output_id=output,
      applicability_overlap=app,
      temporal_overlap=temp,
      expectation_compatibility=compat,
      detection_phase=detection_phase,
      resolution_status=status,
      resolution_type=resolution_type,
      legitimate_winner_key=legitimate,
      semantic_truth=truth,
      system_action=action,
      conflict_resolved_gate=gate,
      rationale=rationale,
      source_refs=sorted(set(refs)),
      adjudication_ref=adjudication_ref,
      record_version="ConflictResolutionRecord-R1.0",
    )

def pre_conflict_comparable(precedence_result,temporal_result):
    """
    Conflict discovery must not be circular. A C4-010 software fixture may contain
    a seeded P8 ConflictException solely to test precedence. We therefore use the
    pre-conflict P0-P6 view for pair discovery.
    """
    fatal_tokens={
      "RELEASE_BLOCKED","COMPILATION_BLOCKED","INELIGIBLE","NOT_APPLICABLE","LOCAL_ONLY_OR_BLOCKED"
    }
    outcome=precedence_result.get("precedence_outcome")
    if outcome in fatal_tokens:
        return False
    # A runtime missingness/precision abstention is not a stable compile-time pairwise comparator.
    if outcome in {"ABSTAIN","PENDING"}:
        return False
    if temporal_result.get("temporal_status") in {"TEMPORALLY_UNSATISFIABLE","INVALID_TEMPORAL_INPUT"}:
        return False
    return True

def detect_expected_relation_conflicts(typed,scopes,precedence,temporal):
    records=[]
    typed_by_key={candidate_key(x.proposition_id,x.operator_id):x for x in typed}
    keys=sorted(typed_by_key)

    for ka,kb in combinations(keys,2):
        a=typed_by_key[ka]; b=typed_by_key[kb]
        sa=scopes[ka]; sb=scopes[kb]

        if sa.target_id!=sb.target_id or sa.output_id!=sb.output_id:
            continue
        # Critical C4 candidate-level guard: opposite/independent transformations are not
        # competing expectations unless they were explicitly declared semantically comparable.
        if sa.comparison_context_id!=sb.comparison_context_id:
            continue
        if not pre_conflict_comparable(precedence[ka],temporal[ka]):
            continue
        if not pre_conflict_comparable(precedence[kb],temporal[kb]):
            continue

        app,app_reason=applicability_overlap(sa,sb)
        temp,temp_reason=temporal_overlap(
            temporal[ka],temporal[kb],sa.temporal_scope_policy,sb.temporal_scope_policy
        )
        compat,compat_reason=relation_compatibility(a,b)

        # C3-013 conflict scope is conjunctive. Only proven overlap + proven incompatibility qualifies.
        if app=="TRUE" and temp=="TRUE" and compat=="FALSE":
            rationale=(
              "Same target/output and comparison context; applicability and temporal scope overlap; "
              f"formal expectation sets are disjoint ({compat_reason})."
            )
            records.append(_resolve_record(
              "ExpectedRelationConflict",[ka,kb],sa.target_id,sa.output_id,app,temp,compat,
              rationale,[app_reason,temp_reason,compat_reason]
            ))
    return records

def detect_temporal_conflicts(typed,scopes,temporal):
    records=[]
    for t in typed:
        k=candidate_key(t.proposition_id,t.operator_id)
        tr=temporal[k]
        if tr.get("temporal_status")=="TEMPORALLY_INDETERMINATE":
            s=scopes[k]
            records.append(_resolve_record(
              "TemporalConflict",[k],s.target_id,s.output_id,"N/A","INDETERMINATE","N/A",
              "Temporal relation is not provable at the available precision; C3-009/C3-013 requires INDETERMINATE rather than a fabricated boolean result.",
              ["C4-011:"+tr["temporal_fingerprint"]],detection_phase="compile_time"
            ))
        elif tr.get("temporal_status")=="TEMPORALLY_UNSATISFIABLE":
            s=scopes[k]
            records.append(_resolve_record(
              "TemporalConflict",[k],s.target_id,s.output_id,"N/A","FALSE","N/A",
              "Declared temporal constraints are mutually unsatisfiable.",
              ["C4-011:"+tr["temporal_fingerprint"]],detection_phase="compile_time"
            ))
    return records

def records_from_explicit_evidence(evidence_rows,scope_lookup):
    records=[]
    for ev in sorted(evidence_rows,key=lambda x:x.evidence_id):
        if ev.conflict_type not in CONFLICT_TYPES:
            raise ValueError(f"Unknown frozen conflict type: {ev.conflict_type}")
        if ev.truth=="FALSE":
            continue
        keys=ev.involved_candidate_keys
        target=None; output=None
        if keys and all(k in scope_lookup for k in keys):
            targets={scope_lookup[k].target_id for k in keys}
            outputs={scope_lookup[k].output_id for k in keys}
            target=next(iter(targets)) if len(targets)==1 else None
            output=next(iter(outputs)) if len(outputs)==1 else None

        if ev.truth=="INDETERMINATE":
            records.append(_resolve_record(
              ev.conflict_type,keys,target,output,"INDETERMINATE","INDETERMINATE","INDETERMINATE",
              ev.rationale,ev.source_refs,adjudication_ref=ev.adjudication_ref
            ))
        elif ev.truth=="TRUE":
            records.append(_resolve_record(
              ev.conflict_type,keys,target,output,"DECLARED","DECLARED","DECLARED",
              ev.rationale,ev.source_refs,hint=ev.resolution_hint,
              winner=ev.legitimate_winner_key,adjudication_ref=ev.adjudication_ref
            ))
        else:
            raise ValueError(f"Invalid conflict evidence truth: {ev.truth}")
    return records

def duplicate_signature(component,typed_relation,invariant_result,exception_result,scope):
    # Provenance IDs are deliberately excluded from semantic duplicate identity, but
    # target/output/applicability/transformation/relation/invariant/exception semantics remain.
    payload={
      "target_id":scope.target_id,
      "output_id":scope.output_id,
      "comparison_context_id":scope.comparison_context_id,
      "C":component["C"],
      "T":component["T"],
      "R":typed_relation.to_dict(),
      "I":[
        {k:v for k,v in inv.items() if k!="invariant_id" and k!="source_refs"}
        for inv in invariant_result.get("inferred_invariants",[])
      ],
      "E":[
        {
          "exception_type":e["exception_type"],
          "scope_ref":e["scope_ref"],
          "precedence_tier":e["precedence_tier"],
          "effect_mode":e["effect_mode"],
          "phase":e["phase"],
        }
        for e in exception_result.get("assembled_exceptions",[])
      ]
    }
    return _sha(payload)

def detect_duplicates(components,typed_by_key,invariants,exceptions,scopes):
    groups={}
    for c in components:
        k=candidate_key(c["proposition_id"],c["operator_id"])
        sig=duplicate_signature(c,typed_by_key[k],invariants[k],exceptions[k],scopes[k])
        groups.setdefault(sig,[]).append(k)
    out=[]
    for sig,keys in sorted(groups.items()):
        if len(keys)>1:
            out.append(DuplicateRecord(
              duplicate_id="DUP-"+_sha({"sig":sig,"keys":sorted(keys)})[:20],
              candidate_keys=sorted(keys),
              duplicate_signature=sig,
              rationale="Candidates are semantically identical under the frozen C/T/R/I/E duplicate projection."
            ))
    return out
