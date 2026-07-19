# Stage 7 Run-Record Contract

## Purpose and ownership

The Stage 7 run-record contract defines a separate machine-readable record for controlled execution provenance. It records who or what synthetic executor performed a run, when the run occurred, the execution environment, frozen input references, and output artifact references.

Ownership belongs to the Stage 7 contract owner. It is not owned by the payload v1 contract, the manifest curator, or the evidence executor. Changes to this contract require a separately approved scope and must not be mixed with scenario execution, evidence generation, oracle changes, manifest updates, validator implementation, or CI changes.

This document and the schema are contract infrastructure only. They do not start controlled execution, authorize scenario execution, generate evidence, accept evidence, establish release readiness, or establish reproducibility.

## Separation from payload v1

The closed Stage 6 payload contract remains unchanged under `contracts/evidence/v1/payload.schema.json`. Payload v1 contains only its existing evidence payload fields and its existing provenance object. Because payload v1 is closed with `additionalProperties: false`, Stage 7-only fields such as `run_id`, `cohort_id`, executor identity, model identifier, execution surface, timestamps, fixture hashes, and oracle hashes must not be added to payload v1.

The run record references payload artifacts by:

- payload path under `evidence/runs/`;
- payload SHA-256;
- payload `evidence_id`.

The run record is a companion artifact. It does not redefine payload v1 and does not expand payload v1.

## Field reference

Top-level required fields:

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

Version 1 lives under `contracts/execution/v1/` and uses `schema_version: 1.0.0`. Incompatible changes belong in a future versioned directory and schema ID. Compatible clarifications may be documented without changing the meaning of v1 data.

This contract is additive to Stage 6 evidence contracts. It does not alter `contracts/evidence/v1/`, `evidence/manifest.v1.json`, or any payload/routing-trace semantics.

## Line-ending attributes

The contract schema and examples under `contracts/execution/v1/**/*.json` are protected as LF text by the repository attributes. Future run records and payload sidecars under `evidence/runs/**/*.json` are also protected as LF text by the repository attributes. These LF attributes preserve cross-platform bytes for strict encoding checks; they do not establish semantic validity, evidence acceptance, release readiness, or reproducibility.

## Append-only behavior

Future run records are append-only. A run ID or path collision is a hard stop. Existing run records, external run-record index entries, payloads, results, and manifest history entries must not be overwritten or silently replaced. Failed, rejected, exploratory, superseded, and restarted attempts remain historical when tracked.

## Example expectations

The valid example under `contracts/execution/v1/examples/valid/run-record.json` is synthetic structural data only. It is not evidence and does not claim that controlled execution occurred.

The invalid examples isolate schema failures:

- `run-record-missing-model-id.json` omits the required `model_id` field.
- `run-record-invalid-role.json` uses an unsupported `execution_role`.

The semantic-invalid examples are expected to pass JSON Schema but remain unacceptable:

- `run-record-cohort-mismatch.json` has a `run_id` cohort segment that differs from `cohort_id`.
- `run-record-artifact-hash-mismatch.json` records a structurally valid result SHA-256 that is documented as not matching the referenced artifact bytes.

## Deferred validator and CI work

Validator and CI integration are explicitly deferred. This contract candidate does not update `scripts/validate_sandbox.py`, tests, workflow files, dependencies, lockfiles, manifests, or evidence contracts. Future validator work must be separately approved and must verify semantic invariants, file existence, link safety, hash integrity, append-only identity, cross-file alignment, and any future external run-record index or manifest.

## Authorization boundary

This contract does not authorize controlled execution, scenario execution, evidence generation, acceptance, release readiness, reproducibility claims, manifest selection, oracle changes, fixture changes, result creation, payload creation, or roadmap changes. Controlled execution remains `NOT STARTED` until a separate approved Level 3 execution gate is granted and all hard dependencies are satisfied.
