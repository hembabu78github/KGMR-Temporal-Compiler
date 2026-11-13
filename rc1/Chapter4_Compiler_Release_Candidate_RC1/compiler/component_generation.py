import hashlib, json
from .precondition_generator import generate_preconditions
from .transformation_generator import generate_transformation
from .output_relation_generator import generate_output_relation
from .component_models import ComponentGenerationResult

def _canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def _fingerprint(payload):
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()

def generate_components(inp, selection_result, transformation_contracts):
    selected = list(selection_result.get("selected_operators", []))
    decision_by_operator = {
        d["operator_id"]: d for d in selection_result.get("operator_decisions", [])
    }
    outputs = []

    for operator_id in selected:
        dec = decision_by_operator[operator_id]
        c = generate_preconditions(inp)
        t = generate_transformation(dec, transformation_contracts)
        r = generate_output_relation(inp, dec)

        if c.status != "GENERATED" or t.status != "GENERATED":
            status = "INVALID"
        elif r.status == "GENERATED":
            status = "COMPONENTS_GENERATED"
        elif r.status in {"UNRESOLVED","AMBIGUOUS"}:
            status = "RELATION_TYPING_PENDING"
        else:
            status = "INVALID"

        semantic_payload = {
            "proposition_id": inp.proposition_id,
            "operator_id": operator_id,
            "C": c.to_dict(),
            "T": t.to_dict(),
            "R": r.to_dict(),
            "source_refs": sorted(inp.source_refs),
            "graph_path_ids": sorted(inp.graph_path_ids),
            "release_ref": inp.release_ref,
            "c4_006_selection_fingerprint": selection_result["selection_fingerprint"],
        }
        fp = _fingerprint(semantic_payload)

        notes = []
        if selection_result.get("admission_status") != "ELIGIBLE":
            notes.append(
                "Component generation does not override C4-006 admission status: "
                + str(selection_result.get("admission_status"))
            )
        if r.status != "GENERATED":
            notes.append("Final output-relation typing is deferred to C4-012.")

        outputs.append(ComponentGenerationResult(
            inp.proposition_id, operator_id, status, c, t, r,
            sorted(inp.source_refs), sorted(inp.graph_path_ids), inp.release_ref,
            selection_result["selection_fingerprint"], fp, notes
        ))

    return outputs
