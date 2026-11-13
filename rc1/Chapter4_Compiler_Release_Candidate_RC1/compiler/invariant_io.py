import json
from pathlib import Path
from .invariant_models import InvariantNeighbourhood

def load_neighbourhoods(path):
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = obj["neighbourhoods"] if isinstance(obj, dict) else obj
    return {x["proposition_id"]: InvariantNeighbourhood.from_obj(x) for x in rows}

def load_c4_008_components(path):
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    return list(obj["results"])
