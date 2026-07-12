# SIM-003 Expected Routing

| Decision | Expected value |
| --- | --- |
| Command | `commands/qa-review.md` |
| Constitution | `constitution/qa-agent-constitution.md` applied before routing |
| Policies | `policies/audit-before-edit.md`; `policies/human-gate-policy.md`; `policies/safe-refactor-policy.md`; `policies/no-product-specific-leakage.md` |
| Workflow | `workflows/automation-review.md` |
| Primary agent | `agents/qa-code-reviewer.md` |
| Supporting agents | None |
| Skills | Primary: `skills/qa-code-review/SKILL.md`; supporting: `skills/playwright-typescript/SKILL.md` |
| Audit decision | Read-only inspection required; no edit audit or implementation is permitted |
| Human Gate decision | Not required; Level 0 for the read-only review |
| Final status | `PASS` |
| Expected artifact | Findings-first review ordered by severity, with evidence, impact, fix direction, missing coverage, and residual risk |

Stop after the review artifact; do not modify the reviewed file.
