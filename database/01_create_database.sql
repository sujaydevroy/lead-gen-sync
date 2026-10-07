-- =============================================================================
-- Optional: create a dedicated database (self-hosted / local PostgreSQL only).
-- =============================================================================
-- Skip this file on Supabase: the project already provides the "postgres" database,
-- and 02_schema.sql creates everything inside the "dcp" schema there.
--
-- Run while connected to any existing database (for example "postgres"):
--   psql -h localhost -U postgres -d postgres -v ON_ERROR_STOP=1 -f database/01_create_database.sql
-- then run 02_schema.sql and 03_seed.sql against the new database:
--   psql -h localhost -U postgres -d dealer_portal -v ON_ERROR_STOP=1 -f database/02_schema.sql
-- =============================================================================

CREATE DATABASE dealer_portal
    WITH ENCODING = 'UTF8'
         TEMPLATE = template0;

COMMENT ON DATABASE dealer_portal IS 'Dealer Communication Portal';
