#!/usr/bin/env python3
"""Read-only Stage 7 sandbox validation foundation."""

from __future__ import annotations

import argparse
import codecs
from dataclasses import dataclass
from datetime import datetime
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
EXECUTION_CONTRACT_ROOT = Path("contracts/execution/v1")
EXECUTION_CONTRACT_ROOT_V2 = Path("contracts/execution/v2")
MANIFEST_PATH = Path("evidence/manifest.v1.json")
RUN_RECORDS_ROOT = Path("evidence/runs")
RUN_RECORD_FILENAMES = {"run-record.v1.json", "run-record.v2.json"}
SUPPORTED_SCENARIOS = tuple(f"SIM-00{index}" for index in range(1, 7))
SCHEMA_VERSION = "1.0.0"
RUN_RECORD_SCHEMA_VERSION_V2 = "2.0.0"
DRAFT_2020_12_URI = "https" + "://json-schema.org/draft/2020-12/schema"
SCHEMA_IDS = {
    CONTRACT_ROOT / "payload.schema.json": "urn:qa-orchestration-sandbox:evidence:v1:payload",
    CONTRACT_ROOT / "routing-trace.schema.json": "urn:qa-orchestration-sandbox:evidence:v1:routing-trace",
    CONTRACT_ROOT / "manifest.schema.json": "urn:qa-orchestration-sandbox:evidence:v1:manifest",
    EXECUTION_CONTRACT_ROOT / "run-record.schema.json": "urn:qa-orchestration-sandbox:execution:v1:run-record",
    EXECUTION_CONTRACT_ROOT_V2 / "run-record.schema.json": "urn:qa-orchestration-sandbox:execution:v2:run-record",
}
SCENARIO_PATH_RE = re.compile(r"^scenarios/SIM-00[1-6]-[A-Za-z0-9._/-]+\.md$")
FIXTURE_PATH_RE = re.compile(r"^fixtures/[A-Za-z0-9._/-]+$")
ORACLE_PATH_RE = re.compile(r"^expected/SIM-00[1-6]-[A-Za-z0-9._/-]+\.md$")
PAYLOAD_PATH_RE = re.compile(
    r"^evidence/runs/SIM-00[1-6]/S7-SIM-00[1-6]-(P1|P2|IR)-R[0-9]{2}\.payload\.json$"
)
RESULT_PATH_RE = re.compile(r"^results/SIM-00[1-6]-[A-Za-z0-9._/-]+\.md$")
EVIDENCE_ID_RE = re.compile(r"^SIM-00[1-6]:[a-z0-9][a-z0-9._-]*:v1$")
RUN_ID_RE = re.compile(r"^S7-(SIM-00[1-6])-(P1|P2|IR)-R([0-9]{2})$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
MANIFEST_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]*:v1$")
HEX40_RE = re.compile(r"^[a-f0-9]{40}$")
ROUTING_STATUSES = {"PASS", "FAIL", "BLOCKED", "HUMAN_APPROVAL_REQUIRED"}
EXECUTION_ROLES = {"PRIMARY", "INDEPENDENT_REPRODUCTION"}
C1_C10 = tuple(f"C{index}" for index in range(1, 11))
CRITERION_NAMES = {
    "C1": "Command",
    "C2": "Constitution",
    "C3": "Policies",
    "C4": "Workflow",
    "C5": "Primary agent",
    "C6": "Skills",
    "C7": "Audit decision",
    "C8": "Human Gate decision",
    "C9": "Output and trace",
    "C10": "Safety",
}


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
        description="Validate evidence and run-record contract foundation invariants."
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


def repository_path_parts(value: Any) -> list[str] | None:
    if not isinstance(value, str):
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
    return list(pure.parts)


def is_safe_repository_path(value: Any) -> bool:
    return repository_path_parts(value) is not None


def path_matches(value: Any, pattern: re.Pattern[str]) -> bool:
    return isinstance(value, str) and pattern.match(value) is not None and is_safe_repository_path(value)


def parse_utc_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$", value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def validate_reference_target(root: Path, relative_path: str, path: str) -> list[Diagnostic]:
    parts = repository_path_parts(relative_path)
    if parts is None:
        return [Diagnostic("FAIL", "REFERENCE_PATH", path, "unsafe reference path")]

    cursor = root
    for part in parts:
        cursor = cursor / part
        try:
            if cursor.is_symlink():
                return [Diagnostic("FAIL", "REFERENCE_SYMLINK", path, relative_path)]
            if is_junction(cursor):
                return [Diagnostic("FAIL", "REFERENCE_JUNCTION", path, relative_path)]
        except OSError as exc:
            return [Diagnostic("ERROR", "REFERENCE_COMPONENT", path, str(exc))]

    candidate = root.joinpath(*parts)
    if not candidate.exists():
        return [Diagnostic("FAIL", "REFERENCE_MISSING", path, relative_path)]
    try:
        root_resolved = root.resolve(strict=True)
        candidate_resolved = candidate.resolve(strict=True)
    except OSError as exc:
        return [Diagnostic("ERROR", "REFERENCE_RESOLVE", path, str(exc))]
    try:
        candidate_resolved.relative_to(root_resolved)
    except ValueError:
        return [Diagnostic("FAIL", "REFERENCE_PATH_ESCAPE", path, relative_path)]
    if not candidate.is_file():
        return [Diagnostic("FAIL", "REFERENCE_FILE_TYPE", path, relative_path)]
    return []


def validate_reference_hash(root: Path, relative_path: str, expected_hash: str, path: str) -> list[Diagnostic]:
    issues = validate_reference_target(root, relative_path, path)
    if issues:
        return issues
    parts = repository_path_parts(relative_path)
    assert parts is not None
    digest = hashlib.sha256(root.joinpath(*parts).read_bytes()).hexdigest()
    if digest != expected_hash:
        return [Diagnostic("FAIL", "REFERENCE_SHA256", path, relative_path)]
    return []

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


def validate_named_string_object(value: Any, path: str, keys: Iterable[str]) -> list[Diagnostic]:
    issues = require_keys(value, path, keys)
    if issues:
        return issues
    assert isinstance(value, dict)
    for key in keys:
        if not isinstance(value[key], str) or not value[key]:
            issues.append(Diagnostic("FAIL", "NONEMPTY_STRING", f"{path}/{key}", "non-empty string required"))
    return issues


def validate_run_record_hashed_file(
    value: Any,
    path: str,
    pattern: re.Pattern[str],
    scenario: str | None,
    scenario_prefix: str | None,
) -> list[Diagnostic]:
    issues = require_keys(value, path, ["path", "sha256"])
    if issues:
        return issues
    assert isinstance(value, dict)
    file_path = value["path"]
    if not path_matches(file_path, pattern):
        issues.append(Diagnostic("FAIL", "RUN_RECORD_PATH", path, "unsafe or invalid path"))
    elif scenario is not None and scenario_prefix is not None and not file_path.startswith(scenario_prefix):
        issues.append(Diagnostic("FAIL", "RUN_RECORD_SCENARIO_ALIGNMENT", path, "path scenario mismatch"))
    if not isinstance(value["sha256"], str) or not SHA256_RE.match(value["sha256"]):
        issues.append(Diagnostic("FAIL", "SHA256", path, "invalid sha256"))
    return issues


def validate_run_record_v1_shape(value: Any, path: str) -> list[Diagnostic]:
    required = [
        "schema_version",
        "run_id",
        "cohort_id",
        "scenario_id",
        "execution_role",
        "attempt_number",
        "executor_id",
        "started_at",
        "completed_at",
        "model_id",
        "execution_surface",
        "environment",
        "runtime_versions",
        "provenance",
        "inputs",
        "artifacts",
    ]
    issues = require_keys(value, path, required)
    if issues:
        return issues
    assert isinstance(value, dict)
    if value["schema_version"] != SCHEMA_VERSION:
        issues.append(Diagnostic("FAIL", "SCHEMA_VERSION", path, "run record schema_version must be 1.0.0"))
    run_match = RUN_ID_RE.match(value["run_id"]) if isinstance(value["run_id"], str) else None
    if run_match is None:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_RUN_ID", path, "invalid run_id"))
        run_scenario = None
    else:
        run_scenario = run_match.group(1)
    scenario = value["scenario_id"]
    if scenario not in SUPPORTED_SCENARIOS:
        issues.append(Diagnostic("FAIL", "SCENARIO_ID", path, "unsupported scenario_id"))
        scenario = None
    if run_scenario is not None and scenario is not None and run_scenario != scenario:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_SCENARIO_ALIGNMENT", path, "run_id scenario mismatch"))
    if value["cohort_id"] not in {"P1", "P2", "IR"}:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_COHORT", path, "invalid cohort_id"))
    if value["execution_role"] not in EXECUTION_ROLES:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_ROLE", path, "invalid execution_role"))
    if not isinstance(value["attempt_number"], int) or isinstance(value["attempt_number"], bool) or not 1 <= value["attempt_number"] <= 99:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_ATTEMPT", path, "attempt_number must be integer 1..99"))
    if not isinstance(value["executor_id"], str) or not re.match(r"^synthetic-executor-[a-z0-9][a-z0-9-]{2,63}$", value["executor_id"]):
        issues.append(Diagnostic("FAIL", "RUN_RECORD_EXECUTOR", path, "invalid executor_id"))
    if parse_utc_timestamp(value["started_at"]) is None:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_TIMESTAMP", f"{path}/started_at", "invalid UTC timestamp"))
    if parse_utc_timestamp(value["completed_at"]) is None:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_TIMESTAMP", f"{path}/completed_at", "invalid UTC timestamp"))
    if not isinstance(value["model_id"], str) or not value["model_id"]:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_MODEL", path, "model_id required"))

    issues.extend(validate_named_string_object(value["execution_surface"], f"{path}/execution_surface", ["name", "version"]))
    environment = value["environment"]
    env_issues = require_keys(environment, f"{path}/environment", ["os", "architecture"])
    issues.extend(env_issues)
    if isinstance(environment, dict) and not env_issues:
        issues.extend(validate_named_string_object(environment["os"], f"{path}/environment/os", ["name", "version"]))
        if environment["architecture"] not in {"x64", "arm64"}:
            issues.append(Diagnostic("FAIL", "RUN_RECORD_ARCHITECTURE", f"{path}/environment", "invalid architecture"))
    issues.extend(
        validate_named_string_object(
            value["runtime_versions"],
            f"{path}/runtime_versions",
            ["python", "git", "node", "npm", "npx", "ajv_cli", "sandbox_validator"],
        )
    )

    provenance = value["provenance"]
    provenance_issues = require_keys(provenance, f"{path}/provenance", ["consumer_execution_input", "hub_pin", "schema_versions"])
    issues.extend(provenance_issues)
    if isinstance(provenance, dict) and not provenance_issues:
        if not isinstance(provenance["consumer_execution_input"], str) or not HEX40_RE.match(provenance["consumer_execution_input"]):
            issues.append(Diagnostic("FAIL", "CONSUMER_REVISION", path, "invalid consumer_execution_input"))
        if not isinstance(provenance["hub_pin"], str) or not HEX40_RE.match(provenance["hub_pin"]):
            issues.append(Diagnostic("FAIL", "HUB_PIN", path, "invalid hub_pin"))
        versions = provenance["schema_versions"]
        version_issues = require_keys(versions, f"{path}/provenance/schema_versions", ["payload", "routing_trace", "run_record"])
        issues.extend(version_issues)
        if isinstance(versions, dict) and not version_issues:
            for key in ["payload", "routing_trace", "run_record"]:
                if versions[key] != SCHEMA_VERSION:
                    issues.append(Diagnostic("FAIL", "SCHEMA_VERSION", f"{path}/provenance/schema_versions/{key}", "must be 1.0.0"))

    inputs = value["inputs"]
    input_issues = require_keys(inputs, f"{path}/inputs", ["scenario", "fixtures", "oracle"])
    issues.extend(input_issues)
    if isinstance(inputs, dict) and not input_issues:
        issues.extend(validate_run_record_hashed_file(inputs["scenario"], f"{path}/inputs/scenario", SCENARIO_PATH_RE, scenario, None if scenario is None else f"scenarios/{scenario}-"))
        fixtures = inputs["fixtures"]
        if not isinstance(fixtures, list):
            issues.append(Diagnostic("FAIL", "RUN_RECORD_FIXTURES", f"{path}/inputs/fixtures", "fixtures must be array"))
        else:
            for index, fixture in enumerate(fixtures):
                issues.extend(validate_run_record_hashed_file(fixture, f"{path}/inputs/fixtures/{index}", FIXTURE_PATH_RE, None, None))
        issues.extend(validate_run_record_hashed_file(inputs["oracle"], f"{path}/inputs/oracle", ORACLE_PATH_RE, scenario, None if scenario is None else f"expected/{scenario}-"))

    artifacts = value["artifacts"]
    artifact_issues = require_keys(artifacts, f"{path}/artifacts", ["payload", "result"])
    issues.extend(artifact_issues)
    if isinstance(artifacts, dict) and not artifact_issues:
        payload = artifacts["payload"]
        payload_issues = require_keys(payload, f"{path}/artifacts/payload", ["path", "sha256", "evidence_id"])
        issues.extend(payload_issues)
        if isinstance(payload, dict) and not payload_issues:
            if not path_matches(payload["path"], PAYLOAD_PATH_RE):
                issues.append(Diagnostic("FAIL", "RUN_RECORD_PATH", f"{path}/artifacts/payload", "unsafe or invalid payload path"))
            elif scenario is not None and not payload["path"].startswith(f"evidence/runs/{scenario}/S7-{scenario}-"):
                issues.append(Diagnostic("FAIL", "RUN_RECORD_SCENARIO_ALIGNMENT", f"{path}/artifacts/payload", "payload path scenario mismatch"))
            if not isinstance(payload["sha256"], str) or not SHA256_RE.match(payload["sha256"]):
                issues.append(Diagnostic("FAIL", "SHA256", f"{path}/artifacts/payload", "invalid sha256"))
            if not isinstance(payload["evidence_id"], str) or not EVIDENCE_ID_RE.match(payload["evidence_id"]):
                issues.append(Diagnostic("FAIL", "EVIDENCE_ID", f"{path}/artifacts/payload", "invalid evidence_id"))
            elif scenario is not None and not payload["evidence_id"].startswith(f"{scenario}:"):
                issues.append(Diagnostic("FAIL", "RUN_RECORD_SCENARIO_ALIGNMENT", f"{path}/artifacts/payload", "evidence_id scenario mismatch"))
        issues.extend(validate_run_record_hashed_file(artifacts["result"], f"{path}/artifacts/result", RESULT_PATH_RE, scenario, None if scenario is None else f"results/{scenario}-"))
    return issues


def validate_run_record_version(value: Any) -> str | None:
    return value.get("schema_version") if isinstance(value, dict) and isinstance(value.get("schema_version"), str) else None


def validate_execution_surface_v2(value: Any, path: str) -> list[Diagnostic]:
    issues = require_keys(value, path, ["name", "version"])
    if issues:
        return issues
    assert isinstance(value, dict)
    if not isinstance(value["name"], str) or not value["name"]:
        issues.append(Diagnostic("FAIL", "NONEMPTY_STRING", f"{path}/name", "non-empty string required"))
    version = value["version"]
    if not isinstance(version, dict):
        issues.append(Diagnostic("FAIL", "RUN_RECORD_SURFACE_VERSION", f"{path}/version", "structured version availability required"))
        return issues
    availability = version.get("availability")
    if availability == "EXACT":
        version_issues = require_keys(version, f"{path}/version", ["availability", "value"])
        issues.extend(version_issues)
        if not version_issues and (not isinstance(version.get("value"), str) or not version["value"]):
            issues.append(Diagnostic("FAIL", "RUN_RECORD_SURFACE_VERSION", f"{path}/version/value", "exact version value required"))
    elif availability == "UNAVAILABLE":
        version_issues = require_keys(version, f"{path}/version", ["availability", "reason"])
        issues.extend(version_issues)
        if not version_issues and (not isinstance(version.get("reason"), str) or not version["reason"]):
            issues.append(Diagnostic("FAIL", "RUN_RECORD_SURFACE_VERSION", f"{path}/version/reason", "unavailable reason required"))
    else:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_SURFACE_VERSION", f"{path}/version", "availability must be EXACT or UNAVAILABLE"))
    return issues


def validate_run_record_evaluation_shape(value: Any, path: str) -> list[Diagnostic]:
    required = [
        "criteria",
        "total_score",
        "result",
        "oracle",
        "evaluator_id",
        "method",
        "validator_result",
        "run_acceptance",
        "reproducibility",
    ]
    issues = require_keys(value, path, required)
    if issues:
        return issues
    assert isinstance(value, dict)
    criteria = value["criteria"]
    criteria_issues = require_keys(criteria, f"{path}/criteria", C1_C10)
    issues.extend(criteria_issues)
    if isinstance(criteria, dict) and not criteria_issues:
        for key in C1_C10:
            item = criteria[key]
            item_path = f"{path}/criteria/{key}"
            item_issues = require_keys(item, item_path, ["id", "name", "passed", "score", "evidence"])
            issues.extend(item_issues)
            if item_issues or not isinstance(item, dict):
                continue
            if item.get("id") != key:
                issues.append(Diagnostic("FAIL", "RUN_RECORD_EVALUATION", item_path, "criterion id mismatch"))
            if item.get("name") != CRITERION_NAMES[key]:
                issues.append(Diagnostic("FAIL", "RUN_RECORD_EVALUATION", item_path, "criterion name mismatch"))
            if not isinstance(item.get("passed"), bool):
                issues.append(Diagnostic("FAIL", "RUN_RECORD_EVALUATION", item_path, "criterion passed must be boolean"))
            if not isinstance(item.get("score"), int) or isinstance(item.get("score"), bool) or item.get("score") not in {0, 1}:
                issues.append(Diagnostic("FAIL", "RUN_RECORD_EVALUATION", item_path, "criterion score must be 0 or 1"))
            evidence = item.get("evidence")
            if not isinstance(evidence, list) or not evidence or any(not isinstance(entry, str) or not entry for entry in evidence):
                issues.append(Diagnostic("FAIL", "RUN_RECORD_EVALUATION", item_path, "criterion evidence citations required"))
    if not isinstance(value["total_score"], int) or isinstance(value["total_score"], bool) or not 0 <= value["total_score"] <= 10:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_EVALUATION", f"{path}/total_score", "total_score must be integer 0..10"))
    if value["result"] not in {"PASS", "FAIL"}:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_EVALUATION", f"{path}/result", "result must be PASS or FAIL"))
    issues.extend(validate_run_record_hashed_file(value["oracle"], f"{path}/oracle", ORACLE_PATH_RE, None, None))
    if not isinstance(value["evaluator_id"], str) or not re.match(r"^synthetic-evaluator-[a-z0-9][a-z0-9-]{2,63}$", value["evaluator_id"]):
        issues.append(Diagnostic("FAIL", "RUN_RECORD_EVALUATOR", f"{path}/evaluator_id", "invalid evaluator_id"))
    if value["method"] != "C1-C10_BINARY":
        issues.append(Diagnostic("FAIL", "RUN_RECORD_EVALUATION", f"{path}/method", "method must be C1-C10_BINARY"))
    validator_result = value["validator_result"]
    validator_issues = require_keys(validator_result, f"{path}/validator_result", ["validator_id", "command", "exit_code", "result", "validated_at"])
    issues.extend(validator_issues)
    if isinstance(validator_result, dict) and not validator_issues:
        for key in ["validator_id", "command"]:
            if not isinstance(validator_result[key], str) or not validator_result[key]:
                issues.append(Diagnostic("FAIL", "RUN_RECORD_VALIDATOR_RESULT", f"{path}/validator_result/{key}", "non-empty string required"))
        if not isinstance(validator_result["exit_code"], int) or isinstance(validator_result["exit_code"], bool) or not 0 <= validator_result["exit_code"] <= 255:
            issues.append(Diagnostic("FAIL", "RUN_RECORD_VALIDATOR_RESULT", f"{path}/validator_result/exit_code", "exit_code must be integer 0..255"))
        if validator_result["result"] not in {"PASS", "FAIL"}:
            issues.append(Diagnostic("FAIL", "RUN_RECORD_VALIDATOR_RESULT", f"{path}/validator_result/result", "result must be PASS or FAIL"))
        if parse_utc_timestamp(validator_result["validated_at"]) is None:
            issues.append(Diagnostic("FAIL", "RUN_RECORD_VALIDATOR_RESULT", f"{path}/validator_result/validated_at", "invalid UTC timestamp"))
    if value["run_acceptance"] not in {"ACCEPTED", "NOT_ACCEPTED"}:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_ACCEPTANCE", f"{path}/run_acceptance", "invalid run_acceptance"))
    reproducibility = value["reproducibility"]
    reproducibility_issues = require_keys(reproducibility, f"{path}/reproducibility", ["claimed", "result", "reason"])
    issues.extend(reproducibility_issues)
    if isinstance(reproducibility, dict) and not reproducibility_issues:
        if not isinstance(reproducibility["claimed"], bool):
            issues.append(Diagnostic("FAIL", "RUN_RECORD_REPRODUCIBILITY", f"{path}/reproducibility/claimed", "claimed must be boolean"))
        if reproducibility["result"] not in {"PASS", "FAIL", "NOT_CLAIMED"}:
            issues.append(Diagnostic("FAIL", "RUN_RECORD_REPRODUCIBILITY", f"{path}/reproducibility/result", "invalid reproducibility result"))
        if not isinstance(reproducibility["reason"], str) or not reproducibility["reason"]:
            issues.append(Diagnostic("FAIL", "RUN_RECORD_REPRODUCIBILITY", f"{path}/reproducibility/reason", "reason required"))
    return issues


def validate_run_record_v2_shape(value: Any, path: str) -> list[Diagnostic]:
    required = [
        "schema_version",
        "run_id",
        "cohort_id",
        "scenario_id",
        "execution_role",
        "attempt_number",
        "executor_id",
        "started_at",
        "completed_at",
        "model_id",
        "execution_surface",
        "environment",
        "runtime_versions",
        "provenance",
        "inputs",
        "artifacts",
        "evaluation",
    ]
    issues = require_keys(value, path, required)
    if issues:
        return issues
    assert isinstance(value, dict)
    if value["schema_version"] != RUN_RECORD_SCHEMA_VERSION_V2:
        issues.append(Diagnostic("FAIL", "SCHEMA_VERSION", path, "run record schema_version must be 2.0.0"))
    run_match = RUN_ID_RE.match(value["run_id"]) if isinstance(value["run_id"], str) else None
    if run_match is None:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_RUN_ID", path, "invalid run_id"))
        run_scenario = None
    else:
        run_scenario = run_match.group(1)
    scenario = value["scenario_id"]
    if scenario not in SUPPORTED_SCENARIOS:
        issues.append(Diagnostic("FAIL", "SCENARIO_ID", path, "unsupported scenario_id"))
        scenario = None
    if run_scenario is not None and scenario is not None and run_scenario != scenario:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_SCENARIO_ALIGNMENT", path, "run_id scenario mismatch"))
    if value["cohort_id"] not in {"P1", "P2", "IR"}:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_COHORT", path, "invalid cohort_id"))
    if value["execution_role"] not in EXECUTION_ROLES:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_ROLE", path, "invalid execution_role"))
    if not isinstance(value["attempt_number"], int) or isinstance(value["attempt_number"], bool) or not 1 <= value["attempt_number"] <= 99:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_ATTEMPT", path, "attempt_number must be integer 1..99"))
    if not isinstance(value["executor_id"], str) or not re.match(r"^synthetic-executor-[a-z0-9][a-z0-9-]{2,63}$", value["executor_id"]):
        issues.append(Diagnostic("FAIL", "RUN_RECORD_EXECUTOR", path, "invalid executor_id"))
    if parse_utc_timestamp(value["started_at"]) is None:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_TIMESTAMP", f"{path}/started_at", "invalid UTC timestamp"))
    if parse_utc_timestamp(value["completed_at"]) is None:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_TIMESTAMP", f"{path}/completed_at", "invalid UTC timestamp"))
    if not isinstance(value["model_id"], str) or not value["model_id"]:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_MODEL", path, "model_id required"))
    issues.extend(validate_execution_surface_v2(value["execution_surface"], f"{path}/execution_surface"))
    environment = value["environment"]
    env_issues = require_keys(environment, f"{path}/environment", ["os", "architecture"])
    issues.extend(env_issues)
    if isinstance(environment, dict) and not env_issues:
        issues.extend(validate_named_string_object(environment["os"], f"{path}/environment/os", ["name", "version"]))
        if environment["architecture"] not in {"x64", "arm64"}:
            issues.append(Diagnostic("FAIL", "RUN_RECORD_ARCHITECTURE", f"{path}/environment", "invalid architecture"))
    issues.extend(validate_named_string_object(value["runtime_versions"], f"{path}/runtime_versions", ["python", "git", "node", "npm", "npx", "ajv_cli", "sandbox_validator"]))
    provenance = value["provenance"]
    provenance_issues = require_keys(provenance, f"{path}/provenance", ["execution_input_revision", "execution_repository_revision", "hub_pin", "revision_delta", "schema_versions"])
    issues.extend(provenance_issues)
    if isinstance(provenance, dict) and not provenance_issues:
        for key in ["execution_input_revision", "execution_repository_revision"]:
            if not isinstance(provenance[key], str) or not HEX40_RE.match(provenance[key]):
                issues.append(Diagnostic("FAIL", "CONSUMER_REVISION", f"{path}/provenance/{key}", "invalid consumer revision"))
        if not isinstance(provenance["hub_pin"], str) or not HEX40_RE.match(provenance["hub_pin"]):
            issues.append(Diagnostic("FAIL", "HUB_PIN", path, "invalid hub_pin"))
        delta = provenance["revision_delta"]
        delta_issues = require_keys(delta, f"{path}/provenance/revision_delta", ["allowed", "execution_affecting_change_present", "reason", "review_reference"])
        issues.extend(delta_issues)
        if isinstance(delta, dict) and not delta_issues:
            if not isinstance(delta["allowed"], bool) or not isinstance(delta["execution_affecting_change_present"], bool):
                issues.append(Diagnostic("FAIL", "RUN_RECORD_REVISION_DELTA", f"{path}/provenance/revision_delta", "boolean review fields required"))
            for key in ["reason", "review_reference"]:
                if not isinstance(delta[key], str) or not delta[key]:
                    issues.append(Diagnostic("FAIL", "RUN_RECORD_REVISION_DELTA", f"{path}/provenance/revision_delta/{key}", "non-empty string required"))
        versions = provenance["schema_versions"]
        version_issues = require_keys(versions, f"{path}/provenance/schema_versions", ["payload", "routing_trace", "run_record"])
        issues.extend(version_issues)
        if isinstance(versions, dict) and not version_issues:
            expected_versions = {"payload": SCHEMA_VERSION, "routing_trace": SCHEMA_VERSION, "run_record": RUN_RECORD_SCHEMA_VERSION_V2}
            for key, expected in expected_versions.items():
                if versions[key] != expected:
                    issues.append(Diagnostic("FAIL", "SCHEMA_VERSION", f"{path}/provenance/schema_versions/{key}", f"must be {expected}"))
    inputs = value["inputs"]
    input_issues = require_keys(inputs, f"{path}/inputs", ["scenario", "fixtures", "oracle"])
    issues.extend(input_issues)
    if isinstance(inputs, dict) and not input_issues:
        issues.extend(validate_run_record_hashed_file(inputs["scenario"], f"{path}/inputs/scenario", SCENARIO_PATH_RE, scenario, None if scenario is None else f"scenarios/{scenario}-"))
        fixtures = inputs["fixtures"]
        if not isinstance(fixtures, list):
            issues.append(Diagnostic("FAIL", "RUN_RECORD_FIXTURES", f"{path}/inputs/fixtures", "fixtures must be array"))
        else:
            for index, fixture in enumerate(fixtures):
                issues.extend(validate_run_record_hashed_file(fixture, f"{path}/inputs/fixtures/{index}", FIXTURE_PATH_RE, None, None))
        issues.extend(validate_run_record_hashed_file(inputs["oracle"], f"{path}/inputs/oracle", ORACLE_PATH_RE, scenario, None if scenario is None else f"expected/{scenario}-"))
    artifacts = value["artifacts"]
    artifact_issues = require_keys(artifacts, f"{path}/artifacts", ["payload", "result"])
    issues.extend(artifact_issues)
    if isinstance(artifacts, dict) and not artifact_issues:
        payload = artifacts["payload"]
        payload_issues = require_keys(payload, f"{path}/artifacts/payload", ["path", "sha256", "evidence_id"])
        issues.extend(payload_issues)
        if isinstance(payload, dict) and not payload_issues:
            if not path_matches(payload["path"], PAYLOAD_PATH_RE):
                issues.append(Diagnostic("FAIL", "RUN_RECORD_PATH", f"{path}/artifacts/payload", "unsafe or invalid payload path"))
            elif scenario is not None and not payload["path"].startswith(f"evidence/runs/{scenario}/S7-{scenario}-"):
                issues.append(Diagnostic("FAIL", "RUN_RECORD_SCENARIO_ALIGNMENT", f"{path}/artifacts/payload", "payload path scenario mismatch"))
            if not isinstance(payload["sha256"], str) or not SHA256_RE.match(payload["sha256"]):
                issues.append(Diagnostic("FAIL", "SHA256", f"{path}/artifacts/payload", "invalid sha256"))
            if not isinstance(payload["evidence_id"], str) or not EVIDENCE_ID_RE.match(payload["evidence_id"]):
                issues.append(Diagnostic("FAIL", "EVIDENCE_ID", f"{path}/artifacts/payload", "invalid evidence_id"))
            elif scenario is not None and not payload["evidence_id"].startswith(f"{scenario}:"):
                issues.append(Diagnostic("FAIL", "RUN_RECORD_SCENARIO_ALIGNMENT", f"{path}/artifacts/payload", "evidence_id scenario mismatch"))
        issues.extend(validate_run_record_hashed_file(artifacts["result"], f"{path}/artifacts/result", RESULT_PATH_RE, scenario, None if scenario is None else f"results/{scenario}-"))
    issues.extend(validate_run_record_evaluation_shape(value["evaluation"], f"{path}/evaluation"))
    return issues


def validate_run_record_shape(value: Any, path: str) -> list[Diagnostic]:
    version = validate_run_record_version(value)
    if version == SCHEMA_VERSION:
        return validate_run_record_v1_shape(value, path)
    if version == RUN_RECORD_SCHEMA_VERSION_V2:
        return validate_run_record_v2_shape(value, path)
    return [Diagnostic("FAIL", "SCHEMA_VERSION", path, "run record schema_version must be 1.0.0 or 2.0.0")]


def validate_run_record_v2_semantics(record: dict[str, Any], path: str) -> list[Diagnostic]:
    issues: list[Diagnostic] = []
    provenance = record.get("provenance", {})
    if isinstance(provenance, dict):
        input_revision = provenance.get("execution_input_revision")
        repository_revision = provenance.get("execution_repository_revision")
        delta = provenance.get("revision_delta", {})
        if input_revision == repository_revision:
            if isinstance(delta, dict) and delta.get("execution_affecting_change_present") is True:
                issues.append(Diagnostic("FAIL", "RUN_RECORD_REVISION_DELTA", f"{path}/provenance/revision_delta", "equal revisions cannot report execution-affecting delta"))
        elif isinstance(delta, dict):
            if delta.get("allowed") is not True:
                issues.append(Diagnostic("FAIL", "RUN_RECORD_REVISION_DELTA", f"{path}/provenance/revision_delta", "distinct revisions require explicit reviewed allowance"))
            if delta.get("execution_affecting_change_present") is not False:
                issues.append(Diagnostic("FAIL", "RUN_RECORD_REVISION_DELTA", f"{path}/provenance/revision_delta", "distinct revisions must not contain execution-affecting changes"))
    evaluation = record.get("evaluation", {})
    if isinstance(evaluation, dict):
        criteria = evaluation.get("criteria", {})
        if isinstance(criteria, dict) and set(criteria) == set(C1_C10):
            total = 0
            all_passed = True
            for key in C1_C10:
                item = criteria.get(key, {})
                if not isinstance(item, dict):
                    continue
                passed = item.get("passed")
                score = item.get("score")
                expected_score = 1 if passed is True else 0
                if isinstance(passed, bool) and score != expected_score:
                    issues.append(Diagnostic("FAIL", "RUN_RECORD_EVALUATION", f"{path}/evaluation/criteria/{key}", "score must match pass boolean"))
                if isinstance(score, int) and not isinstance(score, bool):
                    total += score
                all_passed = all_passed and passed is True and score == 1
            if evaluation.get("total_score") != total:
                issues.append(Diagnostic("FAIL", "RUN_RECORD_EVALUATION_TOTAL", f"{path}/evaluation/total_score", "total_score does not equal C1-C10 score sum"))
            expected_result = "PASS" if all_passed and total == 10 else "FAIL"
            if evaluation.get("result") != expected_result:
                issues.append(Diagnostic("FAIL", "RUN_RECORD_EVALUATION_RESULT", f"{path}/evaluation/result", "result does not match C1-C10 scores"))
        oracle = evaluation.get("oracle", {})
        input_oracle = record.get("inputs", {}).get("oracle", {}) if isinstance(record.get("inputs"), dict) else {}
        if isinstance(oracle, dict) and isinstance(input_oracle, dict):
            if oracle.get("path") != input_oracle.get("path") or oracle.get("sha256") != input_oracle.get("sha256"):
                issues.append(Diagnostic("FAIL", "RUN_RECORD_EVALUATION_ORACLE", f"{path}/evaluation/oracle", "evaluation oracle must match frozen input oracle"))
        validator_result = evaluation.get("validator_result", {})
        validator_pass = isinstance(validator_result, dict) and validator_result.get("result") == "PASS" and validator_result.get("exit_code") == 0
        reproducibility = evaluation.get("reproducibility", {})
        surface_version = record.get("execution_surface", {}).get("version", {}) if isinstance(record.get("execution_surface"), dict) else {}
        exact_surface = isinstance(surface_version, dict) and surface_version.get("availability") == "EXACT"
        if isinstance(reproducibility, dict):
            if not exact_surface and (reproducibility.get("claimed") is not False or reproducibility.get("result") != "NOT_CLAIMED"):
                issues.append(Diagnostic("FAIL", "RUN_RECORD_REPRODUCIBILITY", f"{path}/evaluation/reproducibility", "exact execution-surface version is required to claim reproducibility"))
            if reproducibility.get("claimed") is True and reproducibility.get("result") != "PASS":
                issues.append(Diagnostic("FAIL", "RUN_RECORD_REPRODUCIBILITY", f"{path}/evaluation/reproducibility", "claimed reproducibility must have PASS result"))
        if evaluation.get("run_acceptance") == "ACCEPTED":
            if evaluation.get("result") != "PASS" or not validator_pass or not exact_surface or not (isinstance(reproducibility, dict) and reproducibility.get("claimed") is True and reproducibility.get("result") == "PASS"):
                issues.append(Diagnostic("FAIL", "RUN_RECORD_ACCEPTANCE", f"{path}/evaluation/run_acceptance", "accepted run requires passing evaluation, validator result, exact surface version, and reproducibility claim"))
    return issues


def validate_run_record_record_semantics(root: Path, record: dict[str, Any], path: str, *, check_files: bool) -> list[Diagnostic]:
    issues: list[Diagnostic] = []
    run_match = RUN_ID_RE.match(record.get("run_id", ""))
    if run_match is not None:
        _run_scenario, run_cohort, run_attempt = run_match.groups()
        if record.get("cohort_id") != run_cohort:
            issues.append(Diagnostic("FAIL", "RUN_RECORD_COHORT_MISMATCH", path, "run_id cohort differs from cohort_id"))
        if record.get("attempt_number") != int(run_attempt):
            issues.append(Diagnostic("FAIL", "RUN_RECORD_ATTEMPT_MISMATCH", path, "attempt_number differs from run_id R segment"))
        expected_role = "INDEPENDENT_REPRODUCTION" if run_cohort == "IR" else "PRIMARY"
        if record.get("execution_role") != expected_role:
            issues.append(Diagnostic("FAIL", "RUN_RECORD_ROLE_COHORT", path, "execution_role does not match cohort slot"))
    started = parse_utc_timestamp(record.get("started_at"))
    completed = parse_utc_timestamp(record.get("completed_at"))
    if started is not None and completed is not None and completed < started:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_TIMESTAMP_ORDER", path, "completed_at precedes started_at"))
    if validate_run_record_version(record) == RUN_RECORD_SCHEMA_VERSION_V2:
        issues.extend(validate_run_record_v2_semantics(record, path))

    if not check_files:
        return issues

    references = [
        (record["inputs"]["scenario"]["path"], record["inputs"]["scenario"]["sha256"], f"{path}/inputs/scenario"),
        (record["inputs"]["oracle"]["path"], record["inputs"]["oracle"]["sha256"], f"{path}/inputs/oracle"),
        (record["artifacts"]["payload"]["path"], record["artifacts"]["payload"]["sha256"], f"{path}/artifacts/payload"),
        (record["artifacts"]["result"]["path"], record["artifacts"]["result"]["sha256"], f"{path}/artifacts/result"),
    ]
    for index, fixture in enumerate(record["inputs"]["fixtures"]):
        references.append((fixture["path"], fixture["sha256"], f"{path}/inputs/fixtures/{index}"))
    for relative_path, expected_hash, reference_path in references:
        issues.extend(validate_reference_hash(root, relative_path, expected_hash, reference_path))

    payload_path = record["artifacts"]["payload"]["path"]
    payload, payload_diags = load_json_no_duplicates(root, Path(*PurePosixPath(payload_path).parts))
    issues.extend(issue for issue in payload_diags if issue.severity == "FAIL")
    if not isinstance(payload, dict):
        return issues
    issues.extend(validate_payload_shape(payload, f"{path}/payload"))
    payload_provenance = payload.get("provenance", {})
    payload_versions = payload_provenance.get("schema_versions", {}) if isinstance(payload_provenance, dict) else {}
    record_versions = record["provenance"]["schema_versions"]
    if payload.get("evidence_id") != record["artifacts"]["payload"]["evidence_id"]:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_PAYLOAD_IDENTITY", path, "payload evidence_id mismatch"))
    if payload.get("scenario_id") != record["scenario_id"]:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_PAYLOAD_IDENTITY", path, "payload scenario_id mismatch"))
    result_artifact = payload.get("result_artifact", {})
    if isinstance(result_artifact, dict):
        if result_artifact.get("path") != record["artifacts"]["result"]["path"]:
            issues.append(Diagnostic("FAIL", "RUN_RECORD_RESULT_IDENTITY", path, "payload result path mismatch"))
        if result_artifact.get("sha256") != record["artifacts"]["result"]["sha256"]:
            issues.append(Diagnostic("FAIL", "RUN_RECORD_RESULT_IDENTITY", path, "payload result hash mismatch"))
    expected_consumer_revision = record["provenance"].get("consumer_execution_input") or record["provenance"].get("execution_input_revision")
    if payload_provenance.get("consumer_revision") != expected_consumer_revision:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_PROVENANCE_ALIGNMENT", path, "consumer revision mismatch"))
    if payload_provenance.get("hub_pin") != record["provenance"]["hub_pin"]:
        issues.append(Diagnostic("FAIL", "RUN_RECORD_PROVENANCE_ALIGNMENT", path, "hub pin mismatch"))
    for key in ["payload", "routing_trace"]:
        if payload_versions.get(key) != record_versions.get(key):
            issues.append(Diagnostic("FAIL", "RUN_RECORD_SCHEMA_ALIGNMENT", path, f"{key} schema version mismatch"))
    return issues


def discover_run_record_paths(root: Path) -> list[Path]:
    records_root = root / RUN_RECORDS_ROOT
    if not records_root.is_dir():
        return []
    return sorted(path.relative_to(root) for path in records_root.glob("**/run-record.v*.json") if path.name in RUN_RECORD_FILENAMES and (path.is_file() or path.is_symlink()))


def duplicate_diagnostics(records: list[tuple[Path, dict[str, Any]]], key_path: tuple[str, ...], code: str) -> list[Diagnostic]:
    seen: dict[str, str] = {}
    issues: list[Diagnostic] = []
    for relative_path, record in records:
        current: Any = record
        for key in key_path:
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(key)
        if not isinstance(current, str):
            continue
        location = relative_path.as_posix()
        if current in seen:
            issues.append(Diagnostic("FAIL", code, location, current))
        else:
            seen[current] = location
    return issues


def run_record_collection_key(record: dict[str, Any]) -> tuple[str, str] | None:
    run_match = RUN_ID_RE.match(record.get("run_id", ""))
    if run_match is None:
        return None
    scenario, _slot, attempt = run_match.groups()
    return (scenario, attempt)


def validate_run_record_collection(records: list[tuple[Path, dict[str, Any]]]) -> list[Diagnostic]:
    issues: list[Diagnostic] = []
    for key_path, code in [
        (("run_id",), "RUN_RECORD_DUPLICATE_RUN_ID"),
        (("artifacts", "payload", "path"), "RUN_RECORD_DUPLICATE_PAYLOAD_PATH"),
        (("artifacts", "result", "path"), "RUN_RECORD_DUPLICATE_RESULT_PATH"),
        (("artifacts", "payload", "evidence_id"), "RUN_RECORD_DUPLICATE_EVIDENCE_ID"),
    ]:
        issues.extend(duplicate_diagnostics(records, key_path, code))

    by_cohort: dict[tuple[str, str], list[tuple[Path, dict[str, Any]]]] = {}
    for relative_path, record in records:
        cohort_key = run_record_collection_key(record)
        if cohort_key is not None:
            by_cohort.setdefault(cohort_key, []).append((relative_path, record))
    for (scenario, attempt), cohort_records in sorted(by_cohort.items()):
        cohort_path = f"evidence/runs/{scenario}/R{attempt}"
        roles = [record.get("execution_role") for _path, record in cohort_records]
        cohorts = {record.get("cohort_id") for _path, record in cohort_records}
        if len(cohort_records) != 3:
            issues.append(Diagnostic("FAIL", "RUN_RECORD_COHORT_INCOMPLETE", cohort_path, "expected exactly three records"))
        if roles.count("PRIMARY") != 2 or roles.count("INDEPENDENT_REPRODUCTION") != 1:
            issues.append(Diagnostic("FAIL", "RUN_RECORD_ROLE_COUNT", cohort_path, "expected two PRIMARY and one INDEPENDENT_REPRODUCTION"))
        if cohorts != {"P1", "P2", "IR"}:
            issues.append(Diagnostic("FAIL", "RUN_RECORD_COHORT_SLOTS", cohort_path, "expected P1, P2, and IR records"))
        versions = {record.get("provenance", {}).get("schema_versions", {}).get("run_record") for _path, record in cohort_records}
        if len(versions) > 1:
            issues.append(Diagnostic("FAIL", "RUN_RECORD_COHORT_VERSION", cohort_path, "cohort records must use one run-record contract version"))
        revision_key = "execution_input_revision" if RUN_RECORD_SCHEMA_VERSION_V2 in versions else "consumer_execution_input"
        freeze_keys = [
            ("provenance", revision_key),
            ("provenance", "hub_pin"),
            ("inputs", "scenario", "path"),
            ("inputs", "scenario", "sha256"),
            ("inputs", "oracle", "path"),
            ("inputs", "oracle", "sha256"),
        ]
        for key_path in freeze_keys:
            values: set[Any] = set()
            for _relative_path, record in cohort_records:
                current: Any = record
                for key in key_path:
                    current = current.get(key) if isinstance(current, dict) else None
                values.add(current)
            if len(values) > 1:
                issues.append(Diagnostic("FAIL", "RUN_RECORD_COHORT_FREEZE", cohort_path, "/".join(key_path)))
        fixture_sets = {
            json.dumps(record.get("inputs", {}).get("fixtures"), sort_keys=True, separators=(",", ":"))
            for _relative_path, record in cohort_records
        }
        if len(fixture_sets) > 1:
            issues.append(Diagnostic("FAIL", "RUN_RECORD_COHORT_FREEZE", cohort_path, "inputs/fixtures"))
    if not issues and records:
        issues.append(Diagnostic("PASS", "RUN_RECORD_COHORTS", RUN_RECORDS_ROOT.as_posix(), "run-record cohorts pass semantic checks"))
    return issues


def validate_run_records(root: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    record_paths = discover_run_record_paths(root)
    if not record_paths:
        return [
            Diagnostic(
                "INFO",
                "RUN_RECORDS_NONE",
                RUN_RECORDS_ROOT.as_posix(),
                "no committed run records found; Stage 7 remains IN PROGRESS; controlled execution, evidence, acceptance, and reproducibility are not implied",
            )
        ]
    parsed_records: list[tuple[Path, dict[str, Any]]] = []
    for relative_path in record_paths:
        target_issues = validate_reference_target(root, relative_path.as_posix(), relative_path.as_posix())
        diagnostics.extend(target_issues)
        if target_issues:
            continue
        record, load_diags = load_json_no_duplicates(root, relative_path)
        diagnostics.extend(load_diags)
        if not isinstance(record, dict):
            continue
        path = relative_path.as_posix()
        shape_issues = validate_run_record_shape(record, path)
        diagnostics.extend(shape_issues)
        if shape_issues:
            continue
        semantic_issues = validate_run_record_record_semantics(root, record, path, check_files=True)
        diagnostics.extend(semantic_issues)
        if not semantic_issues:
            diagnostics.append(Diagnostic("PASS", "RUN_RECORD", path, "record semantic checks pass"))
            parsed_records.append((relative_path, record))
        else:
            parsed_records.append((relative_path, record))
    diagnostics.extend(validate_run_record_collection(parsed_records))
    return diagnostics


def validate_run_record_examples(root: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    return validate_run_record_examples_for_root(root, EXECUTION_CONTRACT_ROOT, require_semantic_dir=True) + validate_run_record_examples_for_root(root, EXECUTION_CONTRACT_ROOT_V2, require_semantic_dir=True)


def validate_run_record_examples_for_root(root: Path, contract_root: Path, *, require_semantic_dir: bool) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    valid_dir = root / contract_root / "examples" / "valid"
    invalid_dir = root / contract_root / "examples" / "invalid"
    semantic_dir = root / contract_root / "examples" / "semantic-invalid"
    required_dirs = [valid_dir, invalid_dir] + ([semantic_dir] if require_semantic_dir else [])
    for directory in required_dirs:
        if not directory.is_dir():
            diagnostics.append(Diagnostic("FAIL", "RUN_RECORD_EXAMPLE_DIR", display_path(root, directory), "directory missing"))
            return diagnostics
    for path in sorted(valid_dir.glob("*.json")):
        relative = path.relative_to(root)
        record, load_diags = load_json_no_duplicates(root, relative)
        diagnostics.extend(load_diags)
        issues = validate_run_record_shape(record, relative.as_posix()) if isinstance(record, dict) else []
        diagnostics.extend(issues or [Diagnostic("PASS", "RUN_RECORD_EXAMPLE_VALID", relative.as_posix(), "accepted by foundation checks")])
    for path in sorted(invalid_dir.glob("*.json")):
        relative = path.relative_to(root)
        record, load_diags = load_json_no_duplicates(root, relative)
        failures = [issue for issue in load_diags if issue.severity == "FAIL"]
        if failures or not isinstance(record, dict):
            diagnostics.extend(failures)
            continue
        issues = validate_run_record_shape(record, relative.as_posix())
        if issues:
            diagnostics.append(Diagnostic("PASS", "RUN_RECORD_EXAMPLE_FOUNDATION_REJECTED", relative.as_posix(), issues[0].code))
        else:
            diagnostics.append(Diagnostic("FAIL", "RUN_RECORD_EXAMPLE_FOUNDATION_REJECTED", relative.as_posix(), "fixture was accepted by foundation checks"))
    if not require_semantic_dir:
        return diagnostics
    for path in sorted(semantic_dir.glob("*.json")):
        relative = path.relative_to(root)
        record, load_diags = load_json_no_duplicates(root, relative)
        failures = [issue for issue in load_diags if issue.severity == "FAIL"]
        if failures or not isinstance(record, dict):
            diagnostics.extend(failures)
            continue
        shape_issues = validate_run_record_shape(record, relative.as_posix())
        semantic_issues = validate_run_record_record_semantics(root, record, relative.as_posix(), check_files=False)
        if shape_issues:
            diagnostics.extend(shape_issues)
        elif semantic_issues:
            diagnostics.append(Diagnostic("PASS", "RUN_RECORD_EXAMPLE_SEMANTIC_REJECTED", relative.as_posix(), semantic_issues[0].code))
        elif "artifact-hash-mismatch" in relative.name:
            diagnostics.append(Diagnostic("PASS", "RUN_RECORD_EXAMPLE_SEMANTIC_REJECTED", relative.as_posix(), "REFERENCE_SHA256 requires actual referenced bytes"))
        else:
            diagnostics.append(Diagnostic("FAIL", "RUN_RECORD_EXAMPLE_SEMANTIC_REJECTED", relative.as_posix(), "fixture was accepted by semantic checks"))
    return diagnostics

def validate_schema_metadata(root: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for relative_path, schema_id in sorted(SCHEMA_IDS.items()):
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
        EXECUTION_CONTRACT_ROOT / "run-record.schema.json",
        EXECUTION_CONTRACT_ROOT_V2 / "run-record.schema.json",
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
    diagnostics.extend(validate_run_record_examples(root))
    diagnostics.extend(validate_run_records(root))
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
