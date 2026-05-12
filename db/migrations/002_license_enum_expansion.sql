-- ============================================================
-- Musarde v1 schema migration 002 — license enum expansion
-- Designed: 2026-05-11 (Week 2 Day 1, Week 1 schema review output)
-- See ../../build-log/decisions.md entry 2026-05-11 ("License enum
--     expansion for Week 5 corpus") for the design reasoning.
-- ============================================================
--
-- Two changes:
--
--   1. Expand documents.license enum to include 'cc-by-sa-4.0'
--      (needed for Wikipedia, the Week 5 corpus workhorse per the
--      2026-05-11 licensing audit) and 'cc-by-nc-4.0' (future-proofing;
--      v1 policy excludes NC content, but the value is supported so
--      the enum reflects the closed CC taxonomy, not v1 policy).
--
--   2. Add a CHECK requiring `attribution` to be non-NULL whenever
--      license is any CC-BY variant. Cheap insurance against three
--      upcoming Week 5 loaders (AIC description, Wikipedia, Getty
--      Iris) shipping with a missing-attribution bug.
--
-- Rollback (single transaction; run in reverse):
--
--   ALTER TABLE documents DROP CONSTRAINT documents_cc_by_needs_attribution;
--   ALTER TABLE documents DROP CONSTRAINT documents_license_check;
--   ALTER TABLE documents ADD CONSTRAINT documents_license_check
--     CHECK (license IN ('cc0', 'cc-by-4.0', 'other'));
--
-- ============================================================

-- 1. Expand the license enum.
ALTER TABLE documents DROP CONSTRAINT documents_license_check;
ALTER TABLE documents ADD CONSTRAINT documents_license_check
  CHECK (license IN ('cc0', 'cc-by-4.0', 'cc-by-sa-4.0', 'cc-by-nc-4.0', 'other'));

COMMENT ON CONSTRAINT documents_license_check ON documents IS
  'cc-by-nc-4.0 supported for completeness; v1 corpus policy excludes NC content. See decisions.md 2026-05-11.';

-- 2. CC-BY variants require attribution.
ALTER TABLE documents ADD CONSTRAINT documents_cc_by_needs_attribution
  CHECK (license NOT LIKE 'cc-by%' OR attribution IS NOT NULL);

COMMENT ON CONSTRAINT documents_cc_by_needs_attribution ON documents IS
  'CC-BY license terms require attribution; schema-level enforcement prevents loader-side omission. See decisions.md 2026-05-11.';
