-- Stage 3 analytics support: indexes for BI-01 aggregate reads.
-- No tables are added; the existing event and order-item records already carry
-- the required facts.
BEGIN;

CREATE INDEX IF NOT EXISTS browsing_events_occurred_idx
    ON browsing_events (occurred_at);

CREATE INDEX IF NOT EXISTS order_items_product_idx
    ON order_items (product_id);

COMMENT ON INDEX browsing_events_occurred_idx IS
    'Supports date-ranged consumer-behaviour aggregates for BI-01.';
COMMENT ON INDEX order_items_product_idx IS
    'Supports product/category revenue attribution for BI-01.';

COMMIT;
