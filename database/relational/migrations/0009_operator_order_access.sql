-- Back-office order access: operators need to read the orders they fulfil.
--
-- Until now only customers could read orders (`/v1/orders`), so a confirmed
-- order was invisible to the back office except as an analytics aggregate.
-- This adds the smallest capability needed for a read-only operator queue.
BEGIN;

ALTER TABLE principal_scopes
    DROP CONSTRAINT principal_scopes_scope_check;

ALTER TABLE principal_scopes
    ADD CONSTRAINT principal_scopes_scope_check CHECK (scope IN (
        'orders:read',
        'catalog:write', 'inventory:write', 'pricing:write', 'risk:review',
        'segments:read', 'analytics:read'
    ));

COMMENT ON COLUMN principal_scopes.scope IS
    'Capability grant. orders:read is the read-only operator order queue.';

COMMIT;
