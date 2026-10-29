from __future__ import annotations

from datetime import date, timedelta
import importlib.util
import json
from pathlib import Path
from uuid import UUID

import joblib
import pytest

from smart_ecommerce_api.errors import DependencyUnavailable
from smart_ecommerce_api.forecasting import (
    InventoryService,
    InventorySnapshot,
    SandboxSupplierSimulator,
    StoredReorder,
)


ROOT = Path(__file__).parents[1]
ARTIFACT = ROOT / "artifacts/forecast.joblib"
SPEC = json.loads((ROOT / "data/forecast.synthetic.json").read_text())
AS_OF = date.fromisoformat(SPEC["as_of_date"])


def load_trainer():
    path = ROOT / "ml/forecast/train.py"
    spec = importlib.util.spec_from_file_location("forecast_trainer", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def quantity(base: int, index: int, current: date) -> float:
    return float(
        base
        + (2 if current.weekday() in (4, 5) else 0)
        + index // 60
        + (1 if index % 3 == 0 else 0)
    )


def history(base: int) -> list[float]:
    start = AS_OF - timedelta(days=SPEC["days"])
    return [quantity(base, index, start + timedelta(days=index)) for index in range(SPEC["days"])]


class FakeStore:
    def __init__(self, snapshots, histories):
        self._snapshots = snapshots
        self.histories = histories
        self.forecasts = []
        self.reorders = {}
        self.marks = []
        self.evidence = None

    def snapshots(self):
        adjusted = []
        for item in self._snapshots:
            pending = sum(
                record["quantity"]
                for record in self.reorders.values()
                if record["product_id"] == item.product_id
                and record["status"] in {"created", "dispatched", "acknowledged"}
            )
            adjusted.append(
                InventorySnapshot(
                    item.product_id, item.on_hand, item.reserved, item.available, pending
                )
            )
        return adjusted

    def demand_history(self, product_id, as_of, days=210):
        from smart_ecommerce_api.forecasting import DemandHistory

        values = self.histories.get(product_id, [])
        return DemandHistory(values=list(values), observed_days=len(values))

    def record_evidence(self, artifact):
        self.evidence = artifact

    def save_forecast(self, **values):
        forecast_id = UUID(f"b0000000-0000-4000-8000-{len(self.forecasts) + 1:012d}")
        self.forecasts.append({**values, "forecast_id": forecast_id})
        return forecast_id

    def begin_reorder(self, **values):
        key = values["idempotency_key"]
        if key in self.reorders:
            record = self.reorders[key]
            if record["status"] == "failed":
                record["status"] = "created"
            return StoredReorder(record["reorder_id"], record["status"], False)
        reorder_id = UUID(f"c0000000-0000-4000-8000-{len(self.reorders) + 1:012d}")
        self.reorders[key] = {
            **values,
            "reorder_id": reorder_id,
            "status": "created",
        }
        return StoredReorder(reorder_id, "created", True)

    def mark_reorder(self, reorder_id, *, status, supplier_reference, status_detail):
        record = next(value for value in self.reorders.values() if value["reorder_id"] == reorder_id)
        record["status"] = status
        record["supplier_reference"] = supplier_reference
        record["status_detail"] = status_detail
        self.marks.append((reorder_id, status))


def test_artifact_uses_chronological_holdout_and_meets_baseline() -> None:
    artifact = joblib.load(ARTIFACT)
    assert artifact["forecast_horizon_days"] == 14
    assert artifact["minimum_history_days"] == 28
    assert artifact["metrics"]["holdout_days"] == 28
    assert artifact["metrics"]["mape_non_zero"] <= 0.25
    assert {"lag_1", "lag_7", "lag_14", "rolling_mean_7", "rolling_mean_28"}.issubset(
        artifact["feature_names"]
    )


def test_supervised_features_never_read_target_or_future_values() -> None:
    trainer = load_trainer()
    product_id = SPEC["products"][0]["product_id"]
    rows = trainer.expand_dataset({**SPEC, "products": [SPEC["products"][0]]})[product_id]
    baseline, _, dates = trainer.supervised_rows({product_id: rows}, [product_id])
    changed = list(rows)
    target_index = 75
    changed[target_index] = (changed[target_index][0], 99_999.0)
    changed[target_index + 1 :] = [
        (current, 88_888.0) for current, _ in changed[target_index + 1 :]
    ]
    modified, _, modified_dates = trainer.supervised_rows({product_id: changed}, [product_id])
    feature_row = target_index - 28
    assert dates[feature_row] == modified_dates[feature_row]
    assert baseline[feature_row].tolist() == modified[feature_row].tolist()


def test_model_configuration_and_predictions_are_deterministic() -> None:
    artifact = joblib.load(ARTIFACT)
    model = artifact["model"]
    history_values = history(SPEC["products"][0]["base_demand"])
    vector = InventoryService._feature_vector(
        history_values, AS_OF, 0, len(artifact["product_ids"])
    )
    assert model.random_state == 42
    assert float(model.predict([vector])[0]) == float(model.predict([vector])[0])


def test_missing_model_artifact_is_reported_as_dependency_failure(tmp_path: Path) -> None:
    service = InventoryService(FakeStore([], {}), str(tmp_path / "missing.joblib"), SandboxSupplierSimulator())
    with pytest.raises(DependencyUnavailable, match="forecast model artifact"):
        service.run(AS_OF)


def test_low_stock_reorders_once_and_pending_supply_prevents_duplicate() -> None:
    product = UUID(SPEC["products"][0]["product_id"])
    store = FakeStore(
        [InventorySnapshot(product, 12, 2, 10, 0)],
        {product: history(SPEC["products"][0]["base_demand"])},
    )
    service = InventoryService(store, str(ARTIFACT), SandboxSupplierSimulator())
    first = service.run(AS_OF)
    assert first.reorders_created == 1
    assert first.items[0].reorder_quantity > 0
    assert len(store.reorders) == 1
    assert next(iter(store.reorders.values()))["status"] == "acknowledged"
    assert store.forecasts[0]["horizon_end"] - store.forecasts[0]["horizon_start"] == timedelta(days=13)

    second = service.run(AS_OF)
    assert second.reorders_created == 0
    assert second.adequate_stock == 1
    assert len(store.reorders) == 1


def test_adequate_stock_does_not_reorder() -> None:
    product = UUID(SPEC["products"][8]["product_id"])
    store = FakeStore(
        [InventorySnapshot(product, 500, 0, 500, 0)],
        {product: history(SPEC["products"][8]["base_demand"])},
    )
    result = InventoryService(store, str(ARTIFACT), SandboxSupplierSimulator()).run(AS_OF)
    assert result.adequate_stock == 1
    assert result.reorders_created == 0
    assert not store.reorders


def test_supplier_failure_is_persisted_and_recovery_reuses_record() -> None:
    product = UUID(SPEC["products"][0]["product_id"])
    store = FakeStore(
        [InventorySnapshot(product, 2, 0, 2, 0)],
        {product: history(SPEC["products"][0]["base_demand"])},
    )
    failing = InventoryService(store, str(ARTIFACT), SandboxSupplierSimulator(fail=True))
    with pytest.raises(DependencyUnavailable, match="failed records"):
        failing.run(AS_OF)
    assert len(store.reorders) == 1
    assert next(iter(store.reorders.values()))["status"] == "failed"

    recovered = InventoryService(store, str(ARTIFACT), SandboxSupplierSimulator())
    result = recovered.run(AS_OF)
    assert result.reorders_reused == 1
    assert len(store.reorders) == 1
    assert next(iter(store.reorders.values()))["status"] == "acknowledged"


def test_insufficient_history_is_visible_without_reorder() -> None:
    product = UUID(SPEC["products"][0]["product_id"])
    store = FakeStore(
        [InventorySnapshot(product, 2, 0, 2, 0)],
        {product: history(SPEC["products"][0]["base_demand"])[:20]},
    )
    result = InventoryService(store, str(ARTIFACT), SandboxSupplierSimulator()).run(AS_OF)
    assert result.insufficient_history == 1
    assert result.items[0].outcome == "insufficient_history"
    assert not store.reorders
