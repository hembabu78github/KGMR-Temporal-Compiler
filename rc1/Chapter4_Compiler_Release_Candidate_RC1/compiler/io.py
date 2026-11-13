import json
from pathlib import Path
from .models import ClinicalPropositionIR

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def load_ir_list(path):
    obj = load_json(path)
    rows = obj["propositions"] if isinstance(obj, dict) else obj
    return [ClinicalPropositionIR.from_obj(x) for x in rows]

def write_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
