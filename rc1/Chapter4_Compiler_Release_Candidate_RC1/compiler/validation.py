from .models import (
    ClinicalPropositionIR, FROZEN_GATES, ALLOWED_GATE_VALUES,
    ALLOWED_TRUTH, ALLOWED_DISPOSITIONS
)

def validate_ir(ir: ClinicalPropositionIR):
    errors = []
    if not ir.proposition_id:
        errors.append("proposition_id is required")
    if ir.disposition not in ALLOWED_DISPOSITIONS:
        errors.append(f"invalid disposition: {ir.disposition}")
    if ir.temporal_truth not in ALLOWED_TRUTH:
        errors.append(f"invalid temporal_truth: {ir.temporal_truth}")
    missing_gates = [g for g in FROZEN_GATES if g not in ir.gates]
    if missing_gates:
        errors.append("missing gates: " + ",".join(missing_gates))
    extra_gates = [g for g in ir.gates if g not in FROZEN_GATES]
    if extra_gates:
        errors.append("unknown gates: " + ",".join(extra_gates))
    for g, v in ir.gates.items():
        if v not in ALLOWED_GATE_VALUES:
            errors.append(f"invalid gate status {g}={v}")
    for name, evidence in ir.parameter_evidence.items():
        if not evidence.source_kind:
            errors.append(f"parameter {name}: source_kind is required")
        if not evidence.source_ref:
            errors.append(f"parameter {name}: source_ref is required")
    if errors:
        raise ValueError("; ".join(errors))

def preselection_gate_state(ir: ClinicalPropositionIR):
    # Approved C4 rule: selection may occur before final conflict/release admission,
    # but hard semantic gate failures block selection.
    semantic_gates = ("SourceLocated", "ScopeMatched", "Computable", "TerminologyReady", "ReviewSufficient")
    failed = [g for g in semantic_gates if ir.gates[g] == "Fail"]
    pending = [g for g in semantic_gates if ir.gates[g] == "Pending"]
    if failed:
        return "FAIL", failed
    if pending:
        return "PENDING", pending
    return "PASS", []

def admission_state(ir: ClinicalPropositionIR):
    if ir.disposition != "Executable":
        return "INELIGIBLE"
    if any(v == "Fail" for v in ir.gates.values()):
        return "INELIGIBLE"
    if any(v == "Pending" for v in ir.gates.values()):
        return "PENDING"
    return "ELIGIBLE"
