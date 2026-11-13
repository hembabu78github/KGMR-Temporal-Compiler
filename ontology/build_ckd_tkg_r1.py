from pathlib import Path
import json, re
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL, XSD

ROOT=Path(__file__).resolve().parent
m=json.loads((ROOT/"ckd_tkg_r1_manifest.json").read_text(encoding="utf-8"))
NS={k:Namespace(v) for k,v in m["namespaces"].items() if k in ("ckd","tk","kgmr","prov","term")}
BASE=URIRef(m["ontology"]["base"])

def curie(s):
    if not s: return None
    s=str(s)
    if s=="owl:Thing": return OWL.Thing
    if s=="owl:topObjectProperty": return OWL.topObjectProperty
    if s=="owl:topDataProperty": return OWL.topDataProperty
    p,l=s.split(":",1)
    if p=="xsd": return Namespace(str(XSD))[l]
    if p=="owl": return Namespace(str(OWL))[l]
    if p=="rdf": return Namespace(str(RDF))[l]
    if p=="rdfs": return Namespace(str(RDFS))[l]
    return NS[p][l]

def slug(s):
    return re.sub(r"[^A-Za-z0-9]+","_",str(s)).strip("_")

def build():
    g=Graph()
    for p,ns in NS.items(): g.bind(p,ns)
    g.bind("rdf",RDF); g.bind("rdfs",RDFS); g.bind("owl",OWL); g.bind("xsd",XSD)

    g.add((BASE,RDF.type,OWL.Ontology))
    g.add((BASE,RDFS.label,Literal("CKD-TKG R1.0 Ontology")))
    g.add((BASE,RDFS.comment,Literal(
        "RDF/OWL implementation of the design-closed C3-004 through C3-013 baseline. "
        "External terminology and source-data mappings remain governed annotations."
    )))
    g.add((BASE,OWL.versionInfo,Literal(m["ontology"]["version"])))

    for c in m["classes"]:
        u=curie(c["id"]); g.add((u,RDF.type,OWL.Class))
        if c.get("label"): g.add((u,RDFS.label,Literal(c["label"])))
        if c.get("definition"): g.add((u,RDFS.comment,Literal(c["definition"])))
        if c.get("parent"): g.add((u,RDFS.subClassOf,curie(c["parent"])))

    # Temporal classes closed in C3-009.
    temporal_parent={
        "tk:TemporalInstant":"tk:TemporalEntity",
        "tk:TemporalInterval":"tk:TemporalEntity",
        "tk:TemporalDuration":"tk:TemporalEntity",
        "tk:UncertainTime":"tk:TemporalEntity",
        "tk:EventWindow":"tk:TemporalEntity",
        "tk:SequencePosition":"tk:TemporalEntity",
    }
    for c in m.get("temporal_entities",[]):
        u=curie(c["id"]); g.add((u,RDF.type,OWL.Class))
        g.add((u,RDFS.label,Literal(c.get("label") or c["id"].split(":",1)[1])))
        if c.get("definition"): g.add((u,RDFS.comment,Literal(c["definition"])))
        g.add((u,RDFS.subClassOf,curie(temporal_parent.get(c["id"],"tk:TemporalEntity"))))

    for cid,(label,comment,parent) in m.get("implementation_extension_classes",{}).items():
        u=curie(cid); g.add((u,RDF.type,OWL.Class)); g.add((u,RDFS.label,Literal(label)))
        g.add((u,RDFS.comment,Literal(comment))); g.add((u,RDFS.subClassOf,curie(parent)))

    for p in m["object_properties"]:
        u=curie(p["id"]); g.add((u,RDF.type,OWL.ObjectProperty))
        if p.get("label"): g.add((u,RDFS.label,Literal(p["label"])))
        if p.get("parent") and p["parent"]!="owl:topObjectProperty":
            g.add((u,RDFS.subPropertyOf,curie(p["parent"])))
        if p.get("domain"): g.add((u,RDFS.domain,curie(p["domain"])))
        if p.get("range"): g.add((u,RDFS.range,curie(p["range"])))
        if p.get("inverse"): g.add((u,OWL.inverseOf,curie(p["inverse"])))
        if p.get("characteristics"): g.add((u,RDFS.comment,Literal("C3-005 control: "+str(p["characteristics"]))))

    for p in m["datatype_properties"]:
        u=curie(p["id"]); g.add((u,RDF.type,OWL.DatatypeProperty))
        g.add((u,RDFS.label,Literal(p["id"].split(":",1)[1])))
        if p.get("domain"): g.add((u,RDFS.domain,curie(p["domain"])))
        if p.get("range"): g.add((u,RDFS.range,curie(p["range"])))
        if p.get("definition"): g.add((u,RDFS.comment,Literal(p["definition"])))

    token_map={
        "TemporalEntity":"tk:TemporalEntity","TemporalInterval":"tk:TemporalInterval",
        "ClinicalObservation":"ckd:ClinicalObservation","EventWindow":"tk:EventWindow"
    }
    for p in m.get("temporal_relations",[]):
        pid=p["id"] if ":" in p["id"] else "tk:"+p["id"]
        u=curie(pid); g.add((u,RDF.type,OWL.ObjectProperty))
        g.add((u,RDFS.label,Literal(pid.split(":",1)[1])))
        dom=token_map.get(str(p.get("domain")),p.get("domain"))
        rng=token_map.get(str(p.get("range")),p.get("range"))
        if dom: g.add((u,RDFS.domain,curie(dom)))
        if rng: g.add((u,RDFS.range,curie(rng)))
        if p.get("inverse"):
            inv=p["inverse"] if ":" in p["inverse"] else "tk:"+p["inverse"]
            g.add((u,OWL.inverseOf,curie(inv)))
        char=str(p.get("characteristic") or "")
        if "Symmetric" in char: g.add((u,RDF.type,OWL.SymmetricProperty))
        if "Asymmetric" in char: g.add((u,RDF.type,OWL.AsymmetricProperty))
        low=char.lower()
        if "transitive" in low and "not transitive" not in low and "not declared" not in low:
            g.add((u,RDF.type,OWL.TransitiveProperty))

    for pid,(dom,rng,label) in m.get("implementation_object_properties",{}).items():
        u=curie(pid); g.add((u,RDF.type,OWL.ObjectProperty)); g.add((u,RDFS.label,Literal(label)))
        g.add((u,RDFS.domain,curie(dom))); g.add((u,RDFS.range,curie(rng)))
        if pid=="ckd:overlapsEvent": g.add((u,RDF.type,OWL.SymmetricProperty))

    for pid,(rng,dom) in m.get("implementation_datatype_properties",{}).items():
        u=curie(pid); g.add((u,RDF.type,OWL.DatatypeProperty)); g.add((u,RDFS.label,Literal(pid.split(":",1)[1])))
        g.add((u,RDFS.domain,curie(dom))); g.add((u,RDFS.range,curie(rng)))

    for group in m.get("pairwise_disjoint",[]):
        members=[curie(x) for x in group]
        for i in range(len(members)):
            for j in range(i+1,len(members)):
                g.add((members[i],OWL.disjointWith,members[j]))

    for item in m.get("compilation_gates",[]):
        u=NS["kgmr"]["Gate_"+slug(item["label"])]
        g.add((u,RDF.type,curie("kgmr:CompilationGateType"))); g.add((u,RDFS.label,Literal(item["label"])))
        g.add((u,RDFS.comment,Literal(item["question"])))
    for item in m.get("exception_types",[]):
        u=NS["kgmr"]["Exception_"+slug(item["label"])]
        g.add((u,RDF.type,curie("kgmr:ExceptionType"))); g.add((u,RDFS.label,Literal(item["label"])))
        g.add((u,RDFS.comment,Literal(item["definition"])))
    for item in m.get("conflict_types",[]):
        u=NS["kgmr"]["Conflict_"+slug(item["label"])]
        g.add((u,RDF.type,curie("kgmr:ConflictType"))); g.add((u,RDFS.label,Literal(item["label"])))
        g.add((u,RDFS.comment,Literal(item["condition"])))
    for item in m.get("precedence_tiers",[]):
        u=NS["kgmr"][item["tier"]]
        g.add((u,RDF.type,curie("kgmr:PrecedenceTier"))); g.add((u,RDFS.label,Literal(item["tier"]+" "+item["principle"])))
        g.add((u,RDFS.comment,Literal(item["rule"])))

    for cls,vals in m.get("categorical_individuals",{}).items():
        ns=NS[cls.split(":",1)[0]]
        for v in vals:
            u=ns[v]; g.add((u,RDF.type,curie(cls))); g.add((u,RDFS.label,Literal(v)))

    for s in m.get("review_statuses",[]):
        u=NS["prov"]["ReviewStatus_"+s]
        g.add((u,RDF.type,curie("prov:ReviewStatus"))); g.add((u,RDFS.label,Literal(s)))

    release=NS["prov"]["Release_R1_0_Implementation"]
    g.add((release,RDF.type,curie("prov:ReleaseRecord")))
    g.add((release,RDFS.label,Literal("CKD-TKG R1.0 implementation release")))
    g.add((release,curie("prov:versionLabel"),Literal("R1.0")))
    g.add((release,curie("prov:releaseStatus"),Literal("ImplementationCandidate")))
    g.add((release,curie("prov:recordedDateTime"),Literal("2026-08-06T23:37:00-04:00",datatype=XSD.dateTime)))

    closure=NS["prov"]["DesignClosure_C3_004_C3_013"]
    g.add((closure,RDF.type,curie("prov:ProvenanceRecord")))
    g.add((closure,RDFS.label,Literal("Chapter 3 design closure provenance")))
    g.add((closure,curie("prov:sourceLocator"),Literal("C3-004 through C3-013 design-control artefacts and closure memos")))
    g.add((closure,curie("prov:recordedDateTime"),Literal("2026-08-06T23:37:00-04:00",datatype=XSD.dateTime)))
    g.add((BASE,curie("prov:hasProvenanceRecord"),closure))
    g.add((BASE,curie("prov:hasReleaseRecord"),release))
    return g

if __name__=="__main__":
    g=build()
    g.serialize(destination=ROOT/"ckd_tkg_r1_ontology.ttl",format="turtle")
    g.serialize(destination=ROOT/"ckd_tkg_r1_ontology.owl",format="xml")

    # Refresh the integrity manifest after serialization because RDF/XML
    # serialization order is not guaranteed to be byte-stable across runs.
    import hashlib
    checksum_names=[
        "ckd_tkg_r1_manifest.json", "ckd_tkg_r1_ontology.ttl", "ckd_tkg_r1_ontology.owl",
        "build_ckd_tkg_r1.py", "validate_ckd_tkg_r1.py",
        "ckd_tkg_r1_smoke_queries.rq", "ckd_tkg_r1_smoke_query_results.csv",
        "ckd_tkg_r1_validation_report.json"
    ]
    lines=[]
    for name in checksum_names:
        fp=ROOT/name
        if fp.exists():
            lines.append(f"{hashlib.sha256(fp.read_bytes()).hexdigest()}  {name}")
    (ROOT/"ckd_tkg_r1_checksums.sha256").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"Wrote {len(g)} triples and refreshed checksums.")
