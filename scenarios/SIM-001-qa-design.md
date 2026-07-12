# SIM-001: QA Design Routing

Analyze `fixtures/requirements/generic-resource-feature.md` through the QA orchestration architecture.

## Constraints

- Analysis only. Do not create, edit, delete, rename, or format any file.
- Use command `qa-design` and route through the orchestrator; direct command-to-skill routing is forbidden.
- Treat undocumented behavior as unknown and do not invent facts.
- Human Gate Level 0 is expected because this is read-only test design.
- Do not execute tests or automation.

## Required output

Return a test-design artifact and a **Simulation Routing Trace** containing:

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
