from .temporal_time import parse_utc, add_calendar_duration, fixed_duration_seconds

def k3_and(values):
    vals=list(values)
    if any(v=="FALSE" for v in vals):
        return "FALSE"
    if vals and all(v=="TRUE" for v in vals):
        return "TRUE"
    if not vals:
        return "TRUE"
    return "INDETERMINATE"

def _point_bounds(e):
    a=parse_utc(e.start_earliest)
    b=parse_utc(e.start_latest)
    return a,b

def _extent_bounds(e):
    s0=parse_utc(e.start_earliest)
    s1=parse_utc(e.start_latest)
    e0=parse_utc(e.end_earliest)
    e1=parse_utc(e.end_latest)
    return s0,s1,e0,e1

def _missing(*xs):
    return any(x is None for x in xs)

def eval_point_order(a,b,relation):
    a0,a1=_point_bounds(a); b0,b1=_point_bounds(b)
    if _missing(a0,a1,b0,b1):
        return "INDETERMINATE","REQUIRED_TIME_MISSING"
    if relation=="before":
        if a1 < b0: return "TRUE","ALL_ALLOWED_INSTANTS_SATISFY"
        if a0 >= b1: return "FALSE","NO_ALLOWED_INSTANTS_SATISFY"
        return "INDETERMINATE","PRECISION_SPANS_TRUE_AND_FALSE"
    if relation=="after":
        return eval_point_order(b,a,"before")
    if relation=="equalsTime":
        if a0==a1==b0==b1: return "TRUE","EXACT_NORMALIZED_INSTANT_EQUAL"
        if a1 < b0 or b1 < a0: return "FALSE","UNCERTAINTY_SETS_DISJOINT"
        return "INDETERMINATE","EQUALITY_NOT_INVARIANT_ACROSS_PRECISION"
    if relation=="sameClinicalTime":
        if a.time_domain!="clinical" or b.time_domain!="clinical":
            return "INDETERMINATE","SAME_CLINICAL_TIME_REQUIRES_CLINICAL_DOMAIN"
        if a0==b0 and a1==b1 and a.precision==b.precision:
            return "TRUE","SAME_AVAILABLE_CLINICAL_PRECISION"
        if a1 < b0 or b1 < a0:
            return "FALSE","CLINICAL_TIME_UNCERTAINTY_DISJOINT"
        return "INDETERMINATE","MIXED_OR_OVERLAPPING_PRECISION"
    raise ValueError(relation)

def _exact_interval_relation(sa,ea,sb,eb,relation):
    if relation=="before": return ea < sb
    if relation=="after": return eb < sa
    if relation=="meets": return ea == sb
    if relation=="metBy": return eb == sa
    if relation=="overlaps": return sa < sb < ea < eb
    if relation=="overlappedBy": return sb < sa < eb < ea
    if relation=="starts": return sa == sb and ea < eb
    if relation=="startedBy": return sa == sb and eb < ea
    if relation=="during": return sb < sa and ea < eb
    if relation=="contains": return sa < sb and eb < ea
    if relation=="finishes": return sb < sa and ea == eb
    if relation=="finishedBy": return sa < sb and ea == eb
    if relation=="equalsTime": return sa==sb and ea==eb
    if relation in {"overlapsEventWindow","eventWindowOverlaps"}:
        return sa < eb and sb < ea  # half-open interval intersection
    raise ValueError(relation)

def eval_interval_relation(a,b,relation):
    sa0,sa1,ea0,ea1=_extent_bounds(a)
    sb0,sb1,eb0,eb1=_extent_bounds(b)
    if _missing(sa0,sa1,sb0,sb1):
        return "INDETERMINATE","REQUIRED_INTERVAL_BOUND_MISSING"
    if _missing(ea0,ea1,eb0,eb1):
        return "INDETERMINATE","OPEN_END_PREVENTS_END_DEPENDENT_RELATION"

    # For inequality/equality relations, corner evaluation provides safe TRUE/FALSE
    # when all endpoint extrema agree; disagreement is INDETERMINATE.
    vals=set()
    for sa in {sa0,sa1}:
      for ea in {ea0,ea1}:
       for sb in {sb0,sb1}:
        for eb in {eb0,eb1}:
         if sa>ea or sb>eb:
             continue
         vals.add(_exact_interval_relation(sa,ea,sb,eb,relation))
    if vals=={True}: return "TRUE","RELATION_TRUE_AT_ALL_ENDPOINT_EXTREMA"
    if vals=={False}: return "FALSE","RELATION_FALSE_AT_ALL_ENDPOINT_EXTREMA"
    return "INDETERMINATE","RELATION_VARIES_WITH_ALLOWED_PRECISION"

def eval_relation(a,b,relation):
    pointish={"INSTANT","UNCERTAIN_INSTANT"}
    if a.kind in pointish and b.kind in pointish and relation in {"before","after","equalsTime","sameClinicalTime"}:
        return eval_point_order(a,b,relation)
    return eval_interval_relation(a,b,relation)

def eval_duration(a,b,operator,duration_text):
    a0,a1=_point_bounds(a); b0,b1=_point_bounds(b)
    if _missing(a0,a1,b0,b1):
        return "INDETERMINATE","REQUIRED_TIME_MISSING"
    fixed=fixed_duration_seconds(duration_text)
    if fixed is None:
        # Calendar durations are anchored on B. Monotonicity of calendar addition
        # allows conservative all/none tests using B extrema.
        lower_anchor=add_calendar_duration(b1,duration_text)
        upper_anchor=add_calendar_duration(b0,duration_text)
        if operator=="AT_LEAST":
            if a0 >= lower_anchor: return "TRUE","CALENDAR_MINIMUM_TRUE_FOR_ALL"
            if a1 < upper_anchor: return "FALSE","CALENDAR_MINIMUM_FALSE_FOR_ALL"
            return "INDETERMINATE","CALENDAR_MINIMUM_PRECISION_OVERLAP"
        if operator=="AT_MOST":
            # Require non-negative ordered separation and upper bound.
            if a0 >= b1 and a1 <= add_calendar_duration(b0,duration_text):
                return "TRUE","CALENDAR_MAXIMUM_TRUE_FOR_ALL"
            if a1 < b0 or a0 > add_calendar_duration(b1,duration_text):
                return "FALSE","CALENDAR_MAXIMUM_FALSE_FOR_ALL"
            return "INDETERMINATE","CALENDAR_MAXIMUM_PRECISION_OVERLAP"
        raise ValueError(operator)

    min_delta=(a0-b1).total_seconds()
    max_delta=(a1-b0).total_seconds()
    if operator=="AT_LEAST":
        if min_delta>=fixed: return "TRUE","MINIMUM_SEPARATION_SATISFIED_FOR_ALL"
        if max_delta<fixed: return "FALSE","MINIMUM_SEPARATION_UNSATISFIED_FOR_ALL"
        return "INDETERMINATE","SEPARATION_PRECISION_SPANS_THRESHOLD"
    if operator=="AT_MOST":
        if min_delta>=0 and max_delta<=fixed: return "TRUE","MAXIMUM_SEPARATION_SATISFIED_FOR_ALL"
        if max_delta<0 or min_delta>fixed: return "FALSE","MAXIMUM_SEPARATION_UNSATISFIED_FOR_ALL"
        return "INDETERMINATE","SEPARATION_PRECISION_SPANS_THRESHOLD"
    raise ValueError(operator)

def eval_within(a,b,duration_text):
    a0,a1=_point_bounds(a); b0,b1=_point_bounds(b)
    if _missing(a0,a1,b0,b1):
        return "INDETERMINATE","REQUIRED_TIME_MISSING"
    fixed=fixed_duration_seconds(duration_text)
    if fixed is None:
        # WITHIN is used for day-scale maximum separation in R1.0 fixtures.
        return "INDETERMINATE","CALENDAR_WITHIN_REQUIRES_ANCHORED_DIRECTION"
    max_abs=max(abs((a0-b1).total_seconds()),abs((a1-b0).total_seconds()))
    if a1 < b0:
        min_abs=(b0-a1).total_seconds()
    elif b1 < a0:
        min_abs=(a0-b1).total_seconds()
    else:
        min_abs=0.0
    if max_abs<=fixed: return "TRUE","MAX_ABSOLUTE_SEPARATION_WITHIN_BOUND"
    if min_abs>fixed: return "FALSE","MIN_ABSOLUTE_SEPARATION_EXCEEDS_BOUND"
    return "INDETERMINATE","SEPARATION_PRECISION_SPANS_BOUND"

def eval_within_horizon(a,b,duration_text):
    # A must occur on/after B and no later than B + calendar duration.
    a0,a1=_point_bounds(a); b0,b1=_point_bounds(b)
    if _missing(a0,a1,b0,b1):
        return "INDETERMINATE","REQUIRED_TIME_MISSING"
    latest_all=add_calendar_duration(b0,duration_text)
    latest_any=add_calendar_duration(b1,duration_text)
    if a0>=b1 and a1<=latest_all:
        return "TRUE","WITHIN_CALENDAR_HORIZON_FOR_ALL"
    if a1<b0 or a0>latest_any:
        return "FALSE","OUTSIDE_CALENDAR_HORIZON_FOR_ALL"
    return "INDETERMINATE","HORIZON_TRUTH_DEPENDS_ON_ALLOWED_PRECISION"

def eval_occurs_during(a,b):
    # Reuse strict Allen during; exact equality is not "during" because starts/finishes/equals are separate.
    return eval_interval_relation(a,b,"during")

def eval_persists_for(a,duration_text):
    s0,s1,e0,e1=_extent_bounds(a)
    if _missing(s0,s1,e0,e1):
        return "INDETERMINATE","OPEN_OR_MISSING_PERSISTENCE_BOUND"
    fixed=fixed_duration_seconds(duration_text)
    if fixed is None:
        min_end=add_calendar_duration(s1,duration_text)
        max_end=add_calendar_duration(s0,duration_text)
        if e0>=min_end: return "TRUE","PERSISTENCE_MINIMUM_TRUE_FOR_ALL"
        if e1<max_end: return "FALSE","PERSISTENCE_MINIMUM_FALSE_FOR_ALL"
        return "INDETERMINATE","PERSISTENCE_PRECISION_SPANS_THRESHOLD"
    min_d=(e0-s1).total_seconds()
    max_d=(e1-s0).total_seconds()
    if min_d>=fixed: return "TRUE","PERSISTENCE_MINIMUM_TRUE_FOR_ALL"
    if max_d<fixed: return "FALSE","PERSISTENCE_MINIMUM_FALSE_FOR_ALL"
    return "INDETERMINATE","PERSISTENCE_PRECISION_SPANS_THRESHOLD"
