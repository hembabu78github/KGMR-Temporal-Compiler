import json
from pathlib import Path
from .temporal_models import TemporalCase

def load_temporal_cases(path):
    obj=json.loads(Path(path).read_text(encoding="utf-8"))
    return {x["proposition_id"]:TemporalCase.from_obj(x) for x in obj["cases"]}

def load_components(path):
    obj=json.loads(Path(path).read_text(encoding="utf-8"))
    return list(obj["results"])

def load_precedence_results(path):
    obj=json.loads(Path(path).read_text(encoding="utf-8"))
    return {(x["proposition_id"],x["operator_id"]):x for x in obj["results"]}
