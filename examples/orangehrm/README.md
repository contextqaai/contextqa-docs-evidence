# OrangeHRM: bootstrap journeys from a URL and goal

Target: https://opensource-demo.orangehrmlive.com/web/index.php/auth/login

The user supplies the URL, demo credentials and testing goal. Store credentials in a dedicated ContextQA environment, not in prompts or repository files. These prompts use `*|base_url|`, `*|cqa_username|` and `*|cqa_password|`.

1. Create a small ContextQA AI bootstrap case for authentication and navigation discovery.
2. Execute it through ContextQA and inspect the actual verdict, captured locators and generated typed steps.
3. Split coverage into reusable workflows with explicit assertions and unique synthetic fixtures. The prompts here cover employee and candidate lifecycles, admin job titles, leave validation, and directory/time navigation.
4. Execute an isolated saved plan; retain accepted run IDs rather than retrying starts.
5. Report each workflow's real outcome, evidence and cleanup status. Missing prerequisites are coverage gaps.
6. Feed reviewed successful evidence into task-based documentation. A public demo URL alone does not identify an immutable deployed source revision; do not invent a commit or claim deployment verification.

Tenant-specific setup: Ship 5 workspace 1, environment 7, discovery case 190, workflow cases 191–195, suite 41, plan 41. All accepted executions have finished. Initial suite execution 52 finished with four passes and one recruitment failure. Recruitment passed separately after repair in result 457. Authentication discovery passed (448), and its generated 19-step case passed a repaired replay (452). See [verified outcomes and coverage gaps](coverage.md). This is broad initial coverage, not exhaustive testing or a fully replay-validated suite.

The prompts in [journey-prompts.json](journey-prompts.json) contain environment references, not credentials. They document the bootstrap performed through ContextQA MCP; they are not a new one-command CLI implementation. Replace synthetic fixture suffixes for a fresh bootstrap, preserve the created fixture identity for cleanup, and inspect saved steps before replay. Generated steps may retain AI verification actions.

No seed record, user password, notification setting or organization configuration may be changed. Cleanup targets only the exact synthetic records created by a test. Full leave submission/approval and timesheet submission/approval are explicitly outside these initial validation-only journeys.


## Reusability check

The first generated authentication replay failed because it asserted the shared demo profile name was exactly John Doe. The goal required a visible profile menu, not that identity. The assertion was changed to the catalogued `verifyElementVisible` action with the existing captured locator. An initial MCP partial update left the old assertion type; verification exposed that mismatch. Both the action ID and event were then corrected through the ContextQA API. Failed results 449 and 450 were retained. Result 452 passed all 19 steps.

This is why successful bootstrap, persisted typed steps and successful replay are recorded separately. Do not label every generated test reusable merely because its original AI exploration passed.
