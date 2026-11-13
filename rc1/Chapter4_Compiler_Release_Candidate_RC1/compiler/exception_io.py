import json
from pathlib import Path
from .exception_models import ExceptionEvidence, PrecedenceContext

def load_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def load_exception_inputs(path):
    obj=json.loads(Path(path).read_text(encoding="utf-8"))
    evidence=[ExceptionEvidence.from_obj(x) for x in obj["exceptions"]]
    contexts={
      (x["proposition_id"],x["operator_id"]):PrecedenceContext.from_obj(x)
      for x in obj["contexts"]
    }
    return evidence,contexts

def load_components(path):
    obj=json.loads(Path(path).read_text(encoding="utf-8"))
    return list(obj["results"])

def load_invariants(path):
    obj=json.loads(Path(path).read_text(encoding="utf-8"))
    return {
      (x["proposition_id"],x["operator_id"]):x
      for x in obj["results"]
    }
