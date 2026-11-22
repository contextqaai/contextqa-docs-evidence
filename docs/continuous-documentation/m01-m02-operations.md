# Configure onboarding, discovery and source intake

## Start a workspace

Apply the migrations with `python -m cqa_artifacts.hosted.manage migrate`, build the web app and start the hosted API as described in the repository README. The hosted dependency lock includes the MCP client. The deployment still uses its configured OIDC provider. A fresh signed-in user can create an isolated workspace from **Workspace access** or accept an invitation code. Existing users can do either from **Workspace settings**. A product URL is sufficient to create a workspace. Its name defaults to the hostname, and it starts with an editable discovery goal. The creator is an admin of the new organization. Admins can issue a seven-day code bound to an exact identity-provider subject. Replacing a code invalidates the old one.

In **Workspace settings → App discovery**, save the HTTPS product URL and describe a task real users perform. The settings survive refresh. Set up a separate ContextQA organization or operator-approved onboarding environment for each customer. The onboarding wizard writes organization-level state. Never reuse a shared customer’s onboarding credentials or a mutable, globally switched MCP session across customer accounts.

## Bind the integrations

Set `DOCS_CONNECTIONS_FILE` to a mounted, deployment-managed secret file outside the checkout. Its JSON keys are the actual `organization_id/project_id` values. The API reads this file when a request needs the integration. Fields are never returned by the setup endpoint. For Docker, mount it read-only and pass the path to the app container. Example values below denote placeholders.

```json
{
  "WORKSPACE_ID/docs": {
    "app_url": "https://your-staging.example/app",
    "mcp_url": "https://your-contextqa-mcp.example/mcp",
    "mcp_token": "DEDICATED_TENANT_MCP_TOKEN",
    "workspace_version_id": 1,
    "app_id": "GITHUB_APP_ID",
    "installation_id": "INSTALLATION_ID",
    "app_private_key": "MOUNTED_GITHUB_APP_RSA_PRIVATE_KEY",
    "webhook_secret": "REPLACE_WITH_A_RANDOM_PER_INSTALLATION_SECRET"
  }
}
```

The MCP endpoint must support Streamable HTTP and the ContextQA onboarding, workspace and result tools. The target URL must match the binding exactly. The app checks the selected workspace before sending credentials. Supply a dedicated test account for authenticated products. Its password is sent to ContextQA only when starting a confirmed crawl, kept out of the documentation database and cleared from the form after submission. ContextQA manages its own stored login and metering. An operator can supply a rotating `installation_token` in place of the GitHub App signing key. The GitHub App flow mints a short-lived read credential for repository selection. [GitHub installation access tokens](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app)

Select **Start ContextQA crawl**. A saved receipt identifies the attempt at this setup revision. **Check crawl result** queries the existing session, if returned. A completed onboarding step, an earlier session or an accepted start alone cannot establish coverage. Reconcile uncertain submissions against the tenant before considering another start. Inspect which routes, roles and states were reached. Retain inaccessible routes as gaps. Select repeatable, successful tasks for the documentation evidence set.

## Receive changes from GitHub

In **GitHub**, load the installation repositories. Choose the product repository, documentation destination, existing documentation branch and optional relative directory. The product default branch supplies source events. The documentation destination scopes the reviewed PR. Configure GitHub to send JSON push and pull-request events to the webhook URL shown after saving. Set the same signing secret on both sides. Disconnect pauses hosted intake and scoped delivery. GitHub retains the actual installation until removed there.

Delivery IDs, payload digests, source commit and review item are stored transactionally. A push, a merged PR and concurrent retries for the same repository revision share one review item. Changed paths from a push are bounded. A truncated list or a merged-PR payload without changed files requires further impact analysis. Capture the actual deployed revision before updating procedural guidance.

CI can submit its original GitHub event payload through the same signed endpoint using `DOCS_WEBHOOK_SECRET` in its secret store. Use a stable delivery identifier for retries. For GitHub App bindings, the payload must identify the configured installation.

```sh
docs-agent intake --payload github-event.json --kind push --delivery DELIVERY_ID \
  --url https://docs-app.example --organization WORKSPACE_ID --project docs
```

## Turn successful journeys into a documentation PR

Use the existing ContextQA writer to collect the selected saved journeys, verify deployment and artifact provenance, and prepare the editorial specs. Describe prerequisites, observable steps, expected results and recovery. Use the reviewed screenshot and recording references for each journey. For updates, use the current destination article as the exact baseline in the hosted knowledge base and in the source plan. Guide paths are relative to the configured documentation directory. [ContextQA writer](https://github.com/contextqaai/contextqa-docs-evidence/blob/main/docs/contextqa-writer.md)

```sh
python -m cqa_artifacts.hosted.manage stage-guides \
  --organization WORKSPACE_ID --project docs --subject ADMIN_SUBJECT \
  --delivery DELIVERY_ID --plan plan.json --registry journeys.json \
  --exports reviewed-exports.json --specs editorial-specs.json
```

For initial discovery, use `--discovery LOCAL_DISCOVERY_UUID` in place of `--delivery`. The initial receipt identifies the intake request. Each authored instruction still needs separately verified journey evidence. The command stages a proposal in **Review inbox**, checks the product URL and ContextQA workspace, and attaches the verified media. An identical import reuses the existing item. Unchanged guidance leaves the current article intact.

After editorial review and approval, an operator with Git, authenticated GitHub CLI and a checkout of the documentation destination can create the draft PR. The hosted app container itself does not include GitHub CLI. Use a durable shared journal directory for delivery operations.

```sh
python -m cqa_artifacts.hosted.manage draft-pr \
  --organization WORKSPACE_ID --project docs --subject ADMIN_SUBJECT --item ITEM_ID \
  --checkout /path/to/docs-repository --base-sha FULL_DOCS_BASE_SHA \
  --journal-dir /private/delivery-journals --confirm
```

The command verifies the approved digest, active destination, remote branch and baseline. It packages Markdown, images and recording references under the selected directory. A repeated delivery returns its existing receipt. An intent without a confirmed PR URL needs reconciliation against the journal, branch and GitHub. GitHub merge and website publication remain separate actions.

The push-to-inbox portion runs on webhook receipt. Selecting affected journeys, collecting a verified replay, preparing editorial specs and promoting the reviewed change still require the writer/operator workflow. The durable background scheduling and selective-refresh modules automate those remaining transitions.
