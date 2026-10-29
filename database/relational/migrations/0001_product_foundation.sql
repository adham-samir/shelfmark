-- Stage 2 physical design: product identity, authoritative price and inventory.
-- Apply once to an empty application database using psql -v ON_ERROR_STOP=1.
BEGIN;

CREATE TABLE product_registry (
    product_id uuid PRIMARY KEY,
    lifecycle text NOT NULL DEFAULT 'draft'
        CHECK (lifecycle IN ('draft', 'active', 'archived')),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE product_prices (
    product_id uuid PRIMARY KEY REFERENCES product_registry (product_id),
    amount numeric(20, 6) NOT NULL
        CHECK (amount >= 0 AND amount <> 'NaN'::numeric),
    currency text NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
    version bigint NOT NULL DEFAULT 1 CHECK (version > 0),
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE inventory_balances (
    product_id uuid PRIMARY KEY REFERENCES product_registry (product_id),
    on_hand integer NOT NULL CHECK (on_hand >= 0),
    reserved integer NOT NULL CHECK (reserved >= 0 AND reserved <= on_hand),
    available integer GENERATED ALWAYS AS (on_hand - reserved) STORED,
    version bigint NOT NULL DEFAULT 1 CHECK (version > 0),
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX product_registry_lifecycle_id_idx
    ON product_registry (lifecycle, product_id);

COMMENT ON TABLE product_registry IS
    'Authority for product identity/lifecycle; MongoDB _id uses the same canonical UUID.';
COMMENT ON TABLE product_prices IS
    'Authority for current price only. Price history and checkout snapshots are later migrations.';
COMMENT ON COLUMN product_prices.currency IS
    'Explicit currency code; production currency is not selected by this migration.';
COMMENT ON TABLE inventory_balances IS
    'Initial single-balance design. Missing balance means unavailable data, never zero stock.';

COMMIT;
