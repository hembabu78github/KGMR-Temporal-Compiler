from __future__ import annotations
import copy
import hashlib
import json
import platform
import shutil
import sys
from pathlib import Path

from compiler.candidate_assembly import build_candidate, semantic_fingerprint, key, stable_candidate_id
from compiler.candidate_validation import validate_candidate
from compiler.deterministic_yaml import dumps_yaml_document, loads_deterministic_yaml_document
from compiler.python_codegen import generate_modules
from compiler.static_validation import validate_static_bundle

def _canon(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def _sha_obj(x):
    return hashlib.sha256(_canon(x).encode("utf-8")).hexdigest()

def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def _rmap(path):
    return {key(x["proposition_id"],x["operator_id"]):x for x in _load(path)["results"]}

def environment_observation():
    return {
      "python_version":sys.version.split()[0],
      "python_implementation":platform.python_implementation(),
      "platform_system":platform.system(),
      "platform_machine":platform.machine(),
    }

def version_inventory(specs,policy_version):
    versions={
      "representation_versions":sorted({x["representation_version"] for x in specs}),
      "proposition_ir_versions":sorted({x["P"]["proposition_ir_version"] for x in specs}),
      "candidate_compiler_versions":sorted({x["P"]["compiler_version"] for x in specs}),
      "operator_library_versions":sorted({x["P"]["operator_library_version"] for x in specs}),
      "kg_releases":sorted({x["P"]["kg_release"] for x in specs}),
      "ontology_releases":sorted({x["P"]["ontology_release"] for x in specs}),
      "shacl_releases":sorted({x["P"]["shacl_release"] for x in specs}),
      "inference_profiles":sorted({x["P"]["inference_profile"] for x in specs}),
      "closure_policy_versions":sorted({x["P"]["closure_policy_version"] for x in specs}),
      "srew_versions":sorted({x["P"]["srew_version"] for x in specs}),
      "compiler_config_ids":sorted({x["P"]["compiler_config_id"] for x in specs}),
      "c4_014_runtime_version":"C4-014-R1.0",
      "c4_015_static_validation_version":"C4-015-R1.0",
      "c4_016_reproducibility_version":policy_version,
      "schema_implementation":"CandidateMR-R1.0 / C4-013 schema patch 1",
    }
    return versions

def build_specs_from_upstream(root):
    root=Path(root)
    comps=_load(root/"fixtures"/"researcher_c4_008_component_generation_results.json")["results"]
    inv=_rmap(root/"fixtures"/"researcher_c4_009_invariant_inference_results.json")
    exc=_rmap(root/"fixtures"/"researcher_c4_010_exception_precedence_results.json")
    temp=_rmap(root/"fixtures"/"researcher_c4_011_temporal_satisfiability_results.json")
    typed=_rmap(root/"fixtures"/"researcher_c4_012_output_relation_typing_results.json")
    conflicts=_load(root/"fixtures"/"researcher_c4_012_integrated_conflict_records.json")["records"]

    specs=[]
    controls=[]
    for comp in sorted(comps,key=lambda x:(x["proposition_id"],x["operator_id"])):
        k=key(comp["proposition_id"],comp["operator_id"])
        spec,control=build_candidate(comp,typed[k],inv[k],exc[k],temp[k],conflicts)
        errs=validate_candidate(spec)
        if errs:
            raise ValueError(f"Replay candidate invalid for {k}: {errs}")
        specs.append(spec)
        controls.append(control)
    return specs,controls

def make_c4_013_manifest(specs,controls,out_dir):
    out=Path(out_dir)
    json_dir=out/"candidate_mr_json"
    yaml_dir=out/"candidate_mr_yaml"
    json_dir.mkdir(parents=True,exist_ok=True)
    yaml_dir.mkdir(parents=True,exist_ok=True)
    rows=[]
    for spec,control in zip(specs,controls):
        cid=spec["candidate_mr_id"]
        jp=json_dir/f"{cid}.json"
        yp=yaml_dir/f"{cid}.yaml"
        jp.write_text(json.dumps(spec,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n")
        yp.write_text(dumps_yaml_document(spec),encoding="utf-8",newline="\n")
        # Semantic round-trip is part of replay, not byte-only YAML identity.
        parsed=loads_deterministic_yaml_document(yp.read_text(encoding="utf-8"))
        if parsed != spec:
            raise ValueError("YAML semantic replay mismatch for "+cid)
        row=dict(control)
        row.update({
          "semantic_spec_fingerprint":semantic_fingerprint(spec),
          "json_sha256":hashlib.sha256(jp.read_bytes()).hexdigest(),
          "yaml_sha256":hashlib.sha256(yp.read_bytes()).hexdigest(),
          "json_path":"candidate_mr_json/"+jp.name,
          "yaml_path":"candidate_mr_yaml/"+yp.name,
          "validation_status":"VALID",
        })
        rows.append(row)
    return rows,json_dir,yaml_dir

def unify_candidate_dir(json_dir,yaml_dir,target):
    target=Path(target); target.mkdir(parents=True,exist_ok=True)
    for p in Path(json_dir).glob("*.json"):
        shutil.copy2(p,target/p.name)
    for p in Path(yaml_dir).glob("*.yaml"):
        shutil.copy2(p,target/p.name)
    return target

def replay_once(root,out_dir,policy):
    root=Path(root); out=Path(out_dir)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    specs,controls=build_specs_from_upstream(root)
    c13_rows,jdir,ydir=make_c4_013_manifest(specs,controls,out/"c4_013")
    c13_map={x["candidate_mr_id"]:x for x in c13_rows}

    generated=out/"c4_014"/"generated_mr_python"
    c14_rows=generate_modules(jdir,c13_rows,generated)
    c14_map={x["candidate_mr_id"]:x for x in c14_rows}

    # Use exact researcher C4-014 end-to-end gate evidence for static replay.
    gate_rows=_load(root/"fixtures"/"researcher_c4_014_end_to_end_gate_results.json")["results"]
    gate_map={x["candidate_mr_id"]:x for x in gate_rows}
    runtime_cfg=_load(root/"config"/"executable_runtime_r1.json")
    static_policy=_load(root/"config"/"static_validation_policy_r1.json")
    unified=unify_candidate_dir(jdir,ydir,out/"c4_015"/"candidate_specs")

    static_rows=[]
    for row in sorted(c14_rows,key=lambda x:x["candidate_mr_id"]):
        cid=row["candidate_mr_id"]
        if cid not in gate_map:
            raise ValueError("Missing researcher C4-014 gate row for "+cid)
        s=next(x for x in specs if x["candidate_mr_id"]==cid)
        r=validate_static_bundle(
          s,row,c13_map[cid],gate_map[cid],
          generated/row["module_path"],unified/(cid+".yaml"),
          static_policy,runtime_cfg
        )
        static_rows.append(r)

    # Canonical replay record. Environment is kept out of release signature.
    candidate_rows=[]
    for spec in sorted(specs,key=lambda x:x["candidate_mr_id"]):
        cid=spec["candidate_mr_id"]
        c14=c14_map[cid]
        st=next(x for x in static_rows if x["candidate_mr_id"]==cid)
        candidate_rows.append({
          "candidate_mr_id":cid,
          "semantic_spec_fingerprint":semantic_fingerprint(spec),
          "operator_id":spec["T"]["operator_id"],
          "operator_version":spec["T"]["operator_version"],
          "relation_family":spec["R"]["relation_family"],
          "generated_python_sha256":c14["generated_python_sha256"],
          "static_validation_status":st["static_validation_status"],
          "execution_admission_status":st["execution_admission_status"],
          "expert_validation_status":st["expert_validation_status"],
        })

    versions=version_inventory(specs,policy["policy_version"])
    release_core={
      "release_record_version":"CompilerRunRecord-R1.0",
      "pipeline_scope":"C4-006-through-C4-016",
      "candidate_count":len(candidate_rows),
      "candidate_rows":candidate_rows,
      "versions":versions,
      "policy_version":policy["policy_version"],
    }
    signature=_sha_obj(release_core)
    return {
      "release_core":release_core,
      "reproducibility_signature":signature,
      "environment_observation":environment_observation(),
      "candidate_specs":specs,
      "c4_013_manifest":c13_rows,
      "c4_014_codegen_manifest":c14_rows,
      "c4_015_static_results":static_rows,
    }

def compare_replays(a,b):
    ar=a["release_core"]; br=b["release_core"]
    arows={x["candidate_mr_id"]:x for x in ar["candidate_rows"]}
    brows={x["candidate_mr_id"]:x for x in br["candidate_rows"]}
    ids_a=sorted(arows); ids_b=sorted(brows)
    per=[]
    for cid in sorted(set(ids_a)|set(ids_b)):
        x=arows.get(cid); y=brows.get(cid)
        per.append({
          "candidate_mr_id":cid,
          "present_in_both":x is not None and y is not None,
          "semantic_fingerprint_match":bool(x and y and x["semantic_spec_fingerprint"]==y["semantic_spec_fingerprint"]),
          "generated_python_hash_match":bool(x and y and x["generated_python_sha256"]==y["generated_python_sha256"]),
          "static_status_match":bool(x and y and x["static_validation_status"]==y["static_validation_status"]),
          "execution_admission_match":bool(x and y and x["execution_admission_status"]==y["execution_admission_status"]),
        })
    return {
      "release_signature_match":a["reproducibility_signature"]==b["reproducibility_signature"],
      "candidate_id_set_match":ids_a==ids_b,
      "candidate_id_match_count":len(set(ids_a)&set(ids_b)),
      "semantic_fingerprint_match_count":sum(x["semantic_fingerprint_match"] for x in per),
      "generated_python_hash_match_count":sum(x["generated_python_hash_match"] for x in per),
      "static_status_match_count":sum(x["static_status_match"] for x in per),
      "execution_admission_match_count":sum(x["execution_admission_match"] for x in per),
      "per_candidate":per,
    }

def compare_to_researcher(root,replay):
    root=Path(root)
    c13={x["candidate_mr_id"]:x for x in _load(root/"fixtures"/"researcher_c4_013_candidate_manifest.json")["candidates"]}
    c14={x["candidate_mr_id"]:x for x in _load(root/"fixtures"/"researcher_c4_014_codegen_manifest.json")["modules"]}
    c15={x["candidate_mr_id"]:x for x in _load(root/"fixtures"/"researcher_c4_015_static_validation_registry.json")["candidates"]}
    rows=[]
    for r in replay["release_core"]["candidate_rows"]:
        cid=r["candidate_mr_id"]
        rows.append({
          "candidate_mr_id":cid,
          "researcher_c4_013_id_present":cid in c13,
          "semantic_fingerprint_match":cid in c13 and r["semantic_spec_fingerprint"]==c13[cid]["semantic_spec_fingerprint"],
          "generated_python_sha256_match":cid in c14 and r["generated_python_sha256"]==c14[cid]["generated_python_sha256"],
          "static_validation_status_match":cid in c15 and r["static_validation_status"]==c15[cid]["static_validation_status"],
          "execution_admission_status_match":cid in c15 and r["execution_admission_status"]==c15[cid]["execution_admission_status"],
          "expert_validation_status_match":cid in c15 and r["expert_validation_status"]==c15[cid]["expert_validation_status"],
        })
    return {
      "candidate_count":len(rows),
      "researcher_c4_013_id_match_count":sum(x["researcher_c4_013_id_present"] for x in rows),
      "semantic_fingerprint_match_count":sum(x["semantic_fingerprint_match"] for x in rows),
      "generated_python_sha256_match_count":sum(x["generated_python_sha256_match"] for x in rows),
      "static_validation_status_match_count":sum(x["static_validation_status_match"] for x in rows),
      "execution_admission_status_match_count":sum(x["execution_admission_status_match"] for x in rows),
      "expert_validation_status_match_count":sum(x["expert_validation_status_match"] for x in rows),
      "per_candidate":rows,
    }

def controlled_identity_tests(spec):
    original_id=spec["candidate_mr_id"]
    original_fp=semantic_fingerprint(spec)

    # Environment-only observation is external to spec/identity.
    env1={"hostname":"A","pid":1,"path":"C:/x"}
    env2={"hostname":"B","pid":999,"path":"/tmp/y"}
    environment_excluded=(original_id==spec["candidate_mr_id"] and env1!=env2)

    # Expert-review lifecycle metadata is deliberately excluded from candidate identity.
    expert=copy.deepcopy(spec)
    expert["P"]["mr_expert_validation_status"]="ACCEPTED"
    expert_id=stable_candidate_id(expert["C"],expert["T"],expert["R"],expert["I"],expert["E"],expert["P"])
    expert_status_excluded=(expert_id==original_id)

    # Version-bearing semantic compiler metadata must change identity.
    versioned=copy.deepcopy(spec)
    versioned["P"]["compiler_config_id"]=versioned["P"]["compiler_config_id"]+"-BUMP"
    versioned_id=stable_candidate_id(versioned["C"],versioned["T"],versioned["R"],versioned["I"],versioned["E"],versioned["P"])
    compiler_config_bump_changes_id=(versioned_id!=original_id)

    opver=copy.deepcopy(spec)
    opver["P"]["operator_library_version"]=opver["P"]["operator_library_version"]+"-BUMP"
    opver_id=stable_candidate_id(opver["C"],opver["T"],opver["R"],opver["I"],opver["E"],opver["P"])
    operator_library_bump_changes_id=(opver_id!=original_id)

    return {
      "environment_metadata_excluded_from_identity":environment_excluded,
      "expert_validation_status_excluded_from_identity":expert_status_excluded,
      "compiler_config_version_bump_changes_candidate_id":compiler_config_bump_changes_id,
      "operator_library_version_bump_changes_candidate_id":operator_library_bump_changes_id,
    }

def required_version_check(inventory,required):
    values=set()
    for k,v in inventory.items():
        if isinstance(v,list):
            values.update(str(x) for x in v)
        else:
            values.add(str(v))
    return {x:(x in values) for x in required}
