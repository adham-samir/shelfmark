"""Train the deterministic BO-01 synthetic demand baseline.

The dataset specification expands into chronological daily demand. Every feature
row is built only from observations before its target date; the final 28 days are
held out by date. The resulting artifact is intentionally a project baseline,
not evidence of production forecast quality.
"""

from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
from typing import Any
from uuid import UUID

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor


ROOT = Path(__file__).parents[2]
DATA_PATH = ROOT / "data/forecast.synthetic.json"
ARTIFACT_PATH = ROOT / "artifacts/forecast.joblib"
EVALUATION_PATH = ROOT / "artifacts/forecast.evaluation.json"
MODEL_VERSION_ID = UUID("a0000000-0000-4000-8000-000000000001")
EVALUATION_ID = UUID("a1000000-0000-4000-8000-000000000001")
VERSION_LABEL = "random-forest-lag-calendar-v1"


def synthetic_quantity(base: int, day_index: int, current: date) -> int:
    weekend_uplift = 2 if current.weekday() in (4, 5) else 0
    trend = day_index // 60
    pulse = 1 if day_index % 3 == 0 else 0
    return base + weekend_uplift + trend + pulse


def expand_dataset(spec: dict[str, Any]) -> dict[str, list[tuple[date, float]]]:
    as_of = date.fromisoformat(spec["as_of_date"])
    days = int(spec["days"])
    start = as_of - timedelta(days=days)
    return {
        product["product_id"]: [
            (
                start + timedelta(days=index),
                float(synthetic_quantity(product["base_demand"], index, start + timedelta(days=index))),
            )
            for index in range(days)
        ]
        for product in spec["products"]
    }


def feature_vector(
    history: list[float],
    target_date: date,
    product_index: int,
    product_count: int,
) -> list[float]:
    if len(history) < 28:
        raise ValueError("At least 28 prior daily observations are required.")
    one_hot = [1.0 if index == product_index else 0.0 for index in range(product_count)]
    angle = 2 * np.pi * target_date.weekday() / 7
    return [
        history[-1],
        history[-7],
        history[-14],
        float(np.mean(history[-7:])),
        float(np.mean(history[-28:])),
        float(np.sin(angle)),
        float(np.cos(angle)),
        *one_hot,
    ]


def supervised_rows(
    series: dict[str, list[tuple[date, float]]],
    product_ids: list[str],
) -> tuple[np.ndarray, np.ndarray, list[date]]:
    features: list[list[float]] = []
    targets: list[float] = []
    dates: list[date] = []
    for product_index, product_id in enumerate(product_ids):
        rows = series[product_id]
        values = [value for _, value in rows]
        for index in range(28, len(rows)):
            target_date, target = rows[index]
            features.append(
                feature_vector(values[:index], target_date, product_index, len(product_ids))
            )
            targets.append(target)
            dates.append(target_date)
    return np.asarray(features), np.asarray(targets), dates


def train() -> dict[str, Any]:
    spec = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    series = expand_dataset(spec)
    product_ids = [product["product_id"] for product in spec["products"]]
    features, targets, dates = supervised_rows(series, product_ids)
    holdout_start = date.fromisoformat(spec["as_of_date"]) - timedelta(days=28)
    training_mask = np.asarray([item < holdout_start for item in dates])
    holdout_mask = ~training_mask

    model = RandomForestRegressor(
        n_estimators=160,
        max_depth=10,
        min_samples_leaf=1,
        random_state=42,
        n_jobs=1,
    )
    model.fit(features[training_mask], targets[training_mask])
    predictions = np.maximum(0, model.predict(features[holdout_mask]))
    actual = targets[holdout_mask]
    mape = float(np.mean(np.abs((actual - predictions) / actual)))
    mae = float(np.mean(np.abs(actual - predictions)))

    metrics = {
        "mape_non_zero": round(mape, 6),
        "mae": round(mae, 6),
        "holdout_days": 28,
        "holdout_rows": int(holdout_mask.sum()),
        "training_rows": int(training_mask.sum()),
    }
    artifact = {
        "model_version_id": str(MODEL_VERSION_ID),
        "evaluation_id": str(EVALUATION_ID),
        "version_label": VERSION_LABEL,
        "dataset_snapshot_id": spec["dataset_snapshot_id"],
        "framework": "scikit-learn",
        "product_ids": product_ids,
        "minimum_history_days": 28,
        "forecast_horizon_days": 14,
        "feature_names": [
            "lag_1", "lag_7", "lag_14", "rolling_mean_7", "rolling_mean_28",
            "weekday_sin", "weekday_cos", *[f"product_{index + 1}" for index in range(len(product_ids))],
        ],
        "metrics": metrics,
        "limitations": spec["limitation"],
        "model": model,
    }
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, ARTIFACT_PATH)
    EVALUATION_PATH.write_text(
        json.dumps(
            {
                "model_version_id": str(MODEL_VERSION_ID),
                "evaluation_id": str(EVALUATION_ID),
                "version_label": VERSION_LABEL,
                "dataset_snapshot_id": spec["dataset_snapshot_id"],
                "split_strategy": "final 28 calendar days held out; lag and rolling features use prior observations only",
                "metrics": metrics,
                "limitations": spec["limitation"],
            },
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )
    return artifact


if __name__ == "__main__":
    result = train()
    print(json.dumps(result["metrics"], indent=2))
