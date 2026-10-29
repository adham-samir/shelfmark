-- Machine-readable cancellation reasons.
--
-- Customers pick from a fixed list (plus "other" with free text). Storing the
-- code next to the human-readable reason keeps reporting countable without
-- parsing prose. Operator cancellations leave the code NULL.
BEGIN;

ALTER TABLE order_adjustments
    ADD COLUMN reason_code text
        CHECK (reason_code IS NULL OR reason_code IN (
            'changed_mind',
            'ordered_by_mistake',
            'wrong_item',
            'found_cheaper',
            'delivery_too_slow',
            'other'
        ));

COMMENT ON COLUMN order_adjustments.reason_code IS
    'Optional canonical cancellation reason. NULL for operator actions and for '
    'every refund row.';

COMMIT;
