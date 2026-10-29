import json
from pathlib import Path
from uuid import UUID

from smart_ecommerce_api.errors import DependencyUnavailable
from smart_ecommerce_api.recommendation import (
    CustomerSignals,
    RecommendationService,
)


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/recommendation.joblib"
EVALUATION = ROOT / "artifacts/recommendation.evaluation.json"
CUSTOMER_ID = UUID("20000000-0000-4000-8000-000000000001")
PRODUCT_ONE = "10000000-0000-4000-8000-000000000001"
PRODUCT_TWO = "10000000-0000-4000-8000-000000000002"
ALL_PRODUCTS = {
    f"10000000-0000-4000-8000-00000000000{number}" for number in range(1, 5)
}


class FakeStore:
    def __init__(self, signals: CustomerSignals) -> None:
        self.signals = signals
        self.recorded = None

    def customer_signals(self, customer_id):
        assert customer_id == CUSTOMER_ID
        return self.signals

    def active_products(self):
        return ALL_PRODUCTS

    def record(self, **values):
        self.recorded = values


def test_hybrid_uses_history_and_ranks_related_unseen_product() -> None:
    store = FakeStore(
        CustomerSignals(
            weights={PRODUCT_ONE: 6.0},
            seen=frozenset({PRODUCT_ONE}),
            browsing_events=1,
            purchased_items=1,
        )
    )
    result = RecommendationService(store, str(ARTIFACT)).recommend(CUSTOMER_ID, 3)
    assert result.strategy == "hybrid"
    assert str(result.items[0]) == PRODUCT_TWO
    assert result.basis.browsing_events == 1
    assert result.basis.purchased_items == 1
    assert store.recorded["ranked"][0][0] == PRODUCT_TWO


def test_cold_start_uses_popularity_and_records_strategy() -> None:
    store = FakeStore(
        CustomerSignals({}, frozenset(), browsing_events=0, purchased_items=0)
    )
    result = RecommendationService(store, str(ARTIFACT)).recommend(CUSTOMER_ID, 2)
    assert result.strategy == "cold_start_fallback"
    assert len(result.items) == 2
    assert store.recorded["strategy"] == "cold_start_fallback"


def test_missing_artifact_fails_explicitly() -> None:
    store = FakeStore(CustomerSignals({}, frozenset(), 0, 0))
    try:
        RecommendationService(store, "/definitely/missing.joblib").recommend(CUSTOMER_ID, 2)
    except DependencyUnavailable as error:
        assert "artifact" in error.message
    else:
        raise AssertionError("missing recommendation artifact must fail explicitly")


def test_evaluation_exceeds_accepted_synthetic_baseline() -> None:
    evaluation = json.loads(EVALUATION.read_text())
    assert evaluation["metrics"]["relative_lift"] >= 0.10
    assert evaluation["metrics"]["hybrid_ndcg_at_10"] == 1.0
    assert "Synthetic" in evaluation["limitations"]
