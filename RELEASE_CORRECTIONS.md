# Reproducibility release corrections (successor to v1.0.0)

This is a **new repository snapshot**. Do not replace or rewrite the Zenodo v1.0.0 archive in place.

- Excludes `experiment/scratch_results.json` if present; its 115-distinguishable / 64-vs-69 numbers come from a different provisional run and are **not** the paper's matched primary 103-mutant subset.
- Changes `experiment/protocol.json` metadata from an unverified "frozen-before-execution" claim to an accurate methods-record statement. Its mutation definitions and results were not modified.
- Removes the internal QA-only JSON from the public release. This does not change historical RC1 test logs or compiler source.
- Removes the README entry for absent `experiments/original_controlled/`. Frozen RC1 evidence resides in the historical RC1 directory; do not imply the standalone original baseline regeneration harness is available.
- Retains the historical `rc1/Chapter4_Compiler_Release_Candidate_RC1/` directory name deliberately for source/fixture provenance and existing script compatibility; do not interpret as a current manuscript title.
- The 24-mutant and 388-mutant studies remain distinct. The confirmed primary 388-mutant results are 57/103 for both methods, 245 no observable difference, 40 with execution errors.
- The files in this successor snapshot must be re-archived in a **new Zenodo version** with a newly assigned version DOI. The previous DOI remains an immutable historical record.
