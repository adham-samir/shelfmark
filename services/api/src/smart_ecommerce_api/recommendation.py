"""SF-01 hybrid collaborative/content recommendation runtime."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import joblib
import numpy as np
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json
from pydantic import Field

from . import db
from .errors import DependencyUnavailable
from .models import StrictModel


class RecommendationBasis(StrictModel):
    browsing_events: int = Field(ge=0)
    purchased_items: int = Field(ge=0)


class RecommendationResult(StrictModel):
    items: list[UUID]
    strategy: str
    model_version: str
    basis: RecommendationBasis


@dataclass(frozen=True, slots=True)
class CustomerSignals:
    weights: dict[str, float]
    seen: frozenset[str]
    browsing_events: int
    purchased_items: int


class RecommendationStore:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def customer_signals(self, customer_id: UUID) -> CustomerSignals:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                rows = connection.execute(
                    """
                    WITH signals AS (
                        SELECT product_id,
                               CASE event_type
                                   WHEN 'view' THEN 1.0
                                   WHEN 'search_click' THEN 2.0
                                   WHEN 'compare' THEN 3.0
                                   WHEN 'add_to_cart' THEN 4.0
                               END AS weight,
                               false AS purchase
                        FROM browsing_events WHERE customer_id = %s
                        UNION ALL
                        SELECT oi.product_id, 5.0 AS weight, true AS purchase
                        FROM orders o JOIN order_items oi USING (order_id)
                        WHERE o.customer_id = %s
                          AND o.status IN ('confirmed', 'shipped', 'delivered')
                    )
                    SELECT product_id, sum(weight) AS weight,
                           count(*) FILTER (WHERE NOT purchase) AS browsing_events,
                           count(*) FILTER (WHERE purchase) AS purchased_items
                    FROM signals GROUP BY product_id
                    """,
                    (customer_id, customer_id),
                ).fetchall()
                return CustomerSignals(
                    weights={str(row["product_id"]): float(row["weight"]) for row in rows},
                    seen=frozenset(str(row["product_id"]) for row in rows),
                    browsing_events=sum(row["browsing_events"] for row in rows),
                    purchased_items=sum(row["purchased_items"] for row in rows),
                )
        except psycopg.Error as error:
            raise DependencyUnavailable("Recommendation history is unavailable.") from error

    def active_products(self) -> set[str]:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                rows = connection.execute(
                    "SELECT product_id FROM product_registry WHERE lifecycle = 'active'"
                ).fetchall()
                return {str(row["product_id"]) for row in rows}
        except psycopg.Error as error:
            raise DependencyUnavailable("Recommendation catalog is unavailable.") from error

    def record(
        self,
        *,
        customer_id: UUID,
        artifact: dict[str, Any],
        strategy: str,
        basis: RecommendationBasis,
        ranked: list[tuple[str, float, float, float]],
    ) -> None:
        try:
            with db.connection(self._dsn) as connection:
                model_version_id = UUID(artifact["model_version_id"])
                evaluation_id = UUID(artifact["evaluation_id"])
                connection.execute(
                    """
                    INSERT INTO model_versions(
                        model_version_id, module, version_label,
                        dataset_snapshot_id, artifact_reference, framework
                    ) VALUES (%s, 'recommendation', %s, %s, %s, 'scikit-learn')
                    ON CONFLICT (model_version_id) DO NOTHING
                    """,
                    (model_version_id, artifact["version_label"], artifact["dataset_snapshot_id"],
                     "services/api/artifacts/recommendation.joblib"),
                )
                connection.execute(
                    """
                    INSERT INTO evaluation_runs(
                        evaluation_id, model_version_id, dataset_snapshot_id,
                        split_strategy, metrics, limitations
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (evaluation_id) DO NOTHING
                    """,
                    (evaluation_id, model_version_id, artifact["dataset_snapshot_id"],
                     "fixed user holdout cases separate from collaborative-training users",
                     Json(artifact["metrics"]),
                     "Synthetic four-product fixture validates pipeline behavior only."),
                )
                run_id = uuid4()
                connection.execute(
                    """
                    INSERT INTO recommendation_runs(
                        run_id, customer_id, model_version_id, strategy, input_summary
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    (run_id, customer_id, model_version_id, strategy, Json(basis.model_dump())),
                )
                for rank, (product_id, collaborative, content, combined) in enumerate(ranked, 1):
                    connection.execute(
                        """
                        INSERT INTO recommendation_items(
                            run_id, product_id, rank, collaborative_score,
                            content_score, combined_score
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (run_id, UUID(product_id), rank, collaborative, content, combined),
                    )
        except psycopg.Error as error:
            raise DependencyUnavailable("Recommendation evidence could not be stored.") from error


class RecommendationService:
    def __init__(self, store: RecommendationStore, artifact_path: str) -> None:
        self._store = store
        self._artifact_path = Path(artifact_path)
        self._artifact: dict[str, Any] | None = None

    def _load(self) -> dict[str, Any]:
        if self._artifact is None:
            try:
                artifact = joblib.load(self._artifact_path)
                required = {
                    "model_version_id", "evaluation_id", "version_label",
                    "dataset_snapshot_id", "product_ids", "collaborative_similarity",
                    "content_similarity", "popularity", "metrics",
                }
                if not required.issubset(artifact):
                    raise ValueError("artifact keys missing")
                self._artifact = artifact
            except Exception as error:
                raise DependencyUnavailable("The recommendation artifact is unavailable.") from error
        return self._artifact

    @staticmethod
    def _normalized(values: np.ndarray) -> np.ndarray:
        maximum = float(values.max(initial=0))
        return values / maximum if maximum > 0 else values

    def recommend(self, customer_id: UUID, limit: int) -> RecommendationResult:
        artifact = self._load()
        product_ids = artifact["product_ids"]
        index = {product_id: position for position, product_id in enumerate(product_ids)}
        signals = self._store.customer_signals(customer_id)
        active = self._store.active_products()
        vector = np.zeros(len(product_ids), dtype=float)
        for product_id, weight in signals.weights.items():
            if product_id in index:
                vector[index[product_id]] = weight
        basis = RecommendationBasis(
            browsing_events=signals.browsing_events,
            purchased_items=signals.purchased_items,
        )
        if float(vector.sum()) == 0:
            collaborative = np.zeros(len(product_ids), dtype=float)
            content = np.zeros(len(product_ids), dtype=float)
            combined = self._normalized(np.asarray(artifact["popularity"], dtype=float))
            strategy = "cold_start_fallback"
        else:
            collaborative = self._normalized(vector @ artifact["collaborative_similarity"])
            content = self._normalized(vector @ artifact["content_similarity"])
            combined = 0.6 * collaborative + 0.4 * content + 0.01 * self._normalized(
                np.asarray(artifact["popularity"], dtype=float)
            )
            strategy = "hybrid"
        candidates = [
            position for position, product_id in enumerate(product_ids)
            if product_id in active and product_id not in signals.seen
        ]
        candidates.sort(key=lambda position: (-combined[position], product_ids[position]))
        ranked = [
            (product_ids[position], round(float(collaborative[position]), 9),
             round(float(content[position]), 9), round(float(combined[position]), 9))
            for position in candidates[:limit]
        ]
        self._store.record(
            customer_id=customer_id, artifact=artifact, strategy=strategy,
            basis=basis, ranked=ranked,
        )
        return RecommendationResult(
            items=[UUID(item[0]) for item in ranked], strategy=strategy,
            model_version=artifact["version_label"], basis=basis,
        )
