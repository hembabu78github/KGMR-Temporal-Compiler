from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

FROZEN_GATES = (
    "SourceLocated",
    "ScopeMatched",
    "Computable",
    "TerminologyReady",
    "LicensingAllowed",
    "ReviewSufficient",
    "ConflictResolved",
    "ReleaseIntegrity",
)

ALLOWED_GATE_VALUES = {"Pass", "Fail", "Pending", "NotApplicable"}
ALLOWED_TRUTH = {"TRUE", "FALSE", "INDETERMINATE"}
ALLOWED_DISPOSITIONS = {"Executable", "ContextOnly", "Excluded"}

@dataclass(frozen=True)
class ParameterEvidence:
    value: Any
    source_kind: str
    source_ref: str

    @staticmethod
    def from_obj(obj: Dict[str, Any]) -> "ParameterEvidence":
        return ParameterEvidence(
            value=obj.get("value"),
            source_kind=str(obj.get("source_kind", "")),
            source_ref=str(obj.get("source_ref", "")),
        )

@dataclass
class ClinicalPropositionIR:
    proposition_id: str
    source_knowledge_item_ids: List[str]
    decision_contract: str
    disposition: str
    graph_pattern_family: str
    capabilities: Dict[str, Any]
    parameter_evidence: Dict[str, ParameterEvidence]
    gates: Dict[str, str]
    permitted_relation_families: List[str]
    direction_semantics: Optional[str] = None
    temporal_truth: str = "TRUE"
    exceptions: List[str] = field(default_factory=list)
    provenance_refs: List[str] = field(default_factory=list)
    release_ref: str = ""
    notes: str = ""

    @staticmethod
    def from_obj(obj: Dict[str, Any]) -> "ClinicalPropositionIR":
        pe = {
            k: ParameterEvidence.from_obj(v)
            for k, v in (obj.get("parameter_evidence") or {}).items()
        }
        return ClinicalPropositionIR(
            proposition_id=str(obj["proposition_id"]),
            source_knowledge_item_ids=list(obj.get("source_knowledge_item_ids", [])),
            decision_contract=str(obj.get("decision_contract", "")),
            disposition=str(obj.get("disposition", "Executable")),
            graph_pattern_family=str(obj.get("graph_pattern_family", "")),
            capabilities=dict(obj.get("capabilities", {})),
            parameter_evidence=pe,
            gates=dict(obj.get("gates", {})),
            permitted_relation_families=list(obj.get("permitted_relation_families", [])),
            direction_semantics=obj.get("direction_semantics"),
            temporal_truth=str(obj.get("temporal_truth", "TRUE")),
            exceptions=list(obj.get("exceptions", [])),
            provenance_refs=list(obj.get("provenance_refs", [])),
            release_ref=str(obj.get("release_ref", "")),
            notes=str(obj.get("notes", "")),
        )

@dataclass(frozen=True)
class BoundParameter:
    name: str
    value: Any
    source_kind: str
    source_ref: str

@dataclass
class OperatorDecision:
    operator_id: str
    compatible: bool
    parameterized: bool
    reasons: List[str]
    bound_parameters: List[BoundParameter]
    permitted_relations: List[str]

    def to_dict(self):
        return {
            "operator_id": self.operator_id,
            "compatible": self.compatible,
            "parameterized": self.parameterized,
            "reasons": list(self.reasons),
            "bound_parameters": [asdict(x) for x in self.bound_parameters],
            "permitted_relations": list(self.permitted_relations),
        }

@dataclass
class OperatorSelectionResult:
    proposition_id: str
    compiler_version: str
    operator_library_version: str
    selection_status: str
    admission_status: str
    gate_snapshot: Dict[str, str]
    operator_decisions: List[OperatorDecision]
    selected_operators: List[str]
    selection_fingerprint: str
    notes: List[str]

    def to_dict(self):
        return {
            "proposition_id": self.proposition_id,
            "compiler_version": self.compiler_version,
            "operator_library_version": self.operator_library_version,
            "selection_status": self.selection_status,
            "admission_status": self.admission_status,
            "gate_snapshot": dict(self.gate_snapshot),
            "operator_decisions": [x.to_dict() for x in self.operator_decisions],
            "selected_operators": list(self.selected_operators),
            "selection_fingerprint": self.selection_fingerprint,
            "notes": list(self.notes),
        }
