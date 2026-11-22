CREATE TABLE IF NOT EXISTS docs_workflows (
 organization_id text NOT NULL, project_id text NOT NULL, version integer NOT NULL,
 active boolean NOT NULL DEFAULT false, config jsonb NOT NULL,
 activated_at timestamptz, last_schedule date, live_cursor text,
 PRIMARY KEY(organization_id,project_id),
 FOREIGN KEY(organization_id,project_id) REFERENCES docs_projects ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS docs_workflow_versions (
 organization_id text NOT NULL, project_id text NOT NULL, version integer NOT NULL,
 config jsonb NOT NULL, actor text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(organization_id,project_id,version),
 FOREIGN KEY(organization_id,project_id) REFERENCES docs_workflows ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS docs_runs (
 id uuid PRIMARY KEY, organization_id text NOT NULL, project_id text NOT NULL,
 workflow_version integer NOT NULL, mode text NOT NULL, trigger_key text NOT NULL,
 input jsonb NOT NULL, status text NOT NULL DEFAULT 'queued', stage integer NOT NULL DEFAULT 0,
 attempts integer NOT NULL DEFAULT 0, lease uuid, expires_at timestamptz, reason text,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(organization_id,project_id,mode,trigger_key),
 FOREIGN KEY(organization_id,project_id,workflow_version) REFERENCES docs_workflow_versions ON DELETE CASCADE
);
ALTER TABLE docs_runs ADD COLUMN IF NOT EXISTS stage_attempts integer NOT NULL DEFAULT 0;
CREATE UNIQUE INDEX IF NOT EXISTS docs_active_test ON docs_runs(organization_id,project_id)
 WHERE mode='test' AND status IN ('queued','running');
CREATE INDEX IF NOT EXISTS docs_run_queue ON docs_runs(status,updated_at);
CREATE TABLE IF NOT EXISTS docs_run_stages (
 run_id uuid REFERENCES docs_runs ON DELETE CASCADE, stage integer NOT NULL,
 receipt jsonb NOT NULL, completed_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(run_id,stage)
);
INSERT INTO docs_schema_versions(version) VALUES(4) ON CONFLICT DO NOTHING;
