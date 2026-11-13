from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

K3_VALUES = {"TRUE","FALSE","INDETERMINATE"}
PRECEDENCE_TIERS = tuple(f"P{i}" for i in range(9))

@dataclass(frozen=True)
class ExceptionEvidence:
    exception_ref: str
    exception_type: str
    linked_proposition_id: str
    linked_operator_ids: List[str]
    scope_ref: str
    condition_truth: str
    condition_id: str
    evaluator_id: str
    source_refs: List[str]
    precedence_tier: str
    effect_mode: str = "DEFAULT"
    phase: str = "compile_time"
    specificity_scope_ref: Optional[str] = None
    version_lineage_ref: Optional[str] = None
    release_pinned_current: Optional[bool] = None
    clinically_meaningful: bool = False
    adjudication_status: str = "NOT_REQUIRED"
    adjudication_ref: Optional[str] = None
    guideline_strength_metadata: Optional[Dict[str, Any]] = None

    @staticmethod
    def from_obj(obj):
        return ExceptionEvidence(
            exception_ref=str(obj["exception_ref"]),
            exception_type=str(obj["exception_type"]),
            linked_proposition_id=str(obj["linked_proposition_id"]),
            linked_operator_ids=list(obj.get("linked_operator_ids", [])),
            scope_ref=str(obj["scope_ref"]),
            condition_truth=str(obj["condition_truth"]),
            condition_id=str(obj["condition_id"]),
            evaluator_id=str(obj["evaluator_id"]),
            source_refs=list(obj.get("source_refs", [])),
            precedence_tier=str(obj["precedence_tier"]),
            effect_mode=str(obj.get("effect_mode","DEFAULT")),
            phase=str(obj.get("phase","compile_time")),
            specificity_scope_ref=obj.get("specificity_scope_ref"),
            version_lineage_ref=obj.get("version_lineage_ref"),
            release_pinned_current=obj.get("release_pinned_current"),
            clinically_meaningful=bool(obj.get("clinically_meaningful",False)),
            adjudication_status=str(obj.get("adjudication_status","NOT_REQUIRED")),
            adjudication_ref=obj.get("adjudication_ref"),
            guideline_strength_metadata=obj.get("guideline_strength_metadata"),
        )

@dataclass(frozen=True)
class AssembledException:
    exception_ref: str
    exception_type: str
    linked_proposition_id: str
    linked_operator_id: str
    scope_ref: str
    condition: Dict[str, Any]
    precedence_tier: str
    effect_mode: str
    phase: str
    source_refs: List[str]
    assembly_status: str
    reasons: List[str]

    def to_dict(self):
        return asdict(self)

@dataclass
class PrecedenceContext:
    proposition_id: str
    operator_id: str
    input_integrity_truth: str = "TRUE"
    applicability_truth: str = "TRUE"
    temporal_event_truth: str = "TRUE"
    explicit_scope_containment_ref: Optional[str] = None
    release_lineage_status: str = "CURRENT"
    guideline_strength_metadata: Dict[str, Any] = field(default_factory=dict)
    adjudication_status: str = "NOT_REQUIRED"
    adjudication_ref: Optional[str] = None
    unresolved_conflict: bool = False

    @staticmethod
    def from_obj(obj):
        return PrecedenceContext(
            proposition_id=str(obj["proposition_id"]),
            operator_id=str(obj["operator_id"]),
            input_integrity_truth=str(obj.get("input_integrity_truth","TRUE")),
            applicability_truth=str(obj.get("applicability_truth","TRUE")),
            temporal_event_truth=str(obj.get("temporal_event_truth","TRUE")),
            explicit_scope_containment_ref=obj.get("explicit_scope_containment_ref"),
            release_lineage_status=str(obj.get("release_lineage_status","CURRENT")),
            guideline_strength_metadata=dict(obj.get("guideline_strength_metadata",{})),
            adjudication_status=str(obj.get("adjudication_status","NOT_REQUIRED")),
            adjudication_ref=obj.get("adjudication_ref"),
            unresolved_conflict=bool(obj.get("unresolved_conflict",False)),
        )

@dataclass
class PrecedenceTraceStep:
    tier: str
    principle: str
    decision: str
    evidence_refs: List[str]

    def to_dict(self):
        return asdict(self)

@dataclass
class ExceptionPrecedenceResult:
    proposition_id: str
    operator_id: str
    assembly_status: str
    assembled_exceptions: List[AssembledException]
    precedence_outcome: str
    semantic_truth: str
    system_action: str
    conflict_resolved_gate: str
    trace: List[PrecedenceTraceStep]
    exception_fingerprint: str
    notes: List[str]

    def to_dict(self):
        return {
            "proposition_id": self.proposition_id,
            "operator_id": self.operator_id,
            "assembly_status": self.assembly_status,
            "assembled_exceptions": [x.to_dict() for x in self.assembled_exceptions],
            "precedence_outcome": self.precedence_outcome,
            "semantic_truth": self.semantic_truth,
            "system_action": self.system_action,
            "conflict_resolved_gate": self.conflict_resolved_gate,
            "trace": [x.to_dict() for x in self.trace],
            "exception_fingerprint": self.exception_fingerprint,
            "notes": list(self.notes),
        }
