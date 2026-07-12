# SIM-005 Expected Routing

| Decision | Expected value |
| --- | --- |
| Command | `commands/qa-debug.md` |
| Constitution | `constitution/qa-agent-constitution.md` applied before routing |
| Policies | `policies/evidence-and-citation-policy.md`; `policies/no-product-specific-leakage.md`; `policies/audit-before-edit.md`; `policies/human-gate-policy.md` |
| Workflow | `workflows/flaky-test-investigation.md` |
| Primary agent | `agents/bug-analyst.md` |
| Supporting agents | None |
| Skills | `skills/bug-analysis/SKILL.md`; no framework skill because the evidence is framework-neutral |
| Audit decision | No edit is permitted; audit-before-edit applies only to a later proposed change |
| Human Gate decision | Not required; Level 0 for evidence analysis and diagnostic recommendations |
| Final status | `PASS` |
| Expected artifact | Evidence-separated investigation, likely timing classification with calibrated confidence, alternative causes, unknowns, and diagnostic next steps |

Stop before edits, execution, or treating the timing classification as confirmed root cause.
