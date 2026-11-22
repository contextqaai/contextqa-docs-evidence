CREATE TABLE IF NOT EXISTS docs_capture_profiles (
 organization_id text NOT NULL, project_id text NOT NULL, journey text NOT NULL, digest text NOT NULL, registry jsonb NOT NULL,
 registered_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(organization_id,project_id,journey),
 FOREIGN KEY(organization_id,project_id) REFERENCES docs_projects ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS docs_capture_jobs (
 id uuid PRIMARY KEY, organization_id text NOT NULL, project_id text NOT NULL, request_id uuid NOT NULL,
 journey text NOT NULL, digest text NOT NULL, registry jsonb NOT NULL, revision text NOT NULL,
 status text NOT NULL, reason text, provider_run bigint, receipt jsonb,
 next_at timestamptz NOT NULL DEFAULT now(), attempts integer NOT NULL DEFAULT 0, created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(organization_id,project_id,request_id),
 FOREIGN KEY(organization_id,project_id) REFERENCES docs_projects ON DELETE CASCADE
);
ALTER TABLE docs_capture_profiles ADD COLUMN IF NOT EXISTS source_digest text;
ALTER TABLE docs_capture_jobs ADD COLUMN IF NOT EXISTS source_digest text;
CREATE UNIQUE INDEX IF NOT EXISTS docs_capture_open ON docs_capture_jobs(organization_id,project_id,journey,revision,digest)
 WHERE status IN('queued','starting','running','collecting','reconcile');
CREATE INDEX IF NOT EXISTS docs_capture_due ON docs_capture_jobs(status,next_at);
INSERT INTO docs_schema_versions(version) VALUES(5) ON CONFLICT DO NOTHING;
