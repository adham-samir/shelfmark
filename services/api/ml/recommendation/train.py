"""Train and evaluate the reproducible SF-01 hybrid recommendation baseline."""

from argparse import ArgumentParser
from datetime import UTC, datetime
import json
from math import log2
from pathlib import Path
from uuid import UUID

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


MODEL_VERSION_ID = "a1000000-0000-4000-8000-000000000001"
EVALUATION_ID = "a2000000-0000-4000-8000-000000000001"
WEIGHTS = {"view": 1.0, "search_click": 2.0, "compare": 3.0, "add_to_cart": 4.0, "purchase": 5.0}


def normalized(values: np.ndarray) -> np.ndarray:
    maximum = float(values.max(initial=0))
    return values / maximum if maximum > 0 else values


def rank_scores(history, product_ids, collaborative, content, popularity):
    index = {product_id: position for position, product_id in enumerate(product_ids)}
    vector = np.zeros(len(product_ids), dtype=float)
    for interaction in history:
        position = index.get(interaction["product_id"])
        if position is not None:
            vector[position] += WEIGHTS[interaction["event_type"]]
    collaborative_scores = normalized(vector @ collaborative)
    content_scores = normalized(vector @ content)
    combined = 0.6 * collaborative_scores + 0.4 * content_scores + 0.01 * normalized(popularity)
    for interaction in history:
        if interaction["product_id"] in index:
            combined[index[interaction["product_id"]]] = -1
    return combined


def ndcg_for_target(ranking, target):
    rank = ranking.index(target) + 1
    return 1.0 / log2(rank + 1)


def train(dataset_path: Path, artifact_path: Path, evaluation_path: Path) -> None:
    dataset = json.loads(dataset_path.read_text())
    product_ids = [item["product_id"] for item in dataset["products"]]
    if len(product_ids) != len(set(product_ids)) or any(str(UUID(value)) != value for value in product_ids):
        raise ValueError("product IDs must be unique canonical UUIDs")
    index = {product_id: position for position, product_id in enumerate(product_ids)}
    users = sorted({item["user_id"] for item in dataset["training_interactions"]})
    user_index = {user_id: position for position, user_id in enumerate(users)}
    matrix = np.zeros((len(product_ids), len(users)), dtype=float)
    popularity = np.zeros(len(product_ids), dtype=float)
    signal_types = set()
    for interaction in dataset["training_interactions"]:
        weight = WEIGHTS[interaction["event_type"]]
        matrix[index[interaction["product_id"]], user_index[interaction["user_id"]]] += weight
        popularity[index[interaction["product_id"]]] += weight
        signal_types.add(interaction["event_type"])
    if "purchase" not in signal_types or not signal_types.intersection({"view", "search_click", "compare", "add_to_cart"}):
        raise ValueError("training data must contain both purchase and browsing signals")

    collaborative = cosine_similarity(matrix)
    tfidf = TfidfVectorizer(lowercase=True, ngram_range=(1, 2))
    content_matrix = tfidf.fit_transform([item["text"] for item in dataset["products"]])
    content = cosine_similarity(content_matrix)

    hybrid_values, popularity_values = [], []
    popularity_order = [product_ids[i] for i in np.argsort(-popularity, kind="stable")]
    for case in dataset["evaluation_cases"]:
        scores = rank_scores(case["history"], product_ids, collaborative, content, popularity)
        hybrid_order = [product_ids[i] for i in np.argsort(-scores, kind="stable")]
        hybrid_values.append(ndcg_for_target(hybrid_order, case["target_product_id"]))
        seen_items = {item["product_id"] for item in case["history"]}
        baseline_order = [item for item in popularity_order if item not in seen_items]
        popularity_values.append(ndcg_for_target(baseline_order, case["target_product_id"]))

    hybrid_ndcg = float(np.mean(hybrid_values))
    popularity_ndcg = float(np.mean(popularity_values))
    lift = (hybrid_ndcg / popularity_ndcg - 1.0) if popularity_ndcg else 0.0
    metrics = {
        "hybrid_ndcg_at_10": round(hybrid_ndcg, 6),
        "popularity_ndcg_at_10": round(popularity_ndcg, 6),
        "relative_lift": round(lift, 6),
        "evaluation_cases": len(dataset["evaluation_cases"]),
    }
    artifact = {
        "model_version_id": MODEL_VERSION_ID,
        "evaluation_id": EVALUATION_ID,
        "version_label": "hybrid-recommendation-v1",
        "dataset_snapshot_id": dataset["dataset_snapshot_id"],
        "product_ids": product_ids,
        "collaborative_similarity": collaborative,
        "content_similarity": content,
        "popularity": popularity,
        "weights": WEIGHTS,
        "metrics": metrics,
        "trained_at": datetime.now(UTC).isoformat(),
    }
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    evaluation_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, artifact_path)
    evaluation_path.write_text(json.dumps({
        "evaluation_id": EVALUATION_ID,
        "model_version_id": MODEL_VERSION_ID,
        "dataset_snapshot_id": dataset["dataset_snapshot_id"],
        "split_strategy": "fixed user holdout cases separate from collaborative-training users",
        "metrics": metrics,
        "limitations": "Synthetic four-product fixture validates pipeline behavior only; it does not establish production ranking quality.",
    }, indent=2) + "\n")
    if lift < 0.10:
        raise RuntimeError(f"hybrid lift {lift:.3f} is below the accepted 0.10 fixture target")
    print(json.dumps(metrics, sort_keys=True))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path, required=True)
    arguments = parser.parse_args()
    train(arguments.dataset, arguments.artifact, arguments.evaluation)
