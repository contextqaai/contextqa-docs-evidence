-- Run once as the documentation staging database owner with psql.
-- Provide org, project, audience and verifier_role as psql variables.
-- The DBA provisions the login and supplies its secret to Ship 5 independently.
\set ON_ERROR_STOP on
BEGIN;
CREATE SCHEMA docs_verification;
REVOKE ALL ON SCHEMA docs_verification FROM PUBLIC;
CREATE VIEW docs_verification.guide_integrity WITH (security_barrier = true) AS
WITH scope AS (
 SELECT :'org'::text AS organization_id, :'project'::text AS project_id
), versions AS (
 SELECT v.* FROM public.docs_guide_versions v JOIN scope USING (organization_id,project_id)
), heads AS (
 SELECT h.* FROM public.docs_guide_heads h JOIN scope USING (organization_id,project_id)
), figures AS (
 SELECT v.organization_id, v.project_id, m->>'digest' AS digest,
        m->>'run' AS run_id, m->>'step' AS step_id
 FROM versions v CROSS JOIN LATERAL jsonb_array_elements(v.media) m
)
SELECT EXISTS (SELECT FROM heads) AS has_approved_guide,
 NOT EXISTS (SELECT FROM heads h LEFT JOIN versions v USING (path,digest) WHERE v.path IS NULL)
   AS every_head_resolves,
 NOT EXISTS (SELECT FROM versions WHERE jsonb_array_length(media)=0) AS every_version_has_evidence,
 NOT EXISTS (
   SELECT FROM figures f LEFT JOIN public.docs_guide_media m USING (organization_id,project_id,digest)
   WHERE m.digest IS NULL OR octet_length(m.content)=0 OR f.run_id IS NULL OR f.step_id IS NULL
 ) AS every_file_has_bytes_and_a_run_step,
 EXISTS (
   SELECT FROM public.docs_enablement a JOIN heads h USING (organization_id,project_id,path,digest)
   WHERE a.audience=:'audience' AND a.format='Training lesson' AND a.status='approved'
     AND a.exported_at IS NOT NULL
 ) AS owner_approved_and_exported;
GRANT USAGE ON SCHEMA docs_verification TO :"verifier_role";
GRANT SELECT ON docs_verification.guide_integrity TO :"verifier_role";
COMMIT;
