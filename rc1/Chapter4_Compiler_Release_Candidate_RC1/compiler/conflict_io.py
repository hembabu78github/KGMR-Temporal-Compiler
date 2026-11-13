import json
from pathlib import Path
from .conflict_models import CandidateScope,ConflictEvidence

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def load_components(path):
    return list(load_json(path)["results"])

def load_scopes(path):
    obj=load_json(path)
    return {
      f"{x['proposition_id']}::{x['operator_id']}":CandidateScope.from_obj(x)
      for x in obj["scopes"]
    }

def load_result_map(path):
    obj=load_json(path)
    return {f"{x['proposition_id']}::{x['operator_id']}":x for x in obj["results"]}

def load_conflict_evidence(path):
    obj=load_json(path)
    return [ConflictEvidence.from_obj(x) for x in obj.get("evidence",[])]
