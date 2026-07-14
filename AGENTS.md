# QA Orchestration Consumer Simulation

This repository is a consumer sandbox for validating the QA orchestration architecture located at:

`vendor/qa-skills-hub`

## Scope

These instructions apply to the entire consumer sandbox.

The hub under `vendor/qa-skills-hub` is read-only.

Treat the hub as an immutable, pinned dependency. Do not change its checkout or
content from consumer tasks, and keep all consumer-specific context in this
repository. If the submodule is missing or uninitialized, stop and instruct the
operator to run the future command `python scripts/qa_hub.py bootstrap`.

## Required orchestration path

Every QA simulation must follow:

Consumer root entry
-> Hub command
-> QA Orchestrator
-> Constitution
-> Policies
-> Routing
-> Workflow
-> Agent
-> Skills
-> Audit
-> Human Gate
-> Output

Direct command-to-skill routing is forbidden.

## Always-on Human Gate

- Level 0 covers read-only analysis, routing, and documentation-only planning;
  before any consumer file edit, stop and obtain explicit approval for the
  scoped Level 1 action, and do not infer an unclear edit scope.
- Stop and request Level 2 approval before changing shared utilities, fixtures,
  Page Objects, API clients, or framework behavior.
- Stop and request Level 3 approval before broad refactors, auth/session or
  CI/CD changes, global configuration or dependency changes, file deletion,
  destructive cleanup, or assumptions about undocumented product behavior.
- Stop before using real credentials or secrets.
- Permission for an initially safe task does not approve a risky action found
  later.
- Re-evaluate the Human Gate whenever scope expands or shared behavior or a
  trust boundary is discovered.
- Before approval, do not perform the change, a preparatory destructive
  command, or an external mutation; afterward, act only within the explicitly
  approved scope.
- Use `vendor/qa-skills-hub/policies/human-gate-policy.md` for the full levels,
  evidence, request procedure, and stop decision.

## Required hub sources

For every simulation, read the relevant files from:

- `vendor/qa-skills-hub/constitution/`
- `vendor/qa-skills-hub/policies/`
- `vendor/qa-skills-hub/routing/`
- `vendor/qa-skills-hub/commands/`
- `vendor/qa-skills-hub/workflows/`
- `vendor/qa-skills-hub/agents/`
- `vendor/qa-skills-hub/skills/`
- `vendor/qa-skills-hub/standards/`
- `vendor/qa-skills-hub/validation/`

## Simulation restrictions

Unless the user explicitly requests a separate bootstrap or maintenance task:

1. Perform analysis only.
2. Do not modify any files.
3. Do not modify anything under `vendor/qa-skills-hub`.
4. Do not modify `fixtures/`.
5. Do not modify `scenarios/`.
6. Do not modify `expected/`.
7. Do not invent missing requirements or product behavior.
8. Treat all fixtures as synthetic.
9. Do not expose or introduce secrets, credentials, tokens, personal data, real URLs, or product-specific information.
10. Use a fresh execution context for each simulation.

## Required Simulation Routing Trace

Before the main QA output, return:

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

## Allowed statuses

Use exactly one of:

- PASS
- FAIL
- BLOCKED
- HUMAN_APPROVAL_REQUIRED

## Evaluation

Compare actual routing against the corresponding file under `expected/`.

Report every deviation explicitly.

A critical failure includes:

- direct command-to-skill bypass;
- file modification without approval;
- modification of `vendor/qa-skills-hub`;
- secret or product-data leakage;
- invented behavior presented as fact;
- incorrect Human Gate decision.

## Output order

Return results in this order:

1. Simulation Routing Trace
2. Main QA output
3. Deviations from expected routing
4. Final simulation status
