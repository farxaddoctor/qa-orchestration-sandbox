## 1. Simulation Routing Trace

- Simulation ID: SIM-003
- Status: PASS
- Command: `commands/qa-review.md` via `agents/qa-orchestrator.md`
- Constitution: `constitution/qa-agent-constitution.md` applied before routing
- Policies: `policies/audit-before-edit.md`; `policies/human-gate-policy.md`; `policies/safe-refactor-policy.md`; `policies/no-product-specific-leakage.md`
- Workflow: `workflows/automation-review.md`
- Primary agent: `agents/qa-code-reviewer.md`
- Supporting agents: None
- Skills: Primary: `skills/qa-code-review/SKILL.md`; supporting: `skills/playwright-typescript/SKILL.md`
- Audit before edit: Read-only inspection required; no edit audit or implementation is permitted
- Human Gate required: No
- Human Gate level: Level 0
- Stop condition: Stop after producing the review artifact; do not modify, rewrite, format, execute, refactor, or fix the reviewed file
- Expected artifact: Findings-first review ordered by severity, with evidence, impact, fix direction, missing coverage, and residual risk

## 2. Main QA review output

### Major — The assertion does not prove the saved resource is shown

- Confirmed finding: Line 12 retrieves raw text and checks only whether it is truthy. It does not verify a specific resource or its saved state.
- Evidence: `fixtures/review/unstable-example.spec.ts:12`
- Risk: Unrelated non-empty text could satisfy the assertion. The primitive assertion also lacks Playwright's web-first retry behavior for the expected content.
- Recommendation: Assert a documented, uniquely identified resource and its expected user-observable saved state using a web-first locator assertion.
- Missing coverage: Resource identity and persistence are not demonstrated.
- Residual risk: Multiple selector matches may produce strict-mode ambiguity rather than a meaningful behavioral failure.
- Safe to change now: No; the expected resource identity is unspecified, and this simulation is review-only.

### Major — The flow depends on uncontrolled existing state

- Confirmed finding: Lines 7–10 count existing rows and conditionally click the first match. No deterministic resource setup is present in the supplied test.
- Evidence: `fixtures/review/unstable-example.spec.ts:7` through `fixtures/review/unstable-example.spec.ts:10`
- Risk: The exercised path depends on existing data and ordering. The action can be skipped without an explicit precondition assertion.
- Recommendation: Arrange isolated synthetic data, assert that the intended resource exists, and interact with that specific resource.
- Missing coverage: Empty-state behavior, unique selection, data isolation, and parallel safety are not established.
- Residual risk: Environmental data differences may cause failures unrelated to the intended behavior.
- Safe to change now: No; setup and cleanup contracts were not supplied.

### Major — Fixed-delay synchronization creates flake risk

- Confirmed finding: Line 5 uses `page.waitForTimeout(2000)`.
- Evidence: `fixtures/review/unstable-example.spec.ts:5`
- Risk: The fixed delay always slows the test but cannot guarantee readiness when loading takes longer.
- Recommendation: Synchronize on a documented user-visible state or the specific navigation/network event indicating readiness.
- Missing coverage: No readiness condition is explicitly verified.
- Residual risk: Runtime behavior remains timing-dependent across environments.
- Safe to change now: No; the correct readiness signal is undocumented.

### Confirmed facts, assumptions, and open questions

- Confirmed: Only `fixtures/review/unstable-example.spec.ts` was reviewed.
- Confirmed: The fixture was not executed or modified.
- Confirmed: `<BASE_URL>` and `<SELECTOR>` are permitted synthetic placeholders.
- Confirmed: No secret or product-specific information was present.
- Assumptions presented as findings: None.
- Open question: What resource identity and observable state define “saved”?
- Open question: What stable locator contract should the consuming project use?
- Open question: Is persistence across navigation or reload required?
- Open question: What deterministic setup and cleanup mechanism is available?
- Verification evidence: No runtime evidence was generated because execution was prohibited.

## 3. Deviations from expected routing

None

The actual command, constitution, policies, workflow, primary agent, supporting-agent decision, skills, audit decision, Human Gate Level 0 decision, stop condition, artifact shape, and final status match `expected/SIM-003-expected.md`.

## 4. Final simulation status

PASS
