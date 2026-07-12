# SIM-006 Expected Routing

| Decision | Expected value |
| --- | --- |
| Command | `commands/qa-bug-report.md` |
| Constitution | `constitution/qa-agent-constitution.md` applied before routing |
| Policies | `policies/evidence-and-citation-policy.md`; `policies/no-product-specific-leakage.md`; `policies/audit-before-edit.md`; `policies/human-gate-policy.md` |
| Workflow | `workflows/bug-to-regression.md` |
| Primary agent | `agents/bug-analyst.md` |
| Supporting agents | None |
| Skills | Primary: `skills/bug-analysis/SKILL.md`; `skills/qa-test-design/SKILL.md` only for regression recommendations |
| Audit decision | No edit is permitted; audit-before-edit applies only to a later implementation handoff |
| Human Gate decision | Not required; Level 0 while expected behavior remains evidence-backed and unknown consistency behavior remains open |
| Final status | `COMPLETED` |
| Expected artifact | Structured defect report with evidence, impact, unknown root cause, open questions, and minimal regression recommendations |

Stop if undocumented consistency behavior must be assumed or any file modification is attempted.
