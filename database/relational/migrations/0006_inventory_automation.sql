BEGIN;

ALTER TABLE reorder_records
    ADD COLUMN policy_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(policy_snapshot) = 'object'),
    ADD COLUMN decision_inputs jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(decision_inputs) = 'object'),
    ADD COLUMN status_detail text,
    ADD COLUMN last_attempted_at timestamptz;

CREATE INDEX demand_forecasts_product_generated_idx
    ON demand_forecasts (product_id, generated_at DESC);

COMMENT ON COLUMN reorder_records.policy_snapshot IS
    'Versioned DEC-008 policy inputs used by the automatic reorder decision.';
COMMENT ON COLUMN reorder_records.decision_inputs IS
    'Stock, pending replenishment, forecast, threshold, and target values used by the decision.';
COMMENT ON COLUMN reorder_records.status_detail IS
    'Sanitized supplier-simulator result or failure detail; never provider credentials.';

COMMIT;
