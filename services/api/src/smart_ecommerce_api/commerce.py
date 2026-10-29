"""Customer commerce, sandbox risk, shipment, and interaction services."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

from . import db
from .catalog import DescriptiveCatalog, _decimal_text
from .commerce_models import (
    Cart,
    CartItem,
    InventoryAdjustmentResult,
    OperatorCustomer,
    OperatorOrderDetail,
    OperatorOrderList,
    OperatorOrderSummary,
    OperatorShipping,
    Order,
    OrderAdjustment,
    OrderAdjustmentResult,
    OrderItem,
    OrderList,
    OrderState,
    OrderStatus,
    OrderSummary,
    ReorderItem,
    ReorderResult,
    ReorderSkipped,
    ReviewDecisionResult,
    ReviewQueueItem,
    Shipment,
    ShipmentEvent,
    ShippingAddress,
)
from .errors import (
    Conflict,
    DependencyUnavailable,
    InvalidInput,
    ResourceNotFound,
)
from .fraud import RiskAssessor, RiskContext, RiskResult


_SHIPMENT_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"ready", "exception"},
    "ready": {"in_transit", "exception"},
    "in_transit": {"delivered", "exception"},
    "exception": {"ready"},
    "delivered": set(),
}

_SHIPMENT_DESCRIPTIONS: dict[str, tuple[str, str]] = {
    "ready": ("الشحنة جاهزة لاستلام الناقل", "Shipment ready for carrier pickup"),
    "in_transit": (
        "الشحنة في الطريق إلى العميل",
        "Shipment in transit to the customer",
    ),
    "delivered": ("تم تسليم الشحنة", "Shipment delivered"),
    "exception": ("تم تسجيل استثناء في الشحنة", "Shipment exception recorded"),
}

_ORDER_STATUS_FOR_SHIPMENT: dict[str, OrderState] = {
    "in_transit": "shipped",
    "delivered": "delivered",
}

# Canonical text for each fixed cancellation reason. The storefront shows the
# same options; `other` keeps whatever the customer typed instead.
_CANCELLATION_REASONS: dict[str, str] = {
    "changed_mind": "Changed my mind",
    "ordered_by_mistake": "Ordered by mistake",
    "wrong_item": "Wrong item or variant",
    "found_cheaper": "Found a better price",
    "delivery_too_slow": "Delivery is taking too long",
}


class PostgresCommerceStore:
    def __init__(self, dsn: str, risk_assessor: RiskAssessor) -> None:
        self._dsn = dsn
        self._risk_assessor = risk_assessor

    @staticmethod
    def _cart_from_rows(cart_id: UUID, rows: list[dict[str, Any]]) -> Cart:
        items: list[CartItem] = []
        subtotal = Decimal("0")
        for row in rows:
            if (
                row["lifecycle"] != "active"
                or row["amount"] is None
                or row["available"] is None
            ):
                raise Conflict("The cart contains a product that is no longer available.")
            items.append(
                CartItem(
                    product_id=row["product_id"],
                    quantity=row["quantity"],
                    unit_price=_decimal_text(row["amount"]),
                    available=row["available"],
                )
            )
            subtotal += row["amount"] * row["quantity"]
        return Cart(cart_id=cart_id, items=items, subtotal=_decimal_text(subtotal))

    @staticmethod
    def _open_cart(connection, customer_id: UUID, *, create: bool) -> UUID | None:
        row = connection.execute(
            "SELECT cart_id FROM carts WHERE customer_id = %s AND status = 'open' FOR UPDATE",
            (customer_id,),
        ).fetchone()
        if row:
            return row["cart_id"]
        if not create:
            return None
        return connection.execute(
            "INSERT INTO carts(cart_id, customer_id) VALUES (%s, %s) RETURNING cart_id",
            (uuid4(), customer_id),
        ).fetchone()["cart_id"]

    @staticmethod
    def _cart_rows(connection, cart_id: UUID, *, lock: bool = False):
        suffix = " FOR UPDATE OF ci, r" if lock else ""
        return connection.execute(
            """
            SELECT ci.product_id, ci.quantity, r.lifecycle, p.amount, p.currency,
                   i.available
            FROM cart_items ci
            JOIN product_registry r USING (product_id)
            LEFT JOIN product_prices p USING (product_id)
            LEFT JOIN inventory_balances i USING (product_id)
            WHERE ci.cart_id = %s
            ORDER BY ci.product_id
            """ + suffix,
            (cart_id,),
        ).fetchall()

    def _risk_context(
        self,
        connection,
        *,
        customer_id: UUID,
        amount: Decimal,
        rows: list[dict[str, Any]],
        shipping: ShippingAddress,
        payment_token: str,
    ) -> RiskContext:
        now = datetime.now(UTC)
        stats = connection.execute(
            """
            SELECT c.created_at,
                   count(o.order_id) FILTER (
                       WHERE o.status IN ('confirmed', 'shipped', 'delivered', 'refunded')
                   )::integer AS prior_orders,
                   avg(o.subtotal) FILTER (
                       WHERE o.status IN ('confirmed', 'shipped', 'delivered', 'refunded')
                   ) AS average_order_value,
                   count(o.order_id) FILTER (
                       WHERE o.created_at >= CURRENT_TIMESTAMP - interval '24 hours'
                   )::integer AS orders_last_24h,
                   count(o.order_id) FILTER (
                       WHERE o.status IN ('cancelled', 'payment_failed')
                   )::integer AS prior_failed_orders,
                   count(o.shipping_address)::integer AS address_history,
                   COALESCE(bool_or(o.shipping_address = %s), false) AS address_seen
            FROM customers c
            LEFT JOIN orders o ON o.customer_id = c.customer_id
            WHERE c.customer_id = %s
            GROUP BY c.created_at
            """,
            (shipping.address_line, customer_id),
        ).fetchone()
        if stats is None:
            raise DependencyUnavailable("The customer record is unavailable.")
        reuse = connection.execute(
            "SELECT count(*)::integer AS reuse FROM payment_transactions WHERE token_reference = %s",
            (payment_token,),
        ).fetchone()["reuse"]
        created = stats["created_at"]
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        return RiskContext(
            customer_id=customer_id,
            amount=amount,
            item_count=sum(row["quantity"] for row in rows),
            order_hour=now.hour,
            weekday=now.weekday(),
            customer_age_days=max(0, (now - created).days),
            prior_orders=stats["prior_orders"],
            average_order_value=stats["average_order_value"],
            orders_last_24h=stats["orders_last_24h"],
            prior_failed_orders=stats["prior_failed_orders"],
            new_address=stats["address_history"] > 0 and not stats["address_seen"],
            token_reuse=reuse,
        )

    def get_cart(self, customer_id: UUID) -> Cart:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                cart_id = self._open_cart(connection, customer_id, create=True)
                rows = self._cart_rows(connection, cart_id)
                return self._cart_from_rows(cart_id, rows)
        except psycopg.Error as error:
            raise DependencyUnavailable("The commerce store is unavailable.") from error

    def set_cart_item(self, customer_id: UUID, product_id: UUID, quantity: int) -> Cart:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                cart_id = self._open_cart(connection, customer_id, create=True)
                if quantity == 0:
                    connection.execute(
                        "DELETE FROM cart_items WHERE cart_id = %s AND product_id = %s",
                        (cart_id, product_id),
                    )
                else:
                    product = connection.execute(
                        """
                        SELECT r.lifecycle, p.amount, i.available
                        FROM product_registry r
                        LEFT JOIN product_prices p USING (product_id)
                        LEFT JOIN inventory_balances i USING (product_id)
                        WHERE r.product_id = %s
                        FOR UPDATE OF r
                        """,
                        (product_id,),
                    ).fetchone()
                    if (
                        product is None
                        or product["lifecycle"] != "active"
                        or product["amount"] is None
                        or product["available"] is None
                    ):
                        raise Conflict("The product is unavailable.")
                    if product["available"] < quantity:
                        raise Conflict("The requested quantity is unavailable.")
                    connection.execute(
                        """
                        INSERT INTO cart_items(cart_id, product_id, quantity)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (cart_id, product_id)
                        DO UPDATE SET quantity = EXCLUDED.quantity
                        """,
                        (cart_id, product_id, quantity),
                    )
                connection.execute(
                    "UPDATE carts SET updated_at = CURRENT_TIMESTAMP WHERE cart_id = %s",
                    (cart_id,),
                )
                rows = self._cart_rows(connection, cart_id)
                return self._cart_from_rows(cart_id, rows)
        except psycopg.Error as error:
            raise DependencyUnavailable("The commerce store is unavailable.") from error

    def reorder(self, customer_id: UUID, order_id: UUID) -> ReorderResult:
        """Add a past order's lines to the current cart, reporting every skip.

        Nothing is silently dropped: an inactive product, a missing price, or a
        shortfall is returned in `skipped` with the reason, and prices are
        rechecked at add time rather than reusing the old snapshot.
        """
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                order = connection.execute(
                    "SELECT order_id FROM orders WHERE order_id = %s AND customer_id = %s",
                    (order_id, customer_id),
                ).fetchone()
                if order is None:
                    raise ResourceNotFound("Order not found.")
                lines = connection.execute(
                    """
                    SELECT product_id, product_name_snapshot AS product_name, quantity
                    FROM order_items WHERE order_id = %s ORDER BY order_item_id
                    """,
                    (order_id,),
                ).fetchall()
                cart_id = self._open_cart(connection, customer_id, create=True)
                in_cart = {
                    row["product_id"]: row["quantity"]
                    for row in connection.execute(
                        "SELECT product_id, quantity FROM cart_items WHERE cart_id = %s",
                        (cart_id,),
                    ).fetchall()
                }
                added: list[ReorderItem] = []
                skipped: list[ReorderSkipped] = []
                for line in lines:
                    product = connection.execute(
                        """
                        SELECT r.lifecycle, p.amount, i.available
                        FROM product_registry r
                        LEFT JOIN product_prices p USING (product_id)
                        LEFT JOIN inventory_balances i USING (product_id)
                        WHERE r.product_id = %s
                        FOR UPDATE OF r
                        """,
                        (line["product_id"],),
                    ).fetchone()

                    reason = None
                    if product is None or product["lifecycle"] != "active":
                        reason = "product_inactive"
                    elif product["amount"] is None:
                        reason = "price_unavailable"

                    target = 0
                    if reason is None:
                        available = product["available"] or 0
                        wanted = in_cart.get(line["product_id"], 0) + line["quantity"]
                        target = min(wanted, available, 99)
                        if target <= 0:
                            reason = "out_of_stock"
                        elif target < wanted:
                            reason = "quantity_capped"

                    if reason is not None and reason != "quantity_capped":
                        skipped.append(
                            ReorderSkipped(
                                product_id=line["product_id"],
                                product_name=line["product_name"],
                                quantity=line["quantity"],
                                reason=reason,
                            )
                        )
                        continue

                    self._upsert_cart_item(
                        connection, cart_id, line["product_id"], target
                    )
                    in_cart[line["product_id"]] = target
                    added.append(
                        ReorderItem(
                            product_id=line["product_id"],
                            product_name=line["product_name"],
                            quantity=target,
                        )
                    )
                    if reason == "quantity_capped":
                        skipped.append(
                            ReorderSkipped(
                                product_id=line["product_id"],
                                product_name=line["product_name"],
                                quantity=line["quantity"],
                                reason="quantity_capped",
                            )
                        )

                if added:
                    connection.execute(
                        "UPDATE carts SET updated_at = CURRENT_TIMESTAMP WHERE cart_id = %s",
                        (cart_id,),
                    )
                cart = self._cart_from_rows(
                    cart_id, self._cart_rows(connection, cart_id)
                )
        except psycopg.Error as error:
            raise DependencyUnavailable("The commerce store is unavailable.") from error
        return ReorderResult(
            order_id=order_id, cart=cart, added=added, skipped=skipped
        )

    @staticmethod
    def _upsert_cart_item(connection, cart_id: UUID, product_id: UUID, quantity: int) -> None:
        connection.execute(
            """
            INSERT INTO cart_items(cart_id, product_id, quantity)
            VALUES (%s, %s, %s)
            ON CONFLICT (cart_id, product_id)
            DO UPDATE SET quantity = EXCLUDED.quantity
            """,
            (cart_id, product_id, quantity),
        )

    def checkout_product_ids(self, customer_id: UUID) -> list[UUID]:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                cart_id = self._open_cart(connection, customer_id, create=False)
                if cart_id is None:
                    raise Conflict("The cart is empty.")
                rows = connection.execute(
                    "SELECT product_id FROM cart_items WHERE cart_id = %s ORDER BY product_id",
                    (cart_id,),
                ).fetchall()
                if not rows:
                    raise Conflict("The cart is empty.")
                return [row["product_id"] for row in rows]
        except psycopg.Error as error:
            raise DependencyUnavailable("The commerce store is unavailable.") from error

    @staticmethod
    def _create_shipment(connection, order_id: UUID) -> None:
        shipment_id = uuid4()
        connection.execute(
            """
            INSERT INTO shipments(shipment_id, order_id, provider_reference, status)
            VALUES (%s, %s, %s, 'pending')
            """,
            (shipment_id, order_id, f"sandbox-shipment-{order_id}"),
        )
        connection.execute(
            """
            INSERT INTO shipment_events(
                shipment_event_id, shipment_id, status,
                description_ar, description_en, occurred_at
            ) VALUES (%s, %s, 'pending', %s, %s, CURRENT_TIMESTAMP)
            """,
            (
                uuid4(),
                shipment_id,
                "تم إنشاء الشحنة التجريبية",
                "Sandbox shipment created",
            ),
        )

    @staticmethod
    def _consume_inventory(connection, order_id: UUID, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            updated = connection.execute(
                """
                UPDATE inventory_balances
                SET on_hand = on_hand - %s,
                    version = version + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE product_id = %s AND available >= %s
                RETURNING product_id
                """,
                (row["quantity"], row["product_id"], row["quantity"]),
            ).fetchone()
            if updated is None:
                raise Conflict("Stock changed before the order could be confirmed.")
            connection.execute(
                """
                INSERT INTO inventory_movements(
                    movement_id, product_id, quantity_delta, reason,
                    reference_type, reference_id
                ) VALUES (%s, %s, %s, 'sale', 'order', %s)
                """,
                (uuid4(), row["product_id"], -row["quantity"], order_id),
            )

    def existing_checkout(self, customer_id: UUID, idempotency_key: str) -> OrderStatus | None:
        with db.connection(self._dsn, row_factory=dict_row) as connection:
            row = connection.execute(
                """
                SELECT order_id, status FROM orders
                WHERE customer_id = %s AND checkout_idempotency_key = %s
                """,
                (customer_id, idempotency_key),
            ).fetchone()
            return OrderStatus(**row) if row else None

    def checkout(
        self,
        customer_id: UUID,
        payment_token: str,
        idempotency_key: str,
        product_names: dict[str, str],
        shipping: ShippingAddress,
    ) -> OrderStatus:
        try:
            existing = self.existing_checkout(customer_id, idempotency_key)
            if existing:
                return existing
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                # Concurrent retries of one key must not race the cart transition.
                # The transaction-scoped advisory lock serializes them, so a duplicate
                # waits for the committed order and returns it instead of reporting an
                # already-converted cart as empty.
                connection.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                    (f"{customer_id}:{idempotency_key}",),
                )
                existing_row = connection.execute(
                    """
                    SELECT order_id, status FROM orders
                    WHERE customer_id = %s AND checkout_idempotency_key = %s
                    """,
                    (customer_id, idempotency_key),
                ).fetchone()
                if existing_row:
                    return OrderStatus(**existing_row)
                cart_id = self._open_cart(connection, customer_id, create=False)
                if cart_id is None:
                    raise Conflict("The cart is empty.")
                rows = self._cart_rows(connection, cart_id, lock=True)
                if not rows:
                    raise Conflict("The cart is empty.")
                if any(
                    row["lifecycle"] != "active"
                    or row["amount"] is None
                    or row["available"] is None
                    or row["available"] < row["quantity"]
                    for row in rows
                ):
                    raise Conflict("A cart item is unavailable or changed.")
                if any(str(row["product_id"]) not in product_names for row in rows):
                    raise DependencyUnavailable("A cart item is missing catalog content.")

                subtotal = sum(
                    (row["amount"] * row["quantity"] for row in rows), Decimal("0")
                )
                context = self._risk_context(
                    connection,
                    customer_id=customer_id,
                    amount=subtotal,
                    rows=rows,
                    shipping=shipping,
                    payment_token=payment_token,
                )
                order_id, transaction_id, assessment_id = uuid4(), uuid4(), uuid4()
                connection.execute(
                    """
                    INSERT INTO orders(
                        order_id, customer_id, cart_id, status, currency,
                        subtotal, checkout_idempotency_key, shipping_name,
                        shipping_phone, shipping_city, shipping_address
                    ) VALUES (%s, %s, %s, 'pending_risk', 'EGP', %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        order_id,
                        customer_id,
                        cart_id,
                        subtotal,
                        idempotency_key,
                        shipping.recipient_name,
                        shipping.phone,
                        shipping.city,
                        shipping.address_line,
                    ),
                )
                for row in rows:
                    connection.execute(
                        """
                        INSERT INTO order_items(
                            order_item_id, order_id, product_id,
                            product_name_snapshot, quantity,
                            unit_price_snapshot, currency
                        ) VALUES (%s, %s, %s, %s, %s, %s, 'EGP')
                        """,
                        (
                            uuid4(),
                            order_id,
                            row["product_id"],
                            product_names[str(row["product_id"])],
                            row["quantity"],
                            row["amount"],
                        ),
                    )
                connection.execute(
                    """
                    INSERT INTO payment_transactions(
                        transaction_id, order_id, provider_reference,
                        token_reference, amount, currency, status
                    ) VALUES (%s, %s, %s, %s, %s, 'EGP', 'prepared')
                    """,
                    (
                        transaction_id,
                        order_id,
                        f"sandbox-payment-{order_id}",
                        payment_token,
                        subtotal,
                    ),
                )

                risk = self._risk_assessor.assess(context, payment_token)
                connection.execute(
                    """
                    INSERT INTO risk_assessments(
                        assessment_id, transaction_id, model_version_id, score,
                        outcome, reasons
                    ) VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        assessment_id,
                        transaction_id,
                        risk.model_version_id,
                        risk.score,
                        risk.outcome,
                        Json(risk.reasons),
                    ),
                )
                if risk.outcome == "allow":
                    self._consume_inventory(connection, order_id, rows)
                    connection.execute(
                        "UPDATE payment_transactions SET status = 'authorized', updated_at = CURRENT_TIMESTAMP WHERE transaction_id = %s",
                        (transaction_id,),
                    )
                    connection.execute(
                        "UPDATE orders SET status = 'confirmed', completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE order_id = %s",
                        (order_id,),
                    )
                    self._create_shipment(connection, order_id)
                    status = "confirmed"
                else:
                    connection.execute(
                        "UPDATE orders SET status = 'review', updated_at = CURRENT_TIMESTAMP WHERE order_id = %s",
                        (order_id,),
                    )
                    status = "review"
                connection.execute(
                    "UPDATE carts SET status = 'converted', updated_at = CURRENT_TIMESTAMP WHERE cart_id = %s",
                    (cart_id,),
                )
                return OrderStatus(order_id=order_id, status=status)
        except psycopg.errors.UniqueViolation:
            existing = self.existing_checkout(customer_id, idempotency_key)
            if existing:
                return existing
            raise
        except psycopg.Error as error:
            raise DependencyUnavailable("The commerce store is unavailable.") from error

    def get_order(self, customer_id: UUID, order_id: UUID) -> Order:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                order = connection.execute(
                    """
                    SELECT order_id, status, currency, subtotal, created_at
                    FROM orders WHERE order_id = %s AND customer_id = %s
                    """,
                    (order_id, customer_id),
                ).fetchone()
                if order is None:
                    raise ResourceNotFound("Order not found.")
                rows = connection.execute(
                    """
                    SELECT product_id, product_name_snapshot AS product_name,
                           quantity, unit_price_snapshot, line_total
                    FROM order_items WHERE order_id = %s ORDER BY order_item_id
                    """,
                    (order_id,),
                ).fetchall()
                return Order(
                    **{
                        **order,
                        "subtotal": _decimal_text(order["subtotal"]),
                        "items": [
                            OrderItem(
                                product_id=row["product_id"],
                                product_name=row["product_name"],
                                quantity=row["quantity"],
                                unit_price=_decimal_text(row["unit_price_snapshot"]),
                                line_total=_decimal_text(row["line_total"]),
                            )
                            for row in rows
                        ],
                    }
                )
        except psycopg.Error as error:
            raise DependencyUnavailable("The commerce store is unavailable.") from error

    def list_orders(
        self, customer_id: UUID, *, limit: int = 20, offset: int = 0
    ) -> OrderList:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                total = connection.execute(
                    "SELECT count(*) AS total FROM orders WHERE customer_id = %s",
                    (customer_id,),
                ).fetchone()["total"]
                rows = connection.execute(
                    """
                    SELECT o.order_id, o.status, o.currency, o.subtotal, o.created_at,
                           COALESCE(sum(oi.quantity), 0)::int AS item_count
                    FROM orders o
                    LEFT JOIN order_items oi USING (order_id)
                    WHERE o.customer_id = %s
                    GROUP BY o.order_id
                    ORDER BY o.created_at DESC, o.order_id
                    LIMIT %s OFFSET %s
                    """,
                    (customer_id, limit, offset),
                ).fetchall()
                return OrderList(
                    total=total,
                    limit=limit,
                    offset=offset,
                    items=[
                        OrderSummary(
                            order_id=row["order_id"],
                            status=row["status"],
                            currency=row["currency"],
                            subtotal=_decimal_text(row["subtotal"]),
                            item_count=row["item_count"],
                            created_at=row["created_at"],
                        )
                        for row in rows
                    ],
                )
        except psycopg.Error as error:
            raise DependencyUnavailable("The commerce store is unavailable.") from error

    @staticmethod
    def _shipment_for_order(
        connection, order_id: UUID
    ) -> Shipment | None:
        shipment = connection.execute(
            "SELECT shipment_id, status, updated_at FROM shipments WHERE order_id = %s",
            (order_id,),
        ).fetchone()
        if shipment is None:
            return None
        events = connection.execute(
            """
            SELECT status, description_ar, description_en, occurred_at
            FROM shipment_events WHERE shipment_id = %s ORDER BY occurred_at
            """,
            (shipment["shipment_id"],),
        ).fetchall()
        return Shipment(
            **shipment,
            events=[ShipmentEvent(**event) for event in events],
        )

    def operator_list_orders(
        self,
        *,
        status: OrderState | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> OperatorOrderList:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                total = connection.execute(
                    """
                    SELECT count(*) AS total
                    FROM orders o
                    WHERE (%s::text IS NULL OR o.status = %s)
                    """,
                    (status, status),
                ).fetchone()["total"]
                rows = connection.execute(
                    """
                    SELECT o.order_id, o.status, o.currency, o.subtotal,
                           o.refund_total, o.created_at,
                           COALESCE(sum(oi.quantity), 0)::int AS item_count,
                           c.customer_id, c.email AS customer_email,
                           c.display_name AS customer_name
                    FROM orders o
                    JOIN customers c USING (customer_id)
                    LEFT JOIN order_items oi USING (order_id)
                    WHERE (%s::text IS NULL OR o.status = %s)
                    GROUP BY o.order_id, c.customer_id
                    ORDER BY o.created_at DESC, o.order_id
                    LIMIT %s OFFSET %s
                    """,
                    (status, status, limit, offset),
                ).fetchall()
                return OperatorOrderList(
                    total=total,
                    limit=limit,
                    offset=offset,
                    status=status,
                    items=[
                        OperatorOrderSummary(
                            order_id=row["order_id"],
                            status=row["status"],
                            currency=row["currency"],
                            subtotal=_decimal_text(row["subtotal"]),
                            refund_total=_decimal_text(row["refund_total"]),
                            item_count=row["item_count"],
                            created_at=row["created_at"],
                            customer=OperatorCustomer(
                                customer_id=row["customer_id"],
                                email=row["customer_email"],
                                display_name=row["customer_name"],
                            ),
                        )
                        for row in rows
                    ],
                )
        except psycopg.Error as error:
            raise DependencyUnavailable("The commerce store is unavailable.") from error

    @staticmethod
    def _adjustments_for_order(connection, order_id: UUID) -> list[OrderAdjustment]:
        rows = connection.execute(
            """
            SELECT a.adjustment_id, a.kind, a.amount, a.reason, a.reason_code,
                   a.created_at, p.account_type,
                   COALESCE(c.display_name, p.login_email, 'Operator') AS actor_name
            FROM order_adjustments a
            JOIN account_principals p ON p.principal_id = a.actor_principal_id
            LEFT JOIN customers c ON c.customer_id = p.customer_id
            WHERE a.order_id = %s
            ORDER BY a.created_at, a.adjustment_id
            """,
            (order_id,),
        ).fetchall()
        return [
            OrderAdjustment(
                adjustment_id=row["adjustment_id"],
                kind=row["kind"],
                amount=_decimal_text(row["amount"]),
                reason=row["reason"],
                reason_code=row["reason_code"],
                actor_kind=(
                    "operator" if row["account_type"] == "backoffice" else "customer"
                ),
                actor_name=row["actor_name"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def operator_get_order(self, order_id: UUID) -> OperatorOrderDetail:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                row = connection.execute(
                    """
                    SELECT o.order_id, o.status, o.currency, o.subtotal,
                           o.refund_total, o.created_at, o.completed_at,
                           o.shipping_name, o.shipping_phone, o.shipping_city,
                           o.shipping_address,
                           c.customer_id, c.email AS customer_email,
                           c.display_name AS customer_name
                    FROM orders o
                    JOIN customers c USING (customer_id)
                    WHERE o.order_id = %s
                    """,
                    (order_id,),
                ).fetchone()
                if row is None:
                    raise ResourceNotFound("Order not found.")
                items = connection.execute(
                    """
                    SELECT product_id, product_name_snapshot AS product_name,
                           quantity, unit_price_snapshot, line_total
                    FROM order_items WHERE order_id = %s ORDER BY order_item_id
                    """,
                    (order_id,),
                ).fetchall()
                shipping = None
                if any(
                    row[field]
                    for field in (
                        "shipping_name",
                        "shipping_phone",
                        "shipping_city",
                        "shipping_address",
                    )
                ):
                    shipping = OperatorShipping(
                        recipient_name=row["shipping_name"],
                        phone=row["shipping_phone"],
                        city=row["shipping_city"],
                        address_line=row["shipping_address"],
                    )
                return OperatorOrderDetail(
                    order_id=row["order_id"],
                    status=row["status"],
                    currency=row["currency"],
                    subtotal=_decimal_text(row["subtotal"]),
                    refund_total=_decimal_text(row["refund_total"]),
                    created_at=row["created_at"],
                    completed_at=row["completed_at"],
                    customer=OperatorCustomer(
                        customer_id=row["customer_id"],
                        email=row["customer_email"],
                        display_name=row["customer_name"],
                    ),
                    shipping=shipping,
                    items=[
                        OrderItem(
                            product_id=item["product_id"],
                            product_name=item["product_name"],
                            quantity=item["quantity"],
                            unit_price=_decimal_text(item["unit_price_snapshot"]),
                            line_total=_decimal_text(item["line_total"]),
                        )
                        for item in items
                    ],
                    shipment=self._shipment_for_order(connection, order_id),
                    adjustments=self._adjustments_for_order(connection, order_id),
                )
        except psycopg.Error as error:
            raise DependencyUnavailable("The commerce store is unavailable.") from error

    def operator_transition_shipment(
        self,
        order_id: UUID,
        target: str,
        actor_principal_id: UUID,
    ) -> Shipment:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                record = connection.execute(
                    """
                    SELECT s.shipment_id, s.status, o.status AS order_status
                    FROM shipments s
                    JOIN orders o USING (order_id)
                    WHERE s.order_id = %s
                    FOR UPDATE OF s, o
                    """,
                    (order_id,),
                ).fetchone()
                if record is None:
                    raise ResourceNotFound("Shipment not found.")
                current = record["status"]
                if target != current:
                    if target not in _SHIPMENT_TRANSITIONS.get(current, set()):
                        raise Conflict(
                            f"Shipment cannot move from {current} to {target}."
                        )
                    if record["order_status"] not in (
                        "confirmed",
                        "shipped",
                        "delivered",
                    ):
                        raise Conflict("The order is not open for fulfilment.")
                    description_ar, description_en = _SHIPMENT_DESCRIPTIONS[target]
                    connection.execute(
                        """
                        UPDATE shipments
                        SET status = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE shipment_id = %s
                        """,
                        (target, record["shipment_id"]),
                    )
                    connection.execute(
                        """
                        INSERT INTO shipment_events(
                            shipment_event_id, shipment_id, status,
                            description_ar, description_en, occurred_at,
                            actor_principal_id
                        ) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                        """,
                        (
                            uuid4(),
                            record["shipment_id"],
                            target,
                            description_ar,
                            description_en,
                            actor_principal_id,
                        ),
                    )
                    order_status = _ORDER_STATUS_FOR_SHIPMENT.get(target)
                    if order_status is not None:
                        connection.execute(
                            """
                            UPDATE orders
                            SET status = %s,
                                completed_at = CASE
                                    WHEN %s = 'delivered'
                                    THEN COALESCE(completed_at, CURRENT_TIMESTAMP)
                                    ELSE completed_at
                                END,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE order_id = %s
                            """,
                            (order_status, target, order_id),
                        )
                shipment = self._shipment_for_order(connection, order_id)
                if shipment is None:
                    raise ResourceNotFound("Shipment not found.")
                return shipment
        except psycopg.Error as error:
            raise DependencyUnavailable("The commerce store is unavailable.") from error

    @staticmethod
    def _restore_order_inventory(connection, order_id: UUID) -> None:
        """Return the stock an order actually removed, and only that.

        The `sale` movements are the authority, not `order_items`. Seeded
        historical orders predate the movement ledger, so they have no `sale`
        rows and must restore nothing rather than inflating stock.
        """
        items = connection.execute(
            """
            SELECT product_id, sum(-quantity_delta)::int AS quantity
            FROM inventory_movements
            WHERE reference_type = 'order' AND reference_id = %s
                  AND reason = 'sale'
            GROUP BY product_id
            ORDER BY product_id
            """,
            (order_id,),
        ).fetchall()
        for item in items:
            connection.execute(
                """
                UPDATE inventory_balances
                SET on_hand = on_hand + %s,
                    version = version + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE product_id = %s
                """,
                (item["quantity"], item["product_id"]),
            )
            connection.execute(
                """
                INSERT INTO inventory_movements(
                    movement_id, product_id, quantity_delta, reason,
                    reference_type, reference_id
                ) VALUES (%s, %s, %s, 'release', 'order_cancellation', %s)
                """,
                (uuid4(), item["product_id"], item["quantity"], order_id),
            )

    def _cancel_order_locked(
        self,
        connection,
        order: dict[str, Any],
        reason: str,
        actor_principal_id: UUID,
        reason_code: str | None = None,
    ) -> OrderAdjustmentResult:
        """Cancel an order that the caller already locked with `FOR UPDATE`.

        Shared by the operator and customer surfaces so the two can never drift
        on stock restoration, payment state, shipment state, or the audit row.
        """
        order_id = order["order_id"]
        if order["status"] not in (
            "pending_payment",
            "pending_risk",
            "review",
            "confirmed",
        ):
            raise Conflict("Only an order that has not shipped can be cancelled.")

        if order["status"] == "confirmed":
            self._restore_order_inventory(connection, order_id)

        connection.execute(
            """
            UPDATE orders
            SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
            WHERE order_id = %s
            """,
            (order_id,),
        )
        connection.execute(
            """
            UPDATE payment_transactions
            SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
            WHERE order_id = %s AND status IN ('prepared', 'authorized')
            """,
            (order_id,),
        )
        shipment = connection.execute(
            """
            UPDATE shipments
            SET status = 'exception', updated_at = CURRENT_TIMESTAMP
            WHERE order_id = %s AND status <> 'delivered'
            RETURNING shipment_id
            """,
            (order_id,),
        ).fetchone()
        if shipment is not None:
            connection.execute(
                """
                INSERT INTO shipment_events(
                    shipment_event_id, shipment_id, status,
                    description_ar, description_en, occurred_at,
                    actor_principal_id
                ) VALUES (%s, %s, 'exception', %s, %s,
                          CURRENT_TIMESTAMP, %s)
                """,
                (
                    uuid4(),
                    shipment["shipment_id"],
                    "أُلغيت الشحنة مع الطلب",
                    "Shipment cancelled with the order",
                    actor_principal_id,
                ),
            )

        adjustment = connection.execute(
            """
            INSERT INTO order_adjustments(
                adjustment_id, order_id, kind, amount, reason,
                actor_principal_id, reason_code
            ) VALUES (%s, %s, 'cancellation', 0, %s, %s, %s)
            RETURNING adjustment_id, created_at
            """,
            (uuid4(), order_id, reason, actor_principal_id, reason_code),
        ).fetchone()
        return OrderAdjustmentResult(
            order_id=order_id,
            status="cancelled",
            refund_total=_decimal_text(order["refund_total"]),
            adjustment_id=adjustment["adjustment_id"],
            kind="cancellation",
            amount="0",
            created_at=adjustment["created_at"],
        )

    def customer_cancel_order(
        self,
        customer_id: UUID,
        order_id: UUID,
        reason_code: str,
        reason: str | None,
        actor_principal_id: UUID,
    ) -> OrderAdjustmentResult:
        """Cancel an own order before it ships.

        The stored reason is always human-readable. A fixed code is expanded to
        canonical text so reporting stays countable; `other` keeps the customer's
        own words and requires them.
        """
        text = (
            reason.strip()
            if reason_code == "other" and reason and reason.strip()
            else _CANCELLATION_REASONS.get(reason_code)
        )
        if text is None:
            raise InvalidInput("Choose a cancellation reason and describe it.")
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                order = connection.execute(
                    """
                    SELECT order_id, status, subtotal, refund_total
                    FROM orders
                    WHERE order_id = %s AND customer_id = %s
                    FOR UPDATE
                    """,
                    (order_id, customer_id),
                ).fetchone()
                if order is None:
                    raise ResourceNotFound("Order not found.")
                return self._cancel_order_locked(
                    connection, order, text, actor_principal_id, reason_code
                )
        except psycopg.Error as error:
            raise DependencyUnavailable("The commerce store is unavailable.") from error

    def operator_cancel_order(
        self,
        order_id: UUID,
        reason: str,
        actor_principal_id: UUID,
    ) -> OrderAdjustmentResult:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                order = connection.execute(
                    """
                    SELECT order_id, status, subtotal, refund_total
                    FROM orders WHERE order_id = %s
                    FOR UPDATE
                    """,
                    (order_id,),
                ).fetchone()
                if order is None:
                    raise ResourceNotFound("Order not found.")
                return self._cancel_order_locked(
                    connection, order, reason, actor_principal_id
                )
        except psycopg.Error as error:
            raise DependencyUnavailable("The commerce store is unavailable.") from error

    def operator_refund_order(
        self,
        order_id: UUID,
        amount: str,
        reason: str,
        actor_principal_id: UUID,
    ) -> OrderAdjustmentResult:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                order = connection.execute(
                    """
                    SELECT order_id, status, subtotal, refund_total
                    FROM orders WHERE order_id = %s
                    FOR UPDATE
                    """,
                    (order_id,),
                ).fetchone()
                if order is None:
                    raise ResourceNotFound("Order not found.")
                if order["status"] not in ("confirmed", "shipped", "delivered"):
                    raise Conflict(
                        "Only a confirmed, shipped, or delivered order can be refunded."
                    )
                requested = Decimal(amount)
                remaining = order["subtotal"] - order["refund_total"]
                if requested <= 0 or requested > remaining:
                    raise Conflict(
                        "The refund must be positive and no more than the remaining total."
                    )
                refund_total = order["refund_total"] + requested
                status: OrderState = (
                    "refunded" if refund_total == order["subtotal"] else order["status"]
                )
                connection.execute(
                    """
                    UPDATE orders
                    SET refund_total = %s, status = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE order_id = %s
                    """,
                    (refund_total, status, order_id),
                )
                if status == "refunded":
                    connection.execute(
                        """
                        UPDATE payment_transactions
                        SET status = 'refunded', updated_at = CURRENT_TIMESTAMP
                        WHERE order_id = %s
                        """,
                        (order_id,),
                    )
                adjustment = connection.execute(
                    """
                    INSERT INTO order_adjustments(
                        adjustment_id, order_id, kind, amount, reason,
                        actor_principal_id
                    ) VALUES (%s, %s, 'refund', %s, %s, %s)
                    RETURNING adjustment_id, created_at
                    """,
                    (uuid4(), order_id, requested, reason, actor_principal_id),
                ).fetchone()
                return OrderAdjustmentResult(
                    order_id=order_id,
                    status=status,
                    refund_total=_decimal_text(refund_total),
                    adjustment_id=adjustment["adjustment_id"],
                    kind="refund",
                    amount=_decimal_text(requested),
                    created_at=adjustment["created_at"],
                )
        except psycopg.Error as error:
            raise DependencyUnavailable("The commerce store is unavailable.") from error

    def operator_adjust_inventory(
        self,
        product_id: UUID,
        quantity_delta: int,
        reason: str,
        actor_principal_id: UUID,
    ) -> InventoryAdjustmentResult:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                balance = connection.execute(
                    """
                    SELECT product_id, on_hand, reserved
                    FROM inventory_balances WHERE product_id = %s
                    FOR UPDATE
                    """,
                    (product_id,),
                ).fetchone()
                if balance is None:
                    raise ResourceNotFound("Inventory balance not found.")
                if balance["on_hand"] + quantity_delta < balance["reserved"]:
                    raise Conflict(
                        "The adjustment would leave less stock than is reserved."
                    )
                updated = connection.execute(
                    """
                    UPDATE inventory_balances
                    SET on_hand = on_hand + %s,
                        version = version + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE product_id = %s
                    RETURNING on_hand, reserved, available
                    """,
                    (quantity_delta, product_id),
                ).fetchone()
                movement_id = uuid4()
                movement = connection.execute(
                    """
                    INSERT INTO inventory_movements(
                        movement_id, product_id, quantity_delta, reason,
                        reference_type, reference_id
                    ) VALUES (%s, %s, %s, 'adjustment', 'operator', %s)
                    RETURNING occurred_at
                    """,
                    (movement_id, product_id, quantity_delta, actor_principal_id),
                ).fetchone()
                return InventoryAdjustmentResult(
                    product_id=product_id,
                    on_hand=updated["on_hand"],
                    reserved=updated["reserved"],
                    available=updated["available"],
                    movement_id=movement_id,
                    occurred_at=movement["occurred_at"],
                )
        except psycopg.Error as error:
            raise DependencyUnavailable("The commerce store is unavailable.") from error

    def get_shipment(self, customer_id: UUID, order_id: UUID) -> Shipment:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                shipment = connection.execute(
                    """
                    SELECT s.shipment_id, s.status, s.updated_at
                    FROM shipments s JOIN orders o USING (order_id)
                    WHERE o.order_id = %s AND o.customer_id = %s
                    """,
                    (order_id, customer_id),
                ).fetchone()
                if shipment is None:
                    raise ResourceNotFound("Shipment not found.")
                events = connection.execute(
                    """
                    SELECT status, description_ar, description_en, occurred_at
                    FROM shipment_events WHERE shipment_id = %s ORDER BY occurred_at
                    """,
                    (shipment["shipment_id"],),
                ).fetchall()
                return Shipment(
                    **shipment,
                    events=[ShipmentEvent(**event) for event in events],
                )
        except psycopg.Error as error:
            raise DependencyUnavailable("The commerce store is unavailable.") from error

    def record_event(
        self,
        customer_id: UUID,
        *,
        event_id: UUID,
        session_id: UUID,
        product_id: UUID,
        event_type: str,
        occurred_at: datetime,
        context: dict[str, Any],
    ) -> None:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                active = connection.execute(
                    "SELECT 1 FROM product_registry WHERE product_id = %s AND lifecycle = 'active'",
                    (product_id,),
                ).fetchone()
                if active is None:
                    raise ResourceNotFound("Product not found.")
                connection.execute(
                    """
                    INSERT INTO browsing_events(
                        event_id, customer_id, session_id, product_id,
                        event_type, occurred_at, provenance_class, context
                    ) VALUES (%s, %s, %s, %s, %s, %s, 'synthetic', %s::jsonb)
                    ON CONFLICT (event_id) DO NOTHING
                    """,
                    (
                        event_id,
                        customer_id,
                        session_id,
                        product_id,
                        event_type,
                        occurred_at,
                        Json(context),
                    ),
                )
        except psycopg.Error as error:
            raise DependencyUnavailable("The interaction store is unavailable.") from error

    def decide_review(
        self,
        reviewer_principal_id: UUID,
        assessment_id: UUID,
        decision: str,
    ) -> ReviewDecisionResult:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                record = connection.execute(
                    """
                    SELECT a.assessment_id, t.transaction_id, t.order_id, o.status
                    FROM risk_assessments a
                    JOIN payment_transactions t USING (transaction_id)
                    JOIN orders o USING (order_id)
                    WHERE a.assessment_id = %s
                    FOR UPDATE OF a, t, o
                    """,
                    (assessment_id,),
                ).fetchone()
                if record is None:
                    raise ResourceNotFound("Risk assessment not found.")
                if record["status"] != "review":
                    raise Conflict("The assessment is no longer awaiting review.")
                existing = connection.execute(
                    "SELECT 1 FROM risk_review_decisions WHERE assessment_id = %s",
                    (assessment_id,),
                ).fetchone()
                if existing:
                    raise Conflict("The assessment already has a review decision.")

                if decision == "allow":
                    rows = connection.execute(
                        """
                        SELECT oi.product_id, oi.quantity
                        FROM order_items oi
                        JOIN inventory_balances i USING (product_id)
                        WHERE oi.order_id = %s
                        ORDER BY oi.product_id
                        FOR UPDATE OF i
                        """,
                        (record["order_id"],),
                    ).fetchall()
                    self._consume_inventory(connection, record["order_id"], rows)
                    connection.execute(
                        "UPDATE payment_transactions SET status = 'authorized', updated_at = CURRENT_TIMESTAMP WHERE transaction_id = %s",
                        (record["transaction_id"],),
                    )
                    connection.execute(
                        "UPDATE orders SET status = 'confirmed', completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE order_id = %s",
                        (record["order_id"],),
                    )
                    self._create_shipment(connection, record["order_id"])
                    status = "confirmed"
                else:
                    connection.execute(
                        "UPDATE payment_transactions SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP WHERE transaction_id = %s",
                        (record["transaction_id"],),
                    )
                    connection.execute(
                        "UPDATE orders SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP WHERE order_id = %s",
                        (record["order_id"],),
                    )
                    status = "cancelled"
                connection.execute(
                    """
                    INSERT INTO risk_review_decisions(
                        decision_id, assessment_id, reviewer_principal_id, decision
                    ) VALUES (%s, %s, %s, %s)
                    """,
                    (uuid4(), assessment_id, reviewer_principal_id, decision),
                )
                return ReviewDecisionResult(
                    assessment_id=assessment_id,
                    order_id=record["order_id"],
                    status=status,
                )
        except psycopg.Error as error:
            raise DependencyUnavailable("The commerce store is unavailable.") from error

    def list_risk_reviews(self) -> list[ReviewQueueItem]:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                rows = connection.execute(
                    """
                    SELECT a.assessment_id, o.order_id, o.customer_id, a.score,
                           a.outcome, o.subtotal, a.assessed_at, a.reasons,
                           mv.version_label AS model_version
                    FROM risk_assessments a
                    JOIN payment_transactions t USING (transaction_id)
                    JOIN orders o USING (order_id)
                    LEFT JOIN model_versions mv USING (model_version_id)
                    WHERE o.status = 'review'
                      AND NOT EXISTS (
                          SELECT 1 FROM risk_review_decisions d
                          WHERE d.assessment_id = a.assessment_id
                      )
                    ORDER BY a.assessed_at
                    """
                ).fetchall()
                return [
                    ReviewQueueItem(
                        assessment_id=row["assessment_id"],
                        order_id=row["order_id"],
                        customer_id=row["customer_id"],
                        score=_decimal_text(row["score"]) if row["score"] is not None else None,
                        outcome=row["outcome"],
                        subtotal=_decimal_text(row["subtotal"]),
                        assessed_at=row["assessed_at"],
                        model_version=row["model_version"],
                        reasons=list(row["reasons"] or []),
                    )
                    for row in rows
                ]
        except psycopg.Error as error:
            raise DependencyUnavailable("The commerce store is unavailable.") from error


class CommerceService:
    def __init__(
        self, store: PostgresCommerceStore, descriptive: DescriptiveCatalog
    ) -> None:
        self._store = store
        self._descriptive = descriptive

    def get_cart(self, customer_id: UUID) -> Cart:
        return self._store.get_cart(customer_id)

    def set_cart_item(self, customer_id: UUID, product_id: UUID, quantity: int) -> Cart:
        return self._store.set_cart_item(customer_id, product_id, quantity)

    def reorder(self, customer_id: UUID, order_id: UUID) -> ReorderResult:
        return self._store.reorder(customer_id, order_id)

    def checkout(
        self,
        customer_id: UUID,
        payment_token: str,
        idempotency_key: str,
        shipping: ShippingAddress,
    ) -> OrderStatus:
        existing = self._store.existing_checkout(customer_id, idempotency_key)
        if existing:
            return existing
        product_ids = self._store.checkout_product_ids(customer_id)
        records = self._descriptive.get_many(product_ids)
        names = {
            identifier: record["name"]
            for identifier, record in records.items()
            if isinstance(record.get("name"), str) and record["name"].strip()
        }
        if len(names) != len(product_ids):
            raise DependencyUnavailable("A cart item is missing catalog content.")
        return self._store.checkout(
            customer_id, payment_token, idempotency_key, names, shipping
        )

    def get_order(self, customer_id: UUID, order_id: UUID) -> Order:
        return self._store.get_order(customer_id, order_id)

    def list_orders(
        self, customer_id: UUID, *, limit: int = 20, offset: int = 0
    ) -> OrderList:
        return self._store.list_orders(customer_id, limit=limit, offset=offset)

    def operator_list_orders(
        self,
        *,
        status: OrderState | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> OperatorOrderList:
        return self._store.operator_list_orders(
            status=status, limit=limit, offset=offset
        )

    def operator_get_order(self, order_id: UUID) -> OperatorOrderDetail:
        return self._store.operator_get_order(order_id)

    def operator_transition_shipment(
        self, order_id: UUID, target: str, actor_principal_id: UUID
    ) -> Shipment:
        return self._store.operator_transition_shipment(
            order_id, target, actor_principal_id
        )

    def customer_cancel_order(
        self,
        customer_id: UUID,
        order_id: UUID,
        reason_code: str,
        reason: str | None,
        actor_principal_id: UUID,
    ) -> OrderAdjustmentResult:
        return self._store.customer_cancel_order(
            customer_id, order_id, reason_code, reason, actor_principal_id
        )

    def operator_cancel_order(
        self, order_id: UUID, reason: str, actor_principal_id: UUID
    ) -> OrderAdjustmentResult:
        return self._store.operator_cancel_order(
            order_id, reason, actor_principal_id
        )

    def operator_refund_order(
        self,
        order_id: UUID,
        amount: str,
        reason: str,
        actor_principal_id: UUID,
    ) -> OrderAdjustmentResult:
        return self._store.operator_refund_order(
            order_id, amount, reason, actor_principal_id
        )

    def operator_adjust_inventory(
        self,
        product_id: UUID,
        quantity_delta: int,
        reason: str,
        actor_principal_id: UUID,
    ) -> InventoryAdjustmentResult:
        return self._store.operator_adjust_inventory(
            product_id, quantity_delta, reason, actor_principal_id
        )

    def get_shipment(self, customer_id: UUID, order_id: UUID) -> Shipment:
        return self._store.get_shipment(customer_id, order_id)

    def record_event(self, customer_id: UUID, **event: Any) -> None:
        self._store.record_event(customer_id, **event)

    def decide_review(
        self, reviewer_principal_id: UUID, assessment_id: UUID, decision: str
    ) -> ReviewDecisionResult:
        return self._store.decide_review(
            reviewer_principal_id, assessment_id, decision
        )

    def list_risk_reviews(self) -> list[ReviewQueueItem]:
        return self._store.list_risk_reviews()
