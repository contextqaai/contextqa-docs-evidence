# Optional API and database acceptance

Run the product journey in the isolated staging workspace first. Use its ContextQA browser result to illustrate the reader guide. API and database checks add independent assertions about the service and stored state.

## Native API test

Saved Ship 5 case **223** uses four REST steps. For reuse, replace the temporary sample origin with the staging origin and bind its test identity through a ContextQA environment. Check the returned current guide path and the persisted media count. An invalid OpenAPI format should return 409. A one-character search should return 422. Use the configured tenant and project on each request. [Open the native API case](https://ship-5.contextqa.com/td/cases/223/steps)

## Native Database step

In the ContextQA test authoring view, add a **Database** step, choose the staging environment and its read-only PostgreSQL connection, and select from the scoped view described below. Assert that the single returned row has all five Boolean columns equal to true. The export assertion assumes the support-editor lesson has been approved and exported.

After a failed replay, separately compare the guide head against the digest saved before the replay. The failed run must leave that head unchanged. Record the Database step result alongside the browser case and API result. [Read the SQL assertions](database.sql)

### Connect a new private PostgreSQL target in Ship 5

Use the documentation app's dedicated staging database. Have its database owner provision a new login with a managed secret, read-only transaction defaults and no application table grants. Run the following once in that database with psql. Set the scope to the same organization, project and audience as the browser case. The view exposes one row of booleans, including whether a lesson based on a current guide was approved and exported.

```sh
psql service=docs_staging_admin -v org=sample -v project=handoff \
  -v audience='Support editors' -v verifier_role=docs_ship5_reader \
  -f examples/continuous-documentation-verification/install-verification-view.sql
```

In Ship 5, select the documentation verification environment (ID 10). Configure a PostgreSQL Database step with the approved private endpoint, staging database name, managed login binding and verified TLS. Use the following query with that login.

```sql
SELECT has_approved_guide, every_head_resolves, every_version_has_evidence,
       every_file_has_bytes_and_a_run_step, owner_approved_and_exported
FROM docs_verification.guide_integrity;
```

Assert exactly one row and five true values after exporting the lesson. Before export, the last assertion should be false in a fresh workspace. Record the run and step IDs for each checkpoint. The separate [SQL assertions](database.sql) show the test used by the isolated HTTP verification fixture. Ship 5 executed that fixture through native REST steps in [result 490](https://ship-5.contextqa.com/run-result-view?testCaseId=224&runResultId=490) and [result 492](https://ship-5.contextqa.com/run-result-view?testCaseId=225&runResultId=492). The private native Database step awaits its hostname and binding.
