# Claude Code Consumer Entry

Treat `vendor/qa-skills-hub` as an immutable, pinned dependency. Keep
consumer-specific context in this repository and never modify hub content from
a consumer task.

For QA requests, read `vendor/qa-skills-hub/CLAUDE.md`, select the applicable
hub command, and preserve this flow:

Consumer root entry -> Hub command -> QA orchestrator -> Constitution ->
Policies -> Routing -> Workflow -> Agent -> Skills -> Audit -> Human Gate ->
Output

Do not invoke a skill directly or bypass orchestration. If the submodule is
missing or uninitialized, stop and instruct the operator to run the future
command `python scripts/qa_hub.py bootstrap`.

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
