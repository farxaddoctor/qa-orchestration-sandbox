# Generic Resource Feature

## Confirmed requirements

- A user may create a resource with a required `name` and optional `description`.
- `name` accepts 1 through 80 characters after leading and trailing whitespace is removed.
- A successful create operation persists one resource and returns its generated `<RESOURCE_ID>`.
- A blank name or a name longer than 80 characters is rejected and no resource is persisted.
- A user may update the name or description of an existing resource.
- A user may archive an existing resource. Repeating archive on the same resource must not create a second state transition.
- A user without the required permission receives a denial and no mutation occurs.

## Constraints

- The fixture is synthetic and application-agnostic.
- The supported interfaces and exact validation message text are not specified.
- Concurrency behavior and restoration after archive are not specified.

## Requested analysis

Produce a risk-based test plan with positive, negative, boundary, permission, state-transition, data-integrity, and regression coverage. Separate confirmed behavior from assumptions and open questions. Do not create automation code.
