from datetime import datetime, timezone

def _parse(v):
    if v is None: return None
    t=str(v)
    if t.endswith("Z"): t=t[:-1]+"+00:00"
    d=datetime.fromisoformat(t)
    if d.tzinfo is None:
        raise ValueError("timezone-aware temporal hull required")
    return d.astimezone(timezone.utc)

def applicability_overlap(a,b):
    dimensions=[
        ("care_contexts",set(a.care_contexts),set(b.care_contexts)),
        ("gfr_categories",set(a.gfr_categories),set(b.gfr_categories)),
        ("eligibility_states",set(a.eligibility_states),set(b.eligibility_states)),
    ]
    indeterminate=False
    for name,x,y in dimensions:
        if not x or not y:
            indeterminate=True
            continue
        if not (x&y):
            return "FALSE",f"DISJOINT_{name.upper()}"
    return ("INDETERMINATE","MISSING_APPLICABILITY_DIMENSION") if indeterminate else ("TRUE","ALL_DECLARED_APPLICABILITY_DIMENSIONS_OVERLAP")

def temporal_overlap(ta,tb,policy_a="FROM_C4_011",policy_b="FROM_C4_011"):
    if policy_a=="GLOBAL_WITHIN_APPLICABILITY" or policy_b=="GLOBAL_WITHIN_APPLICABILITY":
        return "TRUE","GLOBAL_SCOPE_OVERLAPS_DECLARED_SCOPE"

    if ta.get("temporal_truth")=="INDETERMINATE" or tb.get("temporal_truth")=="INDETERMINATE":
        return "INDETERMINATE","UPSTREAM_TEMPORAL_PRECISION_INDETERMINATE"
    if ta.get("temporal_truth")=="FALSE" or tb.get("temporal_truth")=="FALSE":
        return "FALSE","AT_LEAST_ONE_TEMPORAL_CONTRACT_UNSATISFIABLE"

    ha=ta.get("temporal_scope_hull",{}); hb=tb.get("temporal_scope_hull",{})
    as_=_parse(ha.get("earliest_clinical_time")); ae=_parse(ha.get("latest_clinical_time"))
    bs=_parse(hb.get("earliest_clinical_time")); be=_parse(hb.get("latest_clinical_time"))

    if None in {as_,ae,bs,be}:
        return "INDETERMINATE","TEMPORAL_HULL_UNAVAILABLE"

    # Point scope when start == end.
    a_point=as_==ae; b_point=bs==be
    if a_point and b_point:
        return ("TRUE","SAME_INSTANT") if as_==bs else ("FALSE","DISTINCT_INSTANTS")
    if a_point:
        return ("TRUE","POINT_WITHIN_HALF_OPEN_INTERVAL") if bs<=as_<be else ("FALSE","POINT_OUTSIDE_INTERVAL")
    if b_point:
        return ("TRUE","POINT_WITHIN_HALF_OPEN_INTERVAL") if as_<=bs<ae else ("FALSE","POINT_OUTSIDE_INTERVAL")

    # half-open [start,end)
    return ("TRUE","HALF_OPEN_INTERVALS_INTERSECT") if max(as_,bs)<min(ae,be) else ("FALSE","HALF_OPEN_INTERVALS_DISJOINT")
