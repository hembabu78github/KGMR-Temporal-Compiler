import json
from pathlib import Path
from .component_models import ComponentGenerationInput

def load_component_inputs(path):
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = obj["inputs"] if isinstance(obj, dict) else obj
    return [ComponentGenerationInput.from_obj(x) for x in rows]

def load_selection_results(path):
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    return {x["proposition_id"]: x for x in obj["results"]}
