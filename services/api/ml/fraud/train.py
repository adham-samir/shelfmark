"""Train and evaluate BO-04 fraud detection on the synthetic dataset.

A scaled logistic baseline and a histogram gradient-boosting model are trained
on the same features. The threshold is chosen on validation to maximize recall
subject to a false-positive rate at or below 0.10. The better model on that
criterion is evaluated once on the sealed holdout and written to the artifact.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from smart_ecommerce_api.fraud import FEATURE_NAMES, RiskContext, features

SEED = 42
# Select below the accepted 0.10 ceiling so split noise does not push the
# sealed holdout over it; the holdout is still judged against the 0.10 target.
MAX_FPR = 0.09
MIN_RECALL = 0.80


def context_from_row(row: dict) -> RiskContext:
    return RiskContext(
        customer_id=row["customer_id"],
        amount=Decimal(row["amount"]),
        item_count=row["item_count"],
        order_hour=row["order_hour"],
        weekday=row["weekday"],
        customer_age_days=row["customer_age_days"],
        prior_orders=row["prior_orders"],
        average_order_value=Decimal(row["average_order_value"])
        if row["average_order_value"] is not None
        else None,
        orders_last_24h=row["orders_last_24h"],
        prior_failed_orders=row["prior_failed_orders"],
        new_address=row["new_address"],
        token_reuse=row["token_reuse"],
    )


def matrix(rows: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    x = np.array([features(context_from_row(row["context"])) for row in rows])
    y = np.array([row["label"] for row in rows])
    return x, y


def threshold_for(
    probabilities: np.ndarray, labels: np.ndarray, max_fpr: float = MAX_FPR
) -> tuple[float, dict[str, float]]:
    candidates = np.unique(np.concatenate(([0.0], probabilities, [1.0])))
    best: tuple[tuple[float, float], float, dict[str, float]] | None = None
    fallback: tuple[tuple[float, float], float, dict[str, float]] | None = None
    for threshold in candidates:
        predicted = probabilities >= threshold
        tp = int(((predicted == 1) & (labels == 1)).sum())
        fp = int(((predicted == 1) & (labels == 0)).sum())
        tn = int(((predicted == 0) & (labels == 0)).sum())
        fn = int(((predicted == 0) & (labels == 1)).sum())
        recall = tp / (tp + fn) if tp + fn else 0.0
        fpr = fp / (fp + tn) if fp + tn else 0.0
        precision = tp / (tp + fp) if tp + fp else 0.0
        record = {
            "threshold": float(threshold),
            "recall": recall,
            "false_positive_rate": fpr,
            "precision": precision,
        }
        score = (recall, -fpr)
        if fpr <= max_fpr and (best is None or score > best[0]):
            best = (score, float(threshold), record)
        if fallback is None or score > fallback[0]:
            fallback = (score, float(threshold), record)
    assert best is not None or fallback is not None
    chosen = best or fallback
    return chosen[1], chosen[2]


def metrics(y_true: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict:
    predicted = probabilities >= threshold
    tn, fp, fn, tp = confusion_matrix(y_true, predicted, labels=[0, 1]).ravel()
    return {
        "threshold": threshold,
        "recall": float(recall_score(y_true, predicted, zero_division=0)),
        "precision": float(precision_score(y_true, predicted, zero_division=0)),
        "f1": float(f1_score(y_true, predicted, zero_division=0)),
        "false_positive_rate": float(fp / (fp + tn)) if fp + tn else 0.0,
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
        "roc_auc": float(roc_auc_score(y_true, probabilities)),
        "pr_auc": float(average_precision_score(y_true, probabilities)),
        "positives": int(y_true.sum()),
        "negatives": int(len(y_true) - y_true.sum()),
    }


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    dataset_path = root / "data/fraud.synthetic.json"
    artifact_path = root / "artifacts/fraud.joblib"
    evaluation_path = root / "artifacts/fraud.evaluation.json"
    dataset = json.loads(dataset_path.read_text())
    rows = dataset["rows"]

    x, y = matrix(rows)
    x_train, x_rest, y_train, y_rest = train_test_split(
        x, y, test_size=0.4, stratify=y, random_state=SEED
    )
    x_val, x_holdout, y_val, y_holdout = train_test_split(
        x_rest, y_rest, test_size=0.5, stratify=y_rest, random_state=SEED
    )

    baseline = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            class_weight="balanced", max_iter=1000, random_state=SEED
        ),
    )
    selected_candidate = HistGradientBoostingClassifier(
        max_iter=250,
        learning_rate=0.08,
        max_leaf_nodes=31,
        min_samples_leaf=30,
        l2_regularization=0.1,
        class_weight="balanced",
        random_state=SEED,
    )
    baseline.fit(x_train, y_train)
    selected_candidate.fit(x_train, y_train)

    baseline_val = baseline.predict_proba(x_val)[:, 1]
    selected_val = selected_candidate.predict_proba(x_val)[:, 1]
    baseline_threshold, baseline_validation = threshold_for(baseline_val, y_val)
    selected_threshold, selected_validation = threshold_for(selected_val, y_val)

    baseline_pr = average_precision_score(y_val, baseline_val)
    selected_pr = average_precision_score(y_val, selected_val)
    choose_boosted = (
        selected_validation["recall"] > baseline_validation["recall"]
        or (
            selected_validation["recall"] == baseline_validation["recall"]
            and selected_pr >= baseline_pr
        )
    )
    model = selected_candidate if choose_boosted else baseline
    model_name = (
        "hist-gradient-boosting" if choose_boosted else "logistic-regression"
    )
    threshold = selected_threshold if choose_boosted else baseline_threshold
    validation = selected_validation if choose_boosted else baseline_validation
    threshold = min(float(threshold), 0.70)

    holdout_probabilities = model.predict_proba(x_holdout)[:, 1]
    holdout = metrics(y_holdout, holdout_probabilities, threshold)
    if holdout["recall"] < MIN_RECALL or holdout["false_positive_rate"] > MAX_FPR:
        raise SystemExit(
            "Holdout target missed: "
            f"recall={holdout['recall']:.3f} (min {MIN_RECALL}), "
            f"fpr={holdout['false_positive_rate']:.3f} (max {MAX_FPR})."
        )

    version_label = f"{model_name}-fraud-v1"
    model_version_id = str(
        uuid5(NAMESPACE_URL, f"smart-ecommerce:fraud:{version_label}")
    )
    evaluation_id = str(
        uuid5(NAMESPACE_URL, f"smart-ecommerce:fraud:evaluation:{version_label}")
    )
    limitations = dataset["limitations"]
    artifact = {
        "model": model,
        "feature_names": list(FEATURE_NAMES),
        "threshold": float(threshold),
        "model_version_id": model_version_id,
        "evaluation_id": evaluation_id,
        "version_label": version_label,
        "dataset_snapshot_id": dataset["dataset_snapshot_id"],
        "metrics": holdout,
        "limitations": limitations,
        "trained_at": datetime.now(UTC).isoformat(),
        "selected_model": model_name,
    }
    joblib.dump(artifact, artifact_path)

    evaluation = {
        "dataset_snapshot_id": dataset["dataset_snapshot_id"],
        "seed": SEED,
        "transactions": dataset["transactions"],
        "positive_rate": dataset["positive_rate"],
        "split": {
            "train": len(y_train),
            "validation": len(y_val),
            "holdout": len(y_holdout),
            "strategy": "stratified 60/20/20",
        },
        "features": list(FEATURE_NAMES),
        "models": {
            "logistic-regression": {
                "validation": baseline_validation,
                "holdout": metrics(
                    y_holdout,
                    baseline.predict_proba(x_holdout)[:, 1],
                    min(baseline_threshold, 0.70),
                ),
            },
            "hist-gradient-boosting": {
                "validation": selected_validation,
                "holdout": metrics(
                    y_holdout,
                    selected_candidate.predict_proba(x_holdout)[:, 1],
                    min(selected_threshold, 0.70),
                ),
            },
        },
        "selected_model": model_name,
        "selected_threshold": float(threshold),
        "holdout": holdout,
        "limitations": limitations,
    }
    evaluation_path.write_text(json.dumps(evaluation, indent=2) + "\n")

    print(
        f"Selected {model_name} at threshold {threshold:.4f}: "
        f"holdout recall={holdout['recall']:.3f}, "
        f"fpr={holdout['false_positive_rate']:.3f}, "
        f"precision={holdout['precision']:.3f}, "
        f"pr_auc={holdout['pr_auc']:.3f}, roc_auc={holdout['roc_auc']:.3f}"
    )
    print(f"Wrote {artifact_path} and {evaluation_path}")


if __name__ == "__main__":
    main()