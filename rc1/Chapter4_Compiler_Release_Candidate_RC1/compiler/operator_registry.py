from dataclasses import dataclass
from typing import Tuple, FrozenSet

@dataclass(frozen=True)
class OperatorSpec:
    operator_id: str
    category: str
    order: int
    required_capabilities: Tuple[str, ...]
    required_parameters: Tuple[str, ...]
    allowed_parameter_sources: FrozenSet[str]
    permitted_relations: FrozenSet[str]
    requires_temporal_truth: bool = False
    requires_direction_semantics: bool = False
    special_rule: str = ""

ALLOWED_PARAMETER_SOURCES = frozenset({"kg", "source_evidence", "compiler_config"})

# Canonical order is frozen for R1.0 and is independent of set/dict iteration order.
OPERATOR_REGISTRY = (
    OperatorSpec(
        "SHIFT_TIME", "timing_sampling", 10,
        ("has_temporal_structure",), ("shift_days",), ALLOWED_PARAMETER_SOURCES,
        frozenset({"EQUALITY_WITHIN_TOLERANCE", "PRESERVE_OUTPUT", "BOUNDED_CHANGE", "DECISION_LEVEL"}),
        True
    ),
    OperatorSpec(
        "RESAMPLE_TRAJECTORY", "timing_sampling", 20,
        ("has_trajectory", "has_sampling_semantics"), ("resample_strategy",), ALLOWED_PARAMETER_SOURCES,
        frozenset({"EQUALITY_WITHIN_TOLERANCE", "PRESERVE_OUTPUT", "BOUNDED_CHANGE", "ORDINAL_NONDECREASE", "ORDINAL_NONINCREASE"}),
        True
    ),
    OperatorSpec(
        "DELAY_RESULT_ENTRY", "timing_sampling", 30,
        ("has_effective_and_issued_time",), ("delay_days",), ALLOWED_PARAMETER_SOURCES,
        frozenset({"PRESERVE_OUTPUT", "DECISION_LEVEL", "BOUNDED_CHANGE"}),
        True
    ),
    OperatorSpec(
        "SWAP_EQUIVALENT_ORDER", "ordering_missingness", 40,
        ("has_equivalent_order_semantics",), tuple(), ALLOWED_PARAMETER_SOURCES,
        frozenset({"EQUALITY_WITHIN_TOLERANCE", "PRESERVE_OUTPUT"}),
        True
    ),
    OperatorSpec(
        "REMOVE_REDUNDANT_OBSERVATION", "ordering_missingness", 50,
        ("has_redundant_observation_semantics",), ("redundancy_key",), ALLOWED_PARAMETER_SOURCES,
        frozenset({"EQUALITY_WITHIN_TOLERANCE", "PRESERVE_OUTPUT", "BOUNDED_CHANGE"}),
        False
    ),
    OperatorSpec(
        "MASK_REQUIRED_OBSERVATION", "ordering_missingness", 60,
        ("has_required_observation", "supports_decision_level_missingness_oracle"), ("observation_key",), ALLOWED_PARAMETER_SOURCES,
        frozenset({"DECISION_LEVEL"}),
        False,
        special_rule="mask_required_observation"
    ),
    OperatorSpec(
        "INCREASE_SLOPE", "trend_event", 70,
        ("has_trajectory", "has_slope_semantics"), ("slope_delta",), ALLOWED_PARAMETER_SOURCES,
        frozenset({"MONOTONIC_INCREASE", "MONOTONIC_DECREASE", "ORDINAL_NONDECREASE", "ORDINAL_NONINCREASE", "BOUNDED_CHANGE"}),
        True, True
    ),
    OperatorSpec(
        "DECREASE_SLOPE", "trend_event", 80,
        ("has_trajectory", "has_slope_semantics"), ("slope_delta",), ALLOWED_PARAMETER_SOURCES,
        frozenset({"MONOTONIC_INCREASE", "MONOTONIC_DECREASE", "ORDINAL_NONDECREASE", "ORDINAL_NONINCREASE", "BOUNDED_CHANGE"}),
        True, True
    ),
    OperatorSpec(
        "INSERT_TRANSIENT_AKI", "trend_event", 90,
        ("supports_aki_like_event", "has_recovery_semantics"), ("decline_fraction", "event_duration_days", "recovery_fraction"), ALLOWED_PARAMETER_SOURCES,
        frozenset({"MONOTONIC_INCREASE", "MONOTONIC_DECREASE", "ORDINAL_NONDECREASE", "ORDINAL_NONINCREASE", "BOUNDED_CHANGE", "DECISION_LEVEL"}),
        True,
        special_rule="aki_like_only"
    ),
    OperatorSpec(
        "CONVERT_UNIT", "normalisation_invariant", 100,
        ("has_unit_conversion_semantics",), ("target_unit", "conversion_id"), ALLOWED_PARAMETER_SOURCES,
        frozenset({"EQUALITY_WITHIN_TOLERANCE", "PRESERVE_OUTPUT"}),
        False
    ),
    OperatorSpec(
        "PRESERVE_CLINICAL_STATE", "normalisation_invariant", 110,
        ("has_state_definition", "has_invariant_safe_dimensions"), ("mutable_fields",), ALLOWED_PARAMETER_SOURCES,
        frozenset({"EQUALITY_WITHIN_TOLERANCE", "PRESERVE_OUTPUT", "ORDINAL_NONDECREASE", "ORDINAL_NONINCREASE", "DECISION_LEVEL"}),
        False
    ),
)

OPERATOR_BY_ID = {x.operator_id: x for x in OPERATOR_REGISTRY}
