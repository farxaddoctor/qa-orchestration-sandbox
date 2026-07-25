# Stage 7 SIM-002/R02 Freeze Readiness

## Status

`READY_FOR_LEVEL3_EXECUTION_APPROVAL`

This document prepares the SIM-002/R02 freeze/readiness record only. It does not approve execution, does not create runtime evidence, and does not authorize any Stage 7 scenario run.

## Cohort

- Scenario: `SIM-002`
- Attempt: `R02`
- Members: `P1`, `P2`, `IR`
- `R01` remains immutable v1 historical/non-acceptance evidence.
- `R02` must use run-record v2 only.

## Execution-Input Revision

`e69d9f5d6a73c2a4c063b675da5aff81574fb5bd`

## Revision Semantics

- `actual execution_repository_revision` will be captured at run time.
- A later freeze-document-only revision delta is allowed only after explicit review.
- `execution_affecting_change_present` must remain `false`.
- No execution-affecting change may be hidden by `revision_delta`.

## Frozen Input Hashes

| Path | SHA-256 |
| --- | --- |
| `scenarios/SIM-002-qa-automate.md` | `76eaafb87911da0d4bf69bdf5bb62c9262dc5f025ad44381dbeeeab5960cb426` |
| `fixtures/automation/approved-test-plan.md` | `1ddce5565a1356ae661d6f0e487183cc9d0934056a432d5b4c837e7cd8e39aa7` |
| `expected/SIM-002-expected.md` | `a09b2f4b43ea83a2e0a52439e757ffba1de1cd926ce79cd31dbda50a0e08ae88` |
| `contracts/execution/v2/run-record.schema.json` | `35a44db33fdf956fad2542a96982a1c698bf61ce80a7a340749974c797637d22` |
| `scripts/validate_sandbox.py` | `c205e2e14fd7826e29bc43defc00e756ceb8f4a51456b81f7b0a812fb801c38b` |
| `.github/workflows/qa-hub-integration.yml` | `dde9615ec2ccb5cba6af780e7e89f5f2b309a030d7c256feaf0e53c22bbd1d0c` |
| `docs/stage7-execution-plan.md` | `a51ef020ad02afe80fa7e27dc20fefa8467bab4220501ec958cfb06bfcceb936` |

## Windows P1/P2 Surface

```yaml
execution_surface:
  name: OpenAI Codex CLI
  version:
    availability: EXACT
    value: 0.144.6
```

- Executable: `C:\Users\user\AppData\Local\Programs\OpenAI\Codex\bin\codex.exe`
- Executable SHA-256: `4b76ded066d0239115ca97473d010c92072bc5c5550a45dd7cbebe1e9eb956a7`
- Runtime: `0.144.6-x86_64-pc-windows-msvc`
- Model configuration: `gpt-5.5`
- Reasoning: `high`

## Ubuntu IR Surface

```yaml
execution_surface:
  name: OpenAI Codex CLI
  version:
    availability: EXACT
    value: 0.144.6
```

- Launcher: `/home/user/.local/stage7-ir/bin/codex-0.144.6`
- Launcher SHA-256: `c4d6a7e3a26128f680dbd40149c330dfd10bd5c9396528f5956401048efcfbae`
- Native executable SHA-256: `a31ae9450a26216eb1e7c53102fd42123dd675974310b0e2ca3aa4cb622a2c15`
- Platform: `Ubuntu 24.04.2 LTS, WSL2, x86_64`
- Runtime: `x86_64-unknown-linux-musl`
- Node: `22.23.1`

IR must use:

- A fresh CLI session.
- A native Linux checkout.
- No resume or fork.
- No P1/P2 conversational state.
- No P1/P2 result artifacts as input.

## Exact Identities And Paths

### P1

- Identity: `S7-SIM-002-P1-R02`
- Result: `results/SIM-002-stage7-p1-r02.md`
- Payload: `evidence/runs/SIM-002/S7-SIM-002-P1-R02.payload.json`
- Run record: `evidence/runs/SIM-002/S7-SIM-002-P1-R02/run-record.v2.json`

### P2

- Identity: `S7-SIM-002-P2-R02`
- Result: `results/SIM-002-stage7-p2-r02.md`
- Payload: `evidence/runs/SIM-002/S7-SIM-002-P2-R02.payload.json`
- Run record: `evidence/runs/SIM-002/S7-SIM-002-P2-R02/run-record.v2.json`

### IR

- Identity: `S7-SIM-002-IR-R02`
- Result: `results/SIM-002-stage7-ir-r02.md`
- Payload: `evidence/runs/SIM-002/S7-SIM-002-IR-R02.payload.json`
- Run record: `evidence/runs/SIM-002/S7-SIM-002-IR-R02/run-record.v2.json`

## Required Gates And Stop Conditions

- This document does not approve execution.
- Separate Human Gate Level 3 approval remains required before execution.
- `C1`-`C10`, validator result, run acceptance, and reproducibility are runtime/post-run evidence.
- No automatic oracle correction is authorized.
- Path collisions or input changes cause `STOP`.
- No `R02` artifact may overwrite `R01`.
