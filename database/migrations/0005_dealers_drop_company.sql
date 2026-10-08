-- =============================================================================
-- Migration 0005 - Dealers belong to no company (drop dcp.dealers.company_id)
-- =============================================================================
-- dcp.dealers becomes one global dealer directory holding only dealer data. Clients are matched to
-- dealers through the products they deal in (dcp.dealer_products), not through ownership, so the
-- company link, its unique key (company_id, dealer_code) and the company-first indexes are removed.
--
-- Dealer ID (dealer_code) becomes unique system-wide. If the same Dealer ID exists more than once
-- (e.g. in a client company and in the old platform dealer pool), the oldest row keeps it and every
-- later duplicate gets the next free DLR-xxxx code (reported with RAISE WARNING). No rows are
-- deleted, so communications, dealer products and sales records keep their links.
--
-- Idempotent: safe to run again and on a database created from the current 02_schema.sql.
-- Applied by Alembic revision 0005_dealers_drop_company.
-- =============================================================================

SET LOCAL client_min_messages = warning;

DO $$
DECLARE
    next_number INTEGER;
    duplicate   RECORD;
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'dcp' AND table_name = 'dealers' AND column_name = 'company_id'
    ) THEN
        SELECT COALESCE(MAX(substring(dealer_code FROM '^DLR-([0-9]+)$')::INTEGER), 1000) + 1
          INTO next_number
          FROM dcp.dealers;

        FOR duplicate IN
            SELECT id, dealer_code
              FROM (SELECT id, dealer_code,
                           row_number() OVER (PARTITION BY lower(dealer_code) ORDER BY id) AS position
                      FROM dcp.dealers) ranked
             WHERE position > 1
             ORDER BY id
        LOOP
            UPDATE dcp.dealers SET dealer_code = 'DLR-' || next_number WHERE id = duplicate.id;
            RAISE WARNING 'Dealer ID % was used more than once: dealer row % is now DLR-%',
                duplicate.dealer_code, duplicate.id, next_number;
            next_number := next_number + 1;
        END LOOP;

        ALTER TABLE dcp.dealers DROP CONSTRAINT IF EXISTS uq_dealers_company_code;
        DROP INDEX IF EXISTS dcp.ix_dealers_company_country_region;
        DROP INDEX IF EXISTS dcp.ix_dealers_company_status;
        DROP INDEX IF EXISTS dcp.ix_dealers_company_type;
        DROP INDEX IF EXISTS dcp.ix_dealers_company_sector;
        DROP INDEX IF EXISTS dcp.ix_dealers_company_name;
        ALTER TABLE dcp.dealers DROP COLUMN company_id;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_dealers_code' AND conrelid = 'dcp.dealers'::regclass
    ) THEN
        ALTER TABLE dcp.dealers ADD CONSTRAINT uq_dealers_code UNIQUE (dealer_code);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_dealers_country_region ON dcp.dealers (country_id, region_id);
CREATE INDEX IF NOT EXISTS ix_dealers_status ON dcp.dealers (dealer_status_id);
CREATE INDEX IF NOT EXISTS ix_dealers_type ON dcp.dealers (dealer_type_id);
CREATE INDEX IF NOT EXISTS ix_dealers_sector ON dcp.dealers (sector_id);
CREATE INDEX IF NOT EXISTS ix_dealers_name ON dcp.dealers (lower(dealer_name));

COMMENT ON TABLE dcp.dealers IS
    'Global dealer directory: dealer data only, owned by no company. Clients are matched to dealers through dealer_products.';
