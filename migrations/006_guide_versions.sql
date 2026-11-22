CREATE TABLE IF NOT EXISTS docs_guide_versions (
 organization_id text NOT NULL, project_id text NOT NULL, path text NOT NULL, digest text NOT NULL,
 parent text, item_id text NOT NULL, approval text NOT NULL, body text NOT NULL,
 media jsonb NOT NULL, source jsonb NOT NULL, actor text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(organization_id,project_id,path,digest),
 FOREIGN KEY(organization_id,project_id) REFERENCES docs_projects ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS docs_guide_heads (
 organization_id text NOT NULL, project_id text NOT NULL, path text NOT NULL, digest text NOT NULL,
 PRIMARY KEY(organization_id,project_id,path),
 FOREIGN KEY(organization_id,project_id,path,digest) REFERENCES docs_guide_versions ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS docs_guide_media (
 organization_id text NOT NULL, project_id text NOT NULL, digest text NOT NULL, mime text NOT NULL, content bytea NOT NULL,
 PRIMARY KEY(organization_id,project_id,digest),
 FOREIGN KEY(organization_id,project_id) REFERENCES docs_projects ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS docs_enablement (
 id uuid PRIMARY KEY, organization_id text NOT NULL, project_id text NOT NULL, path text NOT NULL, digest text NOT NULL,
 audience text NOT NULL, format text NOT NULL, body text NOT NULL, version integer NOT NULL DEFAULT 1,
 status text NOT NULL DEFAULT 'draft', owner_id text NOT NULL, exported_at timestamptz,
 FOREIGN KEY(organization_id,project_id,path,digest) REFERENCES docs_guide_versions ON DELETE CASCADE,
 UNIQUE(organization_id,project_id,path,digest,audience,format)
);
INSERT INTO docs_schema_versions(version) VALUES(6) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS docs_refresh_requests(
 organization_id text NOT NULL,project_id text NOT NULL,path text NOT NULL,base text NOT NULL,revision text NOT NULL,
 item_id text NOT NULL,journeys jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(organization_id,project_id,path,revision),
 FOREIGN KEY(organization_id,project_id,path,base) REFERENCES docs_guide_versions(organization_id,project_id,path,digest) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS docs_reader_keys(
 id uuid PRIMARY KEY,organization_id text NOT NULL,project_id text NOT NULL,subject text NOT NULL,
 digest text NOT NULL UNIQUE,label text NOT NULL,expires_at timestamptz NOT NULL,revoked_at timestamptz,
 FOREIGN KEY(organization_id,project_id) REFERENCES docs_projects ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS docs_media_edits (
 organization_id text NOT NULL,project_id text NOT NULL,path text NOT NULL,version text NOT NULL,
 id text NOT NULL,source_digest text NOT NULL,recipe jsonb NOT NULL,content bytea NOT NULL,actor text NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(organization_id,project_id,id),FOREIGN KEY(organization_id,project_id,path,version)
 REFERENCES docs_guide_versions(organization_id,project_id,path,digest) ON DELETE CASCADE
);
ALTER TABLE docs_refresh_requests ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'waiting';
ALTER TABLE docs_refresh_requests ADD COLUMN IF NOT EXISTS reason text;
ALTER TABLE docs_refresh_requests ADD COLUMN IF NOT EXISTS proposal text;
ALTER TABLE docs_refresh_requests ADD COLUMN IF NOT EXISTS next_at timestamptz NOT NULL DEFAULT now();
CREATE INDEX IF NOT EXISTS docs_refresh_due ON docs_refresh_requests(next_at) WHERE status IN('waiting','capturing');
CREATE TABLE IF NOT EXISTS docs_library_saves (
 organization_id text NOT NULL,project_id text NOT NULL,item_id text NOT NULL,approval text NOT NULL,versions jsonb NOT NULL,
 PRIMARY KEY(organization_id,project_id,item_id,approval),FOREIGN KEY(organization_id,project_id) REFERENCES docs_projects ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS docs_publication_checks (
 organization_id text NOT NULL, project_id text NOT NULL, item_id text NOT NULL, approval_digest text NOT NULL,
 phase text NOT NULL CHECK (phase IN ('merge','build','live')), commit_sha text NOT NULL, result jsonb NOT NULL,
 checked_at timestamptz NOT NULL DEFAULT now(),PRIMARY KEY (organization_id,project_id,item_id,approval_digest,phase),
 FOREIGN KEY(organization_id,project_id,item_id,approval_digest) REFERENCES docs_guide_prs ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS docs_reader_redirects (
 organization_id text NOT NULL,project_id text NOT NULL,source text NOT NULL,target text NOT NULL,actor text NOT NULL,
 PRIMARY KEY(organization_id,project_id,source),FOREIGN KEY(organization_id,project_id) REFERENCES docs_projects ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS docs_guide_retirements (
 organization_id text NOT NULL,project_id text NOT NULL,path text NOT NULL,version text NOT NULL,item_id text NOT NULL,
 reason text NOT NULL,status text NOT NULL,actor text NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(organization_id,project_id,path,version),FOREIGN KEY(organization_id,project_id,path,version)
 REFERENCES docs_guide_versions(organization_id,project_id,path,digest) ON DELETE CASCADE
);
