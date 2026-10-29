-- Synthetic development fixtures only. Safe for an empty development database.
BEGIN;

INSERT INTO product_registry (product_id, lifecycle) VALUES
    ('10000000-0000-4000-8000-000000000001', 'active'),
    ('10000000-0000-4000-8000-000000000002', 'active'),
    ('10000000-0000-4000-8000-000000000003', 'active'),
    ('10000000-0000-4000-8000-000000000004', 'active'),
    ('10000000-0000-4000-8000-000000000005', 'active'),
    ('10000000-0000-4000-8000-000000000006', 'active'),
    ('10000000-0000-4000-8000-000000000007', 'active'),
    ('10000000-0000-4000-8000-000000000008', 'active'),
    ('10000000-0000-4000-8000-000000000009', 'active'),
    ('10000000-0000-4000-8000-000000000010', 'active'),
    ('10000000-0000-4000-8000-000000000011', 'active'),
    ('10000000-0000-4000-8000-000000000012', 'active'),
    ('10000000-0000-4000-8000-000000000013', 'active');

INSERT INTO product_prices (product_id, amount, currency) VALUES
    ('10000000-0000-4000-8000-000000000001', 8900.000000, 'EGP'),
    ('10000000-0000-4000-8000-000000000002', 11400.000000, 'EGP'),
    ('10000000-0000-4000-8000-000000000003', 2400.000000, 'EGP'),
    ('10000000-0000-4000-8000-000000000004', 19500.000000, 'EGP'),
    ('10000000-0000-4000-8000-000000000005', 9750.000000, 'EGP'),
    ('10000000-0000-4000-8000-000000000006', 7250.000000, 'EGP'),
    ('10000000-0000-4000-8000-000000000007', 9750.000000, 'EGP'),
    ('10000000-0000-4000-8000-000000000008', 3100.000000, 'EGP'),
    ('10000000-0000-4000-8000-000000000009', 1900.000000, 'EGP'),
    ('10000000-0000-4000-8000-000000000010', 2200.000000, 'EGP'),
    ('10000000-0000-4000-8000-000000000011', 14800.000000, 'EGP'),
    ('10000000-0000-4000-8000-000000000012', 28900.000000, 'EGP'),
    ('10000000-0000-4000-8000-000000000013', 22400.000000, 'EGP');

INSERT INTO inventory_balances (product_id, on_hand, reserved) VALUES
    ('10000000-0000-4000-8000-000000000001', 12, 2),
    ('10000000-0000-4000-8000-000000000002', 7, 1),
    ('10000000-0000-4000-8000-000000000003', 20, 4),
    ('10000000-0000-4000-8000-000000000004', 5, 0),
    ('10000000-0000-4000-8000-000000000005', 6, 1),
    ('10000000-0000-4000-8000-000000000006', 15, 2),
    ('10000000-0000-4000-8000-000000000007', 0, 0),
    ('10000000-0000-4000-8000-000000000008', 8, 2),
    ('10000000-0000-4000-8000-000000000009', 200, 3),
    ('10000000-0000-4000-8000-000000000010', 14, 2),
    ('10000000-0000-4000-8000-000000000011', 4, 0),
    ('10000000-0000-4000-8000-000000000012', 3, 0),
    ('10000000-0000-4000-8000-000000000013', 5, 1);

INSERT INTO customers (customer_id, email, display_name, preferred_locale) VALUES
    ('20000000-0000-4000-8000-000000000001', 'customer@example.invalid', 'Synthetic Customer', 'ar'),
    ('20000000-0000-4000-8000-000000000002', 'other-customer@example.invalid', 'Other Synthetic Customer', 'en');

INSERT INTO account_principals (principal_id, identity_subject, account_type, customer_id, login_email) VALUES
    ('30000000-0000-4000-8000-000000000001', 'synthetic-customer-subject', 'customer', '20000000-0000-4000-8000-000000000001', NULL),
    ('30000000-0000-4000-8000-000000000002', 'synthetic-operator-subject', 'backoffice', NULL, 'operator@example.invalid'),
    ('30000000-0000-4000-8000-000000000003', 'synthetic-other-customer-subject', 'customer', '20000000-0000-4000-8000-000000000002', NULL);

-- Deterministic demo credentials (argon2id). These are demonstration values,
-- printed in the user manual and the deck; they are not production secrets.
INSERT INTO account_credentials (principal_id, password_hash) VALUES
    ('30000000-0000-4000-8000-000000000001',
     '$argon2id$v=19$m=65536,t=3,p=4$Vu8DLALlPbw1iT6xXWjmdQ$flzdGH8Bfl9pT9932l1uNJ8G9BZ6DYJ94XFHsnF8C3Y'),
    ('30000000-0000-4000-8000-000000000002',
     '$argon2id$v=19$m=65536,t=3,p=4$fOB2Box5eUsdBjNFk09qqw$QjezNVNX+L3jXIZSK144JadLgVW2teVZZcrhBNVmK48'),
    ('30000000-0000-4000-8000-000000000003',
     '$argon2id$v=19$m=65536,t=3,p=4$9eJL3dL+hvbm8SPrkVIwMw$d8a6mvHPRk3j4ZQI0CFgSWJpzrNVPK4wibuORZcA4zQ');

INSERT INTO principal_scopes (principal_id, scope) VALUES
    ('30000000-0000-4000-8000-000000000002', 'orders:read'),
    ('30000000-0000-4000-8000-000000000002', 'orders:write'),
    ('30000000-0000-4000-8000-000000000002', 'catalog:write'),
    ('30000000-0000-4000-8000-000000000002', 'inventory:write'),
    ('30000000-0000-4000-8000-000000000002', 'pricing:write'),
    ('30000000-0000-4000-8000-000000000002', 'risk:review'),
    ('30000000-0000-4000-8000-000000000002', 'segments:read'),
    ('30000000-0000-4000-8000-000000000002', 'analytics:read');

INSERT INTO inventory_movements (movement_id, product_id, quantity_delta, reason, occurred_at) VALUES
    ('40000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000001', 12, 'seed', CURRENT_TIMESTAMP),
    ('40000000-0000-4000-8000-000000000002', '10000000-0000-4000-8000-000000000002', 7, 'seed', CURRENT_TIMESTAMP),
    ('40000000-0000-4000-8000-000000000003', '10000000-0000-4000-8000-000000000003', 20, 'seed', CURRENT_TIMESTAMP),
    ('40000000-0000-4000-8000-000000000004', '10000000-0000-4000-8000-000000000004', 5, 'seed', CURRENT_TIMESTAMP),
    ('40000000-0000-4000-8000-000000000005', '10000000-0000-4000-8000-000000000005', 6, 'seed', CURRENT_TIMESTAMP),
    ('40000000-0000-4000-8000-000000000006', '10000000-0000-4000-8000-000000000006', 15, 'seed', CURRENT_TIMESTAMP),
    ('40000000-0000-4000-8000-000000000008', '10000000-0000-4000-8000-000000000008', 8, 'seed', CURRENT_TIMESTAMP),
    ('40000000-0000-4000-8000-000000000009', '10000000-0000-4000-8000-000000000009', 200, 'seed', CURRENT_TIMESTAMP),
    ('40000000-0000-4000-8000-000000000010', '10000000-0000-4000-8000-000000000010', 14, 'seed', CURRENT_TIMESTAMP),
    ('40000000-0000-4000-8000-000000000011', '10000000-0000-4000-8000-000000000011', 4, 'seed', CURRENT_TIMESTAMP),
    ('40000000-0000-4000-8000-000000000012', '10000000-0000-4000-8000-000000000012', 3, 'seed', CURRENT_TIMESTAMP),
    ('40000000-0000-4000-8000-000000000013', '10000000-0000-4000-8000-000000000013', 5, 'seed', CURRENT_TIMESTAMP);

-- Deterministic synthetic daily sales history for BO-01 only. The formula mirrors
-- services/api/data/forecast.synthetic.json and ends on the day before seeding.
WITH demand_profiles(product_id, base_demand) AS (
    VALUES
        ('10000000-0000-4000-8000-000000000001'::uuid, 8),
        ('10000000-0000-4000-8000-000000000002'::uuid, 5),
        ('10000000-0000-4000-8000-000000000003'::uuid, 3),
        ('10000000-0000-4000-8000-000000000004'::uuid, 2),
        ('10000000-0000-4000-8000-000000000005'::uuid, 4),
        ('10000000-0000-4000-8000-000000000006'::uuid, 3),
        ('10000000-0000-4000-8000-000000000007'::uuid, 2),
        ('10000000-0000-4000-8000-000000000008'::uuid, 3),
        ('10000000-0000-4000-8000-000000000009'::uuid, 1),
        ('10000000-0000-4000-8000-000000000010'::uuid, 1),
        ('10000000-0000-4000-8000-000000000011'::uuid, 2),
        ('10000000-0000-4000-8000-000000000012'::uuid, 2),
        ('10000000-0000-4000-8000-000000000013'::uuid, 2)
), daily AS (
    SELECT product_id, base_demand, day_index,
           CURRENT_DATE - (210 - day_index) AS demand_date
    FROM demand_profiles CROSS JOIN generate_series(0, 209) AS day_index
)
INSERT INTO inventory_movements(
    movement_id, product_id, quantity_delta, reason,
    reference_type, occurred_at
)
SELECT md5(product_id::text || ':' || demand_date::text)::uuid,
       product_id,
       -(base_demand
         + CASE WHEN extract(isodow FROM demand_date) IN (5, 6) THEN 2 ELSE 0 END
         + floor(day_index / 60.0)::integer
         + CASE WHEN day_index % 3 = 0 THEN 1 ELSE 0 END),
       'sale',
       'synthetic_demand_history',
       demand_date + time '12:00'
FROM daily;

-- Deterministic synthetic BO-02 pricing inputs. Competitors' costs are imported
-- values, not a real competitor feed (DEC-007). One observation is intentionally
-- stale so the run reports the freshness rule instead of silently pricing it.
INSERT INTO pricing_observations (
    observation_id, product_id, recorded_cost, supply_value, demand_value,
    competitor_cost, season_id, provenance_class, observed_at
) VALUES
    ('50000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000001', 6230.000000, 10.000000, 56.000000, 6500.000000, 'standard', 'synthetic', CURRENT_TIMESTAMP - interval '15 minutes'),
    ('50000000-0000-4000-8000-000000000002', '10000000-0000-4000-8000-000000000002', 7980.000000, 6.000000, 35.000000, 8100.000000, 'standard', 'synthetic', CURRENT_TIMESTAMP - interval '15 minutes'),
    ('50000000-0000-4000-8000-000000000003', '10000000-0000-4000-8000-000000000003', 1680.000000, 16.000000, 21.000000, 1650.000000, 'standard', 'synthetic', CURRENT_TIMESTAMP - interval '15 minutes'),
    ('50000000-0000-4000-8000-000000000004', '10000000-0000-4000-8000-000000000004', 13650.000000, 5.000000, 14.000000, 14100.000000, 'standard', 'synthetic', CURRENT_TIMESTAMP - interval '15 minutes'),
    ('50000000-0000-4000-8000-000000000005', '10000000-0000-4000-8000-000000000005', 6825.000000, 5.000000, 28.000000, 6700.000000, 'standard', 'synthetic', CURRENT_TIMESTAMP - interval '15 minutes'),
    ('50000000-0000-4000-8000-000000000006', '10000000-0000-4000-8000-000000000006', 5075.000000, 13.000000, 21.000000, 5200.000000, 'standard', 'synthetic', CURRENT_TIMESTAMP - interval '15 minutes'),
    ('50000000-0000-4000-8000-000000000007', '10000000-0000-4000-8000-000000000007', 6825.000000, 0.000000, 14.000000, 7000.000000, 'standard', 'synthetic', CURRENT_TIMESTAMP - interval '15 minutes'),
    ('50000000-0000-4000-8000-000000000008', '10000000-0000-4000-8000-000000000008', 2170.000000, 6.000000, 21.000000, 2250.000000, 'standard', 'synthetic', CURRENT_TIMESTAMP - interval '15 minutes'),
    ('50000000-0000-4000-8000-000000000009', '10000000-0000-4000-8000-000000000009', 1330.000000, 197.000000, 7.000000, 1300.000000, 'standard', 'synthetic', CURRENT_TIMESTAMP - interval '15 minutes'),
    ('50000000-0000-4000-8000-000000000010', '10000000-0000-4000-8000-000000000010', 1540.000000, 12.000000, 7.000000, 1560.000000, 'standard', 'synthetic', CURRENT_TIMESTAMP - interval '15 minutes'),
    ('50000000-0000-4000-8000-000000000011', '10000000-0000-4000-8000-000000000011', 15000.000000, 4.000000, 14.000000, 15200.000000, 'standard', 'synthetic', CURRENT_TIMESTAMP - interval '15 minutes'),
    ('50000000-0000-4000-8000-000000000012', '10000000-0000-4000-8000-000000000012', 20230.000000, 3.000000, 14.000000, 20500.000000, 'standard', 'synthetic', CURRENT_TIMESTAMP - interval '15 minutes'),
    ('50000000-0000-4000-8000-000000000013', '10000000-0000-4000-8000-000000000013', 15680.000000, 4.000000, 14.000000, 15800.000000, 'standard', 'synthetic', CURRENT_TIMESTAMP - interval '30 hours');

-- Deterministic synthetic customer and order history for BO-03 RFM and later BI.
-- Orders intentionally include statuses outside the eligible set, full and partial
-- refunds, and orders older than the 365-day window. They create no inventory
-- movements, so BO-01 stock fixtures remain unchanged.
INSERT INTO customers (customer_id, email, display_name, preferred_locale)
SELECT ('20000000-0000-4000-8000-' || lpad((100 + n)::text, 12, '0'))::uuid,
       'rfm-customer-' || n || '@example.invalid',
       'Synthetic RFM Customer ' || n,
       CASE WHEN n % 2 = 0 THEN 'ar' ELSE 'en' END
FROM generate_series(1, 38) AS n;

WITH customer_index AS (
    SELECT customer_id, row_number() OVER (ORDER BY customer_id)::integer AS idx
    FROM customers
), expanded AS (
    SELECT customer_id, idx,
           2 + (idx * 7) % 22 AS order_count
    FROM customer_index
), sequences AS (
    SELECT customer_id, idx, seq
    FROM expanded
    CROSS JOIN LATERAL generate_series(1, order_count) AS seq
), dated AS (
    SELECT customer_id, idx, seq::integer AS seq,
           CURRENT_DATE - ((idx * 11 + seq * 19) % 400) AS ordered_on,
           (idx * 13 + seq * 7) % 10 AS status_bucket,
           (idx * 17 + seq * 23) % 12 AS refund_bucket,
           (1000 + ((idx * 31 + seq * 47) % 40) * 250)::numeric(20, 6) AS subtotal
    FROM sequences
), shaped AS (
    SELECT customer_id, idx, seq, ordered_on, subtotal, refund_bucket,
           CASE
               WHEN idx % 19 = 0 THEN 'cancelled'
               WHEN status_bucket = 0 THEN 'cancelled'
               WHEN status_bucket = 1 THEN 'payment_failed'
               WHEN refund_bucket = 0 THEN 'refunded'
               WHEN (idx + seq) % 3 = 0 THEN 'confirmed'
               WHEN (idx + seq) % 3 = 1 THEN 'shipped'
               ELSE 'delivered'
           END AS status
    FROM dated
)
INSERT INTO orders (
    order_id, customer_id, status, subtotal, refund_total, created_at, completed_at
)
SELECT md5(customer_id::text || ':rfm:' || seq)::uuid,
       customer_id,
       status,
       subtotal,
       CASE
           WHEN status = 'refunded' THEN subtotal
           WHEN status IN ('confirmed', 'shipped', 'delivered')
                AND refund_bucket = 1 THEN round(subtotal * 0.25, 6)
           ELSE 0
       END,
       ordered_on + time '10:00',
       CASE
           WHEN status IN ('confirmed', 'shipped', 'delivered', 'refunded')
           THEN ordered_on + time '12:00'
           ELSE NULL
       END
FROM shaped;

-- Deterministic synthetic order lines for BI-01 revenue attribution and
-- category filtering. Line prices are derived from the stored order subtotal so
-- sum(line_total) equals subtotal exactly; this keeps reconciliation meaningful
-- instead of trivially failing on synthetic drift.
WITH expanded AS (
    SELECT order_id, subtotal,
           1 + (abs(hashtext(order_id::text)) % 3) AS item_count
    FROM orders
), candidates AS (
    SELECT e.order_id, e.subtotal, e.item_count, r.product_id, p.amount AS list_price,
           row_number() OVER (
               PARTITION BY e.order_id
               ORDER BY md5(e.order_id::text || r.product_id::text)
           ) AS rank
    FROM expanded e
    CROSS JOIN product_registry r
    JOIN product_prices p USING (product_id)
), selected AS (
    SELECT * FROM candidates WHERE rank <= item_count
), weighted AS (
    SELECT order_id, subtotal, product_id, list_price,
           sum(list_price) OVER (PARTITION BY order_id) AS price_total,
           row_number() OVER (PARTITION BY order_id ORDER BY product_id) AS line_no,
           count(*) OVER (PARTITION BY order_id) AS lines
    FROM selected
), priced AS (
    SELECT order_id, product_id, line_no, lines, subtotal,
           CASE WHEN line_no = lines
                THEN subtotal - COALESCE(
                         sum(round(subtotal * list_price / price_total, 6)) OVER (
                             PARTITION BY order_id ORDER BY product_id
                             ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                         ), 0)
                ELSE round(subtotal * list_price / price_total, 6)
           END AS unit_price
    FROM weighted
)
INSERT INTO order_items(
    order_item_id, order_id, product_id, product_name_snapshot,
    quantity, unit_price_snapshot, currency
)
SELECT md5(order_id::text || ':' || product_id::text)::uuid,
       order_id,
       product_id,
       'Synthetic ' || left(product_id::text, 8),
       1,
       unit_price,
       'EGP'
FROM priced;

-- Deterministic synthetic browsing history for BI-01 consumer-behaviour
-- metrics: 9,000 events over the last 90 days across 2,250 sessions, with
-- 30% anonymous sessions so the conversion denominator stays honest.
WITH customer_index AS (
    SELECT customer_id, row_number() OVER (ORDER BY customer_id) - 1 AS n,
           count(*) OVER () AS total
    FROM customers
), product_index AS (
    SELECT product_id, row_number() OVER (ORDER BY product_id) - 1 AS n,
           count(*) OVER () AS total
    FROM product_registry
), series AS (
    SELECT i FROM generate_series(1, 9000) AS i
)
INSERT INTO browsing_events(
    event_id, customer_id, session_id, product_id, event_type,
    occurred_at, provenance_class, context
)
SELECT md5('browse:' || i)::uuid,
       CASE WHEN i % 10 < 7
            THEN (SELECT customer_id FROM customer_index
                  WHERE customer_index.n = (i * 7) % customer_index.total)
       END,
       md5('session:' || (i / 4))::uuid,
       (SELECT product_id FROM product_index
        WHERE product_index.n = (i * 11) % product_index.total),
       CASE
           WHEN i % 10 < 6 THEN 'view'
           WHEN i % 10 < 8 THEN 'search_click'
           WHEN i % 10 < 9 THEN 'compare'
           ELSE 'add_to_cart'
       END,
       (CURRENT_DATE - ((i * 37) % 90)) + make_interval(hours => 8 + (i % 12)),
       'synthetic',
       '{"source":"synthetic_demo"}'::jsonb
FROM series;

COMMIT;
