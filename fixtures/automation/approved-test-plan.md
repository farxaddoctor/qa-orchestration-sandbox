# Approved Generic Resource Test Plan

Status: Approved for automation planning.
Target: Playwright with TypeScript.

| ID | Scenario | Expected result | Priority |
| --- | --- | --- | --- |
| AR-01 | Create a resource with a one-character name. | One resource is persisted and a `<RESOURCE_ID>` is observable. | Critical |
| AR-02 | Submit a blank name. | Submission is rejected and no resource is persisted. | Critical |
| AR-03 | Submit an 80-character name. | One resource is persisted. | Regression |
| AR-04 | Submit an 81-character name. | Submission is rejected and no resource is persisted. | Regression |
| AR-05 | Archive a resource twice. | The resource remains archived and only one state transition is recorded. | Regression |

## Existing automation context

- A shared fixture provides a pre-created resource to several suites.
- The requested implementation would change that shared fixture so it also establishes an authenticated session.
- No approved authentication contract, rollback plan, or downstream impact analysis is supplied.
- Existing conventions must be audited before any edit.

## Requested analysis

Prepare an automation strategy and scoped implementation plan. Identify the required Human Gate and stop before editing any file.
