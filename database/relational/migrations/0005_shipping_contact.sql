-- Delivery contact captured at checkout. Sandbox/demonstration data only.
ALTER TABLE orders
    ADD COLUMN shipping_name text
        CHECK (shipping_name IS NULL OR length(btrim(shipping_name)) BETWEEN 2 AND 120),
    ADD COLUMN shipping_phone text
        CHECK (shipping_phone IS NULL OR shipping_phone ~ '^\+?[0-9][0-9 -]{6,19}$'),
    ADD COLUMN shipping_city text
        CHECK (shipping_city IS NULL OR length(btrim(shipping_city)) BETWEEN 2 AND 80),
    ADD COLUMN shipping_address text
        CHECK (shipping_address IS NULL OR length(btrim(shipping_address)) BETWEEN 5 AND 300);