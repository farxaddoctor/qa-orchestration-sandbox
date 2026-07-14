# QA Orchestration Consumer Simulation

This repository is a consumer sandbox for validating QA orchestration behavior against the architecture supplied by `vendor/qa-skills-hub`. The vendored hub is the read-only source of commands, governance, routing, workflows, agents, skills, standards, and validation rules; the consumer repository supplies synthetic inputs and records expected and actual simulation outcomes.

## Repository structure

- `fixtures/` contains synthetic, application-agnostic source material used by scenarios.
- `scenarios/` defines the simulation prompts and constraints.
- `expected/` contains the expected routing and outcomes used for comparison.
- `results/` is the destination for captured simulation results.
- `evaluation/` contains evaluation reports and routing scorecards.
- `vendor/` contains the read-only `qa-skills-hub` dependency.

## QA Skills Hub Integration

### Dependency and entry flow

The hub is integrated as the Git submodule `vendor/qa-skills-hub` with an
immutable commit pin. The approved initial pin is:

```text
81197bf84ed51913bc3a93ace41661ab80a8e3b9
```

Treat the hub as read-only. Keep product-specific requirements, code, tests,
and other consumer context in this repository. Codex, Claude Code, and Cursor
enter through `AGENTS.md`, `CLAUDE.md`, and
`.cursor/rules/qa-skills-hub.mdc`, respectively.

Every QA request follows:

```text
Consumer root entry -> Hub command -> QA orchestrator -> Constitution -> Policies -> Routing -> Workflow -> Agent -> Skills -> Audit -> Human Gate -> Output
```

Direct command-to-skill or entry-to-skill bypass is forbidden.

### Clone, bootstrap, and health

For a fresh clone, initialize the pinned submodule in the same operation:

```text
git clone --recurse-submodules <consumer-repository-url>
```

After an ordinary clone, or when the submodule is missing or uninitialized,
restore the exact tracked checkout with:

```text
python scripts/qa_hub.py bootstrap
```

Run the read-only integration health check from the consumer root with:

```text
python scripts/qa_hub.py doctor
```

### Immutable updates and rollback

Update only to a reviewed, full 40-character hexadecimal commit SHA:

```text
python scripts/qa_hub.py update --commit <40-character-sha>
```

The update command does not create a commit, push, or pull request. On success,
it leaves only `vendor/qa-skills-hub` staged as a new gitlink. Review that
single-path change before committing it through the normal consumer workflow.

To roll back an update before it is committed, restore the gitlink from `HEAD`,
restore the path-scoped submodule checkout, and run the doctor:

```text
git restore --source=HEAD --staged -- vendor/qa-skills-hub
git submodule update --init --recursive -- vendor/qa-skills-hub
python scripts/qa_hub.py doctor
```

After the update has been committed, revert the corresponding consumer commit
through the normal reviewed workflow, then restore and validate the checkout:

```text
git revert <consumer-commit-sha>
git submodule update --init --recursive -- vendor/qa-skills-hub
python scripts/qa_hub.py doctor
```

### CI and diagnosis

The integration workflow runs on Ubuntu and Windows. It initializes recursive
submodules, runs the consumer doctor, and then runs the hub static validator as
a separate step from `vendor/qa-skills-hub`.

Common diagnostics:

- Missing or uninitialized hub: exit `22`; run `bootstrap`.
- Stale checkout or gitlink mismatch: exit `23`; run `bootstrap` to restore the
  exact tracked commit.
- Dirty hub checkout: exit `24`; stop and inspect the hub changes.
- Dirty consumer: exit `25`; review the reported staged, unstaged, and untracked
  paths before retrying.
- Broken configuration, structure, or validator: exits `20`, `21`, `26`, or
  `27`; stop and repair the reported integration defect before continuing.

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
