# SIM-003: QA Review Routing

Review `fixtures/review/unstable-example.spec.ts` through the QA orchestration architecture.

## Constraints

- Analysis only. Do not create, edit, delete, rename, or format any file.
- Use command `qa-review` and route through the orchestrator; direct command-to-skill routing is forbidden.
- Report findings first, ordered by severity and supported by file evidence.
- `playwright-typescript` is supporting capability only; `qa-code-review` remains primary.
- Do not fix the example or execute it.

## Required output

Return a no-edit review artifact and a **Simulation Routing Trace** containing:

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
