# Stage 7 SIM-002 R01 Historical Disposition

## Status

`SIM-002 / R01` is preserved as historical controlled-execution evidence only. It is not eligible for Stage 7 acceptance and must not be reused as a member of any future cohort.

## Basis

The R01 pilot was a real controlled execution. Its three member outputs routed correctly, matched the frozen oracle assessment, and passed the then-current N=3 cohort validator. The post-execution evidence review identified contract-design gaps that prevent acceptance use:

- run-record v1 could not represent both the frozen execution-input revision and the actual execution repository revision;
- C1-C10 scoring and generated-artifact validator results were not persisted in an approved artifact-backed contract location;
- the exact execution-surface version was unavailable, so reproducibility could not be claimed under the Stage 7 plan.

## Controls

The existing R01 result files, payload files, and run-record v1 files must not be edited, overwritten, regenerated, converted to v2, or retroactively repaired. The oracle must not be corrected automatically. R01 remains append-only history and cannot silently become acceptance evidence for a restarted cohort.

The next controlled SIM-002 attempt, if approved, must use `R02`, a new frozen baseline, run-record v2 evidence, and a separate Human Gate Level 3 controlled-execution approval after the v2 infrastructure is approved.
