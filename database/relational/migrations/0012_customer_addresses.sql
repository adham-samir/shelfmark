-- Customer address book.
--
-- Orders keep their own frozen shipping snapshot and never join to this table,
-- so editing or deleting an address cannot rewrite a placed order. At most one
-- address per customer is the default, enforced by a partial unique index.
BEGIN;

CREATE TABLE customer_addresses (
    address_id uuid PRIMARY KEY,
    customer_id uuid NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    label text NOT NULL CHECK (length(btrim(label)) BETWEEN 1 AND 60),
    recipient_name text NOT NULL
        CHECK (length(btrim(recipient_name)) BETWEEN 2 AND 120),
    phone text NOT NULL CHECK (phone ~ '^\+?[0-9][0-9 -]{6,19}$'),
    city text NOT NULL CHECK (length(btrim(city)) BETWEEN 2 AND 80),
    address_line text NOT NULL CHECK (length(btrim(address_line)) BETWEEN 5 AND 300),
    is_default boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX customer_addresses_customer_idx
    ON customer_addresses (customer_id, created_at);

CREATE UNIQUE INDEX customer_addresses_one_default_idx
    ON customer_addresses (customer_id)
    WHERE is_default;

COMMENT ON TABLE customer_addresses IS
    'Reusable delivery addresses. Never read by order history: orders keep their '
    'own shipping snapshot.';

COMMIT;
