# Exam Score Validation Test Plan

## 1. Objective and scope

### Objective

Verify that exam scores are validated against the configured maximum at both the UI and API layers, that the inclusive boundaries are handled correctly, and that rejected create or update operations do not persist an invalid score.

### In scope

- Score entry through the UI.
- Score submission directly through the API.
- Inclusive validation from `0` through the configured maximum.
- Rejection of negative scores and scores above the configured maximum.
- Invalid create and invalid update persistence checks.
- Consistency between UI and API outcomes.
- Observable validation feedback without prescribing exact message text, API status codes, or response schemas.

This document contains test design only. It does not contain executable tests.

## 2. Confirmed requirements

| ID | Confirmed requirement |
| --- | --- |
| REQ-01 | Every exam has a configured maximum score. |
| REQ-02 | A teacher may enter a score from `0` through the configured maximum, inclusive. |
| REQ-03 | Negative scores must be rejected. |
| REQ-04 | Scores above the configured maximum must be rejected. |
| REQ-05 | Score validation must exist at the UI layer. |
| REQ-06 | Score validation must exist at the API layer. |
| REQ-07 | Invalid scores must not be persisted. |
| REQ-08 | Exact validation-message text is not specified and must not be prescribed by this plan. |

## 3. Assumptions and open questions

### Assumptions

| ID | Assumption |
| --- | --- |
| ASM-01 | Tests use synthetic exams, users, and score records in an isolated test environment. |
| ASM-02 | A create scenario begins with no score for the selected synthetic teacher and exam; an update scenario begins with a known valid persisted score. |
| ASM-03 | A trusted read mechanism is available to verify persisted state independently of the UI submission response. |
| ASM-04 | The configured maximum remains unchanged during an individual test unless a future requirement explicitly covers configuration changes. |
| ASM-05 | UI rejection provides observable validation feedback, but the wording, placement, and presentation are not asserted. |
| ASM-06 | API rejection provides an observable failure signal, but the status code and response schema are not asserted until an API contract is supplied. |
| ASM-07 | All fields unrelated to the score contain otherwise valid synthetic values. |
| ASM-08 | Integer values in this plan are synthetic boundary examples only; they do not imply that decimal scores are unsupported. |
| ASM-09 | A successfully accepted score entry persists the accepted value. This is a test-design assumption, not a confirmed requirement. |

### Open questions

1. Are scores restricted to integers, or are decimals supported?
2. If decimals are supported, what precision, scale, and rounding rules apply?
3. What values are allowed when configuring an exam's maximum score?
4. Can a configured maximum be zero or decimal?
5. What happens to existing scores if the configured maximum is reduced?
6. Are empty, whitespace, non-numeric, scientific-notation, `NaN`, or extremely large values in scope?
7. Does UI validation occur during entry, on blur, or only on submission?
8. Does the UI prevent invalid input, or accept it and reject the submission?
9. What API failure status and response contract represent validation rejection?
10. Must UI and API error categories be identical, or only their accept/reject behavior?
11. Are bulk score entry and bulk update in scope?
12. Are concurrent score updates or maximum-score changes in scope?
13. Are authorization checks for users other than the teacher in scope?
14. Are audit events required for accepted or rejected score submissions?
15. Are validation messages localized or subject to accessibility requirements?

## 4. Risk analysis

| Risk | Impact | Priority | Planned mitigation |
| --- | --- | --- | --- |
| Off-by-one validation at `0` or the configured maximum | Valid boundary scores are rejected or invalid scores are accepted | Critical | Boundary tests at `0`, maximum, below minimum, and above maximum |
| UI and API apply different rules | Direct API calls bypass UI protection or users see inconsistent behavior | Critical | Repeat core partitions at both layers and add cross-layer checks |
| Invalid create is persisted | Corrupt score data is introduced | Critical | Verify absence using an independent persistence read |
| Invalid update overwrites a valid value | Existing valid data is lost or corrupted | Critical | Capture the original value and confirm it is unchanged after rejection |
| Wrong exam maximum is used | Scores are validated against another exam's configuration | High | Test two synthetic exams with different configured maxima |
| Tests prescribe an undocumented error contract | Brittle or misleading test expectations | High | Assert rejection and non-persistence without exact UI text, API code, or schema |
| Numeric type or precision is assumed | Decimal behavior is incorrectly represented as confirmed | Medium | Keep integer data explicitly synthetic and defer decimal assertions |

## 5. Test-design techniques

- **Equivalence partitioning:** valid scores, negative scores, and scores above the configured maximum.
- **Boundary-value analysis:** below minimum, minimum `0`, configured maximum, and above maximum.
- **Decision-table testing:** layer, operation type, score partition, and persistence outcome.
- **Negative testing:** invalid create and update requests through UI and API.
- **State verification:** compare persistence state before and after an invalid update.
- **Cross-layer consistency testing:** confirm the UI and API enforce the same confirmed range.
- **Requirement traceability:** map scenarios and prioritized tests back to `REQ-01` through `REQ-08` or to an explicit assumption.

## 6. Equivalence partitions

Let `M` be the configured maximum for the selected exam.

| Partition | Representative data | Classification | Expected behavior | Basis |
| --- | --- | --- | --- | --- |
| Score below minimum | `-1` | Invalid | Reject at UI and API; do not persist | REQ-03, REQ-05, REQ-06, REQ-07 |
| Minimum score | `0` | Valid | Accept, subject to otherwise valid input | REQ-02 |
| Interior score | A value where `0 < score < M` | Valid | Accept, subject to otherwise valid input | REQ-02 |
| Configured maximum | `M` | Valid | Accept | REQ-02 |
| Score above maximum | `M + 1` | Invalid | Reject at UI and API; do not persist | REQ-04, REQ-05, REQ-06, REQ-07 |
| Decimal score | Example: `M / 2` when non-integral | Undetermined | Do not assert until numeric rules are confirmed | ASM-08; open questions 1-2 |
| Non-numeric or empty input | Synthetic invalid-form examples | Undetermined | Do not assert until input-format rules are confirmed | Open question 6 |

## 7. Boundary matrix

For illustration only, use synthetic exam `EXAM-SYN-A` with `M = 100`. These integer examples do not establish an integer-only product rule.

| Boundary | Synthetic score | UI expectation | API expectation | Persistence expectation | Mapping |
| --- | ---: | --- | --- | --- | --- |
| Below minimum | `-1` | Reject with observable validation feedback; exact text unspecified | Reject through the API's validation mechanism; exact code/schema unspecified | No new invalid score; existing valid score remains unchanged for update | REQ-03, REQ-05, REQ-06, REQ-07, REQ-08 |
| Minimum | `0` | Accept when other input is valid | Accept when other input is valid | `0` may be persisted | REQ-02, REQ-05, REQ-06 |
| Configured maximum | `100` | Accept when other input is valid | Accept when other input is valid | `100` may be persisted | REQ-01, REQ-02, REQ-05, REQ-06 |
| Above configured maximum | `101` | Reject with observable validation feedback; exact text unspecified | Reject through the API's validation mechanism; exact code/schema unspecified | No new invalid score; existing valid score remains unchanged for update | REQ-04, REQ-05, REQ-06, REQ-07, REQ-08 |

## 8. UI validation scenarios

| ID | Scenario | Preconditions | Action | Expected result | Mapping |
| --- | --- | --- | --- | --- | --- |
| UI-01 | Create score at minimum | Synthetic exam has maximum `M`; no existing score | Enter `0` and submit | UI accepts the score; persisted score may be verified as `0` | REQ-01, REQ-02, REQ-05; ASM-02, ASM-03, ASM-09 |
| UI-02 | Create score at maximum | Synthetic exam has maximum `M`; no existing score | Enter `M` and submit | UI accepts the score; persisted score may be verified as `M` | REQ-01, REQ-02, REQ-05; ASM-02, ASM-03, ASM-09 |
| UI-03 | Create interior valid score | Synthetic exam has maximum `M`; no existing score | Enter a value strictly between `0` and `M`; submit | UI accepts the score | REQ-02, REQ-05; ASM-02 |
| UI-04 | Reject negative create | No existing score | Enter `-1` and attempt submission | UI rejects the operation, provides observable feedback, and does not create an invalid score | REQ-03, REQ-05, REQ-07, REQ-08; ASM-03, ASM-05 |
| UI-05 | Reject above-maximum create | No existing score | Enter `M + 1` and attempt submission | UI rejects the operation, provides observable feedback, and does not create an invalid score | REQ-04, REQ-05, REQ-07, REQ-08; ASM-03, ASM-05 |
| UI-06 | Reject negative update | A valid score is already persisted | Replace it with `-1` and attempt submission | UI rejects the update; the original persisted score remains unchanged | REQ-03, REQ-05, REQ-07; ASM-02, ASM-03, ASM-05 |
| UI-07 | Reject above-maximum update | A valid score is already persisted | Replace it with `M + 1` and attempt submission | UI rejects the update; the original persisted score remains unchanged | REQ-04, REQ-05, REQ-07; ASM-02, ASM-03, ASM-05 |
| UI-08 | Use the selected exam's maximum | Two synthetic exams have different maxima | Enter the same score for both exams where it is valid for one and above maximum for the other | Each result is evaluated against its own exam's configured maximum | REQ-01, REQ-02, REQ-04, REQ-05; ASM-04 |
| UI-09 | Validate without exact-text coupling | An invalid score is entered | Submit the invalid score | An observable validation indication exists; the test does not require literal message text | REQ-05, REQ-08; ASM-05 |

UI scenario count: **9**.

## 9. API validation scenarios

| ID | Scenario | Preconditions | Action | Expected result | Mapping |
| --- | --- | --- | --- | --- | --- |
| API-01 | Create score at minimum | Synthetic exam has maximum `M`; no existing score | Submit `0` through the API | Request is accepted according to the documented contract; `0` may be persisted | REQ-01, REQ-02, REQ-06; ASM-02, ASM-03, ASM-06, ASM-09 |
| API-02 | Create score at maximum | Synthetic exam has maximum `M`; no existing score | Submit `M` through the API | Request is accepted according to the documented contract; `M` may be persisted | REQ-01, REQ-02, REQ-06; ASM-02, ASM-03, ASM-06, ASM-09 |
| API-03 | Create interior valid score | Synthetic exam has maximum `M`; no existing score | Submit a value strictly between `0` and `M` | Request is accepted according to the documented contract | REQ-02, REQ-06; ASM-02, ASM-06 |
| API-04 | Reject negative create | No existing score | Submit `-1` directly through the API | API rejects the operation without prescribing a status code or schema; no invalid score is created | REQ-03, REQ-06, REQ-07, REQ-08; ASM-03, ASM-06 |
| API-05 | Reject above-maximum create | No existing score | Submit `M + 1` directly through the API | API rejects the operation without prescribing a status code or schema; no invalid score is created | REQ-04, REQ-06, REQ-07, REQ-08; ASM-03, ASM-06 |
| API-06 | Reject negative update | A valid score is already persisted | Submit an update containing `-1` | API rejects the update; the original persisted score remains unchanged | REQ-03, REQ-06, REQ-07; ASM-02, ASM-03, ASM-06 |
| API-07 | Reject above-maximum update | A valid score is already persisted | Submit an update containing `M + 1` | API rejects the update; the original persisted score remains unchanged | REQ-04, REQ-06, REQ-07; ASM-02, ASM-03, ASM-06 |
| API-08 | Use the target exam's maximum | Two synthetic exams have different maxima | Submit the same score for both exams where it is valid for one and invalid for the other | Each request is evaluated against the corresponding exam's configured maximum | REQ-01, REQ-02, REQ-04, REQ-06; ASM-04 |
| API-09 | UI-bypass/API enforcement | A direct API submission path is available | Submit an invalid score directly to the API without prior UI interaction | API independently enforces score validation and does not persist the invalid value; this scenario specifically proves that UI validation cannot be bypassed | REQ-03, REQ-04, REQ-06, REQ-07; ASM-03, ASM-06 |

API scenario count: **9**.

## 10. Invalid-score persistence checks

| ID | Operation | Invalid data | Verification | Expected persisted state | Mapping |
| --- | --- | --- | --- | --- | --- |
| PERSIST-01 | Create | `-1` | Query using a trusted read mechanism after UI or API rejection | No score record containing `-1` exists for the synthetic teacher and exam | REQ-03, REQ-07; ASM-02, ASM-03 |
| PERSIST-02 | Create | `M + 1` | Query using a trusted read mechanism after UI or API rejection | No score record containing `M + 1` exists for the synthetic teacher and exam | REQ-04, REQ-07; ASM-02, ASM-03 |
| PERSIST-03 | Update | Existing valid score changed to `-1` | Capture the original value; attempt update; read again | Original valid score remains unchanged; `-1` is not persisted | REQ-03, REQ-07; ASM-02, ASM-03 |
| PERSIST-04 | Update | Existing valid score changed to `M + 1` | Capture the original value; attempt update; read again | Original valid score remains unchanged; `M + 1` is not persisted | REQ-04, REQ-07; ASM-02, ASM-03 |

Persistence scenario count: **4**.

## 11. Cross-layer consistency scenarios

| ID | Scenario | Expected result | Mapping |
| --- | --- | --- | --- |
| XL-01 | Submit `0` through UI and API for equivalent isolated records | Both layers accept the minimum boundary | REQ-02, REQ-05, REQ-06 |
| XL-02 | Submit `M` through UI and API for equivalent isolated records | Both layers accept the maximum boundary | REQ-01, REQ-02, REQ-05, REQ-06 |
| XL-03 | Submit `-1` through UI and API | Both layers reject it; neither persists it | REQ-03, REQ-05, REQ-06, REQ-07 |
| XL-04 | Submit `M + 1` through UI and API | Both layers reject it; neither persists it | REQ-04, REQ-05, REQ-06, REQ-07 |
| XL-05 | Bypass UI and submit an invalid score directly to the API | API enforcement remains effective independently of UI validation | REQ-03, REQ-04, REQ-06, REQ-07 |

## 12. Prioritized test cases

Priority definitions:

- **P0:** release-critical data-integrity or boundary validation.
- **P1:** important consistency, configuration, or contract-resilience coverage.

| ID | Priority | Level | Preconditions | Steps and synthetic data | Expected result | Mapping |
| --- | --- | --- | --- | --- | --- | --- |
| TC-001 | P0 | UI + integration | `EXAM-SYN-A` has `M = 100`; no score exists | Create score `0` in UI; read persisted state | UI accepts; persisted value is `0` | REQ-01, REQ-02, REQ-05; ASM-02, ASM-03, ASM-08, ASM-09 |
| TC-002 | P0 | UI + integration | Same as TC-001 with isolated data | Create score `100` in UI; read persisted state | UI accepts; persisted value is `100` | REQ-01, REQ-02, REQ-05; ASM-02, ASM-03, ASM-08, ASM-09 |
| TC-003 | P1 | UI | Same as TC-001 | Create score `50` in UI | UI accepts the interior value | REQ-02, REQ-05; ASM-08 |
| TC-004 | P0 | UI + integration | No score exists | Attempt to create `-1`; inspect persistence | UI rejects with non-literal validation feedback; no invalid record exists | REQ-03, REQ-05, REQ-07, REQ-08; ASM-03, ASM-05, ASM-08 |
| TC-005 | P0 | UI + integration | No score exists; `M = 100` | Attempt to create `101`; inspect persistence | UI rejects with non-literal validation feedback; no invalid record exists | REQ-04, REQ-05, REQ-07, REQ-08; ASM-03, ASM-05, ASM-08 |
| TC-006 | P0 | API + integration | No score exists; `M = 100` | Create score `0` through API; read persisted state | API accepts under its documented contract; persisted value is `0` | REQ-01, REQ-02, REQ-06; ASM-02, ASM-03, ASM-06, ASM-08, ASM-09 |
| TC-007 | P0 | API + integration | Same as TC-006 with isolated data | Create score `100` through API; read persisted state | API accepts under its documented contract; persisted value is `100` | REQ-01, REQ-02, REQ-06; ASM-02, ASM-03, ASM-06, ASM-08, ASM-09 |
| TC-008 | P1 | API | Same as TC-006 | Create score `50` through API | API accepts the interior value under its documented contract | REQ-02, REQ-06; ASM-06, ASM-08 |
| TC-009 | P0 | API + integration | No score exists | Attempt API create with `-1`; inspect persistence | API rejects without a prescribed code/schema; no invalid record exists | REQ-03, REQ-06, REQ-07, REQ-08; ASM-03, ASM-06, ASM-08 |
| TC-010 | P0 | API + integration | No score exists; `M = 100` | Attempt API create with `101`; inspect persistence | API rejects without a prescribed code/schema; no invalid record exists | REQ-04, REQ-06, REQ-07, REQ-08; ASM-03, ASM-06, ASM-08 |
| TC-011 | P0 | UI + integration | Existing valid score is `50` | Attempt UI update to `-1`; read persisted state | UI rejects; persisted score remains `50` | REQ-03, REQ-05, REQ-07; ASM-02, ASM-03, ASM-08 |
| TC-012 | P0 | UI + integration | Existing valid score is `50`; `M = 100` | Attempt UI update to `101`; read persisted state | UI rejects; persisted score remains `50` | REQ-04, REQ-05, REQ-07; ASM-02, ASM-03, ASM-08 |
| TC-013 | P0 | API + integration | Existing valid score is `50` | Attempt API update to `-1`; read persisted state | API rejects; persisted score remains `50` | REQ-03, REQ-06, REQ-07; ASM-02, ASM-03, ASM-06, ASM-08 |
| TC-014 | P0 | API + integration | Existing valid score is `50`; `M = 100` | Attempt API update to `101`; read persisted state | API rejects; persisted score remains `50` | REQ-04, REQ-06, REQ-07; ASM-02, ASM-03, ASM-06, ASM-08 |
| TC-015 | P0 | API + integration | Parameterized API data and isolated records are available | Run the same API validation test once with `-1` and once with `M + 1` | Both invalid equivalence partitions are rejected and neither value is persisted; this case specifically provides parameterized invalid-partition coverage | REQ-03, REQ-04, REQ-06, REQ-07; ASM-03, ASM-06 |
| TC-016 | P1 | UI + API + integration | `EXAM-SYN-A` has `M = 100`; `EXAM-SYN-B` has `M = 40` | Submit score `50` for each exam through isolated UI and API paths; after EXAM-SYN-B rejects `50`, use the trusted read mechanism to inspect its persisted state | `50` is within range for A and above maximum for B; each layer uses the selected exam's maximum, and no score of `50` is persisted for EXAM-SYN-B | REQ-01, REQ-02, REQ-04, REQ-05, REQ-06, REQ-07; ASM-03, ASM-04, ASM-08 |
| TC-017 | P1 | UI | Synthetic parameters `-1` and `M + 1` are available | Submit `-1` and, separately, `M + 1`; inspect each validation indication | UI exposes an observable validation failure for both values without asserting literal text | REQ-03, REQ-04, REQ-05, REQ-08; ASM-05 |
| TC-018 | P1 | API | Synthetic parameters `-1` and `M + 1` are available; exact API failure contract is unspecified | Submit `-1` and, separately, `M + 1`; inspect only the generic rejection outcome and persisted state | Neither request is treated as successful, a validation failure is observable, and neither invalid score is persisted; this case specifically verifies contract-agnostic rejection without prescribing an exact status or schema | REQ-03, REQ-04, REQ-06, REQ-07, REQ-08; ASM-03, ASM-06 |

Prioritized test-case count: **18**.

## 13. Synthetic test data

| Data ID | Synthetic value | Purpose |
| --- | --- | --- |
| EXAM-SYN-A | Configured maximum `100` | Primary boundary examples |
| EXAM-SYN-B | Configured maximum `40` | Verify per-exam configuration selection |
| TEACHER-SYN-01 | Synthetic authorized teacher | Score-entry actor |
| SCORE-EXISTING-A | Existing valid score `50` for EXAM-SYN-A | Invalid update checks |
| SCORE-BELOW-MIN | `-1` | Negative partition |
| SCORE-MIN | `0` | Inclusive minimum |
| SCORE-INTERIOR-A | `50` | Interior valid value for EXAM-SYN-A |
| SCORE-BELOW-MAX-A | `99` | Optional near-maximum valid example |
| SCORE-MAX-A | `100` | Inclusive configured maximum |
| SCORE-ABOVE-MAX-A | `101` | Above-maximum partition |
| SCORE-MAX-B | `40` | Second exam's inclusive maximum |
| SCORE-ABOVE-MAX-B | `41` | Above second exam's maximum |

All values are synthetic. Integer examples make boundaries easy to read and do not establish that decimal scores are unsupported.

## 14. Suggested test levels and automation suitability

| Coverage | Preferred level | Automation suitability |
| --- | --- | --- |
| Core range validation | Unit or service-level validation where available | High; fast parameterized coverage |
| API boundary matrix | API/integration | High; automate `-1`, `0`, `M`, and `M + 1` without prescribing an undocumented response schema |
| UI boundary behavior | UI end-to-end | High for a focused representative set at `0`, `M`, `-1`, and `M + 1` |
| Invalid create persistence | API/integration with independent read | High; critical data-integrity coverage |
| Invalid update persistence | API/integration with before/after read | High; critical regression coverage |
| Cross-layer consistency | UI plus API | High, but keep UI checks small and use API coverage for the broader matrix |
| Multiple exam maxima | API/integration plus one UI example | High once deterministic configuration setup is available |
| Exact UI message wording | Not currently defined | Do not automate literal text until specified |
| Exact API status or schema | Contract test after contract is supplied | Do not prescribe or automate exact details yet |
| Decimal and format handling | Clarification-dependent | Defer until numeric rules are confirmed |

Automation should use parameterized synthetic data, isolated records, deterministic exam configuration, and independent persistence assertions. UI automation should verify user-observable acceptance or rejection without coupling to undocumented literal messages.

## 15. Coverage exclusions

The following are excluded because they were not specified:

- Exact UI validation-message wording, location, styling, and localization.
- Exact API status codes, error identifiers, headers, and response schemas.
- Decimal support, precision, rounding, and numeric normalization.
- Empty, whitespace, non-numeric, scientific-notation, `NaN`, overflow, or locale-formatted input behavior.
- Rules for configuring or changing an exam's maximum score.
- Migration or revalidation of existing scores after a maximum changes.
- Bulk score operations.
- Concurrent updates and race conditions.
- Authorization behavior for actors other than the stated teacher.
- Audit logging, notifications, analytics, and history behavior.
- Performance, availability, transport security, and abuse controls.
- Executable automation implementation.

These exclusions are not assertions that the behaviors are unsupported; they require additional requirements or contracts.

## 16. Requirement-to-test traceability

| Requirement | Scenario coverage | Prioritized tests |
| --- | --- | --- |
| REQ-01: configured maximum per exam | UI-01, UI-02, UI-08; API-01, API-02, API-08; XL-02 | TC-001, TC-002, TC-006, TC-007, TC-016 |
| REQ-02: inclusive valid range | UI-01, UI-02, UI-03; API-01, API-02, API-03; XL-01, XL-02 | TC-001, TC-002, TC-003, TC-006, TC-007, TC-008, TC-016 |
| REQ-03: reject negative scores | UI-04, UI-06; API-04, API-06, API-09; PERSIST-01, PERSIST-03; XL-03, XL-05 | TC-004, TC-009, TC-011, TC-013, TC-015, TC-017, TC-018 |
| REQ-04: reject scores above maximum | UI-05, UI-07, UI-08; API-05, API-07, API-08, API-09; PERSIST-02, PERSIST-04; XL-04, XL-05 | TC-005, TC-010, TC-012, TC-014, TC-015, TC-016, TC-017, TC-018 |
| REQ-05: UI validation | UI-01 through UI-09; XL-01 through XL-04 | TC-001 through TC-005, TC-011, TC-012, TC-016, TC-017 |
| REQ-06: API validation | API-01 through API-09; XL-01 through XL-05 | TC-006 through TC-010, TC-013 through TC-016, TC-018 |
| REQ-07: invalid scores not persisted | UI-04 through UI-07; API-04 through API-07 and API-09; PERSIST-01 through PERSIST-04; XL-03 through XL-05 | TC-004, TC-005, TC-009 through TC-016, TC-018 |
| REQ-08: exact validation text unspecified | UI-04, UI-05, UI-09; API-04, API-05 | TC-004, TC-005, TC-009, TC-010, TC-017, TC-018 |

Every scenario and prioritized test maps to at least one confirmed requirement. Where setup, observation, numeric examples, or failure signaling are not fully specified, the mapping also identifies the relevant explicit assumption.
