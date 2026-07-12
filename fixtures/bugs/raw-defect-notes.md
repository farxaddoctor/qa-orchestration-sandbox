# Raw Synthetic Defect Notes

- Summary: Archiving a resource can leave it visible in an active-resource result.
- Preconditions: A resource exists with `<RESOURCE_ID>` and is active.
- Steps: Open the resource, request archive, confirm the action, then refresh the active-resource result.
- Expected: The archived resource is absent from the active-resource result.
- Actual: The archived resource remains visible until a later refresh.
- Frequency: 3 of 5 attempts.
- Evidence: A sanitized state response reports `archived`, while the active-resource result still includes `<RESOURCE_ID>`.
- Impact: A user may act on a resource that should no longer be active.
- Unknowns: Cache timing, documented consistency window, and the authoritative source for active state.
- Requested output: Structure an evidence-based bug report and recommend minimal regression coverage without asserting an unknown root cause.
