-- Stage 3 SF-01 evidence: recommendation requests and ranked outputs.
BEGIN;

CREATE TABLE recommendation_runs (
    run_id uuid PRIMARY KEY,
    customer_id uuid REFERENCES customers (customer_id),
    model_version_id uuid NOT NULL REFERENCES model_versions (model_version_id),
    strategy text NOT NULL CHECK (strategy IN ('hybrid', 'cold_start_fallback')),
    input_summary jsonb NOT NULL CHECK (jsonb_typeof(input_summary) = 'object'),
    generated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX recommendation_runs_customer_time_idx
    ON recommendation_runs (customer_id, generated_at DESC);

CREATE TABLE recommendation_items (
    run_id uuid NOT NULL REFERENCES recommendation_runs (run_id) ON DELETE CASCADE,
    product_id uuid NOT NULL REFERENCES product_registry (product_id),
    rank integer NOT NULL CHECK (rank > 0),
    collaborative_score numeric(12,9) NOT NULL CHECK (collaborative_score >= 0),
    content_score numeric(12,9) NOT NULL CHECK (content_score >= 0),
    combined_score numeric(12,9) NOT NULL CHECK (combined_score >= 0),
    PRIMARY KEY (run_id, rank),
    UNIQUE (run_id, product_id)
);

COMMENT ON TABLE recommendation_runs IS
    'Auditable SF-01 request evidence; input_summary records signal counts, not raw browsing payloads.';

COMMIT;
