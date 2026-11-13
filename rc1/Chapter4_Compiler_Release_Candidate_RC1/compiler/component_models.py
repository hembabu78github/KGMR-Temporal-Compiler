from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

K3_VALUES = {"TRUE", "FALSE", "INDETERMINATE"}

RELATION_FAMILIES = (
    "EQUALITY_WITHIN_TOLERANCE",
    "MONOTONIC_INCREASE",
    "MONOTONIC_DECREASE",
    "ORDINAL_NONDECREASE",
    "ORDINAL_NONINCREASE",
    "BOUNDED_CHANGE",
    "DECISION_LEVEL",
)

PREDICATE_TYPE_ORDER = {
    "APPLICABILITY": 10,
    "CLINICAL": 20,
    "DATA_AVAILABILITY": 30,
    "TEMPORAL": 40,
    "TERMINOLOGY": 50,
}

@dataclass(frozen=True)
class ConditionAtom:
    predicate_id: str
    predicate_type: str
    arguments: Dict[str, Any]
    evaluator_id: str
    source_refs: List[str]
    missing_evidence_result: str = "INDETERMINATE"

    @staticmethod
    def from_obj(obj):
        return ConditionAtom(
            predicate_id=str(obj["predicate_id"]),
            predicate_type=str(obj["predicate_type"]),
            arguments=dict(obj.get("arguments", {})),
            evaluator_id=str(obj["evaluator_id"]),
            source_refs=list(obj.get("source_refs", [])),
            missing_evidence_result=str(obj.get("missing_evidence_result", "INDETERMINATE")),
        )

    def to_dict(self):
        return asdict(self)

@dataclass(frozen=True)
class RelationEvidence:
    relation_family: str
    source_ref: str
    parameters: Dict[str, Any]
    comparator_id: str
    source_output_selector: str
    followup_output_selector: str
    evidence_priority: int = 100
    applicable_operators: List[str] = field(default_factory=list)

    @staticmethod
    def from_obj(obj):
        return RelationEvidence(
            relation_family=str(obj["relation_family"]),
            source_ref=str(obj["source_ref"]),
            parameters=dict(obj.get("parameters", {})),
            comparator_id=str(obj["comparator_id"]),
            source_output_selector=str(obj["source_output_selector"]),
            followup_output_selector=str(obj["followup_output_selector"]),
            evidence_priority=int(obj.get("evidence_priority", 100)),
            applicable_operators=list(obj.get("applicable_operators", [])),
        )

    def to_dict(self):
        return asdict(self)

@dataclass
class ComponentGenerationInput:
    proposition_id: str
    condition_atoms: List[ConditionAtom]
    relation_evidence: List[RelationEvidence]
    source_refs: List[str]
    graph_path_ids: List[str]
    release_ref: str
    notes: str = ""

    @staticmethod
    def from_obj(obj):
        return ComponentGenerationInput(
            proposition_id=str(obj["proposition_id"]),
            condition_atoms=[ConditionAtom.from_obj(x) for x in obj.get("condition_atoms", [])],
            relation_evidence=[RelationEvidence.from_obj(x) for x in obj.get("relation_evidence", [])],
            source_refs=list(obj.get("source_refs", [])),
            graph_path_ids=list(obj.get("graph_path_ids", [])),
            release_ref=str(obj.get("release_ref", "")),
            notes=str(obj.get("notes", "")),
        )

@dataclass
class GeneratedPrecondition:
    status: str
    expression: Optional[Dict[str, Any]]
    atom_count: int
    reasons: List[str]

    def to_dict(self):
        return asdict(self)

@dataclass
class GeneratedTransformation:
    status: str
    operator_id: str
    operator_version: str
    bound_parameters: List[Dict[str, Any]]
    read_set: List[str]
    touch_set: List[str]
    forbidden_touch_set: List[str]
    reasons: List[str]

    def to_dict(self):
        return asdict(self)

@dataclass
class OutputRelationDraft:
    status: str
    relation_family: Optional[str]
    source_output_selector: Optional[str]
    followup_output_selector: Optional[str]
    comparator_id: Optional[str]
    parameters: Dict[str, Any]
    source_ref: Optional[str]
    candidate_families: List[str]
    reasons: List[str]

    def to_dict(self):
        return asdict(self)

@dataclass
class ComponentGenerationResult:
    proposition_id: str
    operator_id: str
    generation_status: str
    C: GeneratedPrecondition
    T: GeneratedTransformation
    R: OutputRelationDraft
    source_refs: List[str]
    graph_path_ids: List[str]
    release_ref: str
    c4_006_selection_fingerprint: str
    component_fingerprint: str
    notes: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "proposition_id": self.proposition_id,
            "operator_id": self.operator_id,
            "generation_status": self.generation_status,
            "C": self.C.to_dict(),
            "T": self.T.to_dict(),
            "R": self.R.to_dict(),
            "source_refs": list(self.source_refs),
            "graph_path_ids": list(self.graph_path_ids),
            "release_ref": self.release_ref,
            "c4_006_selection_fingerprint": self.c4_006_selection_fingerprint,
            "component_fingerprint": self.component_fingerprint,
            "notes": list(self.notes),
        }
