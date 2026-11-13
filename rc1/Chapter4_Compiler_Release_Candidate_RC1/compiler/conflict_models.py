from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

RELATION_FAMILIES = {
    "EQUALITY_WITHIN_TOLERANCE",
    "MONOTONIC_INCREASE",
    "MONOTONIC_DECREASE",
    "ORDINAL_NONDECREASE",
    "ORDINAL_NONINCREASE",
    "BOUNDED_CHANGE",
    "DECISION_LEVEL",
}

CONFLICT_TYPES = {
    "ExpectedRelationConflict",
    "ApplicabilityConflict",
    "ExceptionConflict",
    "VersionConflict",
    "TerminologyConflict",
    "DataConflict",
    "TemporalConflict",
    "DecisionPolicyConflict",
    "SourceInterpretationConflict",
    "ReviewConflict",
}

@dataclass(frozen=True)
class CandidateScope:
    proposition_id: str
    operator_id: str
    target_id: str
    output_id: str
    comparison_context_id: str
    care_contexts: List[str]
    gfr_categories: List[str]
    eligibility_states: List[str]
    temporal_scope_policy: str
    release_lineage: str
    release_version: str
    source_interpretation_id: str
    review_state: str

    @staticmethod
    def from_obj(obj):
        return CandidateScope(
            proposition_id=str(obj["proposition_id"]),
            operator_id=str(obj["operator_id"]),
            target_id=str(obj["target_id"]),
            output_id=str(obj["output_id"]),
            comparison_context_id=str(obj["comparison_context_id"]),
            care_contexts=list(obj.get("care_contexts",[])),
            gfr_categories=list(obj.get("gfr_categories",[])),
            eligibility_states=list(obj.get("eligibility_states",[])),
            temporal_scope_policy=str(obj.get("temporal_scope_policy","FROM_C4_011")),
            release_lineage=str(obj.get("release_lineage","CKD-TKG")),
            release_version=str(obj.get("release_version","R1.0")),
            source_interpretation_id=str(obj.get("source_interpretation_id","")),
            review_state=str(obj.get("review_state","ClinicallyReviewed")),
        )

@dataclass(frozen=True)
class TypedOutputRelation:
    proposition_id: str
    operator_id: str
    typing_status: str
    relation_family: str
    source_output_selector: str
    followup_output_selector: str
    comparator_id: str
    parameters: Dict[str, Any]
    semantic_domain: str
    normalized_constraint: Dict[str, Any]
    relation_signature: str
    reasons: List[str]

    def to_dict(self):
        return asdict(self)

@dataclass(frozen=True)
class ConflictEvidence:
    evidence_id: str
    conflict_type: str
    involved_candidate_keys: List[str]
    truth: str
    rationale: str
    source_refs: List[str]
    resolution_hint: Optional[str] = None
    legitimate_winner_key: Optional[str] = None
    adjudication_ref: Optional[str] = None

    @staticmethod
    def from_obj(obj):
        return ConflictEvidence(
            evidence_id=str(obj["evidence_id"]),
            conflict_type=str(obj["conflict_type"]),
            involved_candidate_keys=list(obj.get("involved_candidate_keys",[])),
            truth=str(obj["truth"]),
            rationale=str(obj["rationale"]),
            source_refs=list(obj.get("source_refs",[])),
            resolution_hint=obj.get("resolution_hint"),
            legitimate_winner_key=obj.get("legitimate_winner_key"),
            adjudication_ref=obj.get("adjudication_ref"),
        )

@dataclass(frozen=True)
class ConflictResolutionRecord:
    conflict_id: str
    conflict_type: str
    involved_candidate_keys: List[str]
    common_target_id: Optional[str]
    common_output_id: Optional[str]
    applicability_overlap: str
    temporal_overlap: str
    expectation_compatibility: str
    detection_phase: str
    resolution_status: str
    resolution_type: str
    legitimate_winner_key: Optional[str]
    semantic_truth: str
    system_action: str
    conflict_resolved_gate: str
    rationale: str
    source_refs: List[str]
    adjudication_ref: Optional[str]
    record_version: str

    def to_dict(self):
        return asdict(self)

@dataclass(frozen=True)
class DuplicateRecord:
    duplicate_id: str
    candidate_keys: List[str]
    duplicate_signature: str
    rationale: str

    def to_dict(self):
        return asdict(self)
