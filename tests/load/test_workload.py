"""Stage 4 workload checks against a live stack.

DEC-014 accepts a demonstration workload of up to 10 requests per second with 100
concurrent sessions. These checks run that workload against the Docker Compose API
and measure the SRS section 7 latency targets. They are black-box, skipped when no
API is reachable, and do not change catalog or price state.

Run with::

    uv run --project services/api --extra test pytest tests/load -v
"""

from __future__ import annotations

import asyncio
import os
import statistics
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest

BASE_URL = os.getenv("SMART_ECOMMERCE_TEST_BASE_URL", "http://127.0.0.1:8000")
PRODUCT = "10000000-0000-4000-8000-000000000001"
CUSTOMER = "synthetic-customer-subject"
OPERATOR = "synthetic-operator-subject"
SHIPPING = {
    "recipient_name": "Synthetic Customer",
    "phone": "+201000000000",
    "city": "Cairo",
    "address_line": "12 Synthetic Test Street, Apt 4",
}

# DEC-014 / SRS section 7 p95 ceilings in milliseconds.
TARGETS = {
    "catalog": 500,
    "search": 500,
    "facets": 500,
    "detail": 500,
    "recommendations": 500,
    "cart": 500,
    "analytics": 2000,
}

SUSTAINED_SECONDS = float(os.getenv("SMART_ECOMMERCE_LOAD_SECONDS", "20"))
TARGET_RATE = float(os.getenv("SMART_ECOMMERCE_LOAD_RATE", "10"))
CONCURRENT_SESSIONS = int(os.getenv("SMART_ECOMMERCE_LOAD_SESSIONS", "100"))


def auth(subject: str) -> dict[str, str]:
    return {"authorization": f"Bearer {subject}"}


def p95(samples: list[float]) -> float:
    if len(samples) < 2:
        return samples[0] if samples else 0.0
    return statistics.quantiles(samples, n=20)[-1]


@pytest.fixture(scope="module")
def base_url() -> str:
    try:
        ready = httpx.get(f"{BASE_URL}/health/ready", timeout=5)
    except httpx.HTTPError:  # pragma: no cover - environment guard
        pytest.skip(f"No API at {BASE_URL}")
    if ready.status_code != 200:
        pytest.skip("The API is not ready.")
    return BASE_URL


def _client(base_url: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=base_url,
        timeout=30,
        limits=httpx.Limits(
            max_connections=CONCURRENT_SESSIONS + 20,
            max_keepalive_connections=CONCURRENT_SESSIONS,
        ),
    )


async def _timed(
    client: httpx.AsyncClient,
    label: str,
    method: str,
    path: str,
    **kwargs,
) -> tuple[str, float, int, str]:
    began = time.perf_counter()
    response = await client.request(method, path, **kwargs)
    elapsed = (time.perf_counter() - began) * 1000
    return label, elapsed, response.status_code, response.text[:200]


def _assert_targets(samples: dict[str, list[float]], errors: list[str]) -> None:
    assert not errors, "\n".join(errors[:10])
    for label, values in samples.items():
        if not values:
            continue
        measured = p95(values)
        print(f"{label:>16}: n={len(values):>3} p95={measured:7.1f} ms "
              f"target={TARGETS[label]} ms")
        assert measured <= TARGETS[label], (
            f"{label} p95 {measured:.0f} ms exceeds the {TARGETS[label]} ms target"
        )


def test_sustained_mixed_workload(base_url: str) -> None:
    """Open-loop 10 req/s for the agreed duration with up to 100 in flight."""
    today = datetime.now(UTC).date()
    start = today - timedelta(days=29)

    async def scenario() -> None:
        samples: dict[str, list[float]] = {label: [] for label in TARGETS}
        errors: list[str] = []
        semaphore = asyncio.Semaphore(CONCURRENT_SESSIONS)
        async with _client(base_url) as client:
            # Warm the connection pool and any lazy model load before measuring.
            await client.get("/v1/products?limit=5")

            async def call(label: str, method: str, path: str, **kwargs) -> None:
                async with semaphore:
                    result = await _timed(client, label, method, path, **kwargs)
                name, elapsed, status, body = result
                if status >= 500:
                    errors.append(f"{name} {method} {path} -> {status} {body}")
                elif status >= 400:
                    errors.append(f"{name} {method} {path} -> unexpected {status} {body}")
                else:
                    samples[name].append(elapsed)

            # One cycle exercises every read surface in the DEC-014 workload.
            cycle = [
                ("catalog", "GET", "/v1/products?limit=20", {}),
                ("search", "GET", "/v1/products?q=phone&limit=20", {}),
                ("facets", "GET", "/v1/products/facets?q=phone", {}),
                ("detail", "GET", f"/v1/products/{PRODUCT}", {}),
                (
                    "recommendations",
                    "GET",
                    "/v1/recommendations?limit=5",
                    {"headers": auth(CUSTOMER)},
                ),
                ("cart", "GET", "/v1/cart", {"headers": auth(CUSTOMER)}),
                (
                    "analytics",
                    "GET",
                    f"/v1/backoffice/analytics?from={start}&to={today}",
                    {"headers": auth(OPERATOR)},
                ),
            ]

            interval = 1.0 / TARGET_RATE
            loop = asyncio.get_running_loop()
            started = loop.time()
            issued = 0
            pending: list[asyncio.Task] = []
            while (loop.time() - started) < SUSTAINED_SECONDS:
                label, method, path, kwargs = cycle[issued % len(cycle)]
                pending.append(asyncio.create_task(call(label, method, path, **kwargs)))
                issued += 1
                deadline = started + issued * interval
                delay = deadline - loop.time()
                if delay > 0:
                    await asyncio.sleep(delay)
            await asyncio.gather(*pending)

        expected = int(SUSTAINED_SECONDS * TARGET_RATE)
        assert issued >= expected - 2, f"issued {issued} requests, expected ~{expected}"
        assert len(samples["catalog"]) > 0
        _assert_targets(samples, errors)

    asyncio.run(scenario())


def test_hundred_concurrent_sessions(base_url: str) -> None:
    """100 sessions read catalog, detail, recommendations, and cart at once."""
    async def session() -> tuple[list[tuple[str, float]], list[str]]:
        timings: list[tuple[str, float]] = []
        errors: list[str] = []
        async with _client(base_url) as client:
            # Establish the connection before timing so the measurement describes
            # request latency under concurrency, not TCP setup.
            await client.get("/health/live")
            for label, method, path, kwargs in [
                ("catalog", "GET", "/v1/products?limit=20", {}),
                ("detail", "GET", f"/v1/products/{PRODUCT}", {}),
                (
                    "recommendations",
                    "GET",
                    "/v1/recommendations?limit=5",
                    {"headers": auth(CUSTOMER)},
                ),
                ("cart", "GET", "/v1/cart", {"headers": auth(CUSTOMER)}),
            ]:
                name, elapsed, status, body = await _timed(
                    client, label, method, path, **kwargs
                )
                if status != 200:
                    errors.append(f"{name} {path} -> {status} {body}")
                timings.append((name, elapsed))
        return timings, errors

    async def burst() -> tuple[dict[str, list[float]], list[str]]:
        results = await asyncio.gather(
            *(session() for _ in range(CONCURRENT_SESSIONS))
        )
        samples: dict[str, list[float]] = {label: [] for label in TARGETS}
        errors: list[str] = []
        for timings, session_errors in results:
            errors.extend(session_errors)
            for label, elapsed in timings:
                samples[label].append(elapsed)
        return samples, errors

    samples, errors = asyncio.run(burst())
    assert not errors, "\n".join(errors[:10])
    assert len(samples["catalog"]) == CONCURRENT_SESSIONS
    _assert_targets(samples, errors)


def test_concurrent_duplicate_checkout_creates_one_order(base_url: str) -> None:
    """Ten simultaneous retries of one idempotency key produce exactly one order."""
    customer = auth(CUSTOMER)
    key = f"load-duplicate-{uuid4()}"

    async def scenario() -> list[httpx.Response]:
        async with _client(base_url) as client:
            cart = await client.put(
                "/v1/cart/items",
                headers=customer,
                json={"product_id": PRODUCT, "quantity": 1},
            )
            assert cart.status_code == 200, cart.text
            payload = {
                "payment_token": "tok_sandbox_load-duplicate",
                "idempotency_key": key,
                "shipping": SHIPPING,
            }
            gate = asyncio.Event()

            async def attempt() -> httpx.Response:
                await gate.wait()
                return await client.post("/v1/checkout", headers=customer, json=payload)

            attempts = [asyncio.create_task(attempt()) for _ in range(10)]
            await asyncio.sleep(0.05)
            gate.set()
            return await asyncio.gather(*attempts)

    responses = asyncio.run(scenario())
    statuses = [response.status_code for response in responses]
    assert all(status == 202 for status in statuses), statuses
    bodies = [response.json() for response in responses]
    order_ids = {body["order_id"] for body in bodies}
    assert len(order_ids) == 1, f"duplicate orders created: {order_ids}"
    assert {body["status"] for body in bodies} <= {"confirmed", "review"}
