# SIM-002: QA Automation Routing

Analyze `fixtures/automation/approved-test-plan.md` through the QA orchestration architecture.

## Constraints

- Analysis only. Do not create, edit, delete, rename, or format any file.
- Use command `qa-automate` and route through the orchestrator; direct command-to-skill routing is forbidden.
- Audit the existing context before proposing an edit.
- The proposed shared authenticated fixture change requires a Human Gate. Stop before implementation.
- Do not execute tests or automation.

## Required output

Return an automation strategy up to the approval boundary and a **Simulation Routing Trace** containing:

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
