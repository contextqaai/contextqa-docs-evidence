# OrangeHRM execution evidence — November 20, 2026

ContextQA performed all application interactions and produced all screenshots and recordings. The target was the OrangeHRM public demo, using credentials stored in ContextQA environment 7. No credential values or signed media URLs are included here.

## Actual outcomes

| Journey | Result | Evidence and limit |
| --- | --- | --- |
| Authentication and navigation, case 190 | [452: SUCCESS](https://ship-5.contextqa.com/run-result-view?testCaseId=190&runResultId=452) | Saved-case replay passed 19/19 steps: empty-login validation, sign-in, dashboard/profile visibility, PIM and Directory navigation, logout. |
| Employee lifecycle, case 191 | [451: SUCCESS](https://ship-5.contextqa.com/run-result-view?testCaseId=191&runResultId=451) | AI bootstrap created an employee, searched by employee ID, edited details, deleted that employee and verified absence. Generated 26 saved steps; separate replay not run. |
| Recruitment lifecycle, case 192 | [457: SUCCESS](https://ship-5.contextqa.com/run-result-view?testCaseId=192&runResultId=457) | Repaired AI bootstrap checked required fields, reopened a clean form, created and reopened a candidate, deleted that candidate and verified absence. Generated 32 saved steps; separate replay not run. |
| Admin job title, case 193 | [455: SUCCESS](https://ship-5.contextqa.com/run-result-view?testCaseId=193&runResultId=455) | AI bootstrap searched/reset users, created a job title, edited and reopened its description, deleted that title and verified absence. Generated 30 saved steps; separate replay not run. |
| Leave, case 194 | [456: SUCCESS](https://ship-5.contextqa.com/run-result-view?testCaseId=194&runResultId=456) | Default list search/reset and the no-balance prerequisite were observed. Apply displayed “No Leave Types with Leave Balance.” Generated 13 saved steps. Required-field validation, changed-filter behavior and submission are not established by this run. |
| Directory and Time, case 195 | [458: SUCCESS](https://ship-5.contextqa.com/run-result-view?testCaseId=195&runResultId=458) | AI bootstrap searched an observed employee, reset the directory, opened a project report, selected a project and checked results, then logged out. Generated 22 saved steps; separate replay not run. |

[Saved plan 41](https://ship-5.contextqa.com/td/1/plans/41/overview), execution 52, finished **FAILURE: 4 passed / 1 failed**. The failed recruitment result 453 remains part of that history. Separate repair attempts produced failure 454 and success 457; they do not turn execution 52 into a pass. Authentication was executed separately.

“Bootstrap passed” means the AI exploration completed successfully. Its result contains one AI step; the saved actions generated from that exploration are not an independently passed replay. Some generated actions use AI verification. Only authentication currently has a verified saved-case replay.

## Maintenance findings

- Authentication initially asserted a fixed shared-demo profile name. Failed replays 449 and 450 were retained. The repaired assertion checks the visible profile menu using a captured locator; replay 452 passed.
- Recruitment initially chose an Email locator containing a transient validation-error CSS class. Results 453 and 454 failed. The final prompt keeps the negative validation check, then cancels and reopens the form before the positive flow. Result 457 passed, including candidate cleanup.
- The generated Time report assertion expects exactly seven records. Before treating that case as a stable regression test, replace the assertion with the actual intended result invariant and replay it. Shared-demo employee/project fixtures may also change.
- Saved-step API responses are not necessarily ordered; consumers must use each step's position when rendering journeys.

## Documentation output

A local illustrated draft, “Sign in and find employee views in OrangeHRM,” was compiled from successful replay 452. Its three figures are ContextQA step-result screenshots 781 (Dashboard), 785 (Employee List) and 787 (Directory). The article covers sign-in, navigation and sign-out. It does not claim that this navigation case tested employee creation or search.

Login-page screenshots were excluded because the demo page displays credentials. Source screenshots and provenance remain in the private working output; they are not embedded in this repository example. The public demo's deployed source revision is unknown, so the draft is not promoted into the deployment-verified latest documentation library. An observed version label is not a commit attestation.

## Remaining coverage

Independent replay remains required for cases 191–195. Leave submission/approval, timesheet submission/approval, My Info editing, Performance, Maintenance, Claim, Buzz posting, non-admin roles and other browsers are not covered. Missing prerequisites must remain explicit gaps rather than passed requirements. A larger suite should add these workflows with isolated fixtures and the necessary account roles; the six initial journeys do not establish comprehensive product acceptance.
