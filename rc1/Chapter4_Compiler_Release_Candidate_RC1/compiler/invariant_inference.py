import hashlib
import json
import fnmatch
from collections import deque, defaultdict
from .invariant_models import (
    ALLOWED_INVARIANT_TYPES,
    InvariantClause,
    InvariantEvidenceRecord,
    RejectedInvariantCandidate,
    InvariantInferenceResult,
)

SUPPORT_RELATIONS = {
    "supports_invariant",
    "declares_preserved",
    "protects_anchor",
    "defines_preserved_state",
}

DEPENDENCY_RELATIONS = {
    "depends_on",
    "derived_from",
    "state_defined_by",
    "temporally_depends_on",
}

TRAVERSABLE_RELATIONS = SUPPORT_RELATIONS | DEPENDENCY_RELATIONS | {
    "has_member", "has_state_component", "has_trajectory_component"
}

def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def _sha(obj):
    return hashlib.sha256(_canon(obj).encode("utf-8")).hexdigest()

def _selector_matches(selector, pattern):
    if selector == pattern:
        return True
    # Support the limited selector wildcards used by the compiler contracts.
    glob = pattern.replace("[*]", "*").replace("[selected]", "*").replace("[equivalent_set]", "*")
    glob = glob.replace("[selected]", "*")
    return fnmatch.fnmatch(selector, glob) or fnmatch.fnmatch(pattern, selector)

def _selector_is_touched(selector, touch_set):
    return any(_selector_matches(selector, p) for p in touch_set)

def _build_graph(edges):
    forward = defaultdict(list)
    reverse = defaultdict(list)
    for e in edges:
        if e.relation in TRAVERSABLE_RELATIONS:
            forward[e.source].append(e)
            reverse[e.target].append(e)
    for k in forward:
        forward[k].sort(key=lambda e: (e.relation, e.target, e.source_ref))
    for k in reverse:
        reverse[k].sort(key=lambda e: (e.relation, e.source, e.source_ref))
    return forward, reverse

def _reachable_nodes(seed_nodes, forward, max_hops):
    # Deterministic bounded BFS over whitelisted edge relations.
    q = deque((s, 0, [s]) for s in sorted(seed_nodes))
    best_path = {}
    while q:
        node, depth, path = q.popleft()
        if node not in best_path:
            best_path[node] = path
        if depth >= max_hops:
            continue
        for e in forward.get(node, []):
            nxt = e.target
            if nxt not in best_path:
                q.append((nxt, depth + 1, path + [f"{e.relation}:{e.source_ref}", nxt]))
    return best_path

def _dependency_path_to_touched(start_node, forward, node_by_id, touch_set, max_hops):
    # A candidate is not invariant if it explicitly depends on something T touches.
    q = deque([(start_node, 0, [start_node])])
    visited = {start_node}
    while q:
        node, depth, path = q.popleft()
        if depth >= max_hops:
            continue
        for e in forward.get(node, []):
            if e.relation not in DEPENDENCY_RELATIONS:
                continue
            tgt = e.target
            next_path = path + [f"{e.relation}:{e.source_ref}", tgt]
            n = node_by_id.get(tgt)
            if n and _selector_is_touched(n.selector, touch_set):
                return next_path
            if tgt not in visited:
                visited.add(tgt)
                q.append((tgt, depth + 1, next_path))
    return None

def _stable_invariant_id(proposition_id, operator_id, node, edge):
    payload = {
        "proposition_id": proposition_id,
        "operator_id": operator_id,
        "node_id": node.node_id,
        "selector": node.selector,
        "invariant_type": node.invariant_type,
        "comparator_id": edge.comparator_id,
        "parameters": edge.parameters,
        "source_ref": edge.source_ref,
    }
    return "INV-" + _sha(payload)[:16]

def infer_invariants(component, neighbourhood):
    proposition_id = component["proposition_id"]
    operator_id = component["operator_id"]
    T = component["T"]
    touch_set = list(T.get("touch_set", []))
    component_fp = component["component_fingerprint"]

    if neighbourhood.proposition_id != proposition_id:
        raise ValueError("neighbourhood proposition_id does not match component")

    node_by_id = {n.node_id:n for n in neighbourhood.nodes}
    forward, reverse = _build_graph(neighbourhood.edges)
    reach = _reachable_nodes(neighbourhood.seed_nodes, forward, neighbourhood.max_hops)

    inferred = []
    records = []
    rejected = []

    # Positive support is mandatory. Mere absence from touch_set is not evidence.
    support_edges = [
        e for e in neighbourhood.edges
        if e.relation in SUPPORT_RELATIONS
        and (not e.operators or operator_id in set(e.operators))
        and e.source in reach
    ]
    support_edges.sort(key=lambda e: (e.target, e.relation, e.source_ref))

    for edge in support_edges:
        node = node_by_id.get(edge.target)
        if node is None:
            rejected.append(RejectedInvariantCandidate(
                edge.target, "", "SUPPORT_TARGET_NODE_MISSING",
                reach.get(edge.source, [edge.source]),
                [edge.source_ref]
            ))
            continue

        evidence_path = list(reach.get(edge.source, [edge.source])) + [
            f"{edge.relation}:{edge.source_ref}", edge.target
        ]
        refs = sorted(set(node.source_refs + [edge.source_ref]))

        if node.invariant_type not in ALLOWED_INVARIANT_TYPES:
            rejected.append(RejectedInvariantCandidate(
                node.node_id, node.selector, "UNSUPPORTED_INVARIANT_TYPE",
                evidence_path, refs
            ))
            continue

        if not edge.comparator_id:
            rejected.append(RejectedInvariantCandidate(
                node.node_id, node.selector, "MISSING_COMPARATOR",
                evidence_path, refs
            ))
            continue

        if _selector_is_touched(node.selector, touch_set):
            rejected.append(RejectedInvariantCandidate(
                node.node_id, node.selector, "SELECTOR_TOUCHED_BY_TRANSFORMATION",
                evidence_path, refs
            ))
            continue

        dep_path = _dependency_path_to_touched(
            node.node_id, forward, node_by_id, touch_set, neighbourhood.max_hops
        )
        if dep_path is not None:
            rejected.append(RejectedInvariantCandidate(
                node.node_id, node.selector, "DEPENDS_ON_TRANSFORMED_SELECTOR",
                evidence_path + ["DEPENDENCY_CHECK"] + dep_path, refs
            ))
            continue

        inv_id = _stable_invariant_id(proposition_id, operator_id, node, edge)
        clause = InvariantClause(
            invariant_id=inv_id,
            invariant_type=node.invariant_type,
            source_selector=node.selector,
            followup_selector=node.selector,
            comparator_id=edge.comparator_id,
            parameters=dict(edge.parameters),
            source_refs=refs,
        )
        inferred.append(clause)
        records.append(InvariantEvidenceRecord(
            invariant_id=inv_id,
            candidate_node_id=node.node_id,
            evidence_path=evidence_path,
            support_relation=edge.relation,
            operator_id=operator_id,
            source_refs=refs,
        ))

    # Deduplicate by semantic clause, not just node id.
    uniq = {}
    uniq_rec = {}
    for clause, rec in zip(inferred, records):
        key = _canon({
            "type": clause.invariant_type,
            "selector": clause.source_selector,
            "comparator": clause.comparator_id,
            "parameters": clause.parameters,
        })
        if key not in uniq:
            uniq[key] = clause
            uniq_rec[key] = rec
    inferred = [uniq[k] for k in sorted(uniq)]
    records = [uniq_rec[k] for k in sorted(uniq)]

    status = "INVARIANTS_INFERRED" if inferred else "NO_SUPPORTED_INVARIANTS"
    notes = []
    if not inferred:
        notes.append(
            "No invariant was inferred without explicit positive preservation evidence."
        )

    semantic = {
        "proposition_id": proposition_id,
        "operator_id": operator_id,
        "component_fingerprint": component_fp,
        "inferred_invariants": [x.to_dict() for x in inferred],
        "evidence_records": [x.to_dict() for x in records],
        "rejected_candidates": [x.to_dict() for x in rejected],
        "release_ref": neighbourhood.release_ref,
    }
    fp = _sha(semantic)

    return InvariantInferenceResult(
        proposition_id=proposition_id,
        operator_id=operator_id,
        component_fingerprint=component_fp,
        inference_status=status,
        inferred_invariants=inferred,
        evidence_records=records,
        rejected_candidates=rejected,
        invariant_fingerprint=fp,
        release_ref=neighbourhood.release_ref,
        notes=notes,
    )
