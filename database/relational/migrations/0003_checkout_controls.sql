-- Stage 3 commerce controls: retry-safe checkout and auditable risk review.
BEGIN;

ALTER TABLE orders
    ADD COLUMN checkout_idempotency_key text,
    ADD CONSTRAINT orders_checkout_idempotency_length
        CHECK (checkout_idempotency_key IS NULL OR length(checkout_idempotency_key) BETWEEN 16 AND 128),
    ADD CONSTRAINT orders_customer_checkout_idempotency_unique
        UNIQUE (customer_id, checkout_idempotency_key);

CREATE TABLE risk_review_decisions (
    decision_id uuid PRIMARY KEY,
    assessment_id uuid NOT NULL UNIQUE REFERENCES risk_assessments (assessment_id),
    reviewer_principal_id uuid NOT NULL REFERENCES account_principals (principal_id),
    decision text NOT NULL CHECK (decision IN ('allow', 'decline')),
    decided_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON COLUMN orders.checkout_idempotency_key IS
    'Customer-scoped checkout retry key. Application-created orders always set it.';
COMMENT ON TABLE risk_review_decisions IS
    'One immutable authorized back-office disposition for a review assessment.';

COMMIT;
