from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import joblib

from smart_ecommerce_api.fraud import (
    FEATURE_NAMES,
    SCORE_REVIEW_FLOOR,
    HybridRiskAssessor,
    ModelRiskAssessor,
    RiskContext,
    features,
    triggered_reasons,
)


ROOT = Path(__file__).parents[1]
ARTIFACT = ROOT / "artifacts/fraud.joblib"
EVALUATION = ROOT / "artifacts/fraud.evaluation.json"
DATASET = ROOT / "data/fraud.synthetic.json"


class FakeEvidence:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def ensure(self, artifact: dict) -> None:
        self.calls.append(artifact)


def context(**overrides) -> RiskContext:
    values = {
        "customer_id": UUID("20000000-0000-4000-8000-000000000001"),
        "amount": Decimal("8900"),
        "item_count": 2,
        "order_hour": 15,
        "weekday": 2,
        "customer_age_days": 400,
        "prior_orders": 8,
        "average_order_value": Decimal("7000"),
        "orders_last_24h": 0,
        "prior_failed_orders": 0,
        "new_address": False,
        "token_reuse": 0,
    }
    values.update(overrides)
    return RiskContext(**values)


def assessor(path: Path = ARTIFACT) -> tuple[HybridRiskAssessor, FakeEvidence]:
    evidence = FakeEvidence()
    model = ModelRiskAssessor(str(path), evidence)
    return HybridRiskAssessor(model), evidence


def test_feature_vector_shape_and_first_order_neutrality() -> None:
    values = features(context())
    assert len(values) == len(FEATURE_NAMES)
    first = features(
        context(prior_orders=0, average_order_value=None, amount=Decimal("40000"))
    )
    assert first[0] == 1.0
    assert first[-1] == 1.0


def test_model_allows_normal_and_reviews_suspicious_contexts() -> None:
    hybrid, _ = assessor()
    normal = hybrid.assess(context(), "tok_sandbox_safe")
    assert normal.outcome == "allow"
    assert normal.score is not None and normal.score < Decimal("0.70")
    assert normal.model_version_id is not None

    suspicious = hybrid.assess(
        context(
            amount=Decimal("45000"),
            item_count=5,
            order_hour=2,
            weekday=5,
            prior_orders=0,
            average_order_value=None,
            orders_last_24h=5,
            prior_failed_orders=3,
            new_address=True,
            token_reuse=3,
        ),
        "tok_sandbox_suspicious",
    )
    assert suspicious.outcome == "review"
    assert suspicious.score is not None and suspicious.score >= Decimal("0.70")
    assert "model_score_at_or_above_threshold" in suspicious.reasons


def test_forced_sandbox_tokens_keep_their_behavior() -> None:
    hybrid, _ = assessor()
    high = hybrid.assess(context(), "tok_sandbox_risk-high")
    assert high.outcome == "review"
    assert high.score == Decimal("0.9100000")
    assert high.reasons == ["sandbox_high_risk"]
    failed = hybrid.assess(context(), "tok_sandbox_risk-fail")
    assert failed.outcome == "assessment_failed"
    assert failed.score is None
    assert failed.reasons == ["sandbox_assessment_failure"]


def test_missing_artifact_fails_closed(tmp_path: Path) -> None:
    hybrid, _ = assessor(tmp_path / "missing.joblib")
    result = hybrid.assess(context(), "tok_sandbox_safe")
    assert result.outcome == "assessment_failed"
    assert result.score is None
    assert result.reasons == ["fraud_model_unavailable"]


def test_model_evidence_is_registered_once() -> None:
    hybrid, evidence = assessor()
    hybrid.assess(context(), "tok_sandbox_safe")
    hybrid.assess(context(), "tok_sandbox_safe")
    assert len(evidence.calls) == 1
    assert evidence.calls[0]["version_label"].endswith("fraud-v1")


def test_summary_reports_metrics_and_respects_the_review_floor() -> None:
    evidence = FakeEvidence()
    summary = ModelRiskAssessor(str(ARTIFACT), evidence).summary()
    assert summary.feature_names == list(FEATURE_NAMES)
    assert float(summary.threshold) <= SCORE_REVIEW_FLOOR
    assert summary.metrics["recall"] >= 0.80
    assert summary.metrics["false_positive_rate"] <= 0.10
    assert "synthetic" in summary.limitations.lower()


def test_holdout_evaluation_meets_the_source_targets() -> None:
    evaluation = json.loads(EVALUATION.read_text())
    holdout = evaluation["holdout"]
    assert holdout["recall"] >= 0.80
    assert holdout["false_positive_rate"] <= 0.10
    assert evaluation["split"]["strategy"] == "stratified 60/20/20"
    assert set(evaluation["models"]) == {
        "logistic-regression",
        "hist-gradient-boosting",
    }
    assert evaluation["selected_model"] in evaluation["models"]


def test_artifact_feature_set_matches_serving() -> None:
    artifact = joblib.load(ARTIFACT)
    assert tuple(artifact["feature_names"]) == FEATURE_NAMES
    assert artifact["dataset_snapshot_id"].startswith("fraud-synthetic-")
    assert "threshold" in artifact


def test_synthetic_dataset_shape_and_labels() -> None:
    dataset = json.loads(DATASET.read_text())
    assert dataset["transactions"] == len(dataset["rows"]) == 3000
    assert 0.05 <= dataset["positive_rate"] <= 0.25
    labels = {row["label"] for row in dataset["rows"]}
    assert labels == {0, 1}
    first = dataset["rows"][0]["context"]
    assert {
        "amount",
        "item_count",
        "order_hour",
        "prior_orders",
        "average_order_value",
        "new_address",
        "token_reuse",
    }.issubset(first)


def test_triggered_reasons_cover_each_named_signal() -> None:
    reasons = triggered_reasons(
        context(
            amount=Decimal("30000"),
            average_order_value=Decimal("5000"),
            orders_last_24h=4,
            prior_failed_orders=3,
            new_address=True,
            token_reuse=4,
            order_hour=2,
        )
    )
    assert "amount_above_customer_norm" in reasons
    assert "order_velocity_24h_high" in reasons
    assert "prior_failed_attempts" in reasons
    assert "new_shipping_address" in reasons
    assert "payment_token_reuse" in reasons
    assert "unusual_order_hour" in reasons