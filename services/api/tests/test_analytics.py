from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from smart_ecommerce_api.analytics import (
    MAX_RANGE_DAYS,
    AnalyticsService,
    AnalyticsStore,
    ProductScope,
)
from smart_ecommerce_api.errors import DependencyUnavailable, InvalidInput

PRODUCT = UUID("10000000-0000-4000-8000-000000000001")
OTHER = UUID("10000000-0000-4000-8000-000000000002")
START = date(2026, 7, 1)
END = date(2026, 9, 28)
NOW = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)


class FakeStore:
    def __init__(
        self,
        *,
        behaviour=None,
        financial=None,
        daily=None,
        events=None,
        sales=None,
        reconciled=None,
    ) -> None:
        self._behaviour = behaviour or {"views": 0, "sessions": 0, "carts": 0}
        self._financial = financial or {
            "orders": 0,
            "gross": Decimal("0"),
            "refunds": Decimal("0"),
            "net": Decimal("0"),
            "unfulfilled": 0,
        }
        self._daily = daily or []
        self._events = events or []
        self._sales = sales or []
        self._reconciled = reconciled or {
            "orders": 0,
            "subtotals": Decimal("0"),
            "lines": Decimal("0"),
        }
        self.scopes: list[ProductScope] = []

    def behaviour(self, *, start, end, scope):
        self.scopes.append(scope)
        return self._behaviour

    def financial(self, *, start, end, scope):
        return self._financial

    def daily(self, *, start, end, scope):
        return self._daily

    def product_performance(self, *, start, end, scope):
        return self._events, self._sales

    def reconcile_orders(self, *, start, end, scope):
        return self._reconciled


class FakeCatalog:
    def __init__(self, mapping: dict[str, list[UUID]] | None = None) -> None:
        self.mapping = mapping or {}
        self.asked: list[str] = []

    def product_ids_for_category(self, category: str) -> list[UUID]:
        self.asked.append(category)
        return self.mapping.get(category, [])


def service(store: FakeStore, catalog: FakeCatalog | None = None) -> AnalyticsService:
    return AnalyticsService(store, catalog or FakeCatalog())


def test_consumer_and_financial_metrics_are_computed_from_sources() -> None:
    store = FakeStore(
        behaviour={"views": 600, "sessions": 150, "carts": 45},
        financial={
            "orders": 30,
            "gross": Decimal("300000"),
            "refunds": Decimal("30000"),
            "net": Decimal("270000"),
            "unfulfilled": 4,
        },
        events=[
            {"product_id": PRODUCT, "views": 120, "add_to_carts": 12},
            {"product_id": OTHER, "views": 40, "add_to_carts": 3},
        ],
        sales=[
            {"product_id": PRODUCT, "units": 6, "revenue": Decimal("53400")},
        ],
        reconciled={
            "orders": 30,
            "subtotals": Decimal("300000"),
            "lines": Decimal("300000"),
        },
    )
    report = service(store).report(date_from=START, date_to=END, now=NOW)

    assert report.behaviour.product_views == 600
    assert report.behaviour.sessions == 150
    assert report.behaviour.add_to_carts == 45
    assert report.behaviour.created_orders == 30
    assert report.behaviour.orders_per_session == "0.2"
    assert report.behaviour.unfulfilled_orders == 4
    assert report.financial.gross_sales == "300000"
    assert report.financial.refunds == "30000"
    assert report.financial.net_sales == "270000"
    assert report.financial.average_order_value == "9000"
    assert report.financial.currency == "EGP"
    assert [item.product_id for item in report.top_products] == [PRODUCT, OTHER]
    assert report.top_products[0].revenue == "53400"
    assert report.top_products[1].units == 0
    assert report.no_events is False
    assert report.no_orders is False


def test_orders_per_session_is_zero_without_sessions() -> None:
    report = service(FakeStore()).report(date_from=START, date_to=END, now=NOW)
    assert report.behaviour.orders_per_session == "0"
    assert report.financial.average_order_value == "0"
    assert report.no_events is True
    assert report.no_orders is True


def test_category_filter_scopes_products_and_fails_honestly_when_empty() -> None:
    catalog = FakeCatalog({"phones": [PRODUCT]})
    store = FakeStore(
        behaviour={"views": 10, "sessions": 5, "carts": 1},
        financial={
            "orders": 2,
            "gross": Decimal("1000"),
            "refunds": Decimal("0"),
            "net": Decimal("1000"),
            "unfulfilled": 0,
        },
        reconciled={
            "orders": 2,
            "subtotals": Decimal("1000"),
            "lines": Decimal("1000"),
        },
    )
    report = service(store, catalog).report(
        date_from=START, date_to=END, category="phones", now=NOW
    )
    assert catalog.asked == ["phones"]
    assert store.scopes[0].ids == [PRODUCT]
    assert report.scope.category == "phones"
    assert report.scope.category_product_count == 1
    assert report.category_without_products is False

    empty = service(FakeStore(), FakeCatalog({"unknown": []})).report(
        date_from=START, date_to=END, category="unknown", now=NOW
    )
    assert empty.category_without_products is True
    assert empty.scope.category_product_count == 0


def test_no_category_uses_an_unrestricted_scope() -> None:
    store = FakeStore()
    service(store).report(date_from=START, date_to=END, now=NOW)
    assert store.scopes[0].ids is None


def test_reconciliation_reports_both_values_and_match_state() -> None:
    financial = {
        "orders": 3,
        "gross": Decimal("3000"),
        "refunds": Decimal("0"),
        "net": Decimal("3000"),
        "unfulfilled": 0,
    }
    matched = service(
        FakeStore(
            financial=financial,
            reconciled={
                "orders": 3,
                "subtotals": Decimal("3000"),
                "lines": Decimal("3000"),
            },
        )
    ).report(date_from=START, date_to=END, now=NOW)
    assert all(check.matches for check in matched.reconciliation)
    assert {check.metric for check in matched.reconciliation} == {
        "order_totals",
        "order_count",
    }
    assert matched.reconciliation[0].source == "orders.subtotal vs order_items.line_total"

    mismatched = service(
        FakeStore(
            financial=financial,
            reconciled={
                "orders": 2,
                "subtotals": Decimal("3000"),
                "lines": Decimal("2999"),
            },
        )
    ).report(date_from=START, date_to=END, now=NOW)
    assert [check.matches for check in mismatched.reconciliation] == [False, False]
    assert mismatched.reconciliation[0].recomputed == "2999"


def test_daily_series_is_returned_in_order() -> None:
    daily = [
        {"day": START, "views": 5, "sessions": 2, "orders": 1, "net": Decimal("900")},
        {
            "day": START + timedelta(days=1),
            "views": 7,
            "sessions": 3,
            "orders": 0,
            "net": Decimal("0"),
        },
    ]
    report = service(FakeStore(daily=daily)).report(
        date_from=START, date_to=END, now=NOW
    )
    assert [point.day for point in report.daily] == [START, START + timedelta(days=1)]
    assert report.daily[0].net_sales == "900"


def test_invalid_ranges_are_rejected() -> None:
    analytics = service(FakeStore())
    with pytest.raises(InvalidInput, match="end date"):
        analytics.report(date_from=END, date_to=START)
    with pytest.raises(InvalidInput, match="366 days"):
        analytics.report(
            date_from=END - timedelta(days=MAX_RANGE_DAYS),
            date_to=END,
        )
    allowed = analytics.report(
        date_from=END - timedelta(days=MAX_RANGE_DAYS - 1), date_to=END, now=NOW
    )
    assert allowed.scope.date_to == END


def test_definitions_never_claim_profit() -> None:
    report = service(FakeStore()).report(date_from=START, date_to=END, now=NOW)
    text = " ".join(report.definitions)
    assert "Profit is not displayed" in text
    assert "cost coverage" in text


def test_unreachable_database_is_reported(monkeypatch) -> None:
    import psycopg

    def fail(*args, **kwargs):
        raise psycopg.OperationalError("offline")

    monkeypatch.setattr(psycopg, "connect", fail)
    with pytest.raises(DependencyUnavailable, match="Browsing-event"):
        AnalyticsStore("unused").behaviour(
            start=START, end=END, scope=ProductScope()
        )
    with pytest.raises(DependencyUnavailable, match="Order analytics"):
        AnalyticsStore("unused").financial(
            start=START, end=END, scope=ProductScope()
        )
    with pytest.raises(DependencyUnavailable, match="Reconciliation"):
        AnalyticsStore("unused").reconcile_orders(
            start=START, end=END, scope=ProductScope()
        )