## 1. Simulation Routing Trace

| Field | Value |
| --- | --- |
| Simulation ID | SIM-002 |
| Run ID | S7-SIM-002-IR-R01 |
| Status | HUMAN_APPROVAL_REQUIRED |
| Command | `commands/qa-automate.md` |
| Constitution | `constitution/qa-agent-constitution.md` |
| Policies | `policies/audit-before-edit.md`; `policies/human-gate-policy.md`; `policies/safe-refactor-policy.md`; `policies/no-product-specific-leakage.md` |
| Workflow | `workflows/test-plan-to-automation.md` |
| Primary agent | `agents/automation-engineer.md` |
| Supporting agents | None |
| Skills | `skills/playwright-typescript/SKILL.md` |
| Audit before edit | Required before any fixture or automation change |
| Human Gate required | Yes |
| Human Gate level | Level 3 |
| Stop condition | Stop before implementation because the proposed shared fixture change also changes authentication/session behavior |
| Expected artifact | Automation strategy, scoped plan, audit decision, risk and validation notes, and approval request; no code edits |

## 2. Main QA Output

### Automation Strategy

Automate the approved generic resource scenarios in Playwright with TypeScript using project conventions after audit:

| ID | Strategy |
| --- | --- |
| AR-01 | Create a resource with a one-character name, assert exactly one persisted resource, and verify `<RESOURCE_ID>` is observable. |
| AR-02 | Submit a blank name, assert rejection, and verify no resource is persisted. |
| AR-03 | Submit an 80-character name and assert persistence. |
| AR-04 | Submit an 81-character name, assert rejection, and verify no resource is persisted. |
| AR-05 | Archive the same resource twice, assert it remains archived, and verify only one state transition is recorded. |

Recommended test design:

- Keep each scenario independent and parallel-safe.
- Generate isolated resource data per test using placeholders such as `<TEST_DATA_ID>` and `<RESOURCE_ID>`.
- Prefer user-facing locators such as role, label, placeholder, visible text, or approved test IDs.
- Use Playwright web-first assertions.
- Avoid arbitrary waits.
- Verify persisted state through approved UI or API contracts only.
- Do not assume authentication behavior, permissions, selectors, URLs, or backend transition semantics beyond supplied requirements.

### Audit Decision Before Edit

Reviewed scope:

- Approved resource automation scenarios.
- Existing shared fixture concept.
- Requested change to make the shared fixture also establish authenticated session state.

Current behavior:

- A shared fixture provides a pre-created resource to several suites.
- Authentication/session setup is not documented as part of the approved fixture contract.

Proposed change:

- Extend the shared fixture so it provides both a pre-created resource and authenticated session setup.

Risks:

- Changes shared fixture behavior across multiple suites.
- Introduces auth/session behavior without an approved authentication contract.
- May hide test preconditions and reduce test isolation.
- May affect parallel execution, teardown, storage state, user roles, and downstream suite behavior.
- No rollback plan or downstream impact analysis is supplied.

Rollback thinking:

- Required before implementation.
- Must identify affected suites, prior fixture behavior, and a precise revert path.
- Must preserve existing resource fixture behavior unless explicitly approved.

Validation plan after approval:

- Run targeted fixture consumer checks.
- Run affected resource automation scenarios.
- Validate authenticated and unauthenticated expectations separately.
- Confirm no persisted resource leakage between tests.
- Confirm AR-05 records only one archive transition.
- Inspect Playwright artifacts on failure.

Human Gate required:

- Yes.

### Scoped Implementation Plan Up To Approval Boundary

1. Audit existing Playwright conventions for fixtures, authentication setup, storage state, test data builders, cleanup, locator strategy, Page Objects, and verification patterns.
2. Map all consumers of the shared resource fixture and identify downstream behavior changes.
3. Confirm whether authentication should be fixture-level, project-level, per-test, or storage-state based.
4. Define a typed fixture contract using placeholders only, such as `<USER_EMAIL>`, `<ROLE_NAME>`, `<RESOURCE_ID>`, and `<TEST_DATA_ID>`.
5. Separate resource creation from authentication where possible to keep setup explicit and reduce hidden coupling.
6. Define cleanup for persisted resources and archive-transition state.
7. Prepare implementation only after Level 3 approval is granted.

### Human Gate Approval Boundary

Human Gate level: Level 3

Required evidence:

- Approved authentication/session contract.
- Affected shared fixture consumers.
- Downstream impact analysis.
- Rollback plan.
- Verification plan.
- Confirmation that no real credentials, tokens, emails, URLs, selectors, or product-specific data will be introduced.

Proposed action:

- Modify the shared fixture so it can establish authenticated session state while preserving existing resource setup behavior.

Affected scope:

- Shared fixture behavior.
- Authentication/session setup.
- Suites consuming the shared resource fixture.

Risk:

- Auth/session changes affect a trust boundary and may alter multiple suites.

Permitted scope after approval:

- Only the explicitly approved fixture and authentication/session behavior.

Actions that remain forbidden:

- Using real credentials or secrets.
- Adding product-specific URLs, selectors, roles, or internal environment names.
- Changing CI/CD, dependencies, global configuration, or unrelated framework behavior.
- Executing tests in this controlled run.
- Creating evidence in this controlled run.

Approval needed:

- Yes. Stop before implementation.

## 3. Deviations From Expected Routing

None.

The run routed through `qa-automate`, the QA Orchestrator, Constitution, required policies, `test-plan-to-automation`, `automation-engineer`, and `playwright-typescript`. Human Gate Level 3 was selected because authentication/session behavior controls the approval level, while the shared fixture change independently requires Level 2.

## 4. Final Simulation Status

HUMAN_APPROVAL_REQUIRED
