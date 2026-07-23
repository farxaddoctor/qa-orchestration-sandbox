# Stage 7 Run-Record Contract

## Purpose and ownership

The Stage 7 run-record contract defines a separate machine-readable record for controlled execution provenance. It records who or what synthetic executor performed a run, when the run occurred, the execution environment, frozen input references, output artifact references, and, beginning with v2, post-run evaluation and validator-result evidence.

Ownership belongs to the Stage 7 contract owner. It is not owned by the payload v1 contract, the manifest curator, or the evidence executor. Changes to this contract require a separately approved scope and must not be mixed with scenario execution, evidence generation, oracle changes, manifest updates, validator implementation, or CI changes.

This document and the schema are contract infrastructure only. They do not start controlled execution, authorize scenario execution, generate evidence, accept evidence, establish release readiness, or establish reproducibility.

## Separation from payload v1

The closed Stage 6 payload contract remains unchanged under `contracts/evidence/v1/payload.schema.json`. Payload v1 contains only its existing evidence payload fields and its existing provenance object. Because payload v1 is closed with `additionalProperties: false`, Stage 7-only fields such as `run_id`, `cohort_id`, executor identity, model identifier, execution surface, timestamps, fixture hashes, and oracle hashes must not be added to payload v1.

The run record references payload artifacts by:

- payload path under `evidence/runs/`;
- payload SHA-256;
- payload `evidence_id`.

The run record is a companion artifact. It does not redefine payload v1 and does not expand payload v1.

## Version 2 correction

Run-record v2 lives under `contracts/execution/v2/` and uses `schema_version: 2.0.0`. It is the minimum correction for future acceptance-eligible Stage 7 cohorts after the historical SIM-002/R01 pilot exposed v1 evidence-design gaps. Run-record v1 remains immutable and valid only under its original historical semantics.

V2 records two Consumer revisions explicitly:

| Field | Meaning |
| --- | --- |
| `provenance.execution_input_revision` | The approved frozen Consumer revision whose execution-affecting inputs are evaluated: scenario, fixture, oracle, Hub pin, contracts, validator basis, and evaluation rules as applicable. It is captured before execution. |
| `provenance.execution_repository_revision` | The actual Consumer `HEAD` checked out when the run occurred. It is captured at run time. |

The two revisions may be equal. If they differ, `provenance.revision_delta` must explicitly record that the difference was reviewed, why it is allowed, and that no execution-affecting change is present. This explicit provenance is auditable; it must not be used to hide scenario, fixture, oracle, contract, validator, CI, or Hub-pin changes.

V2 also records `evaluation`, a post-run section containing C1-C10 binary criteria, total score, result, oracle path/SHA, evaluator identity, evaluation method, validator command/result, run-level acceptance outcome, and reproducibility claim status. Evaluation belongs in the run record, not in the immutable raw result Markdown or closed payload v1. Cohort acceptance and reproducibility remain derived from the three member run records and the Stage 7 thresholds; no separate cohort artifact is introduced by v2.

V2 models execution-surface version as structured provenance. Exact versions use `availability: EXACT` plus `value`. When the surface cannot expose an exact version, the record must use `availability: UNAVAILABLE` plus `reason`; sentinel prose such as `not-exposed-by-session` must not be recorded as an exact version. A run with an unavailable exact surface version may be preserved as historical/non-reproducible evidence, but it cannot claim reproducibility or contribute to full Stage 7 acceptance under the current plan.

## Field reference

Top-level v1 required fields:

| Field | Meaning |
| --- | --- |
| `schema_version` | Run-record contract version, exactly `1.0.0`. |
| `run_id` | Controlled run identifier using `S7-<SIM-ID>-<COHORT>-R<NN>`. |
| `cohort_id` | Cohort identifier: `P1`, `P2`, or `IR`. |
| `scenario_id` | Scenario identifier from `SIM-001` through `SIM-006`. |
| `execution_role` | `PRIMARY` or `INDEPENDENT_REPRODUCTION`. |
| `attempt_number` | Numeric attempt corresponding semantically to the `R<NN>` run segment. |
| `executor_id` | Synthetic, non-personal executor identifier. |
| `started_at` | UTC timestamp ending in `Z`. |
| `completed_at` | UTC timestamp ending in `Z`. |
| `model_id` | Exact model identifier as recorded by the future approved execution protocol. |
| `execution_surface` | Closed object containing surface name and version. |
| `environment` | Closed object containing OS name, OS version, and architecture. |
| `runtime_versions` | Closed object containing Python, Git, Node, npm, npx, Ajv CLI, and sandbox-validator versions. |
| `provenance` | Closed object containing Consumer execution-input SHA, Hub pin, and schema versions. |
| `inputs` | Closed object containing scenario, consumed fixtures, and oracle path/SHA records. |
| `artifacts` | Closed object containing payload and result artifact references. The run record does not contain its own complete-byte digest. |

The `provenance.schema_versions` object records `payload`, `routing_trace`, and `run_record`, all exactly `1.0.0`.

## Path and identity rules

All paths are repository-relative forward-slash paths. Absolute paths, drive paths, UNC paths, backslashes, and parent traversal are forbidden.

Required path locations:

| Artifact | Path rule |
| --- | --- |
| Run-record external index entry | A future separate index or manifest may record run-record path and digest after the run-record bytes exist. That index is deferred and separately gated. |
| Payload | Under `evidence/runs/`, matching `evidence/runs/<SIM-ID>/S7-<SIM-ID>-<COHORT>-R<NN>.payload.json`. |
| Scenario | Under `scenarios/`, with a scenario-aligned `SIM-00N` prefix. |
| Fixture | Under `fixtures/`. |
| Oracle | Under `expected/`, with a scenario-aligned `SIM-00N` prefix. |
| Result | Under `results/`, matching `^results/SIM-00[1-6]-[A-Za-z0-9._/-]+\.md$`. |

All SHA-256 values recorded inside the run record are exactly 64 lowercase hexadecimal characters. Consumer execution-input SHA and Hub pin values are exactly 40 lowercase hexadecimal characters. The run record intentionally does not contain the SHA-256 of its own complete bytes, because that would create a recursive self-hash dependency. A run-record path and digest belong only in a future separate external index or manifest after the record bytes exist; that external index or manifest remains deferred and separately gated.

The schema enforces scenario-aligned prefixes for `run_id`, scenario path, oracle path, payload `evidence_id`, payload path, and result path where Draft 2020-12 can express those structural checks.

## Schema and semantic boundary

The schema enforces:

- JSON Schema Draft 2020-12 metadata and schema ID `urn:qa-orchestration-sandbox:execution:v1:run-record`;
- `schema_version: 1.0.0`;
- required fields;
- closed objects with `additionalProperties: false`;
- supported scenario IDs;
- run-ID shape;
- execution-role vocabulary;
- UTC timestamp shape ending in `Z`;
- path prefixes and unsafe-path rejection, including backslashes, absolute paths, drive-qualified paths, UNC paths, parent components, dot components, empty internal components, and leading or trailing unsafe separators;
- scenario-aligned run ID, result, evidence, scenario, oracle, and payload prefixes;
- SHA-1 and SHA-256 syntax.

The following semantic invariants are documented but intentionally out of schema:

- `run_id` cohort segment equals `cohort_id`;
- `attempt_number` corresponds to the `R<NN>` segment;
- `completed_at` is the same as or later than `started_at`;
- each scenario has exactly two `PRIMARY` records and one `INDEPENDENT_REPRODUCTION` record in an approved cohort;
- referenced files exist, are safe regular non-link files, and hashes match their recorded values;
- payload, result, evidence, routing trace, and run-record identities align across files;
- execution-input revision and oracle hashes are identical across an approved cohort;
- the `SIM-002` pilot completes before other scenario cohorts start;
- canonical selection remains separate from acceptance.

Those invariants require a future approved validator. Schema-valid semantic-invalid examples remain unacceptable as evidence.

## Versioning and compatibility

Version 1 lives under `contracts/execution/v1/` and uses `schema_version: 1.0.0`. V1 is immutable and remains valid for historical records only under its original semantics. Version 2 lives under `contracts/execution/v2/` and uses `schema_version: 2.0.0`. Future acceptance-eligible cohorts must use v2 unless a later approved version supersedes it. Incompatible changes belong in a future versioned directory and schema ID. Compatible clarifications may be documented without changing the meaning of prior-version data.

This contract is additive to Stage 6 evidence contracts. It does not alter `contracts/evidence/v1/`, `evidence/manifest.v1.json`, or any payload/routing-trace semantics.

## Line-ending attributes

The contract schema and examples under `contracts/execution/v1/**/*.json` and `contracts/execution/v2/**/*.json` are protected as LF text by the repository attributes. Future run records and payload sidecars under `evidence/runs/**/*.json` are also protected as LF text by the repository attributes. These LF attributes preserve cross-platform bytes for strict encoding checks; they do not establish semantic validity, evidence acceptance, release readiness, or reproducibility.

## Append-only behavior

Future run records are append-only. A run ID or path collision is a hard stop. Existing run records, external run-record index entries, payloads, results, and manifest history entries must not be overwritten or silently replaced. Failed, rejected, exploratory, superseded, and restarted attempts remain historical when tracked.

## Example expectations

The valid examples under `contracts/execution/v1/examples/valid/run-record.json` and `contracts/execution/v2/examples/valid/run-record.json` are synthetic structural data only. They are not evidence and do not claim that controlled execution occurred.

The invalid examples isolate schema failures:

- `run-record-missing-model-id.json` omits the required `model_id` field.
- `run-record-invalid-role.json` uses an unsupported `execution_role`.

The semantic-invalid examples are expected to pass JSON Schema but remain unacceptable:

- `run-record-cohort-mismatch.json` has a `run_id` cohort segment that differs from `cohort_id`.
- `run-record-artifact-hash-mismatch.json` records a structurally valid result SHA-256 that is documented as not matching the referenced artifact bytes.

## Validator and CI boundary

The sandbox validator recognizes v1 and v2 run records independently. It preserves v1 historical validation and adds v2 checks for dual Consumer revisions, C1-C10 completeness, oracle evaluation alignment, validator result evidence, structured execution-surface version availability, and false reproducibility claims. CI workflow integration for v2 remains separately gated and is not changed by the v2 contract slice.

## Authorization boundary

This contract does not authorize controlled execution, scenario execution, evidence generation, acceptance, release readiness, reproducibility claims, manifest selection, oracle changes, fixture changes, result creation, payload creation, or roadmap changes. Controlled execution remains `NOT STARTED` until a separate approved Level 3 execution gate is granted and all hard dependencies are satisfied.

## SIM-002 R01 disposition

The SIM-002/R01 pilot is documented in `docs/stage7-sim-002-r01-disposition.md`. Its artifacts remain immutable historical controlled-execution evidence. They are not acceptance evidence, not reusable as R02 members, and not subject to retroactive v2 repair.
