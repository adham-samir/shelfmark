"""The published platform contract must match the application it documents.

``docs/api/platform.openapi.json`` is maintained by hand rather than generated,
because it documents deliberate choices the framework cannot infer: which
capability each route needs, which routes are customer- or operator-scoped, and
what each operation is for. The risk of hand-maintenance is drift, so this test
compares it against ``app.openapi()`` and fails on any path, method, or
operation-id that exists in one and not the other.

Two documented exceptions:

* ``/health/live`` and ``/health/ready`` are operational endpoints, not part of
  the published platform contract.
* ``/v1/products``, ``/v1/products/facets``, and ``/v1/products/{product_id}``
  belong to ``docs/api/catalog.openapi.json``, which is validated separately.
"""

import json
from pathlib import Path

import pytest

from smart_ecommerce_api.main import app

ROOT = Path(__file__).resolve().parents[3]
PLATFORM = json.loads((ROOT / "docs/api/platform.openapi.json").read_text())
CATALOG = json.loads((ROOT / "docs/api/catalog.openapi.json").read_text())

OPERATIONAL = {"/health/live", "/health/ready"}


def _methods(entry: dict) -> set[str]:
    return {method for method in entry if method in {"get", "post", "put", "patch", "delete"}}


def test_every_implemented_route_is_published():
    live = app.openapi()["paths"]
    documented = PLATFORM["paths"]
    catalogued = CATALOG["paths"]

    missing = []
    for path, entry in live.items():
        if path in OPERATIONAL or path in catalogued:
            continue
        if path not in documented:
            missing.append(path)
            continue
        undocumented_methods = _methods(entry) - _methods(documented[path])
        for method in sorted(undocumented_methods):
            missing.append(f"{method.upper()} {path}")

    assert missing == [], (
        "Implemented but absent from docs/api/platform.openapi.json: "
        + ", ".join(sorted(missing))
    )


def test_the_contract_publishes_nothing_the_application_lacks():
    live = app.openapi()["paths"]
    stale = []
    for path, entry in PLATFORM["paths"].items():
        if path not in live:
            stale.append(path)
            continue
        for method in sorted(_methods(entry) - _methods(live[path])):
            stale.append(f"{method.upper()} {path}")

    assert stale == [], (
        "Documented in docs/api/platform.openapi.json but not implemented: "
        + ", ".join(sorted(stale))
    )


def test_operation_ids_are_unique_and_agree_with_the_application():
    """A client generates code from operation ids, so a rename is breaking."""
    live = app.openapi()["paths"]
    platform = PLATFORM["paths"]

    ids = [
        operation["operationId"]
        for entry in platform.values()
        for method, operation in entry.items()
        if method in {"get", "post", "put", "patch", "delete"}
    ]
    assert len(ids) == len(set(ids)), "Duplicate operationId in the platform contract"

    mismatched = []
    for path, entry in platform.items():
        for method, operation in entry.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            live_operation = live.get(path, {}).get(method)
            if live_operation is None:
                continue
            if live_operation["operationId"] != operation["operationId"]:
                mismatched.append(
                    f"{method.upper()} {path}: contract={operation['operationId']} "
                    f"app={live_operation['operationId']}"
                )
    assert mismatched == [], "Operation ids drifted: " + "; ".join(mismatched)


def test_the_contract_version_matches_the_application():
    assert PLATFORM["info"]["version"] == app.version, (
        "docs/api/platform.openapi.json and the FastAPI application disagree on "
        f"the version: {PLATFORM['info']['version']} vs {app.version}"
    )


@pytest.mark.parametrize(
    "path",
    [
        "/v1/backoffice/orders/{order_id}/shipment",
        "/v1/backoffice/orders/{order_id}/cancel",
        "/v1/backoffice/orders/{order_id}/refund",
        "/v1/backoffice/inventory/{product_id}/adjustments",
        "/v1/orders/{order_id}/cancel",
        "/v1/orders/{order_id}/reorder",
        "/v1/addresses",
        "/v1/account/password",
    ],
)
def test_lifecycle_routes_declare_the_capability_they_need(path):
    """The capability annotation is the contract's main hand-written value."""
    operations = PLATFORM["paths"][path]
    annotated = [
        operation
        for method, operation in operations.items()
        if method in {"get", "post", "put", "patch", "delete"}
    ]
    assert annotated, path
    for operation in annotated:
        if path in {"/v1/orders/{order_id}/cancel", "/v1/orders/{order_id}/reorder",
                    "/v1/addresses", "/v1/account/password"}:
            # Customer-scoped: a session, not an operator capability.
            assert operation["security"] == [{"bearerAuth": []}], path
            continue
        assert operation["x-required-scopes"], path
