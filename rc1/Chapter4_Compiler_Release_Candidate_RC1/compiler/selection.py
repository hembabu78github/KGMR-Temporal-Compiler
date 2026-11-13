import hashlib
import json
from typing import Dict, List
from .models import ClinicalPropositionIR, OperatorDecision, OperatorSelectionResult
from .operator_registry import OPERATOR_REGISTRY
from .parameter_binding import bind_parameters
from .reason_codes import ReasonCode
from .validation import validate_ir, preselection_gate_state, admission_state
from .version import COMPILER_VERSION, OPERATOR_LIBRARY_VERSION

def _canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def _fingerprint(proposition_id, decisions):
    payload = {
        "proposition_id": proposition_id,
        "compiler_version": COMPILER_VERSION,
        "operator_library_version": OPERATOR_LIBRARY_VERSION,
        "decisions": [d.to_dict() for d in decisions],
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()

def _special_checks(ir, spec):
    reasons = []
    if spec.requires_temporal_truth:
        if ir.temporal_truth == "INDETERMINATE":
            reasons.append(ReasonCode.TEMPORAL_INDETERMINATE.value)
        elif ir.temporal_truth == "FALSE":
            reasons.append(ReasonCode.TEMPORAL_FALSE.value)

    if spec.requires_direction_semantics and not ir.direction_semantics:
        reasons.append(ReasonCode.DIRECTION_SEMANTICS_MISSING.value)

    if spec.special_rule == "mask_required_observation":
        if "DECISION_LEVEL" not in set(ir.permitted_relation_families):
            reasons.append(ReasonCode.MASK_REQUIRES_DECISION_LEVEL.value)

    if spec.special_rule == "aki_like_only":
        if not bool(ir.capabilities.get("supports_aki_like_event")):
            reasons.append(ReasonCode.AKI_REQUIRES_AKI_LIKE_EVENT_SEMANTICS.value)
        if not bool(ir.capabilities.get("has_recovery_semantics")):
            reasons.append(ReasonCode.AKI_REQUIRES_RECOVERY_SEMANTICS.value)

    permitted = sorted(set(ir.permitted_relation_families) & set(spec.permitted_relations))
    if not permitted:
        reasons.append(ReasonCode.RELATION_NOT_ALLOWED.value)
    return reasons, permitted

def select_operators(ir: ClinicalPropositionIR, config: Dict) -> OperatorSelectionResult:
    validate_ir(ir)
    notes: List[str] = []
    decisions: List[OperatorDecision] = []

    admission = admission_state(ir)

    if ir.disposition != "Executable":
        for spec in OPERATOR_REGISTRY:
            decisions.append(OperatorDecision(
                spec.operator_id, False, False,
                [ReasonCode.DISPOSITION_NOT_EXECUTABLE.value],
                [], []
            ))
        fp = _fingerprint(ir.proposition_id, decisions)
        return OperatorSelectionResult(
            ir.proposition_id, COMPILER_VERSION, OPERATOR_LIBRARY_VERSION,
            "BLOCKED", admission, dict(ir.gates), decisions, [], fp,
            ["Context-only/excluded knowledge is not compiled."]
        )

    gate_state, gate_list = preselection_gate_state(ir)
    if gate_state != "PASS":
        code = ReasonCode.PRE_GATE_FAIL.value if gate_state == "FAIL" else ReasonCode.PRE_GATE_PENDING.value
        for spec in OPERATOR_REGISTRY:
            decisions.append(OperatorDecision(
                spec.operator_id, False, False,
                [code + ":" + ",".join(gate_list)], [], []
            ))
        fp = _fingerprint(ir.proposition_id, decisions)
        return OperatorSelectionResult(
            ir.proposition_id, COMPILER_VERSION, OPERATOR_LIBRARY_VERSION,
            "BLOCKED", admission, dict(ir.gates), decisions, [], fp,
            [f"Preselection gate state is {gate_state}: {','.join(gate_list)}"]
        )

    for spec in OPERATOR_REGISTRY:
        reasons = []
        for cap in spec.required_capabilities:
            if not bool(ir.capabilities.get(cap)):
                reasons.append(f"{ReasonCode.MISSING_CAPABILITY.value}:{cap}")

        special_reasons, permitted = _special_checks(ir, spec)
        reasons.extend(special_reasons)

        compatible = len(reasons) == 0
        parameterized = False
        bound = []
        if compatible:
            ok, bound, param_reasons = bind_parameters(ir, spec, config)
            reasons.extend(param_reasons)
            parameterized = ok

        decisions.append(OperatorDecision(
            operator_id=spec.operator_id,
            compatible=compatible,
            parameterized=parameterized,
            reasons=reasons,
            bound_parameters=bound,
            permitted_relations=permitted,
        ))

    # "Selected" means compatible AND fully parameterized. All such operators are emitted.
    selected = [d.operator_id for d in decisions if d.compatible and d.parameterized]
    if selected:
        status = "SELECTED"
    elif any(d.compatible for d in decisions):
        status = "PARAMETERIZATION_BLOCKED"
    else:
        status = "NO_COMPATIBLE_OPERATORS"

    if admission == "PENDING":
        notes.append("Operator compatibility was assessed, but final MR admission remains Pending.")
    elif admission == "INELIGIBLE":
        notes.append("Operator compatibility does not override final admission ineligibility.")

    fp = _fingerprint(ir.proposition_id, decisions)
    return OperatorSelectionResult(
        ir.proposition_id, COMPILER_VERSION, OPERATOR_LIBRARY_VERSION,
        status, admission, dict(ir.gates), decisions, selected, fp, notes
    )
