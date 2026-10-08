-- =============================================================================
-- Migration 0003 - System administration (System Administrator role + platform company flag)
-- =============================================================================
-- * Role "System Administrator": the platform owners / developers. They manage every company
--   (dcp.companies) and upload dealer files into any company. Company users are managed by each
--   company's own "Company Administrator".
-- * dcp.companies.is_platform: the internal company that system administrators belong to
--   (created by `python -m app.cli create-sysadmin`); it is hidden from the company list.
-- Dealer files uploaded by system administrators are written straight into dcp.dealers and its
-- product tables (no separate upload table; see migration 0004).
--
-- Idempotent: safe to run on a database that already has these objects. Applied by Alembic
-- revision 0003_admin_dealer_uploads; database/02_schema.sql contains the same definitions.
-- =============================================================================

SET LOCAL client_min_messages = warning;

INSERT INTO dcp.roles (name, description) VALUES
    ('System Administrator', 'Platform owners: manage all companies and upload dealers')
ON CONFLICT DO NOTHING;

ALTER TABLE dcp.companies
    ADD COLUMN IF NOT EXISTS is_platform BOOLEAN NOT NULL DEFAULT FALSE;
COMMENT ON COLUMN dcp.companies.is_platform IS 'TRUE for the internal company that system administrators belong to (not a customer).';
