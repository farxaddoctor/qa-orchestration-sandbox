# Stage 7 SIM-002 R01 Freeze Readiness

Status: `READY_FOR_LEVEL3_EXECUTION_APPROVAL`

This record prepares the first controlled Stage 7 SIM-002 cohort for Human Gate Level 3 approval. It does not approve or start controlled execution, execute SIM-002, create result artifacts, create payloads, create run records, update the evidence manifest, or make acceptance, reproducibility, or release-readiness claims.

Controlled execution remains forbidden until a separate explicit Human Gate Level 3 approval is granted.

## Cohort Boundary

- Scenario ID: `SIM-002`
- Cohort attempt: `R01`
- Authoritative cohort boundary: `(scenario_id, R01)`
- Required members: `P1`, `P2`, `IR`
- Required roles: exactly two `PRIMARY` records and exactly one `INDEPENDENT_REPRODUCTION` record
- Restart rule: a later independent or restarted SIM-002 cohort must use the next unused shared RNN, starting with `R02`
- Append-only rule: prior result, payload, and run-record paths must never be overwritten or silently reused as acceptance evidence for a restarted cohort

## Pre-Execution Immutable Fields

| Field | Frozen value or requirement |
| --- | --- |
| Consumer execution-input revision | `20b512f5bcff53aa10416c91e66e11d92a95fcf6` |
| Hub pin recorded by Consumer | `e9478de80719087167e9f4bb1091497df49186e0` |
| Scenario ID | `SIM-002` |
| Scenario path | `scenarios/SIM-002-qa-automate.md` |
| Scenario SHA-256 | `76eaafb87911da0d4bf69bdf5bb62c9262dc5f025ad44381dbeeeab5960cb426` |
| Fixture path | `fixtures/automation/approved-test-plan.md` |
| Fixture SHA-256 | `1ddce5565a1356ae661d6f0e487183cc9d0934056a432d5b4c837e7cd8e39aa7` |
| Oracle path | `expected/SIM-002-expected.md` |
| Oracle SHA-256 | `a09b2f4b43ea83a2e0a52439e757ffba1de1cd926ce79cd31dbda50a0e08ae88` |
| Evaluation rules / C1-C10 reference | `docs/stage7-execution-plan.md`, Stage 7 acceptance criteria C1-C10 |
| Stage 6 evidence contract versions | `contracts/evidence/v1/*.schema.json`, version `1.0.0` |
| Stage 7 run-record contract version | `contracts/execution/v1/run-record.schema.json`, version `1.0.0` |
| Semantic validator version/revision | `scripts/validate_sandbox.py` at Consumer revision `20b512f5bcff53aa10416c91e66e11d92a95fcf6`, SHA-256 `bf1cee7c8156723408a80507cdb4dc1eb4e3eb4de0aeaf037387772ff8db14d3` |
| CI workflow revision | `.github/workflows/qa-hub-integration.yml` at Consumer revision `20b512f5bcff53aa10416c91e66e11d92a95fcf6`, SHA-256 `52e59e285891419d71e94d57b64ef8f9f06db615e39ec9fa38b73ccf32d5f3c7` |
| Model ID policy | Capture the exact model identifier used for each member in the run record; do not substitute aliases after execution |
| Execution surface/version requirement | Capture the exact execution surface and version available to the executor for each member |
| OS/build and architecture requirement | Capture OS name, OS version/build, and architecture for each member |
| Runtime/tool-version requirement | Capture the runtime and validator/tool versions used to produce and validate each generated artifact |
| Executor identity requirement | Capture the executor identity or role permitted by governance for each member |
| Fresh-context requirement | P1, P2, and IR must each run in a fresh execution context; IR must not depend on P1 or P2 outputs |
| Cohort attempt | `R01` |

## First Cohort Map

| Member | Role | Run ID | Result path | Payload path | Run-record path |
| --- | --- | --- | --- | --- | --- |
| `P1` | `PRIMARY` | `S7-SIM-002-P1-R01` | `results/SIM-002-stage7-p1-r01.md` | `evidence/runs/SIM-002/S7-SIM-002-P1-R01.payload.json` | `evidence/runs/SIM-002/S7-SIM-002-P1-R01/run-record.v1.json` |
| `P2` | `PRIMARY` | `S7-SIM-002-P2-R01` | `results/SIM-002-stage7-p2-r01.md` | `evidence/runs/SIM-002/S7-SIM-002-P2-R01.payload.json` | `evidence/runs/SIM-002/S7-SIM-002-P2-R01/run-record.v1.json` |
| `IR` | `INDEPENDENT_REPRODUCTION` | `S7-SIM-002-IR-R01` | `results/SIM-002-stage7-ir-r01.md` | `evidence/runs/SIM-002/S7-SIM-002-IR-R01.payload.json` | `evidence/runs/SIM-002/S7-SIM-002-IR-R01/run-record.v1.json` |

## Run-Time And Post-Run Fields Left Unset

The following values cannot exist before execution and must not be fabricated in this readiness record:

- actual execution timestamps
- exact observed execution surface/version values
- exact observed OS/build, architecture, runtime, and tool-version values
- executor identity values
- result artifact SHA-256 values
- payload artifact path/hash values beyond the deterministic path convention above
- evidence IDs and routing trace payload content
- generated run-record content and any external digest of it
- generated-artifact validator results
- CI run ID or local equivalent for generated artifacts
- manifest selection status
- acceptance, reproducibility, or release-readiness decisions

## Oracle Governance

- Oracle path frozen for R01: `expected/SIM-002-expected.md`
- Oracle SHA-256 frozen for R01: `a09b2f4b43ea83a2e0a52439e757ffba1de1cd926ce79cd31dbda50a0e08ae88`
- Oracle content must not change during R01 execution.
- Automatic oracle correction is forbidden.
- A suspected oracle defect causes STOP.
- Any oracle correction requires the documented Human Gate Level 3 oracle-policy approval path.
- Corrected execution must restart with the next unused shared RNN.
- Already-created prior artifacts remain historical and cannot silently become acceptance evidence for the restarted cohort.

## Approval Boundary

This record may be cited as `READY_FOR_LEVEL3_EXECUTION_APPROVAL`.

It must not be cited as an execution approval. The only next action it prepares is explicit Human Gate Level 3 controlled-execution approval for SIM-002 R01.