#!/usr/bin/env python3
"""Read-only Stage 7 sandbox validation foundation."""

from __future__ import annotations

import argparse
import codecs
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any, Iterable


EXIT_PASSED = 0
EXIT_VALIDATION_FAILURE = 1
EXIT_OPERATIONAL_ERROR = 2

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = Path("contracts/evidence/v1")
MANIFEST_PATH = Path("evidence/manifest.v1.json")
SUPPORTED_SCENARIOS = tuple(f"SIM-00{index}" for index in range(1, 7))
SCHEMA_VERSION = "1.0.0"
DRAFT_2020_12_URI = "https" + "://json-schema.org/draft/2020-12/schema"
SCHEMA_IDS = {
    "payload.schema.json": "urn:qa-orchestration-sandbox:evidence:v1:payload",
    "routing-trace.schema.json": "urn:qa-orchestration-sandbox:evidence:v1:routing-trace",
    "manifest.schema.json": "urn:qa-orchestration-sandbox:evidence:v1:manifest",
}
RESULT_PATH_RE = re.compile(r"^results/SIM-00[1-6]-[A-Za-z0-9._/-]+\.md$")
EVIDENCE_ID_RE = re.compile(r"^SIM-00[1-6]:[a-z0-9][a-z0-9._-]*:v1$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
MANIFEST_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]*:v1$")
HEX40_RE = re.compile(r"^[a-f0-9]{40}$")
ROUTING_STATUSES = {"PASS", "FAIL", "BLOCKED", "HUMAN_APPROVAL_REQUIRED"}


class DuplicateKeyError(ValueError):
    """Raised when strict JSON parsing finds a repeated object key."""


@dataclass(frozen=True, order=True)
class Diagnostic:
    severity: str
    code: str
    path: str
    detail: str

    def render(self) -> str:
        return f"{self.severity} {self.code} {self.path} {self.detail}".rstrip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Stage 6 evidence contracts and sandbox invariants."
    )
    parser.add_argument(
        "--root",
        default=str(REPOSITORY_ROOT),
        help="repository root to validate; defaults to this Consumer checkout",
    )
    return parser.parse_args()


def display_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def read_bytes(root: Path, relative_path: Path) -> tuple[bytes | None, Diagnostic | None]:
    path = root / relative_path
    try:
        return path.read_bytes(), None
    except OSError as exc:
        return None, Diagnostic("ERROR", "READ", relative_path.as_posix(), str(exc))


def validate_bytes(
    root: Path, relative_path: Path, *, require_lf: bool = True
) -> list[Diagnostic]:
    data, error = read_bytes(root, relative_path)
    if error is not None:
        return [error]
    assert data is not None
    issues: list[Diagnostic] = []
    path = relative_path.as_posix()
    if data.startswith(
        (
            codecs.BOM_UTF8,
            codecs.BOM_UTF16_LE,
            codecs.BOM_UTF16_BE,
            codecs.BOM_UTF32_LE,
            codecs.BOM_UTF32_BE,
        )
    ):
        issues.append(Diagnostic("FAIL", "ENCODING_BOM", path, "byte-order mark present"))
    try:
        data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        issues.append(Diagnostic("FAIL", "ENCODING_UTF8", path, str(exc)))
    if b"\x00" in data:
        issues.append(Diagnostic("FAIL", "ENCODING_NUL", path, "NUL byte present"))
    if require_lf and b"\r" in data:
        issues.append(Diagnostic("FAIL", "ENCODING_CR", path, "carriage return present"))
    if require_lf and not data.endswith(b"\n"):
        issues.append(Diagnostic("FAIL", "ENCODING_TRAILING_LF", path, "trailing LF missing"))
    if not issues:
        issues.append(Diagnostic("PASS", "ENCODING", path, "strict UTF-8 LF"))
    return issues


def no_duplicate_pairs(path: str) -> Any:
    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DuplicateKeyError(f"duplicate key {key!r} in {path}")
            result[key] = value
        return result

    return hook


def load_json_no_duplicates(
    root: Path, relative_path: Path
) -> tuple[Any | None, list[Diagnostic]]:
    diagnostics = validate_bytes(root, relative_path)
    failures = [diag for diag in diagnostics if diag.severity != "PASS"]
    if failures:
        return None, failures
    data, error = read_bytes(root, relative_path)
    if error is not None:
        return None, [error]
    assert data is not None
    path = relative_path.as_posix()
    try:
        parsed = json.loads(data.decode("utf-8"), object_pairs_hook=no_duplicate_pairs(path))
    except json.JSONDecodeError as exc:
        return None, [Diagnostic("FAIL", "JSON_PARSE", path, str(exc))]
    except DuplicateKeyError as exc:
        return None, [Diagnostic("FAIL", "JSON_DUPLICATE_KEY", path, str(exc))]
    except ValueError as exc:
        return None, [Diagnostic("FAIL", "JSON_VALUE", path, str(exc))]
    return parsed, [Diagnostic("PASS", "JSON", path, "parsed without duplicate keys")]


def require_keys(
    value: Any, path: str, keys: Iterable[str], *, exact: bool = True
) -> list[Diagnostic]:
    if not isinstance(value, dict):
        return [Diagnostic("FAIL", "TYPE_OBJECT", path, "object required")]
    expected = set(keys)
    actual = set(value)
    issues = [
        Diagnostic("FAIL", "REQUIRED_KEY", path, f"missing {key}")
        for key in sorted(expected - actual)
    ]
    if exact:
        issues.extend(
            Diagnostic("FAIL", "UNDECLARED_KEY", path, f"unexpected {key}")
            for key in sorted(actual - expected)
        )
    return issues


def result_path_parts(value: Any) -> list[str] | None:
    if not isinstance(value, str) or not RESULT_PATH_RE.match(value):
        return None
    if "\\" in value or value.startswith(("/", "//")):
        return None
    if re.match(r"^[A-Za-z]:", value):
        return None
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return None
    pure = PurePosixPath(*parts)
    if pure.is_absolute() or ".." in pure.parts:
        return None
    if pure.parts[0] != "results":
        return None
    return list(pure.parts)


def is_safe_result_path(value: Any) -> bool:
    return result_path_parts(value) is not None


def is_junction(path: Path) -> bool:
    checker = getattr(os.path, "isjunction", None)
    if checker is None:
        return False
    return bool(checker(path))


def validate_result_target(root: Path, result_path: str, path: str) -> list[Diagnostic]:
    parts = result_path_parts(result_path)
    if parts is None:
        return [Diagnostic("FAIL", "RESULT_PATH", path, "unsafe or invalid result path")]

    cursor = root
    for part in parts:
        cursor = cursor / part
        try:
            if cursor.is_symlink():
                return [Diagnostic("FAIL", "RESULT_SYMLINK", path, result_path)]
            if is_junction(cursor):
                return [Diagnostic("FAIL", "RESULT_JUNCTION", path, result_path)]
        except OSError as exc:
            return [Diagnostic("ERROR", "RESULT_COMPONENT", path, str(exc))]

    candidate = root.joinpath(*parts)
    if not candidate.exists():
        return [Diagnostic("FAIL", "RESULT_MISSING", path, result_path)]
    try:
        root_resolved = root.resolve(strict=True)
    except OSError as exc:
        return [Diagnostic("ERROR", "ROOT_RESOLVE", path, str(exc))]
    try:
        candidate_resolved = candidate.resolve(strict=True)
    except OSError as exc:
        return [Diagnostic("ERROR", "RESULT_RESOLVE", path, str(exc))]
    try:
        candidate_resolved.relative_to(root_resolved)
    except ValueError:
        return [Diagnostic("FAIL", "RESULT_PATH_ESCAPE", path, result_path)]
    if not candidate.is_file():
        return [Diagnostic("FAIL", "RESULT_FILE_TYPE", path, result_path)]
    return []


def validate_human_gate(trace: dict[str, Any], path: str) -> list[Diagnostic]:
    issues: list[Diagnostic] = []
    gate = trace.get("human_gate")
    if not isinstance(gate, dict):
        return [Diagnostic("FAIL", "HUMAN_GATE_OBJECT", path, "human_gate object required")]
    issues.extend(
        require_keys(gate, f"{path}/human_gate", ["required", "level", "approval_state", "approved_scope"])
    )
    if issues:
        return issues
    required = gate["required"]
    level = gate["level"]
    state = gate["approval_state"]
    scope = gate["approved_scope"]
    status = trace.get("status")
    if not isinstance(required, bool):
        issues.append(Diagnostic("FAIL", "HUMAN_GATE_REQUIRED_TYPE", path, "required must be boolean"))
    if not isinstance(level, int) or isinstance(level, bool) or not 0 <= level <= 3:
        issues.append(Diagnostic("FAIL", "HUMAN_GATE_LEVEL", path, "level must be integer 0..3"))
    if state not in {"NOT_REQUIRED", "PENDING", "APPROVED", "REJECTED"}:
        issues.append(Diagnostic("FAIL", "HUMAN_GATE_STATE", path, "invalid approval_state"))
    if scope is not None and not (isinstance(scope, str) and scope.strip()):
        issues.append(Diagnostic("FAIL", "HUMAN_GATE_SCOPE", path, "approved_scope must be null or non-empty"))
    if issues:
        return issues
    if state == "NOT_REQUIRED":
        if required is not False or level != 0 or scope is not None or status not in {"PASS", "FAIL", "BLOCKED"}:
            issues.append(Diagnostic("FAIL", "HUMAN_GATE_STATUS", path, "NOT_REQUIRED matrix violation"))
    elif state == "PENDING":
        if required is not True or level not in {1, 2, 3} or scope is not None or status != "HUMAN_APPROVAL_REQUIRED":
            issues.append(Diagnostic("FAIL", "HUMAN_GATE_STATUS", path, "PENDING matrix violation"))
    elif state == "APPROVED":
        if required is not True or level not in {1, 2, 3} or not isinstance(scope, str) or not scope.strip() or status not in {"PASS", "FAIL", "BLOCKED"}:
            issues.append(Diagnostic("FAIL", "HUMAN_GATE_STATUS", path, "APPROVED matrix violation"))
    elif state == "REJECTED":
        if required is not True or level not in {1, 2, 3} or scope is not None or status != "BLOCKED":
            issues.append(Diagnostic("FAIL", "HUMAN_GATE_STATUS", path, "REJECTED matrix violation"))
    return issues


def validate_routing_trace_shape(value: Any, path: str) -> list[Diagnostic]:
    required = [
        "schema_version",
        "simulation_id",
        "status",
        "command",
        "constitution",
        "policies",
        "workflow",
        "primary_agent",
        "supporting_agents",
        "skills",
        "audit_before_edit",
        "human_gate",
        "stop_condition",
        "expected_artifact",
    ]
    issues = require_keys(value, path, required)
    if issues:
        return issues
    assert isinstance(value, dict)
    if value["schema_version"] != SCHEMA_VERSION:
        issues.append(Diagnostic("FAIL", "SCHEMA_VERSION", path, "routing trace schema_version must be 1.0.0"))
    if value["simulation_id"] not in SUPPORTED_SCENARIOS:
        issues.append(Diagnostic("FAIL", "SIMULATION_ID", path, "unsupported simulation_id"))
    if value["status"] not in ROUTING_STATUSES:
        issues.append(Diagnostic("FAIL", "STATUS", path, "unsupported status"))
    for key in ["command", "constitution", "workflow", "primary_agent", "audit_before_edit", "stop_condition", "expected_artifact"]:
        if not isinstance(value[key], str) or not value[key]:
            issues.append(Diagnostic("FAIL", "NONEMPTY_STRING", f"{path}/{key}", "non-empty string required"))
    for key in ["policies", "skills"]:
        items = value[key]
        if not isinstance(items, list) or not items:
            issues.append(Diagnostic("FAIL", "NONEMPTY_ARRAY", f"{path}/{key}", "non-empty array required"))
        elif any(not isinstance(item, str) or not item for item in items):
            issues.append(Diagnostic("FAIL", "NONEMPTY_STRING_ARRAY", f"{path}/{key}", "all items must be non-empty strings"))
        elif len(set(items)) != len(items):
            issues.append(Diagnostic("FAIL", "UNIQUE_ARRAY", f"{path}/{key}", "items must be unique"))
    supporting = value["supporting_agents"]
    if not isinstance(supporting, list):
        issues.append(Diagnostic("FAIL", "ARRAY", f"{path}/supporting_agents", "array required"))
    elif any(not isinstance(item, str) or not item for item in supporting):
        issues.append(Diagnostic("FAIL", "NONEMPTY_STRING_ARRAY", f"{path}/supporting_agents", "all items must be non-empty strings"))
    elif len(set(supporting)) != len(supporting):
        issues.append(Diagnostic("FAIL", "UNIQUE_ARRAY", f"{path}/supporting_agents", "items must be unique"))
    issues.extend(validate_human_gate(value, path))
    return issues


def validate_artifact_shape(artifact: Any, scenario: str, path: str, *, manifest_key: str) -> list[Diagnostic]:
    issues = require_keys(artifact, path, ["evidence_id", manifest_key, "sha256"])
    if issues:
        return issues
    assert isinstance(artifact, dict)
    evidence_id = artifact["evidence_id"]
    result_path = artifact[manifest_key]
    sha256 = artifact["sha256"]
    if not isinstance(evidence_id, str) or not EVIDENCE_ID_RE.match(evidence_id):
        issues.append(Diagnostic("FAIL", "EVIDENCE_ID", path, "invalid evidence_id"))
    elif not evidence_id.startswith(f"{scenario}:"):
        issues.append(Diagnostic("FAIL", "SCENARIO_PREFIX", path, "evidence_id scenario mismatch"))
    if not is_safe_result_path(result_path):
        issues.append(Diagnostic("FAIL", "RESULT_PATH", path, "unsafe or invalid result path"))
    elif not result_path.startswith(f"results/{scenario}-"):
        issues.append(Diagnostic("FAIL", "SCENARIO_PREFIX", path, "result path scenario mismatch"))
    if not isinstance(sha256, str) or not SHA256_RE.match(sha256):
        issues.append(Diagnostic("FAIL", "SHA256", path, "invalid sha256"))
    return issues


def validate_result_artifact_shape(artifact: Any, scenario: str, path: str) -> list[Diagnostic]:
    issues = require_keys(artifact, path, ["path", "sha256"])
    if issues:
        return issues
    assert isinstance(artifact, dict)
    result_path = artifact["path"]
    sha256 = artifact["sha256"]
    if not is_safe_result_path(result_path):
        issues.append(Diagnostic("FAIL", "RESULT_PATH", path, "unsafe or invalid result path"))
    elif not result_path.startswith(f"results/{scenario}-"):
        issues.append(Diagnostic("FAIL", "SCENARIO_PREFIX", path, "result path scenario mismatch"))
    if not isinstance(sha256, str) or not SHA256_RE.match(sha256):
        issues.append(Diagnostic("FAIL", "SHA256", path, "invalid sha256"))
    return issues

def validate_payload_shape(value: Any, path: str) -> list[Diagnostic]:
    issues = require_keys(
        value,
        path,
        ["schema_version", "evidence_id", "scenario_id", "result_artifact", "routing_trace", "provenance"],
    )
    if issues:
        return issues
    assert isinstance(value, dict)
    scenario = value["scenario_id"]
    if value["schema_version"] != SCHEMA_VERSION:
        issues.append(Diagnostic("FAIL", "SCHEMA_VERSION", path, "payload schema_version must be 1.0.0"))
    if scenario not in SUPPORTED_SCENARIOS:
        issues.append(Diagnostic("FAIL", "SCENARIO_ID", path, "unsupported scenario_id"))
        scenario = "SIM-000"
    issues.extend(validate_result_artifact_shape(value["result_artifact"], scenario, f"{path}/result_artifact"))
    issues.extend(validate_routing_trace_shape(value["routing_trace"], f"{path}/routing_trace"))
    provenance = value["provenance"]
    issues.extend(require_keys(provenance, f"{path}/provenance", ["consumer_revision", "hub_pin", "schema_versions"]))
    if isinstance(provenance, dict):
        if not isinstance(provenance.get("consumer_revision"), str) or not HEX40_RE.match(provenance["consumer_revision"]):
            issues.append(Diagnostic("FAIL", "CONSUMER_REVISION", path, "invalid consumer_revision"))
        if not isinstance(provenance.get("hub_pin"), str) or not HEX40_RE.match(provenance["hub_pin"]):
            issues.append(Diagnostic("FAIL", "HUB_PIN", path, "invalid hub_pin"))
        versions = provenance.get("schema_versions")
        issues.extend(require_keys(versions, f"{path}/provenance/schema_versions", ["payload", "routing_trace"]))
        if isinstance(versions, dict):
            for key in ["payload", "routing_trace"]:
                if versions.get(key) != SCHEMA_VERSION:
                    issues.append(Diagnostic("FAIL", "SCHEMA_VERSION", f"{path}/provenance/schema_versions/{key}", "must be 1.0.0"))
    if isinstance(value.get("routing_trace"), dict) and scenario in SUPPORTED_SCENARIOS:
        if value["routing_trace"].get("simulation_id") != scenario:
            issues.append(Diagnostic("FAIL", "PAYLOAD_TRACE_ALIGNMENT", path, "scenario_id must match routing_trace.simulation_id"))
    return issues


def validate_manifest_shape(value: Any, path: str) -> list[Diagnostic]:
    issues = require_keys(value, path, ["schema_version", "manifest_id", "provenance", "scenarios"])
    if issues:
        return issues
    assert isinstance(value, dict)
    if value["schema_version"] != SCHEMA_VERSION:
        issues.append(Diagnostic("FAIL", "SCHEMA_VERSION", path, "manifest schema_version must be 1.0.0"))
    if not isinstance(value["manifest_id"], str) or not MANIFEST_ID_RE.match(value["manifest_id"]):
        issues.append(Diagnostic("FAIL", "MANIFEST_ID", path, "invalid manifest_id"))
    provenance = value["provenance"]
    issues.extend(require_keys(provenance, f"{path}/provenance", ["consumer_revision", "hub_pin", "schema_versions"]))
    if isinstance(provenance, dict):
        if not isinstance(provenance.get("consumer_revision"), str) or not HEX40_RE.match(provenance["consumer_revision"]):
            issues.append(Diagnostic("FAIL", "CONSUMER_REVISION", path, "invalid consumer_revision"))
        if not isinstance(provenance.get("hub_pin"), str) or not HEX40_RE.match(provenance["hub_pin"]):
            issues.append(Diagnostic("FAIL", "HUB_PIN", path, "invalid hub_pin"))
        versions = provenance.get("schema_versions")
        issues.extend(require_keys(versions, f"{path}/provenance/schema_versions", ["payload", "routing_trace", "manifest"]))
        if isinstance(versions, dict):
            for key in ["payload", "routing_trace", "manifest"]:
                if versions.get(key) != SCHEMA_VERSION:
                    issues.append(Diagnostic("FAIL", "SCHEMA_VERSION", f"{path}/provenance/schema_versions/{key}", "must be 1.0.0"))
    scenarios = value["scenarios"]
    issues.extend(require_keys(scenarios, f"{path}/scenarios", SUPPORTED_SCENARIOS))
    if not isinstance(scenarios, dict):
        return issues
    for scenario in SUPPORTED_SCENARIOS:
        entry = scenarios.get(scenario)
        entry_path = f"{path}/scenarios/{scenario}"
        issues.extend(require_keys(entry, entry_path, ["scenario_id", "canonical", "historical_attempts"]))
        if not isinstance(entry, dict):
            continue
        if entry.get("scenario_id") != scenario:
            issues.append(Diagnostic("FAIL", "SCENARIO_ID", entry_path, "scenario_id does not match key"))
        canonical = entry.get("canonical")
        if canonical is not None:
            issues.extend(validate_artifact_shape(canonical, scenario, f"{entry_path}/canonical", manifest_key="result_path"))
        historical = entry.get("historical_attempts")
        if not isinstance(historical, list):
            issues.append(Diagnostic("FAIL", "HISTORICAL_ARRAY", entry_path, "historical_attempts must be array"))
        else:
            seen_exact: set[str] = set()
            for index, artifact in enumerate(historical):
                artifact_path = f"{entry_path}/historical_attempts/{index}"
                issues.extend(validate_artifact_shape(artifact, scenario, artifact_path, manifest_key="result_path"))
                serialized = json.dumps(artifact, sort_keys=True, separators=(",", ":"))
                if serialized in seen_exact:
                    issues.append(Diagnostic("FAIL", "HISTORICAL_DUPLICATE_OBJECT", artifact_path, "duplicate historical descriptor"))
                seen_exact.add(serialized)
    return issues


def artifact_records(manifest: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    records: list[tuple[str, str, dict[str, Any]]] = []
    scenarios = manifest.get("scenarios", {})
    if not isinstance(scenarios, dict):
        return records
    for scenario in sorted(scenarios):
        entry = scenarios.get(scenario)
        if not isinstance(entry, dict):
            continue
        canonical = entry.get("canonical")
        if isinstance(canonical, dict):
            records.append((scenario, f"{scenario}/canonical", canonical))
        historical = entry.get("historical_attempts")
        if isinstance(historical, list):
            for index, artifact in enumerate(historical):
                if isinstance(artifact, dict):
                    records.append((scenario, f"{scenario}/historical_attempts/{index}", artifact))
    return records


def validate_manifest_semantics(
    root: Path, manifest: dict[str, Any], path: str, *, check_files: bool
) -> list[Diagnostic]:
    issues: list[Diagnostic] = []
    records = artifact_records(manifest)
    seen_evidence: dict[str, str] = {}
    seen_paths: dict[str, str] = {}
    for _scenario, location, artifact in records:
        evidence_id = artifact.get("evidence_id")
        result_path = artifact.get("result_path")
        if isinstance(evidence_id, str):
            if evidence_id in seen_evidence:
                issues.append(Diagnostic("FAIL", "MANIFEST_DUPLICATE_EVIDENCE_ID", f"{path}/{location}", evidence_id))
            else:
                seen_evidence[evidence_id] = location
        if isinstance(result_path, str):
            if result_path in seen_paths:
                issues.append(Diagnostic("FAIL", "MANIFEST_DUPLICATE_RESULT_PATH", f"{path}/{location}", result_path))
            else:
                seen_paths[result_path] = location
    scenarios = manifest.get("scenarios", {})
    if isinstance(scenarios, dict):
        for scenario in sorted(scenarios):
            entry = scenarios.get(scenario)
            if not isinstance(entry, dict):
                continue
            canonical = entry.get("canonical")
            historical = entry.get("historical_attempts")
            if isinstance(canonical, dict) and isinstance(historical, list):
                canonical_serialized = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
                for index, artifact in enumerate(historical):
                    if isinstance(artifact, dict) and json.dumps(artifact, sort_keys=True, separators=(",", ":")) == canonical_serialized:
                        issues.append(Diagnostic("FAIL", "MANIFEST_CANONICAL_IN_HISTORY", f"{path}/{scenario}/historical_attempts/{index}", "canonical descriptor repeated in history"))
    if check_files:
        for _scenario, location, artifact in records:
            result_path = artifact.get("result_path")
            expected_hash = artifact.get("sha256")
            if not isinstance(result_path, str) or not is_safe_result_path(result_path):
                continue
            target_issues = validate_result_target(root, result_path, f"{path}/{location}")
            if target_issues:
                issues.extend(target_issues)
                continue
            relative = Path(*PurePosixPath(result_path).parts)
            byte_issues = [issue for issue in validate_bytes(root, relative) if issue.severity != "PASS"]
            issues.extend(byte_issues)
            digest = hashlib.sha256((root / relative).read_bytes()).hexdigest()
            if digest != expected_hash:
                issues.append(Diagnostic("FAIL", "RESULT_SHA256", f"{path}/{location}", result_path))
    if not issues:
        issues.append(Diagnostic("PASS", "MANIFEST_SEMANTICS", path, "selection only; semantic invariants pass"))
    return issues


def validate_schema_metadata(root: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for filename, schema_id in sorted(SCHEMA_IDS.items()):
        relative_path = CONTRACT_ROOT / filename
        schema, load_diags = load_json_no_duplicates(root, relative_path)
        diagnostics.extend(load_diags)
        path = relative_path.as_posix()
        if schema is None:
            continue
        issues = require_keys(schema, path, ["$schema", "$id", "title", "description", "type", "required", "properties"], exact=False)
        if schema.get("$id") != schema_id:
            issues.append(Diagnostic("FAIL", "SCHEMA_ID", path, f"expected {schema_id}"))
        if schema.get("$schema") != DRAFT_2020_12_URI:
            issues.append(Diagnostic("FAIL", "SCHEMA_DRAFT", path, "expected Draft 2020-12"))
        if schema.get("type") != "object":
            issues.append(Diagnostic("FAIL", "SCHEMA_ROOT_TYPE", path, "root type must be object"))
        if schema.get("additionalProperties") is not False:
            issues.append(Diagnostic("FAIL", "SCHEMA_CLOSED", path, "additionalProperties must be false"))
        diagnostics.extend(issues or [Diagnostic("PASS", "SCHEMA_METADATA", path, "required id/version boundary present")])
    return diagnostics


def validate_json_file_by_kind(root: Path, relative_path: Path, *, check_files: bool) -> list[Diagnostic]:
    data, diagnostics = load_json_no_duplicates(root, relative_path)
    if data is None:
        return diagnostics
    path = relative_path.as_posix()
    if relative_path.name == "manifest.schema.json":
        return diagnostics
    if relative_path.name == "payload.schema.json":
        return diagnostics
    if relative_path.name == "routing-trace.schema.json":
        return diagnostics
    if relative_path.name == "payload.json" or "payload-" in relative_path.name:
        issues = validate_payload_shape(data, path)
    elif relative_path.name.startswith("routing-trace"):
        issues = validate_routing_trace_shape(data, path)
    else:
        issues = validate_manifest_shape(data, path)
        if not issues:
            issues.extend(validate_manifest_semantics(root, data, path, check_files=check_files))
    return diagnostics + (issues or [Diagnostic("PASS", "STRUCTURE", path, "structure checks pass")])


def validate_current_manifest(root: Path) -> list[Diagnostic]:
    manifest, diagnostics = load_json_no_duplicates(root, MANIFEST_PATH)
    if manifest is None:
        return diagnostics
    issues = validate_manifest_shape(manifest, MANIFEST_PATH.as_posix())
    if not issues:
        issues.extend(validate_manifest_semantics(root, manifest, MANIFEST_PATH.as_posix(), check_files=True))
    return diagnostics + (issues or [Diagnostic("PASS", "MANIFEST", MANIFEST_PATH.as_posix(), "current manifest passes")])


def validate_examples(root: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    valid_dir = root / CONTRACT_ROOT / "examples" / "valid"
    invalid_dir = root / CONTRACT_ROOT / "examples" / "invalid"
    semantic_dir = root / CONTRACT_ROOT / "examples" / "semantic-invalid"
    for directory in [valid_dir, invalid_dir, semantic_dir]:
        if not directory.is_dir():
            diagnostics.append(Diagnostic("FAIL", "EXAMPLE_DIR", display_path(root, directory), "directory missing"))
            return diagnostics
    for path in sorted(valid_dir.glob("*.json")):
        relative = path.relative_to(root)
        issues = [issue for issue in validate_json_file_by_kind(root, relative, check_files=False) if issue.severity == "FAIL"]
        if issues:
            diagnostics.extend(issues)
        else:
            diagnostics.append(Diagnostic("PASS", "EXAMPLE_VALID", relative.as_posix(), "accepted by foundation checks"))
    for path in sorted(invalid_dir.glob("*.json")):
        relative = path.relative_to(root)
        issues = [issue for issue in validate_json_file_by_kind(root, relative, check_files=False) if issue.severity == "FAIL"]
        if issues:
            diagnostics.append(Diagnostic("PASS", "EXAMPLE_FOUNDATION_REJECTED", relative.as_posix(), issues[0].code))
        else:
            diagnostics.append(Diagnostic("FAIL", "EXAMPLE_FOUNDATION_REJECTED", relative.as_posix(), "fixture was accepted by foundation checks"))
    for path in sorted(semantic_dir.glob("*.json")):
        relative = path.relative_to(root)
        parsed, load_diags = load_json_no_duplicates(root, relative)
        failures = [issue for issue in load_diags if issue.severity == "FAIL"]
        if failures or parsed is None:
            diagnostics.extend(failures)
            continue
        shape_issues = validate_manifest_shape(parsed, relative.as_posix())
        semantic_issues = [
            issue
            for issue in validate_manifest_semantics(root, parsed, relative.as_posix(), check_files=False)
            if issue.severity == "FAIL"
        ]
        if shape_issues:
            diagnostics.extend(shape_issues)
        elif semantic_issues:
            diagnostics.append(
                Diagnostic(
                    "PASS",
                    "EXAMPLE_SEMANTIC_REJECTED",
                    relative.as_posix(),
                    prioritized_semantic_code(semantic_issues),
                )
            )
        else:
            diagnostics.append(Diagnostic("FAIL", "EXAMPLE_SEMANTIC_REJECTED", relative.as_posix(), "fixture was accepted by semantic checks"))
    return diagnostics


def prioritized_semantic_code(issues: list[Diagnostic]) -> str:
    priority = [
        "MANIFEST_CANONICAL_IN_HISTORY",
        "MANIFEST_DUPLICATE_EVIDENCE_ID",
        "MANIFEST_DUPLICATE_RESULT_PATH",
    ]
    codes = {issue.code for issue in issues}
    for code in priority:
        if code in codes:
            return code
    return sorted(codes)[0]


def validate(root: Path) -> tuple[list[Diagnostic], bool]:
    if not root.exists() or not root.is_dir():
        return [Diagnostic("ERROR", "ROOT", root.as_posix(), "root directory missing")], True
    diagnostics: list[Diagnostic] = []
    required_paths = [
        CONTRACT_ROOT / "payload.schema.json",
        CONTRACT_ROOT / "routing-trace.schema.json",
        CONTRACT_ROOT / "manifest.schema.json",
        MANIFEST_PATH,
    ]
    for relative_path in required_paths:
        if not (root / relative_path).is_file():
            diagnostics.append(Diagnostic("FAIL", "REQUIRED_FILE", relative_path.as_posix(), "file missing"))
    if any(diag.code == "REQUIRED_FILE" for diag in diagnostics):
        return diagnostics, False
    diagnostics.extend(validate_schema_metadata(root))
    diagnostics.extend(validate_current_manifest(root))
    diagnostics.extend(validate_examples(root))
    diagnostics.append(
        Diagnostic(
            "INFO",
            "JSON_SCHEMA_ENGINE_DEFERRED",
            ".",
            "Ajv remains authoritative for Draft 2020-12 schema-valid/schema-invalid expectations",
        )
    )
    failed_operationally = any(diag.severity == "ERROR" for diag in diagnostics)
    return sorted(diagnostics), failed_operationally


def main() -> int:
    root = Path(parse_args().root).resolve()
    diagnostics, operational_error = validate(root)
    has_validation_failure = any(diag.severity == "FAIL" for diag in diagnostics)
    for diagnostic in diagnostics:
        print(diagnostic.render())
    if operational_error:
        return EXIT_OPERATIONAL_ERROR
    if has_validation_failure:
        return EXIT_VALIDATION_FAILURE
    print("PASS SANDBOX_VALIDATION . read-only foundation checks passed")
    return EXIT_PASSED


if __name__ == "__main__":
    sys.exit(main())
