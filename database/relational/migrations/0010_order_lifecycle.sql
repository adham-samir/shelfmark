-- Operator order lifecycle: fulfilment transitions, cancellation, refunds, and a
-- record of who performed each adjustment.
--
-- The order queue added in 0009 is read-only. This migration gives operators the
-- write capability and the audit tables needed to move an order forward or close
-- it without rewriting its financial history.
BEGIN;

ALTER TABLE principal_scopes
    DROP CONSTRAINT principal_scopes_scope_check;

ALTER TABLE principal_scopes
    ADD CONSTRAINT principal_scopes_scope_check CHECK (scope IN (
        'orders:read', 'orders:write',
        'catalog:write', 'inventory:write', 'pricing:write', 'risk:review',
        'segments:read', 'analytics:read'
    ));

COMMENT ON COLUMN principal_scopes.scope IS
    'Capability grant. orders:read is the operator order queue; orders:write '
    'allows fulfilment, cancellation, and refund actions.';

ALTER TABLE shipment_events
    ADD COLUMN actor_principal_id uuid REFERENCES account_principals (principal_id);

COMMENT ON COLUMN shipment_events.actor_principal_id IS
    'Operator who recorded the transition. NULL only for events created by checkout.';

CREATE TABLE order_adjustments (
    adjustment_id uuid PRIMARY KEY,
    order_id uuid NOT NULL REFERENCES orders (order_id) ON DELETE CASCADE,
    kind text NOT NULL CHECK (kind IN ('cancellation', 'refund')),
    amount numeric(20,6) NOT NULL DEFAULT 0
        CHECK (amount >= 0 AND amount <> 'NaN'::numeric),
    reason text NOT NULL CHECK (length(btrim(reason)) BETWEEN 3 AND 300),
    actor_principal_id uuid NOT NULL REFERENCES account_principals (principal_id),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        (kind = 'refund' AND amount > 0)
        OR (kind = 'cancellation' AND amount = 0)
    )
);

CREATE INDEX order_adjustments_order_time_idx
    ON order_adjustments (order_id, created_at DESC);

COMMENT ON TABLE order_adjustments IS
    'Append-only operator record of cancellations and refunds. Refunds are '
    'financial only; stock is restored only when an order is cancelled.';

COMMIT;
