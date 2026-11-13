from typing import Dict, List, Tuple
from .models import ClinicalPropositionIR, BoundParameter
from .operator_registry import OperatorSpec
from .reason_codes import ReasonCode

def _valid_value(name, value):
    if name in {"shift_days", "delay_days", "event_duration_days"}:
        return isinstance(value, (int, float)) and value >= 0
    if name in {"slope_delta", "decline_fraction", "recovery_fraction"}:
        return isinstance(value, (int, float)) and value > 0
    if name in {"resample_strategy", "redundancy_key", "observation_key", "target_unit", "conversion_id"}:
        return isinstance(value, str) and len(value.strip()) > 0
    if name == "mutable_fields":
        return isinstance(value, list) and len(value) > 0 and all(isinstance(x, str) and x for x in value)
    return value is not None

def bind_parameters(ir: ClinicalPropositionIR, spec: OperatorSpec, config: Dict):
    bound: List[BoundParameter] = []
    reasons: List[str] = []
    operator_cfg = (config.get("operator_parameters") or {}).get(spec.operator_id, {})

    for name in spec.required_parameters:
        evidence = ir.parameter_evidence.get(name)
        if evidence is not None:
            if evidence.source_kind not in spec.allowed_parameter_sources:
                reasons.append(f"{ReasonCode.UNSUPPORTED_PARAMETER_SOURCE.value}:{name}:{evidence.source_kind}")
                continue
            value = evidence.value
            source_kind = evidence.source_kind
            source_ref = evidence.source_ref
        elif name in operator_cfg:
            cfg_item = operator_cfg[name]
            value = cfg_item.get("value")
            source_kind = "compiler_config"
            source_ref = cfg_item.get("source_ref", "compiler_config")
        else:
            reasons.append(f"{ReasonCode.MISSING_PARAMETER.value}:{name}")
            continue

        if not _valid_value(name, value):
            reasons.append(f"{ReasonCode.INVALID_PARAMETER_VALUE.value}:{name}")
            continue
        bound.append(BoundParameter(name, value, source_kind, source_ref))

    return (len(reasons) == 0), bound, reasons
