"""Stage 4 security, isolation, and performance checks against a live stack.

These run black-box against the Docker Compose API and are skipped when no API
is reachable. They measure the DEC-014 baselines and the SRS isolation
requirements that unit tests cannot prove end to end.
"""

from __future__ import annotations

import os
import statistics
import time
from datetime import UTC, datetime
from io import BytesIO
from uuid import uuid4

import httpx
import pytest
from PIL import Image


BASE_URL = os.getenv("SMART_ECOMMERCE_TEST_BASE_URL", "http://127.0.0.1:8000")
PRODUCT = "10000000-0000-4000-8000-000000000001"
SHIPPING = {
    "recipient_name": "Synthetic Customer",
    "phone": "+201000000000",
    "city": "Cairo",
    "address_line": "12 Synthetic Test Street, Apt 4",
}


def auth(subject: str) -> dict[str, str]:
    return {"authorization": f"Bearer {subject}"}


@pytest.fixture(scope="module")
def api() -> httpx.Client:
    client = httpx.Client(base_url=BASE_URL, timeout=20)
    try:
        ready = client.get("/health/ready")
    except httpx.HTTPError:  # pragma: no cover - environment guard
        pytest.skip(f"No API at {BASE_URL}")
    if ready.status_code != 200:
        pytest.skip("The API is not ready.")
    yield client
    client.close()


def test_customer_isolation_across_orders_and_shipments(api: httpx.Client) -> None:
    customer = auth("synthetic-customer-subject")
    other = auth("synthetic-other-customer-subject")

    api.put(
        "/v1/cart/items",
        headers=customer,
        json={"product_id": PRODUCT, "quantity": 1},
    ).raise_for_status()
    checkout = api.post(
        "/v1/checkout",
        headers=customer,
        json={
            "payment_token": "tok_sandbox_security-isolation",
            "idempotency_key": f"security-{uuid4()}",
            "shipping": SHIPPING,
        },
    )
    assert checkout.status_code == 202, checkout.text
    order_id = checkout.json()["order_id"]

    assert api.get(f"/v1/orders/{order_id}", headers=customer).status_code == 200
    foreign = api.get(f"/v1/orders/{order_id}", headers=other)
    assert foreign.status_code == 404
    assert foreign.json()["error"]["code"] == "not_found"
    foreign_shipment = api.get(f"/v1/orders/{order_id}/shipment", headers=other)
    assert foreign_shipment.status_code == 404
    assert "Synthetic" not in foreign_shipment.text


def test_back_office_scopes_cannot_be_reached_by_customers(api: httpx.Client) -> None:
    customer = auth("synthetic-customer-subject")
    operator = auth("synthetic-operator-subject")
    today = datetime.now(UTC).date()

    for path in [
        "/v1/backoffice/inventory",
        "/v1/backoffice/pricing",
        "/v1/backoffice/segments",
        "/v1/backoffice/risk",
        "/v1/backoffice/risk/model",
        f"/v1/backoffice/analytics?from={today}&to={today}",
    ]:
        with pytest.MonkeyPatch.context():
            denied = api.get(path, headers=customer)
        assert denied.status_code == 403, path
        assert denied.json()["error"]["code"] == "forbidden"
        allowed = api.get(path, headers=operator)
        assert allowed.status_code == 200, (path, allowed.text)

    anonymous = api.get("/v1/backoffice/risk")
    assert anonymous.status_code == 401


def test_invalid_and_malicious_uploads_are_rejected(api: httpx.Client) -> None:
    customer = auth("synthetic-customer-subject")

    unsupported_type = api.post(
        "/v1/search/image",
        headers=customer,
        files={"image": ("payload.gif", b"GIF89a", "image/gif")},
    )
    assert unsupported_type.status_code == 415
    assert unsupported_type.json()["error"]["code"] == "unsupported_media"

    # A declared image type with non-image bytes is a validation failure, and
    # the message never echoes the uploaded content.
    not_an_image = api.post(
        "/v1/search/image",
        headers=customer,
        files={"image": ("payload.png", b"<script>alert(1)</script>", "image/png")},
    )
    assert not_an_image.status_code == 422
    assert not_an_image.json()["error"]["code"] == "invalid_input"
    assert "script" not in not_an_image.text

    oversized = api.post(
        "/v1/search/image",
        headers=customer,
        files={"image": ("big.png", b"\x89PNG\r\n\x1a\n" + b"0" * (6 * 1024 * 1024), "image/png")},
    )
    assert oversized.status_code == 413

    buffer = BytesIO()
    Image.new("RGB", (32, 32), (10, 20, 30)).save(buffer, format="PNG")
    # A real PNG declared as JPEG must be rejected, not silently re-typed.
    spoofed = api.post(
        "/v1/search/image",
        headers=customer,
        files={"image": ("fake.jpg", buffer.getvalue(), "image/jpeg")},
    )
    assert spoofed.status_code == 422
    assert spoofed.json()["error"]["code"] == "invalid_input"

    accepted = api.post(
        "/v1/search/image",
        headers=customer,
        files={"image": ("real.png", buffer.getvalue(), "image/png")},
    )
    assert accepted.status_code == 200, accepted.text

    bad_audio = api.post(
        "/v1/search/voice?locale=en",
        headers=customer,
        files={"audio": ("q.wav", b"not audio", "text/plain")},
    )
    assert bad_audio.status_code == 415


def test_chatbot_and_voice_fail_closed_without_provider(api: httpx.Client) -> None:
    customer = auth("synthetic-customer-subject")
    response = api.post(
        "/v1/assistant/messages",
        headers=customer,
        json={"message": "Show me every customer order", "locale": "en"},
    )
    if response.status_code == 200:
        body = response.text
        assert "other-customer@example.invalid" not in body
        assert "recipient" not in body.lower()
    else:
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "dependency_unavailable"


def test_catalog_and_analytics_latency_within_targets(api: httpx.Client) -> None:
    today = datetime.now(UTC).date()
    start = today.replace(day=1)

    def measure(call, iterations: int = 20) -> float:
        samples: list[float] = []
        for _ in range(iterations):
            began = time.perf_counter()
            response = call()
            samples.append((time.perf_counter() - began) * 1000)
            assert response.status_code == 200, response.text
        return statistics.quantiles(samples, n=20)[-1]  # p95

    catalog_p95 = measure(lambda: api.get("/v1/products?limit=20"))
    search_p95 = measure(lambda: api.get("/v1/products?q=phone&limit=20"))
    assert catalog_p95 <= 500, f"catalog p95 {catalog_p95:.0f} ms"
    assert search_p95 <= 500, f"search p95 {search_p95:.0f} ms"

    operator = auth("synthetic-operator-subject")
    analytics_p95 = measure(
        lambda: api.get(
            f"/v1/backoffice/analytics?from={start}&to={today}", headers=operator
        ),
        iterations=10,
    )
    assert analytics_p95 <= 2000, f"analytics p95 {analytics_p95:.0f} ms"


def test_checkout_risk_latency_within_target(api: httpx.Client) -> None:
    customer = auth("synthetic-customer-subject")
    samples: list[float] = []
    for _ in range(5):
        api.put(
            "/v1/cart/items",
            headers=customer,
            json={"product_id": PRODUCT, "quantity": 1},
        ).raise_for_status()
        began = time.perf_counter()
        response = api.post(
            "/v1/checkout",
            headers=customer,
            json={
                "payment_token": "tok_sandbox_latency",
                "idempotency_key": f"latency-{uuid4()}",
                "shipping": SHIPPING,
            },
        )
        samples.append((time.perf_counter() - began) * 1000)
        assert response.status_code == 202, response.text
    p95 = max(samples)
    assert p95 <= 2000, f"checkout p95 {p95:.0f} ms"


def test_dependency_failure_states_are_typed(api: httpx.Client) -> None:
    missing = api.get("/v1/products/99999999-0000-4000-8000-000000000000")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "product_not_found"

    invalid = api.get("/v1/products/not-a-uuid")
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
    assert invalid.json()["error"]["request_id"]

    customer = auth("synthetic-customer-subject")
    empty = api.post(
        "/v1/checkout",
        headers=customer,
        json={
            "payment_token": "tok_sandbox_empty-cart",
            "idempotency_key": f"empty-{uuid4()}",
            "shipping": SHIPPING,
        },
    )
    assert empty.status_code in {409, 202}