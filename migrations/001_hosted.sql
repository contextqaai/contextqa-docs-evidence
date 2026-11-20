CREATE TABLE IF NOT EXISTS docs_schema_versions (version integer PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS docs_organizations (id text PRIMARY KEY, name text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS docs_memberships (
 organization_id text NOT NULL REFERENCES docs_organizations(id) ON DELETE CASCADE,
 subject text NOT NULL, role text NOT NULL CHECK(role IN ('admin','editor','contributor')),
 PRIMARY KEY (organization_id, subject)
);
CREATE TABLE IF NOT EXISTS docs_projects (
 organization_id text NOT NULL REFERENCES docs_organizations(id) ON DELETE CASCADE,
 id text NOT NULL, state jsonb NOT NULL CHECK(jsonb_typeof(state) = 'object'),
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(organization_id,id)
);
CREATE INDEX IF NOT EXISTS docs_memberships_subject_idx ON docs_memberships(subject);
INSERT INTO docs_schema_versions(version) VALUES(1) ON CONFLICT DO NOTHING;
