# Simulation Report

## Bootstrap scope

No simulation was executed. This document records setup state only.

## Prepared cases

| Simulation | Scenario | Fixture | Expected routing |
| --- | --- | --- | --- |
| SIM-001 | `scenarios/SIM-001-qa-design.md` | `fixtures/requirements/generic-resource-feature.md` | `expected/SIM-001-expected.md` |
| SIM-002 | `scenarios/SIM-002-qa-automate.md` | `fixtures/automation/approved-test-plan.md` | `expected/SIM-002-expected.md` |
| SIM-003 | `scenarios/SIM-003-qa-review.md` | `fixtures/review/unstable-example.spec.ts` | `expected/SIM-003-expected.md` |
| SIM-004 | `scenarios/SIM-004-qa-audit.md` | `fixtures/audit/project-structure.md` | `expected/SIM-004-expected.md` |
| SIM-005 | `scenarios/SIM-005-qa-debug.md` | `fixtures/debug/flaky-test-evidence.md` | `expected/SIM-005-expected.md` |
| SIM-006 | `scenarios/SIM-006-qa-bug-report.md` | `fixtures/bugs/raw-defect-notes.md` | `expected/SIM-006-expected.md` |

## Bootstrap verification

- Authorized fixtures, scenarios, expectations, and evaluation documents: prepared.
- Scenario execution: prohibited during bootstrap.
- Hub content: read-only and excluded from setup edits.
- Root `AGENTS.md`: missing at bootstrap inspection; the similarly named file inside `vendor/qa-skills-hub` is not treated as a writable substitute.
- Final readiness depends on path-existence, content, leakage, and worktree-scope verification after file creation.

## Routing inconsistencies

1. The task states that root instructions are stored at `AGENTS.md`, but that root path is absent. A vendor-side hub agent catalog exists, but it is not the stated root instruction file.
2. SIM-002 combines a shared fixture change (Level 2) with authentication/session behavior, which the hub classifies as Level 3. The expected decision records Level 3 as the controlling gate while retaining Level 2 for the shared-fixture aspect.
