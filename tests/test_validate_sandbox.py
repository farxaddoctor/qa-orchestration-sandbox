from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_sandbox


def read_manifest() -> dict:
    with (REPO_ROOT / "evidence/manifest.v1.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def issue_codes(issues: list[validate_sandbox.Diagnostic]) -> set[str]:
    return {issue.code for issue in issues if issue.severity == "FAIL"}


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def routing_trace(simulation_id: str) -> dict:
    return {
        "schema_version": "1.0.0",
        "simulation_id": simulation_id,
        "status": "PASS",
        "command": "commands/qa-automate.md",
        "constitution": "constitution/qa-agent-constitution.md",
        "policies": ["policies/human-gate-policy.md"],
        "workflow": "workflows/test-plan-to-automation.md",
        "primary_agent": "agents/automation-engineer.md",
        "supporting_agents": [],
        "skills": ["skills/pytest-python/SKILL.md"],
        "audit_before_edit": "completed",
        "human_gate": {
            "required": False,
            "level": 0,
            "approval_state": "NOT_REQUIRED",
            "approved_scope": None,
        },
        "stop_condition": "complete",
        "expected_artifact": "run record",
    }


def payload_document(
    scenario_id: str,
    evidence_id: str,
    result_path: str,
    result_sha: str,
    consumer_revision: str,
    hub_pin: str,
) -> dict:
    return {
        "schema_version": "1.0.0",
        "evidence_id": evidence_id,
        "scenario_id": scenario_id,
        "result_artifact": {
            "path": result_path,
            "sha256": result_sha,
        },
        "routing_trace": routing_trace(scenario_id),
        "provenance": {
            "consumer_revision": consumer_revision,
            "hub_pin": hub_pin,
            "schema_versions": {
                "payload": "1.0.0",
                "routing_trace": "1.0.0",
            },
        },
    }


def run_record_document(
    scenario_id: str,
    cohort_id: str,
    execution_role: str,
    attempt_number: int,
    evidence_id: str,
    scenario_path: str,
    scenario_sha: str,
    fixture_path: str,
    fixture_sha: str,
    oracle_path: str,
    oracle_sha: str,
    payload_path: str,
    payload_sha: str,
    result_path: str,
    result_sha: str,
    consumer_revision: str,
    hub_pin: str,
) -> dict:
    run_id = f"S7-{scenario_id}-{cohort_id}-R{attempt_number:02d}"
    return {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "cohort_id": cohort_id,
        "scenario_id": scenario_id,
        "execution_role": execution_role,
        "attempt_number": attempt_number,
        "executor_id": f"synthetic-executor-{cohort_id.lower()}-01",
        "started_at": "2026-01-01T00:00:00Z",
        "completed_at": "2026-01-01T00:05:00Z",
        "model_id": "synthetic-model-stage7-v1",
        "execution_surface": {
            "name": "synthetic-codex-surface",
            "version": "stage7-contract-test",
        },
        "environment": {
            "os": {
                "name": "SyntheticOS",
                "version": "2026.01",
            },
            "architecture": "x64",
        },
        "runtime_versions": {
            "python": "3.12.0",
            "git": "2.50.0",
            "node": "22.0.0",
            "npm": "10.0.0",
            "npx": "10.0.0",
            "ajv_cli": "5.0.0",
            "sandbox_validator": "stage7-test",
        },
        "provenance": {
            "consumer_execution_input": consumer_revision,
            "hub_pin": hub_pin,
            "schema_versions": {
                "payload": "1.0.0",
                "routing_trace": "1.0.0",
                "run_record": "1.0.0",
            },
        },
        "inputs": {
            "scenario": {
                "path": scenario_path,
                "sha256": scenario_sha,
            },
            "fixtures": [
                {
                    "path": fixture_path,
                    "sha256": fixture_sha,
                }
            ],
            "oracle": {
                "path": oracle_path,
                "sha256": oracle_sha,
            },
        },
        "artifacts": {
            "payload": {
                "path": payload_path,
                "sha256": payload_sha,
                "evidence_id": evidence_id,
            },
            "result": {
                "path": result_path,
                "sha256": result_sha,
            },
        },
    }


def create_valid_run_record_cohort(
    root: Path,
    *,
    scenario_id: str = "SIM-002",
    attempt_number: int = 1,
    consumer_revision: str = "a" * 40,
    hub_pin: str = "b" * 40,
) -> dict[str, Path]:
    attempt_suffix = f"r{attempt_number:02d}"
    scenario_path = f"scenarios/{scenario_id}-qa-automate.md"
    fixture_path = "fixtures/automation/approved-test-plan.md"
    oracle_path = f"expected/{scenario_id}-expected.md"
    for relative_path, content in [
        (scenario_path, "scenario\n"),
        (fixture_path, "fixture\n"),
        (oracle_path, "oracle\n"),
    ]:
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
    scenario_sha = sha256_file(root / scenario_path)
    fixture_sha = sha256_file(root / fixture_path)
    oracle_sha = sha256_file(root / oracle_path)
    paths: dict[str, Path] = {}
    for cohort_id, role in [("P1", "PRIMARY"), ("P2", "PRIMARY"), ("IR", "INDEPENDENT_REPRODUCTION")]:
        run_id = f"S7-{scenario_id}-{cohort_id}-R{attempt_number:02d}"
        evidence_id = f"{scenario_id}:stage7-{cohort_id.lower()}-{attempt_suffix}:v1"
        result_path = f"results/{scenario_id}-stage7-{cohort_id.lower()}-{attempt_suffix}.md"
        result_target = root / result_path
        result_target.parent.mkdir(parents=True, exist_ok=True)
        result_target.write_text(f"result {cohort_id} {attempt_suffix}\n", encoding="utf-8", newline="\n")
        result_sha = sha256_file(result_target)
        payload_path = f"evidence/runs/{scenario_id}/{run_id}.payload.json"
        payload = payload_document(
            scenario_id,
            evidence_id,
            result_path,
            result_sha,
            consumer_revision,
            hub_pin,
        )
        write_json(root / payload_path, payload)
        payload_sha = sha256_file(root / payload_path)
        record = run_record_document(
            scenario_id,
            cohort_id,
            role,
            attempt_number,
            evidence_id,
            scenario_path,
            scenario_sha,
            fixture_path,
            fixture_sha,
            oracle_path,
            oracle_sha,
            payload_path,
            payload_sha,
            result_path,
            result_sha,
            consumer_revision,
            hub_pin,
        )
        record_path = root / "evidence" / "runs" / scenario_id / run_id / "run-record.v1.json"
        write_json(record_path, record)
        paths[cohort_id] = record_path
    return paths


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rewrite_record(path: Path, record: dict) -> None:
    write_json(path, record)


def rewrite_payload_for_record(root: Path, record_path: Path, payload: dict) -> None:
    record = read_json(record_path)
    payload_path = root / record["artifacts"]["payload"]["path"]
    write_json(payload_path, payload)
    record["artifacts"]["payload"]["sha256"] = sha256_file(payload_path)
    rewrite_record(record_path, record)

class ValidateSandboxTests(unittest.TestCase):
    def test_current_manifest_passes_semantic_and_integrity_checks(self) -> None:
        manifest = read_manifest()
        shape_issues = validate_sandbox.validate_manifest_shape(manifest, "manifest")
        semantic_issues = validate_sandbox.validate_manifest_semantics(
            REPO_ROOT, manifest, "manifest", check_files=True
        )
        self.assertEqual([], shape_issues)
        self.assertNotIn("FAIL", {issue.severity for issue in semantic_issues})

    def test_semantic_invalid_manifests_fail_for_intended_reasons(self) -> None:
        cases = {
            "manifest-canonical-in-history.json": "MANIFEST_CANONICAL_IN_HISTORY",
            "manifest-duplicate-evidence-id.json": "MANIFEST_DUPLICATE_EVIDENCE_ID",
            "manifest-duplicate-result-path.json": "MANIFEST_DUPLICATE_RESULT_PATH",
        }
        base = REPO_ROOT / "contracts/evidence/v1/examples/semantic-invalid"
        for filename, expected_code in cases.items():
            with self.subTest(filename=filename):
                data, diagnostics = validate_sandbox.load_json_no_duplicates(REPO_ROOT, base.relative_to(REPO_ROOT) / filename)
                self.assertFalse(issue_codes(diagnostics))
                self.assertEqual([], validate_sandbox.validate_manifest_shape(data, filename))
                issues = validate_sandbox.validate_manifest_semantics(
                    REPO_ROOT, data, filename, check_files=False
                )
                self.assertIn(expected_code, issue_codes(issues))

    def test_duplicate_json_keys_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "dup.json"
            path.write_text('{"a": 1, "a": 2}\n', encoding="utf-8", newline="\n")
            _data, diagnostics = validate_sandbox.load_json_no_duplicates(root, Path("dup.json"))
            self.assertIn("JSON_DUPLICATE_KEY", issue_codes(diagnostics))

    def test_canonical_history_overlap_fails(self) -> None:
        manifest = read_manifest()
        entry = manifest["scenarios"]["SIM-002"]
        entry["historical_attempts"].append(copy.deepcopy(entry["canonical"]))
        issues = validate_sandbox.validate_manifest_semantics(REPO_ROOT, manifest, "manifest", check_files=False)
        self.assertIn("MANIFEST_CANONICAL_IN_HISTORY", issue_codes(issues))

    def test_canonical_null_is_accepted(self) -> None:
        manifest = read_manifest()
        manifest["scenarios"]["SIM-002"]["canonical"] = None
        shape_issues = validate_sandbox.validate_manifest_shape(manifest, "manifest")
        semantic_issues = validate_sandbox.validate_manifest_semantics(
            REPO_ROOT, manifest, "manifest", check_files=False
        )
        self.assertEqual([], shape_issues)
        self.assertNotIn("FAIL", {issue.severity for issue in semantic_issues})

    def test_duplicate_evidence_id_fails(self) -> None:
        manifest = read_manifest()
        duplicate = copy.deepcopy(manifest["scenarios"]["SIM-001"]["historical_attempts"][0])
        duplicate["result_path"] = "results/SIM-001-unique-path.md"
        manifest["scenarios"]["SIM-001"]["historical_attempts"].append(duplicate)
        issues = validate_sandbox.validate_manifest_semantics(REPO_ROOT, manifest, "manifest", check_files=False)
        self.assertIn("MANIFEST_DUPLICATE_EVIDENCE_ID", issue_codes(issues))

    def test_duplicate_result_path_fails(self) -> None:
        manifest = read_manifest()
        duplicate = copy.deepcopy(manifest["scenarios"]["SIM-001"]["historical_attempts"][0])
        duplicate["evidence_id"] = "SIM-001:unique-evidence:v1"
        manifest["scenarios"]["SIM-001"]["historical_attempts"].append(duplicate)
        issues = validate_sandbox.validate_manifest_semantics(REPO_ROOT, manifest, "manifest", check_files=False)
        self.assertIn("MANIFEST_DUPLICATE_RESULT_PATH", issue_codes(issues))

    def test_unsafe_path_traversal_result_path_fails(self) -> None:
        manifest = read_manifest()
        manifest["scenarios"]["SIM-001"]["canonical"]["result_path"] = "results/../SIM-001-bad.md"
        issues = validate_sandbox.validate_manifest_shape(manifest, "manifest")
        self.assertIn("RESULT_PATH", issue_codes(issues))

    def test_missing_result_file_fails(self) -> None:
        manifest = read_manifest()
        manifest["scenarios"]["SIM-001"]["canonical"]["result_path"] = "results/SIM-001-missing.md"
        issues = validate_sandbox.validate_manifest_semantics(REPO_ROOT, manifest, "manifest", check_files=True)
        self.assertIn("RESULT_MISSING", issue_codes(issues))

    def test_direct_symlink_result_target_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            results = root / "results"
            results.mkdir()
            target = results / "SIM-001-target.md"
            target.write_text("target\n", encoding="utf-8", newline="\n")
            link = results / "SIM-001-link.md"
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlink creation denied: {exc}")
            issues = validate_sandbox.validate_result_target(
                root, "results/SIM-001-link.md", "manifest/SIM-001/canonical"
            )
            self.assertIn("RESULT_SYMLINK", issue_codes(issues))

    def test_symlinked_parent_directory_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            real_results = root / "real-results"
            real_results.mkdir()
            (real_results / "SIM-001-target.md").write_text("target\n", encoding="utf-8", newline="\n")
            try:
                (root / "results").symlink_to(real_results, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlink creation denied: {exc}")
            issues = validate_sandbox.validate_result_target(
                root, "results/SIM-001-target.md", "manifest/SIM-001/canonical"
            )
            self.assertIn("RESULT_SYMLINK", issue_codes(issues))

    def test_junction_detection_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            results = root / "results"
            results.mkdir()
            (results / "SIM-001-target.md").write_text("target\n", encoding="utf-8", newline="\n")

            def fake_isjunction(path: object) -> bool:
                return Path(path) == results

            with mock.patch.object(validate_sandbox.os.path, "isjunction", side_effect=fake_isjunction, create=True):
                issues = validate_sandbox.validate_result_target(
                    root, "results/SIM-001-target.md", "manifest/SIM-001/canonical"
                )
            self.assertIn("RESULT_JUNCTION", issue_codes(issues))

    def test_sha_mismatch_fails(self) -> None:
        manifest = read_manifest()
        manifest["scenarios"]["SIM-001"]["canonical"]["sha256"] = "0" * 64
        issues = validate_sandbox.validate_manifest_semantics(REPO_ROOT, manifest, "manifest", check_files=True)
        self.assertIn("RESULT_SHA256", issue_codes(issues))

    def test_encoding_failures(self) -> None:
        cases = {
            "bom.json": b"\xef\xbb\xbf{}\n",
            "cr.json": b"{}\r\n",
            "missing-lf.json": b"{}",
            "nul.json": b"{\x00}\n",
        }
        expected = {
            "bom.json": "ENCODING_BOM",
            "cr.json": "ENCODING_CR",
            "missing-lf.json": "ENCODING_TRAILING_LF",
            "nul.json": "ENCODING_NUL",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for filename, data in cases.items():
                with self.subTest(filename=filename):
                    (root / filename).write_bytes(data)
                    diagnostics = validate_sandbox.validate_bytes(root, Path(filename))
                    self.assertIn(expected[filename], issue_codes(diagnostics))

    def test_malformed_json_reports_json_parse(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "bad.json"
            path.write_text('{"a":\n', encoding="utf-8", newline="\n")
            _data, diagnostics = validate_sandbox.load_json_no_duplicates(root, Path("bad.json"))
            codes = issue_codes(diagnostics)
            self.assertIn("JSON_PARSE", codes)
            self.assertNotIn("JSON_DUPLICATE_KEY", codes)

    def test_example_output_does_not_claim_python_schema_validation(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", str(REPO_ROOT / "scripts/validate_sandbox.py")],
            cwd=REPO_ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertIn("INFO JSON_SCHEMA_ENGINE_DEFERRED", completed.stdout)
        self.assertIn("Ajv remains authoritative", completed.stdout)
        self.assertIn("EXAMPLE_FOUNDATION_REJECTED", completed.stdout)
        self.assertNotIn("EXAMPLE_SCHEMA_INVALID", completed.stdout)

    def test_deterministic_output_ordering(self) -> None:
        first, first_operational = validate_sandbox.validate(REPO_ROOT)
        second, second_operational = validate_sandbox.validate(REPO_ROOT)
        self.assertEqual(first_operational, second_operational)
        self.assertEqual([item.render() for item in first], [item.render() for item in second])

    def test_validator_does_not_change_repository_state_or_target_bytes(self) -> None:
        status_before = subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=REPO_ROOT,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout
        target = REPO_ROOT / "evidence/manifest.v1.json"
        before = hashlib.sha256(target.read_bytes()).hexdigest()
        subprocess.run(
            [sys.executable, "-B", str(REPO_ROOT / "scripts/validate_sandbox.py")],
            cwd=REPO_ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        after = hashlib.sha256(target.read_bytes()).hexdigest()
        status_after = subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=REPO_ROOT,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout
        self.assertEqual(before, after)
        self.assertEqual(status_before, status_after)

    def test_exit_code_classification(self) -> None:
        passed = subprocess.run(
            [sys.executable, "-B", str(REPO_ROOT / "scripts/validate_sandbox.py")],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(validate_sandbox.EXIT_PASSED, passed.returncode)

        failed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(REPO_ROOT / "scripts/validate_sandbox.py"),
                "--root",
                str(self.make_minimal_invalid_root()),
            ],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(validate_sandbox.EXIT_VALIDATION_FAILURE, failed.returncode)

        operational = subprocess.run(
            [
                sys.executable,
                "-B",
                str(REPO_ROOT / "scripts/validate_sandbox.py"),
                "--root",
                str(REPO_ROOT / "does-not-exist"),
            ],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(validate_sandbox.EXIT_OPERATIONAL_ERROR, operational.returncode)

    def test_no_run_record_state_reports_explicit_info(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            diagnostics = validate_sandbox.validate_run_records(root)
        self.assertEqual(["RUN_RECORDS_NONE"], [item.code for item in diagnostics])
        self.assertEqual("INFO", diagnostics[0].severity)
        self.assertIn("controlled execution", diagnostics[0].detail)
        self.assertIn("not implied", diagnostics[0].detail)

    def test_valid_complete_three_run_cohort_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            create_valid_run_record_cohort(root)
            diagnostics = validate_sandbox.validate_run_records(root)
        self.assertNotIn("FAIL", {item.severity for item in diagnostics})
        self.assertIn("RUN_RECORD_COHORTS", {item.code for item in diagnostics})
        self.assertEqual(3, sum(1 for item in diagnostics if item.code == "RUN_RECORD"))

    def test_two_complete_run_record_cohorts_same_scenario_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            create_valid_run_record_cohort(root, attempt_number=1)
            create_valid_run_record_cohort(root, attempt_number=2)
            diagnostics = validate_sandbox.validate_run_records(root)
        self.assertNotIn("FAIL", {item.severity for item in diagnostics})
        self.assertIn("RUN_RECORD_COHORTS", {item.code for item in diagnostics})
        self.assertEqual(6, sum(1 for item in diagnostics if item.code == "RUN_RECORD"))

    def test_incomplete_second_run_record_cohort_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            create_valid_run_record_cohort(root, attempt_number=1)
            second = create_valid_run_record_cohort(root, attempt_number=2)
            second["IR"].unlink()
            issues = validate_sandbox.validate_run_records(root)
        self.assertIn("RUN_RECORD_COHORT_INCOMPLETE", issue_codes(issues))

    def test_run_record_freeze_may_differ_across_complete_cohorts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            create_valid_run_record_cohort(root, attempt_number=1, consumer_revision="a" * 40, hub_pin="b" * 40)
            create_valid_run_record_cohort(root, attempt_number=2, consumer_revision="c" * 40, hub_pin="d" * 40)
            diagnostics = validate_sandbox.validate_run_records(root)
        self.assertNotIn("FAIL", {item.severity for item in diagnostics})
        self.assertEqual(6, sum(1 for item in diagnostics if item.code == "RUN_RECORD"))

    def test_incomplete_run_record_cohort_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = create_valid_run_record_cohort(root)
            paths["IR"].unlink()
            issues = validate_sandbox.validate_run_records(root)
        self.assertIn("RUN_RECORD_COHORT_INCOMPLETE", issue_codes(issues))

    def test_incorrect_run_record_role_count_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = create_valid_run_record_cohort(root)
            record = read_json(paths["IR"])
            record["execution_role"] = "PRIMARY"
            rewrite_record(paths["IR"], record)
            issues = validate_sandbox.validate_run_records(root)
        codes = issue_codes(issues)
        self.assertIn("RUN_RECORD_ROLE_COUNT", codes)
        self.assertIn("RUN_RECORD_ROLE_COHORT", codes)

    def test_duplicate_run_record_identity_keys_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = create_valid_run_record_cohort(root)
            p1 = read_json(paths["P1"])
            p2 = read_json(paths["P2"])
            p2["run_id"] = p1["run_id"]
            p2["artifacts"]["payload"]["path"] = p1["artifacts"]["payload"]["path"]
            p2["artifacts"]["payload"]["evidence_id"] = p1["artifacts"]["payload"]["evidence_id"]
            p2["artifacts"]["result"]["path"] = p1["artifacts"]["result"]["path"]
            rewrite_record(paths["P2"], p2)
            issues = validate_sandbox.validate_run_records(root)
        codes = issue_codes(issues)
        self.assertIn("RUN_RECORD_DUPLICATE_RUN_ID", codes)
        self.assertIn("RUN_RECORD_DUPLICATE_PAYLOAD_PATH", codes)
        self.assertIn("RUN_RECORD_DUPLICATE_RESULT_PATH", codes)
        self.assertIn("RUN_RECORD_DUPLICATE_EVIDENCE_ID", codes)

    def test_run_record_cohort_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = create_valid_run_record_cohort(root)
            record = read_json(paths["P1"])
            record["cohort_id"] = "P2"
            rewrite_record(paths["P1"], record)
            issues = validate_sandbox.validate_run_records(root)
        self.assertIn("RUN_RECORD_COHORT_MISMATCH", issue_codes(issues))

    def test_run_record_attempt_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = create_valid_run_record_cohort(root)
            record = read_json(paths["P1"])
            record["attempt_number"] = 2
            rewrite_record(paths["P1"], record)
            issues = validate_sandbox.validate_run_records(root)
        self.assertIn("RUN_RECORD_ATTEMPT_MISMATCH", issue_codes(issues))

    def test_run_record_timestamp_reversal_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = create_valid_run_record_cohort(root)
            record = read_json(paths["P1"])
            record["completed_at"] = "2025-12-31T23:59:59Z"
            rewrite_record(paths["P1"], record)
            issues = validate_sandbox.validate_run_records(root)
        self.assertIn("RUN_RECORD_TIMESTAMP_ORDER", issue_codes(issues))

    def test_run_record_unsafe_and_symlinked_reference_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = create_valid_run_record_cohort(root)
            unsafe = read_json(paths["P1"])
            unsafe["inputs"]["fixtures"][0]["path"] = "fixtures\\bad.md"
            rewrite_record(paths["P1"], unsafe)
            unsafe_issues = validate_sandbox.validate_run_records(root)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = create_valid_run_record_cohort(root)
            fixture = root / "fixtures/automation/approved-test-plan.md"
            real = root / "fixtures/automation/real-fixture.md"
            real.write_text("fixture\n", encoding="utf-8", newline="\n")
            fixture.unlink()
            try:
                fixture.symlink_to(real)
            except OSError as exc:
                self.skipTest(f"symlink creation denied: {exc}")
            symlink_issues = validate_sandbox.validate_run_records(root)

        self.assertIn("RUN_RECORD_PATH", issue_codes(unsafe_issues))
        self.assertIn("REFERENCE_SYMLINK", issue_codes(symlink_issues))

    def test_run_record_missing_reference_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            create_valid_run_record_cohort(root)
            (root / "expected/SIM-002-expected.md").unlink()
            issues = validate_sandbox.validate_run_records(root)
        self.assertIn("REFERENCE_MISSING", issue_codes(issues))

    def test_run_record_sha_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = create_valid_run_record_cohort(root)
            record = read_json(paths["P1"])
            record["inputs"]["scenario"]["sha256"] = "0" * 64
            rewrite_record(paths["P1"], record)
            issues = validate_sandbox.validate_run_records(root)
        self.assertIn("REFERENCE_SHA256", issue_codes(issues))

    def test_run_record_payload_result_revision_and_schema_mismatch_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = create_valid_run_record_cohort(root)
            record = read_json(paths["P1"])
            payload_path = root / record["artifacts"]["payload"]["path"]
            payload = read_json(payload_path)
            payload["evidence_id"] = "SIM-002:different:v1"
            payload["result_artifact"]["path"] = "results/SIM-002-different.md"
            payload["result_artifact"]["sha256"] = "0" * 64
            payload["provenance"]["consumer_revision"] = "c" * 40
            payload["provenance"]["schema_versions"]["payload"] = "1.0.1"
            rewrite_payload_for_record(root, paths["P1"], payload)
            issues = validate_sandbox.validate_run_records(root)
        codes = issue_codes(issues)
        self.assertIn("RUN_RECORD_PAYLOAD_IDENTITY", codes)
        self.assertIn("RUN_RECORD_RESULT_IDENTITY", codes)
        self.assertIn("RUN_RECORD_PROVENANCE_ALIGNMENT", codes)
        self.assertIn("RUN_RECORD_SCHEMA_ALIGNMENT", codes)

    def test_run_record_cohort_freeze_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = create_valid_run_record_cohort(root)
            record = read_json(paths["P2"])
            record["provenance"]["consumer_execution_input"] = "d" * 40
            rewrite_record(paths["P2"], record)
            issues = validate_sandbox.validate_run_records(root)
        self.assertIn("RUN_RECORD_COHORT_FREEZE", issue_codes(issues))

    def test_run_record_validator_is_read_only_for_temp_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = create_valid_run_record_cohort(root)
            before = {key: sha256_file(path) for key, path in paths.items()}
            validate_sandbox.validate_run_records(root)
            after = {key: sha256_file(path) for key, path in paths.items()}
        self.assertEqual(before, after)

    def test_run_record_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            create_valid_run_record_cohort(root)
            first = validate_sandbox.validate_run_records(root)
            second = validate_sandbox.validate_run_records(root)
        self.assertEqual([item.render() for item in first], [item.render() for item in second])

    def make_minimal_invalid_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        shutil.copytree(REPO_ROOT / "contracts", root / "contracts")
        shutil.copytree(REPO_ROOT / "evidence", root / "evidence")
        shutil.copytree(REPO_ROOT / "results", root / "results")
        manifest_path = root / "evidence/manifest.v1.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        data["scenarios"]["SIM-001"]["canonical"]["sha256"] = "0" * 64
        manifest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
        return root


if __name__ == "__main__":
    unittest.main()
