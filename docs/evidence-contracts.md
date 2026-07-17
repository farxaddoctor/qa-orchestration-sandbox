# Evidence contracts v1

## Purpose and scope

The evidence contracts define versioned, machine-readable structures for recorded QA orchestration evidence. They cover an evidence payload, its routing trace, and the manifest that selects result artifacts for the six canonical simulation IDs.

These contracts describe structure and selection. They do not execute scenarios, evaluate oracle correctness, or establish acceptance, release readiness, or reproducibility. In particular, `canonical` means the selected primary result for a scenario; it does not mean that the result was accepted.

## Contract location and versioning

Version 1 is stored under `contracts/evidence/v1/`. All three schemas use JSON Schema Draft 2020-12 and require `schema_version` to be `1.0.0`.

| Contract | File | Schema ID |
| --- | --- | --- |
| Payload | `contracts/evidence/v1/payload.schema.json` | `urn:qa-orchestration-sandbox:evidence:v1:payload` |
| Routing trace | `contracts/evidence/v1/routing-trace.schema.json` | `urn:qa-orchestration-sandbox:evidence:v1:routing-trace` |
| Manifest | `contracts/evidence/v1/manifest.schema.json` | `urn:qa-orchestration-sandbox:evidence:v1:manifest` |

The directory version (`v1`), schema IDs, and `schema_version` fields are explicit version boundaries. A future incompatible contract belongs in a new versioned location and must not silently change the meaning of v1 data.

The current in-place changes correct a rejected, pre-acceptance Stage 6 v1 candidate before Stage 6 closeout. Version 1 has not been accepted, released, declared release-ready, or claimed reproducible. The directory, schema IDs, and `schema_version: 1.0.0` therefore remain unchanged while the rejected candidate's intended Human Gate and artifact-path semantics are corrected.

## Payload contract

The payload records one scenario result together with its routing trace and provenance. The top-level object requires:

- `schema_version`: exactly `1.0.0`.
- `evidence_id`: an ID such as `SIM-001:qa-design:v1`; it must contain a supported scenario prefix and the `v1` suffix.
- `scenario_id`: one of `SIM-001` through `SIM-006`.
- `result_artifact`: the result path and SHA-256 digest.
- `routing_trace`: an object governed by the routing trace schema.
- `provenance`: the Consumer revision, Hub pin, and payload/routing-trace schema versions.

The selected `scenario_id` constrains the prefixes of `evidence_id` and `result_artifact.path`, and it must match `routing_trace.simulation_id`. A result artifact requires:

- `path`: a scenario-matching Markdown path under `results/` matching `^results/SIM-00[1-6]-[A-Za-z0-9._/-]+\.md$`; at least one character is required after the scenario prefix and parent-directory traversal is forbidden.
- `sha256`: exactly 64 lowercase hexadecimal characters.

Payload provenance requires 40-character lowercase hexadecimal values for `consumer_revision` and `hub_pin`. Its `schema_versions` object requires `payload` and `routing_trace`, both set to `1.0.0`.

## Routing trace contract

The routing trace captures the required orchestration path for one simulation. It requires all of these fields:

- `schema_version`
- `simulation_id`
- `status`
- `command`
- `constitution`
- `policies`
- `workflow`
- `primary_agent`
- `supporting_agents`
- `skills`
- `audit_before_edit`
- `human_gate`
- `stop_condition`
- `expected_artifact`

`simulation_id` is limited to `SIM-001` through `SIM-006`. `status` is limited to `PASS`, `FAIL`, `BLOCKED`, or `HUMAN_APPROVAL_REQUIRED`. String routing fields must be non-empty. `policies` and `skills` must each contain at least one unique, non-empty string. `supporting_agents` may be empty, but any entries must be unique, non-empty strings.

`human_gate` requires `required`, `level`, `approval_state`, and `approved_scope`. `required` is `true` when the action is governed by Level 1 through 3 approval, regardless of whether approval is pending, approved, or rejected. `approved_scope` is either `null` or a non-empty string containing at least one non-whitespace character.

| Status | `required` | `level` | `approval_state` | `approved_scope` |
| --- | --- | --- | --- | --- |
| `PASS`, `FAIL`, or `BLOCKED` | `false` | `0` | `NOT_REQUIRED` | `null` |
| `HUMAN_APPROVAL_REQUIRED` | `true` | `1` through `3` | `PENDING` | `null` |
| `PASS`, `FAIL`, or `BLOCKED` | `true` | `1` through `3` | `APPROVED` | Non-empty, non-whitespace string |
| `BLOCKED` | `true` | `1` through `3` | `REJECTED` | `null` |

The schema encodes this matrix in both the Human Gate object and the routing-trace status conditions. A pending or rejected gate cannot validate with `PASS`, and an approved gate cannot validate without a recorded approved scope.

## Manifest contract

The manifest records the current artifact selection. Its top-level object requires:

- `schema_version`: exactly `1.0.0`.
- `manifest_id`: a lowercase versioned identifier ending in `:v1`.
- `provenance`: the source revisions and all three schema versions.
- `scenarios`: entries for every ID from `SIM-001` through `SIM-006`.

Each scenario entry requires:

- `scenario_id`: fixed to the containing scenario key.
- `canonical`: either a scenario-matching artifact descriptor or `null`.
- `historical_attempts`: a unique array of scenario-matching artifact descriptors; it may be empty.

An artifact descriptor requires `evidence_id`, `result_path`, and `sha256`. Its evidence ID and result path must match the containing scenario, result paths must remain under `results/` without parent-directory traversal, and SHA-256 values must contain 64 lowercase hexadecimal characters.

All contract objects use `additionalProperties: false`; undeclared fields are rejected.

## Canonical selection and historical attempts

`canonical` records which result is selected as the primary result for a scenario. Selection is not acceptance and does not make a claim about oracle correctness, release readiness, or reproducibility. The schema permits `canonical: null` when no result has been selected, but the current manifest selects one result for each of the six scenarios.

`historical_attempts` records non-canonical attempts separately. The only historical attempt currently recorded is `results/SIM-001-attempt-2-oracle-fail.md`; it is not the canonical SIM-001 result.

Draft 2020-12 directly enforces descriptor shape, scenario prefixes, digest syntax, closed objects, and exact-object uniqueness within `historical_attempts`. With the current object shape it does not compare values across `canonical` and `historical_attempts`. `evidence_id` and `result_path` are independent identity keys. The following are mandatory out-of-schema semantic invariants across the union of `canonical` and `historical_attempts`:

- `canonical` and `historical_attempts` must be disjoint.
- Every `evidence_id` must be unique; repeating an `evidence_id` is invalid regardless of the associated `result_path` or SHA-256.
- Every `result_path` must be unique; repeating a `result_path` is invalid regardless of the associated `evidence_id` or SHA-256.
- An `evidence_id` identifies exactly one `result_path`/SHA-256 association.
- A `result_path` identifies exactly one `evidence_id`/SHA-256 association.
- Because repetition of either identity key is forbidden, conflicting hashes for a repeated key are also forbidden.

The examples under `contracts/evidence/v1/examples/semantic-invalid/` intentionally pass JSON Schema validation while violating these invariants. They are unacceptable as evidence. `manifest-canonical-in-history.json` is intentionally compound: exact reappearance of the canonical descriptor in `historical_attempts` demonstrates canonical/history overlap and necessarily also repeats its `evidence_id` and `result_path`; it is not claimed to isolate only one invariant. `manifest-duplicate-evidence-id.json` isolates a repeated `evidence_id` while using a distinct `result_path`, and `manifest-duplicate-result-path.json` isolates a repeated `result_path` while using a distinct `evidence_id`. Enforcing these cross-object invariants requires Stage 7 semantic validation; Stage 6 documents the boundary and does not implement that validator.

## Current manifest mapping

The versioned canonical manifest is `evidence/manifest.v1.json`.

| Scenario | Canonical result | SHA-256 | Historical attempts |
| --- | --- | --- | --- |
| `SIM-001` | `results/SIM-001-qa-design.md` | `cdf2ddd4aa30b811a1361b988fa606085b3aef61334580e27918787b86d0408c` | `results/SIM-001-attempt-2-oracle-fail.md` |
| `SIM-002` | `results/SIM-002-qa-automate.md` | `781d49abb107a192ce47cd3ecc94340715254e1e28e17f4ed1a42eca8713f3dd` | None |
| `SIM-003` | `results/SIM-003-qa-review.md` | `01810d3da984c8b052b726443b3dbbb6a03a0b9e91a40684a828e973559e0dfd` | None |
| `SIM-004` | `results/SIM-004-qa-audit.md` | `5d4e05c2f7dbffa5389eb86f186defa6ade943b8b68f0cb82759badfbca2976d` | None |
| `SIM-005` | `results/SIM-005-qa-debug.md` | `08254bcde0e07ebd800c8f1335b905d58e56a73c9657746aa31abfcb77e1a546` | None |
| `SIM-006` | `results/SIM-006-qa-bug-report.md` | `774c38f29ac35e84be4743c6421c6b07694763ad5a656306f4a9c7fc1afa4d1b` | None |

The SIM-001 historical attempt has SHA-256 `dcfa55ae4b26c377a41e9d12e6a81de6809b33cb017166e5707481d2a7396826`.

## Provenance and artifact integrity

The current manifest records:

- `consumer_revision`: `777f7d5cc5017260df04c012eae963ef3ad63379`
- `hub_pin`: `81197bf84ed51913bc3a93ace41661ab80a8e3b9`
- `payload`, `routing_trace`, and `manifest` schema versions: `1.0.0`

`consumer_revision` is the Consumer revision of the source result artifacts. It is not the commit that added or last changed the manifest. `hub_pin` is the Hub revision used by those source artifacts. The recorded SHA-256 values are calculated from the actual bytes of the referenced result artifacts.

Provenance and digests identify the recorded inputs; they do not by themselves demonstrate acceptance or reproducibility.

## Examples

The example set covers the four Human Gate states, the aligned artifact-path rule, and the documented manifest semantic boundary:

| Schema expectation | Example | Purpose |
| --- | --- | --- |
| Valid | `examples/valid/routing-trace.json` | `NOT_REQUIRED` with `PASS` |
| Valid | `examples/valid/routing-trace-pending.json` | `PENDING` with `HUMAN_APPROVAL_REQUIRED` |
| Valid | `examples/valid/routing-trace-approved.json` | `APPROVED` with a recorded scope |
| Valid | `examples/valid/routing-trace-rejected.json` | `REJECTED` with `BLOCKED` |
| Invalid | `examples/invalid/routing-trace-invalid-status.json` | `status` is outside the enum |
| Invalid | `examples/invalid/routing-trace-unapproved-pass.json` | A pending gate reports `PASS` |
| Invalid | `examples/invalid/routing-trace-approved-missing-scope.json` | An approved gate has no scope |
| Invalid | `examples/invalid/routing-trace-rejected-pass.json` | A rejected gate reports `PASS` |
| Valid | `examples/valid/payload.json` | Valid payload and nested routing trace |
| Invalid | `examples/invalid/payload-human-gate-mismatch.json` | `NOT_REQUIRED` uses nonzero level |
| Invalid | `examples/invalid/payload-empty-artifact-name.json` | Artifact path is `results/SIM-001-.md` |
| Valid | `examples/valid/manifest.json` | Structurally valid manifest |
| Invalid | `examples/invalid/manifest-missing-canonical.json` | Required `canonical` is missing from `SIM-006` |
| Schema-valid, semantic-invalid | `examples/semantic-invalid/manifest-canonical-in-history.json` | Compound fixture: the canonical descriptor is also historical, necessarily repeating both identity keys |
| Schema-valid, semantic-invalid | `examples/semantic-invalid/manifest-duplicate-evidence-id.json` | `evidence_id` is duplicated while `result_path` remains distinct |
| Schema-valid, semantic-invalid | `examples/semantic-invalid/manifest-duplicate-result-path.json` | `result_path` is duplicated while `evidence_id` remains distinct |

Paths in this table are relative to `contracts/evidence/v1/`. Each schema-invalid example differs structurally from its valid base only in its named condition. Semantic-invalid examples are expected to pass Ajv and remain unacceptable as evidence.

## Local validation with Ajv

Run these commands from the Consumer repository root. They use pinned, ephemeral `ajv-cli@5.0.0`; no repository dependency is added. `ajv-cli test` succeeds only when data supplied with `--valid` validates or data supplied with `--invalid` is rejected as expected.

```powershell
npx --yes ajv-cli@5.0.0 test --spec=draft2020 --strict=true -s contracts/evidence/v1/routing-trace.schema.json -d contracts/evidence/v1/examples/valid/routing-trace.json --valid
npx --yes ajv-cli@5.0.0 test --spec=draft2020 --strict=true -s contracts/evidence/v1/routing-trace.schema.json -d contracts/evidence/v1/examples/valid/routing-trace-pending.json --valid
npx --yes ajv-cli@5.0.0 test --spec=draft2020 --strict=true -s contracts/evidence/v1/routing-trace.schema.json -d contracts/evidence/v1/examples/valid/routing-trace-approved.json --valid
npx --yes ajv-cli@5.0.0 test --spec=draft2020 --strict=true -s contracts/evidence/v1/routing-trace.schema.json -d contracts/evidence/v1/examples/valid/routing-trace-rejected.json --valid
npx --yes ajv-cli@5.0.0 test --spec=draft2020 --strict=true -s contracts/evidence/v1/routing-trace.schema.json -d contracts/evidence/v1/examples/invalid/routing-trace-invalid-status.json --invalid
npx --yes ajv-cli@5.0.0 test --spec=draft2020 --strict=true -s contracts/evidence/v1/routing-trace.schema.json -d contracts/evidence/v1/examples/invalid/routing-trace-unapproved-pass.json --invalid
npx --yes ajv-cli@5.0.0 test --spec=draft2020 --strict=true -s contracts/evidence/v1/routing-trace.schema.json -d contracts/evidence/v1/examples/invalid/routing-trace-approved-missing-scope.json --invalid
npx --yes ajv-cli@5.0.0 test --spec=draft2020 --strict=true -s contracts/evidence/v1/routing-trace.schema.json -d contracts/evidence/v1/examples/invalid/routing-trace-rejected-pass.json --invalid
npx --yes ajv-cli@5.0.0 test --spec=draft2020 --strict=true -s contracts/evidence/v1/payload.schema.json -r contracts/evidence/v1/routing-trace.schema.json -d contracts/evidence/v1/examples/valid/payload.json --valid
npx --yes ajv-cli@5.0.0 test --spec=draft2020 --strict=true -s contracts/evidence/v1/payload.schema.json -r contracts/evidence/v1/routing-trace.schema.json -d contracts/evidence/v1/examples/invalid/payload-human-gate-mismatch.json --invalid
npx --yes ajv-cli@5.0.0 test --spec=draft2020 --strict=true -s contracts/evidence/v1/payload.schema.json -r contracts/evidence/v1/routing-trace.schema.json -d contracts/evidence/v1/examples/invalid/payload-empty-artifact-name.json --invalid
npx --yes ajv-cli@5.0.0 test --spec=draft2020 --strict=true -s contracts/evidence/v1/manifest.schema.json -d contracts/evidence/v1/examples/valid/manifest.json --valid
npx --yes ajv-cli@5.0.0 test --spec=draft2020 --strict=true -s contracts/evidence/v1/manifest.schema.json -d contracts/evidence/v1/examples/invalid/manifest-missing-canonical.json --invalid
npx --yes ajv-cli@5.0.0 test --spec=draft2020 --strict=true -s contracts/evidence/v1/manifest.schema.json -d evidence/manifest.v1.json --valid
npx --yes ajv-cli@5.0.0 test --spec=draft2020 --strict=true -s contracts/evidence/v1/manifest.schema.json -d contracts/evidence/v1/examples/semantic-invalid/manifest-canonical-in-history.json --valid
npx --yes ajv-cli@5.0.0 test --spec=draft2020 --strict=true -s contracts/evidence/v1/manifest.schema.json -d contracts/evidence/v1/examples/semantic-invalid/manifest-duplicate-evidence-id.json --valid
npx --yes ajv-cli@5.0.0 test --spec=draft2020 --strict=true -s contracts/evidence/v1/manifest.schema.json -d contracts/evidence/v1/examples/semantic-invalid/manifest-duplicate-result-path.json --valid
```

These are local contract assertions. The final three assertions deliberately confirm the boundary between schema validation and unacceptable semantic evidence; they do not accept those manifests. Stage 6 does not add repository CI enforcement or semantic-validator implementation for schema or manifest validation.

## Encoding and line endings

The versioned evidence JSON is stored as UTF-8 without a byte-order mark, NUL bytes, or carriage returns. Files use two-space indentation, LF line endings, and a trailing LF.

The repository applies these Git attributes:

```gitattributes
contracts/evidence/v1/**/*.json text eol=lf
evidence/*.json text eol=lf
```

These attributes guarantee LF checkout for the covered JSON paths. They do not validate UTF-8 encoding or JSON content.

## Stage boundaries

Stage 6 provides versioned schemas, examples, the canonical selection manifest, and their documentation. It does not run evidence scenarios or create new result artifacts.

The following remain outside Stage 6 and are not implemented here:

- `scripts/validate_sandbox.py`
- schema or manifest CI enforcement
- oracle change-control
- controlled evidence execution
- new result generation
- reproducibility claims
- acceptance or release-readiness reports

Those concerns belong to later work, including Stage 7 where applicable.
