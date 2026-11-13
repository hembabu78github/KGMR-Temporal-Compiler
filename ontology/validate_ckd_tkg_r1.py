from pathlib import Path
from rdflib import Graph, RDF, RDFS, OWL, Namespace

ROOT=Path(__file__).resolve().parent
g=Graph().parse(ROOT/"ckd_tkg_r1_ontology.ttl",format="turtle")
KGMR=Namespace("https://ckd-tkg.org/ontology/r1.0/kgmr/")
failures=[]

classes=set(g.subjects(RDF.type,OWL.Class))
obj=set(g.subjects(RDF.type,OWL.ObjectProperty))
data=set(g.subjects(RDF.type,OWL.DatatypeProperty))

for c in classes:
    if not any(g.objects(c,RDFS.label)): failures.append(f"Unlabelled class: {c}")
for p in obj:
    if p==OWL.topObjectProperty: continue
    if not any(g.objects(p,RDFS.domain)): failures.append(f"Object property missing domain: {p}")
    if not any(g.objects(p,RDFS.range)): failures.append(f"Object property missing range: {p}")
for p in data:
    if not any(g.objects(p,RDFS.range)): failures.append(f"Datatype property missing range: {p}")

expected={
    KGMR.CompilationGateType:8,
    KGMR.ExceptionType:10,
    KGMR.ConflictType:10,
    KGMR.PrecedenceTier:9,
}
for cls,n in expected.items():
    found=len(set(g.subjects(RDF.type,cls)))
    if found!=n: failures.append(f"{cls}: expected {n}, found {found}")

# Safety-critical disjointness pairs required by the closed C3-004 design
# (C3-004-O9: KidneyFailureRiskAssessment vs ProgressionRiskAssessment;
#  C3-004-O4: native KDIGO CGA category vs the MR-testing collapse).
# These prevent an instance from being validly typed as both at once.
CKD = Namespace("https://ckd-tkg.org/ontology/r1.0/ckd/")
required_disjoint_pairs = [
    (CKD.KidneyFailureRiskAssessment, CKD.ProgressionRiskAssessment),
    (CKD.KDIGOCGARiskCategory, KGMR.MRTestingRiskCategory),
]
for a, b in required_disjoint_pairs:
    if (a, OWL.disjointWith, b) not in g and (b, OWL.disjointWith, a) not in g:
        failures.append(f"Missing required safety disjointness: {a} <-> {b}")

print(f"triples={len(g)} classes={len(classes)} object_properties={len(obj)} datatype_properties={len(data)}")
if failures:
    for x in failures: print("FAIL:",x)
    raise SystemExit(1)
print("PASS")
