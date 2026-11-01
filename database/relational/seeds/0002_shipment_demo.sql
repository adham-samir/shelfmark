-- Synthetic shipment fixtures for the demo orders.
--
-- The commerce seed marks orders as confirmed/shipped/delivered/refunded but
-- never created the matching shipment rows, so the tracking timeline on the
-- order page and the assistant's shipment grounding were always empty. This
-- seed derives one deterministic shipment per fulfilled order and a matching
-- event timeline, so the shipment surfaces demonstrate real behaviour.
--
-- Orders that were cancelled or failed payment get no shipment, which keeps the
-- "no tracking yet" path honest instead of inventing a parcel.
--
-- Synthetic development fixtures only. Safe for an empty development database.

BEGIN;

-- One shipment per fulfilled order. Identifiers are derived from the order id so
-- the fixtures stay deterministic across rebuilds.
INSERT INTO shipments (
    shipment_id, order_id, provider_reference, status, sandbox, updated_at
)
SELECT md5(o.order_id::text || ':shipment')::uuid,
       o.order_id,
       'sandbox-shipment-' || o.order_id,
       CASE o.status
           WHEN 'confirmed' THEN 'ready'
           WHEN 'shipped' THEN 'in_transit'
           ELSE 'delivered'
       END,
       true,
       o.completed_at
           + CASE o.status
                 WHEN 'confirmed' THEN interval '0 day'
                 WHEN 'shipped' THEN interval '1 day'
                 ELSE interval '2 days'
             END
FROM orders o
WHERE o.status IN ('confirmed', 'shipped', 'delivered', 'refunded')
  AND o.completed_at IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM shipments s WHERE s.order_id = o.order_id);

-- Timeline: every shipment is packed, in-transit shipments have left the depot,
-- and delivered shipments (including refunded ones, which were delivered first)
-- have arrived.
INSERT INTO shipment_events (
    shipment_event_id, shipment_id, status, description_ar, description_en, occurred_at
)
SELECT md5(o.order_id::text || ':event:ready')::uuid,
       s.shipment_id,
       'ready',
       'الشحنة اتجهزت وفي انتظار شركة التوصيل',
       'Parcel packed and ready for pickup',
       o.completed_at
FROM shipments s
JOIN orders o USING (order_id)
UNION ALL
SELECT md5(o.order_id::text || ':event:in_transit')::uuid,
       s.shipment_id,
       'in_transit',
       'الشحنة في الطريق إليك',
       'Parcel is on its way',
       o.completed_at + interval '1 day'
FROM shipments s
JOIN orders o USING (order_id)
WHERE s.status IN ('in_transit', 'delivered')
UNION ALL
SELECT md5(o.order_id::text || ':event:delivered')::uuid,
       s.shipment_id,
       'delivered',
       'تم تسليم الشحنة بنجاح',
       'Parcel delivered successfully',
       o.completed_at + interval '2 days'
FROM shipments s
JOIN orders o USING (order_id)
WHERE s.status = 'delivered';

COMMIT;
