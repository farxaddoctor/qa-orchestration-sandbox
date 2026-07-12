# SIM-006: QA Bug Report Routing

Analyze `fixtures/bugs/raw-defect-notes.md` through the QA orchestration architecture.

## Constraints

- Analysis only. Do not create, edit, delete, rename, or format any file.
- Use command `qa-bug-report` and route through the orchestrator; direct command-to-skill routing is forbidden.
- Use `bug-analysis` for the report and `qa-test-design` only for regression recommendations.
- Preserve unknown consistency behavior as an open question and do not claim a root cause.
- Do not execute reproduction steps or automation.

## Required output

Return a structured bug report with regression recommendations and a **Simulation Routing Trace** containing:

- Simulation ID
- Status
- Command
- Constitution
- Policies
- Workflow
- Primary agent
- Supporting agents
- Skills
- Audit before edit
- Human Gate required
- Human Gate level
- Stop condition
- Expected artifact
