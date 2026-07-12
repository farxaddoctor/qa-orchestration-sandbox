# SIM-005: QA Debug Routing

Analyze `fixtures/debug/flaky-test-evidence.md` through the QA orchestration architecture.

## Constraints

- Analysis only. Do not create, edit, delete, rename, or format any file.
- Use command `qa-debug` and route through the orchestrator; direct command-to-skill routing is forbidden.
- Separate confirmed evidence, hypotheses, alternatives, and unknowns.
- Load a framework skill only if the supplied evidence requires framework-specific interpretation.
- Do not weaken assertions, propose an invented root cause, or execute diagnostics.

## Required output

Return a flaky-test investigation artifact and a **Simulation Routing Trace** containing:

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
