# Operate a continuously maintained guide

## Connect a client

1. Sign in to the documentation app, choose a workspace and connect the product repository, documentation repository, target branch and docs root. In the ContextQA portal pilot the GitBook repository selects `docs/` in `.gitbook.yaml`. Verify the root under **Operations**.
2. Import the existing documentation, check skipped files and select the article that describes the target task. Keep its revision and current figure for the comparison. [See the import walkthrough](m03-walkthrough.md).
3. Select the Ship 5 profile and a saved journey for this application, role and workspace. Keep sign-in credentials in ContextQA. Review the uncovered prerequisites. The hosted worker requires a workspace-scoped API binding in addition to the browser sign-in. [Configure and verify a capture](m06-results.md).
4. Under **Writing**, enter the reader, goal, prerequisite, source and supported facts. Choose **Tutorial** and attach the reviewed capture. Check placement of each screenshot or recording alongside its step. Accept the article, hand it to the reviewer, approve and save the guide version. [Follow writing and handoff](m05-m07-walkthrough.md).
5. Open **Guide library** to inspect version history and the evidence's run and step. Use **Enablement** to generate, approve and export a training lesson. [Follow the illustrated procedure](guide-library-walkthrough.md).

## Bind automatic updates

Mount the trusted `DOCS_CONNECTIONS_FILE` on the API, workflow worker and capture worker. Each uses the same organization/project binding. Mount the private capture root at the same path for each process. Configure the GitHub installation and scoped repositories through onboarding. The checkout must be accessible to the delivery process.

| Binding | Provided by | What it controls |
|---|---|---|
| `capture_registry_file`, `capture_plan_ids`, `workspace_version_id`, `capture_storage_hosts` | Operator | Allowed saved journeys, plan identities and media origins. |
| `capture_api_token`, `capture_meter_note`, `auto_refresh_plans` | Workspace operator | Server-side ContextQA API access and the numeric plan IDs permitted to run automatically. Agree the budget with the tenant and monitor the balance. |
| `deployment_revision_file` | Product deployer | JSON with `repository`, `application_url` and full `commit_sha` for the deployed app. The workflow worker waits for a match. |
| `deployment_receipt_directory` | Product deployer | The per-run deployment receipt binds the actual serving build to the capture and registered journey. See the capture guide for the full contract. |
| `documentation_checkout`, `delivery_journal_directory` | GitHub operator | The scoped checkout and durable journal for reviewed PR delivery and reconciliation. |
| `publication_webhook_secret`, `published_markdown_origin` | Documentation host | The signed build callback and trusted HTTPS origin serving approved Markdown and media with their original bytes. A host serving only rendered HTML needs its own verification adapter. |

After a signed code push, the workflow worker queues affected approved guides. An editor can see waiting, capturing, investigation and review states in **Operations**. Automatic refresh requires an imported delivered baseline, an approved guide with one scoped managed section and a matching registered journey. A failed replay preserves the approved version. A content-equivalent replay produces a no-change result. A changed replay proposes new text and media for review. Confirm a task removal and check dependencies before proposing retirement. Review the merge, build and live-file receipts individually.

## Run verification and recovery

Use saved Ship 5 browser cases for user journeys, screenshots and recordings. Run optional native REST steps against the same app revision. Choose a private read-only database binding to check persisted outcomes after the browser actions. Keep a failed optional check visible in the acceptance record with its impact. The ledger links real results for all three layers. [See verification results](platform-acceptance.md).

Run the API and both workers with the same database and private volumes. Apply migrations before startup. On a host with the project's hosted dependencies installed, use these entry points.

```sh
python -m cqa_artifacts.hosted.manage migrate
python -m cqa_artifacts.hosted.workflow_worker
python -m cqa_artifacts.hosted.capture_worker
```

The workers run as separate long-lived processes. Issue an expiring personal read key in **Ask documentation** to use the CLI. Set `DOCS_API_ORIGIN` and supply `DOCS_READER_KEY` through the secret store, then run `docs-ask "invitation"` or connect an MCP client to `docs-ask --mcp`.

For a recovery drill, snapshot the database and independently back up the private evidence volume, delivery journals and trusted deployment configuration. Protect the backup as tenant data. Restore into a fresh, fully migrated, empty database. Remount the evidence volume at the original paths and rebind credentials. Reconcile outstanding provider runs and PRs before reactivating schedules. Check a versioned guide, its original media digest and its approval after restore.

```sh
python -m cqa_artifacts.hosted.recovery snapshot docs-backup.zip
python -m cqa_artifacts.hosted.recovery restore docs-backup.zip
python -m cqa_artifacts.hosted.recovery prune --days 90
```

Set `DATABASE_URL` separately for source and restore. Prune defaults to reporting the eligible derived-image count. Add `--apply` to remove eligible derivatives. Versioned original media stay in the guide library. The local drill restored guides, approval lineage and jobs and held an uncertain capture for reconciliation. A staging rollback and evidence-volume recovery drill remain open.
