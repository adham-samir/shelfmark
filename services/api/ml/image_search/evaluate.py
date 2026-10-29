"""Reproduce the synthetic SF-03 PyTorch retrieval evaluation."""

from argparse import ArgumentParser
import json
from pathlib import Path

from PIL import Image

from smart_ecommerce_api.search import PyTorchImageRetriever


def evaluate(artifact_path: Path, evaluation_path: Path) -> None:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    retriever = PyTorchImageRetriever(str(artifact_path))
    cases = 0
    top_one = 0
    recalled_at_three = 0
    for prototype in artifact["prototypes"]:
        expected = prototype["product_id"]
        for delta in (-8, 0, 8):
            rgb = tuple(max(0, min(255, value + delta)) for value in prototype["rgb"])
            ranking = [str(item[0]) for item in retriever.rank(Image.new("RGB", (64, 64), rgb))]
            cases += 1
            top_one += ranking[0] == expected
            recalled_at_three += expected in ranking[:3]
    metrics = {
        "top_1_accuracy": round(top_one / cases, 6),
        "recall_at_3": round(recalled_at_three / cases, 6),
        "evaluation_cases": cases,
    }
    if metrics["recall_at_3"] < 0.80:
        raise RuntimeError("image retrieval recall@3 is below the agreed synthetic target")
    evaluation_path.write_text(
        json.dumps(
            {
                "evaluation_id": artifact["evaluation_id"],
                "model_version_id": artifact["model_version_id"],
                "dataset_snapshot_id": artifact["dataset_snapshot_id"],
                "split_strategy": "three deterministic color perturbations around each of four catalog prototypes",
                "metrics": metrics,
                "limitations": "Synthetic color swatches validate pipeline behavior only; no production visual-relevance claim is made.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metrics, sort_keys=True))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path, required=True)
    arguments = parser.parse_args()
    evaluate(arguments.artifact, arguments.evaluation)
