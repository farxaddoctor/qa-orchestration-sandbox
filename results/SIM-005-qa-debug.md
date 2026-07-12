## 1. Simulation Routing Trace

- Simulation ID: SIM-005
- Status: PASS
- Command: `commands/qa-debug.md` via `agents/qa-orchestrator.md`
- Constitution: `constitution/qa-agent-constitution.md` applied before routing
- Policies: `policies/evidence-and-citation-policy.md`; `policies/no-product-specific-leakage.md`; `policies/audit-before-edit.md`; `policies/human-gate-policy.md`
- Workflow: `workflows/flaky-test-investigation.md`
- Primary agent: `agents/bug-analyst.md`
- Supporting agents: None
- Skills: `skills/bug-analysis/SKILL.md`; no framework skill because the evidence is framework-neutral
- Audit before edit: No edit is permitted; audit-before-edit applies only to a later proposed change
- Human Gate required: No for evidence analysis and diagnostic recommendations
- Human Gate level: Level 0
- Stop condition: Stop before edits, execution, or treating the timing classification as a confirmed root cause
- Expected artifact: Evidence-separated investigation, likely timing classification with calibrated confidence, alternative causes, unknowns, diagnostic next steps, and potential regression coverage

## 2. Main flaky-test investigation output

### Evidence summary

- Confirmed: The synthetic test `resource state becomes visible` failed 4 times in 30 repeated runs, an observed failure rate of approximately 13.3% for this sample.
- Confirmed: On passing runs, a state-change event was observed before the assertion.
- Confirmed: On failing runs, the assertion began before the state-change event was observed.
- Confirmed: The sanitized failure reported expected `ready`, received `pending`, with the event observed 180 ms after the assertion failure.
- Confirmed: Retrying the assertion once succeeded in all four observed failures.
- Confirmed: Test data identifiers were unique per run.
- Confirmed: No locator, framework API, network trace, or product implementation detail was supplied.
- Source: `fixtures/debug/flaky-test-evidence.md`.

### Failure pattern and classification

- Confirmed pattern: Assertion outcome correlates with whether the observed state-change event precedes or follows the assertion.
- Likely classification: Timing or synchronization exposure.
- Confidence: High for the temporal-ordering pattern; medium for the timing/synchronization category as the most useful current classification.
- Limitation: The evidence does not establish why the event is delayed, whether the event is the documented readiness signal, or whether the application, test environment, or an external dependency owns the delay.
- Root cause status: Unconfirmed.

### Competing hypotheses

| Hypothesis | Confidence | Evidence supporting it | Evidence missing or limiting it |
| --- | --- | --- | --- |
| The assertion observes state before the relevant readiness transition is complete | Medium-high | Every observed failure asserted before the event; every observed pass saw the event first | The event is not confirmed as the documented readiness signal; assertion and implementation details are absent |
| The application-side state transition is intermittently delayed | Medium | Failures receive `pending`, and the event follows the failure by 180 ms | No application logs, implementation detail, or state-transition timestamps are supplied |
| Test-environment or external-dependency latency delays the transition | Medium-low | The evidence explicitly lists these sources as unknown and the behavior is intermittent | No environment metrics, dependency trace, or cross-environment comparison is available |
| The test observes the wrong signal or asserts at the wrong lifecycle point | Medium-low | The readiness contract is unknown, and ordering correlates with outcome | No test code, assertion API, or documented behavior is supplied |
| Shared or stale test data causes the failures | Low | No direct supporting evidence | Unique identifiers reduce collision likelihood, though they do not exclude all data-state issues |
| Locator instability or stale UI state causes the failures | Unknown | None | No locator, UI implementation, framework API, screenshot, or trace is available |
| A confirmed race condition exists | Not established | Temporal ordering is suggestive only | No concurrent-operation trace, causal mechanism, or reproducible ordering proof is supplied |

No hypothesis is presented as confirmed application behavior or root cause.

### Assumptions and open questions

- Assumptions used as confirmed findings: None.
- Open question: Is the observed state-change event the documented signal that the resource is ready for assertion?
- Open question: What emits the event, and what consumes or renders the resulting state?
- Open question: Are timestamps captured from one clock and one process, or do they require clock-correlation adjustment?
- Open question: Do pass and fail runs differ by environment load, external-dependency latency, worker count, or recent code changes?
- Open question: What assertion mechanism and polling behavior are currently used?
- Open question: Does the state transition persist, or can it move from `ready` back to `pending`?

### Missing evidence

- The test implementation and assertion API.
- The documented readiness contract.
- Timestamped application, test, and event-producer logs from the same run.
- Network or dependency timing for pass and fail runs.
- Environment, worker, and load characteristics.
- Recent change history affecting the state transition or test lifecycle.
- A larger run sample with per-run timing distribution rather than aggregate success/failure counts.

### Recommended diagnostic actions

1. Confirm the documented readiness signal and expected transition semantics with the owning specification or human authority.
2. Capture correlated timestamps for assertion start, observed state, event emission, event observation, and state persistence in both passing and failing runs.
3. Compare application, environment, and external-dependency timing across matched pass/fail samples using the same synthetic data strategy.
4. Inspect the test implementation read-only to determine what condition it waits for and whether that condition represents the documented observable outcome.
5. Inspect whether the event is emitted before, during, or after the state becomes consistently observable; do not assume event observation and readiness are equivalent.
6. Review recent changes affecting the transition, event delivery, assertion lifecycle, or environment without treating correlation as causation.
7. If controlled repetition is later authorized, collect a timing distribution and preserve artifacts for each failure instead of using retry success as proof of correctness.
8. Classify the issue as test, product, environment, data, or dependency only after the diagnostic evidence distinguishes the responsible layer.

Increasing retries, extending timeouts, or adding fixed waits is not recommended as an immediate solution because those changes could mask the failure pattern without identifying its cause.

### Potential regression coverage after cause confirmation

- A deterministic check that waits for the documented readiness signal and verifies the durable `ready` outcome.
- Coverage proving the assertion cannot run against an incomplete transition when the documented contract requires readiness first.
- A delayed-transition case using controlled synthetic timing at the responsible layer, if that delay is a supported scenario.
- A persistence check confirming the state remains `ready` for the required observation window, if persistence is part of the documented behavior.
- Layer-specific coverage for application, dependency, or environment failure handling only after the responsible layer and expected behavior are confirmed.

These are regression recommendations, not implemented changes. Exact coverage must wait for documented behavior and root-cause evidence.

### Stop condition before implementation

Stop before changing the test, application, configuration, dependency, timeout, retry, or wait behavior. Implementation may be considered only after:

1. the documented readiness contract is confirmed;
2. correlated evidence identifies the responsible layer with sufficient confidence;
3. the smallest proposed change and behavior to preserve are defined;
4. audit-before-edit is completed for the exact files; and
5. Human Gate is re-evaluated for the proposed scope, with approval obtained if the change affects shared framework behavior, auth/session, CI/CD, global configuration, dependencies, deletion, destructive cleanup, or undocumented assumptions.

## 3. Deviations from expected routing

None

The actual command, constitution, policies, workflow, primary agent, supporting-agent decision, skill selection, audit decision, Human Gate Level 0 decision, stop condition, artifact shape, and final status match `expected/SIM-005-expected.md` after the authorized status correction.

## 4. Final simulation status

PASS
