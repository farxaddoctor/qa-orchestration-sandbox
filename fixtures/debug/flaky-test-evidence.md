# Synthetic Flaky Test Evidence

## Confirmed observations

- Test: `resource state becomes visible`.
- Frequency: 4 failures in 30 repeated runs.
- On passing runs, a state-change event is observed before the assertion.
- On failing runs, the assertion starts before the state-change event is observed.
- Retrying the assertion once succeeds in all four observed failures.
- Test data identifiers are unique per run.
- No locator, framework API, network trace, or product implementation detail is available.

## Sanitized failure excerpt

```text
Expected: "ready"
Received: "pending"
Event observed 180 ms after assertion failure
```

## Unknowns

- Whether the delay originates in the application, test environment, or an external dependency.
- Whether the state-change event is the documented readiness signal.
- Whether recent changes affected timing.
