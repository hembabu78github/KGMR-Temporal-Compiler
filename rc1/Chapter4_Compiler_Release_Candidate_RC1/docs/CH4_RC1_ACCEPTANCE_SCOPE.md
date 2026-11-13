# Chapter 4 Compiler Release Candidate RC1

## Purpose

RC1 is the consolidated software-engineering acceptance run for the deterministic
Chapter 4 KG-to-MR compiler chain implemented in C4-006 through C4-016.

This replaces further per-task researcher execution cycles.

## RC1 acceptance scope

RC1 confirms, in one run:

- the complete integrated unit suite passes;
- C4-016 deterministic replay succeeds;
- the replay release signature matches the researcher-confirmed C4-016 signature;
- all 12 CandidateMR IDs and semantic fingerprints reproduce;
- all 12 generated Python hashes reproduce;
- all 12 static-validation/admission outcomes reproduce;
- all 11 frozen transformation operators remain represented;
- all 12 generated modules remain present;
- all 12 candidates remain statically valid;
- 8 remain execution-admissible;
- 4 remain correctly control-blocked;
- blocked candidates make zero target-CDS calls;
- all 12 remain expert-validation `UNREVIEWED`;
- version inventory and controlled identity rules pass.

## RC1 acceptance does NOT establish

RC1 does not establish:

- independent expert clinical validity;
- real candidate-MR yield from the CKD-TKG;
- clinical correctness of the metamorphic relations;
- CDS robustness;
- baseline superiority;
- novelty;
- ablation effects.

These remain evaluation-stage questions.

## Status semantics

`SOFTWARE_ENGINEERING_RC_ACCEPTED`

means the compiler implementation is sufficiently stable and reproducible to freeze its
engineering interface and proceed to evaluation.

It is not equivalent to clinical or empirical thesis validation.

## Next phase after RC1

After researcher reproduction of RC1, routine engineering acceptance cycles stop.

The next workstream is:

1. evaluation protocol;
2. simple rule-to-template baseline;
3. additional baselines as justified;
4. ablation experiments;
5. failure analysis;
6. novelty evaluation;
7. real evidence-linked CKD-TKG compiler population (D-27);
8. figures/tables/results/discussion.

The optional LLM-assisted candidate-generation branch remains exploratory and is not required
to freeze the deterministic compiler RC1.
