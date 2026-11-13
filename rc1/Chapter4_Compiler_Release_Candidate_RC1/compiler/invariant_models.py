from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

ALLOWED_INVARIANT_TYPES = {
    "VALUE", "IDENTITY", "TIME", "STATE", "STRUCTURE",
    "UNIT_CANONICAL_VALUE", "CUSTOM_DECLARED"
}

@dataclass(frozen=True)
class NeighbourhoodNode:
    node_id: str
    selector: str
    invariant_type: str
    source_refs: List[str] = field(default_factory=list)

    @staticmethod
    def from_obj(obj):
        return NeighbourhoodNode(
            node_id=str(obj["node_id"]),
            selector=str(obj["selector"]),
            invariant_type=str(obj["invariant_type"]),
            source_refs=list(obj.get("source_refs", [])),
        )

@dataclass(frozen=True)
class NeighbourhoodEdge:
    source: str
    relation: str
    target: str
    source_ref: str
    comparator_id: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    operators: List[str] = field(default_factory=list)

    @staticmethod
    def from_obj(obj):
        return NeighbourhoodEdge(
            source=str(obj["source"]),
            relation=str(obj["relation"]),
            target=str(obj["target"]),
            source_ref=str(obj["source_ref"]),
            comparator_id=obj.get("comparator_id"),
            parameters=dict(obj.get("parameters", {})),
            operators=list(obj.get("operators", [])),
        )

@dataclass
class InvariantNeighbourhood:
    proposition_id: str
    seed_nodes: List[str]
    nodes: List[NeighbourhoodNode]
    edges: List[NeighbourhoodEdge]
    max_hops: int = 2
    release_ref: str = ""
    notes: str = ""

    @staticmethod
    def from_obj(obj):
        return InvariantNeighbourhood(
            proposition_id=str(obj["proposition_id"]),
            seed_nodes=list(obj.get("seed_nodes", [])),
            nodes=[NeighbourhoodNode.from_obj(x) for x in obj.get("nodes", [])],
            edges=[NeighbourhoodEdge.from_obj(x) for x in obj.get("edges", [])],
            max_hops=int(obj.get("max_hops", 2)),
            release_ref=str(obj.get("release_ref", "")),
            notes=str(obj.get("notes", "")),
        )

@dataclass(frozen=True)
class InvariantClause:
    invariant_id: str
    invariant_type: str
    source_selector: str
    followup_selector: str
    comparator_id: str
    parameters: Dict[str, Any]
    source_refs: List[str]

    def to_dict(self):
        return asdict(self)

@dataclass
class InvariantEvidenceRecord:
    invariant_id: str
    candidate_node_id: str
    evidence_path: List[str]
    support_relation: str
    operator_id: str
    source_refs: List[str]

    def to_dict(self):
        return asdict(self)

@dataclass
class RejectedInvariantCandidate:
    candidate_node_id: str
    selector: str
    reason: str
    evidence_path: List[str]
    source_refs: List[str]

    def to_dict(self):
        return asdict(self)

@dataclass
class InvariantInferenceResult:
    proposition_id: str
    operator_id: str
    component_fingerprint: str
    inference_status: str
    inferred_invariants: List[InvariantClause]
    evidence_records: List[InvariantEvidenceRecord]
    rejected_candidates: List[RejectedInvariantCandidate]
    invariant_fingerprint: str
    release_ref: str
    notes: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "proposition_id": self.proposition_id,
            "operator_id": self.operator_id,
            "component_fingerprint": self.component_fingerprint,
            "inference_status": self.inference_status,
            "inferred_invariants": [x.to_dict() for x in self.inferred_invariants],
            "evidence_records": [x.to_dict() for x in self.evidence_records],
            "rejected_candidates": [x.to_dict() for x in self.rejected_candidates],
            "invariant_fingerprint": self.invariant_fingerprint,
            "release_ref": self.release_ref,
            "notes": list(self.notes),
        }
