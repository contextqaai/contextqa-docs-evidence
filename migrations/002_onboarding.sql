CREATE TABLE IF NOT EXISTS docs_setup (
 organization_id text NOT NULL, project_id text NOT NULL,
 app_url text NOT NULL DEFAULT '', description text NOT NULL DEFAULT '',
 product_repo text NOT NULL DEFAULT '', docs_repo text NOT NULL DEFAULT '',
 branch text NOT NULL DEFAULT '', docs_root text NOT NULL DEFAULT '',
 connected boolean NOT NULL DEFAULT false, revision integer NOT NULL DEFAULT 0,
 PRIMARY KEY (organization_id,project_id),
 FOREIGN KEY (organization_id,project_id) REFERENCES docs_projects ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS docs_invites (
 organization_id text NOT NULL REFERENCES docs_organizations ON DELETE CASCADE,
 subject text NOT NULL, role text NOT NULL CHECK(role IN ('admin','editor','contributor')),
 digest text NOT NULL UNIQUE, expires_at timestamptz NOT NULL,
 PRIMARY KEY (organization_id,subject)
);
CREATE TABLE IF NOT EXISTS docs_source_deliveries (
 organization_id text NOT NULL, project_id text NOT NULL, delivery text NOT NULL,
 payload_hash text NOT NULL, repository text NOT NULL, revision text NOT NULL,
 item_id text NOT NULL, received_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(organization_id,project_id,delivery),
 FOREIGN KEY(organization_id,project_id) REFERENCES docs_projects ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS docs_source_revision ON docs_source_deliveries(organization_id,project_id,repository,revision);
CREATE TABLE IF NOT EXISTS docs_discoveries (
 id uuid PRIMARY KEY, organization_id text NOT NULL, project_id text NOT NULL,
 setup_revision integer NOT NULL, status text NOT NULL, provider_job text,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(organization_id,project_id,setup_revision),
 FOREIGN KEY(organization_id,project_id) REFERENCES docs_projects ON DELETE CASCADE
);
INSERT INTO docs_schema_versions(version) VALUES(2) ON CONFLICT DO NOTHING;
ALTER TABLE docs_setup ADD COLUMN IF NOT EXISTS connected_by text NOT NULL DEFAULT '';
ALTER TABLE docs_setup ADD COLUMN IF NOT EXISTS source_branch text NOT NULL DEFAULT '';
ALTER TABLE docs_source_deliveries ADD COLUMN IF NOT EXISTS destination jsonb NOT NULL DEFAULT '{}';
ALTER TABLE docs_discoveries ADD COLUMN IF NOT EXISTS target_url text;
ALTER TABLE docs_discoveries ADD COLUMN IF NOT EXISTS provider_case integer;
ALTER TABLE docs_discoveries ADD COLUMN IF NOT EXISTS provider_requirement integer;
ALTER TABLE docs_discoveries ADD COLUMN IF NOT EXISTS provider_session text;
CREATE TABLE IF NOT EXISTS docs_guide_prs (
 organization_id text NOT NULL, project_id text NOT NULL, item_id text NOT NULL,
 approval_digest text NOT NULL, status text NOT NULL, pr_url text,
 PRIMARY KEY (organization_id, project_id, item_id, approval_digest),
 FOREIGN KEY (organization_id, project_id) REFERENCES docs_projects ON DELETE CASCADE
);
ALTER TABLE docs_discoveries ADD COLUMN IF NOT EXISTS evidence_receipt jsonb;
ALTER TABLE docs_guide_prs ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();
