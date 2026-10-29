from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from smart_ecommerce_api.segmentation import (
    MIN_COHORT_SIZE,
    SEGMENTS,
    OrderAggregate,
    SegmentationService,
    SegmentationStore,
)


REFERENCE = date(2026, 10, 27)
START = REFERENCE - timedelta(days=364)
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


def customer(index: int) -> UUID:
    return UUID(f"20000000-0000-4000-8000-{index:012d}")


def aggregate(index: int, *, days_ago: int, frequency: int, monetary: str) -> OrderAggregate:
    return OrderAggregate(
        customer_id=customer(index),
        last_order_date=REFERENCE - timedelta(days=days_ago),
        frequency=frequency,
        monetary=Decimal(monetary),
    )


def snapshot_row(
    index: int,
    *,
    segment: str,
    recency: int,
    frequency: int,
    monetary: str,
    recency_score: int = 3,
    frequency_score: int = 3,
    monetary_score: int = 3,
) -> dict[str, object]:
    return {
        "customer_id": customer(index),
        "email": f"customer-{index}@example.invalid",
        "display_name": f"Synthetic Customer {index}",
        "reference_date": REFERENCE,
        "recency_days": recency,
        "frequency": frequency,
        "monetary": Decimal(monetary),
        "recency_score": recency_score,
        "frequency_score": frequency_score,
        "monetary_score": monetary_score,
        "segment": segment,
        "created_at": NOW,
    }


class FakeStore:
    def __init__(
        self,
        aggregates: list[OrderAggregate] | None = None,
        *,
        customer_total: int = 0,
        eligible_orders: int = 0,
        excluded_orders: int = 0,
        latest: date | None = None,
        snapshot_rows: list[dict[str, object]] | None = None,
    ) -> None:
        self.aggregates = aggregates or []
        self._customer_total = customer_total
        self.eligible_orders = eligible_orders
        self.excluded_orders = excluded_orders
        self.latest = latest
        self.snapshot_rows = snapshot_rows or []
        self.replaced: list[tuple[date, list[dict[str, object]]]] = []

    def eligible_aggregates(self, observation_start, reference_date):
        return list(self.aggregates)

    def order_counts(self, observation_start, reference_date):
        return self.eligible_orders, self.excluded_orders

    def replace_snapshots(self, reference_date, rows):
        self.replaced.append((reference_date, rows))

    def latest_reference_date(self):
        return self.latest

    def snapshots(self, reference_date):
        return list(self.snapshot_rows)

    def customer_total(self):
        return self._customer_total


def service(store: FakeStore) -> SegmentationService:
    return SegmentationService(store)


def test_quintile_scores_are_monotonic_and_bounded() -> None:
    values = {customer(index + 1): Decimal(index + 1) for index in range(10)}
    recency = SegmentationService._quintiles(values, higher_is_better=False)
    frequency = SegmentationService._quintiles(values, higher_is_better=True)
    assert [recency[customer(index + 1)] for index in range(10)] == [
        5, 5, 4, 4, 3, 3, 2, 2, 1, 1,
    ]
    assert [frequency[customer(index + 1)] for index in range(10)] == [
        1, 1, 2, 2, 3, 3, 4, 4, 5, 5,
    ]
    assert all(1 <= score <= 5 for score in {**recency, **frequency}.values())


def test_ties_share_the_same_score() -> None:
    values = {
        customer(1): Decimal("10"),
        customer(2): Decimal("10"),
        customer(3): Decimal("20"),
        customer(4): Decimal("30"),
        customer(5): Decimal("40"),
    }
    scores = SegmentationService._quintiles(values, higher_is_better=True)
    assert scores[customer(1)] == scores[customer(2)]
    assert scores[customer(1)] < scores[customer(5)]


def test_small_cohort_scores_neutrally() -> None:
    values = {
        customer(index + 1): Decimal(index) for index in range(MIN_COHORT_SIZE - 1)
    }
    scores = SegmentationService._quintiles(values, higher_is_better=True)
    assert set(scores.values()) == {3}


@pytest.mark.parametrize(
    ("recency", "frequency", "monetary", "expected"),
    [
        (5, 5, 5, "champions"),
        (4, 4, 4, "champions"),
        (4, 4, 3, "loyal"),
        (3, 3, 1, "loyal"),
        (5, 2, 5, "potential"),
        (4, 1, 5, "potential"),
        (3, 2, 5, "new"),
        (3, 1, 1, "new"),
        (2, 5, 5, "at_risk"),
        (1, 3, 1, "at_risk"),
        (2, 2, 5, "hibernating"),
        (1, 1, 1, "hibernating"),
    ],
)
def test_segment_for_matrix(recency, frequency, monetary, expected) -> None:
    assert SegmentationService.segment_for(recency, frequency, monetary) == expected


def test_every_score_combination_maps_to_exactly_one_segment() -> None:
    for recency in range(1, 6):
        for frequency in range(1, 6):
            for monetary in range(1, 6):
                segment = SegmentationService.segment_for(
                    recency, frequency, monetary
                )
                assert segment in SEGMENTS


def test_run_persists_snapshots_and_reports_counts() -> None:
    aggregates = [
        aggregate(1, days_ago=1, frequency=12, monetary="9000"),
        aggregate(2, days_ago=5, frequency=8, monetary="6000"),
        aggregate(3, days_ago=20, frequency=4, monetary="3000"),
        aggregate(4, days_ago=60, frequency=2, monetary="1500"),
        aggregate(5, days_ago=120, frequency=1, monetary="500"),
        aggregate(6, days_ago=200, frequency=6, monetary="2500"),
        aggregate(7, days_ago=250, frequency=3, monetary="1200"),
        aggregate(8, days_ago=300, frequency=1, monetary="400"),
    ]
    store = FakeStore(
        aggregates,
        customer_total=10,
        eligible_orders=40,
        excluded_orders=7,
    )
    result = service(store).run(reference_date=REFERENCE)
    assert result.classified == 8
    assert result.insufficient_history == 2
    assert result.eligible_orders == 40
    assert result.excluded_orders == 7
    assert result.observation_start == START
    assert sum(count.customers for count in result.counts) == 8
    reference, rows = store.replaced[0]
    assert reference == REFERENCE
    assert len(rows) == 8
    row = next(item for item in rows if item["customer_id"] == customer(1))
    assert row["recency_days"] == 1
    assert row["frequency"] == 12
    assert row["monetary"] == Decimal("9000")
    assert row["recency_score"] == 5
    assert row["frequency_score"] == 5
    assert row["monetary_score"] == 5
    assert row["segment"] == "champions"


def test_run_with_no_eligible_orders_still_replaces_snapshots() -> None:
    store = FakeStore([], customer_total=3)
    result = service(store).run(reference_date=REFERENCE)
    assert result.classified == 0
    assert result.insufficient_history == 3
    assert store.replaced == [(REFERENCE, [])]


def test_overview_filters_and_pages_members() -> None:
    rows = [
        snapshot_row(1, segment="champions", recency=1, frequency=9, monetary="9000"),
        snapshot_row(2, segment="champions", recency=2, frequency=8, monetary="8000"),
        snapshot_row(3, segment="loyal", recency=4, frequency=6, monetary="6000"),
    ]
    store = FakeStore(
        customer_total=5,
        latest=REFERENCE,
        snapshot_rows=rows,
    )
    overview = service(store).overview(segment="champions", limit=1, offset=1)
    assert overview.snapshot_available is True
    assert overview.reference_date == REFERENCE
    assert overview.cohort_size == 3
    assert overview.insufficient_history == 2
    assert overview.total_members == 2
    assert len(overview.members) == 1
    assert overview.members[0].customer_id == customer(2)
    assert overview.generated_at == NOW
    assert [count.customers for count in overview.counts] == [2, 1, 0, 0, 0, 0]


def test_overview_marks_old_snapshots_stale() -> None:
    store = FakeStore(
        customer_total=1,
        latest=date(2020, 1, 1),
        snapshot_rows=[
            {
                **snapshot_row(
                    1, segment="loyal", recency=1, frequency=3, monetary="1000"
                ),
                "reference_date": date(2020, 1, 1),
            }
        ],
    )
    overview = service(store).overview()
    assert overview.stale is True
    assert overview.reference_date == date(2020, 1, 1)


def test_overview_without_snapshot_is_honest() -> None:
    overview = service(FakeStore(customer_total=40)).overview()
    assert overview.snapshot_available is False
    assert overview.reference_date is None
    assert overview.cohort_size == 0
    assert overview.insufficient_history == 40
    assert overview.members == []
    assert sum(count.customers for count in overview.counts) == 0


def test_export_rows_honour_the_segment_filter() -> None:
    rows = [
        snapshot_row(1, segment="champions", recency=1, frequency=9, monetary="9000"),
        snapshot_row(3, segment="loyal", recency=4, frequency=6, monetary="6000"),
    ]
    store = FakeStore(latest=REFERENCE, snapshot_rows=rows)
    exported = service(store).export_rows(segment="loyal")
    assert len(exported) == 1
    assert exported[0].customer_id == customer(3)
    assert exported[0].email == "customer-3@example.invalid"


def test_unreachable_order_history_is_reported(monkeypatch) -> None:
    import psycopg

    from smart_ecommerce_api.errors import DependencyUnavailable

    def fail(*args, **kwargs):
        raise psycopg.OperationalError("offline")

    monkeypatch.setattr(psycopg, "connect", fail)
    with pytest.raises(DependencyUnavailable, match="Order history"):
        SegmentationStore("unused").eligible_aggregates(START, REFERENCE)