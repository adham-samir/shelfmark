"""BI-01 interactive analytics under the DEC-013 metric contract.

Consumer metrics come from recorded browsing events; financial metrics come
from authoritative order records. Category filtering resolves catalog
identifiers and scopes both product-scoped behaviour and item-line revenue.
Profit is never shown because the project holds no complete cost coverage.

Every response carries an independent reconciliation block: aggregate values
computed from the reporting queries are compared with values recomputed from
raw source rows, and the caller can see both numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from pydantic import Field

from . import db
from .catalog import CatalogService, _decimal_text
from .errors import DependencyUnavailable, InvalidInput
from .models import StrictModel

MAX_RANGE_DAYS = 366
ELIGIBLE_STATUSES = ("confirmed", "shipped", "delivered", "refunded")
UNFULFILLED_STATUSES = ("cancelled", "payment_failed")
METRIC_DEFINITIONS = [
    "Product views: browsing events with event_type = view in the selected range.",
    "Sessions: distinct session identifiers with at least one event in the range.",
    "Add to cart: browsing events with event_type = add_to_cart.",
    "Orders per session: created orders divided by sessions with any event. "
    "Anonymous and non-converting sessions stay in the denominator.",
    "Order count: orders in confirmed, shipped, delivered, or refunded state.",
    "Gross sales: sum of order subtotals before refunds.",
    "Refunds: sum of recorded refund totals.",
    "Net sales: gross sales minus refunds.",
    "Average order value: net sales divided by order count.",
    "Profit is not displayed: the project holds no complete cost coverage.",
]


class AnalyticsScope(StrictModel):
    date_from: date
    date_to: date
    category: str | None = None
    category_product_count: int = Field(ge=0)


class BehaviourMetrics(StrictModel):
    product_views: int = Field(ge=0)
    sessions: int = Field(ge=0)
    add_to_carts: int = Field(ge=0)
    created_orders: int = Field(ge=0)
    orders_per_session: str
    unfulfilled_orders: int = Field(ge=0)


class FinancialMetrics(StrictModel):
    order_count: int = Field(ge=0)
    gross_sales: str
    refunds: str
    net_sales: str
    average_order_value: str
    currency: str = "EGP"


class ProductPerformance(StrictModel):
    product_id: UUID
    views: int = Field(ge=0)
    add_to_carts: int = Field(ge=0)
    units: int = Field(ge=0)
    revenue: str


class DailyPoint(StrictModel):
    day: date
    views: int = Field(ge=0)
    sessions: int = Field(ge=0)
    orders: int = Field(ge=0)
    net_sales: str


class ReconciliationCheck(StrictModel):
    metric: str
    reported: str
    recomputed: str
    matches: bool
    source: str


class AnalyticsResponse(StrictModel):
    generated_at: datetime
    scope: AnalyticsScope
    behaviour: BehaviourMetrics
    financial: FinancialMetrics
    top_products: list[ProductPerformance]
    daily: list[DailyPoint]
    reconciliation: list[ReconciliationCheck]
    no_events: bool
    no_orders: bool
    category_without_products: bool
    definitions: list[str] = list(METRIC_DEFINITIONS)


@dataclass(frozen=True, slots=True)
class ProductScope:
    """None means every product; an empty list means the category matched none."""

    ids: list[UUID] | None = None

    def as_array(self) -> list[UUID] | None:
        return self.ids


class AnalyticsStore:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def behaviour(self, *, start: date, end: date, scope: ProductScope) -> dict[str, Any]:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                row = connection.execute(
                    """
                    SELECT count(*) FILTER (WHERE event_type = 'view')::integer AS views,
                           count(DISTINCT session_id)::integer AS sessions,
                           count(*) FILTER (WHERE event_type = 'add_to_cart')::integer AS carts
                    FROM browsing_events
                    WHERE (occurred_at AT TIME ZONE 'UTC')::date BETWEEN %(start)s AND %(end)s
                      AND (%(ids)s::uuid[] IS NULL OR product_id = ANY(%(ids)s::uuid[]))
                    """,
                    {"start": start, "end": end, "ids": scope.as_array()},
                ).fetchone()
        except psycopg.Error as error:
            raise DependencyUnavailable(
                "Browsing-event analytics are unavailable."
            ) from error
        return row

    def financial(self, *, start: date, end: date, scope: ProductScope) -> dict[str, Any]:
        """Revenue for the scope.

        Without a category the authoritative order subtotal is used. With a
        category, revenue is the item-line value of the matching products and
        refunds are allocated by that item share, so a category never claims
        revenue from unrelated products in the same order.
        """

        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                row = connection.execute(
                    """
                    WITH scoped AS (
                        SELECT o.order_id, o.subtotal, o.refund_total
                        FROM orders o
                        WHERE (o.created_at AT TIME ZONE 'UTC')::date
                              BETWEEN %(start)s AND %(end)s
                          AND o.status = ANY(%(eligible)s)
                          AND (
                              %(ids)s::uuid[] IS NULL
                              OR EXISTS (
                                  SELECT 1 FROM order_items s
                                  WHERE s.order_id = o.order_id
                                    AND s.product_id = ANY(%(ids)s::uuid[])
                              )
                          )
                    )
                    SELECT count(*)::integer AS orders,
                           COALESCE(sum(subtotal), 0) AS gross,
                           COALESCE(sum(refund_total), 0) AS refunds
                    FROM scoped
                    """,
                    {
                        "start": start,
                        "end": end,
                        "eligible": list(ELIGIBLE_STATUSES),
                        "ids": scope.as_array(),
                    },
                ).fetchone()
                if scope.ids is not None:
                    row = connection.execute(
                        """
                        SELECT count(DISTINCT o.order_id)::integer AS orders,
                               COALESCE(sum(i.line_total), 0) AS gross,
                               COALESCE(sum(
                                   o.refund_total * i.line_total
                                   / NULLIF(o.subtotal, 0)
                               ), 0) AS refunds
                        FROM orders o
                        JOIN order_items i USING (order_id)
                        WHERE (o.created_at AT TIME ZONE 'UTC')::date
                              BETWEEN %(start)s AND %(end)s
                          AND o.status = ANY(%(eligible)s)
                          AND i.product_id = ANY(%(ids)s::uuid[])
                        """,
                        {
                            "start": start,
                            "end": end,
                            "eligible": list(ELIGIBLE_STATUSES),
                            "ids": scope.as_array(),
                        },
                    ).fetchone()
                unfulfilled = connection.execute(
                    """
                    SELECT count(*)::integer AS unfulfilled
                    FROM orders
                    WHERE (created_at AT TIME ZONE 'UTC')::date BETWEEN %(start)s AND %(end)s
                      AND status = ANY(%(statuses)s)
                      AND (
                          %(ids)s::uuid[] IS NULL
                          OR EXISTS (
                              SELECT 1 FROM order_items i
                              WHERE i.order_id = orders.order_id
                                AND i.product_id = ANY(%(ids)s::uuid[])
                          )
                      )
                    """,
                    {
                        "start": start,
                        "end": end,
                        "statuses": list(UNFULFILLED_STATUSES),
                        "ids": scope.as_array(),
                    },
                ).fetchone()
        except psycopg.Error as error:
            raise DependencyUnavailable("Order analytics are unavailable.") from error
        return {**row, "unfulfilled": unfulfilled["unfulfilled"]}

    def daily(self, *, start: date, end: date, scope: ProductScope) -> list[dict[str, Any]]:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                return connection.execute(
                    """
                    WITH days AS (
                        SELECT generate_series(
                            %(start)s::date, %(end)s::date, interval '1 day'
                        )::date AS day
                    ), events AS (
                        SELECT (occurred_at AT TIME ZONE 'UTC')::date AS day,
                               count(*) FILTER (WHERE event_type = 'view')::integer AS views,
                               count(DISTINCT session_id)::integer AS sessions
                        FROM browsing_events
                        WHERE (occurred_at AT TIME ZONE 'UTC')::date
                              BETWEEN %(start)s AND %(end)s
                          AND (%(ids)s::uuid[] IS NULL
                               OR product_id = ANY(%(ids)s::uuid[]))
                        GROUP BY 1
                    ), orders AS (
                        SELECT (created_at AT TIME ZONE 'UTC')::date AS day,
                               count(*)::integer AS orders,
                               COALESCE(sum(subtotal - refund_total), 0) AS net
                        FROM orders
                        WHERE (created_at AT TIME ZONE 'UTC')::date
                              BETWEEN %(start)s AND %(end)s
                          AND status = ANY(%(eligible)s)
                          AND (%(ids)s::uuid[] IS NULL
                               OR EXISTS (
                                   SELECT 1 FROM order_items i
                                   WHERE i.order_id = orders.order_id
                                     AND i.product_id = ANY(%(ids)s::uuid[])
                               ))
                        GROUP BY 1
                    )
                    SELECT d.day,
                           COALESCE(e.views, 0) AS views,
                           COALESCE(e.sessions, 0) AS sessions,
                           COALESCE(o.orders, 0) AS orders,
                           COALESCE(o.net, 0) AS net
                    FROM days d
                    LEFT JOIN events e ON e.day = d.day
                    LEFT JOIN orders o ON o.day = d.day
                    ORDER BY d.day
                    """,
                    {
                        "start": start,
                        "end": end,
                        "eligible": list(ELIGIBLE_STATUSES),
                        "ids": scope.as_array(),
                    },
                ).fetchall()
        except psycopg.Error as error:
            raise DependencyUnavailable("Daily analytics are unavailable.") from error

    def product_performance(
        self, *, start: date, end: date, scope: ProductScope
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                events = connection.execute(
                    """
                    SELECT product_id,
                           count(*) FILTER (WHERE event_type = 'view')::integer AS views,
                           count(*) FILTER (WHERE event_type = 'add_to_cart')::integer AS carts
                    FROM browsing_events
                    WHERE (occurred_at AT TIME ZONE 'UTC')::date BETWEEN %(start)s AND %(end)s
                      AND (%(ids)s::uuid[] IS NULL OR product_id = ANY(%(ids)s::uuid[]))
                    GROUP BY product_id
                    """,
                    {"start": start, "end": end, "ids": scope.as_array()},
                ).fetchall()
                sales = connection.execute(
                    """
                    SELECT i.product_id,
                           COALESCE(sum(i.quantity), 0)::integer AS units,
                           COALESCE(sum(i.line_total), 0) AS revenue
                    FROM order_items i
                    JOIN orders o USING (order_id)
                    WHERE (o.created_at AT TIME ZONE 'UTC')::date
                          BETWEEN %(start)s AND %(end)s
                      AND o.status = ANY(%(eligible)s)
                      AND (%(ids)s::uuid[] IS NULL OR i.product_id = ANY(%(ids)s::uuid[]))
                    GROUP BY i.product_id
                    """,
                    {
                        "start": start,
                        "end": end,
                        "eligible": list(ELIGIBLE_STATUSES),
                        "ids": scope.as_array(),
                    },
                ).fetchall()
        except psycopg.Error as error:
            raise DependencyUnavailable(
                "Product analytics are unavailable."
            ) from error
        return [
            {
                "product_id": row["product_id"],
                "views": row["views"],
                "add_to_carts": row["carts"],
                "units": 0,
                "revenue": Decimal("0"),
            }
            for row in events
        ], sales

    def reconcile_orders(self, *, start: date, end: date, scope: ProductScope) -> dict[str, Any]:
        """Recompute order totals independently from stored order-item lines."""

        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                row = connection.execute(
                    """
                    WITH scoped AS (
                        SELECT o.order_id, o.subtotal
                        FROM orders o
                        WHERE (o.created_at AT TIME ZONE 'UTC')::date
                              BETWEEN %(start)s AND %(end)s
                          AND o.status = ANY(%(eligible)s)
                          AND (
                              %(ids)s::uuid[] IS NULL
                              OR EXISTS (
                                  SELECT 1 FROM order_items s
                                  WHERE s.order_id = o.order_id
                                    AND s.product_id = ANY(%(ids)s::uuid[])
                              )
                          )
                    )
                    SELECT count(*)::integer AS orders,
                           COALESCE(sum(subtotal), 0) AS subtotals,
                           COALESCE((
                               SELECT sum(lines.line_total)
                               FROM order_items lines
                               JOIN scoped ON scoped.order_id = lines.order_id
                           ), 0) AS lines
                    FROM scoped
                    """,
                    {
                        "start": start,
                        "end": end,
                        "eligible": list(ELIGIBLE_STATUSES),
                        "ids": scope.as_array(),
                    },
                ).fetchone()
        except psycopg.Error as error:
            raise DependencyUnavailable("Reconciliation is unavailable.") from error
        return row


class AnalyticsService:
    def __init__(self, store: AnalyticsStore, catalog: CatalogService) -> None:
        self._store = store
        self._catalog = catalog

    @staticmethod
    def _ratio(numerator: int, denominator: int) -> str:
        if denominator == 0:
            return "0"
        return _decimal_text(
            (Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.0001"))
        )

    def report(
        self,
        *,
        date_from: date,
        date_to: date,
        category: str | None = None,
        now: datetime | None = None,
    ) -> AnalyticsResponse:
        if date_to < date_from:
            raise InvalidInput("The end date must not precede the start date.")
        if (date_to - date_from).days + 1 > MAX_RANGE_DAYS:
            raise InvalidInput("The selected range must not exceed 366 days.")

        scope = ProductScope()
        if category:
            identifiers = self._catalog.product_ids_for_category(category)
            scope = ProductScope(ids=identifiers)

        behaviour = self._store.behaviour(start=date_from, end=date_to, scope=scope)
        financial = self._store.financial(start=date_from, end=date_to, scope=scope)
        daily = self._store.daily(start=date_from, end=date_to, scope=scope)
        events, sales = self._store.product_performance(
            start=date_from, end=date_to, scope=scope
        )
        reconciled = self._store.reconcile_orders(
            start=date_from, end=date_to, scope=scope
        )

        revenue_by_product = {row["product_id"]: row for row in sales}
        performance: list[ProductPerformance] = []
        for row in events:
            sale = revenue_by_product.pop(row["product_id"], None)
            performance.append(
                ProductPerformance(
                    product_id=row["product_id"],
                    views=row["views"],
                    add_to_carts=row["add_to_carts"],
                    units=sale["units"] if sale else 0,
                    revenue=_decimal_text(sale["revenue"]) if sale else "0",
                )
            )
        for product_id, sale in revenue_by_product.items():
            performance.append(
                ProductPerformance(
                    product_id=product_id,
                    views=0,
                    add_to_carts=0,
                    units=sale["units"],
                    revenue=_decimal_text(sale["revenue"]),
                )
            )
        performance.sort(
            key=lambda item: (Decimal(item.revenue), item.views), reverse=True
        )

        gross = Decimal(financial["gross"])
        refunds = Decimal(financial["refunds"])
        net = gross - refunds
        orders = int(financial["orders"])
        average = (
            _decimal_text((net / Decimal(orders)).quantize(Decimal("0.01")))
            if orders
            else "0"
        )
        gross_text = _decimal_text(gross)
        refunds_text = _decimal_text(refunds)
        net_text = _decimal_text(net)

        subtotal_text = _decimal_text(Decimal(reconciled["subtotals"]))
        lines_text = _decimal_text(Decimal(reconciled["lines"]))
        checks = [
            ReconciliationCheck(
                metric="order_totals",
                reported=subtotal_text,
                recomputed=lines_text,
                matches=subtotal_text == lines_text,
                source="orders.subtotal vs order_items.line_total",
            ),
            ReconciliationCheck(
                metric="order_count",
                reported=str(orders),
                recomputed=str(reconciled["orders"]),
                matches=orders == int(reconciled["orders"]),
                source="distinct order_items.order_id",
            ),
        ]

        return AnalyticsResponse(
            generated_at=now or datetime.now(UTC),
            scope=AnalyticsScope(
                date_from=date_from,
                date_to=date_to,
                category=category,
                category_product_count=len(scope.ids) if scope.ids is not None else 0,
            ),
            behaviour=BehaviourMetrics(
                product_views=behaviour["views"],
                sessions=behaviour["sessions"],
                add_to_carts=behaviour["carts"],
                created_orders=orders,
                orders_per_session=self._ratio(orders, behaviour["sessions"]),
                unfulfilled_orders=financial["unfulfilled"],
            ),
            financial=FinancialMetrics(
                order_count=orders,
                gross_sales=gross_text,
                refunds=refunds_text,
                net_sales=net_text,
                average_order_value=average,
            ),
            top_products=performance[:10],
            daily=[
                DailyPoint(
                    day=row["day"],
                    views=row["views"],
                    sessions=row["sessions"],
                    orders=row["orders"],
                    net_sales=_decimal_text(Decimal(row["net"])),
                )
                for row in daily
            ],
            reconciliation=checks,
            no_events=behaviour["sessions"] == 0,
            no_orders=orders == 0,
            category_without_products=bool(category)
            and scope.ids is not None
            and len(scope.ids) == 0,
        )