CREATE TABLE IF NOT EXISTS docs_writing_profiles (
 organization_id text NOT NULL, project_id text NOT NULL, revision integer NOT NULL CHECK(revision > 0),
 brand text NOT NULL, audience text NOT NULL, voice text NOT NULL, actor text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY (organization_id, project_id, revision),
 FOREIGN KEY (organization_id, project_id) REFERENCES docs_projects ON DELETE CASCADE
);
INSERT INTO docs_schema_versions(version) VALUES(7) ON CONFLICT DO NOTHING;
