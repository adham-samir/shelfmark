"""BO-02 dynamic pricing from supply, demand, competitors' costs, and seasons.

DEC-009 fixes the operating policy: daily calculation, mandatory inputs must be
fresh, no update when an input is missing or stale, at most a 20% change per
run, and never below the recorded cost plus 5%. The calculation is deterministic
and every applied change keeps its complete input snapshot in
`price_changes.contributing_inputs`.

Competitors' costs keep the literal source wording (DEC-007): the project has no
real competitor-cost feed, so observations are synthetic/manual imports recorded
with explicit provenance.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP, ROUND_UP
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json
from pydantic import AwareDatetime, Field, field_validator

from . import db
from .errors import DependencyUnavailable, InvalidInput
from .models import StrictModel

POLICY_VERSION = "dec-009-v1"
CALCULATION_VERSION = "dec-009-v1"
MAX_CHANGE_RATIO = Decimal("0.20")
MIN_MARGIN_RATIO = Decimal("0.05")
DEMAND_WEIGHT = Decimal("0.15")
COMPETITOR_WEIGHT = Decimal("0.10")
OBSERVATION_FRESHNESS = timedelta(hours=24)
CURRENCY_QUANTUM = Decimal("0.01")
THOUSANDTH = Decimal("0.000001")


class PricingPolicy(StrictModel):
    version: str = POLICY_VERSION
    max_change_ratio: str = str(MAX_CHANGE_RATIO)
    minimum_margin_ratio: str = str(MIN_MARGIN_RATIO)
    demand_weight: str = str(DEMAND_WEIGHT)
    competitor_weight: str = str(COMPETITOR_WEIGHT)
    freshness_hours: int = 24
    rounding: str = str(CURRENCY_QUANTUM)
    rules: list[str] = [
        "Price moves with demand relative to observed supply.",
        "A higher competitor cost pulls the price up; a lower one pulls it down.",
        "The configured season multiplier is applied last.",
        "One price change is applied per observation; reruns do not compound it.",
    ]


class PricingSeason(StrictModel):
    season_id: str
    label_en: str
    label_ar: str
    price_multiplier: str
    starts_on: date | None = None
    ends_on: date | None = None


class PricingObservationSummary(StrictModel):
    observation_id: UUID
    recorded_cost: Decimal = Field(ge=0)
    supply: Decimal = Field(ge=0)
    demand: Decimal = Field(ge=0)
    competitor_cost: Decimal = Field(ge=0)
    observed_season_id: str
    provenance: str
    observed_at: datetime
    fresh: bool


class PriceChangeSummary(StrictModel):
    price_change_id: UUID
    product_id: UUID
    old_amount: Decimal = Field(ge=0)
    new_amount: Decimal = Field(ge=0)
    currency: str
    calculation_version: str
    applied_at: datetime
    contributing_inputs: dict[str, Any]


class PricingOverviewItem(StrictModel):
    product_id: UUID
    currency: str
    current_amount: Decimal = Field(ge=0)
    price_updated_at: datetime
    input_status: Literal["fresh", "stale", "missing"]
    observation: PricingObservationSummary | None = None
    outcome: str
    detail: str | None = None
    proposed_amount: Decimal | None = Field(default=None, ge=0)
    latest_change: PriceChangeSummary | None = None


class PricingOverviewResponse(StrictModel):
    generated_at: datetime
    as_of: date
    season: PricingSeason
    policy: PricingPolicy
    items: list[PricingOverviewItem]
    recent_changes: list[PriceChangeSummary]


class PricingRunInput(StrictModel):
    product_ids: list[UUID] | None = Field(default=None, min_length=1)

    @field_validator("product_ids")
    @classmethod
    def _unique_ids(cls, value: list[UUID] | None) -> list[UUID] | None:
        if value is not None and len(set(value)) != len(value):
            raise ValueError("product_ids must be unique")
        return value


class PricingObservationInput(StrictModel):
    product_id: UUID
    recorded_cost: Decimal = Field(gt=0)
    supply: Decimal = Field(
        ge=0, description="Available units observed for the product."
    )
    demand: Decimal = Field(
        ge=0, description="Units demanded during the observation window."
    )
    competitor_cost: Decimal = Field(
        ge=0, description="Imported competitor cost for the same product."
    )
    observed_at: AwareDatetime | None = None
    provenance: Literal["synthetic", "sandbox", "public"] = "synthetic"


class PricingObservationResult(StrictModel):
    observation_id: UUID
    product_id: UUID
    observed_at: datetime
    season_id: str
    provenance: str


class PricingRunItem(StrictModel):
    product_id: UUID
    outcome: str
    detail: str | None = None
    old_amount: Decimal | None = Field(default=None, ge=0)
    new_amount: Decimal | None = Field(default=None, ge=0)


class PricingRunResult(StrictModel):
    run_date: date
    policy_version: str
    season_id: str
    evaluated: int = Field(ge=0)
    updated: int = Field(ge=0)
    unchanged: int = Field(ge=0)
    missing_input: int = Field(ge=0)
    stale_input: int = Field(ge=0)
    constraint_blocked: int = Field(ge=0)
    already_applied: int = Field(ge=0)
    conflict: int = Field(ge=0)
    items: list[PricingRunItem]


@dataclass(frozen=True, slots=True)
class Season:
    season_id: str
    label_en: str
    label_ar: str
    price_multiplier: Decimal
    starts_on: date | None = None
    ends_on: date | None = None

    def summary(self) -> PricingSeason:
        return PricingSeason(
            season_id=self.season_id,
            label_en=self.label_en,
            label_ar=self.label_ar,
            price_multiplier=str(self.price_multiplier),
            starts_on=self.starts_on,
            ends_on=self.ends_on,
        )


class SeasonCalendar:
    """Dated season configuration; never model knowledge."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._config: dict[str, Any] | None = None

    def _load(self) -> dict[str, Any]:
        if self._config is None:
            try:
                config = json.loads(self._path.read_text())
                standard = config["standard"]
                seasons = [
                    {
                        "season_id": season["season_id"],
                        "label_en": season["label_en"],
                        "label_ar": season["label_ar"],
                        "price_multiplier": Decimal(str(season["price_multiplier"])),
                        "starts_on": date.fromisoformat(season["starts_on"]),
                        "ends_on": date.fromisoformat(season["ends_on"]),
                    }
                    for season in config["seasons"]
                ]
                self._config = {
                    "standard": {
                        "season_id": standard["season_id"],
                        "label_en": standard["label_en"],
                        "label_ar": standard["label_ar"],
                        "price_multiplier": Decimal(str(standard["price_multiplier"])),
                        "starts_on": None,
                        "ends_on": None,
                    },
                    "seasons": sorted(
                        seasons,
                        key=lambda item: (item["starts_on"], item["season_id"]),
                    ),
                }
            except (OSError, KeyError, TypeError, ValueError) as error:
                raise DependencyUnavailable(
                    "The pricing season calendar is unavailable."
                ) from error
        return self._config

    def resolve(self, current: date) -> Season:
        config = self._load()
        for season in config["seasons"]:
            if season["starts_on"] <= current <= season["ends_on"]:
                return Season(**season)
        return Season(**config["standard"])

    def get(self, season_id: str) -> Season:
        config = self._load()
        for season in config["seasons"]:
            if season["season_id"] == season_id:
                return Season(**season)
        if season_id == config["standard"]["season_id"]:
            return Season(**config["standard"])
        raise InvalidInput("The selected season is not defined in the calendar.")


@dataclass(frozen=True, slots=True)
class PricingCandidate:
    product_id: UUID
    amount: Decimal
    currency: str
    updated_at: datetime
    observation_id: UUID | None = None
    recorded_cost: Decimal | None = None
    supply: Decimal | None = None
    demand: Decimal | None = None
    competitor_cost: Decimal | None = None
    observed_season_id: str | None = None
    observed_at: datetime | None = None
    provenance: str | None = None


@dataclass(frozen=True, slots=True)
class Evaluation:
    outcome: str
    new_amount: Decimal | None = None
    detail: str | None = None
    contributing: dict[str, Any] | None = None


class PricingStore:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def candidates(self, product_ids: list[UUID] | None = None) -> list[PricingCandidate]:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                rows = connection.execute(
                    """
                    SELECT r.product_id, p.amount, p.currency, p.updated_at,
                           o.observation_id, o.recorded_cost, o.supply_value AS supply,
                           o.demand_value AS demand, o.competitor_cost,
                           o.season_id AS observed_season_id, o.observed_at,
                           o.provenance_class AS provenance
                    FROM product_registry r
                    JOIN product_prices p USING (product_id)
                    LEFT JOIN LATERAL (
                        SELECT * FROM pricing_observations
                        WHERE product_id = r.product_id
                        ORDER BY observed_at DESC, observation_id DESC
                        LIMIT 1
                    ) o ON true
                    WHERE r.lifecycle = 'active'
                      AND (%s::uuid[] IS NULL OR r.product_id = ANY(%s::uuid[]))
                    ORDER BY r.product_id
                    """,
                    (product_ids, product_ids),
                ).fetchall()
        except psycopg.Error as error:
            raise DependencyUnavailable("Pricing inputs are unavailable.") from error
        return [
            PricingCandidate(
                product_id=row["product_id"],
                amount=row["amount"],
                currency=row["currency"],
                updated_at=row["updated_at"],
                observation_id=row["observation_id"],
                recorded_cost=row["recorded_cost"],
                supply=row["supply"],
                demand=row["demand"],
                competitor_cost=row["competitor_cost"],
                observed_season_id=row["observed_season_id"],
                observed_at=row["observed_at"],
                provenance=row["provenance"],
            )
            for row in rows
        ]

    def applied_observations(self, observation_ids: list[UUID]) -> set[UUID]:
        if not observation_ids:
            return set()
        try:
            with db.connection(self._dsn) as connection:
                rows = connection.execute(
                    """
                    SELECT DISTINCT (contributing_inputs->>'observation_id')::uuid
                    FROM price_changes
                    WHERE contributing_inputs->>'observation_id' = ANY(%s)
                    """,
                    ([str(observation_id) for observation_id in observation_ids],),
                ).fetchall()
        except psycopg.Error as error:
            raise DependencyUnavailable("Applied price changes are unavailable.") from error
        return {row[0] for row in rows}

    def apply_change(
        self,
        *,
        product_id: UUID,
        expected_amount: Decimal,
        new_amount: Decimal,
        currency: str,
        contributing_inputs: dict[str, Any],
    ) -> bool:
        change_id = uuid4()
        try:
            with db.connection(self._dsn) as connection:
                row = connection.execute(
                    """
                    WITH updated AS (
                        UPDATE product_prices
                        SET amount = %(new_amount)s,
                            version = version + 1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE product_id = %(product_id)s
                          AND amount = %(expected_amount)s
                        RETURNING product_id
                    )
                    INSERT INTO price_changes(
                        price_change_id, product_id, old_amount, new_amount,
                        currency, calculation_version, contributing_inputs
                    )
                    SELECT %(change_id)s, product_id, %(expected_amount)s,
                           %(new_amount)s, %(currency)s, %(calculation_version)s,
                           %(contributing_inputs)s
                    FROM updated
                    RETURNING price_change_id
                    """,
                    {
                        "change_id": change_id,
                        "product_id": product_id,
                        "expected_amount": expected_amount,
                        "new_amount": new_amount,
                        "currency": currency,
                        "calculation_version": CALCULATION_VERSION,
                        "contributing_inputs": Json(contributing_inputs),
                    },
                ).fetchone()
        except psycopg.Error as error:
            raise DependencyUnavailable("The price change could not be applied.") from error
        return row is not None

    def record_observation(
        self,
        *,
        product_id: UUID,
        recorded_cost: Decimal,
        supply: Decimal,
        demand: Decimal,
        competitor_cost: Decimal,
        season_id: str,
        provenance: str,
        observed_at: datetime,
    ) -> UUID:
        observation_id = uuid4()
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                lifecycle = connection.execute(
                    "SELECT lifecycle FROM product_registry WHERE product_id = %s",
                    (product_id,),
                ).fetchone()
                if lifecycle is None or lifecycle["lifecycle"] != "active":
                    raise InvalidInput(
                        "Pricing observations require an existing active product."
                    )
                connection.execute(
                    """
                    INSERT INTO pricing_observations(
                        observation_id, product_id, recorded_cost, supply_value,
                        demand_value, competitor_cost, season_id,
                        provenance_class, observed_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        observation_id,
                        product_id,
                        recorded_cost,
                        supply,
                        demand,
                        competitor_cost,
                        season_id,
                        provenance,
                        observed_at,
                    ),
                )
        except psycopg.Error as error:
            raise DependencyUnavailable(
                "The pricing observation could not be stored."
            ) from error
        return observation_id

    def recent_changes(self, limit: int = 20) -> list[PriceChangeSummary]:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                rows = connection.execute(
                    """
                    SELECT price_change_id, product_id, old_amount, new_amount,
                           currency, calculation_version, applied_at,
                           contributing_inputs
                    FROM price_changes
                    ORDER BY applied_at DESC, price_change_id DESC
                    LIMIT %s
                    """,
                    (limit,),
                ).fetchall()
        except psycopg.Error as error:
            raise DependencyUnavailable("Price-change history is unavailable.") from error
        return [PriceChangeSummary(**row) for row in rows]


class PricingService:
    def __init__(self, store: PricingStore, calendar: SeasonCalendar) -> None:
        self._store = store
        self._calendar = calendar

    @staticmethod
    def _clamp(value: Decimal, low: Decimal = Decimal("-1"), high: Decimal = Decimal("1")) -> Decimal:
        return min(max(value, low), high)

    def _evaluate(
        self, candidate: PricingCandidate, season: Season, now: datetime
    ) -> Evaluation:
        if candidate.observation_id is None or any(
            value is None
            for value in (
                candidate.recorded_cost,
                candidate.supply,
                candidate.demand,
                candidate.competitor_cost,
                candidate.observed_at,
            )
        ):
            return Evaluation(
                "missing_input", None, "No pricing observation is recorded."
            )

        observed_at = candidate.observed_at
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=UTC)
        age = now - observed_at
        if age < timedelta(0):
            return Evaluation(
                "stale_input",
                None,
                "The observation timestamp is in the future.",
            )
        if age > OBSERVATION_FRESHNESS:
            return Evaluation(
                "stale_input",
                None,
                "The observation is older than the 24-hour freshness limit.",
            )

        current = candidate.amount
        recorded_cost = candidate.recorded_cost
        supply = candidate.supply
        demand = candidate.demand
        competitor_cost = candidate.competitor_cost

        scale = max(demand, supply)
        demand_balance = Decimal("0") if scale == 0 else (demand - supply) / scale
        demand_balance = self._clamp(demand_balance)
        competitor_balance = self._clamp(
            (competitor_cost - recorded_cost) / max(recorded_cost, Decimal("1"))
        )

        demand_factor = Decimal("1") + DEMAND_WEIGHT * demand_balance
        competitor_factor = Decimal("1") + COMPETITOR_WEIGHT * competitor_balance
        raw_amount = current * demand_factor * competitor_factor * season.price_multiplier

        upper = current * (Decimal("1") + MAX_CHANGE_RATIO)
        lower = current * (Decimal("1") - MAX_CHANGE_RATIO)
        floor = recorded_cost * (Decimal("1") + MIN_MARGIN_RATIO)
        upper_quantized = upper.quantize(CURRENCY_QUANTUM, rounding=ROUND_DOWN)
        lower_quantized = lower.quantize(CURRENCY_QUANTUM, rounding=ROUND_UP)
        floor_quantized = floor.quantize(CURRENCY_QUANTUM, rounding=ROUND_UP)
        bounded = min(max(raw_amount, lower), upper)

        detail: str | None = None
        if floor > upper:
            return Evaluation(
                "constraint_blocked",
                None,
                "The recorded cost floor exceeds the maximum permitted increase.",
                self._contributing(
                    candidate, season, current, demand_balance,
                    competitor_balance, demand_factor, competitor_factor,
                    raw_amount, bounded, floor, applied=False,
                ),
            )
        if bounded < floor:
            bounded = floor
            detail = "The recorded cost floor raised the proposed price."

        new_amount = bounded.quantize(CURRENCY_QUANTUM, rounding=ROUND_HALF_UP)
        if new_amount > upper_quantized:
            new_amount = upper_quantized
        if new_amount < lower_quantized:
            new_amount = lower_quantized
        if new_amount < floor_quantized:
            new_amount = floor_quantized
        if new_amount > upper_quantized or new_amount <= 0:
            return Evaluation(
                "constraint_blocked",
                None,
                "The cost floor and the change cap cannot both be satisfied.",
                self._contributing(
                    candidate, season, current, demand_balance,
                    competitor_balance, demand_factor, competitor_factor,
                    raw_amount, bounded, floor, applied=False,
                ),
            )
        if new_amount == current:
            return Evaluation(
                "unchanged",
                None,
                "The calculated price equals the current price.",
                self._contributing(
                    candidate, season, current, demand_balance, competitor_balance,
                    demand_factor, competitor_factor, raw_amount, bounded, floor,
                    applied=False,
                ),
            )

        return Evaluation(
            "update",
            new_amount,
            detail,
            self._contributing(
                candidate, season, current, demand_balance, competitor_balance,
                demand_factor, competitor_factor, raw_amount, bounded, floor,
                applied=True, new_amount=new_amount,
            ),
        )

    @staticmethod
    def _contributing(
        candidate: PricingCandidate,
        season: Season,
        current: Decimal,
        demand_balance: Decimal,
        competitor_balance: Decimal,
        demand_factor: Decimal,
        competitor_factor: Decimal,
        raw_amount: Decimal,
        bounded: Decimal,
        floor: Decimal,
        *,
        applied: bool,
        new_amount: Decimal | None = None,
    ) -> dict[str, Any]:
        inputs: dict[str, Any] = {
            "policy_version": POLICY_VERSION,
            "observation_id": str(candidate.observation_id),
            "observed_at": candidate.observed_at.isoformat()
            if candidate.observed_at
            else None,
            "provenance": candidate.provenance,
            "recorded_cost": str(candidate.recorded_cost),
            "supply": str(candidate.supply),
            "demand": str(candidate.demand),
            "competitor_cost": str(candidate.competitor_cost),
            "observed_season_id": candidate.observed_season_id,
            "season_id": season.season_id,
            "season_multiplier": str(season.price_multiplier),
            "currency": candidate.currency,
            "reference_amount": str(current),
            "demand_balance": str(demand_balance.quantize(THOUSANDTH)),
            "competitor_balance": str(competitor_balance.quantize(THOUSANDTH)),
            "demand_factor": str(demand_factor.quantize(THOUSANDTH)),
            "competitor_factor": str(competitor_factor.quantize(THOUSANDTH)),
            "raw_amount": str(raw_amount.quantize(THOUSANDTH)),
            "bounded_amount": str(bounded.quantize(THOUSANDTH)),
            "floor_amount": str(floor.quantize(THOUSANDTH)),
            "rounding": str(CURRENCY_QUANTUM),
            "applied": applied,
        }
        if new_amount is not None:
            inputs["new_amount"] = str(new_amount)
        return inputs

    def run(
        self,
        *,
        as_of: datetime | None = None,
        product_ids: list[UUID] | None = None,
    ) -> PricingRunResult:
        now = as_of or datetime.now(UTC)
        season = self._calendar.resolve(now.date())
        candidates = self._store.candidates(product_ids)
        applied = self._store.applied_observations(
            [
                candidate.observation_id
                for candidate in candidates
                if candidate.observation_id is not None
            ]
        )
        counts: Counter[str] = Counter()
        items: list[PricingRunItem] = []
        for candidate in candidates:
            if (
                candidate.observation_id is not None
                and candidate.observation_id in applied
            ):
                evaluation = Evaluation(
                    "already_applied",
                    None,
                    "This observation has already produced a price change.",
                )
            else:
                evaluation = self._evaluate(candidate, season, now)

            outcome = evaluation.outcome
            if outcome == "update":
                stored = self._store.apply_change(
                    product_id=candidate.product_id,
                    expected_amount=candidate.amount,
                    new_amount=evaluation.new_amount,
                    currency=candidate.currency,
                    contributing_inputs=evaluation.contributing or {},
                )
                outcome = "updated" if stored else "conflict"
            counts[outcome] += 1
            items.append(
                PricingRunItem(
                    product_id=candidate.product_id,
                    outcome=outcome,
                    detail=evaluation.detail
                    or (
                        "Another writer changed the price first; the run left it untouched."
                        if outcome == "conflict"
                        else None
                    ),
                    old_amount=candidate.amount,
                    new_amount=evaluation.new_amount if outcome == "updated" else None,
                )
            )

        return PricingRunResult(
            run_date=now.date(),
            policy_version=POLICY_VERSION,
            season_id=season.season_id,
            evaluated=len(items),
            updated=counts["updated"],
            unchanged=counts["unchanged"],
            missing_input=counts["missing_input"],
            stale_input=counts["stale_input"],
            constraint_blocked=counts["constraint_blocked"],
            already_applied=counts["already_applied"],
            conflict=counts["conflict"],
            items=items,
        )

    def overview(self, *, now: datetime | None = None) -> PricingOverviewResponse:
        generated_at = now or datetime.now(UTC)
        season = self._calendar.resolve(generated_at.date())
        candidates = self._store.candidates()
        applied = self._store.applied_observations(
            [
                candidate.observation_id
                for candidate in candidates
                if candidate.observation_id is not None
            ]
        )
        recent = self._store.recent_changes()
        latest_by_product: dict[UUID, PriceChangeSummary] = {}
        for change in reversed(recent):
            latest_by_product[change.product_id] = change

        items: list[PricingOverviewItem] = []
        for candidate in candidates:
            observation = None
            input_status = "missing"
            if candidate.observation_id is not None:
                observed_at = candidate.observed_at or generated_at
                if observed_at.tzinfo is None:
                    observed_at = observed_at.replace(tzinfo=UTC)
                age = generated_at - observed_at
                fresh = timedelta(0) <= age <= OBSERVATION_FRESHNESS
                input_status = "fresh" if fresh else "stale"
                observation = PricingObservationSummary(
                    observation_id=candidate.observation_id,
                    recorded_cost=candidate.recorded_cost or Decimal("0"),
                    supply=candidate.supply or Decimal("0"),
                    demand=candidate.demand or Decimal("0"),
                    competitor_cost=candidate.competitor_cost or Decimal("0"),
                    observed_season_id=candidate.observed_season_id or "standard",
                    provenance=candidate.provenance or "synthetic",
                    observed_at=observed_at,
                    fresh=fresh,
                )

            if (
                candidate.observation_id is not None
                and candidate.observation_id in applied
            ):
                evaluation = Evaluation(
                    "already_applied",
                    None,
                    "This observation has already produced a price change.",
                )
            else:
                evaluation = self._evaluate(candidate, season, generated_at)

            outcome = "would_update" if evaluation.outcome == "update" else evaluation.outcome
            items.append(
                PricingOverviewItem(
                    product_id=candidate.product_id,
                    currency=candidate.currency,
                    current_amount=candidate.amount,
                    price_updated_at=candidate.updated_at,
                    input_status=input_status,
                    observation=observation,
                    outcome=outcome,
                    detail=evaluation.detail,
                    proposed_amount=evaluation.new_amount,
                    latest_change=latest_by_product.get(candidate.product_id),
                )
            )

        return PricingOverviewResponse(
            generated_at=generated_at,
            as_of=generated_at.date(),
            season=season.summary(),
            policy=PricingPolicy(),
            items=items,
            recent_changes=recent,
        )

    def record_observation(
        self, observation: PricingObservationInput
    ) -> PricingObservationResult:
        observed_at = observation.observed_at or datetime.now(UTC)
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=UTC)
        observed_at = observed_at.astimezone(UTC)
        if observed_at > datetime.now(UTC) + timedelta(minutes=5):
            raise InvalidInput(
                "The observation timestamp cannot be in the future."
            )
        season = self._calendar.resolve(observed_at.date())
        observation_id = self._store.record_observation(
            product_id=observation.product_id,
            recorded_cost=observation.recorded_cost,
            supply=observation.supply,
            demand=observation.demand,
            competitor_cost=observation.competitor_cost,
            season_id=season.season_id,
            provenance=observation.provenance,
            observed_at=observed_at,
        )
        return PricingObservationResult(
            observation_id=observation_id,
            product_id=observation.product_id,
            observed_at=observed_at,
            season_id=season.season_id,
            provenance=observation.provenance,
        )