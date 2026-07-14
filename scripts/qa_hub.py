#!/usr/bin/env python3
"""Read-only lifecycle checks for the pinned QA skills hub submodule."""

from __future__ import annotations

import argparse
import configparser
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence

EXIT_HEALTHY = 0
EXIT_CLI_USAGE = 2
EXIT_GIT_ENVIRONMENT = 10
EXIT_INVALID_GITMODULES = 20
EXIT_INVALID_GITLINK = 21
EXIT_MISSING_SUBMODULE = 22
EXIT_CHECKOUT_MISMATCH = 23
EXIT_DIRTY_SUBMODULE = 24
EXIT_DIRTY_CONSUMER = 25
EXIT_BROKEN_STRUCTURE = 26
EXIT_VALIDATOR_FAILURE = 27
EXIT_SUBMODULE_SYNC_FAILURE = 30
EXIT_SUBMODULE_UPDATE_FAILURE = 31
EXIT_UPDATE_FETCH_FAILURE = 40
EXIT_UPDATE_TARGET_NOT_COMMIT = 41
EXIT_UPDATE_CHECKOUT_FAILURE = 42
EXIT_UPDATE_GITLINK_FAILURE = 43
EXIT_UPDATE_VALIDATION_FAILURE = 44
EXIT_UPDATE_ROLLBACK_FAILURE = 45

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
HUB_RELATIVE_PATH = "vendor/qa-skills-hub"
HUB_ROOT = REPOSITORY_ROOT / "vendor" / "qa-skills-hub"
EXPECTED_HUB_URL = "https://github.com/farxaddoctor/qa-skills-hub"
GITMODULE_SECTION = 'submodule "vendor/qa-skills-hub"'

HUB_ANCHORS = (
    "constitution/qa-agent-constitution.md",
    "policies/audit-before-edit.md",
    "policies/human-gate-policy.md",
    "routing/skill-routing-rules.md",
    "commands/qa-design.md",
    "agents/qa-orchestrator.md",
    "workflows/ai-native-qa-workflow.md",
    "SKILL_INDEX.md",
    "standards/agent-handoff-standard.md",
    "scripts/validate_repository.py",
)
CONSUMER_ENTRIES = ("AGENTS.md", "CLAUDE.md", ".cursor/rules/qa-skills-hub.mdc")


def command_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def run_command(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=command_environment(),
        shell=False,
    )


def run_git(arguments: Sequence[str], cwd: Path = REPOSITORY_ROOT) -> subprocess.CompletedProcess[str]:
    return run_command(("git", *arguments), cwd)


def pass_check(number: int, label: str, detail: str) -> None:
    print(f"PASS {number:02d} {label}: {detail}")


def fail_check(number: int, label: str, detail: str, exit_code: int) -> int:
    print(f"FAIL {number:02d} {label}: {detail}")
    return exit_code


def process_error(process: subprocess.CompletedProcess[str]) -> str:
    return process.stderr.strip() or process.stdout.strip() or f"exit {process.returncode}"


def is_link_or_junction(path: Path) -> bool:
    is_junction = getattr(os.path, "isjunction", None)
    return path.is_symlink() or bool(is_junction and is_junction(path))


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def parse_gitlink(output: str) -> tuple[str, str] | None:
    match = re.fullmatch(r"([0-9]{6}) ([0-9a-f]{40}) 0\t(.+)", output.strip())
    if not match or match.group(3) != HUB_RELATIVE_PATH:
        return None
    return match.group(1), match.group(2)


def full_commit_sha(value: str) -> str:
    if not re.fullmatch(r"[0-9a-fA-F]{40}", value):
        raise argparse.ArgumentTypeError("commit must be a full 40-character hexadecimal SHA")
    return value.lower()


def doctor(*, allow_only_staged_gitlink: bool = False) -> int:
    print("QA hub doctor")

    # 1. Consumer Git repository.
    try:
        top_level = run_git(("rev-parse", "--show-toplevel"))
    except OSError as exc:
        return fail_check(1, "CONSUMER_GIT", f"unable to execute Git ({exc})", EXIT_GIT_ENVIRONMENT)
    if top_level.returncode != 0:
        return fail_check(1, "CONSUMER_GIT", process_error(top_level), EXIT_GIT_ENVIRONMENT)
    try:
        detected_root = Path(top_level.stdout.strip()).resolve(strict=True)
        expected_root = REPOSITORY_ROOT.resolve(strict=True)
    except OSError as exc:
        return fail_check(1, "CONSUMER_GIT", f"unable to resolve repository root ({exc})", EXIT_GIT_ENVIRONMENT)
    if detected_root != expected_root:
        return fail_check(1, "CONSUMER_GIT", "script root does not match Git top-level", EXIT_GIT_ENVIRONMENT)
    pass_check(1, "CONSUMER_GIT", "consumer repository detected")

    # 2. Exact .gitmodules path and URL.
    gitmodules = REPOSITORY_ROOT / ".gitmodules"
    if not gitmodules.is_file() or is_link_or_junction(gitmodules):
        return fail_check(2, "GITMODULES", ".gitmodules is missing or is not a regular file", EXIT_INVALID_GITMODULES)
    parser = configparser.RawConfigParser(interpolation=None, strict=True)
    try:
        with gitmodules.open("r", encoding="utf-8") as handle:
            parser.read_file(handle)
    except (OSError, UnicodeError, configparser.Error) as exc:
        return fail_check(2, "GITMODULES", f"unable to parse .gitmodules ({exc})", EXIT_INVALID_GITMODULES)
    configured_path = parser.get(GITMODULE_SECTION, "path", fallback=None)
    configured_url = parser.get(GITMODULE_SECTION, "url", fallback=None)
    if configured_path != HUB_RELATIVE_PATH or configured_url != EXPECTED_HUB_URL:
        return fail_check(2, "GITMODULES", "path or URL does not match the integration contract", EXIT_INVALID_GITMODULES)
    pass_check(2, "GITMODULES", f"path={configured_path}; url={configured_url}")

    # 3. Gitlink mode 160000.
    gitlink_process = run_git(("ls-files", "--stage", "--", HUB_RELATIVE_PATH))
    if gitlink_process.returncode != 0:
        return fail_check(3, "GITLINK", process_error(gitlink_process), EXIT_GIT_ENVIRONMENT)
    gitlink = parse_gitlink(gitlink_process.stdout)
    if gitlink is None or gitlink[0] != "160000":
        return fail_check(3, "GITLINK", "tracked entry is missing or is not mode 160000", EXIT_INVALID_GITLINK)
    tracked_sha = gitlink[1]
    pass_check(3, "GITLINK", f"mode=160000; sha={tracked_sha}")

    # 4. Initialized submodule.
    git_marker = HUB_ROOT / ".git"
    if not HUB_ROOT.is_dir() or not git_marker.exists():
        return fail_check(4, "SUBMODULE_INIT", "submodule is missing or uninitialized", EXIT_MISSING_SUBMODULE)
    submodule_top = run_git(("-C", str(HUB_ROOT), "rev-parse", "--show-toplevel"))
    if submodule_top.returncode != 0:
        return fail_check(4, "SUBMODULE_INIT", process_error(submodule_top), EXIT_MISSING_SUBMODULE)
    try:
        detected_submodule_root = Path(submodule_top.stdout.strip()).resolve(strict=True)
        expected_submodule_root = HUB_ROOT.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        return fail_check(4, "SUBMODULE_INIT", f"unable to resolve submodule root ({exc})", EXIT_MISSING_SUBMODULE)
    if detected_submodule_root != expected_submodule_root:
        return fail_check(4, "SUBMODULE_INIT", "submodule Git top-level does not match integration path", EXIT_MISSING_SUBMODULE)
    pass_check(4, "SUBMODULE_INIT", "submodule worktree initialized")

    # 5. Submodule HEAD equals the tracked gitlink.
    submodule_head = run_git(("-C", str(HUB_ROOT), "rev-parse", "HEAD"))
    if submodule_head.returncode != 0:
        return fail_check(5, "CHECKOUT_SHA", process_error(submodule_head), EXIT_GIT_ENVIRONMENT)
    checkout_sha = submodule_head.stdout.strip()
    if checkout_sha != tracked_sha:
        return fail_check(5, "CHECKOUT_SHA", f"checkout={checkout_sha}; tracked={tracked_sha}", EXIT_CHECKOUT_MISMATCH)
    pass_check(5, "CHECKOUT_SHA", f"checkout matches {tracked_sha}")

    # 6. Clean submodule.
    submodule_status = run_git(("-C", str(HUB_ROOT), "status", "--porcelain=v1", "--untracked-files=all"))
    if submodule_status.returncode != 0:
        return fail_check(6, "SUBMODULE_CLEAN", process_error(submodule_status), EXIT_GIT_ENVIRONMENT)
    if submodule_status.stdout.strip():
        return fail_check(6, "SUBMODULE_CLEAN", submodule_status.stdout.strip(), EXIT_DIRTY_SUBMODULE)
    pass_check(6, "SUBMODULE_CLEAN", "submodule has no tracked or untracked changes")

    # 7. Required hub architecture anchors and validator.
    missing_anchors = [anchor for anchor in HUB_ANCHORS if not (HUB_ROOT / anchor).is_file()]
    if missing_anchors:
        return fail_check(7, "HUB_STRUCTURE", f"missing: {', '.join(missing_anchors)}", EXIT_BROKEN_STRUCTURE)
    pass_check(7, "HUB_STRUCTURE", f"{len(HUB_ANCHORS)} required anchors present")

    # 8. Consumer root entries.
    missing_entries = [entry for entry in CONSUMER_ENTRIES if not (REPOSITORY_ROOT / entry).is_file()]
    if missing_entries:
        return fail_check(8, "ROOT_ENTRIES", f"missing: {', '.join(missing_entries)}", EXIT_BROKEN_STRUCTURE)
    pass_check(8, "ROOT_ENTRIES", f"{len(CONSUMER_ENTRIES)} consumer entries present")

    # 9. Reject symlink, junction, embedded, and external-gitdir integration.
    vendor_root = REPOSITORY_ROOT / "vendor"
    git_marker = HUB_ROOT / ".git"
    if is_link_or_junction(vendor_root) or is_link_or_junction(HUB_ROOT):
        return fail_check(9, "INTEGRATION_TYPE", "vendor path is a symlink or junction", EXIT_BROKEN_STRUCTURE)
    if not git_marker.is_file() or is_link_or_junction(git_marker):
        return fail_check(9, "INTEGRATION_TYPE", "submodule .git marker is not a regular file", EXIT_BROKEN_STRUCTURE)
    try:
        marker_text = git_marker.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        return fail_check(9, "INTEGRATION_TYPE", f"unable to read submodule .git marker ({exc})", EXIT_BROKEN_STRUCTURE)
    if not marker_text.startswith("gitdir:"):
        return fail_check(9, "INTEGRATION_TYPE", "submodule .git marker has invalid format", EXIT_BROKEN_STRUCTURE)
    consumer_git_dir = run_git(("rev-parse", "--absolute-git-dir"))
    submodule_git_dir = run_git(("-C", str(HUB_ROOT), "rev-parse", "--absolute-git-dir"))
    if consumer_git_dir.returncode != 0 or submodule_git_dir.returncode != 0:
        failed = consumer_git_dir if consumer_git_dir.returncode else submodule_git_dir
        return fail_check(9, "INTEGRATION_TYPE", process_error(failed), EXIT_BROKEN_STRUCTURE)
    try:
        expected_worktree = HUB_ROOT.resolve(strict=True)
        actual_worktree = Path(submodule_top.stdout.strip()).resolve(strict=True)
        modules_root = Path(consumer_git_dir.stdout.strip()).resolve(strict=True) / "modules"
        actual_git_dir = Path(submodule_git_dir.stdout.strip()).resolve(strict=True)
    except OSError as exc:
        return fail_check(9, "INTEGRATION_TYPE", f"unable to resolve integration paths ({exc})", EXIT_BROKEN_STRUCTURE)
    if actual_worktree != expected_worktree or not is_within(actual_git_dir, modules_root):
        return fail_check(9, "INTEGRATION_TYPE", "submodule uses an external worktree or gitdir", EXIT_BROKEN_STRUCTURE)
    pass_check(9, "INTEGRATION_TYPE", "native in-repository Git submodule; no symlink or external path")

    # 10. Hub static validator through the current Python interpreter.
    validator_path = HUB_ROOT / "scripts" / "validate_repository.py"
    try:
        validator = run_command((sys.executable, str(validator_path)), HUB_ROOT)
    except OSError as exc:
        return fail_check(10, "HUB_VALIDATOR", f"unable to launch validator ({exc})", EXIT_VALIDATOR_FAILURE)
    if validator.returncode != 0:
        detail = validator.stderr.strip() or validator.stdout.strip() or f"exit {validator.returncode}"
        return fail_check(10, "HUB_VALIDATOR", detail, EXIT_VALIDATOR_FAILURE)
    validator_summary = validator.stdout.strip() or "validator completed without output"
    pass_check(10, "HUB_VALIDATOR", validator_summary)

    # 11. Consumer clean is intentionally checked last.
    if allow_only_staged_gitlink:
        staged = run_git(("diff", "--cached", "--name-only"))
        unstaged = run_git(("diff", "--name-only"))
        untracked = run_git(("ls-files", "--others", "--exclude-standard"))
        failed = next((item for item in (staged, unstaged, untracked) if item.returncode != 0), None)
        if failed is not None:
            return fail_check(11, "CONSUMER_SCOPE", process_error(failed), EXIT_GIT_ENVIRONMENT)
        staged_paths = [line for line in staged.stdout.splitlines() if line]
        unstaged_paths = [line for line in unstaged.stdout.splitlines() if line]
        untracked_paths = [line for line in untracked.stdout.splitlines() if line]
        if staged_paths != [HUB_RELATIVE_PATH] or unstaged_paths or untracked_paths:
            return fail_check(11, "CONSUMER_SCOPE", "expected exactly one staged gitlink and no other changes", EXIT_DIRTY_CONSUMER)
        pass_check(11, "CONSUMER_SCOPE", "only the hub gitlink is staged")
        return EXIT_HEALTHY

    consumer_status = run_git(("status", "--porcelain=v1", "--untracked-files=all"))
    if consumer_status.returncode != 0:
        return fail_check(11, "CONSUMER_CLEAN", process_error(consumer_status), EXIT_GIT_ENVIRONMENT)
    if consumer_status.stdout.strip():
        changes = "; ".join(consumer_status.stdout.strip().splitlines())
        return fail_check(11, "CONSUMER_CLEAN", changes, EXIT_DIRTY_CONSUMER)
    pass_check(11, "CONSUMER_CLEAN", "consumer has no tracked or untracked changes")
    return EXIT_HEALTHY


def rollback_update(original_sha: str) -> bool:
    print(f"ROLLBACK restoring {original_sha}")
    try:
        checkout = run_git(("-C", str(HUB_ROOT), "checkout", "--detach", original_sha))
        if checkout.returncode != 0:
            print(f"FAIL ROLLBACK_CHECKOUT: {process_error(checkout)}")
            return False
        restore_index = run_git(("add", "--", HUB_RELATIVE_PATH))
        if restore_index.returncode != 0:
            print(f"FAIL ROLLBACK_INDEX: {process_error(restore_index)}")
            return False

        head = run_git(("-C", str(HUB_ROOT), "rev-parse", "HEAD"))
        branch = run_git(("-C", str(HUB_ROOT), "branch", "--show-current"))
        submodule_status = run_git(("-C", str(HUB_ROOT), "status", "--porcelain=v1", "--untracked-files=all"))
        gitlink_process = run_git(("ls-files", "--stage", "--", HUB_RELATIVE_PATH))
        consumer_status = run_git(("status", "--porcelain=v1", "--untracked-files=all"))
    except OSError as exc:
        print(f"FAIL ROLLBACK_ENVIRONMENT: {exc}")
        return False

    processes = (head, branch, submodule_status, gitlink_process, consumer_status)
    if any(process.returncode != 0 for process in processes):
        failed = next(process for process in processes if process.returncode != 0)
        print(f"FAIL ROLLBACK_VERIFY: {process_error(failed)}")
        return False
    gitlink = parse_gitlink(gitlink_process.stdout)
    restored = (
        head.stdout.strip() == original_sha
        and not branch.stdout.strip()
        and not submodule_status.stdout.strip()
        and gitlink == ("160000", original_sha)
        and not consumer_status.stdout.strip()
    )
    if not restored:
        print("FAIL ROLLBACK_VERIFY: consumer did not return to its original clean state")
        return False
    print("PASS ROLLBACK: original detached checkout and gitlink restored")
    return True


def update_failure_after_checkout(label: str, detail: str, exit_code: int, original_sha: str) -> int:
    print(f"FAIL {label}: {detail}")
    if rollback_update(original_sha):
        return exit_code
    return EXIT_UPDATE_ROLLBACK_FAILURE


def bootstrap() -> int:
    print("QA hub bootstrap")

    # Validate the immutable integration contract before any Git mutation.
    gitmodules = REPOSITORY_ROOT / ".gitmodules"
    if not gitmodules.is_file() or is_link_or_junction(gitmodules):
        return fail_check(1, "BOOTSTRAP_GITMODULES", ".gitmodules is missing or is not a regular file", EXIT_INVALID_GITMODULES)
    module_parser = configparser.RawConfigParser(interpolation=None, strict=True)
    try:
        with gitmodules.open("r", encoding="utf-8") as handle:
            module_parser.read_file(handle)
    except (OSError, UnicodeError, configparser.Error) as exc:
        return fail_check(1, "BOOTSTRAP_GITMODULES", f"unable to parse .gitmodules ({exc})", EXIT_INVALID_GITMODULES)
    configured_path = module_parser.get(GITMODULE_SECTION, "path", fallback=None)
    configured_url = module_parser.get(GITMODULE_SECTION, "url", fallback=None)
    if configured_path != HUB_RELATIVE_PATH or configured_url != EXPECTED_HUB_URL:
        return fail_check(1, "BOOTSTRAP_GITMODULES", "path or URL does not match the integration contract", EXIT_INVALID_GITMODULES)
    pass_check(1, "BOOTSTRAP_GITMODULES", f"path={configured_path}; url={configured_url}")

    try:
        gitlink_process = run_git(("ls-files", "--stage", "--", HUB_RELATIVE_PATH))
    except OSError as exc:
        return fail_check(2, "BOOTSTRAP_GITLINK", f"unable to execute Git ({exc})", EXIT_GIT_ENVIRONMENT)
    if gitlink_process.returncode != 0:
        return fail_check(2, "BOOTSTRAP_GITLINK", process_error(gitlink_process), EXIT_GIT_ENVIRONMENT)
    gitlink = parse_gitlink(gitlink_process.stdout)
    if gitlink is None or gitlink[0] != "160000":
        return fail_check(2, "BOOTSTRAP_GITLINK", "tracked entry is missing or is not mode 160000", EXIT_INVALID_GITLINK)
    tracked_sha = gitlink[1]
    pass_check(2, "BOOTSTRAP_GITLINK", f"mode=160000; target={tracked_sha}")

    try:
        sync = run_git(("submodule", "sync", "--recursive", "--", HUB_RELATIVE_PATH))
    except OSError as exc:
        return fail_check(3, "SUBMODULE_SYNC", f"unable to execute Git ({exc})", EXIT_SUBMODULE_SYNC_FAILURE)
    if sync.returncode != 0:
        return fail_check(3, "SUBMODULE_SYNC", process_error(sync), EXIT_SUBMODULE_SYNC_FAILURE)
    pass_check(3, "SUBMODULE_SYNC", "git submodule sync completed with exit 0")

    try:
        update = run_git(("submodule", "update", "--init", "--recursive", "--", HUB_RELATIVE_PATH))
    except OSError as exc:
        return fail_check(4, "SUBMODULE_UPDATE", f"unable to execute Git ({exc})", EXIT_SUBMODULE_UPDATE_FAILURE)
    if update.returncode != 0:
        return fail_check(4, "SUBMODULE_UPDATE", process_error(update), EXIT_SUBMODULE_UPDATE_FAILURE)
    pass_check(4, "SUBMODULE_UPDATE", f"exact tracked commit checked out: {tracked_sha}")

    return doctor()


def update_hub(target_sha: str) -> int:
    print(f"QA hub update target={target_sha}")

    # Strict public doctor must pass before fetch, checkout, or index mutation.
    preflight = doctor()
    if preflight != EXIT_HEALTHY:
        print(f"FAIL UPDATE_PREFLIGHT: doctor exit {preflight}; no update mutation attempted")
        return preflight

    try:
        gitlink_process = run_git(("ls-files", "--stage", "--", HUB_RELATIVE_PATH))
        origin = run_git(("-C", str(HUB_ROOT), "remote", "get-url", "origin"))
    except OSError as exc:
        return fail_check(0, "UPDATE_ORIGIN", f"unable to execute Git ({exc})", EXIT_UPDATE_FETCH_FAILURE)
    gitlink = parse_gitlink(gitlink_process.stdout) if gitlink_process.returncode == 0 else None
    if gitlink is None or gitlink[0] != "160000":
        return fail_check(0, "UPDATE_GITLINK", "unable to capture original gitlink", EXIT_UPDATE_GITLINK_FAILURE)
    original_sha = gitlink[1]
    if origin.returncode != 0 or origin.stdout.strip() != EXPECTED_HUB_URL:
        detail = process_error(origin) if origin.returncode else "origin does not match .gitmodules"
        return fail_check(0, "UPDATE_ORIGIN", detail, EXIT_UPDATE_FETCH_FAILURE)
    pass_check(0, "UPDATE_ORIGIN", "configured origin matches .gitmodules")

    try:
        fetch = run_git(("-C", str(HUB_ROOT), "fetch", "origin", target_sha))
    except OSError as exc:
        return fail_check(0, "UPDATE_FETCH", f"unable to execute Git ({exc})", EXIT_UPDATE_FETCH_FAILURE)
    if fetch.returncode != 0:
        return fail_check(0, "UPDATE_FETCH", process_error(fetch), EXIT_UPDATE_FETCH_FAILURE)
    pass_check(0, "UPDATE_FETCH", f"exact SHA fetched: {target_sha}")

    try:
        object_type = run_git(("-C", str(HUB_ROOT), "cat-file", "-t", target_sha))
        resolved = run_git(("-C", str(HUB_ROOT), "rev-parse", f"{target_sha}^{{commit}}"))
    except OSError as exc:
        return fail_check(0, "UPDATE_TARGET", f"unable to inspect target ({exc})", EXIT_UPDATE_TARGET_NOT_COMMIT)
    if (
        object_type.returncode != 0
        or object_type.stdout.strip() != "commit"
        or resolved.returncode != 0
        or resolved.stdout.strip() != target_sha
    ):
        return fail_check(0, "UPDATE_TARGET", "target is not the requested commit object", EXIT_UPDATE_TARGET_NOT_COMMIT)
    pass_check(0, "UPDATE_TARGET", "target is an exact commit object")

    try:
        checkout = run_git(("-C", str(HUB_ROOT), "checkout", "--detach", target_sha))
    except OSError as exc:
        return update_failure_after_checkout("UPDATE_CHECKOUT", str(exc), EXIT_UPDATE_CHECKOUT_FAILURE, original_sha)
    if checkout.returncode != 0:
        return update_failure_after_checkout("UPDATE_CHECKOUT", process_error(checkout), EXIT_UPDATE_CHECKOUT_FAILURE, original_sha)
    pass_check(0, "UPDATE_CHECKOUT", f"detached checkout={target_sha}")

    try:
        stage = run_git(("add", "--", HUB_RELATIVE_PATH))
    except OSError as exc:
        return update_failure_after_checkout("UPDATE_GITLINK", str(exc), EXIT_UPDATE_GITLINK_FAILURE, original_sha)
    if stage.returncode != 0:
        return update_failure_after_checkout("UPDATE_GITLINK", process_error(stage), EXIT_UPDATE_GITLINK_FAILURE, original_sha)
    try:
        updated_entry = run_git(("ls-files", "--stage", "--", HUB_RELATIVE_PATH))
    except OSError as exc:
        return update_failure_after_checkout("UPDATE_GITLINK", str(exc), EXIT_UPDATE_GITLINK_FAILURE, original_sha)
    updated_gitlink = parse_gitlink(updated_entry.stdout) if updated_entry.returncode == 0 else None
    if updated_gitlink != ("160000", target_sha):
        return update_failure_after_checkout(
            "UPDATE_GITLINK", "index does not contain the exact target gitlink", EXIT_UPDATE_GITLINK_FAILURE, original_sha
        )
    pass_check(0, "UPDATE_GITLINK", f"staged mode=160000; sha={target_sha}")

    try:
        post_update = doctor(allow_only_staged_gitlink=True)
    except Exception as exc:
        return update_failure_after_checkout("UPDATE_POSTCHECK", str(exc), EXIT_UPDATE_VALIDATION_FAILURE, original_sha)
    if post_update != EXIT_HEALTHY:
        return update_failure_after_checkout(
            "UPDATE_POSTCHECK", f"internal doctor exit {post_update}", EXIT_UPDATE_VALIDATION_FAILURE, original_sha
        )
    print("PASS UPDATE: validated target gitlink is staged; no commit created")
    return EXIT_HEALTHY


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the pinned QA skills hub integration.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="run deterministic read-only integration checks")
    commands.add_parser("bootstrap", help="initialize the exact pinned hub submodule checkout")
    update_parser = commands.add_parser("update", help="stage an exact immutable hub commit")
    update_parser.add_argument("--commit", required=True, type=full_commit_sha, help="full 40-character commit SHA")
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    if arguments.command == "doctor":
        return doctor()
    if arguments.command == "bootstrap":
        return bootstrap()
    if arguments.command == "update":
        return update_hub(arguments.commit)
    return EXIT_CLI_USAGE


if __name__ == "__main__":
    sys.exit(main())
