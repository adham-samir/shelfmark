from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP, ROUND_UP
from pathlib import Path
from uuid import UUID

import pytest

from smart_ecommerce_api.errors import DependencyUnavailable, InvalidInput
from smart_ecommerce_api.pricing import (
    COMPETITOR_WEIGHT,
    DEMAND_WEIGHT,
    MAX_CHANGE_RATIO,
    MIN_MARGIN_RATIO,
    PricingCandidate,
    PricingObservationInput,
    PricingService,
    PriceChangeSummary,
    SeasonCalendar,
)


ROOT = Path(__file__).parents[1]
SEASONS = ROOT / "data/pricing_seasons.json"
PRODUCT = UUID("10000000-0000-4000-8000-000000000001")
OTHER_PRODUCT = UUID("10000000-0000-4000-8000-000000000002")
OBSERVATION = UUID("50000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


def candidate(
    *,
    amount: str = "8900",
    cost: str = "6230",
    supply: str = "10",
    demand: str = "56",
    competitor: str = "6500",
    observed_at: datetime | None = NOW - timedelta(minutes=15),
    observation_id: UUID | None = OBSERVATION,
    product_id: UUID = PRODUCT,
) -> PricingCandidate:
    return PricingCandidate(
        product_id=product_id,
        amount=Decimal(amount),
        currency="EGP",
        updated_at=NOW,
        observation_id=observation_id,
        recorded_cost=Decimal(cost) if observation_id else None,
        supply=Decimal(supply) if observation_id else None,
        demand=Decimal(demand) if observation_id else None,
        competitor_cost=Decimal(competitor) if observation_id else None,
        observed_season_id="standard" if observation_id else None,
        observed_at=observed_at if observation_id else None,
        provenance="synthetic" if observation_id else None,
    )


def expected_amount(
    *,
    amount: str,
    cost: str,
    supply: str,
    demand: str,
    competitor: str,
    multiplier: Decimal = Decimal("1"),
) -> Decimal:
    """The documented DEC-009 calculation, independent of the service internals."""

    current = Decimal(amount)
    recorded_cost = Decimal(cost)
    supply_value = Decimal(supply)
    demand_value = Decimal(demand)
    scale = max(demand_value, supply_value)
    demand_balance = (
        Decimal("0") if scale == 0 else (demand_value - supply_value) / scale
    )
    demand_balance = min(max(demand_balance, Decimal("-1")), Decimal("1"))
    competitor_balance = min(
        max((Decimal(competitor) - recorded_cost) / max(recorded_cost, Decimal("1")), Decimal("-1")),
        Decimal("1"),
    )
    raw = (
        current
        * (Decimal("1") + DEMAND_WEIGHT * demand_balance)
        * (Decimal("1") + COMPETITOR_WEIGHT * competitor_balance)
        * multiplier
    )
    upper = current * (Decimal("1") + MAX_CHANGE_RATIO)
    lower = current * (Decimal("1") - MAX_CHANGE_RATIO)
    floor = recorded_cost * (Decimal("1") + MIN_MARGIN_RATIO)
    bounded = max(min(max(raw, lower), upper), floor)
    amount = bounded.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    amount = min(amount, upper.quantize(Decimal("0.01"), rounding=ROUND_DOWN))
    amount = max(amount, lower.quantize(Decimal("0.01"), rounding=ROUND_UP))
    amount = max(amount, floor.quantize(Decimal("0.01"), rounding=ROUND_UP))
    return amount


class FakeStore:
    def __init__(self, candidates, applied=None, history=None) -> None:
        self._candidates = list(candidates)
        self.applied = set(applied or [])
        self.history = list(history or [])
        self.changes = []
        self.observations = []
        self.conflict = False

    def candidates(self, product_ids=None):
        if product_ids is None:
            return list(self._candidates)
        return [value for value in self._candidates if value.product_id in product_ids]

    def applied_observations(self, observation_ids):
        return {value for value in observation_ids if value in self.applied}

    def apply_change(
        self, *, product_id, expected_amount, new_amount, currency, contributing_inputs
    ):
        if self.conflict:
            return False
        self.changes.append(
            {
                "product_id": product_id,
                "expected_amount": expected_amount,
                "new_amount": new_amount,
                "currency": currency,
                "contributing_inputs": contributing_inputs,
            }
        )
        self.applied.add(UUID(contributing_inputs["observation_id"]))
        return True

    def record_observation(self, **values):
        self.observations.append(values)
        return UUID("60000000-0000-4000-8000-000000000001")

    def recent_changes(self, limit=20):
        return self.history[:limit]


def service(store: FakeStore, path: Path = SEASONS) -> PricingService:
    return PricingService(store, SeasonCalendar(path))


def test_season_calendar_resolves_dated_windows() -> None:
    calendar = SeasonCalendar(SEASONS)
    assert calendar.resolve(date(2026, 10, 27)).season_id == "standard"
    year_end = calendar.resolve(date(2026, 12, 1))
    assert year_end.season_id == "year-end-2026"
    assert year_end.price_multiplier == Decimal("0.97")
    assert calendar.resolve(date(2027, 2, 20)).season_id == "ramadan-eid-2027"
    assert calendar.resolve(date(2028, 1, 1)).season_id == "standard"


def test_missing_season_calendar_is_a_dependency_failure(tmp_path: Path) -> None:
    with pytest.raises(DependencyUnavailable, match="season calendar"):
        SeasonCalendar(tmp_path / "missing.json").resolve(date(2026, 10, 27))


def test_missing_observation_blocks_pricing() -> None:
    store = FakeStore([candidate(observation_id=None)])
    result = service(store).run(as_of=NOW)
    assert result.missing_input == 1
    assert result.updated == 0
    assert result.items[0].outcome == "missing_input"
    assert not store.changes


def test_stale_or_future_observation_blocks_pricing() -> None:
    fresh = candidate(observed_at=NOW - timedelta(hours=23, minutes=59))
    stale = candidate(observed_at=NOW - timedelta(hours=24, minutes=1))
    future = candidate(observed_at=NOW + timedelta(minutes=10))
    store = FakeStore([fresh, stale, future])
    result = service(store).run(as_of=NOW)
    assert result.updated == 1
    assert result.stale_input == 2
    assert [item.outcome for item in result.items] == [
        "updated",
        "stale_input",
        "stale_input",
    ]
    assert "24-hour" in result.items[1].detail
    assert "future" in result.items[2].detail


def test_demand_above_supply_raises_price_and_records_audit() -> None:
    store = FakeStore([candidate()])
    result = service(store).run(as_of=NOW)
    assert result.updated == 1
    assert result.items[0].old_amount == Decimal("8900")
    assert result.items[0].new_amount == expected_amount(
        amount="8900", cost="6230", supply="10", demand="56", competitor="6500"
    )
    inputs = store.changes[0]["contributing_inputs"]
    assert inputs["observation_id"] == str(OBSERVATION)
    assert inputs["recorded_cost"] == "6230"
    assert inputs["supply"] == "10"
    assert inputs["demand"] == "56"
    assert inputs["competitor_cost"] == "6500"
    assert inputs["season_id"] == "standard"
    assert inputs["currency"] == "EGP"
    assert inputs["applied"] is True
    assert inputs["demand_balance"] == "0.821429"
    assert inputs["competitor_balance"] == "0.043339"
    assert inputs["new_amount"] == str(result.items[0].new_amount)


def test_oversupply_lowers_price() -> None:
    inputs = dict(amount="1900", cost="1330", supply="197", demand="7", competitor="1300")
    result = service(FakeStore([candidate(**inputs)])).run(as_of=NOW)
    assert result.updated == 1
    assert result.items[0].new_amount == expected_amount(**inputs)
    assert result.items[0].new_amount < Decimal("1900")


def test_higher_demand_always_raises_the_price() -> None:
    low = service(FakeStore([candidate(demand="10")])).run(as_of=NOW)
    high = service(FakeStore([candidate(demand="80")])).run(as_of=NOW)
    assert high.items[0].new_amount > low.items[0].new_amount


def test_competitor_cost_moves_the_price_in_both_directions() -> None:
    base = service(FakeStore([candidate(competitor="6230")])).run(as_of=NOW)
    higher = service(FakeStore([candidate(competitor="7500")])).run(as_of=NOW)
    lower = service(FakeStore([candidate(competitor="5000")])).run(as_of=NOW)
    assert higher.items[0].new_amount > base.items[0].new_amount
    assert lower.items[0].new_amount < base.items[0].new_amount


def test_season_multiplier_changes_the_proposal(tmp_path: Path) -> None:
    standard_only = json.loads(SEASONS.read_text())
    standard_only["seasons"] = []
    path = tmp_path / "seasons.json"
    path.write_text(json.dumps(standard_only))

    observation = candidate(observed_at=datetime(2026, 12, 1, 8, 0, tzinfo=UTC))
    as_of = datetime(2026, 12, 1, 12, 0, tzinfo=UTC)
    seasonal = service(FakeStore([observation])).run(as_of=as_of)
    plain = service(FakeStore([observation]), path).run(as_of=as_of)
    assert seasonal.season_id == "year-end-2026"
    assert plain.season_id == "standard"
    assert seasonal.items[0].new_amount < plain.items[0].new_amount
    assert seasonal.items[0].new_amount == expected_amount(
        amount="8900",
        cost="6230",
        supply="10",
        demand="56",
        competitor="6500",
        multiplier=Decimal("0.97"),
    )


def test_change_is_capped_at_twenty_percent() -> None:
    store = FakeStore(
        [candidate(supply="0", demand="100", competitor="20000", cost="1000")]
    )
    result = service(store).run(as_of=NOW)
    assert result.items[0].new_amount == Decimal("10680.00")
    assert result.items[0].new_amount == Decimal("8900") * (Decimal("1") + MAX_CHANGE_RATIO)


def test_downward_change_is_capped_at_twenty_percent() -> None:
    store = FakeStore(
        [candidate(supply="1000", demand="1", competitor="0", cost="100")]
    )
    result = service(store).run(as_of=NOW)
    assert result.items[0].new_amount == Decimal("7120.00")
    assert result.items[0].new_amount == Decimal("8900") * (Decimal("1") - MAX_CHANGE_RATIO)


def test_cost_floor_raises_a_below_cost_price() -> None:
    inputs = dict(
        amount="10000", cost="9900", supply="30", demand="5", competitor="9900"
    )
    result = service(FakeStore([candidate(**inputs)])).run(as_of=NOW)
    assert result.items[0].new_amount == Decimal("10395.00")
    assert "floor" in (result.items[0].detail or "")


def test_floor_above_the_change_cap_blocks_the_update() -> None:
    store = FakeStore(
        [
            candidate(
                amount="10000", cost="15000", supply="30", demand="5", competitor="15000"
            )
        ]
    )
    result = service(store).run(as_of=NOW)
    assert result.constraint_blocked == 1
    assert result.items[0].outcome == "constraint_blocked"
    assert result.items[0].new_amount is None
    assert not store.changes


def test_unchanged_price_creates_no_audit_row() -> None:
    store = FakeStore(
        [
            candidate(
                amount="10000", cost="5000", supply="100", demand="100", competitor="5000"
            )
        ]
    )
    result = service(store).run(as_of=NOW)
    assert result.unchanged == 1
    assert result.items[0].outcome == "unchanged"
    assert not store.changes


def test_same_observation_is_not_applied_twice() -> None:
    store = FakeStore([candidate()])
    pricing = service(store)
    first = pricing.run(as_of=NOW)
    second = pricing.run(as_of=NOW + timedelta(hours=1))
    assert first.updated == 1
    assert second.already_applied == 1
    assert second.updated == 0
    assert len(store.changes) == 1


def test_concurrent_price_change_is_reported_as_conflict() -> None:
    store = FakeStore([candidate()])
    store.conflict = True
    result = service(store).run(as_of=NOW)
    assert result.conflict == 1
    assert result.items[0].outcome == "conflict"
    assert result.items[0].new_amount is None


def test_run_can_be_limited_to_selected_products() -> None:
    store = FakeStore(
        [
            candidate(),
            candidate(
                product_id=OTHER_PRODUCT,
                observation_id=UUID("50000000-0000-4000-8000-000000000002"),
            ),
        ]
    )
    result = service(store).run(as_of=NOW, product_ids=[OTHER_PRODUCT])
    assert result.evaluated == 1
    assert result.items[0].product_id == OTHER_PRODUCT


def test_overview_reports_proposal_inputs_and_history() -> None:
    latest = PriceChangeSummary(
        price_change_id=UUID("70000000-0000-4000-8000-000000000001"),
        product_id=PRODUCT,
        old_amount=Decimal("8700"),
        new_amount=Decimal("8900"),
        currency="EGP",
        calculation_version="dec-009-v1",
        applied_at=NOW - timedelta(days=1),
        contributing_inputs={"observation_id": "previous"},
    )
    overview = service(FakeStore([candidate()], history=[latest])).overview(now=NOW)
    assert overview.season.season_id == "standard"
    assert overview.policy.max_change_ratio == "0.20"
    item = overview.items[0]
    assert item.input_status == "fresh"
    assert item.outcome == "would_update"
    assert item.proposed_amount == expected_amount(
        amount="8900", cost="6230", supply="10", demand="56", competitor="6500"
    )
    assert item.latest_change is not None
    assert item.latest_change.new_amount == Decimal("8900")
    assert overview.recent_changes[0].old_amount == Decimal("8700")


def test_overview_marks_missing_and_stale_inputs() -> None:
    overview = service(
        FakeStore(
            [
                candidate(observation_id=None),
                candidate(observed_at=NOW - timedelta(hours=30)),
            ]
        )
    ).overview(now=NOW)
    assert [item.input_status for item in overview.items] == ["missing", "stale"]
    assert [item.outcome for item in overview.items] == [
        "missing_input",
        "stale_input",
    ]


def test_observation_import_records_season_and_rejects_future_inputs() -> None:
    store = FakeStore([])
    pricing = service(store)
    result = pricing.record_observation(
        PricingObservationInput(
            product_id=PRODUCT,
            recorded_cost=Decimal("6230"),
            supply=Decimal("10"),
            demand=Decimal("56"),
            competitor_cost=Decimal("6500"),
        )
    )
    assert result.season_id == "standard"
    assert result.provenance == "synthetic"
    recorded = store.observations[0]
    assert recorded["season_id"] == "standard"
    assert recorded["provenance"] == "synthetic"
    assert recorded["observed_at"].tzinfo is not None

    with pytest.raises(InvalidInput, match="future"):
        pricing.record_observation(
            PricingObservationInput(
                product_id=PRODUCT,
                recorded_cost=Decimal("6230"),
                supply=Decimal("10"),
                demand=Decimal("56"),
                competitor_cost=Decimal("6500"),
                observed_at=datetime.now(UTC) + timedelta(days=1),
            )
        )


def test_zero_supply_and_zero_demand_leave_the_price_unchanged() -> None:
    store = FakeStore([candidate(supply="0", demand="0", competitor="6230")])
    result = service(store).run(as_of=NOW)
    assert result.unchanged == 1
    assert result.items[0].new_amount is None

def test_bounds_and_rounding_hold_for_fractional_prices() -> None:
    cases = [
        dict(amount="8899.995", cost="1000", supply="0", demand="100", competitor="9999"),
        dict(amount="0.03", cost="0.01", supply="0", demand="100", competitor="0.02"),
        dict(amount="12345.678", cost="12000", supply="50", demand="5", competitor="11000"),
        dict(amount="50.005", cost="49.99", supply="10", demand="10", competitor="49.99"),
    ]
    for inputs in cases:
        result = service(FakeStore([candidate(**inputs)])).run(as_of=NOW)
        item = result.items[0]
        if item.outcome != "updated":
            continue
        amount = item.new_amount
        assert amount == amount.quantize(Decimal("0.01")), inputs
        assert amount <= Decimal(inputs["amount"]) * (
            Decimal("1") + MAX_CHANGE_RATIO
        ), inputs
        assert amount >= Decimal(inputs["cost"]) * (
            Decimal("1") + MIN_MARGIN_RATIO
        ), inputs
