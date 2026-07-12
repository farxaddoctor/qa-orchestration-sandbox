# SIM-004: QA Audit Routing

Audit `fixtures/audit/project-structure.md` through the QA orchestration architecture.

## Constraints

- Analysis only. Do not create, edit, delete, rename, or format any file.
- Use command `qa-audit` and route through the orchestrator; direct command-to-skill routing is forbidden.
- The audit itself is read-only and Human Gate Level 0.
- Identify Level 2 for future shared framework changes and Level 3 for future global, dependency, auth/session, deletion, or destructive changes.
- Do not claim safe-to-refactor beyond the supplied evidence.

## Required output

Return a read-only audit artifact and a **Simulation Routing Trace** containing:

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
