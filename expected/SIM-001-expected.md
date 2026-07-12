# SIM-001 Expected Routing

| Decision | Expected value |
| --- | --- |
| Command | `commands/qa-design.md` |
| Constitution | `constitution/qa-agent-constitution.md` applied before routing |
| Policies | `policies/no-product-specific-leakage.md`; `policies/human-gate-policy.md` |
| Workflow | `workflows/requirement-to-test-plan.md` |
| Primary agent | `agents/test-designer.md` |
| Supporting agents | None |
| Skills | `skills/qa-test-design/SKILL.md` |
| Audit decision | Audit before edit is not required because no edit or implementation handoff occurs |
| Human Gate decision | Not required; Level 0 |
| Final status | `COMPLETED` |
| Expected artifact | Read-only test-design summary, scenario matrix, risks, test levels, assumptions, and open questions |

Stop if an undocumented behavior would be presented as confirmed or any file modification is attempted.
