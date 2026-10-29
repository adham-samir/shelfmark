"""BO-03 RFM customer segmentation under DEC-011.

Eligible orders are paid/completed orders whose net value (subtotal minus
refunds) is positive. Fully refunded orders and pre-completion statuses are
excluded. Recency, frequency, and monetary values are scored independently in
quintiles; ties share a score. Segments come from one ordered, first-match-wins
rule set so every score combination maps to exactly one segment.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, ROUND_CEILING
from typing import Literal
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from pydantic import Field

from . import db
from .errors import DependencyUnavailable
from .models import StrictModel

POLICY_VERSION = "dec-011-v1"
WINDOW_DAYS = 365
MIN_COHORT_SIZE = 5
ELIGIBLE_STATUSES = ("confirmed", "shipped", "delivered", "refunded")
EXCLUDED_STATUSES = (
    "pending_payment",
    "pending_risk",
    "review",
    "payment_failed",
    "cancelled",
)
SEGMENTS = (
    "champions",
    "loyal",
    "potential",
    "new",
    "at_risk",
    "hibernating",
)
SegmentName = Literal[
    "champions", "loyal", "potential", "new", "at_risk", "hibernating"
]


class SegmentRule(StrictModel):
    segment: str
    rule: str


class RfmPolicy(StrictModel):
    version: str = POLICY_VERSION
    window_days: int = WINDOW_DAYS
    eligible_statuses: list[str] = list(ELIGIBLE_STATUSES)
    excluded_statuses: list[str] = list(EXCLUDED_STATUSES)
    minimum_cohort_size: int = MIN_COHORT_SIZE
    scoring: str = (
        "Independent quintiles per dimension. Recency is scored so fewer days "
        "score higher; frequency and monetary score higher values higher. Ties "
        "share a score computed from the empirical distribution. A cohort "
        "smaller than the minimum scores neutrally at 3."
    )
    rules: list[SegmentRule] = [
        SegmentRule(segment="champions", rule="R >= 4 and F >= 4 and M >= 4"),
        SegmentRule(segment="loyal", rule="R >= 3 and F >= 3"),
        SegmentRule(segment="potential", rule="R >= 4 and F <= 2"),
        SegmentRule(segment="new", rule="R = 3 and F <= 2"),
        SegmentRule(segment="at_risk", rule="R <= 2 and F >= 3"),
        SegmentRule(segment="hibernating", rule="R <= 2 and F <= 2"),
    ]


class SegmentCount(StrictModel):
    segment: str
    customers: int = Field(ge=0)


class CustomerSegment(StrictModel):
    customer_id: UUID
    email: str
    display_name: str
    reference_date: date
    recency_days: int = Field(ge=0)
    frequency: int = Field(ge=0)
    monetary: Decimal = Field(ge=0)
    recency_score: int = Field(ge=1, le=5)
    frequency_score: int = Field(ge=1, le=5)
    monetary_score: int = Field(ge=1, le=5)
    segment: str


class SegmentationResponse(StrictModel):
    snapshot_available: bool
    reference_date: date | None = None
    observation_start: date | None = None
    generated_at: datetime | None = None
    stale: bool = False
    policy: RfmPolicy
    cohort_size: int = Field(ge=0)
    insufficient_history: int = Field(ge=0)
    counts: list[SegmentCount]
    members: list[CustomerSegment]
    total_members: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class SegmentationRunResult(StrictModel):
    reference_date: date
    observation_start: date
    policy_version: str
    classified: int = Field(ge=0)
    insufficient_history: int = Field(ge=0)
    eligible_orders: int = Field(ge=0)
    excluded_orders: int = Field(ge=0)
    cohort_size: int = Field(ge=0)
    counts: list[SegmentCount]


@dataclass(frozen=True, slots=True)
class OrderAggregate:
    customer_id: UUID
    last_order_date: date
    frequency: int
    monetary: Decimal


class SegmentationStore:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def eligible_aggregates(
        self, observation_start: date, reference_date: date
    ) -> list[OrderAggregate]:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                rows = connection.execute(
                    """
                    SELECT customer_id,
                           max((created_at AT TIME ZONE 'UTC')::date) AS last_order_date,
                           count(*)::integer AS frequency,
                           sum(subtotal - refund_total) AS monetary
                    FROM orders
                    WHERE (created_at AT TIME ZONE 'UTC')::date BETWEEN %s AND %s
                      AND status = ANY(%s)
                      AND subtotal - refund_total > 0
                    GROUP BY customer_id
                    ORDER BY customer_id
                    """,
                    (observation_start, reference_date, list(ELIGIBLE_STATUSES)),
                ).fetchall()
        except psycopg.Error as error:
            raise DependencyUnavailable("Order history is unavailable.") from error
        return [
            OrderAggregate(
                customer_id=row["customer_id"],
                last_order_date=row["last_order_date"],
                frequency=row["frequency"],
                monetary=row["monetary"],
            )
            for row in rows
        ]

    def order_counts(
        self, observation_start: date, reference_date: date
    ) -> tuple[int, int]:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                row = connection.execute(
                    """
                    SELECT count(*) FILTER (
                               WHERE status = ANY(%(eligible)s)
                                 AND subtotal - refund_total > 0
                           )::integer AS eligible,
                           count(*) FILTER (
                               WHERE NOT (
                                   status = ANY(%(eligible)s)
                                   AND subtotal - refund_total > 0
                               )
                           )::integer AS excluded
                    FROM orders
                    WHERE (created_at AT TIME ZONE 'UTC')::date BETWEEN %(start)s
                          AND %(reference)s
                    """,
                    {
                        "eligible": list(ELIGIBLE_STATUSES),
                        "start": observation_start,
                        "reference": reference_date,
                    },
                ).fetchone()
        except psycopg.Error as error:
            raise DependencyUnavailable("Order history is unavailable.") from error
        return row["eligible"], row["excluded"]

    def replace_snapshots(
        self, reference_date: date, rows: list[dict[str, object]]
    ) -> None:
        try:
            with db.connection(self._dsn) as connection:
                connection.execute(
                    "DELETE FROM rfm_snapshots WHERE reference_date = %s",
                    (reference_date,),
                )
                with connection.cursor() as cursor:
                    cursor.executemany(
                        """
                        INSERT INTO rfm_snapshots(
                            snapshot_id, customer_id, reference_date, observation_start,
                            recency_days, frequency, monetary, recency_score,
                            frequency_score, monetary_score, segment
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        [
                            (
                                row["snapshot_id"],
                                row["customer_id"],
                                reference_date,
                                row["observation_start"],
                                row["recency_days"],
                                row["frequency"],
                                row["monetary"],
                                row["recency_score"],
                                row["frequency_score"],
                                row["monetary_score"],
                                row["segment"],
                            )
                            for row in rows
                        ],
                    )
        except psycopg.Error as error:
            raise DependencyUnavailable(
                "RFM snapshots could not be stored."
            ) from error

    def latest_reference_date(self) -> date | None:
        try:
            with db.connection(self._dsn) as connection:
                row = connection.execute(
                    "SELECT max(reference_date) FROM rfm_snapshots"
                ).fetchone()
        except psycopg.Error as error:
            raise DependencyUnavailable("Segmentation history is unavailable.") from error
        return row[0] if row else None

    def snapshots(self, reference_date: date) -> list[dict[str, object]]:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                rows = connection.execute(
                    """
                    SELECT s.customer_id, c.email, c.display_name, s.reference_date,
                           s.recency_days, s.frequency, s.monetary, s.recency_score,
                           s.frequency_score, s.monetary_score, s.segment,
                           s.created_at
                    FROM rfm_snapshots s
                    JOIN customers c USING (customer_id)
                    WHERE s.reference_date = %s
                    ORDER BY s.segment, s.monetary DESC, s.customer_id
                    """,
                    (reference_date,),
                ).fetchall()
        except psycopg.Error as error:
            raise DependencyUnavailable("RFM snapshots are unavailable.") from error
        return rows

    def customer_total(self) -> int:
        try:
            with db.connection(self._dsn) as connection:
                row = connection.execute("SELECT count(*) FROM customers").fetchone()
        except psycopg.Error as error:
            raise DependencyUnavailable("Customer records are unavailable.") from error
        return row[0]


class SegmentationService:
    def __init__(self, store: SegmentationStore) -> None:
        self._store = store

    @staticmethod
    def _quintiles(
        values: dict[UUID, Decimal], *, higher_is_better: bool
    ) -> dict[UUID, int]:
        cohort = len(values)
        if cohort < MIN_COHORT_SIZE:
            return {customer_id: 3 for customer_id in values}
        distinct = set(values.values())
        scores: dict[Decimal, int] = {}
        for value in distinct:
            at_least_as_good = sum(
                1
                for other in values.values()
                if (other <= value if higher_is_better else other >= value)
            )
            raw = (Decimal(at_least_as_good) * 5 / Decimal(cohort)).to_integral_value(
                rounding=ROUND_CEILING
            )
            scores[value] = max(1, min(5, int(raw)))
        return {customer_id: scores[value] for customer_id, value in values.items()}

    @staticmethod
    def segment_for(
        recency_score: int, frequency_score: int, monetary_score: int
    ) -> str:
        if recency_score >= 4 and frequency_score >= 4 and monetary_score >= 4:
            return "champions"
        if recency_score >= 3 and frequency_score >= 3:
            return "loyal"
        if recency_score >= 4 and frequency_score <= 2:
            return "potential"
        if recency_score == 3 and frequency_score <= 2:
            return "new"
        if recency_score <= 2 and frequency_score >= 3:
            return "at_risk"
        return "hibernating"

    def _classify(
        self,
        aggregates: list[OrderAggregate],
        reference_date: date,
        observation_start: date,
    ) -> list[dict[str, object]]:
        if not aggregates:
            return []
        recency = {
            aggregate.customer_id: Decimal(
                (reference_date - aggregate.last_order_date).days
            )
            for aggregate in aggregates
        }
        frequency = {
            aggregate.customer_id: Decimal(aggregate.frequency)
            for aggregate in aggregates
        }
        monetary = {
            aggregate.customer_id: aggregate.monetary for aggregate in aggregates
        }
        recency_scores = self._quintiles(recency, higher_is_better=False)
        frequency_scores = self._quintiles(frequency, higher_is_better=True)
        monetary_scores = self._quintiles(monetary, higher_is_better=True)

        rows: list[dict[str, object]] = []
        for aggregate in aggregates:
            customer_id = aggregate.customer_id
            recency_score = recency_scores[customer_id]
            frequency_score = frequency_scores[customer_id]
            monetary_score = monetary_scores[customer_id]
            rows.append(
                {
                    "snapshot_id": uuid4(),
                    "customer_id": customer_id,
                    "observation_start": observation_start,
                    "recency_days": int(recency[customer_id]),
                    "frequency": aggregate.frequency,
                    "monetary": aggregate.monetary,
                    "recency_score": recency_score,
                    "frequency_score": frequency_score,
                    "monetary_score": monetary_score,
                    "segment": self.segment_for(
                        recency_score, frequency_score, monetary_score
                    ),
                }
            )
        return rows

    def run(self, *, reference_date: date | None = None) -> SegmentationRunResult:
        reference = reference_date or datetime.now(UTC).date()
        observation_start = reference - timedelta(days=WINDOW_DAYS - 1)
        aggregates = self._store.eligible_aggregates(observation_start, reference)
        rows = self._classify(aggregates, reference, observation_start)
        self._store.replace_snapshots(reference, rows)
        eligible_orders, excluded_orders = self._store.order_counts(
            observation_start, reference
        )
        counts = Counter(str(row["segment"]) for row in rows)
        return SegmentationRunResult(
            reference_date=reference,
            observation_start=observation_start,
            policy_version=POLICY_VERSION,
            classified=len(rows),
            insufficient_history=max(0, self._store.customer_total() - len(rows)),
            eligible_orders=eligible_orders,
            excluded_orders=excluded_orders,
            cohort_size=len(rows),
            counts=[
                SegmentCount(segment=segment, customers=counts.get(segment, 0))
                for segment in SEGMENTS
            ],
        )

    def overview(
        self,
        *,
        reference_date: date | None = None,
        segment: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> SegmentationResponse:
        latest = self._store.latest_reference_date()
        reference = reference_date or latest
        if reference is None:
            return SegmentationResponse(
                snapshot_available=False,
                policy=RfmPolicy(),
                cohort_size=0,
                insufficient_history=self._store.customer_total(),
                counts=[
                    SegmentCount(segment=name, customers=0) for name in SEGMENTS
                ],
                members=[],
                total_members=0,
                limit=limit,
                offset=offset,
            )

        rows = self._store.snapshots(reference)
        counts = Counter(str(row["segment"]) for row in rows)
        selected = [
            row
            for row in rows
            if segment is None or str(row["segment"]) == segment
        ]
        total = len(selected)
        members = [
            CustomerSegment(
                customer_id=row["customer_id"],
                email=row["email"],
                display_name=row["display_name"],
                reference_date=row["reference_date"],
                recency_days=row["recency_days"],
                frequency=row["frequency"],
                monetary=row["monetary"],
                recency_score=row["recency_score"],
                frequency_score=row["frequency_score"],
                monetary_score=row["monetary_score"],
                segment=row["segment"],
            )
            for row in selected[offset : offset + limit]
        ]
        generated_at = rows[0]["created_at"] if rows else None
        today = datetime.now(UTC).date()
        return SegmentationResponse(
            snapshot_available=True,
            reference_date=reference,
            observation_start=reference - timedelta(days=WINDOW_DAYS - 1),
            generated_at=generated_at,
            stale=reference < today,
            policy=RfmPolicy(),
            cohort_size=len(rows),
            insufficient_history=max(0, self._store.customer_total() - len(rows)),
            counts=[
                SegmentCount(segment=name, customers=counts.get(name, 0))
                for name in SEGMENTS
            ],
            members=members,
            total_members=total,
            limit=limit,
            offset=offset,
        )

    def export_rows(
        self, *, reference_date: date | None = None, segment: str | None = None
    ) -> list[CustomerSegment]:
        latest = self._store.latest_reference_date()
        reference = reference_date or latest
        if reference is None:
            return []
        rows = self._store.snapshots(reference)
        return [
            CustomerSegment(
                customer_id=row["customer_id"],
                email=row["email"],
                display_name=row["display_name"],
                reference_date=row["reference_date"],
                recency_days=row["recency_days"],
                frequency=row["frequency"],
                monetary=row["monetary"],
                recency_score=row["recency_score"],
                frequency_score=row["frequency_score"],
                monetary_score=row["monetary_score"],
                segment=row["segment"],
            )
            for row in rows
            if segment is None or str(row["segment"]) == segment
        ]