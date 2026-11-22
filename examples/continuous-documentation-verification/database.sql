-- Optional ContextQA Database step. Bind a read-only connection to the isolated documentation test database.
-- Replace sample and handoff with the verification fixture's organization and project.
-- Expect one row and a true value for each named assertion after the guide-library journey.
WITH versions AS (
 SELECT * FROM docs_guide_versions WHERE organization_id = 'sample' AND project_id = 'handoff'
), heads AS (
 SELECT * FROM docs_guide_heads WHERE organization_id = 'sample' AND project_id = 'handoff'
), references_used AS (
 SELECT v.path, m ->> 'digest' AS digest, m ->> 'run' AS run_id, m ->> 'step' AS step_id
 FROM versions v CROSS JOIN LATERAL jsonb_array_elements(v.media) m
)
SELECT
 EXISTS(SELECT 1 FROM heads) AS has_approved_guide,
 NOT EXISTS(SELECT FROM heads h LEFT JOIN versions v USING(path,digest) WHERE v.digest IS NULL) AS every_head_resolves,
 NOT EXISTS(SELECT FROM versions WHERE jsonb_array_length(media)=0) AS every_version_has_evidence,
 NOT EXISTS(SELECT FROM references_used r LEFT JOIN docs_guide_media m
   ON m.organization_id='sample' AND m.project_id='handoff' AND m.digest=r.digest
   WHERE m.digest IS NULL OR octet_length(m.content)=0 OR r.run_id IS NULL OR r.step_id IS NULL) AS every_file_has_bytes_and_a_run_step,
 EXISTS(SELECT FROM docs_enablement WHERE organization_id='sample' AND project_id='handoff'
   AND audience='Support editors' AND status='approved' AND exported_at IS NOT NULL) AS owner_approved_and_exported;
