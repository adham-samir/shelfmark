"""Generate the deterministic synthetic fraud dataset for BO-04.

The process is explicitly synthetic: it encodes the risk signals the checkout
service can actually observe. Its labels prove pipeline and policy behavior;
they do not establish real-world fraud-detection quality.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid5, NAMESPACE_URL

import numpy as np

SEED = 42
TRANSACTIONS = 3_000
CUSTOMERS = 600
DATASET_SNAPSHOT = "fraud-synthetic-2026-10-27-v1"
LIMITATIONS = (
    "Synthetic seeded generator over checkout-observable signals. Labels come "
    "from a documented probabilistic process, not real payment data, so the "
    "evaluation proves pipeline, threshold, and policy behavior only. Device "
    "fingerprints and card-network signals are unavailable; the model must be "
    "retrained and re-evaluated before any production use."
)
PROCESS = (
    "Base logit -7.0; amount spike at or above 3x the customer norm, new shipping "
    "address, token reuse, 24h order velocity, prior failed attempts, overnight "
    "orders, high absolute amount, and a small first-order adjustment. Label is "
    "a Bernoulli draw at the resulting probability."
)


def customer_id(index: int) -> str:
    return str(UUID(f"80000000-0000-4000-8000-{index:012d}"))


def main() -> None:
    rng = np.random.default_rng(SEED)
    root = Path(__file__).resolve().parents[2]
    output = root / "data/fraud.synthetic.json"

    profiles = []
    for index in range(CUSTOMERS):
        has_history = bool(rng.random() > 0.15)
        average = float(np.clip(rng.lognormal(8.5, 0.45), 900, 30000)) if has_history else None
        profiles.append(
            {
                "average": average,
                "age_days": int(rng.integers(0, 900)),
                "failed": int(rng.choice([0, 0, 0, 1, 1, 2, 3, 4])),
                "prior_orders": int(rng.integers(1, 40)) if has_history else 0,
            }
        )

    transactions = []
    positives = 0
    for index in range(TRANSACTIONS):
        customer_index = int(rng.integers(0, CUSTOMERS))
        profile = profiles[customer_index]
        average = profile["average"]
        if average is None:
            amount = float(np.clip(rng.lognormal(8.6, 0.55), 300, 40000))
            amount_ratio = 1.0
        else:
            amount = float(np.clip(average * rng.lognormal(0, 0.35), 200, 60000))
            if rng.random() < 0.10:
                amount = float(np.clip(amount * rng.uniform(3, 8), 200, 90000))
            amount_ratio = amount / average

        overnight = bool(rng.random() < 0.06)
        order_hour = int(rng.integers(0, 6)) if overnight else int(rng.integers(9, 23))
        weekday = int(rng.integers(0, 7))
        prior_orders = profile["prior_orders"]
        orders_last_24h = int(
            rng.choice([0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 2, 3, 4, 5])
        )
        prior_failed = profile["failed"]
        new_address = bool(prior_orders > 0 and rng.random() < 0.12)
        token_reuse = int(rng.choice([0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 2, 3]))
        item_count = int(rng.integers(1, 6))

        logit = -7.0
        logit += 3.5 if amount_ratio >= 3 else 0.0
        logit += 2.8 if new_address else 0.0
        logit += 1.3 * min(token_reuse, 3)
        logit += 1.1 * min(orders_last_24h, 4)
        logit += 0.9 * min(prior_failed, 4)
        logit += 1.3 if order_hour < 6 else 0.0
        logit += 1.1 if amount > 20000 else 0.0
        logit += -0.5 if prior_orders == 0 else 0.0
        probability = 1 / (1 + math.exp(-logit))
        label = int(rng.random() < probability)
        positives += label

        transactions.append(
            {
                "transaction_id": str(
                    uuid5(NAMESPACE_URL, f"{DATASET_SNAPSHOT}:{index}")
                ),
                "customer_id": customer_id(customer_index),
                "label": label,
                "context": {
                    "customer_id": customer_id(customer_index),
                    "amount": f"{amount:.2f}",
                    "item_count": item_count,
                    "order_hour": order_hour,
                    "weekday": weekday,
                    "customer_age_days": profile["age_days"],
                    "prior_orders": prior_orders,
                    "average_order_value": f"{average:.2f}" if average is not None else None,
                    "orders_last_24h": orders_last_24h,
                    "prior_failed_orders": prior_failed,
                    "new_address": new_address,
                    "token_reuse": token_reuse,
                },
            }
        )

    payload = {
        "dataset_snapshot_id": DATASET_SNAPSHOT,
        "generated_at": datetime.now(UTC).isoformat(),
        "seed": SEED,
        "transactions": TRANSACTIONS,
        "positives": positives,
        "positive_rate": round(positives / TRANSACTIONS, 6),
        "process": PROCESS,
        "limitations": LIMITATIONS,
        "rows": transactions,
    }
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(
        f"Wrote {len(transactions)} transactions "
        f"({positives} positives, {positives / TRANSACTIONS:.2%}) to {output}"
    )


if __name__ == "__main__":
    main()