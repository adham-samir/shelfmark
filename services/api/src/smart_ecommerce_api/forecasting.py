"""BO-01 chronological demand forecasting and automatic reorder policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, ROUND_CEILING
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol
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


FORECAST_DAYS = 14
LEAD_TIME_DAYS = 7
SAFETY_STOCK_DAYS = 7
TARGET_COVER_DAYS = 21
POLICY_VERSION = "dec-008-v1"
PENDING_REORDER_STATUSES = ("created", "dispatched", "acknowledged")


class ForecastSummary(StrictModel):
    forecast_id: UUID
    horizon_start: date
    horizon_end: date
    predicted_quantity: Decimal = Field(ge=0)
    model_version: str
    generated_at: datetime


class ReorderSummary(StrictModel):
    reorder_id: UUID
    quantity: int = Field(gt=0)
    status: str
    supplier_reference: str | None = None
    simulator: bool
    status_detail: str | None = None
    last_attempted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class InventoryPlanningItem(StrictModel):
    product_id: UUID
    on_hand: int = Field(ge=0)
    reserved: int = Field(ge=0)
    available: int = Field(ge=0)
    pending_replenishment: int = Field(ge=0)
    inventory_position: int = Field(ge=0)
    forecast: ForecastSummary | None = None
    reorder_point: int | None = Field(default=None, ge=0)
    target_stock: int | None = Field(default=None, ge=0)
    latest_reorder: ReorderSummary | None = None
    planning_status: str


class InventoryPolicy(StrictModel):
    version: str = POLICY_VERSION
    forecast_days: int = FORECAST_DAYS
    lead_time_days: int = LEAD_TIME_DAYS
    safety_stock_days: int = SAFETY_STOCK_DAYS
    target_cover_days: int = TARGET_COVER_DAYS


class InventoryPlanningResponse(StrictModel):
    generated_at: datetime
    policy: InventoryPolicy
    items: list[InventoryPlanningItem]


class ReorderRunItem(StrictModel):
    product_id: UUID
    forecast_id: UUID | None = None
    predicted_quantity: Decimal | None = Field(default=None, ge=0)
    reorder_id: UUID | None = None
    reorder_quantity: int = Field(default=0, ge=0)
    outcome: str


class ReorderRunResult(StrictModel):
    run_date: date
    model_version: str
    forecasts_generated: int = Field(ge=0)
    reorders_created: int = Field(ge=0)
    reorders_reused: int = Field(ge=0)
    adequate_stock: int = Field(ge=0)
    insufficient_history: int = Field(ge=0)
    items: list[ReorderRunItem]


@dataclass(frozen=True, slots=True)
class DemandHistory:
    values: list[float]
    observed_days: int


@dataclass(frozen=True, slots=True)
class InventorySnapshot:
    product_id: UUID
    on_hand: int
    reserved: int
    available: int
    pending_replenishment: int


@dataclass(frozen=True, slots=True)
class StoredReorder:
    reorder_id: UUID
    status: str
    created: bool


class SupplierGateway(Protocol):
    def dispatch(self, *, reorder_id: UUID, idempotency_key: str, quantity: int) -> str: ...


class SandboxSupplierSimulator:
    """Deterministic supplier boundary used only by the project demonstration."""

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def dispatch(self, *, reorder_id: UUID, idempotency_key: str, quantity: int) -> str:
        if self.fail:
            raise DependencyUnavailable("The supplier simulator rejected the reorder dispatch.")
        digest = sha256(f"{reorder_id}:{idempotency_key}:{quantity}".encode()).hexdigest()
        return f"SIM-{digest[:12].upper()}"


class InventoryStore:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def snapshots(self) -> list[InventorySnapshot]:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                rows = connection.execute(
                    """
                    SELECT r.product_id, i.on_hand, i.reserved, i.available,
                           COALESCE(sum(rr.quantity) FILTER (
                               WHERE rr.status IN ('created', 'dispatched', 'acknowledged')
                           ), 0)::integer AS pending_replenishment
                    FROM product_registry r
                    JOIN inventory_balances i USING (product_id)
                    LEFT JOIN reorder_records rr USING (product_id)
                    WHERE r.lifecycle = 'active'
                    GROUP BY r.product_id, i.on_hand, i.reserved, i.available
                    ORDER BY r.product_id
                    """
                ).fetchall()
            return [InventorySnapshot(**row) for row in rows]
        except psycopg.Error as error:
            raise DependencyUnavailable("Inventory planning data is unavailable.") from error

    def demand_history(self, product_id: UUID, as_of: date, days: int = 210) -> DemandHistory:
        start = as_of - timedelta(days=days)
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                rows = connection.execute(
                    """
                    SELECT occurred_at::date AS demand_date,
                           sum(-quantity_delta)::double precision AS quantity
                    FROM inventory_movements
                    WHERE product_id = %s
                      AND reason = 'sale'
                      AND quantity_delta < 0
                      AND occurred_at >= %s
                      AND occurred_at < %s
                    GROUP BY occurred_at::date
                    ORDER BY occurred_at::date
                    """,
                    (product_id, start, as_of),
                ).fetchall()
        except psycopg.Error as error:
            raise DependencyUnavailable("Historical demand is unavailable.") from error
        by_date = {row["demand_date"]: float(row["quantity"]) for row in rows}
        values = [by_date.get(start + timedelta(days=index), 0.0) for index in range(days)]
        return DemandHistory(values=values, observed_days=len(by_date))

    def record_evidence(self, artifact: dict[str, Any]) -> None:
        try:
            with db.connection(self._dsn) as connection:
                model_version_id = UUID(artifact["model_version_id"])
                connection.execute(
                    """
                    INSERT INTO model_versions(
                        model_version_id, module, version_label, dataset_snapshot_id,
                        artifact_reference, framework
                    ) VALUES (%s, 'forecast', %s, %s, %s, 'scikit-learn')
                    ON CONFLICT (model_version_id) DO NOTHING
                    """,
                    (
                        model_version_id,
                        artifact["version_label"],
                        artifact["dataset_snapshot_id"],
                        "services/api/artifacts/forecast.joblib",
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
                        model_version_id,
                        artifact["dataset_snapshot_id"],
                        "final 28 calendar days held out; lag and rolling features use prior observations only",
                        Json(artifact["metrics"]),
                        artifact["limitations"],
                    ),
                )
        except psycopg.Error as error:
            raise DependencyUnavailable("Forecast evidence could not be stored.") from error

    def save_forecast(
        self,
        *,
        product_id: UUID,
        model_version_id: UUID,
        horizon_start: date,
        horizon_end: date,
        predicted_quantity: Decimal,
    ) -> UUID:
        forecast_id = uuid4()
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                row = connection.execute(
                    """
                    INSERT INTO demand_forecasts(
                        forecast_id, product_id, model_version_id, horizon_start,
                        horizon_end, predicted_quantity
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (product_id, model_version_id, horizon_start, horizon_end)
                    DO UPDATE SET predicted_quantity = EXCLUDED.predicted_quantity,
                                  generated_at = CURRENT_TIMESTAMP
                    RETURNING forecast_id
                    """,
                    (
                        forecast_id, product_id, model_version_id, horizon_start,
                        horizon_end, predicted_quantity,
                    ),
                ).fetchone()
            return row["forecast_id"]
        except psycopg.Error as error:
            raise DependencyUnavailable("The demand forecast could not be stored.") from error

    def begin_reorder(
        self,
        *,
        product_id: UUID,
        forecast_id: UUID,
        idempotency_key: str,
        quantity: int,
        policy_snapshot: dict[str, Any],
        decision_inputs: dict[str, Any],
    ) -> StoredReorder:
        reorder_id = uuid4()
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                inserted = connection.execute(
                    """
                    INSERT INTO reorder_records(
                        reorder_id, product_id, forecast_id, idempotency_key,
                        quantity, status, policy_snapshot, decision_inputs
                    ) VALUES (%s, %s, %s, %s, %s, 'created', %s, %s)
                    ON CONFLICT (idempotency_key) DO NOTHING
                    RETURNING reorder_id, status
                    """,
                    (
                        reorder_id, product_id, forecast_id, idempotency_key, quantity,
                        Json(policy_snapshot), Json(decision_inputs),
                    ),
                ).fetchone()
                if inserted is not None:
                    return StoredReorder(inserted["reorder_id"], inserted["status"], True)
                existing = connection.execute(
                    """
                    SELECT reorder_id, status FROM reorder_records
                    WHERE idempotency_key = %s FOR UPDATE
                    """,
                    (idempotency_key,),
                ).fetchone()
                if existing["status"] == "failed":
                    connection.execute(
                        """
                        UPDATE reorder_records
                        SET status = 'created', status_detail = NULL,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE reorder_id = %s
                        """,
                        (existing["reorder_id"],),
                    )
                    return StoredReorder(existing["reorder_id"], "created", False)
                return StoredReorder(existing["reorder_id"], existing["status"], False)
        except psycopg.Error as error:
            raise DependencyUnavailable("The reorder record could not be created.") from error

    def mark_reorder(
        self,
        reorder_id: UUID,
        *,
        status: str,
        supplier_reference: str | None,
        status_detail: str,
    ) -> None:
        try:
            with db.connection(self._dsn) as connection:
                connection.execute(
                    """
                    UPDATE reorder_records
                    SET status = %s, supplier_reference = %s, status_detail = %s,
                        last_attempted_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE reorder_id = %s
                    """,
                    (status, supplier_reference, status_detail, reorder_id),
                )
        except psycopg.Error as error:
            raise DependencyUnavailable("The supplier result could not be stored.") from error

    def planning_rows(self) -> list[dict[str, Any]]:
        try:
            with db.connection(self._dsn, row_factory=dict_row) as connection:
                return connection.execute(
                    """
                    SELECT r.product_id, i.on_hand, i.reserved, i.available,
                           COALESCE(pending.quantity, 0)::integer AS pending_replenishment,
                           f.forecast_id, f.horizon_start, f.horizon_end,
                           f.predicted_quantity, f.generated_at,
                           mv.version_label AS model_version,
                           rr.reorder_id, rr.quantity AS reorder_quantity,
                           rr.status AS reorder_status,
                           rr.supplier_reference, rr.simulator, rr.status_detail,
                           rr.last_attempted_at, rr.created_at AS reorder_created_at,
                           rr.updated_at AS reorder_updated_at
                    FROM product_registry r
                    JOIN inventory_balances i USING (product_id)
                    LEFT JOIN LATERAL (
                        SELECT sum(quantity) AS quantity FROM reorder_records
                        WHERE product_id = r.product_id
                          AND status IN ('created', 'dispatched', 'acknowledged')
                    ) pending ON true
                    LEFT JOIN LATERAL (
                        SELECT * FROM demand_forecasts
                        WHERE product_id = r.product_id
                        ORDER BY generated_at DESC LIMIT 1
                    ) f ON true
                    LEFT JOIN model_versions mv USING (model_version_id)
                    LEFT JOIN LATERAL (
                        SELECT * FROM reorder_records
                        WHERE product_id = r.product_id
                        ORDER BY created_at DESC LIMIT 1
                    ) rr ON true
                    WHERE r.lifecycle = 'active'
                    ORDER BY r.product_id
                    """
                ).fetchall()
        except psycopg.Error as error:
            raise DependencyUnavailable("Inventory planning data is unavailable.") from error


class InventoryService:
    def __init__(
        self,
        store: InventoryStore,
        artifact_path: str,
        supplier: SupplierGateway,
    ) -> None:
        self._store = store
        self._artifact_path = Path(artifact_path)
        self._supplier = supplier
        self._artifact: dict[str, Any] | None = None

    def _load(self) -> dict[str, Any]:
        if self._artifact is None:
            try:
                artifact = joblib.load(self._artifact_path)
                required = {
                    "model_version_id", "evaluation_id", "version_label",
                    "dataset_snapshot_id", "product_ids", "minimum_history_days",
                    "forecast_horizon_days", "metrics", "limitations", "model",
                }
                if not required.issubset(artifact):
                    raise ValueError("forecast artifact keys missing")
                if artifact["forecast_horizon_days"] != FORECAST_DAYS:
                    raise ValueError("forecast horizon does not match DEC-008")
                self._artifact = artifact
            except Exception as error:
                raise DependencyUnavailable("The forecast model artifact is unavailable.") from error
        return self._artifact

    @staticmethod
    def _feature_vector(
        history: list[float], target_date: date, product_index: int, product_count: int
    ) -> list[float]:
        one_hot = [1.0 if index == product_index else 0.0 for index in range(product_count)]
        angle = 2 * np.pi * target_date.weekday() / 7
        return [
            history[-1], history[-7], history[-14],
            float(np.mean(history[-7:])), float(np.mean(history[-28:])),
            float(np.sin(angle)), float(np.cos(angle)), *one_hot,
        ]

    def _forecast_product(
        self, artifact: dict[str, Any], product_id: UUID, as_of: date
    ) -> Decimal | None:
        product_ids: list[str] = artifact["product_ids"]
        product_key = str(product_id)
        if product_key not in product_ids:
            return None
        history = self._store.demand_history(product_id, as_of)
        if history.observed_days < artifact["minimum_history_days"]:
            return None
        values = list(history.values)
        product_index = product_ids.index(product_key)
        predictions: list[float] = []
        for step in range(FORECAST_DAYS):
            target_date = as_of + timedelta(days=step)
            vector = self._feature_vector(values, target_date, product_index, len(product_ids))
            prediction = max(0.0, float(artifact["model"].predict([vector])[0]))
            predictions.append(prediction)
            values.append(prediction)
        return Decimal(str(round(sum(predictions), 6)))

    @staticmethod
    def _policy_values(predicted: Decimal, snapshot: InventorySnapshot) -> tuple[int, int, int]:
        daily = predicted / Decimal(FORECAST_DAYS)
        reorder_point = int(
            (daily * Decimal(LEAD_TIME_DAYS + SAFETY_STOCK_DAYS)).to_integral_value(
                rounding=ROUND_CEILING
            )
        )
        target_stock = int(
            (daily * Decimal(TARGET_COVER_DAYS)).to_integral_value(rounding=ROUND_CEILING)
        )
        inventory_position = snapshot.available + snapshot.pending_replenishment
        reorder_quantity = max(0, target_stock - inventory_position) if inventory_position < reorder_point else 0
        return reorder_point, target_stock, reorder_quantity

    def run(self, as_of: date | None = None) -> ReorderRunResult:
        run_date = as_of or datetime.now(UTC).date()
        artifact = self._load()
        self._store.record_evidence(artifact)
        model_version_id = UUID(artifact["model_version_id"])
        horizon_start = run_date
        horizon_end = run_date + timedelta(days=FORECAST_DAYS - 1)
        created = reused = adequate = insufficient = 0
        items: list[ReorderRunItem] = []
        supplier_failures: list[DependencyUnavailable] = []

        for snapshot in self._store.snapshots():
            predicted = self._forecast_product(artifact, snapshot.product_id, run_date)
            if predicted is None:
                insufficient += 1
                items.append(ReorderRunItem(product_id=snapshot.product_id, outcome="insufficient_history"))
                continue
            forecast_id = self._store.save_forecast(
                product_id=snapshot.product_id,
                model_version_id=model_version_id,
                horizon_start=horizon_start,
                horizon_end=horizon_end,
                predicted_quantity=predicted,
            )
            reorder_point, target_stock, quantity = self._policy_values(predicted, snapshot)
            if quantity == 0:
                adequate += 1
                items.append(
                    ReorderRunItem(
                        product_id=snapshot.product_id,
                        forecast_id=forecast_id,
                        predicted_quantity=predicted,
                        outcome="adequate_stock",
                    )
                )
                continue

            key_material = (
                f"{POLICY_VERSION}:{artifact['version_label']}:{snapshot.product_id}:"
                f"{horizon_start.isoformat()}:{horizon_end.isoformat()}"
            )
            idempotency_key = f"inventory:{sha256(key_material.encode()).hexdigest()}"
            reorder = self._store.begin_reorder(
                product_id=snapshot.product_id,
                forecast_id=forecast_id,
                idempotency_key=idempotency_key,
                quantity=quantity,
                policy_snapshot=InventoryPolicy().model_dump(),
                decision_inputs={
                    "available": snapshot.available,
                    "pending_replenishment": snapshot.pending_replenishment,
                    "inventory_position": snapshot.available + snapshot.pending_replenishment,
                    "predicted_quantity": str(predicted),
                    "reorder_point": reorder_point,
                    "target_stock": target_stock,
                },
            )
            if reorder.created:
                created += 1
            else:
                reused += 1
            outcome = "created" if reorder.created else "reused"
            if reorder.status in ("created", "failed"):
                try:
                    reference = self._supplier.dispatch(
                        reorder_id=reorder.reorder_id,
                        idempotency_key=idempotency_key,
                        quantity=quantity,
                    )
                    self._store.mark_reorder(
                        reorder.reorder_id,
                        status="acknowledged",
                        supplier_reference=reference,
                        status_detail="Acknowledged by the synthetic supplier simulator.",
                    )
                except DependencyUnavailable as error:
                    self._store.mark_reorder(
                        reorder.reorder_id,
                        status="failed",
                        supplier_reference=None,
                        status_detail=error.message,
                    )
                    supplier_failures.append(error)
                    outcome = "supplier_failed"
            items.append(
                ReorderRunItem(
                    product_id=snapshot.product_id,
                    forecast_id=forecast_id,
                    predicted_quantity=predicted,
                    reorder_id=reorder.reorder_id,
                    reorder_quantity=quantity,
                    outcome=outcome,
                )
            )
        if supplier_failures:
            raise DependencyUnavailable(
                "One or more supplier-simulator dispatches failed; the failed records are available for retry."
            )
        return ReorderRunResult(
            run_date=run_date,
            model_version=artifact["version_label"],
            forecasts_generated=len(items) - insufficient,
            reorders_created=created,
            reorders_reused=reused,
            adequate_stock=adequate,
            insufficient_history=insufficient,
            items=items,
        )

    def planning(self) -> InventoryPlanningResponse:
        self._load()
        items: list[InventoryPlanningItem] = []
        for row in self._store.planning_rows():
            forecast = None
            reorder_point = target_stock = None
            snapshot = InventorySnapshot(
                product_id=row["product_id"],
                on_hand=row["on_hand"],
                reserved=row["reserved"],
                available=row["available"],
                pending_replenishment=row["pending_replenishment"],
            )
            if row["forecast_id"] is not None:
                forecast = ForecastSummary(
                    forecast_id=row["forecast_id"],
                    horizon_start=row["horizon_start"],
                    horizon_end=row["horizon_end"],
                    predicted_quantity=row["predicted_quantity"],
                    model_version=row["model_version"],
                    generated_at=row["generated_at"],
                )
                reorder_point, target_stock, _ = self._policy_values(
                    forecast.predicted_quantity, snapshot
                )
            latest_reorder = None
            if row["reorder_id"] is not None:
                latest_reorder = ReorderSummary(
                    reorder_id=row["reorder_id"],
                    quantity=row["reorder_quantity"],
                    status=row["reorder_status"],
                    supplier_reference=row["supplier_reference"],
                    simulator=row["simulator"],
                    status_detail=row["status_detail"],
                    last_attempted_at=row["last_attempted_at"],
                    created_at=row["reorder_created_at"],
                    updated_at=row["reorder_updated_at"],
                )
            planning_status = "forecast_missing"
            if forecast is not None:
                planning_status = "reorder_pending" if snapshot.pending_replenishment else "planned"
                if latest_reorder is not None and latest_reorder.status == "failed":
                    planning_status = "supplier_failed"
            items.append(
                InventoryPlanningItem(
                    product_id=snapshot.product_id,
                    on_hand=snapshot.on_hand,
                    reserved=snapshot.reserved,
                    available=snapshot.available,
                    pending_replenishment=snapshot.pending_replenishment,
                    inventory_position=snapshot.available + snapshot.pending_replenishment,
                    forecast=forecast,
                    reorder_point=reorder_point,
                    target_stock=target_stock,
                    latest_reorder=latest_reorder,
                    planning_status=planning_status,
                )
            )
        return InventoryPlanningResponse(
            generated_at=datetime.now(UTC),
            policy=InventoryPolicy(),
            items=items,
        )
