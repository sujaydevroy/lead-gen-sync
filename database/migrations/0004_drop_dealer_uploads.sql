-- =============================================================================
-- Migration 0004 - Remove dcp.dealer_uploads
-- =============================================================================
-- Dealer files uploaded by system administrators are saved only in dcp.dealers and its
-- product tables (dcp.dealer_products, dcp.products, dcp.product_sub_sectors); who changed a
-- dealer is in its created_by / modified_by columns. The separate upload log table from the
-- first version of migration 0003 is no longer used.
--
-- Idempotent: safe to run on a database that never had the table. Applied by Alembic revision
-- 0004_drop_dealer_uploads.
-- =============================================================================

SET LOCAL client_min_messages = warning;

DROP TABLE IF EXISTS dcp.dealer_uploads;
