import hashlib, json
from .exception_models import ExceptionPrecedenceResult, PrecedenceTraceStep
from .exception_assembly import assemble_exceptions

TIER_PRINCIPLES = {
    "P0":"Input integrity / legality",
    "P1":"Applicability",
    "P2":"Explicit linked exception",
    "P3":"Temporal/event semantics",
    "P4":"Specificity",
    "P5":"Release/version",
    "P6":"Guideline strength metadata only",
    "P7":"Human adjudication",
    "P8":"Unresolved safety / abstention",
}

def _canon(x):
    return json.dumps(x, sort_keys=True, separators=(",",":"), ensure_ascii=False)

def _fingerprint(payload):
    return hashlib.sha256(_canon(payload).encode("utf-8")).hexdigest()

def _step(trace, tier, decision, refs=None):
    trace.append(PrecedenceTraceStep(
        tier=tier,
        principle=TIER_PRINCIPLES[tier],
        decision=decision,
        evidence_refs=sorted(refs or [])
    ))

def _active(assembled):
    return [
        x for x in assembled
        if x.assembly_status=="ASSEMBLED"
        and x.condition["observed_fixture_truth"] in {"TRUE","INDETERMINATE"}
    ]

def _finalize(proposition_id, operator_id, assembled, outcome, truth, action, gate, trace, notes):
    payload={
      "proposition_id":proposition_id,
      "operator_id":operator_id,
      "assembled_exceptions":[x.to_dict() for x in assembled],
      "precedence_outcome":outcome,
      "semantic_truth":truth,
      "system_action":action,
      "conflict_resolved_gate":gate,
      "trace":[x.to_dict() for x in trace],
    }
    return ExceptionPrecedenceResult(
        proposition_id,operator_id,
        "ASSEMBLED" if all(x.assembly_status=="ASSEMBLED" for x in assembled) else "INVALID",
        assembled,outcome,truth,action,gate,trace,_fingerprint(payload),notes
    )

def resolve_exception_precedence(proposition_id, operator_id, evidence_rows, context, config):
    assembled=assemble_exceptions(proposition_id, operator_id, evidence_rows, config)
    trace=[]
    notes=[]

    if any(x.assembly_status!="ASSEMBLED" for x in assembled):
        _step(trace,"P0","INVALID_EXCEPTION_STRUCTURE")
        return _finalize(
            proposition_id,operator_id,assembled,
            "INVALID_INPUT","INDETERMINATE","ABSTAIN","Pending",
            trace,["Invalid exception structure is not a clinical FALSE."]
        )

    # P0 — integrity/legality
    if context.input_integrity_truth=="FALSE":
        _step(trace,"P0","INPUT_INTEGRITY_FAILED")
        return _finalize(proposition_id,operator_id,assembled,
                         "INELIGIBLE","INDETERMINATE","ABSTAIN","Pending",trace,notes)
    if context.input_integrity_truth=="INDETERMINATE":
        _step(trace,"P0","INPUT_INTEGRITY_INDETERMINATE")
        return _finalize(proposition_id,operator_id,assembled,
                         "PENDING","INDETERMINATE","ABSTAIN","Pending",trace,notes)
    _step(trace,"P0","PASS")

    # Some frozen exception types directly instantiate P0 effects.
    active=_active(assembled)
    active_true=[x for x in active if x.condition["observed_fixture_truth"]=="TRUE"]
    active_indet=[x for x in active if x.condition["observed_fixture_truth"]=="INDETERMINATE"]

    p0_types={"DataQualityException","MissingDataException","TerminologyMappingException",
              "LicensingReleaseException","ReviewGateException"}
    p0=[x for x in active_true if x.exception_type in p0_types]
    p0_indet=[x for x in active_indet if x.exception_type in p0_types]

    if p0_indet:
        refs=[r for x in p0_indet for r in x.source_refs]
        _step(trace,"P0","P0_EXCEPTION_INDETERMINATE",refs)
        return _finalize(proposition_id,operator_id,assembled,
                         "PENDING","INDETERMINATE","ABSTAIN","Pending",trace,notes)

    # Licensing and review are compilation/release controls; data/missing/terminology are safe non-decision controls.
    for typ,outcome in [
        ("LicensingReleaseException","RELEASE_BLOCKED"),
        ("ReviewGateException","COMPILATION_BLOCKED"),
        ("DataQualityException","INELIGIBLE"),
        ("MissingDataException","ABSTAIN"),
        ("TerminologyMappingException","LOCAL_ONLY_OR_BLOCKED"),
    ]:
        xs=[x for x in p0 if x.exception_type==typ]
        if xs:
            refs=[r for x in xs for r in x.source_refs]
            _step(trace,"P0",f"{typ}:{outcome}",refs)
            if typ=="TerminologyMappingException" and all(x.effect_mode=="LOCAL_FALLBACK_AVAILABLE" for x in xs):
                notes.append("External mapping blocked; explicitly available local concept may continue.")
                break
            return _finalize(
                proposition_id,operator_id,assembled,outcome,"INDETERMINATE","ABSTAIN","Pending",trace,notes
            )

    # P1 — applicability
    app_ex=[x for x in active_true if x.exception_type=="ApplicabilityExclusion"]
    if context.applicability_truth=="FALSE" or app_ex:
        refs=[r for x in app_ex for r in x.source_refs]
        _step(trace,"P1","NOT_APPLICABLE",refs)
        return _finalize(proposition_id,operator_id,assembled,
                         "NOT_APPLICABLE","FALSE","DO_NOT_FIRE","Pass",trace,notes)
    if context.applicability_truth=="INDETERMINATE":
        _step(trace,"P1","APPLICABILITY_INDETERMINATE")
        return _finalize(proposition_id,operator_id,assembled,
                         "PENDING","INDETERMINATE","ABSTAIN","Pending",trace,notes)
    _step(trace,"P1","PASS")

    # P2 — explicit linked exception only. Assembly already enforced explicit links.
    _step(trace,"P2",f"EXPLICIT_LINK_SCOPE_ENFORCED:{len(active)}")

    # P3 — temporal/event semantics
    temporal_precision=[x for x in active_true if x.exception_type=="TemporalPrecisionException"]
    temporal_indet=[x for x in active_indet if x.precedence_tier=="P3"]
    if context.temporal_event_truth=="INDETERMINATE" or temporal_precision or temporal_indet:
        refs=[r for x in temporal_precision+temporal_indet for r in x.source_refs]
        _step(trace,"P3","TEMPORAL_EVENT_INDETERMINATE",refs)
        return _finalize(proposition_id,operator_id,assembled,
                         "PENDING","INDETERMINATE","ABSTAIN","Pending",trace,notes)
    if context.temporal_event_truth=="FALSE":
        _step(trace,"P3","TEMPORAL_EVENT_FALSE")
        return _finalize(proposition_id,operator_id,assembled,
                         "NOT_APPLICABLE","FALSE","DO_NOT_FIRE","Pass",trace,notes)

    qualifiers=[x for x in active_true if x.exception_type in
                {"ClinicalEventException","MedicationContextException"}]
    if qualifiers:
        refs=[r for x in qualifiers for r in x.source_refs]
        _step(trace,"P3","QUALIFIED_LINKED_SCOPE",refs)
        notes.append("Qualifier affects only its explicitly linked segment/window; no global override.")
    else:
        _step(trace,"P3","PASS")

    # P4 — specificity can only be used with explicit containment evidence.
    if context.explicit_scope_containment_ref:
        _step(trace,"P4","EXPLICIT_SCOPE_CONTAINMENT_AVAILABLE",
              [context.explicit_scope_containment_ref])
    else:
        _step(trace,"P4","NO_SPECIFICITY_DECISION")
    # Never infer specificity from labels/text.

    # P5 — release/version
    if context.release_lineage_status=="SUPERSEDED":
        _step(trace,"P5","SUPERSEDED_VERSION_EXCLUDED")
        return _finalize(proposition_id,operator_id,assembled,
                         "INELIGIBLE","INDETERMINATE","ABSTAIN","Pending",trace,notes)
    if context.release_lineage_status=="AMBIGUOUS":
        _step(trace,"P5","VERSION_LINEAGE_AMBIGUOUS")
        # C4-012 will detect/group VersionConflict; here we safely preserve unresolved state.
        return _finalize(proposition_id,operator_id,assembled,
                         "PENDING","INDETERMINATE","ABSTAIN","Pending",trace,notes)
    _step(trace,"P5","CURRENT_RELEASE_PINNED")

    # P6 — guideline strength is metadata only.
    if context.guideline_strength_metadata:
        _step(trace,"P6","RECORDED_METADATA_ONLY")
        notes.append("Guideline strength/certainty was not used as an automatic precedence tiebreaker.")
    else:
        _step(trace,"P6","NO_STRENGTH_METADATA")

    # Explicit ConflictException or supplied unresolved-conflict signal survives to P7/P8.
    conflict_ex=[x for x in active_true if x.exception_type=="ConflictException"]
    unresolved = bool(conflict_ex) or bool(context.unresolved_conflict)

    if unresolved:
        if context.adjudication_status=="ADJUDICATED" and context.adjudication_ref:
            _step(trace,"P7","HUMAN_ADJUDICATION_APPLIED",[context.adjudication_ref])
            return _finalize(proposition_id,operator_id,assembled,
                             "ADJUDICATED","TRUE","PROCEED","Pass",trace,notes)
        _step(trace,"P7","HUMAN_ADJUDICATION_REQUIRED")
        _step(trace,"P8","SAFE_ABSTENTION_NO_ARBITRARY_WINNER")
        return _finalize(proposition_id,operator_id,assembled,
                         "UNRESOLVED","INDETERMINATE","ABSTAIN","Fail",trace,
                         notes+["ConflictResolved cannot pass while the contradiction is unresolved."])

    _step(trace,"P7","NOT_REQUIRED")
    _step(trace,"P8","NOT_REACHED_AS_FAILURE")

    outcome="QUALIFIED" if qualifiers else "PROCEED"
    return _finalize(proposition_id,operator_id,assembled,
                     outcome,"TRUE","PROCEED","Pass",trace,notes)
