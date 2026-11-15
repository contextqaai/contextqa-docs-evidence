# Use the context layer during Salesforce implementation

The useful implementation loop is approved requirement → scoped build → independent verification → owner decision. SX360 supplies configuration evidence; ContextQA can supply actual execution evidence through an authorized workflow; this repository assembles reviewed documentation. The starter does not autonomously implement or deploy Salesforce changes.

## Greenfield and existing orgs

For a new implementation, begin with process documents, data mappings, personas and acceptance criteria. An empty org cannot reveal business intent. For an existing org, compare stated policy with discovered behavior and retain legacy exceptions until an owner decides what to change.

## A bounded autonomous-agent pilot

Select one sandbox validation-rule change. A business owner approves the rule, equality boundary, exceptions and definition of done. An implementation agent receives only the approved specification and permitted actions. Verification uses independent acceptance criteria, negative/persona cases and affected regressions. The builder's claim of completion does not establish pass. Production deployment remains a separately reviewed action with rollback ownership.

Required inputs: approved rule version; impacted component references; authorized environment; data/side-effect charter; expected outputs; independent checks; allowed repair attempts; escalation and release sign-off. Open business questions stop autonomous implementation rather than inviting guesses.

This content supports implementation teams today through structured context and reviewable assets. Executable spec/MCP tools, automatic code/configuration changes, orchestration of a repair loop and full cross-system verification remain separate capabilities to implement and validate.
