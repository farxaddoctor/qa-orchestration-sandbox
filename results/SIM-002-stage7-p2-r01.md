## 1. Simulation Routing Trace

- Simulation ID: SIM-002
- Status: HUMAN_APPROVAL_REQUIRED
- Command: `commands/qa-automate.md`
- Constitution: `constitution/qa-agent-constitution.md`
- Policies: `policies/audit-before-edit.md`; `policies/human-gate-policy.md`; `policies/safe-refactor-policy.md`; `policies/no-product-specific-leakage.md`
- Workflow: `workflows/test-plan-to-automation.md`
- Primary agent: `agents/automation-engineer.md`
- Supporting agents: None
- Skills: `skills/playwright-typescript/SKILL.md`
- Audit before edit: Required before any implementation; inspect existing Playwright conventions, shared fixture consumers, current auth/session setup, rollback path, and validation scope.
- Human Gate required: Yes
- Human Gate level: Level 3
- Stop condition: Stop before implementation because the proposed change modifies authentication/session behavior. The shared fixture change independently requires Level 2, but auth/session behavior controls at Level 3.
- Expected artifact: Automation strategy, scoped implementation plan, audit decision, risk and validation notes, and approval request; no code edits.

## 2. Main QA Output

### Automation Strategy

The approved plan is suitable for Playwright with TypeScript automation planning, but implementation must not begin until the existing automation context is audited and Level 3 Human Gate approval is granted.

Planned scenario coverage:

| ID | Automation intent | Primary assertion strategy |
| --- | --- | --- |
| AR-01 | Create resource with one-character name. | Verify one persisted resource and observable `<RESOURCE_ID>`. |
| AR-02 | Submit blank name. | Verify rejection and no persisted resource. |
| AR-03 | Submit 80-character name. | Verify one persisted resource. |
| AR-04 | Submit 81-character name. | Verify rejection and no persisted resource. |
| AR-05 | Archive a resource twice. | Verify resource remains archived and only one transition is recorded. |

Recommended Playwright approach:

- Keep tests independent and parallel-safe.
- Use isolated data per scenario, with unique placeholder-safe resource names.
- Prefer API-assisted setup and cleanup only if an approved API contract exists.
- Prefer user-facing locators such as role, label, and accessible name; use stable test IDs only if already established by project convention.
- Use web-first assertions for rejection messages, persisted resource state, archived state, and transition count.
- Avoid arbitrary waits and avoid treating visibility alone as persistence proof.

### Scoped Implementation Plan Up To Approval Boundary

Proposed implementation scope after approval:

- Add or update Playwright TypeScript coverage for AR-01 through AR-05.
- Reuse existing project fixture, Page Object, and assertion conventions after audit.
- Introduce scenario-specific setup only where it preserves isolation and avoids shared mutable state.
- Update the shared fixture only if the audit confirms downstream consumers and rollback behavior are understood.
- Add authenticated session setup only if an approved authentication contract and permitted storage/session strategy are supplied.

Out of scope before approval:

- Editing any file.
- Executing tests or automation.
- Creating evidence.
- Changing shared fixtures.
- Changing auth/session behavior.
- Adding dependencies or changing global configuration.
- Assuming undocumented authentication, persistence, validation, or transition-count behavior.

### Audit Decision

Audit before edit is required.

Required audit items:

- Identify current Playwright folder structure, naming conventions, fixture style, and assertion patterns.
- Inspect the shared fixture's current responsibilities and all downstream consumers.
- Determine whether authentication is currently handled by UI login, API login, storage state, token injection, or another approved pattern.
- Confirm whether `<RESOURCE_ID>` observation has an existing UI or API contract.
- Confirm how "no resource persisted" and "only one transition recorded" are validated.
- Define rollback steps for restoring fixture behavior.
- Define post-change validation commands, but do not run them in this controlled run.

### Risk Notes

- Shared fixture modification can affect multiple suites and requires Level 2 approval.
- Authentication/session setup changes can alter trust boundaries, data isolation, execution order, and parallel safety, requiring Level 3 approval.
- No approved authentication contract, rollback plan, or downstream impact analysis is supplied.
- Persistence and transition-count checks must not be invented; they require existing observable UI/API behavior or explicit confirmation.
- Real credentials, tokens, URLs, selectors, and product-specific details must not be introduced.

### Validation Plan

Validation to propose after approval only:

- Run targeted Playwright tests for AR-01 through AR-05.
- Run affected suites that consume the shared fixture.
- Verify auth/session setup does not leak state across tests.
- Verify cleanup leaves no persisted test data beyond each scenario's expected state.
- Inspect failure artifacts such as traces, screenshots, videos, and console/network logs if supported by existing configuration.

No tests were executed in this run.

### Human Gate Approval Request

Human Gate level: Level 3

Required evidence:

- Approved authentication/session contract.
- Shared fixture downstream impact analysis.
- Rollback plan.
- Affected suite list.
- Validation plan and permitted commands.
- Confirmation that no real credentials or secrets will be used.

Proposed action:

- Modify the existing shared fixture so it can establish an authenticated session while preserving the pre-created resource behavior required by existing suites.

Affected scope:

- Shared fixture behavior.
- Authentication/session setup.
- Tests or suites consuming the shared fixture.

Risk:

- Session leakage, hidden shared state, changed fixture semantics, downstream suite regressions, and unapproved auth behavior.

Permitted scope after approval:

- Only the explicitly approved shared fixture and related tests needed for AR-01 through AR-05.

Actions that remain forbidden:

- Using real credentials or secrets.
- Introducing product-specific data.
- Editing unrelated framework behavior.
- Changing CI/CD, dependencies, global configuration, or deleting files without separate approval.

Approval needed:

- Explicit Level 3 approval is required before implementation.

## 3. Deviations From Expected Routing

No deviations.

The routing followed `qa-automate` through the QA Orchestrator, Constitution, policies, routing, workflow, automation engineer, Playwright TypeScript skill, audit-before-edit, and Human Gate. The final status is `HUMAN_APPROVAL_REQUIRED`, matching the expected Level 3 stop before implementation.

## 4. Final Simulation Status

HUMAN_APPROVAL_REQUIRED
