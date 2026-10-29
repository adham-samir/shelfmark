"""Black-box Stage 3 commerce flow against the Docker Compose stack."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import BytesIO
import os
from uuid import uuid4

import httpx
from PIL import Image


BASE_URL = os.getenv("SMART_ECOMMERCE_TEST_BASE_URL", "http://127.0.0.1:8000")
PRODUCT_ONE = "10000000-0000-4000-8000-000000000001"
PRODUCT_TWO = "10000000-0000-4000-8000-000000000002"
SHIPPING = {
    "recipient_name": "Synthetic Customer",
    "phone": "+201000000000",
    "city": "Cairo",
    "address_line": "12 Synthetic Test Street, Apt 4",
}


def auth(subject: str) -> dict[str, str]:
    return {"authorization": f"Bearer {subject}"}


def assert_error(response: httpx.Response, status: int, code: str) -> None:
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code


def png(rgb: tuple[int, int, int]) -> bytes:
    output = BytesIO()
    Image.new("RGB", (64, 64), rgb).save(output, format="PNG")
    return output.getvalue()


def test_customer_checkout_risk_review_and_isolation() -> None:
    customer = auth("synthetic-customer-subject")
    other_customer = auth("synthetic-other-customer-subject")
    operator = auth("synthetic-operator-subject")

    with httpx.Client(base_url=BASE_URL, timeout=10) as api:
        assert api.get("/health/ready").json() == {"status": "ready"}

        cart = api.put(
            "/v1/cart/items",
            headers=customer,
            json={"product_id": PRODUCT_ONE, "quantity": 2},
        )
        assert cart.status_code == 200, cart.text
        assert cart.json()["subtotal"] == "17800"

        event_id = str(uuid4())
        event = api.post(
            "/v1/events/browsing",
            headers=customer,
            json={
                "event_id": event_id,
                "session_id": str(uuid4()),
                "product_id": PRODUCT_ONE,
                "event_type": "add_to_cart",
                "occurred_at": datetime.now(UTC).isoformat(),
                "context": {"test": "commerce-flow"},
            },
        )
        assert event.status_code == 202, event.text

        safe_payload = {
            "payment_token": "tok_sandbox_safe-flow",
            "idempotency_key": f"safe-{uuid4()}",
            "shipping": SHIPPING,
        }
        safe = api.post("/v1/checkout", headers=customer, json=safe_payload)
        assert safe.status_code == 202, safe.text
        assert safe.json()["status"] == "confirmed"
        order_id = safe.json()["order_id"]

        repeated = api.post("/v1/checkout", headers=customer, json=safe_payload)
        assert repeated.status_code == 202, repeated.text
        assert repeated.json() == safe.json()

        order = api.get(f"/v1/orders/{order_id}", headers=customer)
        assert order.status_code == 200, order.text
        assert order.json()["items"][0]["unit_price"] == "8900"
        assert api.get(
            f"/v1/orders/{order_id}/shipment", headers=customer
        ).status_code == 200
        assert_error(
            api.get(f"/v1/orders/{order_id}", headers=other_customer),
            404,
            "not_found",
        )

        recommendations = api.get("/v1/recommendations?limit=3", headers=customer)
        assert recommendations.status_code == 200, recommendations.text
        recommendation_data = recommendations.json()
        assert recommendation_data["strategy"] == "hybrid"
        assert recommendation_data["basis"]["browsing_events"] >= 1
        assert recommendation_data["basis"]["purchased_items"] >= 1
        assert PRODUCT_ONE not in recommendation_data["items"]

        facets = api.get("/v1/products/facets?q=phone")
        assert facets.status_code == 200, facets.text
        assert facets.json()["total"] == 5
        assert any(item["key"] == "storage" for item in facets.json()["facets"])

        image_search = api.post(
            "/v1/search/image?category=phones&filter=storage%3A128%20GB",
            files={"image": ("phone.png", png((40, 100, 220)), "image/png")},
        )
        assert image_search.status_code == 200, image_search.text
        assert image_search.json()["items"][0]["product"]["product_id"] == PRODUCT_ONE
        assert image_search.json()["model_version"] == "pytorch-color-retrieval-v1"

        assert_error(
            api.post(
                "/v1/search/voice?locale=en",
                files={"audio": ("query.wav", b"synthetic audio", "audio/wav")},
            ),
            503,
            "dependency_unavailable",
        )
        assert_error(
            api.post(
                "/v1/assistant/messages",
                headers=customer,
                json={
                    "message": "Where is my shipment?",
                    "locale": "en",
                    "order_id": order_id,
                },
            ),
            503,
            "dependency_unavailable",
        )

        api.put(
            "/v1/cart/items",
            headers=customer,
            json={"product_id": PRODUCT_TWO, "quantity": 1},
        ).raise_for_status()
        review = api.post(
            "/v1/checkout",
            headers=customer,
            json={
                "payment_token": "tok_sandbox_risk-high-flow",
                "idempotency_key": f"review-{uuid4()}",
                "shipping": SHIPPING,
            },
        )
        assert review.status_code == 202, review.text
        assert review.json()["status"] == "review"
        review_order_id = review.json()["order_id"]
        assert_error(
            api.get(f"/v1/orders/{review_order_id}/shipment", headers=customer),
            404,
            "not_found",
        )

        queue = api.get("/v1/backoffice/risk", headers=operator)
        assert queue.status_code == 200, queue.text
        assessment = next(
            item for item in queue.json() if item["order_id"] == review_order_id
        )
        assert assessment["outcome"] == "review"
        assert assessment["reasons"] == ["sandbox_high_risk"]
        assert assessment["model_version"] is None
        assert_error(
            api.post(
                f"/v1/backoffice/risk/{assessment['assessment_id']}/decision",
                headers=customer,
                json={"decision": "allow"},
            ),
            403,
            "forbidden",
        )
        allowed = api.post(
            f"/v1/backoffice/risk/{assessment['assessment_id']}/decision",
            headers=operator,
            json={"decision": "allow"},
        )
        assert allowed.status_code == 200, allowed.text
        assert allowed.json()["status"] == "confirmed"
        assert api.get(
            f"/v1/orders/{review_order_id}/shipment", headers=customer
        ).status_code == 200

        api.put(
            "/v1/cart/items",
            headers=customer,
            json={"product_id": PRODUCT_ONE, "quantity": 1},
        ).raise_for_status()
        failed_assessment = api.post(
            "/v1/checkout",
            headers=customer,
            json={
                "payment_token": "tok_sandbox_risk-fail-flow",
                "idempotency_key": f"failure-{uuid4()}",
                "shipping": SHIPPING,
            },
        )
        assert failed_assessment.status_code == 202, failed_assessment.text
        assert failed_assessment.json()["status"] == "review"
        failure_order_id = failed_assessment.json()["order_id"]
        queue = api.get("/v1/backoffice/risk", headers=operator).json()
        failure = next(item for item in queue if item["order_id"] == failure_order_id)
        assert failure["outcome"] == "assessment_failed"
        assert failure["reasons"] == ["sandbox_assessment_failure"]
        declined = api.post(
            f"/v1/backoffice/risk/{failure['assessment_id']}/decision",
            headers=operator,
            json={"decision": "decline"},
        )
        assert declined.status_code == 200, declined.text
        assert declined.json()["status"] == "cancelled"
        assert api.get(
            f"/v1/orders/{failure_order_id}", headers=customer
        ).json()["status"] == "cancelled"



def test_dynamic_pricing_updates_storefront_price_and_preserves_order_snapshot() -> None:
    customer = auth("synthetic-customer-subject")
    operator = auth("synthetic-operator-subject")
    # Product 12 is reserved for this flow so the commerce assertions above keep
    # their original seeded price on a fresh stack.
    product_id = "10000000-0000-4000-8000-000000000012"

    with httpx.Client(base_url=BASE_URL, timeout=10) as api:
        assert_error(api.get("/v1/backoffice/pricing"), 401, "unauthorized")
        assert_error(
            api.get("/v1/backoffice/pricing", headers=customer), 403, "forbidden"
        )

        overview = api.get("/v1/backoffice/pricing", headers=operator)
        assert overview.status_code == 200, overview.text
        policy = overview.json()["policy"]
        assert policy["max_change_ratio"] == "0.20"
        assert policy["minimum_margin_ratio"] == "0.05"
        assert policy["freshness_hours"] == 24

        before = Decimal(api.get(f"/v1/products/{product_id}").json()["price"]["amount"])

        raised = api.post(
            "/v1/backoffice/pricing/observations",
            headers=operator,
            json={
                "product_id": product_id,
                "recorded_cost": "20000",
                "supply": "2",
                "demand": "40",
                "competitor_cost": "21000",
            },
        )
        assert raised.status_code == 202, raised.text
        assert raised.json()["provenance"] == "synthetic"

        run = api.post(
            "/v1/backoffice/pricing/run",
            headers=operator,
            json={"product_ids": [product_id]},
        )
        assert run.status_code == 202, run.text
        result = run.json()
        assert result["evaluated"] == 1
        assert result["updated"] == 1
        assert result["items"][0]["outcome"] == "updated"
        new_amount = Decimal(result["items"][0]["new_amount"])
        assert new_amount > before
        assert new_amount <= before * Decimal("1.20")

        storefront = api.get(f"/v1/products/{product_id}")
        assert storefront.status_code == 200, storefront.text
        assert Decimal(storefront.json()["price"]["amount"]) == new_amount

        repeated = api.post(
            "/v1/backoffice/pricing/run",
            headers=operator,
            json={"product_ids": [product_id]},
        )
        assert repeated.status_code == 202, repeated.text
        assert repeated.json()["already_applied"] == 1
        assert repeated.json()["updated"] == 0
        assert (
            Decimal(api.get(f"/v1/products/{product_id}").json()["price"]["amount"])
            == new_amount
        )

        api.put(
            "/v1/cart/items",
            headers=customer,
            json={"product_id": product_id, "quantity": 1},
        ).raise_for_status()
        checkout = api.post(
            "/v1/checkout",
            headers=customer,
            json={
                "payment_token": "tok_sandbox_pricing-flow",
                "idempotency_key": f"pricing-{uuid4()}",
                "shipping": SHIPPING,
            },
        )
        assert checkout.status_code == 202, checkout.text
        assert checkout.json()["status"] in {"confirmed", "review"}
        order_id = checkout.json()["order_id"]
        if checkout.json()["status"] == "review":
            # Repeat orders in the same session can cross the model threshold;
            # resolve the resulting review through the audited operator path.
            queue = api.get("/v1/backoffice/risk", headers=operator).json()
            assessment = next(
                item for item in queue if item["order_id"] == order_id
            )
            allowed = api.post(
                f"/v1/backoffice/risk/{assessment['assessment_id']}/decision",
                headers=operator,
                json={"decision": "allow"},
            )
            assert allowed.status_code == 200, allowed.text
        order = api.get(f"/v1/orders/{order_id}", headers=customer)
        assert order.status_code == 200, order.text
        assert Decimal(order.json()["items"][0]["unit_price"]) == new_amount

        lowered = api.post(
            "/v1/backoffice/pricing/observations",
            headers=operator,
            json={
                "product_id": product_id,
                "recorded_cost": "20000",
                "supply": "500",
                "demand": "1",
                "competitor_cost": "15000",
            },
        )
        assert lowered.status_code == 202, lowered.text
        second = api.post(
            "/v1/backoffice/pricing/run",
            headers=operator,
            json={"product_ids": [product_id]},
        )
        assert second.status_code == 202, second.text
        assert second.json()["updated"] == 1
        reduced = Decimal(
            api.get(f"/v1/products/{product_id}").json()["price"]["amount"]
        )
        assert reduced < new_amount
        assert reduced >= Decimal("20000") * Decimal("1.05")

        unchanged_order = api.get(f"/v1/orders/{order_id}", headers=customer)
        assert Decimal(unchanged_order.json()["items"][0]["unit_price"]) == new_amount

        history = api.get("/v1/backoffice/pricing", headers=operator)
        assert history.status_code == 200, history.text
        changes = [
            change
            for change in history.json()["recent_changes"]
            if change["product_id"] == product_id
        ]
        assert len(changes) == 2
        assert all(
            change["contributing_inputs"]["policy_version"] == "dec-009-v1"
            for change in changes
        )
        assert all(
            change["contributing_inputs"]["competitor_cost"] for change in changes
        )


def test_rfm_segmentation_snapshot_filter_and_export() -> None:
    customer = auth("synthetic-customer-subject")
    operator = auth("synthetic-operator-subject")

    with httpx.Client(base_url=BASE_URL, timeout=10) as api:
        assert_error(api.get("/v1/backoffice/segments"), 401, "unauthorized")
        assert_error(
            api.get("/v1/backoffice/segments", headers=customer), 403, "forbidden"
        )

        run = api.post("/v1/backoffice/segments/run", headers=operator)
        assert run.status_code == 202, run.text
        result = run.json()
        assert result["policy_version"] == "dec-011-v1"
        assert result["classified"] + result["insufficient_history"] == 40
        assert result["classified"] >= 38
        assert result["eligible_orders"] >= 342
        assert sum(count["customers"] for count in result["counts"]) == result[
            "classified"
        ]

        overview = api.get(
            "/v1/backoffice/segments?limit=200", headers=operator
        )
        assert overview.status_code == 200, overview.text
        data = overview.json()
        assert data["snapshot_available"] is True
        assert data["cohort_size"] == result["classified"]
        assert data["total_members"] == result["classified"]
        assert len(data["members"]) == result["classified"]
        assert data["policy"]["window_days"] == 365
        for member in data["members"]:
            assert 1 <= member["recency_score"] <= 5
            assert 1 <= member["frequency_score"] <= 5
            assert 1 <= member["monetary_score"] <= 5
            assert member["segment"] in {
                "champions",
                "loyal",
                "potential",
                "new",
                "at_risk",
                "hibernating",
            }

        selected = next(count for count in data["counts"] if count["customers"] > 0)
        segment = selected["segment"]
        filtered = api.get(
            f"/v1/backoffice/segments?segment={segment}&limit=200",
            headers=operator,
        )
        assert filtered.status_code == 200, filtered.text
        filtered_data = filtered.json()
        assert filtered_data["total_members"] == selected["customers"]
        assert all(
            member["segment"] == segment for member in filtered_data["members"]
        )

        export = api.get(
            f"/v1/backoffice/segments/export?segment={segment}", headers=operator
        )
        assert export.status_code == 200, export.text
        assert export.headers["content-type"].startswith("text/csv")
        lines = export.text.strip().splitlines()
        assert lines[0].startswith("customer_id,email,display_name")
        assert len(lines) == selected["customers"] + 1

        repeated = api.post("/v1/backoffice/segments/run", headers=operator)
        assert repeated.status_code == 202, repeated.text
        assert repeated.json()["counts"] == result["counts"]
        assert repeated.json()["classified"] == result["classified"]


def test_fraud_model_evidence_and_ordinary_checkout() -> None:
    customer = auth("synthetic-customer-subject")
    other_customer = auth("synthetic-other-customer-subject")
    operator = auth("synthetic-operator-subject")

    with httpx.Client(base_url=BASE_URL, timeout=10) as api:
        assert_error(api.get("/v1/backoffice/risk/model"), 401, "unauthorized")
        assert_error(
            api.get("/v1/backoffice/risk/model", headers=customer), 403, "forbidden"
        )

        model = api.get("/v1/backoffice/risk/model", headers=operator)
        assert model.status_code == 200, model.text
        body = model.json()
        assert body["version_label"].endswith("fraud-v1")
        assert float(body["threshold"]) <= 0.70
        assert body["metrics"]["recall"] >= 0.80
        assert body["metrics"]["false_positive_rate"] <= 0.10
        assert "amount_ratio" in body["feature_names"]
        assert "synthetic" in body["limitations"].lower()

        queue = api.get("/v1/backoffice/risk", headers=operator)
        assert queue.status_code == 200, queue.text
        for item in queue.json():
            assert "reasons" in item
            assert isinstance(item["reasons"], list)
            assert "model_version" in item


def test_analytics_dashboards_filter_and_reconcile() -> None:
    customer = auth("synthetic-customer-subject")
    operator = auth("synthetic-operator-subject")
    end = datetime.now(UTC).date()
    start = end - timedelta(days=89)

    with httpx.Client(base_url=BASE_URL, timeout=15) as api:
        query = f"/v1/backoffice/analytics?from={start}&to={end}"
        assert_error(api.get(query), 401, "unauthorized")
        assert_error(api.get(query, headers=customer), 403, "forbidden")

        report = api.get(query, headers=operator)
        assert report.status_code == 200, report.text
        body = report.json()
        assert body["scope"]["date_from"] == start.isoformat()
        assert body["scope"]["date_to"] == end.isoformat()
        assert body["behaviour"]["product_views"] > 0
        assert body["behaviour"]["sessions"] > 0
        assert body["behaviour"]["orders_per_session"]
        assert Decimal(body["financial"]["gross_sales"]) > 0
        assert Decimal(body["financial"]["net_sales"]) <= Decimal(
            body["financial"]["gross_sales"]
        )
        assert body["financial"]["currency"] == "EGP"
        assert len(body["daily"]) == 90
        assert any("Profit is not displayed" in item for item in body["definitions"])
        for check in body["reconciliation"]:
            assert check["matches"] is True, check
        assert {check["metric"] for check in body["reconciliation"]} == {
            "order_totals",
            "order_count",
        }
        assert body["top_products"], "expected product performance rows"
        assert Decimal(body["top_products"][0]["revenue"]) >= 0

        phones = api.get(f"{query}&category=phones", headers=operator)
        assert phones.status_code == 200, phones.text
        phone_body = phones.json()
        assert phone_body["scope"]["category"] == "phones"
        assert phone_body["scope"]["category_product_count"] > 0
        assert phone_body["behaviour"]["product_views"] <= body["behaviour"]["product_views"]
        assert Decimal(phone_body["financial"]["gross_sales"]) <= Decimal(
            body["financial"]["gross_sales"]
        )
        for check in phone_body["reconciliation"]:
            assert check["matches"] is True, check

        unknown = api.get(f"{query}&category=does-not-exist", headers=operator)
        assert unknown.status_code == 200, unknown.text
        assert unknown.json()["category_without_products"] is True
        assert unknown.json()["no_events"] is True

        narrow = api.get(
            f"/v1/backoffice/analytics?from={end}&to={end}", headers=operator
        )
        assert narrow.status_code == 200, narrow.text
        assert len(narrow.json()["daily"]) == 1

        inverted = api.get(
            f"/v1/backoffice/analytics?from={end}&to={start}", headers=operator
        )
        assert inverted.status_code == 422
        assert inverted.json()["error"]["code"] == "invalid_input"

def test_operator_order_lifecycle_advances_cancels_refunds_and_adjusts() -> None:
    """DEC-018: fulfilment, refunds, cancellation, and stock are operator actions."""
    customer = auth("synthetic-customer-subject")
    operator = auth("synthetic-operator-subject")

    with httpx.Client(base_url=BASE_URL, timeout=10) as api:
        inventory = api.get("/v1/backoffice/inventory", headers=operator).json()
        product = next(
            row for row in inventory["items"] if row["product_id"] == PRODUCT_TWO
        )
        available_before = product["available"]

        api.put(
            "/v1/cart/items",
            headers=customer,
            json={"product_id": PRODUCT_TWO, "quantity": 1},
        ).raise_for_status()
        checkout = api.post(
            "/v1/checkout",
            headers=customer,
            json={
                "payment_token": "tok_sandbox_safe-lifecycle",
                "idempotency_key": f"lifecycle-{uuid4()}",
                "shipping": SHIPPING,
            },
        )
        assert checkout.status_code == 202, checkout.text
        order_id = checkout.json()["order_id"]
        if checkout.json()["status"] == "review":
            queue = api.get("/v1/backoffice/risk", headers=operator).json()
            assessment = next(item for item in queue if item["order_id"] == order_id)
            allowed = api.post(
                f"/v1/backoffice/risk/{assessment['assessment_id']}/decision",
                headers=operator,
                json={"decision": "allow"},
            )
            assert allowed.status_code == 200, allowed.text

        detail = api.get(f"/v1/backoffice/orders/{order_id}", headers=operator)
        assert detail.status_code == 200, detail.text
        assert detail.json()["shipment"]["status"] == "pending"
        subtotal = detail.json()["subtotal"]

        # A jump over `ready` is refused, not silently applied.
        skipped = api.post(
            f"/v1/backoffice/orders/{order_id}/shipment",
            headers=operator,
            json={"status": "delivered"},
        )
        assert_error(skipped, 409, "conflict")

        for target in ("ready", "in_transit"):
            moved = api.post(
                f"/v1/backoffice/orders/{order_id}/shipment",
                headers=operator,
                json={"status": target},
            )
            assert moved.status_code == 200, moved.text
            assert moved.json()["status"] == target

        assert api.get(
            f"/v1/backoffice/orders/{order_id}", headers=operator
        ).json()["status"] == "shipped"
        shipment = api.get(f"/v1/orders/{order_id}/shipment", headers=customer)
        assert shipment.json()["status"] == "in_transit"
        assert [event["status"] for event in shipment.json()["events"]] == [
            "pending",
            "ready",
            "in_transit",
        ]

        partial = api.post(
            f"/v1/backoffice/orders/{order_id}/refund",
            headers=operator,
            json={"amount": "100", "reason": "Integration partial refund"},
        )
        assert partial.status_code == 200, partial.text
        assert partial.json()["refund_total"] == "100"
        assert partial.json()["status"] == "shipped"
        assert api.get(
            f"/v1/orders/{order_id}", headers=customer
        ).json()["subtotal"] == subtotal

        assert_error(
            api.post(
                f"/v1/backoffice/orders/{order_id}/refund",
                headers=operator,
                json={"amount": subtotal, "reason": "Integration over-refund"},
            ),
            409,
            "conflict",
        )
        assert_error(
            api.post(
                f"/v1/backoffice/orders/{order_id}/cancel",
                headers=operator,
                json={"reason": "Integration cancel after shipping"},
            ),
            409,
            "conflict",
        )
        assert_error(
            api.post(
                f"/v1/backoffice/orders/{order_id}/shipment",
                headers=customer,
                json={"status": "delivered"},
            ),
            403,
            "forbidden",
        )

        # A second order is cancelled before shipping and returns its stock.
        api.put(
            "/v1/cart/items",
            headers=customer,
            json={"product_id": PRODUCT_TWO, "quantity": 1},
        ).raise_for_status()
        second = api.post(
            "/v1/checkout",
            headers=customer,
            json={
                "payment_token": "tok_sandbox_safe-lifecycle-2",
                "idempotency_key": f"lifecycle-cancel-{uuid4()}",
                "shipping": SHIPPING,
            },
        )
        second_id = second.json()["order_id"]
        if second.json()["status"] == "review":
            queue = api.get("/v1/backoffice/risk", headers=operator).json()
            assessment = next(item for item in queue if item["order_id"] == second_id)
            api.post(
                f"/v1/backoffice/risk/{assessment['assessment_id']}/decision",
                headers=operator,
                json={"decision": "allow"},
            ).raise_for_status()

        stocked = api.get("/v1/backoffice/inventory", headers=operator).json()
        after_sale = next(
            row for row in stocked["items"] if row["product_id"] == PRODUCT_TWO
        )
        # The first order in this test also consumed one unit of the same product.
        assert after_sale["on_hand"] == product["on_hand"] - 2

        cancelled = api.post(
            f"/v1/backoffice/orders/{second_id}/cancel",
            headers=operator,
            json={"reason": "Integration lifecycle cancellation"},
        )
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["status"] == "cancelled"
        assert cancelled.json()["kind"] == "cancellation"

        restored = api.get("/v1/backoffice/inventory", headers=operator).json()
        after_cancel = next(
            row for row in restored["items"] if row["product_id"] == PRODUCT_TWO
        )
        assert after_cancel["on_hand"] == product["on_hand"] - 1

        adjusted = api.post(
            f"/v1/backoffice/inventory/{PRODUCT_TWO}/adjustments",
            headers=operator,
            json={"quantity_delta": 2, "reason": "Integration stock count"},
        )
        assert adjusted.status_code == 200, adjusted.text
        assert adjusted.json()["on_hand"] == after_cancel["on_hand"] + 2
        assert adjusted.json()["available"] == after_cancel["available"] + 2
        assert available_before >= 0
