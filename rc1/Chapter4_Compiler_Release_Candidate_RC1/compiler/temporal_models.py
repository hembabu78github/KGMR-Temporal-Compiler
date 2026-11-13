from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

K3 = {"TRUE","FALSE","INDETERMINATE"}
TIME_DOMAINS = {"clinical","availability","provenance"}
ENTITY_KINDS = {"INSTANT","INTERVAL","UNCERTAIN_INSTANT","OPEN_INTERVAL"}

@dataclass(frozen=True)
class TemporalEntity:
    entity_id: str
    kind: str
    time_domain: str
    start_earliest: Optional[str]
    start_latest: Optional[str]
    end_earliest: Optional[str] = None
    end_latest: Optional[str] = None
    precision: str = "exact"
    lexical_value: Optional[str] = None
    source_refs: List[str] = field(default_factory=list)

    @staticmethod
    def from_obj(obj):
        return TemporalEntity(
            entity_id=str(obj["entity_id"]),
            kind=str(obj["kind"]),
            time_domain=str(obj["time_domain"]),
            start_earliest=obj.get("start_earliest"),
            start_latest=obj.get("start_latest"),
            end_earliest=obj.get("end_earliest"),
            end_latest=obj.get("end_latest"),
            precision=str(obj.get("precision","exact")),
            lexical_value=obj.get("lexical_value"),
            source_refs=list(obj.get("source_refs",[])),
        )

@dataclass(frozen=True)
class TemporalConstraint:
    constraint_id: str
    operator: str
    left: str
    right: Optional[str]
    duration: Optional[str]
    time_domain: str
    source_refs: List[str]
    comparator: Optional[str] = None

    @staticmethod
    def from_obj(obj):
        return TemporalConstraint(
            constraint_id=str(obj["constraint_id"]),
            operator=str(obj["operator"]),
            left=str(obj["left"]),
            right=obj.get("right"),
            duration=obj.get("duration"),
            time_domain=str(obj.get("time_domain","clinical")),
            source_refs=list(obj.get("source_refs",[])),
            comparator=obj.get("comparator"),
        )

@dataclass
class TemporalCase:
    proposition_id: str
    entities: List[TemporalEntity]
    constraints: List[TemporalConstraint]
    release_ref: str
    notes: str = ""

    @staticmethod
    def from_obj(obj):
        return TemporalCase(
            proposition_id=str(obj["proposition_id"]),
            entities=[TemporalEntity.from_obj(x) for x in obj.get("entities",[])],
            constraints=[TemporalConstraint.from_obj(x) for x in obj.get("constraints",[])],
            release_ref=str(obj.get("release_ref","")),
            notes=str(obj.get("notes","")),
        )

@dataclass(frozen=True)
class ConstraintEvaluation:
    constraint_id: str
    operator: str
    truth: str
    reason: str
    source_refs: List[str]

    def to_dict(self):
        return asdict(self)

@dataclass
class TemporalSatisfiabilityResult:
    proposition_id: str
    operator_id: str
    component_fingerprint: str
    c4_010_exception_fingerprint: str
    temporal_status: str
    temporal_truth: str
    system_action: str
    constraint_evaluations: List[ConstraintEvaluation]
    structural_conflicts: List[str]
    temporal_scope_hull: Dict[str, Optional[str]]
    temporal_fingerprint: str
    notes: List[str]

    def to_dict(self):
        return {
          "proposition_id":self.proposition_id,
          "operator_id":self.operator_id,
          "component_fingerprint":self.component_fingerprint,
          "c4_010_exception_fingerprint":self.c4_010_exception_fingerprint,
          "temporal_status":self.temporal_status,
          "temporal_truth":self.temporal_truth,
          "system_action":self.system_action,
          "constraint_evaluations":[x.to_dict() for x in self.constraint_evaluations],
          "structural_conflicts":list(self.structural_conflicts),
          "temporal_scope_hull":dict(self.temporal_scope_hull),
          "temporal_fingerprint":self.temporal_fingerprint,
          "notes":list(self.notes),
        }
