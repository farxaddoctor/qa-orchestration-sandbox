# Synthetic Automation Project Structure

```text
automation/
  fixtures/
    resource-fixture.ts       # shared by multiple suites
    session-fixture.ts        # shared authentication behavior
  pages/
    resource-page.ts
  tests/
    create-resource.spec.ts
    archive-resource.spec.ts
  support/
    cleanup.ts                # shared cleanup utility
  playwright.config.ts        # global test configuration
```

## Audit context

- The audit is read-only and has no proposed edit scope.
- Shared fixtures and cleanup utilities have multiple downstream consumers.
- A future change to a shared fixture, Page Object, or cleanup utility would affect framework behavior.
- A future change to global configuration, dependencies, authentication/session behavior, file deletion, or destructive cleanup would affect broader trust boundaries.
- No implementation evidence, dependency manifest, or consumer count beyond the notes above is supplied.
