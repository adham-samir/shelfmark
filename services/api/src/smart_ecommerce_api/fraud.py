"""BO-04 fraud risk assessment.

The trained model scores payment transactions before order completion and
returns a risk score plus human-readable feature flags. DEC-010 still governs
the response: scores at or above the review threshold, forced sandbox tokens,
and assessment failures go to review; only a passed assessment can confirm an
order. Missing artifacts fail closed to review.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

import joblib
import psycopg
from psycopg.types.json import Json

from . import db
from .errors import DependencyUnavailable
from .models import StrictModel

MODEL_MODULE = "fraud"
SCORE_REVIEW_FLOOR = 0.70
FEATURE_NAMES = (
    "amount_ratio",
    "amount_ratio_high",
    "amount_log",
    "high_amount",
    "item_count",
    "order_hour_sin",
    "order_hour_cos",
    "overnight",
    "is_weekend",
    "customer_age_log",
    "prior_orders_log",
    "orders_last_24h",
    "prior_failed_orders",
    "new_address",
    "token_reuse",
    "first_order",
)


@dataclass(frozen=True, slots=True)
class RiskContext:
    """Signals available before completion; no card or token data is included."""

    customer_id: UUID
    amount: Decimal
    item_count: int
    order_hour: int
    weekday: int
    customer_age_days: int
    prior_orders: int
    average_order_value: Decimal | None
    orders_last_24h: int
    prior_failed_orders: int
    new_address: bool
    token_reuse: int


@dataclass(frozen=True, slots=True)
class RiskResult:
    score: Decimal | None
    outcome: str
    reasons: list[str]
    model_version_id: UUID | None = None


class RiskAssessor(Protocol):
    def assess(self, context: RiskContext, payment_token: str) -> RiskResult: ...


class FraudModelSummary(StrictModel):
    model_version_id: UUID
    version_label: str
    dataset_snapshot_id: str
    threshold: str
    feature_names: list[str]
    metrics: dict[str, Any]
    limitations: str
    trained_at: str | None = None


def features(context: RiskContext) -> list[float]:
    """Deterministic feature vector shared by training and serving."""

    average = context.average_order_value
    if average is None or average <= 0:
        amount_ratio = 1.0
    else:
        amount_ratio = max(0.1, min(20.0, float(context.amount / average)))
    hour_angle = 2 * math.pi * (context.order_hour % 24) / 24
    return [
        amount_ratio,
        1.0 if amount_ratio >= 3 else 0.0,
        math.log1p(float(context.amount)),
        1.0 if context.amount > 20000 else 0.0,
        float(context.item_count),
        math.sin(hour_angle),
        math.cos(hour_angle),
        1.0 if context.order_hour < 6 else 0.0,
        1.0 if context.weekday >= 5 else 0.0,
        math.log1p(max(0, context.customer_age_days)),
        math.log1p(max(0, context.prior_orders)),
        float(context.orders_last_24h),
        float(context.prior_failed_orders),
        1.0 if context.new_address else 0.0,
        float(context.token_reuse),
        1.0 if context.prior_orders == 0 else 0.0,
    ]


def triggered_reasons(context: RiskContext) -> list[str]:
    reasons: list[str] = []
    average = context.average_order_value
    if average and average > 0 and context.amount >= average * 3:
        reasons.append("amount_above_customer_norm")
    if context.orders_last_24h >= 3:
        reasons.append("order_velocity_24h_high")
    if context.prior_failed_orders >= 2:
        reasons.append("prior_failed_attempts")
    if context.new_address and context.prior_orders > 0:
        reasons.append("new_shipping_address")
    if context.token_reuse >= 2:
        reasons.append("payment_token_reuse")
    if context.order_hour < 6:
        reasons.append("unusual_order_hour")
    if context.prior_orders == 0:
        reasons.append("first_order")
    return reasons


class FraudEvidenceStore:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def ensure(self, artifact: dict[str, Any]) -> None:
        try:
            with db.connection(self._dsn) as connection:
                connection.execute(
                    """
                    INSERT INTO model_versions(
                        model_version_id, module, version_label, dataset_snapshot_id,
                        artifact_reference, framework
                    ) VALUES (%s, %s, %s, %s, %s, 'scikit-learn')
                    ON CONFLICT (model_version_id) DO NOTHING
                    """,
                    (
                        UUID(artifact["model_version_id"]),
                        MODEL_MODULE,
                        artifact["version_label"],
                        artifact["dataset_snapshot_id"],
                        "services/api/artifacts/fraud.joblib",
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO evaluation_runs(
                        evaluation_id, model_version_id, dataset_snapshot_id,
                        split_strategy, metrics, limitations
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (evaluation_id) DO NOTHING
                    """,
                    (
                        UUID(artifact["evaluation_id"]),
                        UUID(artifact["model_version_id"]),
                        artifact["dataset_snapshot_id"],
                        "stratified 60/20/20 train/validation/holdout; threshold "
                        "selected on validation, holdout reported once",
                        Json(artifact["metrics"]),
                        artifact["limitations"],
                    ),
                )
        except psycopg.Error as error:
            raise DependencyUnavailable(
                "Fraud model evidence could not be stored."
            ) from error


class ModelRiskAssessor:
    def __init__(self, artifact_path: str, evidence: FraudEvidenceStore) -> None:
        self._artifact_path = Path(artifact_path)
        self._evidence = evidence
        self._artifact: dict[str, Any] | None = None
        self._evidence_stored = False

    def _load(self) -> dict[str, Any]:
        if self._artifact is None:
            try:
                artifact = joblib.load(self._artifact_path)
                required = {
                    "model",
                    "feature_names",
                    "threshold",
                    "model_version_id",
                    "evaluation_id",
                    "version_label",
                    "dataset_snapshot_id",
                    "metrics",
                    "limitations",
                }
                if not required.issubset(artifact):
                    raise ValueError("fraud artifact keys missing")
                if tuple(artifact["feature_names"]) != FEATURE_NAMES:
                    raise ValueError("fraud feature set does not match serving")
                self._artifact = artifact
            except Exception as error:
                raise DependencyUnavailable(
                    "The fraud model artifact is unavailable."
                ) from error
        return self._artifact

    def _ensure_evidence(self, artifact: dict[str, Any]) -> None:
        if not self._evidence_stored:
            self._evidence.ensure(artifact)
            self._evidence_stored = True

    def assess(self, context: RiskContext, payment_token: str) -> RiskResult:
        del payment_token
        try:
            artifact = self._load()
            self._ensure_evidence(artifact)
            probability = float(
                artifact["model"].predict_proba([features(context)])[0][1]
            )
            threshold = min(float(artifact["threshold"]), SCORE_REVIEW_FLOOR)
            outcome = "review" if probability >= threshold else "allow"
            reasons = triggered_reasons(context)
            if outcome == "review":
                reasons.append("model_score_at_or_above_threshold")
            else:
                reasons.append("model_score_below_threshold")
            return RiskResult(
                score=Decimal(str(round(probability, 7))),
                outcome=outcome,
                reasons=reasons,
                model_version_id=UUID(artifact["model_version_id"]),
            )
        except Exception:
            return RiskResult(
                score=None,
                outcome="assessment_failed",
                reasons=["fraud_model_unavailable"],
            )

    def summary(self) -> FraudModelSummary:
        artifact = self._load()
        return FraudModelSummary(
            model_version_id=UUID(artifact["model_version_id"]),
            version_label=artifact["version_label"],
            dataset_snapshot_id=artifact["dataset_snapshot_id"],
            threshold=str(min(float(artifact["threshold"]), SCORE_REVIEW_FLOOR)),
            feature_names=list(artifact["feature_names"]),
            metrics=artifact["metrics"],
            limitations=artifact["limitations"],
            trained_at=artifact.get("trained_at"),
        )


class HybridRiskAssessor:
    """Forced sandbox tokens first, then the trained model."""

    def __init__(self, model: ModelRiskAssessor) -> None:
        self._model = model

    def assess(self, context: RiskContext, payment_token: str) -> RiskResult:
        if "risk-fail" in payment_token:
            return RiskResult(None, "assessment_failed", ["sandbox_assessment_failure"])
        if "risk-high" in payment_token:
            return RiskResult(
                Decimal("0.9100000"), "review", ["sandbox_high_risk"]
            )
        return self._model.assess(context, payment_token)


def now_signals(now: datetime | None = None) -> tuple[int, int]:
    current = now or datetime.now(UTC)
    return current.hour, current.weekday()