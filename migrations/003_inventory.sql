CREATE TABLE IF NOT EXISTS docs_imports (
 id uuid PRIMARY KEY, organization_id text NOT NULL, project_id text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(), scope jsonb NOT NULL, commit_sha text NOT NULL,
 manifest jsonb NOT NULL, status text NOT NULL DEFAULT 'reading', summary jsonb NOT NULL DEFAULT '{}',
 FOREIGN KEY (organization_id, project_id) REFERENCES docs_projects ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS docs_import_latest ON docs_imports(organization_id, project_id, created_at DESC);
CREATE TABLE IF NOT EXISTS docs_import_files (
 job_id uuid REFERENCES docs_imports ON DELETE CASCADE, path text NOT NULL,
 kind text NOT NULL, sha text NOT NULL, status text NOT NULL DEFAULT 'pending',
 data jsonb, issue text, PRIMARY KEY(job_id,path)
);
CREATE TABLE IF NOT EXISTS docs_import_versions (
 organization_id text NOT NULL, project_id text NOT NULL, path text NOT NULL, version integer NOT NULL,
 job_id uuid NOT NULL REFERENCES docs_imports ON DELETE CASCADE, article_id uuid NOT NULL,
 source jsonb NOT NULL, body text NOT NULL,
 PRIMARY KEY(organization_id,project_id,path,version),
 FOREIGN KEY(organization_id,project_id) REFERENCES docs_projects ON DELETE CASCADE
);
INSERT INTO docs_schema_versions(version) VALUES(3) ON CONFLICT DO NOTHING;
