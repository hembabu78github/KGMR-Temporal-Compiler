# Algorithm 4.X — Deterministic invariant inference

Input:
    component c = (C,T,R)
    bounded KG neighbourhood G_N
    seed set S
    maximum hop bound h

Output:
    ordered invariant set I
    rejection ledger L

1. Reach <- bounded_BFS(S, G_N, h, whitelisted_relations)
2. Support <- all positive preservation edges whose source is in Reach
3. Sort Support canonically by target, relation, source_ref
4. For each support edge e:
      v <- target(e)
      if operator(T) not permitted by e: continue
      if selector(v) is touched by T:
           reject(v, DIRECT_TOUCH)
           continue
      if v has a dependency path to any selector touched by T:
           reject(v, DEPENDS_ON_TRANSFORMED_SELECTOR)
           continue
      if comparator(e) undefined:
           reject(v, MISSING_COMPARATOR)
           continue
      emit invariant:
         source_selector = selector(v)
         followup_selector = selector(v)
         comparator = comparator(e)
         provenance = node/evidence references
5. Canonically deduplicate semantic-equivalent invariant clauses
6. Compute deterministic invariant fingerprint
7. Return I and L

Safety property:
    No invariant is emitted solely from absence of a mutation edge or from
    membership in T.forbidden_touch_set.
