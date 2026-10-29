-- Stage 2 physical design: identities, interactions, commerce, risk, shipment,
-- forecasting/reorder, pricing audit, segmentation, and model evidence.
BEGIN;

CREATE TABLE customers (
    customer_id uuid PRIMARY KEY,
    email text NOT NULL UNIQUE CHECK (email = lower(email) AND position('@' IN email) > 1),
    display_name text NOT NULL CHECK (length(btrim(display_name)) > 0),
    preferred_locale text NOT NULL DEFAULT 'ar' CHECK (preferred_locale IN ('ar', 'en')),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE account_principals (
    principal_id uuid PRIMARY KEY,
    identity_subject text NOT NULL UNIQUE CHECK (length(btrim(identity_subject)) > 0),
    account_type text NOT NULL CHECK (account_type IN ('customer', 'backoffice')),
    customer_id uuid UNIQUE REFERENCES customers (customer_id),
    enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK ((account_type = 'customer' AND customer_id IS NOT NULL)
        OR (account_type = 'backoffice' AND customer_id IS NULL))
);

CREATE TABLE principal_scopes (
    principal_id uuid NOT NULL REFERENCES account_principals (principal_id) ON DELETE CASCADE,
    scope text NOT NULL CHECK (scope IN (
        'catalog:write', 'inventory:write', 'pricing:write', 'risk:review',
        'segments:read', 'analytics:read'
    )),
    granted_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (principal_id, scope)
);

CREATE TABLE browsing_events (
    event_id uuid PRIMARY KEY,
    customer_id uuid REFERENCES customers (customer_id),
    session_id uuid NOT NULL,
    product_id uuid NOT NULL REFERENCES product_registry (product_id),
    event_type text NOT NULL CHECK (event_type IN ('view', 'search_click', 'compare', 'add_to_cart')),
    occurred_at timestamptz NOT NULL,
    provenance_class text NOT NULL CHECK (provenance_class IN ('real', 'public', 'synthetic', 'sandbox')),
    context jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(context) = 'object')
);

CREATE INDEX browsing_events_customer_time_idx ON browsing_events (customer_id, occurred_at DESC);
CREATE INDEX browsing_events_product_time_idx ON browsing_events (product_id, occurred_at DESC);

CREATE TABLE carts (
    cart_id uuid PRIMARY KEY,
    customer_id uuid NOT NULL REFERENCES customers (customer_id),
    status text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'converted', 'abandoned')),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX carts_one_open_per_customer_idx ON carts (customer_id) WHERE status = 'open';

CREATE TABLE cart_items (
    cart_id uuid NOT NULL REFERENCES carts (cart_id) ON DELETE CASCADE,
    product_id uuid NOT NULL REFERENCES product_registry (product_id),
    quantity integer NOT NULL CHECK (quantity > 0),
    added_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (cart_id, product_id)
);

CREATE TABLE orders (
    order_id uuid PRIMARY KEY,
    customer_id uuid NOT NULL REFERENCES customers (customer_id),
    cart_id uuid UNIQUE REFERENCES carts (cart_id),
    status text NOT NULL CHECK (status IN (
        'pending_payment', 'pending_risk', 'review', 'confirmed',
        'payment_failed', 'cancelled', 'shipped', 'delivered', 'refunded'
    )),
    currency text NOT NULL DEFAULT 'EGP' CHECK (currency = 'EGP'),
    subtotal numeric(20,6) NOT NULL CHECK (subtotal >= 0 AND subtotal <> 'NaN'::numeric),
    refund_total numeric(20,6) NOT NULL DEFAULT 0 CHECK (refund_total >= 0 AND refund_total <> 'NaN'::numeric),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamptz,
    CHECK (refund_total <= subtotal)
);

CREATE INDEX orders_customer_time_idx ON orders (customer_id, created_at DESC);
CREATE INDEX orders_status_time_idx ON orders (status, created_at);

CREATE TABLE order_items (
    order_item_id uuid PRIMARY KEY,
    order_id uuid NOT NULL REFERENCES orders (order_id) ON DELETE CASCADE,
    product_id uuid NOT NULL REFERENCES product_registry (product_id),
    product_name_snapshot text NOT NULL CHECK (length(btrim(product_name_snapshot)) > 0),
    quantity integer NOT NULL CHECK (quantity > 0),
    unit_price_snapshot numeric(20,6) NOT NULL CHECK (unit_price_snapshot >= 0 AND unit_price_snapshot <> 'NaN'::numeric),
    currency text NOT NULL CHECK (currency = 'EGP'),
    line_total numeric(20,6) GENERATED ALWAYS AS (quantity * unit_price_snapshot) STORED,
    UNIQUE (order_id, product_id)
);

CREATE TABLE payment_transactions (
    transaction_id uuid PRIMARY KEY,
    order_id uuid NOT NULL REFERENCES orders (order_id),
    provider_reference text NOT NULL UNIQUE CHECK (length(btrim(provider_reference)) > 0),
    token_reference text NOT NULL CHECK (length(btrim(token_reference)) > 0),
    amount numeric(20,6) NOT NULL CHECK (amount >= 0 AND amount <> 'NaN'::numeric),
    currency text NOT NULL CHECK (currency = 'EGP'),
    status text NOT NULL CHECK (status IN ('prepared', 'authorized', 'failed', 'cancelled', 'refunded')),
    sandbox boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX payment_transactions_order_idx ON payment_transactions (order_id, created_at DESC);

CREATE TABLE model_versions (
    model_version_id uuid PRIMARY KEY,
    module text NOT NULL CHECK (module IN ('recommendation', 'image_search', 'forecast', 'fraud')),
    version_label text NOT NULL,
    dataset_snapshot_id text NOT NULL,
    artifact_reference text NOT NULL,
    framework text NOT NULL CHECK (framework IN ('scikit-learn', 'pytorch')),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (module, version_label)
);

CREATE TABLE risk_assessments (
    assessment_id uuid PRIMARY KEY,
    transaction_id uuid NOT NULL REFERENCES payment_transactions (transaction_id),
    model_version_id uuid REFERENCES model_versions (model_version_id),
    score numeric(8,7) CHECK (score >= 0 AND score <= 1 AND score <> 'NaN'::numeric),
    outcome text NOT NULL CHECK (outcome IN ('allow', 'review', 'assessment_failed')),
    reasons jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(reasons) = 'array'),
    assessed_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (transaction_id)
);

CREATE TABLE shipments (
    shipment_id uuid PRIMARY KEY,
    order_id uuid NOT NULL UNIQUE REFERENCES orders (order_id),
    provider_reference text NOT NULL UNIQUE,
    status text NOT NULL CHECK (status IN ('pending', 'ready', 'in_transit', 'delivered', 'exception')),
    sandbox boolean NOT NULL DEFAULT true,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE shipment_events (
    shipment_event_id uuid PRIMARY KEY,
    shipment_id uuid NOT NULL REFERENCES shipments (shipment_id) ON DELETE CASCADE,
    status text NOT NULL CHECK (status IN ('pending', 'ready', 'in_transit', 'delivered', 'exception')),
    description_ar text NOT NULL,
    description_en text NOT NULL,
    occurred_at timestamptz NOT NULL
);

CREATE INDEX shipment_events_timeline_idx ON shipment_events (shipment_id, occurred_at);

CREATE TABLE inventory_movements (
    movement_id uuid PRIMARY KEY,
    product_id uuid NOT NULL REFERENCES product_registry (product_id),
    quantity_delta integer NOT NULL CHECK (quantity_delta <> 0),
    reason text NOT NULL CHECK (reason IN ('seed', 'sale', 'reservation', 'release', 'replenishment', 'adjustment')),
    reference_type text,
    reference_id uuid,
    occurred_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX inventory_movements_product_time_idx ON inventory_movements (product_id, occurred_at DESC);

CREATE TABLE price_changes (
    price_change_id uuid PRIMARY KEY,
    product_id uuid NOT NULL REFERENCES product_registry (product_id),
    old_amount numeric(20,6) NOT NULL CHECK (old_amount >= 0 AND old_amount <> 'NaN'::numeric),
    new_amount numeric(20,6) NOT NULL CHECK (new_amount >= 0 AND new_amount <> 'NaN'::numeric),
    currency text NOT NULL CHECK (currency = 'EGP'),
    calculation_version text NOT NULL,
    contributing_inputs jsonb NOT NULL CHECK (jsonb_typeof(contributing_inputs) = 'object'),
    applied_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (old_amount <> new_amount)
);

CREATE INDEX price_changes_product_time_idx ON price_changes (product_id, applied_at DESC);

CREATE TABLE pricing_observations (
    observation_id uuid PRIMARY KEY,
    product_id uuid NOT NULL REFERENCES product_registry (product_id),
    recorded_cost numeric(20,6) NOT NULL CHECK (recorded_cost >= 0 AND recorded_cost <> 'NaN'::numeric),
    supply_value numeric(20,6) NOT NULL CHECK (supply_value >= 0 AND supply_value <> 'NaN'::numeric),
    demand_value numeric(20,6) NOT NULL CHECK (demand_value >= 0 AND demand_value <> 'NaN'::numeric),
    competitor_cost numeric(20,6) NOT NULL CHECK (competitor_cost >= 0 AND competitor_cost <> 'NaN'::numeric),
    season_id text NOT NULL,
    provenance_class text NOT NULL CHECK (provenance_class IN ('real', 'public', 'synthetic', 'sandbox')),
    observed_at timestamptz NOT NULL
);

CREATE INDEX pricing_observations_product_time_idx ON pricing_observations (product_id, observed_at DESC);

CREATE TABLE demand_forecasts (
    forecast_id uuid PRIMARY KEY,
    product_id uuid NOT NULL REFERENCES product_registry (product_id),
    model_version_id uuid NOT NULL REFERENCES model_versions (model_version_id),
    horizon_start date NOT NULL,
    horizon_end date NOT NULL,
    predicted_quantity numeric(20,6) NOT NULL CHECK (predicted_quantity >= 0 AND predicted_quantity <> 'NaN'::numeric),
    generated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (horizon_end >= horizon_start),
    UNIQUE (product_id, model_version_id, horizon_start, horizon_end)
);

CREATE TABLE reorder_records (
    reorder_id uuid PRIMARY KEY,
    product_id uuid NOT NULL REFERENCES product_registry (product_id),
    forecast_id uuid NOT NULL REFERENCES demand_forecasts (forecast_id),
    idempotency_key text NOT NULL UNIQUE,
    quantity integer NOT NULL CHECK (quantity > 0),
    status text NOT NULL CHECK (status IN ('created', 'dispatched', 'acknowledged', 'failed', 'received')),
    supplier_reference text,
    simulator boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX reorder_records_product_status_idx ON reorder_records (product_id, status, created_at DESC);

CREATE TABLE rfm_snapshots (
    snapshot_id uuid PRIMARY KEY,
    customer_id uuid NOT NULL REFERENCES customers (customer_id),
    reference_date date NOT NULL,
    observation_start date NOT NULL,
    recency_days integer NOT NULL CHECK (recency_days >= 0),
    frequency integer NOT NULL CHECK (frequency >= 0),
    monetary numeric(20,6) NOT NULL CHECK (monetary >= 0 AND monetary <> 'NaN'::numeric),
    recency_score smallint NOT NULL CHECK (recency_score BETWEEN 1 AND 5),
    frequency_score smallint NOT NULL CHECK (frequency_score BETWEEN 1 AND 5),
    monetary_score smallint NOT NULL CHECK (monetary_score BETWEEN 1 AND 5),
    segment text NOT NULL CHECK (segment IN ('champions', 'loyal', 'potential', 'new', 'at_risk', 'hibernating')),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (reference_date >= observation_start),
    UNIQUE (customer_id, reference_date)
);

CREATE TABLE evaluation_runs (
    evaluation_id uuid PRIMARY KEY,
    model_version_id uuid NOT NULL REFERENCES model_versions (model_version_id),
    dataset_snapshot_id text NOT NULL,
    split_strategy text NOT NULL,
    metrics jsonb NOT NULL CHECK (jsonb_typeof(metrics) = 'object'),
    limitations text NOT NULL,
    evaluated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE account_principals IS 'Authentication subject mapping; credentials/tokens remain with the selected identity boundary.';
COMMENT ON TABLE payment_transactions IS 'Stores token/provider references only; never card number or verification code.';
COMMENT ON TABLE risk_assessments IS 'Must be persisted before the application moves an order to confirmed.';
COMMENT ON TABLE order_items IS 'Immutable commercial snapshot; application must not update rows after order creation.';
COMMENT ON TABLE pricing_observations IS 'competitor_cost preserves the literal source requirement; demonstration records are synthetic.';

COMMIT;
