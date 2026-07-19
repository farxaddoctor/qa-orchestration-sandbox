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
