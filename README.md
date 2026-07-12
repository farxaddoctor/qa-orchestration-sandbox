# QA Orchestration Consumer Simulation

This repository is a consumer sandbox for validating QA orchestration behavior against the architecture supplied by `vendor/qa-skills-hub`. The vendored hub is the read-only source of commands, governance, routing, workflows, agents, skills, standards, and validation rules; the consumer repository supplies synthetic inputs and records expected and actual simulation outcomes.

## Repository structure

- `fixtures/` contains synthetic, application-agnostic source material used by scenarios.
- `scenarios/` defines the simulation prompts and constraints.
- `expected/` contains the expected routing and outcomes used for comparison.
- `results/` is the destination for captured simulation results.
- `evaluation/` contains evaluation reports and routing scorecards.
- `vendor/` contains the read-only `qa-skills-hub` dependency.

## Running simulations

Run each simulation in a fresh Codex session so no context or state carries over from another scenario. Simulation sessions are analysis-only and use:

```text
--sandbox read-only
```

Repository setup or maintenance tasks are separate from simulations and use:

```text
--sandbox workspace-write
```

Compare each simulation result with its corresponding file under `expected/`.

## Scenarios

- `SIM-001 qa-design`
- `SIM-002 qa-automate`
- `SIM-003 qa-review`
- `SIM-004 qa-audit`
- `SIM-005 qa-debug`
- `SIM-006 qa-bug-report`

All fixtures are synthetic and application-agnostic. Do not add real URLs, credentials, company names, product names, customer data, or secrets to this repository.
